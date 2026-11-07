"""
BrowserManager — CRUD operations for browser sessions.

Manages session lifecycle: create, read, update, delete.
Handles persistence in Chat.meta_data and Docker container management.

Follows the workspace pattern:
    .codx/browser_sessions/<session_id>/<session_id>.session

A session is created with a human-readable ``name`` and may be shared by several
chats (``session.chat_ids``).  The container is a Chromium instance with a live
VNC view (for the user) and a CDP endpoint (for the AI), so both actors control
the same browser page.

Lifecycle primitives
--------------------
- ``create_session(name, chat_id, initial_url, description)`` : start a new container + persist metadata.
- ``stop_session(session_id)``      : stop the container but KEEP it (restartable).
- ``restart_session(session_id)``   : start an existing/recreate a stopped session.
- ``delete_session(session_id)``    : stop the container, remove it and the folder.
- ``log_activity(...)``             : append an audit entry for a user/AI action.
"""

import logging
import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from codx.junior.settings import CODXJuniorSettings
from codx.junior.browser.model import BrowserSession
from codx.junior.browser.docker_browser_manager import DockerBrowserManager
from codx.junior.browser.browser import Browser
from codx.junior.browser.activity import BrowserActivityLog

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
        │   ├── chromium_profile/        (persistent profile)
        │   ├── cdp_proxy.py             (DevTools proxy, mounted read-only)
        │   └── activity.jsonl           (user + AI audit trail)
        └── ...

    Session metadata is also synchronized with Chat.meta_data["browser"].

    Responsibilities:
    - Create/list/get/stop/restart/delete browser sessions
    - Persist session state to Chat.meta_data
    - Docker container orchestration via DockerBrowserManager
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
            f"{session_id}{SESSION_FILE_EXTENSION}",
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
    ) -> BrowserSession:
        """
        Create and start a new browser session.

        Args:
            name: Human-readable session name given at creation.
            chat_id: Optional chat to connect to the session immediately.
            initial_url: Optional URL opened when the browser starts.
            description: Optional free-form description.

        Returns:
            Created BrowserSession

        Raises:
            RuntimeError: If container startup fails
        """
        existing_sessions = self.list_sessions()
        if len(existing_sessions) >= self.docker_manager.MAX_SESSIONS:
            raise RuntimeError(
                f"Maximum number of browser sessions reached "
                f"({self.docker_manager.MAX_SESSIONS}); delete an old session first."
            )

        session = BrowserSession(
            name=name,
            description=(description or "").strip() or None,
            chat_ids=[chat_id] if chat_id else [],
            current_url=(initial_url or "").strip() or None,
        )
        if not session.name:
            session.name = f"Browser {session.id[:8]}"

        session_folder = self._session_folder_path(session.id)
        os.makedirs(session_folder, exist_ok=True)

        logger.info(
            "Creating browser session %s ('%s') for chat %s",
            session.id[:8], session.name, chat_id,
        )

        # Start Docker container
        session = self.docker_manager.start_container(session)

        # Save session metadata to file
        self._save_session_file(session)
        self.log_activity(
            session,
            actor="system",
            action="create",
            chat_id=chat_id,
            params={"name": session.name, "initial_url": initial_url},
            url=session.current_url,
            title=session.current_title,
        )
        return session

    def update_session(self, session_id: str, name: Optional[str] = None) -> Optional[BrowserSession]:
        """
        Rename a session and persist it.

        Args:
            session_id: Session to update.
            name: New human-readable name (None keeps the current one).

        Returns:
            The updated BrowserSession, or None when not found.
        """
        session = self.get_session(session_id)
        if not session:
            return None
        if name is not None and str(name).strip():
            session.name = str(name).strip()
        session.mark_active()
        self._save_session_file(session)
        self.log_activity(session, actor="system", action="rename", params={"name": session.name})
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

        self.docker_manager.stop_container(session, remove=False)
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
            # Stop & remove Docker container
            self.log_activity(session, actor="system", action="delete")
            self.docker_manager.stop_container(session, remove=True)
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

    async def restart_session(self, session_id: str) -> Optional[BrowserSession]:
        """
        Restart a stopped session (preserves profile).

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

        logger.info("Restarting session %s", session_id[:8])
        session = self.docker_manager.restart_container(session)
        self._save_session_file(session)
        self.log_activity(
            session,
            actor="system",
            action="restart",
            url=session.current_url,
            title=session.current_title,
        )
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
        return self._activity_log(session_id).record(
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

        return {
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