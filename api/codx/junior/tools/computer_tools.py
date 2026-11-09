"""
Computer session tools for codx-junior agents.

These tools let the LLM drive a **whole computer** shared with the user, not
just a browser:

* ``start_computer``   – create/resume a Linux desktop, Windows/macOS VM or a
                        remote VNC/SSH machine (or a browser session).
* ``computer_action``  – screenshot/OCR, mouse, keyboard, windows, apps, shell
                        commands and batches, all on the shared machine.
* ``computer_screenshot`` – capture the screen (+ OCR text) in one call.
* ``computer_status``  – kind, connection, control lease and desktop size.
* ``computer_control`` – handoff / take control / give back / pause.
* ``computer_activity`` – what the user did recently (co-driving awareness).
* ``finish_computer``  – stop (keep profile/storage) or delete the session.

The desktop vocabulary is intentionally close to the browser one so the model
does not have to learn two different interaction models; the profile explains
when to use ``snapshot`` (browser DOM) versus ``ocr``/``click_text`` (pixels).

Settings
--------
Every tool receives ``settings`` through the ``project_settings`` injection and
``chat_id`` from the running SmolAgent when its signature declares it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from codx.junior.settings import CODXJuniorSettings
from codx.junior.computer.backend import normalize_action
from codx.junior.computer.runtime import ComputerControlError
from .model import ToolResponse

logger = logging.getLogger(__name__)

COMPUTER_TOOL_SETTINGS: Dict[str, Any] = {
    "async": True,
    "is_async": True,
    "project_settings": True,
    "dual_response": True,
    "scope": "chat",
    "cache": False,
}

MAX_OCR_TEXT = 6000
MAX_OCR_WORDS = 120


def _settings_from(kwargs: Dict[str, Any]) -> CODXJuniorSettings:
    """Extract injected project settings."""
    settings = kwargs.get("settings")
    if not settings:
        raise Exception("Invalid project settings")
    return settings


def _manager(settings: CODXJuniorSettings):
    from codx.junior.browser.browser_manager import get_computer_manager
    return get_computer_manager(settings)


def _resolve(manager, session_id: Optional[str] = None, chat_id: Optional[str] = None):
    """Resolve a session by id, falling back to the chat's session."""
    session = manager.get_session(session_id) if session_id else None
    if not session and chat_id:
        session = manager.get_session_for_chat(chat_id)
    return session


def _persist(settings: CODXJuniorSettings, session, chat_id: Optional[str]) -> None:
    """Persist the session into the chat metadata (best effort)."""
    if not chat_id:
        return
    try:
        from codx.junior.chat_manager import ChatManager
        manager = _manager(settings)
        chat_manager = ChatManager(settings)
        chat = chat_manager.find_by_id(chat_id)
        if chat:
            manager.save_session_to_chat(session, chat)
            chat_manager.save_chat(chat)
    except Exception as ex:
        logger.debug("Could not persist computer session to chat %s: %s", chat_id, ex)


def _summary(session) -> str:
    """Short human/model summary of a computer session."""
    lines = [
        f"session_id={session.id}",
        f"kind={session.kind}",
        f"control={session.control}",
        f"status={session.status}",
        f"name={session.name or '(unnamed)'}",
        f"image={session.image or '(default)'}",
        *([f"library={session.library_item_name or session.library_item_id}"] if getattr(session, "library_item_id", None) else []),
        f"chats={', '.join(session.chat_ids) or '(none)'}",
        f"live_view={session.vnc_url or session.vnc_public_url or '(built-in VNC viewer)'}",
        f"desktop={session.desktop_width}x{session.desktop_height}",
    ]
    if session.vnc_host and session.control == "vnc":
        lines.append(f"vnc={session.vnc_host}:{session.vnc_port}")
    if session.ssh_host:
        lines.append(f"ssh={session.ssh_user + '@' if session.ssh_user else ''}{session.ssh_host}:{session.ssh_port}")
    if session.guest_share_path:
        lines.append(f"shared_folder={session.guest_share_path} (host: {session.downloads_path or '-'})")
    if session.shared_folders:
        lines.append("mounted_folders=" + ", ".join(
            f"{share.mount_path} (project: {share.folder or '/'})"
            for share in session.shared_folders
        ))
    capabilities = ", ".join(session.capabilities or [])
    if capabilities:
        lines.append(f"capabilities={capabilities}")
    return "\n".join(lines)


def _sharing_note(session) -> str:
    """Explain file sharing to the model."""
    if not session.shared_folders and not session.downloads_path:
        return ""
    note = ""
    if session.kind in ("windows", "macos"):
        note = (
            f"The host project is shared with the VM as '{session.guest_share_path}'. "
            f"Files saved there appear on the host at '{session.downloads_path}'.\n"
        )
    elif session.shared_folders:
        note = "The project folders are mounted at: " + ", ".join(
            share.mount_path for share in session.shared_folders
        ) + ".\n"
    if session.downloads_path:
        note += f"Downloads/files are saved in the project at '{session.downloads_path}'."
    return note.strip()


def _format_words(words: List[Dict[str, Any]], limit: int = MAX_OCR_WORDS) -> str:
    """Format OCR words with their clickable centres."""
    lines = []
    for word in (words or [])[:limit]:
        lines.append(
            f"{word.get('text')} @ ({word.get('cx')},{word.get('cy')})"
            f" conf={word.get('confidence')}"
        )
    if len(words or []) > limit:
        lines.append(f"... ({len(words) - limit} more words; use action='ocr' if needed)")
    return "\n".join(lines)


def _screenshot_response(session, result: Dict[str, Any], chat_id: Optional[str]) -> ToolResponse:
    """Build a dual response for a screenshot with OCR text."""
    text = (result.get("text") or "").strip()
    words = result.get("words") or []
    dimensions = f"{result.get('width')}x{result.get('height')}"
    image = result.get("image")
    user = (
        f"📸 Screen of **{session.kind_label}** `{session.id[:8]}` ({dimensions}):\n\n"
        f"![screen]({image})"
    )
    llm = (
        f"Screenshot captured for session {session.id} ({session.kind}), "
        f"desktop {dimensions}.\n"
        f"Visible text (OCR):\n{text[:MAX_OCR_TEXT] or '(no text detected)'}\n"
    )
    if words:
        llm += (
            "\nClickable OCR words (text @ centre coordinates):\n"
            + _format_words(words)
            + "\nUse computer_action(action='click_text', text='...') to click a label."
        )
    return ToolResponse(user_response=user, llm_response=llm)


# ---------------------------------------------------------------------------
# start_computer
# ---------------------------------------------------------------------------
async def start_computer(
    name: str = None,
    kind: str = "linux",
    os_version: str = None,
    chat_id: str = None,
    description: str = None,
    initial_url: str = None,
    share_project: bool = None,
    share_folders: List[str] = None,
    downloads_folder: str = None,
    image: str = None,
    image_provider: str = None,
    library_item_id: str = None,
    vnc_host: str = None,
    vnc_port: int = 5900,
    vnc_password: str = None,
    vnc_public_url: str = None,
    ssh_host: str = None,
    ssh_port: int = 22,
    ssh_user: str = None,
    ssh_key_path: str = None,
    ssh_password: str = None,
    **kwargs,
) -> ToolResponse:
    """
    Start (or resume) a computer shared with the user.

    Args:
        name: Human-readable session name.
        kind: ``linux`` (desktop container), ``windows``/``macos`` (QEMU VM),
            ``remote`` (existing VNC/SSH machine) or ``browser``.
        os_version: VM release (Windows '11', macOS '15'); ignored by Linux.
        chat_id: Injected by SmolAgent; links the session to the chat.
        description: Optional free-form description.
        initial_url: Browser start URL (browser kind only).
        share_project: Mount the project into the machine (container kinds).
        share_folders: Project folders to mount (Linux; VMs get the project root).
        downloads_folder: Project folder for files saved by the machine.
        image: Docker image override (advanced).
        vnc_host/vnc_port/vnc_password: Existing VNC endpoint (remote kind).
        vnc_public_url: Viewer URL supplied by the user (noVNC).
        ssh_host/ssh_port/ssh_user/ssh_key_path/ssh_password: Optional shell
            access for remote machines (needed for run_command).
        **kwargs: Injected ``settings``.
    """
    from codx.junior.browser.model import normalize_kind

    settings = _settings_from(kwargs)
    manager = _manager(settings)
    try:
        kind = normalize_kind(kind, default="linux")
    except ValueError as ex:
        return ToolResponse(user_response=f"❌ {ex}", llm_response=str(ex))
    session_name = (name or "").strip() or (
        f"{kind.title()} {datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    )

    try:
        existing = manager.get_session_for_chat(chat_id) if chat_id else None
        if existing and existing.kind == kind:
            if existing.status != "running":
                try:
                    existing = await manager.restart_session(existing.id)
                except Exception as ex:
                    logger.warning("Could not restart %s session %s: %s", kind, existing.id, ex)
            if existing and existing.status == "running":
                existing_live = existing.vnc_url or existing.vnc_public_url
                return ToolResponse(
                    user_response=(
                        f"♻️ {existing.kind_label} session already running.\n"
                        + (f"[Open the live view]({existing_live})\n" if existing_live else "")
                        + f"```\n{_summary(existing)}\n```"
                    ),
                    llm_response=(
                        f"A {existing.kind} session is already running for this chat. "
                        f"Use session_id {existing.id} with computer_action. "
                        f"{_sharing_note(existing)}"
                    ),
                )

        session = await asyncio.to_thread(
            manager.create_session,
            name=session_name,
            chat_id=chat_id,
            initial_url=initial_url,
            description=description,
            share_project=share_project,
            share_folders=share_folders,
            readonly=None,
            downloads_folder=downloads_folder,
            downloads_mount=None,
            kind=kind,
            os_version=os_version,
            image=image,
            image_provider=image_provider,
            library_item_id=library_item_id,
            vnc_host=vnc_host,
            vnc_port=vnc_port,
            vnc_password=vnc_password,
            vnc_public_url=vnc_public_url,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
            ssh_key_path=ssh_key_path,
            ssh_password=ssh_password,
        )
        _persist(settings, session, chat_id)
        live = session.vnc_url or session.vnc_public_url
        llm = (
            f"{session.kind_label} session '{session.name}' started. "
            f"session_id: {session.id}. Live view: {live}. "
            f"Control channel: {session.control}. "
            "Use computer_action with this session_id; start with action='screenshot' "
            "to see the screen (it returns OCR text too). Call finish_computer when done. "
            + (
                "The VM may still be booting/installing Windows/macOS: take a "
                "screenshot and wait (computer_action action='wait') before acting. "
                if session.kind in ("windows", "macos") else ""
            )
            + f"{_sharing_note(session)}"
        )
        live_line = (
            f"[Open the live view]({live})"
            if live else
            "Open the session panel in the UI for the live desktop view."
        )
        return ToolResponse(
            user_response=(
                f"✅ {session.kind_label} session '{session.name}' ready.\n"
                f"{live_line}\n"
                f"```\n{_summary(session)}\n```"
            ),
            llm_response=llm,
        )
    except Exception as ex:
        logger.exception("start_computer failed: %s", ex)
        return ToolResponse(
            user_response=f"❌ Failed to start {kind} session: {ex}",
            llm_response=(
                f"Failed to start {kind} session: {ex}. "
                "Windows/macOS VMs need KVM (/dev/kvm) on the Docker host; "
                "use kind='remote' with vnc_host for an existing machine."
            ),
        )


# ---------------------------------------------------------------------------
# computer_action
# ---------------------------------------------------------------------------
async def save_computer(
    session_id: str,
    name: str = None,
    description: str = None,
    include_profile: bool = False,
    **kwargs,
) -> ToolResponse:
    """Save a running Linux/Kasmweb desktop into the project computer library."""
    from codx.junior.computer.library import save_session_to_library

    settings = _settings_from(kwargs)
    manager = _manager(settings)
    session = manager.get_session(session_id)
    if not session:
        return ToolResponse(
            user_response="❌ Computer session not found",
            llm_response=f"Computer session not found: {session_id}",
        )
    username = getattr(getattr(settings, "user", None), "username", None)
    try:
        item = await save_session_to_library(
            manager,
            session,
            name=name,
            description=description,
            include_profile=bool(include_profile),
            created_by=username,
        )
    except Exception as ex:
        return ToolResponse(
            user_response=f"❌ Could not save the computer: {ex}",
            llm_response=f"Could not save computer: {ex}",
        )
    size = item.image_size_bytes or 0
    return ToolResponse(
        user_response=(
            f"💾 Saved **{item.name}** to the computer library "
            f"({size / (1024 ** 3):.1f} GB image). Other project users can now start it "
            f"from the library."
        ),
        llm_response=(
            f"Saved computer '{item.name}' (id={item.id}, image={item.image}, "
            f"provider={item.provider}, include_profile={item.include_profile})"
        ),
    )


async def computer_action(
    action: str,
    session_id: str = None,
    chat_id: str = None,
    url: str = None,
    selector: str = None,
    ref: str = None,
    value: str = None,
    script: str = None,
    x: int = None,
    y: int = None,
    x2: int = None,
    y2: int = None,
    text: str = None,
    key: str = None,
    combo: str = None,
    button: str = "left",
    clicks: int = 1,
    amount: int = 3,
    direction: str = "down",
    seconds: float = 1,
    command: str = None,
    app: str = None,
    window_id: str = None,
    title: str = None,
    timeout: float = 60,
    include_text: bool = True,
    max_width: int = 1600,
    index: int = 0,
    double: bool = False,
    steps: List[Dict[str, Any]] = None,
    variables: Dict[str, Any] = None,
    **kwargs,
) -> ToolResponse:
    """
    Perform an action on the shared computer.

    Use ``screenshot`` (or ``ocr``) first: it returns the visible text and
    clickable word coordinates. Prefer ``click_text`` for labels/buttons;
    use ``click`` with coordinates only when the target is not text.

    Args:
        action: screenshot, ocr, click, double_click, right_click, click_text,
            move, drag, scroll, type, key, hotkey, wait, windows,
            active_window, focus_window, close_window, open_app, list_apps,
            run_command, screen_size, batch.
        session_id: Session id from ``start_computer`` (or ``chat_id``).
        chat_id: Resolve the chat's session instead of passing an id.
        url/selector/ref/value/script: Browser-page parameters when the session
            kind is ``browser`` (delegated to ``browse_action``).
        x/y: Display coordinates in pixels (not the rendered screenshot size).
        x2/y2: Drag end coordinates.
        text: Text to type, or text to find for ``click_text``.
        key/combo: Key or combo (``ctrl+shift+t``, ``Return``, ``super``).
        button: Mouse button (left/middle/right).
        clicks: Click count (1-3).
        amount/direction: Scroll steps and direction.
        seconds: Wait duration.
        command: Shell command for ``run_command`` (Linux container or SSH).
        app: Application name for ``open_app``.
        window_id/title: Window target for focus/close.
        timeout: Command timeout in seconds.
        include_text: Run OCR on screenshots (default true).
        max_width: Returned screenshot width in pixels.
        index: Match index for ``click_text``.
        double: Double-click the text match.
        steps: Steps for ``batch`` (list of {action, ...}).
        variables: ``{{name}}`` values for batch steps.
        **kwargs: Injected ``settings``.
    """
    settings = _settings_from(kwargs)
    manager = _manager(settings)
    session = _resolve(manager, session_id=session_id, chat_id=chat_id)
    if not session:
        return ToolResponse(
            user_response="❌ No computer session found. Call `start_computer` first.",
            llm_response="No computer session available. Start one with start_computer.",
        )
    if session.status != "running":
        try:
            session = await manager.restart_session(session.id)
        except Exception as ex:
            return ToolResponse(
                user_response=f"❌ Session is not running and could not be restarted: {ex}",
                llm_response=f"Session {session.id} is not running (status: {session.status}) and restart failed: {ex}",
            )

    action = normalize_action(action)
    if session.kind == "browser":
        # Reuse the browser tool for DOM-aware actions.  Import lazily to
        # avoid a tools/__init__ import cycle.
        from .browser_tools import browse_action
        return await browse_action(
            action=action,
            session_id=session.id,
            chat_id=chat_id,
            url=url,
            selector=selector,
            ref=ref,
            value=value,
            script=script,
            text=text,
            key=key or combo,
            index=index,
            steps=steps,
            variables=variables,
            **kwargs,
        )

    params: Dict[str, Any] = {}
    for name, value in {
        "x": x, "y": y, "x2": x2, "y2": y2, "text": text, "key": key,
        "combo": combo, "button": button, "clicks": clicks, "amount": amount,
        "direction": direction, "seconds": seconds, "command": command,
        "app": app, "window_id": window_id, "title": title, "timeout": timeout,
        "include_text": include_text, "max_width": max_width, "index": index,
        "double": double,
    }.items():
        if value is not None:
            params[name] = value
    if action == "batch":
        params = {"steps": steps or [], "variables": variables or {}}

    started_at = time.monotonic()
    try:
        runtime = await manager.get_runtime(session)
        if action == "batch":
            result = await runtime.run_steps(
                params["steps"], params["variables"], force=False
            )
        else:
            result = await runtime.run(action, force=False, user_wait=3, **params)
        session = getattr(runtime, "session", None) or session
    except ComputerControlError as ex:
        return ToolResponse(
            user_response=f"✋ The AI is paused: {ex}",
            llm_response=(
                f"Action '{action}' was not executed: {ex} "
                "Call computer_control(action='status') and wait for the user to "
                "give control back; never type over the user."
            ),
        )
    except Exception as ex:
        logger.exception("computer_action '%s' failed: %s", action, ex)
        manager.log_activity(
            session, actor="ai", action=action, chat_id=chat_id, params=params,
            success=False, error=str(ex),
            duration_ms=(time.monotonic() - started_at) * 1000,
        )
        return ToolResponse(
            user_response=f"❌ {action} failed: {ex}",
            llm_response=(
                f"Computer action '{action}' failed on session {session.id}: {ex}. "
                "Take a screenshot to see the current state before retrying."
            ),
        )

    if action == "screenshot" and isinstance(result, dict):
        return _screenshot_response(session, result, chat_id)

    if action == "ocr" and isinstance(result, dict):
        text = (result.get("text") or "").strip()
        words = result.get("words") or []
        return ToolResponse(
            user_response=(
                f"🔎 OCR of `{session.id[:8]}` ({result.get('width')}x{result.get('height')}):\n"
                f"```\n{text[:MAX_OCR_TEXT] or '(no text detected)'}\n```"
            ),
            llm_response=(
                f"OCR text for session {session.id}:\n{text[:MAX_OCR_TEXT] or '(no text detected)'}\n"
                + (f"\nClickable words:\n{_format_words(words)}" if words else "")
            ),
        )

    if action == "run_command" and isinstance(result, dict):
        stdout = (result.get("stdout") or "")[:5000]
        stderr = (result.get("stderr") or "")[:2000]
        exit_code = result.get("exit_code")
        llm = f"Command exited with {exit_code}.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        return ToolResponse(
            user_response=(
                f"💻 Command finished (exit {exit_code}) on {session.kind_label} "
                f"`{session.id[:8]}`:\n```\n{stdout or stderr or '(no output)'}\n```"
            ),
            llm_response=llm,
        )

    if action == "windows" and isinstance(result, dict):
        windows = result.get("windows") or []
        lines = "\n".join(
            f"- {item.get('id')}: {item.get('title')} "
            f"({item.get('x')},{item.get('y')} {item.get('width')}x{item.get('height')})"
            + (" [active]" if item.get("active") else "")
            for item in windows
        )
        return ToolResponse(
            user_response=f"🪟 {len(windows)} window(s) on session {session.id[:8]}:\n```\n{lines}\n```",
            llm_response=f"Windows on session {session.id}:\n{lines or '(none)'}",
        )

    summary = json.dumps(result, ensure_ascii=False, default=str)[:3000] if result is not None else ""
    return ToolResponse(
        user_response=f"✅ {action} completed on {session.kind_label} `{session.id[:8]}`.",
        llm_response=(
            f"'{action}' completed on computer session {session.id}. "
            f"Result: {summary}"
        ),
    )


# ---------------------------------------------------------------------------
# Convenience tools
# ---------------------------------------------------------------------------
async def computer_screenshot(
    session_id: str = None,
    chat_id: str = None,
    include_text: bool = True,
    max_width: int = 1600,
    **kwargs,
) -> ToolResponse:
    """Capture the shared desktop and return the image plus OCR text."""
    return await computer_action(
        action="screenshot",
        session_id=session_id,
        chat_id=chat_id,
        include_text=include_text,
        max_width=max_width,
        **kwargs,
    )


async def computer_status(
    session_id: str = None,
    chat_id: str = None,
    **kwargs,
) -> ToolResponse:
    """Report the shared computer's kind, connection and control lease."""
    settings = _settings_from(kwargs)
    manager = _manager(settings)

    if not session_id and not chat_id:
        sessions = manager.list_sessions()
        lines = [
            f"- {item.id[:8]} [{item.kind}/{item.status}] {item.name or '(unnamed)'}"
            for item in sessions
        ]
        text = "\n".join(lines) or "(no computer sessions)"
        return ToolResponse(
            user_response=f"🖥️ Computer sessions:\n```\n{text}\n```",
            llm_response=f"Computer sessions for this project:\n{text}",
        )

    session = _resolve(manager, session_id=session_id, chat_id=chat_id)
    if not session:
        return ToolResponse(
            user_response="❌ No computer session found.",
            llm_response="No computer session available. Start one with start_computer.",
        )
    state = {
        "session_id": session.id,
        "kind": session.kind,
        "status": session.status,
        "control": session.control,
        "controller": session.controller,
        "handoff_reason": session.handoff_reason,
        "user_active_until": session.user_active_until,
        "desktop": f"{session.desktop_width}x{session.desktop_height}",
        "live_view": session.vnc_url or session.vnc_public_url,
        "vnc": (
            f"{session.vnc_host}:{session.vnc_port}"
            if session.vnc_host and session.control == "vnc" else None
        ),
        "ssh": f"{session.ssh_user or ''}@{session.ssh_host}:{session.ssh_port}" if session.ssh_host else None,
        "capabilities": session.capabilities,
        "last_action": session.last_action,
        "last_action_at": session.last_action_at,
        "error": session.error,
    }
    state = {key: value for key, value in state.items() if value not in (None, "", [])}
    text = "\n".join(f"{key}: {value}" for key, value in state.items())
    return ToolResponse(
        user_response=f"🖥️ Computer status `{session.id[:8]}`:\n```\n{text}\n```",
        llm_response=f"Computer session {session.id}:\n{text}",
    )


async def computer_control(
    action: str,
    reason: str = None,
    session_id: str = None,
    chat_id: str = None,
    **kwargs,
) -> ToolResponse:
    """Manage the human/AI control lease of the shared computer.

    Actions: ``status``, ``handoff`` (pause the AI for login/MFA/approval),
    ``take_control``, ``give_back``, ``pause``.
    """
    settings = _settings_from(kwargs)
    manager = _manager(settings)
    session = _resolve(manager, session_id=session_id, chat_id=chat_id)
    if not session:
        return ToolResponse(
            user_response="❌ No computer session found.",
            llm_response="No computer session available. Start one with start_computer.",
        )
    action = (action or "status").strip().lower()
    if action in ("status", "info"):
        state = (
            f"controller={session.controller}\n"
            f"user_active={session.user_is_active()}\n"
            f"handoff_reason={session.handoff_reason or '-'}\n"
            f"last_user_event={session.last_user_event_at or '-'}"
        )
        return ToolResponse(
            user_response=f"ℹ️ Control of `{session.id[:8]}`:\n```\n{state}\n```",
            llm_response=f"Computer control state for session {session.id}:\n{state}",
        )
    if action in ("handoff", "request_handoff", "request"):
        session.request_handoff(reason or "The user needs to take over", chat_id=chat_id)
        message = "The AI paused; the user has been asked to take control."
    elif action in ("take_control", "take"):
        session.set_controller("user", chat_id=chat_id, reason=reason)
        session.mark_user_active(seconds=600)
        message = "The user now controls the computer."
    elif action in ("give_back", "release", "resume"):
        session.set_controller("ai", chat_id=chat_id)
        message = "Control returned to the AI."
    elif action in ("pause", "stop"):
        session.set_controller("none", chat_id=chat_id, reason=reason)
        message = "The computer is paused; neither side may act."
    else:
        return ToolResponse(
            user_response=f"❌ Unknown control action '{action}'.",
            llm_response="Unknown control action. Use status, handoff, take_control, give_back or pause.",
        )
    manager.save_session(session)
    manager.log_activity(
        session, actor="ai", action=f"control:{action}", chat_id=chat_id,
        params={"reason": reason},
    )
    try:
        from codx.junior.browser import events as browser_events
        browser_events.broadcast_control(session)
    except Exception:
        pass
    return ToolResponse(
        user_response=f"🤝 {message}",
        llm_response=f"{message} Session {session.id}, controller={session.controller}.",
    )


async def computer_activity(
    session_id: str = None,
    chat_id: str = None,
    limit: int = 30,
    actor: str = None,
    since: str = None,
    **kwargs,
) -> ToolResponse:
    """Return recent user/AI actions on the shared computer."""
    from .browser_tools import browser_activity
    return await browser_activity(
        session_id=session_id,
        chat_id=chat_id,
        limit=limit,
        actor=actor,
        since=since,
        **kwargs,
    )


async def finish_computer(
    session_id: str = None,
    chat_id: str = None,
    delete: bool = False,
    **kwargs,
) -> ToolResponse:
    """Stop (default, keeps profile/storage) or delete the computer session."""
    from .browser_tools import finish_session
    response = await finish_session(
        session_id=session_id, chat_id=chat_id, delete=delete, **kwargs
    )
    response.user_response = response.user_response.replace("Browser session", "Computer session")
    response.llm_response = response.llm_response.replace("Browser session", "Computer session")
    return response


# ---------------------------------------------------------------------------
# Tool JSON schemas
# ---------------------------------------------------------------------------
START_COMPUTER_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "start_computer",
        "description": (
            "Start (or resume) a whole computer shared with the user. kind='linux' opens a "
            "Linux desktop container, 'windows'/'macos' a QEMU VM (needs KVM on the Docker "
            "host), 'remote' an existing machine reachable over VNC (and optionally SSH), "
            "and 'browser' a Chromium session. Returns session_id and the live view; use "
            "computer_action afterwards. Project files are mounted into containers; VMs see "
            "the project as a shared folder. Use this for tasks a browser cannot do: mobile "
            "app builds on macOS, installing/using desktop programs, OS settings, terminals."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Human-readable session name."},
                "kind": {
                    "type": "string",
                    "enum": ["linux", "windows", "macos", "remote", "browser"],
                    "description": "Machine kind (default linux).",
                },
                "os_version": {
                    "type": "string",
                    "description": "VM release: Windows '11'/'10', macOS '15'/'14'. Ignored by Linux.",
                },
                "image": {
                    "type": "string",
                    "description": (
                        "Docker image, from the image library: e.g. "
                        "lscr.io/linuxserver/webtop:ubuntu-xfce or "
                        "kasmweb/core-ubuntu-jammy:1.18.0. Omit for the default."
                    ),
                },
                "image_provider": {
                    "type": "string",
                    "enum": ["linuxserver", "kasmweb", "custom"],
                    "description": "Image provider (inferred from image when omitted).",
                },
                "library_item_id": {
                    "type": "string",
                    "description": "Start from a saved computer in the project library.",
                },
                "description": {"type": "string", "description": "Optional description."},
                "initial_url": {"type": "string", "description": "Browser start URL (browser kind)."},
                "share_project": {
                    "type": "boolean",
                    "description": "Mount the project into the machine (container kinds).",
                },
                "share_folders": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Project folders to mount (Linux desktop; VMs get the project root).",
                },
                "downloads_folder": {
                    "type": "string",
                    "description": "Project folder receiving files saved by the machine.",
                },
                "vnc_host": {
                    "type": "string",
                    "description": "VNC host for kind='remote' (e.g. 192.168.1.20 or mac-mini.local).",
                },
                "vnc_port": {"type": "integer", "description": "VNC port (default 5900)."},
                "vnc_password": {"type": "string", "description": "VNC password (never logged)."},
                "vnc_public_url": {
                    "type": "string",
                    "description": "Optional noVNC/other viewer URL supplied by the user.",
                },
                "ssh_host": {"type": "string", "description": "SSH host for shell commands."},
                "ssh_port": {"type": "integer", "description": "SSH port (default 22)."},
                "ssh_user": {"type": "string", "description": "SSH username."},
                "ssh_key_path": {"type": "string", "description": "Host path of the SSH private key."},
                "ssh_password": {"type": "string", "description": "SSH password (never logged)."},
            },
            "required": [],
        },
    },
}

SAVE_COMPUTER_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "save_computer",
        "description": (
            "Save the current Linux/Kasmweb desktop as a reusable computer in the "
            "project library. Commits installed packages and container changes; "
            "optionally archives the home/profile (which may contain secrets). "
            "Only use this when the user explicitly asks to save the computer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session id from start_computer."},
                "name": {"type": "string", "description": "Name for the saved computer."},
                "description": {"type": "string", "description": "What is installed/configured."},
                "include_profile": {
                    "type": "boolean",
                    "description": "Archive the bind-mounted home/profile (may contain logins/keys).",
                },
            },
            "required": ["session_id"],
        },
    },
}

COMPUTER_ACTION_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "computer_action",
        "description": (
            "Drive the shared computer. Start with action='screenshot' (returns OCR text and "
            "word coordinates) or 'ocr'. Prefer click_text to click labels/buttons; use click "
            "with display-pixel coordinates only when there is no text. Actions: screenshot, "
            "ocr, click, double_click, right_click, click_text, move, drag, scroll, type, key, "
            "hotkey, wait, windows, active_window, focus_window, close_window, open_app, "
            "list_apps, run_command, screen_size, batch. On browser-kind sessions, page "
            "actions (navigate, fill, execute, text, links, snapshot, tabs...) are delegated "
            "to the browser tools. Coordinates are display pixels, not the rendered "
            "screenshot size. Use batch for multi-step flows."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "screenshot", "ocr", "click", "double_click", "right_click",
                        "click_text", "move", "drag", "scroll", "type", "key",
                        "hotkey", "wait", "windows", "active_window",
                        "focus_window", "close_window", "open_app", "list_apps",
                        "run_command", "screen_size", "batch",
                        # Browser-kind page actions (delegated to browse_action)
                        "navigate", "fill", "execute", "text", "links", "snapshot",
                        "back", "forward", "refresh", "press", "select", "hover",
                        "tabs", "new_tab", "switch_tab", "close_tab",
                    ],
                    "description": "Action to perform.",
                },
                "session_id": {"type": "string", "description": "Session id from start_computer."},
                "url": {"type": "string", "description": "Browser page URL (browser kind)."},
                "selector": {"type": "string", "description": "Browser CSS selector (browser kind)."},
                "ref": {"type": "string", "description": "Browser element ref from a snapshot."},
                "value": {"type": "string", "description": "Browser fill/select value."},
                "script": {"type": "string", "description": "Browser JavaScript to execute."},
                "x": {"type": "integer", "description": "Display X coordinate."},
                "y": {"type": "integer", "description": "Display Y coordinate."},
                "x2": {"type": "integer", "description": "Drag end X."},
                "y2": {"type": "integer", "description": "Drag end Y."},
                "text": {"type": "string", "description": "Text to type or to click (click_text)."},
                "key": {"type": "string", "description": "Key or combo (Return, ctrl+c, super+space)."},
                "combo": {"type": "string", "description": "Alias of key for combinations."},
                "button": {"type": "string", "enum": ["left", "middle", "right"]},
                "clicks": {"type": "integer", "description": "Click count (1-3)."},
                "amount": {"type": "integer", "description": "Scroll steps."},
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "seconds": {"type": "number", "description": "Wait duration."},
                "command": {"type": "string", "description": "Shell command for run_command."},
                "app": {"type": "string", "description": "Application name for open_app."},
                "window_id": {"type": "string", "description": "Window id."},
                "title": {"type": "string", "description": "Window title (partial)."},
                "timeout": {"type": "number", "description": "Command timeout seconds."},
                "include_text": {"type": "boolean", "description": "Run OCR on screenshots."},
                "max_width": {"type": "integer", "description": "Returned screenshot width."},
                "index": {"type": "integer", "description": "Match index for click_text."},
                "double": {"type": "boolean", "description": "Double-click the text match."},
                "steps": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Batch steps: [{action, x, y, text...}].",
                },
                "variables": {"type": "object", "description": "{{name}} values for batch."},
            },
            "required": ["action"],
        },
    },
}

COMPUTER_SCREENSHOT_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "computer_screenshot",
        "description": (
            "Capture the shared computer screen. Returns the image (shown to the user) and "
            "OCR text with clickable word centres for the model. Use it before acting and "
            "after an action whose result is uncertain."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session id from start_computer."},
                "include_text": {"type": "boolean", "description": "Run OCR (default true)."},
                "max_width": {"type": "integer", "description": "Returned image width (default 1600)."},
            },
        },
    },
}

COMPUTER_STATUS_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "computer_status",
        "description": (
            "Return the shared computer's kind, connection, control lease and desktop size. "
            "Omit session_id to list all computer sessions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session id (optional)."},
            },
        },
    },
}

COMPUTER_CONTROL_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "computer_control",
        "description": (
            "Manage who drives the shared computer: status, handoff (pause the AI for "
            "login/MFA/payment approval), take_control, give_back, pause. Never act while the "
            "user controls the computer."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "handoff", "take_control", "give_back", "pause"],
                },
                "reason": {"type": "string", "description": "Why the AI hands control over."},
                "session_id": {"type": "string", "description": "Session id."},
            },
            "required": ["action"],
        },
    },
}

COMPUTER_ACTIVITY_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "computer_activity",
        "description": (
            "Return recent user/AI actions on the shared computer. Call it after a pause to "
            "see what the user did in the live view."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session id."},
                "limit": {"type": "integer", "description": "Max entries (default 30)."},
                "actor": {"type": "string", "enum": ["user", "ai", "system"]},
                "since": {"type": "string", "description": "ISO timestamp filter."},
            },
        },
    },
}

FINISH_COMPUTER_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "finish_computer",
        "description": (
            "Finish a computer session. Stopping (delete=false) keeps the profile/VM storage "
            "for a later restart; deleting removes the session and its data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session id."},
                "delete": {"type": "boolean", "description": "Delete the session and its data."},
            },
        },
    },
}
