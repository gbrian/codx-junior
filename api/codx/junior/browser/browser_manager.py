"""
BrowserManager — CRUD operations for browser sessions.

Manages session lifecycle: create, read, update, delete.
Handles persistence in Chat.meta_data and Docker container management.

Follows the workspace pattern:
    .codx/browser_sessions/<session_id>/<session_id>.session
"""

import logging
import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from codx.junior.settings import CODXJuniorSettings
from codx.junior.browser.model import BrowserSession
from codx.junior.browser.docker_firefox_manager import DockerFirefoxManager
from codx.junior.browser.browser import Browser

logger = logging.getLogger(__name__)

BROWSER_SESSIONS_DIR = "browser_sessions"
SESSION_FILE_EXTENSION = ".session"


class BrowserManager:
    """
    Manages browser session lifecycle and persistence.

    Sessions are stored in the project's .codx/browser_sessions/ directory,
    mirroring the Workspace pattern.

    Folder structure:
        .codx/browser_sessions/
        ├── <session_id>/
        │   ├── <session_id>.session     (metadata)
        │   └── firefox_profile/         (persistent profile)
        └── ...

    Session metadata is also synchronized with Chat.meta_data["browser"].

    Responsibilities:
    - Create/list/get/delete browser sessions
    - Persist session state to Chat.meta_data
    - Docker container orchestration via DockerFirefoxManager
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
        self.docker_manager = DockerFirefoxManager(
            self.sessions_path,
            traefik_domain=traefik_domain
        )
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
            f"{session_id}{SESSION_FILE_EXTENSION}"
        )

    def _session_file_paths(self) -> List[str]:
        """Return all .session file paths for this project."""
        return [
            str(f)
            for f in Path(self.sessions_path).glob(f"*/*{SESSION_FILE_EXTENSION}")
            if f.is_file()
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
        file_path = self._session_file_path(session_id)
        if os.path.isfile(file_path):
            return self._load_session_from_file(file_path)
        # Fallback: scan all files (covers edge cases)
        return next((s for s in self.list_sessions() if s.id == session_id), None)

    def create_session(self, chat_id: str) -> BrowserSession:
        """
        Create and start a new browser session.

        Args:
            chat_id: Associated chat ID (for logging)

        Returns:
            Created BrowserSession

        Raises:
            RuntimeError: If container startup fails
        """
        session = BrowserSession(chat_id=chat_id)
        session_folder = self._session_folder_path(session.id)
        os.makedirs(session_folder, exist_ok=True)

        logger.info("Creating browser session %s for chat %s", session.id[:8], chat_id)

        # Start Docker container
        session = self.docker_manager.start_container(session)

        # Save session metadata to file
        self._save_session_file(session)

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

        logger.info("Saving session '%s'", session.id[:8])
        self._save_session_file(session)

        return session

    def delete_session(self, session_id: str) -> None:
        """
        Stop container and remove session.

        Args:
            session_id: Session ID to delete
        """
        session = self.get_session(session_id)
        if session:
            # Stop Docker container
            self.docker_manager.stop_container(session)
            logger.info("Stopped container for session %s", session_id[:8])

        # Remove session folder
        session_folder = self._session_folder_path(session_id)
        if os.path.isdir(session_folder):
            import shutil
            try:
                shutil.rmtree(session_folder)
                logger.info("Deleted session folder: %s", session_id[:8])
            except Exception as e:
                logger.exception("Error deleting session folder: %s", e)

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
        if not chat.meta_data or "browser" not in chat.meta_data:
            return None

        try:
            session_data = chat.meta_data["browser"]
            return BrowserSession.from_dict(session_data)
        except Exception as e:
            logger.exception("Error loading session from chat: %s", e)
            return None

    def save_session_to_chat(self, session: BrowserSession, chat: "Chat") -> None:
        """
        Save session to Chat.meta_data["browser"].

        Args:
            session: BrowserSession to save
            chat: Chat to update
        """
        if not chat.meta_data:
            chat.meta_data = {}

        chat.meta_data["browser"] = session.to_dict()
        logger.debug("Saved session %s to chat %s", session.id[:8], chat.id)

    # -------------------------------------------------------------------------
    # Browser connection
    # -------------------------------------------------------------------------

    async def connect_browser(self, session: BrowserSession) -> Browser:
        """
        Create a Browser instance and connect via CDP.

        Args:
            session: BrowserSession with container info

        Returns:
            Connected Browser instance

        Raises:
            RuntimeError: If connection fails
        """
        browser = Browser(session, self.docker_manager)
        await browser.connect()
        return browser

    async def restart_session(self, session_id: str) -> BrowserSession:
        """
        Restart a stopped session (preserves profile).

        Args:
            session_id: Session ID to restart

        Returns:
            Updated BrowserSession

        Raises:
            RuntimeError: If restart fails
        """
        session = self.get_session(session_id)
        if not session:
            raise RuntimeError(f"Session not found: {session_id}")

        logger.info("Restarting session %s", session_id[:8])
        session = self.docker_manager.restart_container(session)
        self._save_session_file(session)
        return session

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
        """Save session metadata to file."""
        session_folder = self._session_folder_path(session.id)
        os.makedirs(session_folder, exist_ok=True)

        file_path = self._session_file_path(session.id)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(session.to_json())
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