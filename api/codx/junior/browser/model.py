"""
BrowserSession — data model for browser session state.

Stores session configuration and connection info, persisted in Chat.meta_data["browser"]
and in session folder as <session_id>.session JSON file.

A session is shared between chats: ``chat_ids`` holds every chat currently connected
to the session while ``name`` is the human-readable label provided at creation.

The session also stores the **project folder mapping**: any number of project folders
are bind mounted inside the browser container under ``/home/<project_name>/<folder>``
and the browser's downloads are written into a project folder, so the user (live VNC
view) and the AI exchange files with the project instead of being isolated in the
container.
"""

import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from pydantic import BaseModel, Field, model_validator


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
    Represents the state of a Chromium co-browsing session running in Docker.

    Stores connection details, ports, and session metadata.
    Persisted as JSON in Chat.meta_data["browser"] and as file in session folder.

    A single session may be connected to **several chats** (``chat_ids``); the
    ``name`` is supplied by the caller when the session is created.  The same
    browser is displayed to users (live VNC view) and automated by the AI
    (Chrome DevTools Protocol), so both operate on the exact same page.

    Files are shared with the project through bind mounts:

    - ``shared_folders``: every project folder mounted in the container, laid out
      under ``home_path`` (``/home/<project_name>``);
    - ``downloads_path`` (host) mounted/known as ``downloads_mount``, where
      everything the browser downloads is saved.
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
        description="Browser engine powering the session (chromium)"
    )
    browser_profile_path: Optional[str] = Field(
        default=None,
        description="Path to the persistent Chromium profile (cookies, logins, etc.)"
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
        Backwards compatibility for persisted sessions.

        Older session records stored a single ``chat_id`` and a single project
        share (``shared_project_path``/``shared_project_mount``); both are mapped
        to ``chat_ids`` and ``shared_folders`` so existing sessions keep working.
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
        return data

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = str(uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for JSON serialization."""
        return self.model_dump(exclude_none=False)

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
            f"name={self.name!r}, "
            f"status={self.status}, container={self.container_name}, "
            f"shares={len(self.shared_folders)})"
        )