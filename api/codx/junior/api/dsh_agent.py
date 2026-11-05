"""
Outbound DSH agent API.

These endpoints are called by the DSH Host plugin, never by the browser:

* ``POST /api/dsh/agent/register``          register a running DSH Host
* ``POST /api/dsh/agent/heartbeat``         refresh liveness/load
* ``GET  /api/dsh/agent/commands``          long-poll the command queue
* ``POST /api/dsh/agent/commands/{id}/result`` post a command outcome
* ``POST /api/dsh/agent/events``            task created/changed/disposed events
* ``POST /api/dsh/agent/unregister``        best-effort shutdown notice

Every route authenticates the agent token from Global Settings
(``dsh.agent_token`` or ``CODX_JUNIOR_DSH_AGENT_TOKEN``). The token is separate
from the codx-junior user login; it only grants agent-channel access for the
project named by ``codx_path``.
"""

from __future__ import annotations

import json
import logging
from hmac import compare_digest
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from codx.junior.integrations.dsh import DshConfig, DshSync
from codx.junior.integrations.dsh_agent import (
    DshAgentClient,
    DshAgentError,
    DshCommandTimeout,
    DshInstanceOffline,
    get_dsh_agent_registry,
)

logger = logging.getLogger(__name__)

router = APIRouter()


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


def _presented_token(request: Request) -> str:
    authorization = request.headers.get("authorization") or ""
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("x-dsh-agent-token") or ""


def _verify_agent(request: Request, config: DshConfig) -> str:
    expected = (config.agent_token or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail=(
                "DSH agent token is not configured. Generate one in "
                "Global Settings → DSH Harness."
            ),
        )
    presented = _presented_token(request)
    if not presented or not compare_digest(presented, expected):
        raise HTTPException(status_code=401, detail="invalid DSH agent token")
    return presented


def _sync_for_instance(request: Request, instance_id: str) -> DshSync:
    session = _session(request)
    config = _config(session.settings)
    registry = get_dsh_agent_registry()
    client = DshAgentClient(
        registry,
        instance_id,
        timeout=max(config.timeout, 20),
    )
    return (
        DshSync(
            session.settings,
            config=config,
            client=client,
            instance_id=instance_id,
        )
        .for_chat_manager(session.get_chat_manager())
    )


def _instance_id(request: Request, payload: Optional[Dict[str, Any]] = None) -> str:
    value = (payload or {}).get("instance_id") or request.query_params.get("instance_id")
    value = str(value or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="instance_id is required")
    return value


@router.post("/dsh/agent/register")
async def dsh_agent_register(request: Request):
    """Register (or refresh) one running DSH Host and return its channel config."""
    session = _session(request)
    config = _config(session.settings)
    _verify_agent(request, config)
    try:
        payload = await request.json()
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"invalid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")
    registry = get_dsh_agent_registry()
    try:
        instance = registry.register(
            project_id=getattr(session.settings, "project_id", None),
            codx_path=getattr(session.settings, "codx_path", None),
            payload=payload,
        )
    except DshAgentError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    logger.info(
        "dsh agent registered: %s (%s) project=%s",
        instance.name,
        instance.id,
        instance.project_id,
    )
    return {
        "ok": True,
        "instance": instance.to_dict(),
        "conf": {
            "board": config.board,
            "poll_wait_ms": 25000,
            "heartbeat_ms": 5000,
            "default_instance_id": config.default_instance_id or instance.id,
        },
    }


@router.post("/dsh/agent/heartbeat")
async def dsh_agent_heartbeat(request: Request):
    """Refresh liveness and load counters for one DSH Host."""
    session = _session(request)
    config = _config(session.settings)
    _verify_agent(request, config)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")
    instance_id = _instance_id(request, payload)
    instance = get_dsh_agent_registry().heartbeat(
        instance_id,
        getattr(session.settings, "project_id", None),
        payload,
    )
    if instance is None:
        return {"ok": False, "reregister": True}
    return {
        "ok": True,
        "instance": instance.to_dict(),
        "conf": {
            "board": config.board,
            "poll_wait_ms": 25000,
            "heartbeat_ms": 5000,
        },
    }


@router.get("/dsh/agent/commands")
def dsh_agent_commands(
    request: Request,
    instance_id: str,
    wait: int = 25,
    limit: int = 20,
):
    """
    Long-poll the command queue.

    This is a blocking endpoint on purpose: FastAPI runs it in its thread pool,
    and DSH keeps the request open until a command is available or ``wait``
    expires. Returning 204 lets the plugin poll again immediately.
    """
    session = _session(request)
    config = _config(session.settings)
    _verify_agent(request, config)
    commands = get_dsh_agent_registry().take_commands(
        instance_id,
        wait_seconds=wait,
        limit=limit,
    )
    if not commands:
        return Response(status_code=204)
    return {
        "ok": True,
        "commands": [command.to_dict() for command in commands],
        "server_time": __import__("time").time(),
    }


@router.post("/dsh/agent/commands/{command_id}/result")
async def dsh_agent_command_result(command_id: str, request: Request):
    """Accept the outcome of one command."""
    session = _session(request)
    config = _config(session.settings)
    _verify_agent(request, config)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")
    instance_id = _instance_id(request, payload)
    ok = bool(payload.get("ok"))
    error = payload.get("error")
    result = payload.get("result")
    accepted = get_dsh_agent_registry().complete(
        command_id,
        instance_id,
        result=result,
        error=None if ok else (str(error or "DSH command failed")),
    )
    return {"ok": True, "accepted": accepted}


@router.post("/dsh/agent/events")
async def dsh_agent_events(request: Request):
    """Upsert mirrored tasks from the DSH event feed."""
    session = _session(request)
    config = _config(session.settings)
    _verify_agent(request, config)
    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail=f"invalid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")
    instance_id = _instance_id(request, payload)
    sync = _sync_for_instance(request, instance_id)
    try:
        result = await run_in_threadpool(sync.handle_event, payload, instance_id)
    except (DshInstanceOffline, DshCommandTimeout) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.exception("dsh_agent_events failed")
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {"ok": True, **result}


@router.post("/dsh/agent/unregister")
async def dsh_agent_unregister(request: Request):
    """Mark one instance offline on a clean shutdown (best effort)."""
    session = _session(request)
    config = _config(session.settings)
    _verify_agent(request, config)
    payload = await request.json()
    instance_id = _instance_id(request, payload if isinstance(payload, dict) else None)
    removed = get_dsh_agent_registry().unregister(
        instance_id,
        getattr(session.settings, "project_id", None),
    )
    return {"ok": True, "removed": removed}
