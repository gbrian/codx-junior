"""
Chat + AI
This module is responsible for chat persistence and management.

Besides the classic full-chat ``save_chat``, this module now exposes granular,
merge-safe message operations (``add_message``, ``update_message``,
``remove_message``) used to persist chat changes *during* an AI turn (e.g.
tool-usage notification messages) without overwriting concurrent updates.

Merge strategy (per message, keyed by ``doc_id``):

    ```mermaid
    flowchart TD
        A[Incoming chat messages] --> C{doc_id exists in stored chat?}
        B[Stored chat messages] --> C
        C -->|No| D[Keep message]
        C -->|Yes| E{incoming.updated_at >= stored.updated_at?}
        E -->|Yes| F[Keep incoming]
        E -->|No| G[Keep stored]
        D --> H[Merged message list]
        F --> H
        G --> H
    ```
"""
import logging
import pathlib
import os
import json
import uuid
import shutil
import yaml

from slugify import slugify
from collections import deque, defaultdict

from typing import Dict, Any, List, Optional

from datetime import datetime, timezone, timedelta
from codx.junior.settings import CODXJuniorSettings

from codx.junior.db import Chat, Message
from codx.junior.utils.utils import write_file

from codx.junior.profiling.profiler import profile_function

from codx.junior.chat.chat_export import ChatExport, ExportedDocument

from codx.junior.events.event_manager import EventManager

from codx.junior.project.project_discover import find_project_by_id

logger = logging.getLogger(__name__)

DEFAULT_BOARD = "kanban"
DEFAULT_COLUMN = "tasks"


class ChatManager:
    """
    Manages chat persistence and retrieval for a given project.

    Provides full-chat save/load operations as well as granular, merge-safe
    message operations (``add_message``, ``update_message``, ``remove_message``)
    that are safe to call while an AI turn is in progress.
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

    def chat_paths(self, last_update: Optional[datetime] = None) -> List[str]:
        """
        Return chat file paths, optionally filtering by last update time.

        :param last_update: Only return paths for chats updated since this date.
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

    def list_chats(self, from_date: Optional[str] = None) -> List[Chat]:
        """
        Return a sorted list of all chats (metadata only, no messages).

        :param from_date: ISO-format date string; only chats modified after
            this date are returned.
        :return: List of Chat objects sorted by index/updated_at descending.
        """
        last_update = datetime.fromisoformat(from_date) if from_date else None
        file_paths = self.chat_paths(last_update=last_update)

        def _load_chat_info(file_path: str) -> Optional[Chat]:
            try:
                return self.load_chat_from_path(chat_file=file_path, chat_only=True)
            except Exception as ex:  # noqa: BLE001
                logger.error("Error loading chat '%s': %s", file_path, ex)
            return None

        chats = [c for c in (_load_chat_info(p) for p in file_paths) if c]
        return sorted(chats, key=lambda x: str(x.chat_index or x.updated_at), reverse=True)

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
            elif str(message.updated_at or "") >= str(existing.updated_at or ""):
                # Incoming (or later duplicate) is newer or equal: overwrite
                merged[message.doc_id] = message

        return [merged[doc_id] for doc_id in order]

    def _persist_chat_messages(self, chat: Chat) -> Chat:
        """
        Merge-safe persistence used by the granular message operations.

        Reloads the stored chat (if any), merges message lists so mid-turn
        saves never clobber concurrent updates, then delegates to
        :meth:`save_chat`.

        :param chat: The in-memory chat to persist.
        :return: The persisted chat (same instance, messages may be merged).
        """
        manager = self._resolve_owner_manager(chat)
        stored_chat = manager.find_by_id(chat_id=chat.id) if chat.id else None
        if stored_chat:
            chat.messages = self._merge_message_lists(
                stored_messages=stored_chat.messages,
                incoming_messages=chat.messages,
            )
        return manager.save_chat(chat=chat)

    def add_message(self, chat: Chat, message: Message) -> Chat:
        """
        Append *message* to *chat* and persist immediately (merge-safe).

        Used to notify events (tool usage, run lifecycle) in real time while
        an AI turn is still running.

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
        return self._persist_chat_messages(chat)

    def update_message(self, chat: Chat, message: Message) -> Chat:
        """
        Update an existing message in *chat* (matched by ``doc_id``) and
        persist immediately (merge-safe). If the message is not found it is
        appended instead.

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
        logger.info(
            "update_message: chat='%s' message='%s' found=%s",
            chat.id,
            message.doc_id,
            found,
        )
        return self._persist_chat_messages(chat)

    def remove_message(self, chat: Chat, message_doc_id: str) -> Chat:
        """
        Remove the message identified by *message_doc_id* from *chat* and
        persist. The removal is applied on top of the merged (stored +
        in-memory) message list so no other concurrent change is lost.

        :param chat: The chat containing the message (mutated in place).
        :param message_doc_id: ``doc_id`` of the message to remove.
        :return: The persisted chat.
        """
        manager = self._resolve_owner_manager(chat)
        stored_chat = manager.find_by_id(chat_id=chat.id) if chat.id else None
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

    def save_chat(self, chat: Chat, chat_only: bool = False) -> Chat:
        """
        Persist *chat* to disk, handling board/column defaults, ID assignment,
        user/profile aggregation, old-file cleanup and event emission.

        When ``chat.owner_project_id`` points to a different project the call
        is transparently forwarded to the correct :class:`ChatManager`.

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

        users: List[str] = []
        profiles: List[str] = []
        for msg in chat.messages:
            if not msg.doc_id:
                msg.doc_id = str(uuid.uuid4())
            if msg.user:
                users.append(msg.user)
            profiles = profiles + msg.profiles
        chat.users = list(set(users))
        chat.profiles = list(set(profiles))
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
        Load a Chat from a JSON file.

        :param chat_file: Path to the chat JSON file.
        :param chat_only: If ``True`` the returned chat has an empty message list.
        :return: Loaded Chat object.
        """
        with open(chat_file, "r", encoding="utf-8") as f:
            chat_data = json.loads(f.read())
        chat = Chat(**chat_data)
        if chat_only:
            chat.messages = []
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
            file_path = next(
                (path for path in self.chat_paths() if chat_id in path), None
            )
            if file_path:
                return self.load_chat_from_path(chat_file=file_path)
            logger.error("[chat_id] not found: %s\n%s", chat_id, self.chat_paths())
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

# Made with ❤️ by codx-junior