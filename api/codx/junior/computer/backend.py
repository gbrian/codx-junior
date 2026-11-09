"""
Control backends for computer sessions.

Two backends implement the same small action vocabulary:

* :class:`DockerExecBackend` — Linux desktop containers (LinuxServer webtop).
  The AI runs the bundled X11 agent through ``docker exec``; input uses
  ``xdotool`` and screenshots use Pillow over X11.
* :class:`VncBackend` — Windows/macOS VM containers and remote machines.  It
  speaks RFB directly (see :mod:`codx.junior.computer.vnc`), so the AI sees the
  same framebuffer the human sees in the noVNC viewer and injects pointer/key
  events into the same session.

Both expose ``run(action, **params)`` and enrich screenshots with OCR text and
word boxes (see :mod:`codx.junior.computer.ocr`), which is what lets a model act
on a GUI without vision.

Both also accept the ``resize`` action (see
:mod:`codx.junior.computer.resize`): VNC desktops through ``SetDesktopSize`` and
Linux containers through ``xrandr``, so the live view can fit the desktop to the
viewer instead of being letterboxed.  Resizing is best effort: the result always
reports ``supported``/``applied`` and the size actually in use.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import subprocess
import time
from typing import Any, Dict, List, Optional

from codx.junior.computer import ocr
from codx.junior.computer.resize import fit_resolution, parse_resolution, xrandr_resize_script
from codx.junior.computer.ssh import SSHError, SSHRunner
from codx.junior.computer.vnc import KEYSYMS, RFBClient, RFBError

logger = logging.getLogger(__name__)

#: Actions that only read the screen and must not pause the AI.
READ_ONLY_ACTIONS = {
    "screenshot",
    "ocr",
    "read_screen",
    "screen_size",
    "windows",
    "list_windows",
    "active_window",
    "list_apps",
    "mouse_position",
    "clipboard_get",
    "ping",
    "status",
}

#: Aliases accepted from prompts and the UI.
ACTION_ALIASES = {
    "left_click": "click",
    "doubleclick": "double_click",
    "double-click": "double_click",
    "rightclick": "right_click",
    "right-click": "right_click",
    "typewrite": "type",
    "type_text": "type",
    "keypress": "key",
    "press": "key",
    "read": "ocr",
    "read_screen": "ocr",
    "screen": "screenshot",
    "screen_shot": "screenshot",
    "list_windows": "windows",
    "run": "run_command",
    "shell": "run_command",
    "execute": "run_command",
    "launch": "open_app",
    "set_resolution": "resize",
    "set_screen_size": "resize",
    "set_desktop_size": "resize",
    "resize_desktop": "resize",
    "resolution": "resize",
}

DEFAULT_MAX_WIDTH = 1600
DEFAULT_ACTION_TIMEOUT = 120


class DesktopControlError(RuntimeError):
    """An action could not be executed on the desktop."""


class UnsupportedComputerActionError(DesktopControlError):
    """The backend/session cannot perform this action."""


def normalize_action(action: str) -> str:
    """Normalize an action name (aliases, case, whitespace)."""
    value = str(action or "").strip().lower().replace(" ", "_")
    return ACTION_ALIASES.get(value, value)


def _resize_size(params: Dict[str, Any]) -> tuple[int, int]:
    """
    Resolve the requested desktop size from action parameters.

    Args:
        params: Action parameters (``width``/``height`` or ``resolution``).

    Returns:
        tuple[int, int]: Even, in-range target size.

    Raises:
        DesktopControlError: When the size is missing or not a number.
    """
    parsed = parse_resolution(params.get("resolution"))
    width = parsed[0] if parsed else params.get("width")
    height = parsed[1] if parsed else params.get("height")
    if not width or not height:
        raise DesktopControlError(
            "resize requires width and height (or resolution='1920x1080')"
        )
    try:
        return fit_resolution(width, height)
    except ValueError as ex:
        raise DesktopControlError(str(ex)) from ex


def _summarize_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """Keep batch results small (never echo whole screen data)."""
    result = dict(step)
    if "image" in result:
        result["image"] = "(screenshot captured)"
    return result


def screenshot_payload(
    png: bytes,
    width: int,
    height: int,
    include_text: bool = True,
    max_width: int = DEFAULT_MAX_WIDTH,
    min_confidence: float = ocr.DEFAULT_MIN_CONFIDENCE,
) -> Dict[str, Any]:
    """
    Build the common screenshot response: resized data URI + OCR text/words.

    Args:
        png: Original PNG bytes (full resolution for OCR).
        width: Original desktop width.
        height: Original desktop height.
        include_text: Run OCR and include ``text``/``words``.
        max_width: Resize the returned image to at most this width.
        min_confidence: OCR word confidence threshold.
    """
    result: Dict[str, Any] = {"width": width, "height": height}
    data_uri = None
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(png))
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")
        image_width, image_height = image.size
        target_width = max(320, int(max_width or DEFAULT_MAX_WIDTH))
        if image_width > target_width:
            ratio = target_width / float(image_width)
            image = image.resize(
                (target_width, max(1, int(round(image_height * ratio)))),
                Image.LANCZOS,
            )
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        data_uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
        result["image_width"], result["image_height"] = image.size
    except Exception as ex:
        logger.warning("Could not resize screenshot: %s", ex)
        data_uri = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
        result["image_width"], result["image_height"] = width, height
    result["image"] = data_uri
    result["mime"] = "image/png"
    if include_text:
        text_result = ocr.extract_text(png, min_confidence=min_confidence)
        result["text"] = text_result.get("text", "")
        result["words"] = text_result.get("words", [])
        result["ocr_available"] = text_result.get("available", False)
        if text_result.get("error"):
            result["ocr_error"] = text_result["error"]
    return result


def _find_text(png: bytes, text: str, index: int = 0, min_confidence: float = 25.0) -> Optional[Dict[str, Any]]:
    """OCR *png* and return the matching word box (with full-image coordinates)."""
    text_result = ocr.extract_text(png, min_confidence=min_confidence)
    return ocr.find_text(text_result.get("words") or [], text, index=index)


class BaseComputerBackend:
    """Common action plumbing (batch, text clicks, OCR screenshots)."""

    kind = "computer"

    def __init__(self, session):
        self.session = session

    # -- to implement ------------------------------------------------------
    async def capture_png(self) -> tuple[bytes, int, int]:
        """Return ``(png_bytes, width, height)`` for the current desktop."""
        raise NotImplementedError

    async def execute(self, action: str, **params) -> Dict[str, Any]:
        """Execute one primitive action."""
        raise NotImplementedError

    async def close(self) -> None:
        """Release connections/resources."""

    def resize_support(self) -> Dict[str, Any]:
        """
        Describe whether/how this backend can change the desktop size.

        Returns:
            Dict[str, Any]: ``supported`` plus the ``mode`` (``rfb``, ``xrandr``
            or ``none``) so the UI knows whether to offer the resize control or
            just scale the framebuffer.
        """
        return {"supported": False, "mode": "none"}

    async def health(self) -> Dict[str, Any]:
        """Check the connection and return the desktop size."""
        png, width, height = await self.capture_png()
        return {
            "width": width,
            "height": height,
            "bytes": len(png),
            "resize": self.resize_support(),
        }

    # -- shared implementation --------------------------------------------
    async def screenshot(self, include_text: bool = True, max_width: int = DEFAULT_MAX_WIDTH, **_: Any) -> Dict[str, Any]:
        """Capture the desktop and return image + OCR text/words."""
        png, width, height = await self.capture_png()
        return screenshot_payload(
            png,
            width,
            height,
            include_text=bool(include_text),
            max_width=int(max_width or DEFAULT_MAX_WIDTH),
        )

    async def click_text(
        self,
        text: str,
        index: int = 0,
        button: str = "left",
        double: bool = False,
        **params: Any,
    ) -> Dict[str, Any]:
        """Click the centre of the *index*-th OCR match for *text*."""
        if not str(text or "").strip():
            raise DesktopControlError("click_text requires text")
        png, width, height = await self.capture_png()
        match = _find_text(png, text, index=index)
        if not match:
            raise DesktopControlError(
                f"Text '{text}' was not found on screen. Take a screenshot/ocr first."
            )
        result = await self.execute(
            "click",
            x=match["cx"],
            y=match["cy"],
            button=button,
            clicks=2 if double else 1,
        )
        return {**result, "matched": match}

    async def run(self, action: str, **params: Any) -> Dict[str, Any]:
        """Execute one action, expanding batch/click_text/screenshot helpers."""
        action = normalize_action(action)
        if action == "batch":
            steps = params.get("steps") or []
            return await self.run_batch(steps)
        if action == "click_text":
            return await self.click_text(**params)
        if action == "screenshot":
            return await self.screenshot(
                include_text=params.get("include_text", True),
                max_width=params.get("max_width", DEFAULT_MAX_WIDTH),
            )
        if action == "ocr":
            result = await self.screenshot(include_text=True, max_width=720)
            # OCR callers do not need the image payload.
            result.pop("image", None)
            return result
        if action == "status":
            status = await self.health()
            status.update({
                "kind": self.session.kind,
                "control": self.session.control,
                "name": self.session.name,
            })
            return status
        action_params = dict(params)
        action_params.pop("steps", None)
        return await self.execute(action, **action_params)

    async def run_batch(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run an ordered list of steps on one connection."""
        results = []
        for index, raw_step in enumerate(steps or []):
            step = dict(raw_step or {})
            action = normalize_action(step.pop("action", step.pop("type", "")))
            if not action:
                return {
                    "success": False,
                    "step": index,
                    "error": "Step is missing an action",
                    "results": [_summarize_step(item) for item in results],
                }
            target = step.pop("target", None)
            if isinstance(target, dict):
                step.update(target)
            elif isinstance(target, str) and "text" not in step:
                step["text"] = target
            try:
                result = await self.run(action, **step)
            except Exception as ex:
                results.append({"action": action, "success": False, "error": str(ex)})
                return {
                    "success": False,
                    "step": index,
                    "action": action,
                    "error": str(ex),
                    "results": [_summarize_step(item) for item in results],
                }
            results.append({"action": action, "success": True, **_summarize_step(result)})
        return {"success": True, "steps": len(results), "results": results}


class DockerExecBackend(BaseComputerBackend):
    """Drive a Linux desktop container through the mounted X11 agent."""

    kind = "linux"

    def __init__(self, session, runtime=None):
        super().__init__(session)
        self.runtime = runtime
        self.container = session.container_name or session.container_id

    def _python_candidates(self) -> List[str]:
        """Python interpreters tried inside the container."""
        return ["python3", "/lsiopy/bin/python3"]

    def _exec(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Run one command through the agent (blocking)."""
        if not self.container:
            raise DesktopControlError("The desktop container is not running")
        payload = json.dumps(command)
        last_error = ""
        for python in self._python_candidates():
            try:
                result = subprocess.run(
                    [
                        "docker", "exec", "-i",
                        "-e", f"DISPLAY={self.session.display or ':1'}",
                        self.container,
                        python, "/codx/computer_agent.py",
                    ],
                    input=payload,
                    capture_output=True,
                    text=True,
                    timeout=DEFAULT_ACTION_TIMEOUT,
                )
            except subprocess.TimeoutExpired as ex:
                raise DesktopControlError(
                    f"Desktop action '{command.get('action')}' timed out"
                ) from ex
            stdout = (result.stdout or "").strip()
            if stdout:
                try:
                    parsed = json.loads(stdout)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, dict):
                    if not parsed.get("ok", False):
                        error = str(parsed.get("error") or "Computer action failed")
                        # The image may only have Pillow in its virtualenv;
                        # try the next interpreter before giving up.
                        if "No module named" in error or "not found" in error:
                            last_error = error
                            continue
                        raise DesktopControlError(error)
                    parsed.pop("ok", None)
                    return parsed
            last_error = (result.stderr or result.stdout or "").strip()
            # Retry with the image's virtualenv interpreter when python3 lacks
            # Pillow (LinuxServer images provide /lsiopy/bin/python3).
            if "No module named" not in last_error and "not found" not in last_error:
                break
        raise DesktopControlError(
            f"Computer agent failed in container {self.container}: {last_error[:500]}"
        )

    async def capture_png(self) -> tuple[bytes, int, int]:
        """Capture the X11 root window through the agent."""
        result = await asyncio.to_thread(
            self._exec, {"action": "screenshot", "max_width": 4096}
        )
        data_uri = result.get("data") or ""
        if "," not in data_uri:
            raise DesktopControlError("Computer agent returned no screenshot data")
        png = base64.b64decode(data_uri.split(",", 1)[1])
        return png, int(result.get("width") or 0), int(result.get("height") or 0)

    def resize_support(self) -> Dict[str, Any]:
        """Linux desktops can be resized with xrandr when the X server allows it."""
        return {"supported": True, "mode": "xrandr"}

    async def _resize_desktop(self, width: int, height: int) -> Dict[str, Any]:
        """
        Resize the X11 desktop through xrandr (best effort).

        X servers that own the framebuffer (Xvnc/KasmVNC) reject RandR mode
        changes; the call then reports ``applied=False`` so the viewer keeps
        scaling the image instead of showing a broken desktop.
        """
        result = await asyncio.to_thread(
            self._exec,
            {"action": "run_command", "command": xrandr_resize_script(width, height), "timeout": 30},
        )
        stdout = (result.get("stdout") or "").strip()
        size = await self.execute("screen_size")
        current_width = int(size.get("width") or 0)
        current_height = int(size.get("height") or 0)
        applied = (current_width, current_height) == (width, height)
        if applied:
            message = f"Desktop resized to {current_width}x{current_height}"
        elif "no-output" in stdout:
            message = "The desktop has no active xrandr output; keep the live view scaled"
        else:
            message = (
                "The desktop X server does not accept RandR mode changes "
                "(Xvnc owns the framebuffer); keep the live view scaled instead"
            )
        return {
            "width": current_width,
            "height": current_height,
            "requested_width": width,
            "requested_height": height,
            "supported": True,
            "applied": applied,
            "message": message,
            "output": stdout[-500:],
            "exit_code": result.get("exit_code"),
        }

    async def execute(self, action: str, **params: Any) -> Dict[str, Any]:
        """Map a normalized action to the agent command."""
        command: Dict[str, Any] = {"action": action}
        if action == "resize":
            width, height = _resize_size(params)
            return await self._resize_desktop(width, height)
        if action in ("click", "double_click", "right_click"):
            command.update({
                "x": params.get("x", 0),
                "y": params.get("y", 0),
                "button": params.get("button", "left"),
                "clicks": params.get("clicks", 2 if action == "double_click" else 1),
            })
            if action == "right_click":
                command["button"] = "right"
        elif action in ("key", "hotkey"):
            command["action"] = "key"
            command["combo"] = params.get("combo") or params.get("key") or params.get("keys")
        elif action == "type":
            command["text"] = params.get("text", "")
            command["interval_ms"] = params.get("interval_ms", 30)
        elif action == "drag":
            command.update({
                "from_x": params.get("from_x", params.get("x", 0)),
                "from_y": params.get("from_y", params.get("y", 0)),
                "to_x": params.get("to_x", params.get("x2", 0)),
                "to_y": params.get("to_y", params.get("y2", 0)),
                "duration_ms": params.get("duration_ms", 500),
            })
        elif action == "scroll":
            command.update({
                "x": params.get("x", 0),
                "y": params.get("y", 0),
                "amount": params.get("amount", 3),
                "direction": params.get("direction", "down"),
            })
        elif action in ("move", "focus_window", "close_window", "open_app", "list_apps", "run_command", "wait", "clipboard_set"):
            command.update(params)
        elif action in ("screen_size", "windows", "active_window", "mouse_position", "clipboard_get", "ping"):
            pass
        else:
            raise UnsupportedComputerActionError(f"Unknown desktop action '{action}'")
        return await asyncio.to_thread(self._exec, command)

    async def close(self) -> None:
        """Nothing persistent to release for docker exec."""


class VncBackend(BaseComputerBackend):
    """Drive a Windows/macOS/remote desktop through RFB (and SSH when configured)."""

    kind = "vnc"

    def __init__(self, session, runtime=None):
        super().__init__(session)
        self.runtime = runtime
        self._client: Optional[RFBClient] = None
        self._ssh = SSHRunner(
            host=session.ssh_host,
            user=session.ssh_user,
            port=session.ssh_port,
            key_path=session.ssh_key_path,
            password=session.ssh_password,
            os_kind=session.kind,
        )

    @property
    def client(self) -> RFBClient:
        """Return (and lazily connect) the RFB client."""
        if self._client is None:
            host = self.session.vnc_host or self.session.ssh_host
            if not host:
                raise DesktopControlError(
                    "This session has no VNC host; set vnc_host on the session"
                )
            self._client = RFBClient(
                host,
                port=self.session.vnc_port or 5900,
                password=self.session.vnc_password,
            )
            self._client.connect()
        elif not self._client.connected:
            self._client.connect()
        return self._client

    def resize_support(self) -> Dict[str, Any]:
        """VNC desktops resize through SetDesktopSize when the server supports it."""
        client = self._client
        return {
            "supported": bool(client is not None and client.supports_extended_desktop_size),
            "mode": "rfb",
        }

    async def capture_png(self) -> tuple[bytes, int, int]:
        """Capture the VNC framebuffer."""
        def _capture():
            client = self.client
            png, info = client.screenshot()
            return png, int(info["width"]), int(info["height"])
        return await asyncio.to_thread(_capture)

    async def _resize_desktop(self, width: int, height: int) -> Dict[str, Any]:
        """Ask the VNC server for a new framebuffer size (SetDesktopSize)."""
        def _resize():
            client = self.client
            try:
                info = client.set_desktop_size(width, height)
            except RFBError as ex:
                return {
                    "width": client.width,
                    "height": client.height,
                    "requested_width": width,
                    "requested_height": height,
                    "supported": bool(client.supports_extended_desktop_size),
                    "applied": False,
                    "message": str(ex),
                }
            applied = bool(info.get("applied", True))
            return {
                "width": int(info.get("width") or client.width),
                "height": int(info.get("height") or client.height),
                "requested_width": width,
                "requested_height": height,
                "supported": bool(info.get("supported", True)),
                "applied": applied,
                "screens": info.get("screens") or [],
                "message": (
                    f"Desktop resized to {info.get('width')}x{info.get('height')}"
                    if applied else
                    "The VNC server kept its framebuffer size; keep the live view scaled"
                ),
            }
        return await asyncio.to_thread(_resize)

    async def execute(self, action: str, **params: Any) -> Dict[str, Any]:
        """Map a normalized action to RFB/SSH operations."""
        if action == "resize":
            width, height = _resize_size(params)
            return await self._resize_desktop(width, height)
        if action == "run_command":
            return await self._run_command(
                params.get("command", ""),
                timeout=params.get("timeout", 60),
            )
        if action == "open_app":
            return await self._open_app(
                params.get("app") or params.get("command") or "",
                wait=params.get("wait", 1.5),
            )
        if action == "windows":
            return {
                "windows": [],
                "note": "Window enumeration is not available over VNC; use OCR/click_text.",
            }
        if action in ("clipboard_get", "clipboard_set"):
            raise UnsupportedComputerActionError(
                "Clipboard transfer is not implemented for VNC sessions; use run_command over SSH."
            )
        if action == "ping":
            return await self.health()

        def _input():
            client = self.client
            if action in ("click", "double_click", "right_click"):
                button = params.get("button", "right" if action == "right_click" else "left")
                clicks = params.get("clicks", 2 if action == "double_click" else 1)
                client.click(
                    int(params.get("x", 0)),
                    int(params.get("y", 0)),
                    button=button,
                    clicks=clicks,
                )
                return {"x": params.get("x", 0), "y": params.get("y", 0), "button": button}
            if action == "move":
                client.move(int(params.get("x", 0)), int(params.get("y", 0)))
                return {"x": params.get("x", 0), "y": params.get("y", 0)}
            if action == "drag":
                client.drag(
                    int(params.get("from_x", params.get("x", 0))),
                    int(params.get("from_y", params.get("y", 0))),
                    int(params.get("to_x", params.get("x2", 0))),
                    int(params.get("to_y", params.get("y2", 0))),
                    duration_ms=int(params.get("duration_ms", 500)),
                )
                return {"from": [params.get("from_x"), params.get("from_y")],
                        "to": [params.get("to_x"), params.get("to_y")]}
            if action == "scroll":
                client.scroll(
                    int(params.get("x", 0)),
                    int(params.get("y", 0)),
                    amount=int(params.get("amount", 3)),
                    direction=params.get("direction", "down"),
                )
                return {"amount": params.get("amount", 3), "direction": params.get("direction", "down")}
            if action in ("key", "hotkey"):
                combo = params.get("combo") or params.get("key") or params.get("keys")
                if not combo:
                    raise DesktopControlError("key action requires a combo")
                client.press(str(combo))
                return {"keys": combo}
            if action == "type":
                text = params.get("text", "")
                client.type_text(str(text))
                return {"typed": len(str(text))}
            if action == "screen_size":
                return {"width": client.width, "height": client.height}
            if action == "wait":
                seconds = max(0.0, min(120.0, float(params.get("seconds", 1))))
                time.sleep(seconds)
                return {"waited": seconds}
            if action == "active_window":
                return {"window": None, "note": "Not exposed over VNC"}
            raise UnsupportedComputerActionError(f"Unknown VNC action '{action}'")

        return await asyncio.to_thread(_input)

    async def _run_command(self, command: str, timeout: float = 60) -> Dict[str, Any]:
        """Run a command through SSH (the only shell available for VMs)."""
        if not self._ssh.configured:
            raise UnsupportedComputerActionError(
                "No SSH endpoint is configured for this session. Open a terminal "
                "in the desktop and type commands, or add ssh_host/ssh_user to "
                "the session to enable shell commands."
            )
        try:
            return await asyncio.to_thread(self._ssh.run, command, timeout)
        except SSHError as ex:
            raise DesktopControlError(str(ex)) from ex

    async def _open_app(self, app: str, wait: float = 1.5) -> Dict[str, Any]:
        """Open the OS launcher, type the app name and press Enter."""
        app = str(app or "").strip()
        if not app:
            raise DesktopControlError("open_app requires an app name")
        if self.session.kind == "macos":
            combo = "super+space"
        elif self.session.kind == "windows":
            combo = "super"
        else:
            combo = "alt+F2"

        def _launch():
            client = self.client
            client.press(combo)
            time.sleep(0.6)
            client.type_text(app)
            time.sleep(0.4)
            client.tap(KEYSYMS["return"])
        await asyncio.to_thread(_launch)
        await asyncio.sleep(max(0.0, float(wait or 0)))
        return {"app": app, "launcher": combo}

    async def close(self) -> None:
        """Close the RFB connection."""
        if self._client is not None:
            await asyncio.to_thread(self._client.close)
            self._client = None


def get_backend(session, runtime=None) -> BaseComputerBackend:
    """Return the backend that drives *session*."""
    if session.kind == "linux" and session.control != "vnc":
        return DockerExecBackend(session, runtime=runtime)
    if session.kind in ("linux", "windows", "macos", "remote"):
        return VncBackend(session, runtime=runtime)
    raise UnsupportedComputerActionError(
        f"Session kind '{session.kind}' is driven by the browser runtime, not the computer backend"
    )