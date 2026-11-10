"""
codx-junior's DSH integration API.

Primary path (outbound agent channel):

* ``POST /api/dsh/agent/register``          DSH registers itself (agent token)
* ``POST /api/dsh/agent/heartbeat``         liveness/load
* ``GET  /api/dsh/agent/commands``          long-poll commands
* ``POST /api/dsh/agent/commands/{id}/result``
* ``POST /api/dsh/agent/events``            task created/changed/disposed

Dashboard / board path:

* ``GET  /api/dsh/status``       connection config + connected instances
* ``POST /api/dsh/token``        generate/rotate the DSH agent token
* ``PUT  /api/dsh/settings``     board + preferred instance
* ``POST /api/dsh/sync``         ask an instance for all tasks
* ``POST /api/dsh/tasks``        create a DSH session and mirror it
* ``GET  /api/dsh/tasks/{id}/messages``  live messages via a command
* ``POST /api/dsh/tasks/{id}/prompt``    follow-up prompt via a command
* ``POST /api/dsh/tasks/{id}/cancel``    cancel the active DSH turn
* ``POST /api/dsh/tasks/{id}/rename``    rename the DSH session

The legacy inbound bridge webhook (``POST /api/dsh/events``) remains for
backward compatibility but is no longer the dashboard path.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from codx.junior.global_settings import read_global_settings, write_settings_section
from codx.junior.integrations.dsh import (
    DshAuthError,
    DshConfig,
    DshError,
    DshSync,
    dsh_chats,
    verify_webhook,
)
from codx.junior.integrations.harness_models import HarnessModelError, list_llm_models
from codx.junior.integrations.harness_sandbox import HarnessSandboxError
from codx.junior.integrations.harness_usage import aggregate_usage
from codx.junior.integrations.dsh_agent import (
    DshAgentClient,
    DshCommandTimeout,
    DshInstanceOffline,
    generate_agent_token,
    get_dsh_agent_registry,
    write_agent_token_file,
)
from codx.junior.model.model import CodxUser, DshSettings
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


def _require_admin(user: Optional[CodxUser] = Depends(get_authenticated_user)) -> CodxUser:
    """Integration settings are admin-only, like the rest of Global Settings."""
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admins only.")
    return user


def _public_config(config: DshConfig, include_token: bool = False) -> dict:
    result = {
        "board": config.board,
        "columns": list(config.columns),
        "enabled": config.enabled,
        "only_project": config.only_project,
        "sandbox_enabled": config.sandbox_enabled,
        "project_root": config.project_root,
        "has_agent_token": bool(config.agent_token),
        "agent_token_source": config.agent_token_source,
        "default_instance_id": config.default_instance_id,
        "configured": bool(config.enabled and config.agent_token),
        # Legacy direct-bridge fields: kept for diagnostics only.
        "has_secret": bool(config.secret),
        "secret_source": config.secret_source,
    }
    if include_token:
        result["agent_token"] = config.agent_token or ""
    return result


def _instances(settings) -> list:
    registry = get_dsh_agent_registry()
    return [
        instance.to_dict()
        for instance in registry.list_instances(getattr(settings, "project_id", None))
    ]


def _resolve_instance_id(
    request: Request,
    preferred: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    session = _session(request)
    config = _config(session.settings)
    registry = get_dsh_agent_registry()
    preferred = preferred or request.query_params.get("instance_id")
    if preferred:
        instance = registry.get(str(preferred))
        if instance is None:
            raise HTTPException(status_code=404, detail=f"DSH instance {preferred} is not registered")
        return instance.id
    if session_id:
        try:
            for chat in dsh_chats(session.get_chat_manager()):
                chat_session_id = (
                    getattr(chat, "harness_task_id", None)
                    or getattr(chat, "external_id", None)
                )
                instance_id = (
                    getattr(chat, "harness_instance_id", None)
                    or getattr(chat, "external_instance_id", None)
                )
                if chat_session_id == session_id and instance_id:
                    return str(instance_id)
        except Exception:  # pragma: no cover - lookup must not hide the fallback
            logger.debug("dsh: instance lookup from chat failed", exc_info=True)
    instance = registry.default_instance(
        getattr(session.settings, "project_id", None),
        config.default_instance_id,
    )
    if instance is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "No DSH instance is connected. Start the DSH plugin with the "
                "codx-junior URL and agent token."
            ),
        )
    return instance.id


def _sync_for_instance(request: Request, instance_id: str) -> DshSync:
    session = _session(request)
    config = _config(session.settings)
    client = DshAgentClient(
        get_dsh_agent_registry(),
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


def _legacy_sync(request: Request) -> DshSync:
    session = _session(request)
    return DshSync(session.settings).for_chat_manager(session.get_chat_manager())


# ---------------------------------------------------------------------------
# Agent channel status / token / settings
# ---------------------------------------------------------------------------

@router.get("/dsh/status")
def dsh_status(
    request: Request,
    user: CodxUser = Depends(_require_admin),
):
    """Return the agent-token configuration and every registered DSH instance."""
    session = _session(request)
    config = _config(session.settings)
    registry = get_dsh_agent_registry()
    instances = _instances(session.settings)
    online = [instance for instance in instances if instance["status"] == "online"]
    default_instance = registry.default_instance(
        getattr(session.settings, "project_id", None),
        config.default_instance_id,
    )
    result = {
        "ok": bool(config.enabled and config.agent_token and online),
        "config": _public_config(config, include_token=True),
        "instances": instances,
        "online_instances": len(online),
        "default_instance_id": default_instance.id if default_instance else None,
        "mirrored_tasks": 0,
        "error": None,
    }
    try:
        mirrored = list(dsh_chats(session.get_chat_manager()))
        result["mirrored_tasks"] = len(mirrored)
        result["usage"] = aggregate_usage(mirrored)
    except Exception:  # pragma: no cover - diagnostics must not fail the panel
        logger.debug("dsh_status: could not count mirrored tasks", exc_info=True)
        result["usage"] = {"measured_tasks": 0, "cost": 0.0, "input_tokens": 0, "output_tokens": 0}
    if not config.agent_token:
        result["error"] = "Agent token is not configured. Generate one below."
    elif not online:
        result["error"] = "No DSH instance is connected. Start the DSH plugin with this URL and token."
    result["token_file"] = None
    if config.project_root:
        result["token_file"] = f"{config.project_root.rstrip('/')}/.dsh-codx-junior/token"
    return result


@router.get("/dsh/models")
def dsh_models(
    user: CodxUser = Depends(_require_admin),
):
    """
    Return the LLM models defined in codx-junior.

    The DSH plugin cannot invent a model: a task may only ask for one of these
    names (or a name resolvable through the model catalogue). The optional
    ``metadata.dsh`` block on an ``AIModel`` maps the codx-junior name to the
    provider/model ids DSH expects.
    """
    models = list_llm_models(kind="dsh")
    default_name = str(getattr(read_global_settings(), "llm_model", "") or "")
    default = next((model for model in models if model["name"] == default_name), None)
    return {"ok": True, "models": models, "default": default}


@router.post("/dsh/token")
def dsh_generate_token(
    request: Request,
    user: CodxUser = Depends(_require_admin),
):
    """Generate (or rotate) the token used by DSH agents and write the token file."""
    session = _session(request)
    current = getattr(read_global_settings(), "dsh", DshSettings())
    payload = current.model_dump()
    token = generate_agent_token()
    payload["agent_token"] = token
    model = DshSettings(**payload)
    write_settings_section("dsh", model.model_dump())
    config = _config(session.settings)
    token_file = write_agent_token_file(config.project_root, token)
    logger.info("dsh agent token rotated by '%s'", getattr(user, "username", "admin"))
    return {
        "ok": True,
        "token": token,
        "token_file": token_file,
        "config": _public_config(config, include_token=True),
    }


@router.put("/dsh/settings")
async def dsh_save_settings(
    request: Request,
    user: CodxUser = Depends(_require_admin),
):
    """Persist board, enabled and preferred-instance settings."""
    data = await request.json()
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")
    current = getattr(read_global_settings(), "dsh", DshSettings())
    payload = current.model_dump()
    if "board" in data:
        payload["board"] = str(data.get("board") or "").strip() or DshSettings().board
    if "enabled" in data:
        payload["enabled"] = bool(data.get("enabled"))
    if "only_project" in data:
        payload["only_project"] = bool(data.get("only_project"))
    if "sandbox_enabled" in data:
        payload["sandbox_enabled"] = bool(data.get("sandbox_enabled"))
    if "default_instance_id" in data:
        payload["default_instance_id"] = str(data.get("default_instance_id") or "").strip()
    # Legacy fields remain editable if a caller still sends them.
    if "url" in data:
        payload["url"] = str(data.get("url") or "").strip().rstrip("/")
    if "secret" in data and data.get("secret") is not None:
        payload["secret"] = str(data.get("secret") or "").strip()
    try:
        model = DshSettings(**payload)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    write_settings_section("dsh", model.model_dump())
    session = _session(request)
    logger.info("dsh settings updated by '%s'", getattr(user, "username", "admin"))
    return {
        "ok": True,
        "settings": model.model_dump(exclude={"secret", "agent_token"}),
        "config": _public_config(_config(session.settings), include_token=True),
    }


# ---------------------------------------------------------------------------
# Board operations (outbound commands)
# ---------------------------------------------------------------------------

@router.post("/dsh/sync")
def dsh_sync(
    request: Request,
    instance_id: Optional[str] = None,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Ask one DSH instance for every task and upsert the mirror board."""
    chosen = _resolve_instance_id(request, preferred=instance_id)
    sync = _sync_for_instance(request, chosen)
    try:
        return {"ok": True, "instance_id": chosen, **sync.sync_all()}
    except DshInstanceOffline as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DshCommandTimeout as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except HarnessSandboxError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DshError as error:
        logger.error("dsh_sync: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/dsh/tasks")
async def dsh_create_task(
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Create a DSH Session through the selected instance and mirror it."""
    data = await request.json()
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")
    name = str(data.get("name") or data.get("title") or "").strip()
    prompt = str(data.get("prompt") or data.get("content") or "")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    chosen = _resolve_instance_id(request, preferred=data.get("instance_id"))
    sync = _sync_for_instance(request, chosen)
    try:
        chat = sync.create_task(
            name=name,
            prompt=prompt,
            board=data.get("board"),
            column=data.get("column"),
            parent_id=data.get("parent_id"),
            agent_preset=data.get("agent_preset") or data.get("agentPreset"),
            model=data.get("model") or data.get("harness_model"),
            cwd=data.get("cwd"),
        )
    except DshInstanceOffline as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DshCommandTimeout as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except (HarnessModelError, HarnessSandboxError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DshError as error:
        logger.error("dsh_create_task: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {
        "ok": True,
        "instance_id": chosen,
        "chat": chat.model_dump(),
        "session_id": chat.external_id,
    }


@router.get("/dsh/tasks/{session_id}/messages")
def dsh_task_messages(
    session_id: str,
    request: Request,
    instance_id: Optional[str] = None,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Read the live message surface through a command (never persisted)."""
    chosen = _resolve_instance_id(request, preferred=instance_id, session_id=session_id)
    client = DshAgentClient(
        get_dsh_agent_registry(),
        chosen,
        timeout=max(_config(_session(request).settings).timeout, 20),
    )
    try:
        payload = client.get_task(session_id)
    except DshInstanceOffline as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DshCommandTimeout as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except DshError as error:
        status = 404 if getattr(error, "status", None) == 404 else 502
        raise HTTPException(status_code=status, detail=str(error)) from error
    return {
        "ok": True,
        "instance_id": chosen,
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
    """Send a prompt to an existing DSH session through its owning instance."""
    data = await request.json()
    text = str((data or {}).get("text") or (data or {}).get("prompt") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="text is required")
    chosen = _resolve_instance_id(
        request,
        preferred=(data or {}).get("instance_id"),
        session_id=session_id,
    )
    client = DshAgentClient(
        get_dsh_agent_registry(),
        chosen,
        timeout=max(_config(_session(request).settings).timeout, 20),
    )
    try:
        result = client.prompt(session_id, text, mode=str(data.get("mode") or "queue"))
    except DshInstanceOffline as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DshCommandTimeout as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except DshError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"ok": True, "instance_id": chosen, **(result or {})}


@router.post("/dsh/tasks/{session_id}/cancel")
def dsh_cancel_task(
    session_id: str,
    request: Request,
    instance_id: Optional[str] = None,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Cancel the active turn of one DSH session."""
    chosen = _resolve_instance_id(request, preferred=instance_id, session_id=session_id)
    client = DshAgentClient(get_dsh_agent_registry(), chosen, timeout=20)
    try:
        return {"ok": True, "instance_id": chosen, **(client.cancel(session_id) or {})}
    except DshInstanceOffline as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DshCommandTimeout as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except DshError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


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
    chosen = _resolve_instance_id(
        request,
        preferred=(data or {}).get("instance_id"),
        session_id=session_id,
    )
    client = DshAgentClient(get_dsh_agent_registry(), chosen, timeout=25)
    try:
        result = client.rename(session_id, title)
    except DshInstanceOffline as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DshCommandTimeout as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except DshError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    try:
        chat = _sync_for_instance(request, chosen).find_chat(session_id)
        if chat is not None:
            chat.name = title
            _session(request).get_chat_manager().save_chat(chat=chat, chat_only=True)
    except Exception:  # pragma: no cover - the DSH rename already succeeded
        logger.warning("dsh_rename_task: could not update mirror chat", exc_info=True)
    return {"ok": True, "instance_id": chosen, **(result or {})}


# ---------------------------------------------------------------------------
# Legacy inbound bridge (kept for backward compatibility)
# ---------------------------------------------------------------------------

@router.post("/dsh/events")
async def dsh_events(request: Request):
    """Legacy direct-bridge webhook. Prefer ``/api/dsh/agent/events``."""
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

    sync = _legacy_sync(request)
    try:
        result = sync.handle_event(payload)
    except DshError as error:
        logger.error("dsh_events: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"ok": True, **result}
