"""
Chat + AI
This module is responsible for chat persistence and management.

Besides the classic full-chat ``save_chat``, this module now exposes granular,
merge-safe message operations (``add_message``, ``update_message``,
``remove_message``) used to persist chat changes *during* an AI turn (e.g.
tool-usage notification messages, streamed partial responses) without
overwriting concurrent updates.

It also provides full-text search capabilities via the ``search_chats`` method,
delegating to the ``ChatSearcher`` class for filtering by time frame, keyword
matching, and pagination.

Merge strategy (per message, keyed by ``doc_id``):

    ```mermaid
    flowchart TD
        A[Incoming chat messages] --> C{doc_id exists in stored chat?}
        B[Stored chat messages] --> C
        C -->|No| D[Keep message]
        C -->|Yes| E{parse incoming.updated_at >= parse stored.updated_at?}
        E -->|Yes| F[Keep incoming]
        E -->|No| G[Keep stored]
        D --> H[Merged message list]
        F --> H
        G --> H
    ```

CHANGED — timestamp normalisation:
    ``updated_at`` values historically exist in TWO formats:
    ``str(datetime.now())`` (space separator, Message default) and
    ``datetime.isoformat()`` (T separator, stamped by add/update_message).
    Comparing them as raw strings is WRONG ("...T..." always beats "... ..."
    lexicographically for the same day). :func:`_parse_timestamp` parses both
    formats so the last-writer-wins decision uses real datetimes.

CHANGED — persist hot-path:
    The granular operations are now called frequently mid-run (tool events,
    throttled stream persists). :meth:`ChatManager._load_stored_chat` reads
    the chat directly from ``chat.file_path`` when possible instead of
    scanning the whole tasks tree via ``find_by_id``.

NEW — chat search:
    The :meth:`ChatManager.search_chats` method provides full-text search
    across all chat data with optional time-frame filtering, user filtering,
    and pagination, delegating to :class:`codx.junior.chat_searcher.ChatSearcher`.

NEW — chat filtering:
    The :meth:`ChatManager.get_recent_chats` method now supports filtering by
    user_id, board, column, and chat_type (task or chat).

CHANGED — project_ids filtering:
    The :meth:`ChatManager.search_chats` method now supports filtering by
    project_ids list. When no query is provided, returns latest chats from
    accessible user projects.

CHANGED — chat ID validation:
    The :meth:`ChatManager.load_chat_from_path` method now ensures all loaded
    chats have a valid ID. Missing IDs are extracted from the filename or
    generated fresh, guaranteeing no chat is returned without an ID.

CHANGED — time-range filtering:
    :meth:`ChatManager.chat_paths` and :meth:`ChatManager.list_chats` now
    accept an optional **upper bound** (``before_update`` / ``to_date``) in
    addition to the existing lower bound (``last_update`` / ``from_date``),
    enabling an explicit ``[from_date, to_date]`` window. Both bounds are
    applied against the chat file ``mtime``. When a bound is ``None`` it is
    ignored, so existing callers are unaffected.

NEW — accumulated chat cost (``Chat.cost``):
    ``Chat.cost`` accumulates the cxjcoins spent on a chat. It is updated here
    whenever a message carrying a cost is added or updated, using the persisted
    version of that message as the baseline (so a cost registered *after* the
    message was first persisted is still captured exactly once). The value is
    MONOTONIC — deleting a message never reduces it — so the chat budget stays
    accurate even when messages are removed.

NEW — chat status history (``Chat.status_history``):
    ``Chat.status`` was previously a single mutable field ("last writer wins"),
    making it impossible to reconstruct when a task moved between statuses. This
    module now appends a :class:`codx.junior.db.ChatStatusEvent` to
    ``Chat.status_history`` every time ``status`` actually changes (detected in
    :meth:`ChatManager.save_chat` via :meth:`ChatManager._register_status_change`).
    The log is append-only and merge-safe (dedup by ``doc_id``), giving future
    task-performance metrics (cycle time, throughput, error rate) the raw
    transition feed they need.
"""
import logging
import pathlib
import os
import json
import uuid
import shutil

from slugify import slugify

from typing import Dict, List, Optional, Any

from datetime import datetime, timedelta
from codx.junior.settings import CODXJuniorSettings

from codx.junior.db import Chat, Message, ChatStatusEvent

from codx.junior.profiling.profiler import profile_function

from codx.junior.chat.chat_export import ChatExport, ExportedDocument

from codx.junior.events.event_manager import EventManager

from codx.junior.project.project_discover import find_project_by_id

logger = logging.getLogger(__name__)

DEFAULT_BOARD = "kanban"
DEFAULT_COLUMN = "tasks"


def _parse_timestamp(value: Optional[str]) -> datetime:
    """
    Parse a message timestamp that may be in either historical format.

    Handles both ``datetime.isoformat()`` ("2023-10-01T12:00:00") and
    ``str(datetime.now())`` ("2023-10-01 12:00:00") — ``fromisoformat``
    accepts both separators. Unparseable/missing values sort OLDEST so a
    real timestamp always wins over a missing one.

    :param value: Raw timestamp string (may be None/empty/invalid).
    :return: Parsed datetime, or ``datetime.min`` when unparseable.
    """
    if not value:
        return datetime.min
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        logger.debug("Unparseable message timestamp: '%s'", value)
        return datetime.min


def _extract_id_from_filename(file_path: str) -> Optional[str]:
    """
    Extract chat ID from filename.

    Chat files follow the pattern: {slugified_name}.{uuid}.json
    This function extracts the UUID part.

    :param file_path: Full path to the chat file.
    :return: Extracted UUID or None if pattern doesn't match.
    """
    try:
        filename = os.path.basename(file_path)
        # Remove .json extension
        name_without_ext = filename.replace('.json', '').replace('.yaml', '')
        # Split by '.' and take the last part (should be the UUID)
        parts = name_without_ext.split('.')
        if len(parts) >= 2:
            potential_id = parts[-1]
            # Validate it looks like a UUID (36 chars with hyphens)
            if len(potential_id) == 36 and potential_id.count('-') == 4:
                return potential_id
    except Exception as ex:
        logger.warning("Failed to extract ID from filename '%s': %s", file_path, ex)
    return None


class ChatManager:
    """
    Manages chat persistence and retrieval for a given project.

    Provides full-chat save/load operations as well as granular, merge-safe
    message operations (``add_message``, ``update_message``, ``remove_message``)
    that are safe to call while an AI turn is in progress.

    Also provides full-text search via ``search_chats`` with user filtering,
    project_ids filtering, time-frame filtering and pagination support.

    Contract relied upon by :class:`codx.junior.chat.chat_event_bridge.ChatEventBridge`:
        * ``add_message`` inserts (idempotent: skips in-memory duplicate by ``doc_id``).
        * ``update_message`` matches by ``doc_id`` (appends if missing).
        * Both merge against the stored chat so concurrent updates are never lost.

    Contract relied upon for the chat budget:
        * ``add_message`` / ``update_message`` accumulate ``message.cost`` into
          ``chat.cost`` (monotonic). ``remove_message`` never reduces
          ``chat.cost``, so deleted messages still count towards the budget.

    Contract relied upon for task-performance metrics:
        * Every real ``Chat.status`` transition is appended to
          ``Chat.status_history`` by :meth:`save_chat` (via
          :meth:`_register_status_change`), producing an append-only,
          merge-safe transition log.
    """

    def __init__(self, settings: CODXJuniorSettings, event_manager: Optional[EventManager] = None):
        """
        Initialise the manager, creating the required directory structure.

        :param settings: Project-level settings.
        :param event_manager: Optional shared EventManager; a new one is
            created if not supplied.
        """
        self.settings = settings
        self.chat_path = f"{settings.codx_path}/tasks"
        self.event_manager = (
            event_manager if event_manager else EventManager(codx_path=settings.codx_path)
        )
        os.makedirs(self.chat_path, exist_ok=True)
        os.makedirs(f"{self.chat_path}/{DEFAULT_BOARD}/{DEFAULT_COLUMN}", exist_ok=True)

    # -------------------------------------------------------------------------
    # Path helpers
    # -------------------------------------------------------------------------

    def get_chat_file(self, chat: Chat) -> str:
        """
        Build the canonical file path for *chat*.

        :param chat: Chat whose path to compute.
        :return: Absolute file path string.
        """
        return (
            f"{self.chat_path}/{chat.board}/{chat.column}"
            f"/{slugify(chat.name)}.{chat.id}.json"
        )

    def chat_paths(
        self,
        last_update: Optional[datetime] = None,
        before_update: Optional[datetime] = None,
    ) -> List[str]:
        """
        Return chat file paths, optionally filtering by last update time.

        CHANGED — time-range support:
            An optional upper bound ``before_update`` was added so callers can
            request an explicit ``[last_update, before_update]`` window. Both
            bounds are compared against the chat file ``mtime``. A ``None``
            bound is ignored, preserving the previous behavior.

        :param last_update: Only return paths for chats updated **after** this
            date (exclusive lower bound).
        :param before_update: Only return paths for chats updated **on or
            before** this date (inclusive upper bound).
        :return: List of file paths.
        """
        all_paths = (
            [str(p) for p in pathlib.Path(self.chat_path).rglob("*.yaml")]
            + [str(p) for p in pathlib.Path(self.chat_path).rglob("*.json")]
        )

        if last_update:
            all_paths = [
                path for path in all_paths
                if datetime.fromtimestamp(os.path.getmtime(path)) > last_update
            ]

        if before_update:
            all_paths = [
                path for path in all_paths
                if datetime.fromtimestamp(os.path.getmtime(path)) <= before_update
            ]

        return all_paths

    def chat_board_column_name_from_path(
        self, file_path: str
    ) -> tuple:
        """
        Parse board, column and name from a chat file path.

        :param file_path: Absolute path to a chat file.
        :return: Tuple of (board, column, name) or (None, None, None).
        """
        chat_parts = file_path.replace(self.chat_path, "").split("/")[1:]
        if len(chat_parts) != 3:
            return None, None, None

        name = chat_parts[-1].replace(".md", "")
        column = chat_parts[-2]
        board = chat_parts[-3]
        return board, column, name

    # -------------------------------------------------------------------------
    # Chat listing
    # -------------------------------------------------------------------------

    def get_recent_chats(
        self,
        user_id: Optional[str] = None,
        board: Optional[str] = None,
        column: Optional[str] = None,
        chat_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Get recent chats with optional filtering and pagination.

        Loads all chats and filters by user, board, column, and/or chat type
        (if provided), then sorts by recency and paginates.

        :param user_id: Optional user ID to filter chats (only chats where
            user created or participated). If None, returns all recent chats.
        :param board: Optional board name filter.
        :param column: Optional column name filter.
        :param chat_type: Optional chat type filter ('task' or 'chat').
        :param page: Page number (1-indexed).
        :param page_size: Number of results per page.
        :return: Dict with paginated results and metadata.
        """
        all_chats = self.list_chats()

        # Apply filters
        filtered_chats = all_chats
        
        if user_id:
            filtered_chats = [
                chat for chat in filtered_chats
                if self._user_involved_in_chat(chat, user_id)
            ]
        
        if board:
            filtered_chats = [
                chat for chat in filtered_chats
                if chat.board and chat.board.lower() == board.lower()
            ]
        
        if column:
            filtered_chats = [
                chat for chat in filtered_chats
                if chat.column and chat.column.lower() == column.lower()
            ]
        
        if chat_type:
            filtered_chats = [
                chat for chat in filtered_chats
                if self._matches_chat_type(chat, chat_type)
            ]

        # Sort by recency (updated_at descending)
        sorted_chats = sorted(
            filtered_chats,
            key=lambda c: _parse_timestamp(c.updated_at),
            reverse=True,
        )

        # Calculate pagination
        total = len(sorted_chats)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        paginated_chats = sorted_chats[start_idx:end_idx]

        return {
            "chats": paginated_chats,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    @staticmethod
    def _user_involved_in_chat(chat: Chat, user_id: str) -> bool:
        """
        Check if a user is involved in a chat (created, participated, or mentioned).

        :param chat: The chat to check.
        :param user_id: The user ID to look for.
        :return: True if user is involved in chat.
        """
        if not chat or not user_id:
            return False

        # Check if user created the chat
        if chat.created_by == user_id:
            return True

        # Check if user is in profiles
        if chat.profiles and isinstance(chat.profiles, list):
            if any(p and (p.get("id") == user_id or p.get("user_id") == user_id) for p in chat.profiles):
                return True

        # Check if user has messages in chat
        if chat.messages and isinstance(chat.messages, list):
            if any(m and (m.created_by == user_id or m.user_id == user_id) for m in chat.messages):
                return True

        return False

    @staticmethod
    def _matches_chat_type(chat: Chat, chat_type: str) -> bool:
        """
        Check if a chat matches the specified type.

        :param chat: The chat to check.
        :param chat_type: The type to match ('task' or 'chat').
        :return: True if chat matches the type.
        """
        if not chat or not chat_type:
            return True
        
        chat_type = chat_type.lower()
        
        # Determine chat type based on attributes
        if chat_type == 'task':
            return bool(chat.board or chat.column)
        elif chat_type == 'chat':
            return not (chat.board or chat.column)
        
        return True

    def list_chats(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Chat]:
        """
        Return a sorted list of all chats (metadata only, no messages).

        CHANGED — time-range filtering:
            An optional upper bound ``to_date`` was added, turning the previous
            single lower-bound filter into a full ``[from_date, to_date]``
            window. Both bounds are optional; when omitted no filtering is
            applied on that side (backward compatible). Invalid date strings
            raise :class:`ValueError` (propagated to the caller).

        :param from_date: ISO-format date string; only chats modified after
            this date are returned (lower bound).
        :param to_date: ISO-format date string; only chats modified on or
            before this date are returned (inclusive upper bound).
        :return: List of Chat objects sorted by index/updated_at descending.
        """
        last_update = datetime.fromisoformat(from_date) if from_date else None
        before_update = datetime.fromisoformat(to_date) if to_date else None
        file_paths = self.chat_paths(
            last_update=last_update,
            before_update=before_update,
        )

        def _load_chat_info(file_path: str) -> Optional[Chat]:
            try:
                return self.load_chat_from_path(chat_file=file_path, chat_only=True)
            except (OSError, ValueError, KeyError) as ex:
                # ValueError covers json.JSONDecodeError and pydantic validation
                logger.error("Error loading chat '%s': %s", file_path, ex)
            return None

        chats = [c for c in (_load_chat_info(p) for p in file_paths) if c]
        return sorted(chats, key=lambda x: str(x.chat_index or x.updated_at), reverse=True)

    # -------------------------------------------------------------------------
    # Chat search
    # -------------------------------------------------------------------------

    def search_chats(
        self,
        query: str,
        user_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        project_ids: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
        user: Optional[object] = None,
    ) -> Dict[str, Any]:
        """
        Search chats with full-text search, user filtering, project filtering,
        and pagination.

        When no query is provided and project_ids is specified, returns the
        latest chats from those projects (sorted by recency).

        Delegates to :class:`codx.junior.chat_searcher.ChatSearcher` for
        full-text search across chat data. Results can be filtered by user_id
        (chats where user created or participated) and project_ids list.

        :param query: Search query string (case-insensitive substring matching).
            If empty and project_ids is provided, returns latest chats instead.
        :param user_id: Optional user ID to filter search results to only chats
            where this user created or participated. If None, searches all chats.
        :param from_date: ISO-format date string; only include chats updated
            after this date (inclusive).
        :param to_date: ISO-format date string; only include chats updated
            before this date (inclusive).
        :param project_ids: Optional list of project IDs to filter chats by.
            If None, all projects are searched. If empty list, no chats are returned.
        :param page: Page number (1-indexed).
        :param page_size: Number of results per page.
        :param user: Optional CodxUser object for permission-based project loading.
            If provided and project_ids is None, loads all user's accessible projects.
        :return: Dict with paginated results and metadata.
        """
        from codx.junior.project.project_discover import find_all_user_projects

        # Determine which projects to search
        projects_to_search = []
        
        if project_ids is not None:
            # Use explicitly provided project_ids
            for proj_id in project_ids:
                proj = find_project_by_id(proj_id)
                if proj:
                    projects_to_search.append(proj)
        elif user is not None:
            # Load all user's accessible projects
            try:
                user_projects = list(find_all_user_projects(user))
                projects_to_search = [p for p in user_projects]
            except Exception as ex:
                logger.warning(
                    "search_chats: failed to load user projects for user '%s': %s",
                    user,
                    ex,
                )
                # Fall back to current project only
                projects_to_search = [self.settings]
        else:
            # Default: search current project
            projects_to_search = [self.settings]

        if not projects_to_search:
            logger.warning(
                "search_chats: no projects to search for user_id='%s' project_ids=%s",
                user_id,
                project_ids,
            )
            return {
                "results": [],
                "total": 0,
                "page": 1,
                "page_size": page_size,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            }

        # Load chats from all accessible projects
        all_project_chats: List[Chat] = []
        for proj_settings in projects_to_search:
            try:
                proj_manager = ChatManager(settings=proj_settings, event_manager=self.event_manager)
                proj_chats = proj_manager.list_chats()
                all_project_chats.extend(proj_chats)
            except Exception as ex:
                logger.warning(
                    "search_chats: failed to load chats from project '%s': %s",
                    proj_settings.project_name,
                    ex,
                )

        # Apply user_id filter
        if user_id:
            all_project_chats = [
                chat for chat in all_project_chats
                if self._user_involved_in_chat(chat, user_id)
            ]

        # If no query provided, return latest chats (already filtered by projects)
        if not query or not query.strip():
            sorted_chats = sorted(
                all_project_chats,
                key=lambda c: _parse_timestamp(c.updated_at),
                reverse=True,
            )
            total = len(sorted_chats)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size

            logger.info(
                "search_chats: no query, returning %d latest chats from %d total",
                len(sorted_chats[start_idx:end_idx]),
                total,
            )
            return {
                "results": sorted_chats[start_idx:end_idx],
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }

        # Perform full-text search
        from codx.junior.chat_searcher import ChatSearcher

        searcher = ChatSearcher()
        results = searcher.search(
            chats=all_project_chats,
            query=query,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )

        logger.info(
            "search_chats: query='%s' user_id=%s project_ids=%s returned %d results, page %d of %d",
            query,
            user_id or "all",
            project_ids or "all",
            results.get("total", 0),
            results.get("page", 1),
            results.get("total_pages", 0),
        )
        return results

    # -------------------------------------------------------------------------
    # Owner project resolution
    # -------------------------------------------------------------------------

    def _resolve_owner_manager(self, chat: Chat) -> "ChatManager":
        """
        Return the ChatManager owning *chat*.

        When the chat belongs to a different project (``owner_project_id``),
        a manager scoped to that project is returned so persistence lands in
        the correct location.

        :param chat: The chat whose owner manager to resolve.
        :return: ``self`` or a ChatManager scoped to the owner project.
        """
        if chat.owner_project_id and chat.owner_project_id != self.settings.project_id:
            chat_project = find_project_by_id(chat.owner_project_id)
            if chat_project:
                return ChatManager(settings=chat_project, event_manager=self.event_manager)
            logger.warning(
                "Owner project '%s' not found for chat '%s'; using current manager",
                chat.owner_project_id,
                chat.id,
            )
        return self

    # -------------------------------------------------------------------------
    # Merge-safe message helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _merge_message_lists(
        stored_messages: List[Message],
        incoming_messages: List[Message],
    ) -> List[Message]:
        """
        Merge two message lists by ``doc_id`` using ``updated_at`` to decide
        which version wins (last-writer-wins per message, never regress).

        Stored message ordering is preserved; new incoming messages are
        appended in their original relative order.

        FIXED: timestamps are parsed with :func:`_parse_timestamp` before
        comparison. Raw string comparison was incorrect because message
        timestamps exist in two formats (isoformat with 'T' vs
        ``str(datetime)`` with a space): the 'T' variant always won
        lexicographically, letting an OLDER incoming message overwrite a
        NEWER stored one.

        :param stored_messages: Messages loaded from disk.
        :param incoming_messages: Messages from the in-memory chat.
        :return: Merged, ordered message list.
        """
        merged: Dict[str, Message] = {}
        order: List[str] = []

        for message in list(stored_messages) + list(incoming_messages):
            if not message.doc_id:
                message.doc_id = str(uuid.uuid4())

            existing = merged.get(message.doc_id)
            if existing is None:
                merged[message.doc_id] = message
                order.append(message.doc_id)
            elif _parse_timestamp(message.updated_at) >= _parse_timestamp(existing.updated_at):
                # Incoming (or later duplicate) is newer or equal: overwrite
                merged[message.doc_id] = message

        return [merged[doc_id] for doc_id in order]

    def _load_stored_chat(self, chat: Chat) -> Optional[Chat]:
        """
        ADDED: Load the persisted version of *chat* with a fast-path.

        The granular message operations are hot-path code during an AI turn
        (invoked on every tool event and throttled stream persist). Scanning
        the whole tasks tree via :meth:`find_by_id` on every call is wasteful,
        so when ``chat.file_path`` is known, valid and inside this manager's
        tree it is read directly; otherwise fall back to :meth:`find_by_id`
        (covers moved/renamed chats).

        :param chat: The in-memory chat whose stored version to load.
        :return: The stored Chat, or ``None`` when not persisted yet.
        """
        if (
            chat.file_path
            and chat.file_path.startswith(self.chat_path)
            and os.path.isfile(chat.file_path)
        ):
            try:
                return self.load_chat_from_path(chat_file=chat.file_path)
            except (OSError, ValueError, KeyError) as ex:
                logger.warning(
                    "Fast-path load failed for chat '%s' at '%s': %s — "
                    "falling back to find_by_id",
                    chat.id,
                    chat.file_path,
                    ex,
                )
        return self.find_by_id(chat_id=chat.id) if chat.id else None

    @staticmethod
    def _accumulate_message_cost(
        chat: Chat,
        stored_chat: Optional[Chat],
        message: Message,
    ) -> float:
        """
        Accumulate the cost of a single *message* into ``chat.cost`` (monotonic).

        The persisted (stored) version of the message is used as the baseline so
        the cost is counted **exactly once**, while still capturing costs that
        are registered AFTER the message was first persisted (SmolAgent sets the
        cost on the response message once the AI call returns, which happens
        after the message may already have been streamed/saved with cost 0).

        Only POSITIVE deltas are applied, so ``chat.cost`` never decreases. As a
        result, deleting a message (see :meth:`remove_message`) never reduces the
        accumulated cost of the chat.

        :param chat: The in-memory chat whose accumulated cost to update.
        :param stored_chat: The persisted chat (baseline), or ``None``.
        :param message: The message whose cost to account for.
        :return: The delta actually added (0.0 when nothing changed).
        """
        new_cost = getattr(message, "cost", 0.0) or 0.0
        if new_cost <= 0:
            return 0.0

        previous_cost = 0.0
        if stored_chat:
            stored_message = next(
                (m for m in stored_chat.messages if m.doc_id == message.doc_id),
                None,
            )
            if stored_message is not None:
                previous_cost = getattr(stored_message, "cost", 0.0) or 0.0

        delta = new_cost - previous_cost
        if delta <= 0:
            return 0.0

        chat.cost = (getattr(chat, "cost", 0.0) or 0.0) + delta
        logger.info(
            "Accumulated chat cost: chat='%s' message='%s' delta=%.6f total=%.6f",
            chat.id,
            message.doc_id,
            delta,
            chat.cost,
        )
        return delta

    def _persist_chat_messages(
        self,
        chat: Chat,
        stored_chat: Optional[Chat] = None,
        cost_message: Optional[Message] = None,
    ) -> Chat:
        """
        Merge-safe persistence used by the granular message operations.

        Reloads the stored chat (if any), merges message lists so mid-turn
        saves never clobber concurrent updates, optionally accumulates the cost
        of *cost_message* into ``chat.cost`` and then delegates to
        :meth:`save_chat`.

        :param chat: The in-memory chat to persist.
        :param stored_chat: Optional pre-loaded stored chat (avoids a second
            disk read when the caller already loaded it).
        :param cost_message: Optional message whose cost must be accumulated
            into ``chat.cost`` before saving.
        :return: The persisted chat (same instance, messages may be merged).
        """
        manager = self._resolve_owner_manager(chat)
        if stored_chat is None:
            stored_chat = manager._load_stored_chat(chat)
        if stored_chat:
            # Keep the accumulated cost monotonic: never regress a value that
            # may already have been persisted by another writer.
            if (stored_chat.cost or 0.0) > (chat.cost or 0.0):
                chat.cost = stored_chat.cost
            chat.messages = self._merge_message_lists(
                stored_messages=stored_chat.messages,
                incoming_messages=chat.messages,
            )
        if cost_message is not None:
            manager._accumulate_message_cost(
                chat=chat,
                stored_chat=stored_chat,
                message=cost_message,
            )
        return manager.save_chat(chat=chat)

    def add_message(self, chat: Chat, message: Message) -> Chat:
        """
        Append *message* to *chat* and persist immediately (merge-safe).

        Used to notify events (tool usage, run lifecycle) in real time while
        an AI turn is still running. Idempotent in memory: the message is not
        appended twice if its ``doc_id`` is already on the chat.

        The message's cost (if any) is accumulated into ``chat.cost``.

        :param chat: The chat to add the message to (mutated in place).
        :param message: The message to add.
        :return: The persisted chat.
        """
        if not message.doc_id:
            message.doc_id = str(uuid.uuid4())
        message.updated_at = datetime.now().isoformat()
        if not any(m.doc_id == message.doc_id for m in chat.messages):
            chat.messages.append(message)
        logger.info(
            "add_message: chat='%s' message='%s' role='%s'",
            chat.id,
            message.doc_id,
            message.role,
        )
        return self._persist_chat_messages(chat, cost_message=message)

    def update_message(self, chat: Chat, message: Message) -> Chat:
        """
        Update an existing message in *chat* (matched by ``doc_id``) and
        persist immediately (merge-safe). If the message is not found it is
        appended instead.

        The message's cost (if any) is accumulated into ``chat.cost`` — this
        captures the cost SmolAgent registers on the response message AFTER the
        AI call completes, even if the message was already persisted with a
        cost of 0 during streaming.

        :param chat: The chat containing the message (mutated in place).
        :param message: The updated message.
        :return: The persisted chat.
        """
        if not message.doc_id:
            message.doc_id = str(uuid.uuid4())
        message.updated_at = datetime.now().isoformat()
        found = False
        for index, existing in enumerate(chat.messages):
            if existing.doc_id == message.doc_id:
                chat.messages[index] = message
                found = True
                break
        if not found:
            chat.messages.append(message)
        # CHANGED: debug level — this is hot-path (tool events + throttled
        # stream persists) and info-level logging would flood the logs.
        logger.debug(
            "update_message: chat='%s' message='%s' found=%s",
            chat.id,
            message.doc_id,
            found,
        )
        return self._persist_chat_messages(chat, cost_message=message)

    def update_chat_metadata(self, chat: Chat, metadata: dict) -> Chat:
        """
        Update chat metadata only (name, description, board, column, etc.)
        without touching messages.

        :param chat: The chat to update (mutated in place).
        :param metadata: Dict of metadata fields to update (excluding messages).
        :return: The persisted chat.
        """
        # Update only metadata fields, preserve messages
        for key, value in metadata.items():
            if key != "messages" and hasattr(chat, key):
                setattr(chat, key, value)
        
        # Save with chat_only=True to preserve messages
        updated_chat = self.save_chat(chat=chat, chat_only=True)
        
        logger.info(
            "update_chat_metadata: updated metadata for chat '%s'",
            chat.id
        )
        return updated_chat

    def remove_message(self, chat: Chat, message_doc_id: str) -> Chat:
        """
        Remove the message identified by *message_doc_id* from *chat* and
        persist. The removal is applied on top of the merged (stored +
        in-memory) message list so no other concurrent change is lost.

        The accumulated cost (``chat.cost``) is intentionally NOT changed:
        deleting a message keeps its cost in the chat budget.

        :param chat: The chat containing the message (mutated in place).
        :param message_doc_id: ``doc_id`` of the message to remove.
        :return: The persisted chat.
        """
        manager = self._resolve_owner_manager(chat)
        stored_chat = manager._load_stored_chat(chat)
        if stored_chat:
            chat.messages = self._merge_message_lists(
                stored_messages=stored_chat.messages,
                incoming_messages=chat.messages,
            )
        chat.messages = [m for m in chat.messages if m.doc_id != message_doc_id]
        logger.info(
            "remove_message: chat='%s' message='%s'", chat.id, message_doc_id
        )
        return manager.save_chat(chat=chat)

    # -------------------------------------------------------------------------
    # Full-chat persistence
    # -------------------------------------------------------------------------

    def _register_status_change(
        self,
        chat: Chat,
        current_chat: Optional[Chat],
        user: Optional[str] = None,
    ) -> bool:
        """
        Detect and record a ``Chat.status`` transition into ``chat.status_history``.

        The history is APPEND-ONLY: persisted entries (from ``current_chat``) are
        merged with any in-memory entries (dedup by ``doc_id``) so concurrent
        writers never lose a transition. A new :class:`ChatStatusEvent` is only
        appended when the status actually changed.

        This produces the raw transition feed required by the task-performance
        metrics (cycle time, throughput, error rate) that cannot be derived from
        the single mutable ``Chat.status`` field.

        :param chat: The in-memory chat being persisted (mutated in place).
        :param current_chat: The previously persisted chat, or ``None`` if new.
        :param user: Optional user that triggered the change.
        :return: ``True`` when a new transition was registered.
        """
        # Merge persisted (source of truth) + in-memory history, dedup by doc_id
        merged: Dict[str, ChatStatusEvent] = {}
        stored_history = current_chat.status_history if current_chat else []
        for event in list(stored_history) + list(chat.status_history):
            if not event.doc_id:
                event.doc_id = str(uuid.uuid4())
            merged[event.doc_id] = event

        history = sorted(merged.values(), key=lambda e: _parse_timestamp(e.at))

        previous_status = (current_chat.status if current_chat else None) or None
        new_status = chat.status or None

        if previous_status == new_status:
            # No real transition — keep merged history and bail out
            chat.status_history = history
            return False

        history.append(
            ChatStatusEvent(
                doc_id=str(uuid.uuid4()),
                from_status=previous_status,
                to_status=new_status or "",
                user=user,
                at=datetime.now().isoformat(),
            )
        )
        chat.status_history = history
        logger.info(
            "Chat status change: chat='%s' '%s' -> '%s' (history=%d)",
            chat.id,
            previous_status,
            new_status,
            len(history),
        )
        return True

    def save_chat(self, chat: Chat, chat_only: bool = False) -> Chat:
        """
        Persist *chat* to disk, handling board/column defaults, ID assignment,
        user/profile aggregation, old-file cleanup and event emission.

        When ``chat.owner_project_id`` points to a different project the call
        is transparently forwarded to the correct :class:`ChatManager`.

        Status transitions are registered into ``chat.status_history`` before
        the chat is written, using the previously persisted chat as the
        ``from_status`` baseline.

        :param chat: The chat to save.
        :param chat_only: If ``True`` and the chat already exists, preserve
            its stored messages (useful for metadata-only updates).
        :return: The saved chat.
        """
        # Delegate to the owning project's manager when necessary
        manager = self._resolve_owner_manager(chat)
        if manager is not self:
            return manager.save_chat(chat=chat, chat_only=chat_only)

        if not chat.board:
            chat.board = DEFAULT_BOARD
        if not chat.column:
            chat.column = DEFAULT_COLUMN
        if not chat.id:
            chat.id = str(uuid.uuid4())
        if not chat.created_at:
            chat.created_at = chat.updated_at

        chat.updated_at = datetime.now().isoformat()

        current_chat = self.find_by_id(chat_id=chat.id)
        if chat_only and current_chat:
            chat.messages = current_chat.messages

        # Detect and register chat status transitions (performance metrics).
        # Runs before store_chat so the new record is persisted with the chat.
        self._register_status_change(chat=chat, current_chat=current_chat)

        chat.file_path = self.get_chat_file(chat)

        self.store_chat(chat=chat)

        # Remove superseded yaml file (legacy format)
        yaml_path = chat.file_path.replace(".json", ".yaml")
        if os.path.isfile(yaml_path):
            logger.info("Remove old yaml chat: %s", chat.file_path)
            os.remove(yaml_path)

        # Remove old path if the chat was moved (board/column/name changed)
        if current_chat:
            logger.info(
                "Save chat, current_chat %s at %s", current_chat.id, current_chat.file_path
            )
            if chat.file_path != current_chat.file_path:
                self.delete_chat(current_chat.file_path)

        self.event_manager.chat_event(chat=chat, event_type="changed")

        return chat

    def store_chat(self, chat: Chat) -> None:
        """
        Write *chat* to its ``file_path`` as JSON.

        :param chat: The chat to write.
        """
        logger.info("Save chat: %s", chat.file_path)
        os.makedirs(os.path.dirname(chat.file_path), exist_ok=True)
        with open(chat.file_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(chat.model_dump(), indent=2))

    def delete_chat(self, file_path: Optional[str] = None, chat_id: Optional[str] = None) -> None:
        """
        Delete a chat file from disk.

        :param file_path: Direct path to the chat file.
        :param chat_id: Chat ID; resolved to a path via :meth:`find_by_id`.
        """
        logger.info("Removing chat by file_path: %s  - chat_id: %s", file_path, chat_id)

        if chat_id:
            chat = self.find_by_id(chat_id)
            # FIXED: guard against a missing chat to avoid AttributeError
            if not chat:
                logger.error("delete_chat: chat_id '%s' not found, nothing to delete", chat_id)
                return
            file_path = chat.file_path

        if file_path and os.path.isfile(file_path) and file_path.startswith(self.chat_path):
            logger.info("Removing chat at %s", file_path)
            os.remove(file_path)
        else:
            logger.error("Removing chat error %s", file_path)

    # -------------------------------------------------------------------------
    # Chat loading
    # -------------------------------------------------------------------------

    def load_chat(
        self,
        board: str,
        column: Optional[str] = None,
        chat_name: Optional[str] = None,
    ) -> Chat:
        """
        Load a chat by board/column/name, returning an empty Chat if not found.

        :param board: Board name.
        :param column: Column name.
        :param chat_name: Chat name.
        :return: Loaded or new Chat object.
        """
        chat = Chat(board=board, column=column, name=chat_name)
        chat_file = self.get_chat_file(chat)
        if not os.path.isfile(chat_file):
            chat.file_path = chat_file
            return chat
        return self.load_chat_from_path(chat_file=chat_file)

    def load_chat_from_path(self, chat_file: str, chat_only: bool = False) -> Chat:
        """
        Load a Chat from a JSON file, ensuring the loaded chat always has a valid ID.

        NEW: If the chat has no ID in the JSON data, attempts to extract it from the
        filename (format: {slugified_name}.{uuid}.json). If extraction fails, generates
        a fresh UUID and logs a warning.

        :param chat_file: Path to the chat JSON file.
        :param chat_only: If ``True`` the returned chat has an empty message list.
        :return: Loaded Chat object with guaranteed valid ID.
        """
        with open(chat_file, "r", encoding="utf-8") as f:
            chat_data = json.loads(f.read())
        chat = Chat(**chat_data)
        
        # ADDED: Ensure chat always has an ID
        if not chat.id:
            # Try to extract ID from filename
            extracted_id = _extract_id_from_filename(chat_file)
            if extracted_id:
                chat.id = extracted_id
                logger.warning(
                    "Chat loaded from '%s' had no ID; extracted from filename: %s",
                    chat_file,
                    extracted_id,
                )
            else:
                # Generate a new ID as fallback
                chat.id = str(uuid.uuid4())
                logger.warning(
                    "Chat loaded from '%s' had no ID; generated new UUID: %s",
                    chat_file,
                    chat.id,
                )
        
        if chat_only:
            chat.messages = [chat.messages[-1]] if len(chat.messages) else []
        chat.owner_project_id = self.settings.project_id
        return chat

    # -------------------------------------------------------------------------
    # Kanban helpers
    # -------------------------------------------------------------------------

    def delete_kanban(self, kanban_title: str) -> None:
        """
        Remove an entire kanban board directory.

        :param kanban_title: Name of the kanban board to delete.
        """
        shutil.rmtree(f"{self.chat_path}/{kanban_title}")

    def chat_count(self) -> int:
        """Return the total number of chat files on disk."""
        return len(self.chat_paths())

    def last_chats(self) -> List[Chat]:
        """
        Return up to three chats modified within the last two days.

        :return: List of recently modified Chat objects.
        """
        cutoff = (datetime.now() - timedelta(days=2)).timestamp()
        chat_paths = [
            {"chat_path": p, "updated_at": os.stat(p).st_ctime}
            for p in self.chat_paths()
        ]
        recent = sorted(
            [c for c in chat_paths if c["updated_at"] > cutoff],
            key=lambda x: x["updated_at"],
            reverse=True,
        )[:3]
        return [self.load_chat_from_path(chat_file=c["chat_path"]) for c in recent]

    def find_by_id(self, chat_id: Optional[str]) -> Optional[Chat]:
        """
        Find and load a chat by its ID.

        :param chat_id: The UUID of the chat to locate.
        :return: Loaded Chat or ``None`` if not found.
        """
        if chat_id:
            all_paths = self.chat_paths()
            file_path = next(
                (path for path in all_paths if chat_id in path), None
            )
            if file_path:
                return self.load_chat_from_path(chat_file=file_path)
            # CHANGED: log the count instead of dumping every path (log noise)
            logger.error(
                "[chat_id] not found: %s (searched %d chat files)",
                chat_id,
                len(all_paths),
            )
        return None

    def load_kanban_from_file(self, kanban_file: str) -> dict:
        """
        Load kanban state from a JSON file, applying defaults when missing.

        :param kanban_file: Path to the kanban JSON file.
        :return: Kanban dict with ``version``, ``boards`` and ``tags`` keys.
        """
        kanban: dict = {"version": 0.1, "boards": {}, "tags": {}}
        if os.path.isfile(kanban_file):
            with open(kanban_file, "r", encoding="utf-8") as f:
                kanban = json.loads(f.read())
            # Migrate legacy format that lacked the version envelope
            if not kanban.get("version"):
                kanban = {"version": 0.1, "boards": kanban, "tags": {}}
        logger.info("Loading %s kanban", self.settings.project_name)
        return kanban

    @profile_function
    def load_kanban(self) -> dict:
        """
        Load the project's kanban configuration.

        :return: Kanban dict.
        """
        kanban_file = f"{self.chat_path}/kanban.json"
        logger.info("load_kanban %s", kanban_file)
        return self.load_kanban_from_file(kanban_file=kanban_file)

    def save_kanban(self, kanban: dict) -> None:
        """
        Persist the kanban configuration to disk.

        :param kanban: Kanban dict to save.
        """
        kanban_file = f"{self.chat_path}/kanban.json"
        with open(kanban_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(kanban))

    # -------------------------------------------------------------------------
    # Chat querying
    # -------------------------------------------------------------------------

    def find_chats(self, last_update: Optional[datetime] = None) -> List[Chat]:
        """
        Return chats based on filters.

        :param last_update: Return chats updated since this date.
        :return: List of Chat objects.
        """
        filtered_chats: List[Chat] = []
        for file_path in self.chat_paths(last_update=last_update):
            chat = self.load_chat_from_path(chat_file=file_path)
            if chat:
                filtered_chats.append(chat)
        return filtered_chats

    # -------------------------------------------------------------------------
    # Chat export
    # -------------------------------------------------------------------------

    def traverse_chat_messages(
        self, chat_id: str, all_chats: List[Chat]
    ) -> List[Message]:
        """
        Recursively traverse messages in *chat_id* and its descendants.

        Linked chats (via ``message_id``) and child chats (via ``parent_id``)
        are both followed.

        :param chat_id: Root chat ID to start traversal from.
        :param all_chats: Full list of chats used for link resolution.
        :return: Ordered list of messages.
        """
        messages: List[Message] = []
        chat = self.find_by_id(chat_id)

        logger.info(
            "chat_export traversing chat: %s, messages: %s", chat.name, len(chat.messages)
        )
        for message in chat.messages:
            # Follow any chat that is linked to this message
            linked_chat = next(
                (c for c in all_chats if c.message_id == message.doc_id), None
            )
            if linked_chat:
                messages.extend(
                    self.traverse_chat_messages(
                        chat_id=linked_chat.id, all_chats=all_chats
                    )
                )
            messages.append(message)

        # Append child chats in index order
        child_chats = sorted(
            [c for c in all_chats if c.parent_id == chat.id],
            key=lambda x: x.child_index,
        )
        for child_chat in child_chats:
            messages.extend(
                self.traverse_chat_messages(chat_id=child_chat.id, all_chats=all_chats)
            )

        return messages

    def build_markdown_document(self, chat_id: str) -> str:
        """
        Traverse the chat and generate a markdown document.

        Messages with ``hide=True`` are excluded.

        :param chat_id: ID of the root chat.
        :return: Markdown string.
        """
        all_chats = self.list_chats()
        messages = self.traverse_chat_messages(chat_id=chat_id, all_chats=all_chats)
        markdown = ""
        for msg in messages:
            if not msg.hide:
                markdown += f"# {msg.content}\n\n"
        return markdown

    def export_chat(self, chat_id: str, export_format: str) -> ExportedDocument:
        """
        Export a chat and its descendants to the specified format.

        :param chat_id: The ID of the chat to export.
        :param export_format: Target format (e.g. ``markdown``, ``docx``,
            ``pdf``, ``excel``).
        :return: An ExportedDocument containing the exported content.
        """
        chat = self.find_by_id(chat_id=chat_id)
        content = self.build_markdown_document(chat_id=chat_id)
        chat_exporter = ChatExport(chat=chat, content=content, export_format=export_format)
        return chat_exporter.export_chat()

    def mark_message_as_seen(self, chat: Chat, message: Message, username: str) -> List[str]:
        """
        Add username to message's read_by list if not already present.
        
        Persists the updated message immediately (merge-safe).
        
        :param chat: The chat containing the message.
        :param message: The message to mark as seen.
        :param username: Username of the reader.
        :return: Updated read_by list.
        """
        if not message.read_by:
            message.read_by = []
        
        if username not in message.read_by:
            message.read_by.append(username)
            message.updated_at = datetime.now().isoformat()
            self.update_message(chat=chat, message=message)
            logger.info(
                "mark_message_as_seen: chat='%s' message='%s' user='%s'",
                chat.id,
                message.doc_id,
                username,
            )
        
        return message.read_by

    def unmark_message_as_seen(self, chat: Chat, message: Message, username: str) -> List[str]:
        """
        Remove username from message's read_by list.
        
        Persists the updated message immediately (merge-safe).
        
        :param chat: The chat containing the message.
        :param message: The message to mark as un-seen.
        :param username: Username of the reader to remove.
        :return: Updated read_by list.
        """
        if not message.read_by:
            message.read_by = []
        
        if username in message.read_by:
            message.read_by.remove(username)
            message.updated_at = datetime.now().isoformat()
            self.update_message(chat=chat, message=message)
            logger.info(
                "unmark_message_as_seen: chat='%s' message='%s' user='%s'",
                chat.id,
                message.doc_id,
                username,
            )
        
        return message.read_by

# Made with ❤️ by codx-junior