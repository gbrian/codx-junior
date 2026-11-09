"""
ComputerSession — data model for shared computer sessions.

A session is a **computer the user and the AI share**, not necessarily a
browser: the same record describes a Chromium page (``kind="browser"``), a Linux
desktop container, a Windows VM, a macOS VM or a remote machine reachable over
VNC/SSH.  Every kind has one live view for the human and one control channel for
the AI, so both actors operate on the same screen and the same state.

Persisted in Chat.meta_data["browser"] (legacy key, kept so existing chats keep
working) and in the session folder as ``<session_id>.session`` JSON.

A session is shared between chats: ``chat_ids`` holds every chat currently
connected to the session while ``name`` is the human-readable label provided at
creation.

The session also stores the **project folder mapping**: any number of project
folders are bind mounted inside the container under ``/home/<project_name>/<folder>``
(and ``/shared`` for the Windows/macOS VMs) and downloads are written into a
project folder, so the user (live view) and the AI exchange files with the
project instead of being isolated in the container.
"""

import json
import os
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator, model_validator


#: Session kinds supported by the computer manager.
#: ``browser`` keeps the original Chromium/CDP behaviour; the rest share a
#: desktop with the AI through a screenshot/input backend.
COMPUTER_KINDS = ("browser", "linux", "macos", "windows", "remote")
#: Kinds backed by a Docker container owned by codx-junior.
CONTAINER_KINDS = ("browser", "linux", "macos", "windows")
#: Kinds that expose a graphical desktop (not a browser page).
DESKTOP_KINDS = ("linux", "macos", "windows", "remote")
#: Ways the AI can drive a session.
CONTROL_MODES = ("cdp", "docker", "vnc", "ssh")

KIND_ALIASES = {
    "mac": "macos",
    "macosx": "macos",
    "osx": "macos",
    "darwin": "macos",
    "mac-os": "macos",
    "win": "windows",
    "win10": "windows",
    "win11": "windows",
    "ubuntu": "linux",
    "debian": "linux",
    "desktop": "linux",
    "x11": "linux",
    "vnc": "remote",
    "ssh": "remote",
    "server": "remote",
}

#: Capabilities advertised to the model per session kind.
DEFAULT_CAPABILITIES = {
    "browser": ["screenshot", "mouse", "keyboard", "shell", "files", "browser"],
    "linux": ["screenshot", "ocr", "mouse", "keyboard", "shell", "files", "apps", "windows"],
    "windows": ["screenshot", "ocr", "mouse", "keyboard", "files"],
    "macos": ["screenshot", "ocr", "mouse", "keyboard", "files"],
    "remote": ["screenshot", "ocr", "mouse", "keyboard"],
}

#: Resource sizes accepted for RAM, disk and shared memory (``8G``, ``1.5G``,
#: ``64GiB``...).  A unit is required: Docker treats a bare number as bytes.
SIZE_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([KMGT])(?:I?B)?\s*$", re.IGNORECASE)
#: Accepted names for extra image environment variables.
ENV_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
#: Upper bounds for the advanced settings (they reach ``docker run``).
MAX_EXTRA_ENV = 50
MAX_ENV_VALUE_LENGTH = 4096


def normalize_size(value: Any, field: str = "size") -> Optional[str]:
    """
    Normalize a resource size (``"8g"`` -> ``"8G"``, ``"64GiB"`` -> ``"64G"``).

    Args:
        value: User supplied size; ``None``/empty clears it.
        field: Field name used in the error message.

    Returns:
        Optional[str]: Normalized size or None.

    Raises:
        ValueError: When the value is not a positive number with a unit.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = SIZE_PATTERN.match(text)
    if not match:
        raise ValueError(
            f"Invalid {field} '{value}'. Use a positive number with a unit, "
            "for example 4G, 512M or 1.5G."
        )
    number, unit = match.group(1), match.group(2).upper()
    if float(number) <= 0:
        raise ValueError(f"Invalid {field} '{value}': it must be greater than zero")
    return f"{number}{unit}"


def normalize_extra_env(value: Any) -> Dict[str, str]:
    """
    Normalize the advanced image environment variables.

    Accepts a mapping, a list of ``KEY=VALUE`` strings or a multi-line string
    (as typed in the UI).  Blank lines and ``#`` comments are ignored.

    Raises:
        ValueError: When a name/value is invalid or the list is too long.
    """
    if value is None or value == "":
        return {}
    entries: List[Any]
    if isinstance(value, dict):
        entries = list(value.items())
    elif isinstance(value, str):
        entries = [line for line in value.splitlines() if line.strip() and not line.strip().startswith("#")]
    elif isinstance(value, (list, tuple)):
        entries = list(value)
    else:
        raise ValueError("extra_env must be an object, a list of KEY=VALUE pairs or a string")

    result: Dict[str, str] = {}
    for entry in entries:
        if isinstance(entry, dict):
            name = entry.get("name") or entry.get("key")
            raw_value = entry.get("value")
        elif isinstance(entry, str):
            name, separator, raw_value = entry.partition("=")
            if not separator:
                raise ValueError(f"Invalid environment variable '{entry}': use KEY=VALUE")
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            name, raw_value = entry
        else:
            raise ValueError(f"Invalid environment variable entry: {entry!r}")

        name = str(name or "").strip()
        if not ENV_NAME_PATTERN.match(name):
            raise ValueError(f"Invalid environment variable name '{name}'")
        text_value = "" if raw_value is None else str(raw_value)
        if len(text_value) > MAX_ENV_VALUE_LENGTH:
            raise ValueError(
                f"Environment variable '{name}' is too long "
                f"(max {MAX_ENV_VALUE_LENGTH} characters)"
            )
        result[name] = text_value

    if len(result) > MAX_EXTRA_ENV:
        raise ValueError(f"Too many environment variables (max {MAX_EXTRA_ENV})")
    return result


def normalize_kind(value: Optional[str], default: str = "browser") -> str:
    """Normalize a user supplied session kind (``mac`` -> ``macos``)."""
    kind = str(value or default or "browser").strip().lower().replace("_", "-")
    kind = KIND_ALIASES.get(kind, kind)
    if kind not in COMPUTER_KINDS:
        raise ValueError(
            f"Unknown computer kind '{value}'. Use one of: {', '.join(COMPUTER_KINDS)}"
        )
    return kind


def default_control(kind: str) -> str:
    """Return the control channel used by a session kind by default."""
    if kind == "browser":
        return "cdp"
    if kind == "linux":
        return "docker"
    return "vnc"


class SharedFolder(BaseModel):
    """
    One host folder bind mounted inside a browser container.

    ``folder`` is the project-relative path (``""`` means the project itself),
    ``host_path`` the absolute host folder and ``mount_path`` the path the same
    folder gets inside the container (``/home/<project_name>/<folder>`` unless
    the caller asked for a custom mount point).
    """

    id: Optional[str] = Field(
        default=None,
        description="Immutable share identifier (auto-generated)"
    )
    name: Optional[str] = Field(
        default=None,
        description="Human-readable label of the shared folder"
    )
    folder: Optional[str] = Field(
        default=None,
        description="Project-relative folder ('' or None means the project root)"
    )
    host_path: str = Field(
        description="Absolute host folder bind mounted into the container"
    )
    mount_path: str = Field(
        description="Path of the folder inside the container (e.g. /home/proj/docs)"
    )
    readonly: bool = Field(
        default=False,
        description="Mount the folder read-only (the browser cannot write into it)"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = str(uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert the share to a dictionary for JSON serialization."""
        return self.model_dump(exclude_none=False)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SharedFolder":
        """Reconstruct a share from a dictionary."""
        return SharedFolder(**data)

    def contains(self, host_path: str) -> bool:
        """Return True when *host_path* lives inside this shared folder."""
        base = os.path.abspath(self.host_path)
        target = os.path.abspath(host_path or "")
        return target == base or target.startswith(base + os.sep)

    def container_path(self, relative_path: str = "") -> str:
        """
        Return the container path of a file inside this share.

        Args:
            relative_path: Path relative to the shared folder.

        Raises:
            ValueError: When the path escapes the shared folder.
        """
        base = (self.mount_path or "").rstrip("/")
        relative = (relative_path or "").strip().strip("/")
        if not relative:
            return base
        parts = [part for part in relative.split("/") if part not in ("", ".")]
        if any(part == ".." for part in parts):
            raise ValueError(f"'{relative_path}' is outside the shared folder")
        return f"{base}/{'/'.join(parts)}"

    def file_url(self, relative_path: str = "") -> str:
        """Return the ``file://`` URL the browser must open for a shared file."""
        return f"file://{self.container_path(relative_path)}"

    def file_path(self, relative_path: str = "") -> str:
        """
        Return the host path of a file inside this share.

        Raises:
            ValueError: When the path escapes the shared folder.
        """
        base = os.path.abspath(self.host_path)
        relative = (relative_path or "").strip().lstrip("/")
        target = os.path.abspath(os.path.join(base, relative)) if relative else base
        if target != base and not target.startswith(base + os.sep):
            raise ValueError(f"'{relative_path}' is outside the shared folder")
        return target

    def __repr__(self) -> str:
        return f"SharedFolder(name={self.name!r}, {self.host_path} -> {self.mount_path})"


class BrowserSession(BaseModel):
    """
    Represents the state of a shared **computer** session.

    - ``kind="browser"``: a Chromium container driven through CDP;
    - ``kind="linux"``: a Linux desktop container driven through ``docker exec``
      (xdotool + X11 screenshots);
    - ``kind="windows"`` / ``macos``: a VM container driven through its VNC
      framebuffer (QEMU/dockurr), with an optional direct VNC endpoint;
    - ``kind="remote"``: an existing machine reachable over VNC (and optionally
      SSH), e.g. a physical Mac used for iOS development.

    The user sees the same machine through the live view (Selkies iframe or the
    built-in noVNC viewer); the AI drives it through the control channel, so
    both operate on exactly the same screen and state.

    Files are shared with the project through bind mounts:

    - ``shared_folders``: every project folder mounted in the container, laid out
      under ``home_path`` (``/home/<project_name>``), or ``/shared`` for the
      Windows/macOS VMs (``guest_share_path`` tells the model where it appears);
    - ``downloads_path`` (host) mounted/known as ``downloads_mount``, where
      everything saved by the AI/user is written.
    """

    id: Optional[str] = Field(
        default=None,
        description="Unique session identifier (auto-generated)"
    )
    name: Optional[str] = Field(
        default=None,
        description="Human-readable session name given at creation"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional free-form description of the session"
    )
    kind: str = Field(
        default="browser",
        description="Session kind: browser, linux, macos, windows or remote"
    )
    control: Optional[str] = Field(
        default=None,
        description="AI control channel: cdp, docker, vnc or ssh"
    )
    os_version: Optional[str] = Field(
        default=None,
        description="OS release/version label (e.g. '11' for Windows 11, '15' for macOS)"
    )
    image: Optional[str] = Field(
        default=None,
        description="Docker image used to start the session (container kinds)"
    )
    image_provider: Optional[str] = Field(
        default=None,
        description="Image provider: linuxserver, kasmweb, dockurr or custom"
    )
    library_item_id: Optional[str] = Field(
        default=None,
        description="Saved computer library item this session was started from"
    )
    library_item_name: Optional[str] = Field(
        default=None,
        description="Human-readable name of the saved computer used at creation"
    )
    live_view: Optional[str] = Field(
        default=None,
        description="Human live view transport: selkies, kasmvnc, vnc or screenshot"
    )
    live_scheme: Optional[str] = Field(
        default=None,
        description="Scheme of the live view service (http/https)"
    )
    live_port: Optional[int] = Field(
        default=None,
        description="Container port of the live view service"
    )
    strip_prefix: bool = Field(
        default=False,
        description="Strip the public path prefix when proxying the live view"
    )
    viewer_user: Optional[str] = Field(
        default=None,
        description="Login user shown to the human for the live view (KasmVNC)"
    )
    viewer_password: Optional[str] = Field(
        default=None,
        description="Login password for the live view (never serialized to clients)"
    )
    cpu_cores: Optional[int] = Field(
        default=None,
        ge=1,
        le=128,
        description=(
            "Virtual CPUs for the machine. VM images receive it as CPU_CORES; "
            "browser/Linux containers get a Docker --cpus limit."
        ),
    )
    ram_size: Optional[str] = Field(
        default=None,
        description=(
            "RAM for the machine (e.g. '8G'). VM images receive it as RAM_SIZE; "
            "browser/Linux containers get a Docker --memory limit."
        ),
    )
    disk_size: Optional[str] = Field(
        default=None,
        description=(
            "Disk size for Windows/macOS VM images (e.g. '64G'). It is only "
            "used when the VM disk is created, so it cannot shrink later."
        ),
    )
    shm_size: Optional[str] = Field(
        default=None,
        description=(
            "Docker shared-memory size for browser/Linux containers "
            "(e.g. '2G'; default 2G)."
        ),
    )
    extra_env: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Extra environment variables passed to the image (advanced). "
            "Variables owned by codx-junior (SUBFOLDER, VERSION, ...) win."
        ),
    )
    container_id: Optional[str] = Field(
        default=None,
        description="Docker container ID"
    )
    container_name: Optional[str] = Field(
        default=None,
        description="Human-readable container name"
    )
    status: str = Field(
        default="idle",
        description="Current session status: idle, running, stopped, error"
    )
    vnc_url: Optional[str] = Field(
        default=None,
        description="Live view (VNC/Selkies) URL via Traefik routing"
    )
    vnc_path: Optional[str] = Field(
        default=None,
        description="Same-origin live view path (e.g. /browser/<id>/)"
    )
    debug_url: Optional[str] = Field(
        default=None,
        description="Chrome DevTools Protocol connection URL"
    )
    current_url: Optional[str] = Field(
        default=None,
        description="Currently loaded page URL in browser"
    )
    engine: str = Field(
        default="chromium",
        description="Engine powering the session: chromium, desktop or remote"
    )
    browser_profile_path: Optional[str] = Field(
        default=None,
        description="Path to the persistent browser/desktop profile (cookies, logins, home)"
    )
    profile_path: Optional[str] = Field(
        default=None,
        description="Generic alias of browser_profile_path (desktop containers too)"
    )
    display: Optional[str] = Field(
        default=None,
        description="X11 display inside the container (linux desktop, e.g. ':1')"
    )
    desktop_width: int = Field(
        default=1920,
        description="Desktop width in pixels (used to scale screenshot coordinates)"
    )
    desktop_height: int = Field(
        default=1080,
        description="Desktop height in pixels (used to scale screenshot coordinates)"
    )
    vnc_host: Optional[str] = Field(
        default=None,
        description="Host the AI's VNC control connection reaches (container DNS or remote host)"
    )
    vnc_port: int = Field(
        default=5900,
        description="VNC/RFB port of the desktop"
    )
    vnc_password: Optional[str] = Field(
        default=None,
        description="VNC password (never serialized to clients/logs)"
    )
    vnc_public_url: Optional[str] = Field(
        default=None,
        description="Optional viewer URL for the human (noVNC/Selkies)"
    )
    vnc_public_port: Optional[int] = Field(
        default=None,
        description="Host port published for a user-provided VNC client"
    )
    ssh_host: Optional[str] = Field(
        default=None,
        description="SSH host for shell access (remote sessions)"
    )
    ssh_port: int = Field(
        default=22,
        description="SSH port (remote sessions)"
    )
    ssh_user: Optional[str] = Field(
        default=None,
        description="SSH username (remote sessions)"
    )
    ssh_key_path: Optional[str] = Field(
        default=None,
        description="Host path of the SSH private key used for shell access"
    )
    ssh_password: Optional[str] = Field(
        default=None,
        description="SSH password (never serialized to clients/logs)"
    )
    guest_share_path: Optional[str] = Field(
        default=None,
        description="Where the shared folder appears inside the guest (e.g. 'Z:\\\\' for Windows)"
    )
    capabilities: List[str] = Field(
        default_factory=list,
        description="Actions this session supports (screenshot, mouse, keyboard, shell, files...)"
    )
    project_name: Optional[str] = Field(
        default=None,
        description="Project name used to build the container home folder"
    )
    home_path: Optional[str] = Field(
        default=None,
        description="Container folder holding the project folders (e.g. /home/proj)"
    )
    shared_folders: List[SharedFolder] = Field(
        default_factory=list,
        description="Project folders mounted inside the browser container"
    )
    downloads_path: Optional[str] = Field(
        default=None,
        description="Host folder receiving the files downloaded by the browser"
    )
    downloads_folder: Optional[str] = Field(
        default=None,
        description="Project-relative folder receiving the downloads"
    )
    downloads_mount: Optional[str] = Field(
        default=None,
        description="Container path where the downloads are written"
    )
    downloads_own_mount: bool = Field(
        default=True,
        description=(
            "True when the downloads folder has its own bind mount; False when "
            "it already lives inside one of the shared folders"
        )
    )
    current_title: Optional[str] = Field(
        default=None,
        description="Title of the page currently loaded in the browser"
    )
    # -- Co-browsing control -------------------------------------------------
    # The page is shared by the human (VNC view) and the AI (CDP tools).  These
    # fields make the hand-off explicit instead of relying on "whoever calls
    # last wins": the AI must not type over a form the user is editing, and a
    # session waiting for MFA/captcha must say so.
    controller: str = Field(
        default="ai",
        description="Who may drive the page: 'ai', 'user' or 'none'"
    )
    controller_chat_id: Optional[str] = Field(
        default=None,
        description="Chat that owns the current control lease (when known)"
    )
    user_active_until: Optional[str] = Field(
        default=None,
        description="ISO timestamp until which recent user input keeps the AI paused"
    )
    handoff_reason: Optional[str] = Field(
        default=None,
        description="Why the AI handed control to the user (MFA, captcha, approval...)"
    )
    last_user_event_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp of the last real user interaction captured in the page"
    )
    last_action: Optional[str] = Field(
        default=None,
        description="Last action performed by a user or the AI"
    )
    last_action_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp of the last action"
    )
    chat_ids: List[str] = Field(
        default_factory=list,
        description="Chat IDs connected to this session (multiple chats can share it)"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp when session was created"
    )
    last_active: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of last activity"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if session failed"
    )
    traefik_domain: Optional[str] = Field(
        default=None,
        description="Traefik domain for routing (e.g., app.example.com)"
    )
    traefik_path_prefix: Optional[str] = Field(
        default=None,
        description="Traefik path prefix (e.g., /browser/<session_id>)"
    )

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, data: Any) -> Any:
        """
        Backwards compatibility and defaults for persisted sessions.

        Older session records stored a single ``chat_id`` and a single project
        share (``shared_project_path``/``shared_project_mount``); both are mapped
        to ``chat_ids`` and ``shared_folders`` so existing sessions keep working.
        Records created before computer sessions have no ``kind`` and are
        therefore browsers.
        """
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if data.get("chat_id") and not data.get("chat_ids"):
            data["chat_ids"] = [data["chat_id"]]
        if data.get("shared_project_path") and not data.get("shared_folders"):
            data["shared_folders"] = [{
                "name": data.get("project_name"),
                "folder": "",
                "host_path": data["shared_project_path"],
                "mount_path": data.get("shared_project_mount") or "/project",
                "readonly": bool(data.get("shared_project_readonly")),
            }]

        kind = normalize_kind(data.get("kind"))
        data["kind"] = kind
        control = str(data.get("control") or "").strip().lower()
        if control not in CONTROL_MODES:
            control = default_control(kind)
        # The control channel is dictated by the kind: browsers only speak CDP,
        # Windows/macOS/remote desktops only speak VNC, Linux may use its
        # in-container agent (default) or VNC for a custom image.
        if kind == "browser":
            control = "cdp"
        elif kind == "linux":
            control = "vnc" if control == "vnc" else "docker"
        else:
            control = "vnc"
        data["control"] = control
        if not data.get("capabilities"):
            data["capabilities"] = list(DEFAULT_CAPABILITIES.get(kind, []))
        # Nullable persisted values must not break reloads: ports and sizes have
        # concrete defaults.
        for key, default in (("vnc_port", 5900), ("ssh_port", 22),
                             ("desktop_width", 1920), ("desktop_height", 1080)):
            if data.get(key) is None:
                data[key] = default
        if not data.get("engine"):
            data["engine"] = "chromium" if kind == "browser" else (
                "remote" if kind == "remote" else "desktop"
            )
        # Generic profile path mirrors the legacy browser field both ways.
        if data.get("profile_path") and not data.get("browser_profile_path"):
            data["browser_profile_path"] = data["profile_path"]
        if data.get("browser_profile_path") and not data.get("profile_path"):
            data["profile_path"] = data["browser_profile_path"]
        # Advanced resource settings are optional: an empty form field or 0
        # means "use the image/manager default" instead of failing validation.
        for key in ("cpu_cores", "ram_size", "disk_size", "shm_size"):
            if data.get(key) in ("", 0, "0"):
                data[key] = None
        return data

    @field_validator("ram_size", "disk_size", "shm_size", mode="before")
    @classmethod
    def _normalize_resource_sizes(cls, value: Any, info) -> Optional[str]:
        """Normalize/validate the advanced size fields (``8g`` -> ``8G``)."""
        return normalize_size(value, info.field_name)

    @field_validator("extra_env", mode="before")
    @classmethod
    def _normalize_extra_env(cls, value: Any) -> Dict[str, str]:
        """Accept a mapping, KEY=VALUE lines or a list from the UI/API."""
        return normalize_extra_env(value)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = str(uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for JSON serialization/persistence."""
        return self.model_dump(exclude_none=False)

    def to_public_dict(self) -> Dict[str, Any]:
        """
        Return the session as safe to send to a browser client.

        Secrets (VNC/SSH passwords and the SSH key path) stay on disk: the
        public record is what the UI, Socket.IO events and API responses use.
        """
        data = self.to_dict()
        for secret in ("vnc_password", "ssh_password", "ssh_key_path", "viewer_password"):
            data.pop(secret, None)
        return data

    # -------------------------------------------------------------------------
    # Computer kind helpers
    # -------------------------------------------------------------------------
    @property
    def is_browser(self) -> bool:
        """True for the original Chromium/CDP session."""
        return self.kind == "browser"

    @property
    def is_desktop(self) -> bool:
        """True for any session exposing a graphical desktop."""
        return self.kind in DESKTOP_KINDS

    @property
    def is_remote(self) -> bool:
        """True when the session points at an existing machine (no container)."""
        return self.kind == "remote"

    @property
    def kind_label(self) -> str:
        """Human label used by the UI (``macOS``, ``Windows``, ``Linux``...)."""
        return {
            "browser": "Browser",
            "linux": "Linux",
            "macos": "macOS",
            "windows": "Windows",
            "remote": "Remote",
        }.get(self.kind, self.kind.title())

    @property
    def has_shell(self) -> bool:
        """True when ``run_command`` can execute commands on the machine."""
        return "shell" in (self.capabilities or [])

    def supports(self, capability: str) -> bool:
        """Return True when the session advertises *capability*."""
        return (capability or "").lower() in (self.capabilities or [])

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "BrowserSession":
        """Reconstruct session from dictionary."""
        return BrowserSession(**data)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def from_json(json_str: str) -> "BrowserSession":
        """Deserialize from JSON string."""
        return BrowserSession.from_dict(json.loads(json_str))

    def mark_active(self) -> None:
        """Update last_active timestamp to now."""
        self.last_active = datetime.utcnow().isoformat()

    def mark_action(self, action: str) -> None:
        """Record the last action and its timestamp."""
        self.last_action = action
        self.last_action_at = datetime.utcnow().isoformat()
        self.mark_active()

    # -------------------------------------------------------------------------
    # Advanced settings (image/resources) on an existing session
    # -------------------------------------------------------------------------
    def apply_advanced_settings(self, updates: Dict[str, Any]) -> None:
        """
        Validate and apply advanced settings to an existing session.

        Only the keys present in *updates* change, which lets the API update a
        single setting without resending the rest.  The values are validated
        exactly like at creation (sizes normalized, env names checked); an
        invalid update raises ``ValueError`` and leaves the session untouched.

        Resource changes are stored on the record and take effect the next time
        the container is recreated (``restart``), because Docker cannot change
        the memory/CPU/disk of a running container.
        """
        allowed = {
            "image",
            "cpu_cores",
            "ram_size",
            "disk_size",
            "shm_size",
            "extra_env",
            "desktop_width",
            "desktop_height",
        }
        pending: Dict[str, Any] = {}
        for key, value in (updates or {}).items():
            if key not in allowed:
                continue
            if key in ("ram_size", "disk_size", "shm_size"):
                pending[key] = normalize_size(value, key)
            elif key == "extra_env":
                pending[key] = normalize_extra_env(value)
            elif key == "image":
                pending[key] = (str(value).strip() or None) if value is not None else None
            elif key == "cpu_cores":
                if value in (None, "", 0, "0"):
                    pending[key] = None
                else:
                    cpus = int(value)
                    if cpus < 1 or cpus > 128:
                        raise ValueError("cpu_cores must be between 1 and 128")
                    pending[key] = cpus
            elif key == "desktop_width":
                if value in (None, "", 0, "0"):
                    pending[key] = 1920
                else:
                    width = int(value)
                    if width < 640 or width > 7680:
                        raise ValueError("desktop_width must be between 640 and 7680")
                    pending[key] = width
            elif key == "desktop_height":
                if value in (None, "", 0, "0"):
                    pending[key] = 1080
                else:
                    height = int(value)
                    if height < 480 or height > 4320:
                        raise ValueError("desktop_height must be between 480 and 4320")
                    pending[key] = height

        for key, value in pending.items():
            setattr(self, key, value)
        if pending:
            self.mark_active()

    # -------------------------------------------------------------------------
    # Co-browsing control
    # -------------------------------------------------------------------------
    def set_controller(
        self,
        controller: str,
        chat_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Move the control lease to ``ai``, ``user`` or ``none``."""
        value = str(controller or "").strip().lower()
        if value not in ("ai", "user", "none"):
            raise ValueError("controller must be 'ai', 'user' or 'none'")
        self.controller = value
        self.controller_chat_id = chat_id if value != "none" else None
        if value == "user":
            self.handoff_reason = (reason or "").strip() or None
        elif value == "ai":
            self.handoff_reason = None
            # Giving control back explicitly overrides the "recent input" pause;
            # otherwise a handoff would keep the AI blocked for its 10-minute
            # user-active window even after the human pressed "Give back".
            self.user_active_until = None
        self.mark_active()

    def mark_user_active(self, seconds: int = 10) -> None:
        """Remember that the human is interacting with the page right now.

        While this window is open the AI yields: it would otherwise type over
        the user's input or navigate away from the field being edited.
        """
        now = datetime.now(timezone.utc)
        self.last_user_event_at = now.isoformat()
        self.user_active_until = (
            now + timedelta(seconds=max(1, int(seconds)))
        ).isoformat()
        self.mark_active()

    def user_is_active(self, grace_seconds: int = 0) -> bool:
        """True while the human is considered to be driving the page."""
        if self.controller == "user":
            return True
        if not self.user_active_until:
            return False
        try:
            until = datetime.fromisoformat(self.user_active_until)
        except Exception:
            return False
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        if grace_seconds:
            until = until + timedelta(seconds=max(0, int(grace_seconds)))
        return datetime.now(timezone.utc) < until

    def can_ai_act(self, grace_seconds: int = 0) -> bool:
        """True when the AI is allowed to perform a state-changing action."""
        if self.controller == "user":
            return False
        if self.controller == "none":
            return False
        return not self.user_is_active(grace_seconds=grace_seconds)

    def request_handoff(self, reason: str, chat_id: Optional[str] = None) -> None:
        """Pause the AI and ask the human to take over the page."""
        self.set_controller("user", chat_id=chat_id, reason=reason)
        self.mark_user_active(seconds=600)

    def add_chat(self, chat_id: str) -> None:
        """Connect a chat to this session (idempotent)."""
        if chat_id and chat_id not in self.chat_ids:
            self.chat_ids.append(chat_id)

    def remove_chat(self, chat_id: str) -> None:
        """Disconnect a chat from this session."""
        if chat_id and chat_id in self.chat_ids:
            self.chat_ids.remove(chat_id)

    def has_chat(self, chat_id: str) -> bool:
        """Return True when *chat_id* is connected to this session."""
        return bool(chat_id) and chat_id in self.chat_ids

    # -------------------------------------------------------------------------
    # Project file sharing
    # -------------------------------------------------------------------------

    def shares_project(self) -> bool:
        """Return True when at least one project folder is mounted."""
        return bool(self.shared_folders)

    def shares_files(self) -> bool:
        """Return True when files can be exchanged with the project."""
        return bool(self.downloads_path or self.shared_folders)

    def project_share(self) -> Optional[SharedFolder]:
        """Return the share holding the project root (None when not mounted)."""
        return next(
            (share for share in self.shared_folders if not (share.folder or "").strip("/")),
            None,
        )

    def shared_folder(self, reference: str) -> Optional[SharedFolder]:
        """
        Return a share by id, name, project folder or container mount path.
        """
        key = (reference or "").strip()
        if not key:
            return None
        for share in self.shared_folders:
            if key in (share.id, share.name, share.folder, share.mount_path):
                return share
        return None

    def covering_share(self, host_path: str, writable_only: bool = False) -> Optional[SharedFolder]:
        """
        Return the innermost shared folder containing *host_path*.

        Args:
            host_path: Absolute host path to locate.
            writable_only: Ignore read-only shares (used to place the downloads).
        """
        target = os.path.abspath(host_path or "")
        best: Optional[SharedFolder] = None
        for share in self.shared_folders:
            if writable_only and share.readonly:
                continue
            if not share.contains(target):
                continue
            if best is None or len(share.host_path) > len(best.host_path):
                best = share
        return best

    def project_file_path(self, relative_path: str = "") -> Optional[str]:
        """
        Return the host path of a project file.

        Args:
            relative_path: Path relative to the project root.

        Returns:
            Optional[str]: Absolute host path, or None when the project root is
            not mounted.

        Raises:
            ValueError: When the path escapes the project folder.
        """
        share = self.project_share()
        return share.file_path(relative_path) if share else None

    def container_project_path(self, relative_path: str = "") -> Optional[str]:
        """
        Return the container path of a project file (``/home/<project>/<path>``).
        """
        share = self.project_share()
        return share.container_path(relative_path) if share else None

    def project_file_url(self, relative_path: str = "") -> Optional[str]:
        """Return the ``file://`` URL the browser must open for a project file."""
        share = self.project_share()
        return share.file_url(relative_path) if share else None

    def __repr__(self) -> str:
        return (
            f"BrowserSession(id={self.id[:8]}, "
            f"kind={self.kind}, "
            f"name={self.name!r}, "
            f"status={self.status}, container={self.container_name}, "
            f"shares={len(self.shared_folders)})"
        )

#: The generic name used by the computer-session code and the new API.  The
#: original class name is kept as an alias so every existing import, persisted
#: record and test keeps working.
ComputerSession = BrowserSession
