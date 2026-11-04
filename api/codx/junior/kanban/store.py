"""
Kanban storage v2: one file per board, atomic writes, cross-process lock.

Problem solved
--------------
v1 kept every board of a project in a single ``tasks/kanban.json`` written with
read‑modify‑write and no lock, by the UI *and* by the tools. A concurrent write
dropped boards. v2 keeps:

* ``tasks/index.json`` - the board list (id, title, type, parent, folder, order)
  plus the project tags,
* ``tasks/boards/<board_id>/board.json`` - the full definition of one board
  (description, columns, parents...).

Both are written atomically (``tmp`` + ``os.replace``) while holding a project
level ``fcntl`` lock, so the API process and the background process can write
the same catalogue without losing data.

Identity
--------
``id`` and ``folder`` are immutable. ``title`` is a label: renaming a board or a
column changes nothing on disk, so **no task is moved or rewritten**.

Compatibility
-------------
:meth:`KanbanStore.load` returns the *assembled* legacy shape::

    {"version": 2, "boards": {"<title>": {...}}, "tags": {...}}

so ``GET /api/kanban`` and the Vue client keep working unchanged, and
``POST /api/kanban`` (the whole assembled document) is diffed against the index
by :meth:`KanbanStore.save`.

Made with ❤️ by codx-junior
"""

import json
import logging
import os
import shutil
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:  # POSIX only; the container always has it.
    import fcntl
except ImportError:  # pragma: no cover - non POSIX fallback
    fcntl = None

from codx.junior.kanban.model import (
    BACKUP_FILE,
    BOARD_FILE,
    BOARDS_DIR,
    BOARD_TYPE_KANBAN,
    DEFAULT_BOARD,
    DEFAULT_COLUMN,
    INDEX_FILE,
    LEGACY_FILE,
    LOCK_FILE,
    STORE_VERSION,
    safe_folder,
)
from codx.junior.migrations.kanban_v1_to_v2 import migrate_kanban_v1_to_v2

logger = logging.getLogger(__name__)


class KanbanStore:
    """
    Persistence of the kanban catalogue (boards, sprints and columns).

    Attributes:
        tasks_path: Absolute ``<codx_path>/tasks`` folder.
    """

    def __init__(self, tasks_path: str) -> None:
        """
        Args:
            tasks_path: Absolute path of the project's ``tasks`` folder.
        """
        self.tasks_path = str(tasks_path)
        self.boards_path = os.path.join(self.tasks_path, BOARDS_DIR)
        self._cache_key: Optional[Tuple[str, Optional[float]]] = None
        self._cache: Optional[Dict[str, Dict[str, Any]]] = None

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------
    def _path(self, *parts: str) -> str:
        """Join *parts* onto the tasks folder."""
        return os.path.join(self.tasks_path, *parts)

    def _index_file(self) -> str:
        """Absolute path of the index file."""
        return self._path(INDEX_FILE)

    def _board_file(self, board_id: Optional[str]) -> str:
        """Absolute path of the definition file of *board_id*."""
        return self._path(BOARDS_DIR, str(board_id or ""), BOARD_FILE)

    def _board_dir(self, board_id: Optional[str]) -> str:
        """Absolute path of the folder that holds the definition of *board_id*."""
        return self._path(BOARDS_DIR, str(board_id or ""))

    # ------------------------------------------------------------------
    # Low level IO
    # ------------------------------------------------------------------
    @staticmethod
    def _read_json(file_path: str) -> Optional[dict]:
        """Read a JSON object, returning None when missing or unreadable."""
        if not os.path.isfile(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                data = json.loads(handle.read())
            return data if isinstance(data, dict) else None
        except (OSError, ValueError) as ex:
            logger.warning("kanban: cannot read '%s': %s", file_path, ex)
            return None

    @staticmethod
    def _write_json(file_path: str, data: dict) -> None:
        """Write *data* atomically so a crash never leaves a half written file."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        tmp_path = f"{file_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2))
        os.replace(tmp_path, file_path)

    @contextmanager
    def locked(self) -> Iterator[None]:
        """
        Hold the project wide kanban lock.

        The lock file is opened in append mode and ``flock``ed exclusively: it
        serialises every writer **across processes** (the API process and the
        background process), which is what makes concurrent board edits safe.
        On platforms without ``fcntl`` the context manager degrades to a no-op
        instead of failing.
        """
        lock_file = self._path(LOCK_FILE)
        os.makedirs(os.path.dirname(lock_file) or ".", exist_ok=True)
        handle = open(lock_file, "a+", encoding="utf-8")
        try:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()

    # ------------------------------------------------------------------
    # Migration
    # ------------------------------------------------------------------
    def migrate_if_needed(self) -> Dict[str, Any]:
        """
        Ensure the project uses the v2 layout.

        Returns:
            The migration summary (``{"migrated": False, ...}`` when there was
            nothing to do).
        """
        if os.path.isfile(self._index_file()):
            return {"migrated": False, "boards": 0}
        try:
            return migrate_kanban_v1_to_v2(tasks_path=self.tasks_path)
        except Exception as ex:  # a broken catalogue must never break a chat
            logger.exception("kanban: migration failed for '%s': %s", self.tasks_path, ex)
            return {"migrated": False, "boards": 0}

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------
    def _catalogue(self) -> Dict[str, Dict[str, Any]]:
        """
        Return the boards indexed by **lowercase title**, with a short lived cache.

        The cache is invalidated by the ``index.json`` ``mtime``: it exists
        because :meth:`resolve_folders` is called for every chat save (a hot
        path) while the catalogue changes rarely.
        """
        index_file = self._index_file()
        try:
            mtime = os.path.getmtime(index_file)
        except OSError:
            mtime = None
        if self._cache is not None and self._cache_key == (index_file, mtime):
            return self._cache

        boards: Dict[str, Dict[str, Any]] = {}
        index = self._read_json(index_file) or {}
        for entry in index.get("boards") or []:
            if not isinstance(entry, dict):
                continue
            board = self._read_json(self._board_file(entry.get("id"))) or {}
            merged = {**entry, **board}
            title = str(merged.get("title") or entry.get("title") or "").strip()
            if title:
                boards[title.lower()] = merged

        self._cache_key = (index_file, mtime)
        self._cache = boards
        return boards

    def invalidate(self) -> None:
        """Drop the in-memory catalogue cache."""
        self._cache_key = None
        self._cache = None

    def load(self) -> Dict[str, Any]:
        """
        Load the whole catalogue in the assembled (legacy compatible) shape.

        Returns:
            ``{"version": 2, "boards": {"<title>": {...}}, "tags": {...}}``.

        Example:
            >>> KanbanStore("/proj/.codx/tasks").load()["boards"].keys()
            dict_keys(['Bugs', 'Sprint 12'])
        """
        self.migrate_if_needed()
        index = self._read_json(self._index_file())

        if index is None:
            # Not migrated and nothing to migrate: behave like an empty project.
            legacy = self._read_json(self._path(LEGACY_FILE))
            if legacy:
                logger.warning(
                    "kanban: reading the legacy file at '%s' directly (migration "
                    "did not run)",
                    self._path(LEGACY_FILE),
                )
                return self._assemble_legacy(legacy)
            return {"version": STORE_VERSION, "boards": {}, "tags": {}}

        boards: Dict[str, Any] = {}
        order: List[Tuple[int, str]] = []
        for position, entry in enumerate(index.get("boards") or []):
            if not isinstance(entry, dict):
                continue
            board = self._read_json(self._board_file(entry.get("id"))) or {}
            merged = {**entry, **board}
            title = str(merged.get("title") or entry.get("title") or "").strip()
            if not title:
                continue
            boards[title] = merged
            order.append((int(merged.get("order") or position), title))

        # Preserve the catalogue order so the board list does not jump around.
        ordered = {
            title: boards[title] for _, title in sorted(order, key=lambda item: item[0])
        }
        return {
            "version": index.get("version") or STORE_VERSION,
            "boards": ordered,
            "tags": index.get("tags") or {},
        }

    @staticmethod
    def _assemble_legacy(legacy: Dict[str, Any]) -> Dict[str, Any]:
        """Shape a raw v1 payload like :meth:`load` does."""
        if not legacy.get("version"):
            return {
                "version": STORE_VERSION,
                "boards": legacy if isinstance(legacy.get("boards"), dict) else {},
                "tags": {},
            }
        return legacy

    # ------------------------------------------------------------------
    # Folder resolution (used by ChatManager.get_chat_file)
    # ------------------------------------------------------------------
    def resolve_folders(
        self,
        board: Optional[str],
        column: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Resolve the *folders* of a board/column from their (mutable) titles.

        Because ``title`` is only a label, the storage path of a task must be
        computed from the immutable ``folder``. Two fallbacks keep old projects
        and hand‑edited catalogues working:

        1. when the folder recorded in the catalogue no longer exists on disk,
           an existing directory with the same name (case insensitive) is used,
        2. when the board is unknown, the title itself is used (v1 behaviour).

        Args:
            board: Board title (``Chat.board``).
            column: Column title (``Chat.column``).

        Returns:
            Tuple of ``(board_folder, column_folder)``.

        Example:
            >>> store.resolve_folders("Bugs", "In progress")
            ('Bugs', 'In progress')
        """
        board_title = str(board or DEFAULT_BOARD).strip() or DEFAULT_BOARD
        column_title = str(column or DEFAULT_COLUMN).strip() or DEFAULT_COLUMN

        info = self._catalogue().get(board_title.lower()) or {}
        board_folder = str(info.get("folder") or "").strip() or safe_folder(board_title, DEFAULT_BOARD)

        columns = {}
        for entry in info.get("columns") or []:
            if isinstance(entry, dict) and entry.get("title"):
                columns[str(entry["title"]).strip().lower()] = (
                    str(entry.get("folder") or "").strip() or safe_folder(entry["title"], DEFAULT_COLUMN)
                )
            elif isinstance(entry, str):
                columns[entry.strip().lower()] = safe_folder(entry, DEFAULT_COLUMN)

        column_folder = columns.get(column_title.lower()) or safe_folder(column_title, DEFAULT_COLUMN)

        existing_board = self._existing_dir(self.tasks_path, board_folder)
        if existing_board:
            board_folder = existing_board

        board_abs_path = self._path(board_folder)
        if os.path.isdir(board_abs_path):
            existing_column = self._existing_dir(board_abs_path, column_folder)
            if existing_column:
                column_folder = existing_column

        return board_folder, column_folder

    @staticmethod
    def _existing_dir(parent_path: str, name: str) -> Optional[str]:
        """
        Return the real name of *name* inside *parent_path* (case insensitive).

        Args:
            parent_path: Folder to look into.
            name: Expected directory name.

        Returns:
            The directory name as stored on disk, or None when absent.
        """
        if not name or not os.path.isdir(parent_path):
            return None
        if os.path.isdir(os.path.join(parent_path, name)):
            return name
        wanted = name.strip().lower()
        try:
            for entry in os.listdir(parent_path):
                if entry.strip().lower() == wanted and os.path.isdir(os.path.join(parent_path, entry)):
                    return entry
        except OSError as ex:
            logger.warning("kanban: cannot list '%s': %s", parent_path, ex)
        return None

    def board_dirs(self) -> List[str]:
        """
        Return the folders that hold chats (every directory except ``boards``).

        Returns:
            List of folder names directly under ``tasks``.
        """
        try:
            entries = os.listdir(self.tasks_path)
        except OSError:
            return []
        return sorted(
            entry for entry in entries
            if not entry.startswith(".")
            and entry != BOARDS_DIR
            and os.path.isdir(self._path(entry))
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------
    @staticmethod
    def _iter_boards(raw_boards: Any) -> List[Tuple[str, Dict[str, Any]]]:
        """Normalize ``kanban["boards"]`` (dict or list) into ``[(name, entry)]``."""
        if isinstance(raw_boards, dict):
            return [
                (str(name), entry if isinstance(entry, dict) else {})
                for name, entry in raw_boards.items()
            ]
        if isinstance(raw_boards, list):
            return [
                (
                    str(entry.get("title") or entry.get("name") or entry.get("id") or ""),
                    entry,
                )
                for entry in raw_boards
                if isinstance(entry, dict)
            ]
        return []

    @staticmethod
    def _find_existing(
        existing: Dict[str, Dict[str, Any]],
        board_id: Optional[str],
        title: str,
    ) -> Optional[Dict[str, Any]]:
        """Find a stored board entry by id, then by (case insensitive) title."""
        if board_id and board_id in existing:
            return existing[board_id]
        wanted = (title or "").strip().lower()
        if not wanted:
            return None
        return next(
            (
                entry for entry in existing.values()
                if str(entry.get("title") or "").strip().lower() == wanted
            ),
            None,
        )

    def _normalize_columns(
        self,
        columns: Any,
        previous: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Normalize a board's columns to ``[{id, title, color, folder, order}]``.

        ``id`` and ``folder`` are inherited from *previous* (matched by title)
        so a rename of a column keeps the chats where they are.

        Args:
            columns: Raw columns (list of dicts/strings or a ``{title: {...}}`` dict).
            previous: Columns currently stored for the same board.

        Returns:
            Normalized column list.
        """
        by_title = {
            str(entry.get("title") or "").strip().lower(): entry
            for entry in (previous or [])
            if isinstance(entry, dict) and entry.get("title")
        }

        if isinstance(columns, dict):
            items: List[Any] = [
                {"title": name, **(value if isinstance(value, dict) else {})}
                for name, value in columns.items()
            ]
        elif isinstance(columns, list):
            items = columns
        else:
            items = []

        normalized: List[Dict[str, Any]] = []
        for order, column in enumerate(items):
            if isinstance(column, str):
                column = {"title": column}
            if not isinstance(column, dict):
                continue
            title = str(column.get("title") or column.get("name") or "").strip()
            if not title:
                continue
            previous_column = by_title.get(title.lower()) or {}
            normalized.append({
                "id": column.get("id") or previous_column.get("id") or str(uuid.uuid4()),
                "title": title,
                "color": column.get("color") if column.get("color") is not None
                         else previous_column.get("color") or "",
                "folder": column.get("folder") or previous_column.get("folder")
                          or safe_folder(title, DEFAULT_COLUMN),
                "order": column.get("order") if column.get("order") is not None else order,
            })
        return normalized

    def _normalize_board(
        self,
        name: str,
        entry: Dict[str, Any],
        existing: Dict[str, Dict[str, Any]],
        order: int,
    ) -> Dict[str, Any]:
        """
        Build the definition that will be written for a single board.

        Args:
            name: Key used for the board in the assembled document.
            entry: Board entry as received (may be partial).
            existing: Boards currently stored (keyed by id).
            order: Position of the board in the catalogue.

        Returns:
            The full board definition (id/folder/title/columns always present).
        """
        title = str(entry.get("title") or name or "").strip() or str(entry.get("id") or "board")
        stored = self._find_existing(existing, entry.get("id"), title) or {}

        board_type = str(entry.get("type") or stored.get("type") or BOARD_TYPE_KANBAN).strip().lower()
        folder = (
            entry.get("folder")
            or stored.get("folder")
            or safe_folder(title, DEFAULT_BOARD)
        )

        return {
            **stored,
            **entry,
            "id": entry.get("id") or stored.get("id") or str(uuid.uuid4()),
            "title": title,
            "description": entry.get("description") if entry.get("description") is not None
                           else stored.get("description") or "",
            "type": board_type or BOARD_TYPE_KANBAN,
            "parent_id": entry.get("parent_id", stored.get("parent_id")),
            "folder": folder,
            "columns": self._normalize_columns(
                columns=entry.get("columns", stored.get("columns")),
                previous=stored.get("columns"),
            ),
            "order": order,
        }

    def save(self, kanban: Dict[str, Any]) -> None:
        """
        Persist the assembled catalogue (the shape returned by :meth:`load`).

        The document is diffed against the stored index: boards that are still
        present are rewritten (one file each), boards that disappeared are
        removed, and the index is written last so it is always consistent with
        the board files.

        Args:
            kanban: ``{"version", "boards", "tags"}``.

        Example:
            >>> store.save({"version": 2, "boards": {"Bugs": {...}}, "tags": {}})
        """
        kanban = kanban if isinstance(kanban, dict) else {}
        with self.locked():
            self.migrate_if_needed()
            self.invalidate()

            index = self._read_json(self._index_file()) or {}
            existing = {
                str(entry.get("id")): entry
                for entry in index.get("boards") or []
                if isinstance(entry, dict) and entry.get("id")
            }

            entries: List[Dict[str, Any]] = []
            written_ids = set()

            for order, (name, entry) in enumerate(self._iter_boards(kanban.get("boards"))):
                board = self._normalize_board(
                    name=name, entry=entry, existing=existing, order=order
                )
                board_id = str(board["id"])
                self._write_json(self._board_file(board_id), board)
                written_ids.add(board_id)
                entries.append({
                    "id": board_id,
                    "title": board["title"],
                    "type": board["type"],
                    "parent_id": board.get("parent_id"),
                    "folder": board["folder"],
                    "order": order,
                })

            # Remove the definitions of the boards that are no longer present.
            for board_id in set(existing) - written_ids:
                self.remove_board_files(board_id)

            self._write_json(self._index_file(), {
                "version": STORE_VERSION,
                "boards": entries,
                "tags": kanban.get("tags") or index.get("tags") or {},
            })
            self.invalidate()

        logger.info(
            "kanban: saved %d board(s) for '%s'", len(entries), self.tasks_path
        )

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------
    def remove_board_files(self, board_id: str) -> None:
        """
        Delete the definition folder of *board_id* (chats are not touched).

        Args:
            board_id: Id of the board whose definition to delete.
        """
        board_dir = self._board_dir(board_id)
        if not os.path.isdir(board_dir):
            return
        try:
            shutil.rmtree(board_dir)
        except OSError as ex:
            logger.warning("kanban: cannot remove '%s': %s", board_dir, ex)

    def remove_board(self, title: str) -> bool:
        """
        Remove a board from the catalogue (definition only).

        Args:
            title: Board title (case insensitive).

        Returns:
            True when the board existed and was removed.
        """
        wanted = str(title or "").strip().lower()
        if not wanted:
            return False

        with self.locked():
            self.invalidate()
            index = self._read_json(self._index_file()) or {}
            entries = [
                entry for entry in index.get("boards") or []
                if isinstance(entry, dict)
            ]
            kept = [
                entry for entry in entries
                if str(entry.get("title") or "").strip().lower() != wanted
            ]
            if len(kept) == len(entries):
                return False
            for entry in entries:
                if str(entry.get("title") or "").strip().lower() == wanted:
                    self.remove_board_files(str(entry.get("id")))
            self._write_json(self._index_file(), {
                "version": STORE_VERSION,
                "boards": kept,
                "tags": index.get("tags") or {},
            })
            self.invalidate()

        logger.info("kanban: board '%s' removed from the catalogue", title)
        return True

    @property
    def backup_file(self) -> str:
        """Absolute path of the v1 backup created by the migration."""
        return self._path(BACKUP_FILE)

# Made with ❤️ by codx-junior