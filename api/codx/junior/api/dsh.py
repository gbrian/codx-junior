"""
codx-junior's DSH integration API.

Routes:

* ``POST /api/dsh/events``       DSH -> codx-junior webhook (HMAC protected)
* ``GET  /api/dsh/status``       bridge configuration + DSH health
* ``POST /api/dsh/sync``         pull every DSH task into the mirror board
* ``POST /api/dsh/tasks``        create a DSH session and mirror it as a task
* ``GET  /api/dsh/tasks/{id}/messages``  live message surface from DSH
* ``POST /api/dsh/tasks/{id}/prompt``    send a follow-up prompt to DSH
* ``POST /api/dsh/tasks/{id}/cancel``    cancel the active DSH turn
* ``POST /api/dsh/tasks/{id}/rename``    rename the DSH session

The routes never persist DSH message content. Only task identity and board
placement live in codx-junior's task files; the conversation is fetched live
from the bridge.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from codx.junior.integrations.dsh import (
    DshAuthError,
    DshConfig,
    DshError,
    DshSync,
    DshTask,
    verify_webhook,
)
from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_WEBHOOK_BYTES = 5 * 1024 * 1024


def _session(request: Request):
    session = getattr(request.state, "codx_junior_session", None)
    if session is None:
        raise HTTPException(
            status_code=400,
            detail="codx_path is required (query string or x-codx-path header)",
        )
    return session


def _config(settings) -> DshConfig:
    return DshConfig.from_settings(settings)


def _sync(request: Request) -> DshSync:
    session = _session(request)
    return DshSync(session.settings).for_chat_manager(session.get_chat_manager())


def _public_config(config: DshConfig) -> dict:
    return {
        "url": config.url,
        "board": config.board,
        "columns": list(config.columns),
        "enabled": config.enabled,
        "only_project": config.only_project,
        "project_root": config.project_root,
        "has_secret": bool(config.secret),
    }


@router.post("/dsh/events")
async def dsh_events(request: Request):
    """Receive a task change notification from the DSH plugin."""
    raw = await request.body()
    if len(raw) > MAX_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="webhook body is too large")
    settings = _session(request).settings
    config = _config(settings)
    try:
        verify_webhook(request.headers, raw, config)
    except DshAuthError as error:
        logger.warning("dsh_events: rejected webhook: %s", error)
        raise HTTPException(status_code=401, detail=str(error)) from error

    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail=f"invalid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="webhook body must be a JSON object")

    sync = _sync(request)
    try:
        result = sync.handle_event(payload)
    except DshError as error:
        logger.error("dsh_events: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"ok": True, **result}


@router.get("/dsh/status")
def dsh_status(
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Report the local bridge configuration and whether DSH is reachable."""
    settings = _session(request).settings
    config = _config(settings)
    result = {"ok": True, "config": _public_config(config), "dsh": None, "error": None}
    if not config.secret:
        result["error"] = "missing bridge secret"
        return result
    try:
        sync = DshSync(settings, config=config)
        result["dsh"] = sync.client.health()
    except DshError as error:
        result["ok"] = False
        result["error"] = str(error)
    return result


@router.post("/dsh/sync")
def dsh_sync(
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Pull all DSH tasks into this project's mirror board."""
    sync = _sync(request)
    try:
        return {"ok": True, **sync.sync_all()}
    except DshError as error:
        logger.error("dsh_sync: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/dsh/tasks")
async def dsh_create_task(
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """
    Create a DSH session from codx-junior and mirror it as a board task.

    Body::

        {
          "name": "Fix the login timeout",
          "prompt": "Investigate and fix the timeout",
          "board": "DSH",
          "column": "Todo",
          "parent_id": "<codx parent chat id>",
          "agent_preset": "..."
        }
    """
    data = await request.json()
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")
    name = str(data.get("name") or data.get("title") or "").strip()
    prompt = str(data.get("prompt") or data.get("content") or "")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    sync = _sync(request)
    try:
        chat = sync.create_task(
            name=name,
            prompt=prompt,
            board=data.get("board"),
            column=data.get("column"),
            parent_id=data.get("parent_id"),
            agent_preset=data.get("agent_preset") or data.get("agentPreset"),
        )
    except DshError as error:
        logger.error("dsh_create_task: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"ok": True, "chat": chat.model_dump(), "session_id": chat.external_id}


@router.get("/dsh/tasks/{session_id}/messages")
def dsh_task_messages(
    session_id: str,
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Read the live message surface of one DSH task (not persisted)."""
    sync = _sync(request)
    try:
        payload = sync.client.get_task(session_id)
    except DshError as error:
        status = 404 if error.status == 404 else 502
        raise HTTPException(status_code=status, detail=str(error)) from error
    return {
        "ok": True,
        "task": payload.get("task"),
        "messages": payload.get("messages") or [],
        "lastSeq": payload.get("lastSeq"),
    }


@router.post("/dsh/tasks/{session_id}/prompt")
async def dsh_prompt_task(
    session_id: str,
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Send a prompt to an existing DSH session."""
    data = await request.json()
    text = str((data or {}).get("text") or (data or {}).get("prompt") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="text is required")
    sync = _sync(request)
    try:
        result = sync.prompt(session_id, text, mode=str(data.get("mode") or "queue"))
    except DshError as error:
        status = 404 if error.status == 404 else 502
        raise HTTPException(status_code=status, detail=str(error)) from error
    return {"ok": True, **(result or {})}


@router.post("/dsh/tasks/{session_id}/cancel")
def dsh_cancel_task(
    session_id: str,
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Cancel the active turn of one DSH session."""
    sync = _sync(request)
    try:
        return {"ok": True, **(sync.cancel(session_id) or {})}
    except DshError as error:
        status = 404 if error.status == 404 else 502
        raise HTTPException(status_code=status, detail=str(error)) from error


@router.post("/dsh/tasks/{session_id}/rename")
async def dsh_rename_task(
    session_id: str,
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Rename one DSH session and its mirror task."""
    data = await request.json()
    title = str((data or {}).get("title") or (data or {}).get("name") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="title is required")
    sync = _sync(request)
    try:
        result = sync.rename(session_id, title)
    except DshError as error:
        status = 404 if error.status == 404 else 502
        raise HTTPException(status_code=status, detail=str(error)) from error
    try:
        chat = sync.find_chat(session_id)
        if chat is not None:
            chat.name = title
            sync.chat_manager.save_chat(chat=chat, chat_only=True)
    except Exception:  # pragma: no cover - the DSH rename already succeeded
        logger.warning("dsh_rename_task: could not update mirror chat", exc_info=True)
    return {"ok": True, **(result or {})}
