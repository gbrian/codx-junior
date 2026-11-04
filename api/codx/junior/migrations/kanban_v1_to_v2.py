"""
Migrate the kanban catalogue from the single ``tasks/kanban.json`` file (v1)
to the split layout (v2): ``tasks/index.json`` + ``tasks/boards/<id>/board.json``.

Why the split
-------------
v1 is read‑modify‑write over one file with no lock, and it is written by the UI
*and* by the tools. Two writers can silently drop a board. v2 keeps one small
file per board plus a light index, so a write touches a single board.

Guarantees of this migration
----------------------------
* **Idempotent**: a board id is derived from the board name
  (``uuid5``), so re-running produces the same ids and files.
* **Non destructive**: the legacy file is copied to
  ``kanban.v1.backup.json`` *before* anything is written, and it is only removed
  after every board file has been written and verified.
* **Folder preserving**: the folder of every board and column is the name that
  is already used on disk, so no chat has to be moved.

Made with ❤️ by codx-junior
"""

import json
import logging
import os
import shutil
import uuid
from typing import Any, Dict, List, Optional

from codx.junior.kanban.model import (
    BACKUP_FILE,
    BOARD_FILE,
    BOARDS_DIR,
    BOARD_TYPE_KANBAN,
    BOARD_TYPE_SPRINT,
    INDEX_FILE,
    LEGACY_FILE,
    LEGACY_VERSION,
    STORE_VERSION,
    safe_folder,
)

logger = logging.getLogger(__name__)

# Namespace used to derive a STABLE board id from its name.
_ID_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")


def stable_board_id(tasks_path: str, name: str) -> str:
    """
    Return the deterministic id of a board.

    Using ``uuid5`` keeps the migration idempotent: migrating twice, or loading
    a project whose index was lost, regenerates the same ids instead of
    duplicating the boards.

    Args:
        tasks_path: Absolute ``tasks`` folder (scopes the id to the project).
        name: Board name/title.

    Returns:
        A UUID string.
    """
    return str(uuid.uuid5(_ID_NAMESPACE, f"{tasks_path}::{name}"))


def _read_json(file_path: str) -> Optional[dict]:
    """Read a JSON file, returning None when it is missing or unreadable."""
    if not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.loads(handle.read())
        return data if isinstance(data, dict) else None
    except (OSError, ValueError) as ex:
        logger.warning("kanban migration: cannot read '%s': %s", file_path, ex)
        return None


def _write_json(file_path: str, data: dict) -> None:
    """Write JSON atomically (temporary file + ``os.replace``)."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    tmp_path = f"{file_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(data, indent=2))
    os.replace(tmp_path, file_path)


def _board_type(entry: Dict[str, Any]) -> str:
    """Return the canonical board type of a legacy entry."""
    board_type = str(entry.get("type") or "").strip().lower()
    if board_type in (BOARD_TYPE_KANBAN, BOARD_TYPE_SPRINT):
        return board_type
    return BOARD_TYPE_SPRINT if entry.get("sprint") else BOARD_TYPE_KANBAN


def _columns(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalize the columns of a legacy board entry.

    Legacy files store columns either as ``{"<title>": {...}}`` or as a list of
    ``{"title": ...}`` dicts (and, in the oldest ones, as plain strings).
    """
    raw = entry.get("columns")
    if isinstance(raw, dict):
        items = [{"title": name, **(value if isinstance(value, dict) else {})}
                 for name, value in raw.items()]
    elif isinstance(raw, list):
        items = raw
    else:
        items = []

    columns: List[Dict[str, Any]] = []
    for order, column in enumerate(items):
        if isinstance(column, str):
            column = {"title": column}
        if not isinstance(column, dict):
            continue
        title = (column.get("title") or column.get("name") or "").strip()
        if not title:
            continue
        columns.append({
            "id": column.get("id") or str(uuid.uuid4()),
            "title": title,
            "color": column.get("color") or "",
            # Existing chats live in a directory named after the column.
            "folder": column.get("folder") or safe_folder(title, default="tasks"),
            "order": column.get("order") if column.get("order") is not None else order,
        })
    return columns


def _boards(legacy: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return a normalized ``[(name, entry), ...]`` list from a legacy payload."""
    raw = legacy.get("boards")
    if isinstance(raw, dict):
        return [(str(name), entry if isinstance(entry, dict) else {})
                for name, entry in raw.items()]
    if isinstance(raw, list):
        return [
            (str(entry.get("title") or entry.get("name") or entry.get("id") or ""),
             entry)
            for entry in raw
            if isinstance(entry, dict)
        ]
    return []


def migrate_kanban_v1_to_v2(tasks_path: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Convert ``tasks/kanban.json`` into the v2 layout.

    Args:
        tasks_path: Absolute path of the project's ``tasks`` folder.
        dry_run: Compute the result without writing anything (used by tests and
            by the migration report).

    Returns:
        A summary dict: ``{"migrated", "boards", "index_file", "backup_file"}``.

    Example:
        >>> migrate_kanban_v1_to_v2("/proj/.codx/tasks")["boards"]
        3
    """
    tasks_path = str(tasks_path)
    legacy_path = os.path.join(tasks_path, LEGACY_FILE)
    index_path = os.path.join(tasks_path, INDEX_FILE)
    backup_path = os.path.join(tasks_path, BACKUP_FILE)

    summary = {
        "migrated": False,
        "boards": 0,
        "index_file": index_path,
        "backup_file": backup_path,
    }

    if os.path.isfile(index_path):
        logger.info("kanban migration: already migrated (%s exists)", index_path)
        return summary

    legacy = _read_json(legacy_path)
    if legacy is None:
        logger.info("kanban migration: no legacy file at %s, nothing to do", legacy_path)
        return summary

    # v1 files without a version envelope stored the boards at the root level.
    if not legacy.get("version"):
        legacy = {"version": LEGACY_VERSION, "boards": legacy, "tags": {}}

    entries: List[Dict[str, Any]] = []
    board_files: List[tuple] = []

    for order, (name, entry) in enumerate(_boards(legacy)):
        title = (entry.get("title") or name or "").strip() or f"board-{order}"
        board_id = stable_board_id(tasks_path, title)
        folder = entry.get("folder") or safe_folder(title)
        board = {
            **entry,
            "id": board_id,
            "title": title,
            "description": entry.get("description") or "",
            "type": _board_type(entry),
            "parent_id": entry.get("parent_id"),
            # The folder already holds the tasks: never move it here.
            "folder": folder,
            "columns": _columns(entry),
            "order": order,
        }
        entries.append({
            "id": board_id,
            "title": title,
            "type": board["type"],
            "parent_id": board.get("parent_id"),
            "folder": folder,
            "order": order,
        })
        board_files.append((os.path.join(tasks_path, BOARDS_DIR, board_id, BOARD_FILE), board))

    summary["boards"] = len(entries)

    if dry_run:
        summary["migrated"] = True
        return summary

    # Back up the legacy file BEFORE writing anything.
    try:
        shutil.copy2(legacy_path, backup_path)
    except OSError as ex:
        logger.error("kanban migration: cannot back up '%s': %s", legacy_path, ex)
        return summary

    for file_path, board in board_files:
        _write_json(file_path, board)

    _write_json(index_path, {
        "version": STORE_VERSION,
        "boards": entries,
        "tags": legacy.get("tags") or {},
    })

    written = sum(
        1 for file_path, _ in board_files if os.path.isfile(file_path)
    )
    if written != len(board_files):
        logger.error(
            "kanban migration: %d of %d board files written, keeping the legacy "
            "file in place",
            written,
            len(board_files),
        )
        return summary

    try:
        os.remove(legacy_path)
    except OSError as ex:
        logger.warning("kanban migration: cannot remove '%s': %s", legacy_path, ex)

    summary["migrated"] = True
    logger.info(
        "kanban migration: %d board(s) migrated (%s -> %s)",
        len(entries),
        legacy_path,
        index_path,
    )
    return summary

# Made with ❤️ by codx-junior