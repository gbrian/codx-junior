"""
BrowserManager / ComputerManager — CRUD and lifecycle for computer sessions.

A session is a machine shared by the user and the AI.  ``kind="browser"`` keeps
the original Chromium/CDP behaviour; ``linux`` runs a desktop container driven
through ``docker exec``; ``windows``/``macos`` run QEMU VMs driven through VNC;
``remote`` points at an existing VNC/SSH machine.  This class owns session
persistence, chat linking, activity audit, folder sharing and the per-session
runtime (BrowserRuntime for browsers, DesktopRuntime for desktops).

Follows the workspace pattern:
    .codx/browser_sessions/<session_id>/<session_id>.session

A session is created with a human-readable ``name`` and may be shared by several
chats (``session.chat_ids``).  The container is a Chromium instance with a live
VNC view (for the user) and a CDP endpoint (for the AI), so both actors control
the same browser page.

Folder sharing
--------------
Any number of project folders are mounted inside the browser container under a
single tree (``/home/<project_name>/<folder>``) and the browser downloads are
written inside a project folder, so the user and the AI exchange files with the
project instead of being locked in the container:

- ``configure_share`` decides the mounts when the session is created;
- the downloads folder is written into the browser profile *before* the container
  starts (``codx/junior/browser/download_settings.py``), because Chromium reads
  the download directory at launch — this is the durable half and covers the
  downloads the user starts in the live VNC view;
- the same folder is also applied through CDP on every connection
  (``Browser.setDownloadBehavior``), which is the live half: it also covers a
  download triggered by the AI while its connection is open;
- ``get_shared_paths`` / ``get_shared_files`` expose the mapping and the files
  the browser saved inside the project.

Browser window survival
-----------------------
Chromium exits when its last window (tab) is closed, while the container keeps
running: the live view stays up but the browser window is gone and the DevTools
endpoint is dead.  Two defences keep a session usable:

- a protected **keep-alive tab** is created with the session and ensured on every
  connection (``codx/junior/browser/tabs.py``), so closing every other tab leaves
  the window alive;
- ``connect_browser`` **recovers** a dead browser by restarting the container
  entrypoint (which relaunches Chromium with the mounted profile) and retrying
  the connection once.

Lifecycle primitives
--------------------
- ``create_session(name, chat_id, initial_url, description)`` : start a new container + persist metadata.
- ``stop_session(session_id)``      : stop the container but KEEP it (restartable).
- ``restart_session(session_id)``   : relaunch Chromium (recovery) / recreate a stopped session.
- ``delete_session(session_id)``    : stop the container, remove it and the folder.
- ``log_activity(...)``             : append an audit entry for a user/AI action.
"""

import logging
import os
import json
import asyncio
import secrets
import shutil
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Set, Tuple
from pathlib import Path

from codx.junior.settings import CODXJuniorSettings
from codx.junior.browser.model import BrowserSession
from codx.junior.browser.docker_browser_manager import DockerBrowserManager
from codx.junior.browser.browser import Browser, run_coroutine_sync
from codx.junior.browser import download_settings
from codx.junior.browser import tabs as browser_tabs
from codx.junior.browser.activity import BrowserActivityLog
from codx.junior.browser import events as browser_events

logger = logging.getLogger(__name__)

BROWSER_SESSIONS_DIR = "browser_sessions"
SESSION_FILE_EXTENSION = ".session"
#: Hard cap applied to the shared-files listing.
MAX_SHARED_FILES = 500

#: References to the background tasks started outside a request (keep-alive tab).
_background_tasks: Set[Any] = set()

#: One BrowserManager per project.  It owns the long-lived browser runtimes, so
#: constructing a fresh manager on every tool call would defeat the runtime
#: cache (and recreate the Docker manager on every action).
_MANAGERS: Dict[Tuple[str, str], "BrowserManager"] = {}
_MANAGERS_LOCK = threading.Lock()


def get_browser_manager(settings: CODXJuniorSettings) -> "BrowserManager":
    """Return the cached manager of a project (thread-safe)."""
    key = (
        str(getattr(settings, "codx_path", "") or ""),
        str(getattr(settings, "project_id", "") or ""),
    )
    with _MANAGERS_LOCK:
        manager = _MANAGERS.get(key)
        if manager is None:
            manager = BrowserManager(settings)
            _MANAGERS[key] = manager
        return manager


def _is_inside(path: str, base: str) -> bool:
    """Return True when *path* is inside *base* (both may be relative)."""
    try:
        return os.path.commonpath(
            [os.path.abspath(path), os.path.abspath(base)]
        ) == os.path.abspath(base)
    except ValueError:
        return False


def _spawn_background(coroutine) -> None:
    """
    Schedule *coroutine* on the running loop, keeping a reference until it ends.

    Used for work that must never block a request (creating the keep-alive tab).
    """
    task = asyncio.get_running_loop().create_task(coroutine)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


class BrowserManager:
    """
    Manages browser session lifecycle and persistence.

    Sessions are stored in the project's .codx/browser_sessions/ directory,
    mirroring the Workspace pattern.

    Folder structure:
        .codx/browser_sessions/
        ├── <session_id>/
        │   ├── <session_id>.session     (metadata)
        │   ├── chromium_profile/        (persistent profile, mounted at /config)
        │   │   ├── .config/chromium/Default/Preferences  (download directory)
        │   │   └── Downloads -> <mapped downloads folder>
        │   ├── cdp_proxy.py             (DevTools proxy, mounted read-only)
        │   ├── activity.jsonl           (user + AI audit trail)
        │   └── downloads/               (only when the project is not shared)
        └── ...

    When the project is shared, downloads go to the project folder configured for
    the session (``.codx/browser_downloads/<session_id>`` by default), so they are
    project files.

    Session metadata is also synchronized with Chat.meta_data["browser"].

    Responsibilities:
    - Create/list/get/stop/restart/delete browser sessions
    - Persist session state to Chat.meta_data
    - Docker container orchestration via DockerBrowserManager
    - Project folder mapping, download directory and shared files listing
    - Keep-alive tab and recovery of a browser whose window was closed
    - Activity auditing for user and AI actions
    """

    def __init__(self, settings: CODXJuniorSettings):
        """
        Initialize BrowserManager.

        Args:
            settings: CODXJuniorSettings instance
        """
        self.settings = settings
        self.sessions_path = os.path.join(settings.codx_path, BROWSER_SESSIONS_DIR)
        os.makedirs(self.sessions_path, exist_ok=True)

        traefik_domain = os.environ.get("CODX_JUNIOR_DOMAIN", "localhost")
        self.docker_manager = DockerBrowserManager(
            self.sessions_path,
            traefik_domain=traefik_domain,
            project_id=settings.project_id,
            project_root_path=getattr(settings, "abs_project_path", None),
            project_name=getattr(settings, "project_name", None),
        )
        # Persistent runtimes (one Playwright connection per session).
        self._runtimes: Dict[str, Any] = {}
        self._runtimes_guard = threading.Lock()
        self._cost_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        logger.debug("BrowserManager initialized at '%s'", self.sessions_path)

    # -------------------------------------------------------------------------
    # Path helpers
    # -------------------------------------------------------------------------

    def _session_folder_path(self, session_id: str) -> str:
        """Get folder path for session."""
        return os.path.join(self.sessions_path, session_id)

    def _session_file_path(self, session_id: str) -> str:
        """Get metadata file path for session (inside its folder)."""
        return os.path.join(
            self._session_folder_path(session_id),
            f"{session_id}{SESSION_FILE_EXTENSION}",
        )

    def _profile_folder(self, session_or_id) -> str:
        """
        Get the host folder of the Chromium profile.

        The docker manager binds this folder at ``/config`` inside the container,
        which is the browser's ``$HOME``: it holds the preferences Chromium reads
        at launch, including the download directory.
        """
        session_id = getattr(session_or_id, "id", session_or_id)
        return os.path.join(
            self._session_folder_path(session_id), download_settings.PROFILE_FOLDER
        )

    def _session_file_paths(self) -> List[str]:
        """Return all .session file paths for this project."""
        return [
            str(f)
            for f in Path(self.sessions_path).glob(f"*/*{SESSION_FILE_EXTENSION}")
            if f.is_file() and ".trash" not in f.parts
        ]

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    def list_sessions(self) -> List[BrowserSession]:
        """Return all browser sessions for this project."""
        sessions = []
        for file_path in self._session_file_paths():
            session = self._load_session_from_file(file_path)
            if session:
                sessions.append(session)
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """
        Return a single session by ID, or None if not found.

        Args:
            session_id: Session ID

        Returns:
            BrowserSession or None
        """
        if not session_id:
            return None
        file_path = self._session_file_path(session_id)
        if os.path.isfile(file_path):
            return self._load_session_from_file(file_path)
        # Fallback: scan all files (covers edge cases)
        return next((s for s in self.list_sessions() if s.id == session_id), None)

    def get_session_for_chat(self, chat_id: str) -> Optional[BrowserSession]:
        """
        Return the most recent session connected to a chat, or None.

        A session may be shared by several chats, so this matches any session
        whose ``chat_ids`` list contains *chat_id*.

        Args:
            chat_id: Chat ID

        Returns:
            BrowserSession or None
        """
        if not chat_id:
            return None
        return next((s for s in self.list_sessions() if s.has_chat(chat_id)), None)

    def create_session(
        self,
        name: str,
        chat_id: Optional[str] = None,
        initial_url: Optional[str] = None,
        description: Optional[str] = None,
        share_project: Optional[bool] = None,
        share_folders: Optional[List[Any]] = None,
        readonly: Optional[bool] = None,
        downloads_folder: Optional[str] = None,
        downloads_mount: Optional[str] = None,
        kind: str = "browser",
        os_version: Optional[str] = None,
        image: Optional[str] = None,
        image_provider: Optional[str] = None,
        library_item_id: Optional[str] = None,
        vnc_host: Optional[str] = None,
        vnc_port: Optional[int] = None,
        vnc_password: Optional[str] = None,
        vnc_public_url: Optional[str] = None,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        ssh_password: Optional[str] = None,
        guest_share_path: Optional[str] = None,
        control: Optional[str] = None,
        cpu_cores: Optional[int] = None,
        ram_size: Optional[str] = None,
        disk_size: Optional[str] = None,
        shm_size: Optional[str] = None,
        extra_env: Optional[Dict[str, str]] = None,
        desktop_width: Optional[int] = None,
        desktop_height: Optional[int] = None,
    ) -> BrowserSession:
        """
        Create and start a new browser session.

        Args:
            name: Human-readable session name given at creation.
            chat_id: Optional chat to connect to the session immediately.
            initial_url: Optional URL opened when the browser starts.
            description: Optional free-form description.
            share_project: Mount the project root at ``/home/<project_name>``.
                ``None`` mounts it only when no specific folder is listed.
            share_folders: Project folders mounted under
                ``/home/<project_name>/<folder>``. Each entry is a project
                relative path or a dict with folder/name/mount_path/readonly.
            readonly: Mount the listed folders read-only.
            downloads_folder: Project-relative folder receiving the downloads
                (default ``.codx/browser_downloads/<session_id>``).
            downloads_mount: Container path forcing a dedicated downloads mount.
            kind: ``browser`` (default), ``linux``, ``windows``, ``macos`` or
                ``remote``.  See :class:`BrowserSession`.
            os_version: OS release for VM images (Windows 11, macOS 15...).
            image: Docker image override (container kinds).
            image_provider: linuxserver, kasmweb or custom. Inferred from
                ``image`` when omitted.
            library_item_id: Start from a saved computer in the project library.
                The saved image/live-view/defaults take precedence over
                ``image``/``image_provider``.
            vnc_host: Remote VNC host (``remote`` kind; also inferred for VMs).
            vnc_port: Remote VNC port (default 5900).
            vnc_password: Remote VNC password.
            vnc_public_url: Optional viewer URL supplied by the user.
            ssh_host/ssh_port/ssh_user/ssh_key_path/ssh_password: Optional SSH
                endpoint used by ``run_command`` on remote sessions.
            guest_share_path: Where the shared folder appears in a VM guest.
            control: Force a control channel (normally inferred from ``kind``).
            cpu_cores: vCPUs for the machine (advanced settings).
            ram_size: RAM size for the machine, e.g. ``"8G"`` (advanced).
            disk_size: Disk size for a Windows/macOS VM image, e.g. ``"64G"``.
            shm_size: Docker shared memory for browser/Linux containers.
            extra_env: Extra environment variables passed to the image.
            desktop_width/desktop_height: Desktop/browser window size in pixels.

        Returns:
            Created BrowserSession

        Raises:
            RuntimeError: If container startup fails
            ValueError: If a folder is outside the project or missing
        """
        existing_sessions = self.list_sessions()
        if len(existing_sessions) >= self.docker_manager.MAX_SESSIONS:
            raise RuntimeError(
                f"Maximum number of browser sessions reached "
                f"({self.docker_manager.MAX_SESSIONS}); delete an old session first."
            )

        from codx.junior.browser.model import normalize_kind
        from codx.junior.computer.images import resolve_image
        from codx.junior.computer.library import (
            restore_profile,
            saved_library_for,
        )

        session_kind = normalize_kind(kind)
        image = (image or "").strip() or None
        image_provider = (image_provider or "").strip().lower() or None
        image_spec = None
        library_item = None
        library = None
        if library_item_id:
            library = saved_library_for(self)
            library_item = library.get(library_item_id)
            if not library_item:
                raise ValueError("Saved computer not found")
            if library_item.kind != "linux":
                raise ValueError(
                    f"Saved computer kind '{library_item.kind}' is not supported for new sessions"
                )
            session_kind = normalize_kind(library_item.kind)
            image = library_item.image
            image_provider = library_item.provider
            # Apply the saved resource/env shape only where the caller did not
            # provide an explicit value.
            defaults = library_item.defaults or {}
            cpu_cores = cpu_cores if cpu_cores is not None else defaults.get("cpu_cores")
            ram_size = ram_size if ram_size is not None else defaults.get("ram_size")
            disk_size = disk_size if disk_size is not None else defaults.get("disk_size")
            shm_size = shm_size if shm_size is not None else defaults.get("shm_size")
            desktop_width = desktop_width or defaults.get("desktop_width")
            desktop_height = desktop_height or defaults.get("desktop_height")
            extra_env = {
                **(defaults.get("extra_env") or {}),
                **(extra_env or {}),
            }
        elif session_kind == "linux":
            # Resolve before creating the record: the image decides the live
            # view (Selkies/KasmVNC), its port/scheme and the Docker profile.
            image_spec = resolve_image(
                image or os.environ.get("CODX_COMPUTER_LINUX_IMAGE"),
                provider=image_provider,
                kind=session_kind,
            )
            image = image_spec.image
        session = BrowserSession(
            name=name,
            description=(description or "").strip() or None,
            chat_ids=[chat_id] if chat_id else [],
            current_url=(initial_url or "").strip() or None,
            kind=session_kind,
            os_version=(os_version or "").strip() or None,
            image=(image or "").strip() or None,
            control=(control or "").strip().lower() or None,
            vnc_host=(vnc_host or "").strip() or None,
            vnc_port=int(vnc_port or 5900),
            vnc_password=vnc_password or None,
            vnc_public_url=(vnc_public_url or "").strip() or None,
            ssh_host=(ssh_host or "").strip() or None,
            ssh_port=int(ssh_port or 22),
            ssh_user=(ssh_user or "").strip() or None,
            ssh_key_path=(ssh_key_path or "").strip() or None,
            ssh_password=ssh_password or None,
            guest_share_path=(guest_share_path or "").strip() or None,
            cpu_cores=cpu_cores,
            ram_size=(ram_size or "").strip() or None,
            disk_size=(disk_size or "").strip() or None,
            shm_size=(shm_size or "").strip() or None,
            extra_env=extra_env or {},
            desktop_width=desktop_width or 1920,
            desktop_height=desktop_height or 1080,
        )
        if image_spec is not None:
            session.image = image_spec.image
            session.image_provider = image_spec.provider
            session.live_view = image_spec.live_view
            session.live_port = image_spec.live_port
            session.live_scheme = image_spec.live_scheme
            session.strip_prefix = image_spec.strip_prefix
            session.viewer_user = image_spec.viewer_user
            if image_spec.provider == "kasmweb" and not session.viewer_password:
                session.viewer_password = secrets.token_urlsafe(9)
        if library_item is not None:
            session.library_item_id = library_item.id
            session.library_item_name = library_item.name
            session.image = library_item.image
            session.image_provider = library_item.provider
            session.live_view = library_item.live_view
            session.live_port = library_item.live_port
            session.live_scheme = library_item.live_scheme
            session.strip_prefix = bool(library_item.strip_prefix)
            session.control = library_item.control or session.control
            session.viewer_user = library_item.viewer_user
            if (library_item.provider or "").lower() == "kasmweb" and not session.viewer_password:
                session.viewer_password = secrets.token_urlsafe(9)
        if session.ssh_host and "shell" not in (session.capabilities or []):
            session.capabilities = [*(session.capabilities or []), "shell"]
        if not session.name:
            session.name = f"{session.kind_label} {session.id[:8]}"

        session_folder = self._session_folder_path(session.id)
        os.makedirs(session_folder, exist_ok=True)

        if session.kind == "remote":
            if not session.vnc_host:
                raise ValueError("Remote computer sessions require vnc_host")
            session.status = "running"
            session.vnc_url = session.vnc_public_url
            session.engine = "remote"
            session.control = "vnc"
            session.mark_active()
            self._save_session_file(session)
            self.log_activity(
                session,
                actor="system",
                action="create",
                chat_id=chat_id,
                params={
                    "kind": "remote",
                    "vnc": f"{session.vnc_host}:{session.vnc_port}",
                    "ssh": session.ssh_host or None,
                },
            )
            return session

        # The project folders (and the downloads folder) must be mapped before
        # the container is created: docker run mounts them.
        self.docker_manager.configure_share(
            session,
            share_project=share_project,
            share_folders=share_folders,
            readonly=readonly,
            downloads_folder=downloads_folder,
            downloads_mount=downloads_mount,
        )

        if session.kind == "browser":
            # Chromium reads its download directory at launch, so the mapped
            # folder must reach the profile *before* the container is created.
            self._prepare_downloads(session)

        if library_item is not None and library_item.has_profile and library is not None:
            profile_path = self.docker_manager._desktop_profile_path(session.id)
            try:
                restore_profile(library_item, library, profile_path)
            except Exception:
                # Never leave a half-created session behind.
                self.delete_session(session.id)
                raise

        logger.info(
            "Creating %s session %s ('%s') for chat %s",
            session.kind, session.id[:8], session.name, chat_id,
        )

        # Start Docker container (browser or desktop/VM)
        session = self.docker_manager.start_container(session)

        # The keep-alive tab and the page recorder are ensured by the runtime
        # on its first connection: doing it here would open a second Playwright
        # connection (and add ~0.5 s) before the session is even returned.

        # Save session metadata to file
        self._save_session_file(session)
        self.log_activity(
            session,
            actor="system",
            action="create",
            chat_id=chat_id,
            params={
                "name": session.name,
                "initial_url": initial_url,
                "folders": [share.mount_path for share in session.shared_folders],
                "downloads": session.downloads_mount,
            },
            url=session.current_url,
            title=session.current_title,
        )
        return session

    def update_session(
        self,
        session_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        control: Optional[str] = None,
        vnc_host: Optional[str] = None,
        vnc_port: Optional[int] = None,
        vnc_password: Optional[str] = None,
        vnc_public_url: Optional[str] = None,
        ssh_host: Optional[str] = None,
        ssh_port: Optional[int] = None,
        ssh_user: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        ssh_password: Optional[str] = None,
        advanced: Optional[Dict[str, Any]] = None,
    ) -> Optional[BrowserSession]:
        """
        Update a session (name, connection and advanced settings) and persist it.

        ``vnc_password``/``ssh_password`` are changed when the field is not
        ``None``; pass ``""`` to clear them.  This lets a session be created
        first (e.g. a VM that needs to boot) and get its SSH endpoint later
        without recreating it.

        ``advanced`` holds the image/resource fields (``image``, ``cpu_cores``,
        ``ram_size``, ``disk_size``, ``shm_size``, ``extra_env``,
        ``desktop_width``/``desktop_height``).  Docker cannot change those on a
        running container: they take effect when the session is restarted
        (the container is recreated and the VM disk/profile is preserved).

        Returns:
            The updated BrowserSession, or None when not found.
        """
        session = self.get_session(session_id)
        if not session:
            return None
        if name is not None and str(name).strip():
            session.name = str(name).strip()
        if description is not None:
            session.description = str(description).strip() or None
        if control is not None and str(control).strip():
            from codx.junior.browser.model import CONTROL_MODES
            value = str(control).strip().lower()
            if value not in CONTROL_MODES:
                raise ValueError(f"control must be one of: {', '.join(CONTROL_MODES)}")
            session.control = value
        if vnc_host is not None:
            session.vnc_host = str(vnc_host).strip() or None
        if vnc_port is not None:
            session.vnc_port = int(vnc_port)
        if vnc_password is not None:
            session.vnc_password = str(vnc_password) or None
        if vnc_public_url is not None:
            session.vnc_public_url = str(vnc_public_url).strip() or None
        if ssh_host is not None:
            session.ssh_host = str(ssh_host).strip() or None
        if ssh_port is not None:
            session.ssh_port = int(ssh_port)
        if ssh_user is not None:
            session.ssh_user = str(ssh_user).strip() or None
        if ssh_key_path is not None:
            session.ssh_key_path = str(ssh_key_path).strip() or None
        if ssh_password is not None:
            session.ssh_password = str(ssh_password) or None
        if session.ssh_host and "shell" not in (session.capabilities or []):
            session.capabilities = [*(session.capabilities or []), "shell"]
        if advanced:
            session.apply_advanced_settings(advanced)
            if "image" in advanced:
                # Editing the image detaches the session from a saved-library
                # item; it should no longer be treated as a saved snapshot.
                session.library_item_id = None
                session.library_item_name = None
            if session.kind == "linux" and "image" in advanced:
                # The image decides the live-view transport (Selkies vs
                # KasmVNC): re-resolve it so a changed/cleared override does
                # not keep the previous provider's ports and scheme.
                from codx.junior.computer.images import resolve_image
                spec = resolve_image(
                    session.image or os.environ.get("CODX_COMPUTER_LINUX_IMAGE"),
                    kind="linux",
                )
                session.image = spec.image
                session.image_provider = spec.provider
                session.live_view = spec.live_view
                session.live_port = spec.live_port
                session.live_scheme = spec.live_scheme
                session.strip_prefix = spec.strip_prefix
                session.viewer_user = spec.viewer_user
                if spec.provider == "kasmweb":
                    session.viewer_password = session.viewer_password or secrets.token_urlsafe(9)
                else:
                    session.viewer_password = None
        session.mark_active()
        self._save_session_file(session)
        # Extra image env values can contain credentials: audit the names only.
        safe_advanced = {
            key: (sorted(value) if key == "extra_env" and isinstance(value, dict) else value)
            for key, value in (advanced or {}).items()
        }
        self.log_activity(
            session,
            actor="system",
            action="update",
            params={"name": session.name, **safe_advanced},
        )
        return session

    def save_session(self, session: BrowserSession) -> BrowserSession:
        """
        Create or update a session.

        Args:
            session: BrowserSession to save

        Returns:
            The saved session object
        """
        session_folder = self._session_folder_path(session.id)
        os.makedirs(session_folder, exist_ok=True)

        logger.debug("Saving session '%s'", session.id[:8])
        self._save_session_file(session)

        return session

    def connect_chat(self, session_id: str, chat_id: str) -> Optional[BrowserSession]:
        """
        Connect an additional chat to an existing session.

        Args:
            session_id: Session to connect the chat to.
            chat_id: Chat ID to connect.

        Returns:
            The updated BrowserSession, or None when the session is not found.
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning("connect_chat: session not found: %s", session_id)
            return None
        session.add_chat(chat_id)
        self._save_session_file(session)
        logger.info("Connected chat %s to session %s", chat_id, session.id[:8])
        return session

    def stop_session(self, session_id: str) -> Optional[BrowserSession]:
        """
        Stop a session's container but KEEP it so it can be restarted.

        Args:
            session_id: Session ID to stop

        Returns:
            The updated BrowserSession, or None when not found.
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning("stop_session: session not found: %s", session_id)
            return None

        self.forget_runtime(session_id)
        if session.kind != "remote":
            # VMs need a graceful shutdown so the guest disk is consistent;
            # browser/Linux containers keep the historic fast stop call.
            if session.kind in ("windows", "macos"):
                self.docker_manager.stop_container(session, remove=False, fast=False)
            else:
                self.docker_manager.stop_container(session, remove=False)
        else:
            session.status = "stopped"
        self._save_session_file(session)
        self.log_activity(session, actor="system", action="stop")
        logger.info("Stopped session %s", session_id[:8])
        return session

    def delete_session(self, session_id: str) -> None:
        """
        Stop container, remove it and delete the session folder.

        Args:
            session_id: Session ID to delete
        """
        session = self.get_session(session_id)
        if session:
            # Stop & remove Docker container (fast kill: no 10 s grace period)
            self.log_activity(session, actor="system", action="delete")
            if session.kind != "remote":
                self.docker_manager.stop_container(session, remove=True)
                logger.info("Stopped container for session %s", session_id[:8])

        self.forget_runtime(session_id)

        # Deleting a 100+ MB Chromium profile with shutil.rmtree() on the event
        # loop makes the whole API stutter.  Move it to .trash (same filesystem,
        # instant) and let the caller/background cleanup remove it.
        session_folder = self._session_folder_path(session_id)
        if os.path.isdir(session_folder):
            trash = os.path.join(self.sessions_path, ".trash")
            try:
                os.makedirs(trash, exist_ok=True)
                target = os.path.join(
                    trash, f"{session_id}-{int(time.time())}"
                )
                shutil.move(session_folder, target)
                logger.info("Moved session folder to trash: %s", session_id[:8])
                threading.Thread(
                    target=self._remove_trash_folder, args=(target,), daemon=True
                ).start()
            except Exception as e:
                logger.exception("Error moving session folder to trash: %s", e)

    # -------------------------------------------------------------------------
    # Project folder sharing
    # -------------------------------------------------------------------------

    def get_shared_paths(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the project/downloads mapping of a session.

        Args:
            session_id: Session ID

        Returns:
            Dict with ``session_id``, ``project_name``, ``home_path``,
            ``folders`` (list of share dicts), ``downloads_path``,
            ``downloads_folder``, ``downloads_mount`` and
            ``downloads_own_mount``; or None when the session does not exist.
        """
        session = self.get_session(session_id)
        if not session:
            return None
        return {
            "session_id": session.id,
            "project_name": session.project_name,
            "home_path": session.home_path,
            "folders": [share.to_dict() for share in session.shared_folders],
            "downloads_path": session.downloads_path,
            "downloads_folder": session.downloads_folder,
            "downloads_mount": session.downloads_mount,
            "downloads_own_mount": bool(session.downloads_own_mount),
        }

    def get_shared_files(self, session_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """
        List the files the browser saved in the session's downloads folder.

        The folder lives inside the project when the project is shared, so every
        entry can be read through the project files API.

        Args:
            session_id: Session ID
            limit: Maximum number of entries (newest first)

        Returns:
            List of dicts with ``name``, ``relative_path``, ``path``,
            ``container_path``, ``size`` and ``modified_at``.
        """
        session = self.get_session(session_id)
        if not session or not session.downloads_path:
            return []
        root = session.downloads_path
        if not os.path.isdir(root):
            return []

        project_root = getattr(self.settings, "abs_project_path", None)
        project_root = project_root if isinstance(project_root, str) and project_root else None
        downloads_mount = (session.downloads_mount or "").rstrip("/")

        files: List[Dict[str, Any]] = []
        for folder, _subfolders, names in os.walk(root):
            for name in names:
                full_path = os.path.join(folder, name)
                # Chromium keeps the partial download next to the final file
                if name.endswith(".crdownload"):
                    continue
                try:
                    stat = os.stat(full_path)
                except OSError:
                    continue
                relative = os.path.relpath(full_path, root).replace(os.sep, "/")
                if project_root and _is_inside(full_path, project_root):
                    path = os.path.relpath(full_path, project_root).replace(os.sep, "/")
                else:
                    path = full_path
                files.append({
                    "name": name,
                    "relative_path": relative,
                    "path": path,
                    "container_path": f"{downloads_mount}/{relative}" if downloads_mount else relative,
                    "size": int(stat.st_size),
                    "modified_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
                })

        files.sort(key=lambda entry: entry["modified_at"], reverse=True)
        return files[:max(1, min(int(limit or 200), MAX_SHARED_FILES))]

    # -------------------------------------------------------------------------
    # Chat integration
    # -------------------------------------------------------------------------

    def get_session_from_chat(self, chat: "Chat") -> Optional[BrowserSession]:
        """
        Load a browser session from Chat.meta_data.

        Args:
            chat: Chat object

        Returns:
            BrowserSession or None if not in chat metadata
        """
        if not getattr(chat, "meta_data", None) or "browser" not in chat.meta_data:
            return None

        try:
            session_data = chat.meta_data["browser"]
            return BrowserSession.from_dict(session_data)
        except Exception as e:
            logger.exception("Error loading session from chat: %s", e)
            return None

    def save_session_to_chat(self, session: BrowserSession, chat: "Chat") -> None:
        """
        Save session to Chat.meta_data["browser"] and connect the chat to it.

        Several chats can be connected to the same session: every call registers
        the chat in ``session.chat_ids`` (persisted to the session file) in
        addition to storing the session snapshot in the chat metadata.

        Args:
            session: BrowserSession to save
            chat: Chat to update
        """
        if getattr(chat, "meta_data", None) is None:
            chat.meta_data = {}

        # Register this chat as a consumer of the shared session
        if getattr(chat, "id", None):
            session.add_chat(chat.id)
            self._save_session_file(session)

        chat.meta_data["browser"] = session.to_public_dict()
        logger.debug("Saved session %s to chat %s", session.id[:8], chat.id)

    # -------------------------------------------------------------------------
    # Persistent runtimes
    # -------------------------------------------------------------------------

    async def get_runtime(self, session: BrowserSession):
        """Return (creating once) the persistent runtime of *session*.

        Browser sessions get a Playwright/``BrowserRuntime``; desktop sessions
        get a ``DesktopRuntime`` backed by ``docker exec`` (Linux) or RFB
        (Windows/macOS/remote).  Both are cached per session and expose the same
        ``run``/``close``/``loop`` surface used by the API and tools.
        """
        if getattr(self, "_runtimes_guard", None) is None:
            self._runtimes = {}
            self._runtimes_guard = threading.Lock()
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        with self._runtimes_guard:
            runtime = self._runtimes.get(session.id)
            stale_loop = (
                runtime is not None
                and getattr(runtime, "loop", None) is not None
                and current_loop is not None
                and runtime.loop is not current_loop
            )
            if runtime is None or getattr(runtime, "_closed", False) or stale_loop:
                if session.kind == "browser":
                    from codx.junior.browser.runtime import BrowserRuntime
                    runtime = BrowserRuntime(self, session)
                else:
                    from codx.junior.computer.runtime import DesktopRuntime
                    runtime = DesktopRuntime(self, session)
                runtime.loop = current_loop
                self._runtimes[session.id] = runtime
            return runtime

    async def warm_runtime(self, session: BrowserSession) -> None:
        """Connect the runtime in the background so human input is captured.

        A session created from the UI may be driven by the human before the AI
        says anything.  Connecting once here starts the page recorder and the
        1 s watcher, so those clicks appear in the activity trail immediately.
        """
        if session.kind != "browser":
            # Desktop backends connect lazily on the first action; there is no
            # page recorder that must be started in advance.
            return
        try:
            runtime = await self.get_runtime(session)
            await runtime.drain()
        except Exception as ex:
            logger.debug("Could not warm browser runtime %s: %s", str(session.id)[:8], ex)

    def peek_runtime(self, session_id: str):
        """Return the runtime without creating it (or None)."""
        return getattr(self, "_runtimes", {}).get(session_id)

    def forget_runtime(self, session_id: str) -> None:
        """Drop a session runtime and close it on the loop that owns it."""
        runtime = getattr(self, "_runtimes", {}).pop(session_id, None)
        if runtime is None:
            return
        loop = getattr(runtime, "loop", None)
        if loop is None or not loop.is_running():
            return
        try:
            current = asyncio.get_running_loop()
        except RuntimeError:
            current = None
        try:
            if current is loop:
                _spawn_background(runtime.close())
            elif loop.is_running():
                asyncio.run_coroutine_threadsafe(runtime.close(), loop)
        except RuntimeError:
            pass

    def _remove_trash_folder(self, path: str) -> None:
        """Delete a trashed session folder off the request path."""
        try:
            shutil.rmtree(path, ignore_errors=True)
            logger.info("Removed trashed session folder %s", path)
        except Exception as ex:
            logger.warning("Could not remove trashed session folder %s: %s", path, ex)

    # -------------------------------------------------------------------------
    # Browser connection + keep-alive tab
    # -------------------------------------------------------------------------

    async def connect_browser(self, session: BrowserSession) -> Browser:
        """
        Create a Browser instance, connect via CDP and prepare the shared page.

        Chromium exits when its last window is closed, which leaves the container
        running with a dead DevTools endpoint (the live view is still up but the
        browser window is gone).  A failed connection is therefore recovered once
        by restarting the browser process, so a session never stays unreachable,
        and the protected keep-alive tab is ensured on every connection.

        Args:
            session: BrowserSession with container info

        Returns:
            Connected Browser instance

        Raises:
            RuntimeError: If connection fails, even after the recovery attempt
        """
        browser = Browser(session, self.docker_manager)
        try:
            await browser.connect()
        except Exception as ex:
            if not session.container_id:
                raise
            logger.warning(
                "Browser of session %s is not reachable (%s); restarting it",
                str(session.id)[:8], ex,
            )
            try:
                await browser.close()
            except Exception:
                pass
            session = await asyncio.to_thread(self._restart_browser, session)
            browser = Browser(session, self.docker_manager)
            await browser.connect()

        await self._apply_downloads_path(browser, session)
        await self._ensure_keep_alive_tab(browser, session)
        return browser

    def _prepare_downloads(self, session: BrowserSession) -> Dict[str, Any]:
        """
        Anchor the session's download folder in the browser profile.

        ``Browser.setDownloadBehavior`` (used by :meth:`_apply_downloads_path`)
        is scoped to the DevTools client that sends it and Chromium drops it when
        that client disconnects — which happens on every tool call — and it never
        applies to a download the user starts in the live VNC view.  The mapping
        must therefore also be stored where Chromium reads it at launch:

        - ``download.default_directory`` (+ ``savefile``) in the profile
          ``Preferences``, without a "save as" prompt;
        - ``<HOME>/Downloads`` (inside ``/config``, the mounted profile) pointing
          at the mapped folder, so the browser fallback lands there too.

        Must be called *before* the container starts.  Best effort: a session
        whose profile cannot be written still works, it only keeps the
        per-connection CDP mapping.

        Args:
            session: Session whose ``downloads_mount`` becomes the browser's
                download folder.

        Returns:
            Dict[str, Any]: Report from ``download_settings`` (empty when there
            is nothing to map or the profile could not be written).
        """
        if not session or not session.downloads_mount:
            return {}
        try:
            report = download_settings.apply_download_settings(
                self._profile_folder(session.id), session.downloads_mount
            )
        except Exception as ex:
            logger.warning(
                "Could not set the download folder of session %s: %s",
                str(session.id)[:8], ex,
            )
            return {}
        if report.get("preferences"):
            logger.info(
                "Session %s download folder: %s (%d preference file(s), link: %s)",
                str(session.id)[:8],
                session.downloads_mount,
                len(report["preferences"]),
                report.get("symlink") or "-",
            )
        return report

    async def _apply_downloads_path(self, browser: Browser, session: BrowserSession) -> None:
        """
        Point the running browser to the session's mapped download folder.

        This is the *live* half of the mapping: while the connection is open it
        also covers a download started by the AI (and it wins over anything
        Playwright sets for its own context).  Chromium scopes
        ``Browser.setDownloadBehavior`` to the DevTools client that sends it, so
        the value is dropped when the connection closes — the durable half lives
        in the profile (see :meth:`_prepare_downloads`).

        Args:
            browser: Connected Browser instance.
            session: Session whose ``downloads_mount`` is applied.
        """
        download_path = (session.downloads_mount or "").strip()
        if not download_path or not getattr(browser, "browser", None):
            return
        try:
            cdp_session = await browser.browser.new_browser_cdp_session()
            # Keep a strong reference: a detached CDP session resets the
            # behaviour being set right below.
            browser.downloads_cdp_session = cdp_session
            await cdp_session.send(
                "Browser.setDownloadBehavior",
                {
                    "behavior": "allow",
                    "downloadPath": download_path,
                    "eventsEnabled": False,
                },
            )
            logger.info(
                "Browser downloads pointed to %s (session %s)",
                download_path, str(session.id)[:8],
            )
        except Exception as ex:
            logger.warning(
                "Could not point the browser downloads to %s: %s "
                "(the profile default written when the session was created still applies)",
                download_path, ex,
            )

    async def _ensure_keep_alive_tab(self, browser: Browser, session: BrowserSession) -> None:
        """
        Guarantee the protected tab that keeps the browser window alive.

        Best effort: a session without the tab still works, it is only less
        resilient to the user closing every tab.

        Args:
            browser: Connected Browser instance.
            session: Session the browser belongs to (used for logging).
        """
        try:
            await browser_tabs.ensure_keep_alive_tab(browser)
        except Exception as ex:
            logger.warning(
                "Could not ensure the keep-alive tab for session %s: %s",
                str(session.id)[:8], ex,
            )

    async def _ensure_keep_alive_tab_async(self, session: BrowserSession) -> Optional[Dict[str, Any]]:
        """Connect, ensure the protected tab and disconnect (helper coroutine)."""
        browser = await self.connect_browser(session)
        try:
            return await browser_tabs.ensure_keep_alive_tab(browser)
        finally:
            await browser.close()

    async def _open_keep_alive_tab_async(self, session: BrowserSession) -> Optional[Dict[str, Any]]:
        """Background variant of :meth:`_ensure_keep_alive_tab_async` (never raises)."""
        try:
            return await self._ensure_keep_alive_tab_async(session)
        except Exception as ex:
            logger.warning(
                "Could not create the keep-alive tab for session %s: %s",
                str(session.id)[:8], ex,
            )
            return None

    def _open_keep_alive_tab(self, session: BrowserSession) -> None:
        """
        Create the protected tab right after the browser is (re)started.

        Inside a request (there is a running loop) the work is scheduled in the
        background so the response is never blocked by a browser connection;
        without a loop it runs inline. Failures are only logged.
        """
        if not session or not session.container_id or not session.debug_url:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                run_coroutine_sync(lambda: self._ensure_keep_alive_tab_async(session))
            except Exception as ex:
                logger.warning(
                    "Could not create the keep-alive tab for session %s: %s",
                    str(session.id)[:8], ex,
                )
            return
        _spawn_background(self._open_keep_alive_tab_async(session))

    def _restart_browser(self, session: BrowserSession, reason: str = "recover") -> BrowserSession:
        """
        Restart the browser process of a session (blocking: runs in a thread).

        Stopping and starting the container runs the entrypoint again, which
        relaunches Chromium with the mounted profile (cookies and logins are
        preserved) and exposes a new DevTools endpoint.

        Args:
            session: Session whose browser must be restarted.
            reason: Audit action recorded in the activity log.

        Returns:
            The updated BrowserSession (new ``debug_url``).
        """
        logger.warning("Restarting session %s (%s)", str(session.id)[:8], reason)
        if session.kind == "browser":
            # Chromium rewrites Preferences when it exits: re-assert the mapped
            # downloads folder so the relaunched browser keeps it.
            self._prepare_downloads(session)
        if session.kind in ("windows", "macos"):
            self.docker_manager.stop_container(session, remove=False, fast=False)
        else:
            self.docker_manager.stop_container(session, remove=False)
        session = self.docker_manager.restart_container(session)
        self._save_session_file(session)
        self.log_activity(session, actor="system", action=reason)
        return session

    async def restart_session(self, session_id: str) -> Optional[BrowserSession]:
        """
        Restart a session's browser (preserves the Chromium profile).

        The container is stopped and started again so the entrypoint relaunches
        Chromium. This is also the recovery path for a session whose window was
        closed by the user: Chromium exits when its last tab is closed, leaving
        the container alive with a dead DevTools endpoint.

        Args:
            session_id: Session ID to restart

        Returns:
            Updated BrowserSession, or None when not found.

        Raises:
            RuntimeError: If restart fails
        """
        session = self.get_session(session_id)
        if not session:
            return None
        if session.kind == "remote":
            runtime = self.peek_runtime(session_id)
            if runtime is not None:
                await runtime.close()
                getattr(self, "_runtimes", {}).pop(session_id, None)
            session.status = "running"
            session.mark_active()
            self._save_session_file(session)
            return session

        logger.info("Restarting session %s", session_id[:8])
        runtime = self.peek_runtime(session_id)
        if runtime is not None:
            await runtime.close()
            getattr(self, "_runtimes", {}).pop(session_id, None)
        session = await asyncio.to_thread(self._restart_browser, session, "restart")
        # The runtime re-creates the keep-alive tab (and the recorder) on its
        # next connection; doing it here would open a second Playwright
        # connection and race the first AI action.
        return session

    # -------------------------------------------------------------------------
    # Activity audit + cost summary
    # -------------------------------------------------------------------------

    def _activity_log(self, session_or_id) -> BrowserActivityLog:
        """Return the activity log for a session object or id."""
        session_id = getattr(session_or_id, "id", session_or_id)
        return BrowserActivityLog(self._session_folder_path(session_id))

    def log_activity(
        self,
        session,
        *,
        actor: str,
        action: str,
        chat_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None,
        title: Optional[str] = None,
        success: bool = True,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        result: Any = None,
    ) -> Dict[str, Any]:
        """
        Append an audit entry for a user/AI action on a browser session.

        The session's cached last-action fields are updated as a side effect.
        """
        session_id = getattr(session, "id", session)
        if session and not isinstance(session, str):
            session.mark_action(action)
            self._save_session_file(session)
        entry = self._activity_log(session_id).record(
            session_id=session_id,
            chat_id=chat_id,
            actor=actor,
            action=action,
            params=params,
            url=url or getattr(session, "current_url", None),
            title=title or getattr(session, "current_title", None),
            success=success,
            duration_ms=duration_ms,
            error=error,
            result=result,
        )
        # Invalidate the cost cache: chat usage changes while the user works.
        if getattr(self, "_cost_cache", None) is not None:
            self._cost_cache.pop(session_id, None)
        # Live UI (no 7 s polling).  Best effort by design.
        browser_events.broadcast_activity(session_id, entry)
        return entry

    def get_activity(self, session_id: str, limit: int = 100) -> list:
        """Return the most recent activity entries for a session."""
        return self._activity_log(session_id).read(limit=limit)

    def get_cost_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Return the AI cost/usage summary for every chat connected to a session.

        ``Chat.cost`` is the source of truth for the accumulated chat cost.  We
        also include the token/tool usage recorded by analytics for the same
        chats when available, so the UI can show both the budget and the actual
        traffic breakdown.

        Returns:
            Dict with ``session_id``, ``chats`` (per-chat rows) and totals.
        """
        cache = getattr(self, "_cost_cache", None)
        if cache is None:
            cache = self._cost_cache = {}
        cached = cache.get(session_id)
        if cached and time.monotonic() - cached[0] < 30:
            return cached[1]
        session = self.get_session(session_id)
        if not session:
            return {
                "session_id": session_id,
                "chats": [],
                "total_cost_cxjcoins": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_llm_calls": 0,
                "total_tool_calls": 0,
            }

        from codx.junior.chat_manager import ChatManager

        chat_manager = ChatManager(self.settings)
        rows = []
        total_cost = 0.0
        total_input = 0
        total_output = 0
        total_calls = 0
        total_tools = 0

        analytics = None
        try:
            from codx.junior.analytics.analytics import Analytics
            analytics = Analytics()
        except Exception as ex:
            logger.debug("Analytics not available for browser cost summary: %s", ex)

        for chat_id in session.chat_ids:
            try:
                chat = chat_manager.find_by_id(chat_id)
            except Exception as ex:
                logger.warning("Could not load chat %s for cost summary: %s", chat_id, ex)
                chat = None
            cost = float(getattr(chat, "cost", 0.0) or 0.0) if chat else 0.0
            estimation = getattr(chat, "estimation_cost", None) if chat else None
            input_tokens = 0
            output_tokens = 0
            llm_calls = 0
            tool_calls = 0
            if analytics and chat:
                try:
                    context = analytics.get_chat_with_requests(chat_id=chat_id)
                    requests = context.get("llm_requests") or []
                    tools = context.get("tool_calls") or []
                    llm_calls = len(requests)
                    tool_calls = len(tools)
                    input_tokens = sum(int(getattr(r, "input_tokens", 0) or 0) for r in requests)
                    output_tokens = sum(int(getattr(r, "output_tokens", 0) or 0) for r in requests)
                except Exception as ex:
                    logger.debug("Could not read analytics for chat %s: %s", chat_id, ex)

            rows.append({
                "chat_id": chat_id,
                "chat_name": getattr(chat, "name", None) if chat else None,
                "cost_cxjcoins": round(cost, 6),
                "estimation_cost_cxjcoins": estimation,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "llm_calls": llm_calls,
                "tool_calls": tool_calls,
            })
            total_cost += cost
            total_input += input_tokens
            total_output += output_tokens
            total_calls += llm_calls
            total_tools += tool_calls

        summary = {
            "session_id": session.id,
            "chats": rows,
            "total_cost_cxjcoins": round(total_cost, 6),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_llm_calls": total_calls,
            "total_tool_calls": total_tools,
            "window": "all-time",
        }
        cache[session_id] = (time.monotonic(), summary)
        return summary

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def cleanup_all_sessions(self) -> None:
        """
        Stop all containers and cleanup (called on shutdown).
        """
        logger.info("Cleaning up all browser sessions")
        self.docker_manager.cleanup_all_containers()

    # -------------------------------------------------------------------------
    # Private
    # -------------------------------------------------------------------------

    def _save_session_file(self, session: BrowserSession) -> None:
        """Save session metadata to file (atomic replace)."""
        session_folder = self._session_folder_path(session.id)
        os.makedirs(session_folder, exist_ok=True)

        file_path = self._session_file_path(session.id)
        try:
            tmp_path = f"{file_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(session.to_json())
            os.replace(tmp_path, file_path)
            # The record may hold VNC/SSH passwords: keep it private.
            try:
                os.chmod(file_path, 0o600)
            except OSError:
                pass
            logger.debug("Saved session metadata: %s", session.id[:8])
        except Exception as e:
            logger.exception("Error saving session file: %s", e)

    def _load_session_from_file(self, file_path: str) -> Optional[BrowserSession]:
        """Load and deserialize a session from a JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
            return BrowserSession.from_dict(data)
        except Exception as e:
            logger.exception("Error loading session from '%s': %s", file_path, e)
            return None

#: The generic names used by the computer-session API and tools.  The original
#: ``BrowserManager``/``get_browser_manager`` names stay as aliases so every
#: existing import, chat record and test keeps working.
ComputerManager = BrowserManager
get_computer_manager = get_browser_manager
