"""
Shared constants and helpers of the kanban storage.

The kanban catalogue lives in ``<codx_path>/tasks`` and is stored in **v2
format** (see :mod:`codx.junior.kanban.store`):

```
.codx/tasks/
  index.json                       { version: 2, boards: [ {id,title,type,parent_id,folder,order} ], tags }
  boards/<board_id>/board.json     { id,title,description,type,parent_id,folder,columns:[{id,title,color,folder,order}] }
  <folder>/<column_folder>/<slug>.<chat_id>.json
```

``folder`` is **immutable**: it is the name of the directory that holds the
board/column chats. ``title`` is only a label, so renaming a board or a column
changes nothing on disk and no task has to be rewritten.

This module must stay dependency free (no imports from the rest of codx-junior)
because both the store and the migration import it.

Made with ❤️ by codx-junior
"""

import os
import re

# Bumped whenever the on-disk layout changes in a breaking way.
STORE_VERSION = 2

# Version reported by the legacy (v1) single-file layout.
LEGACY_VERSION = 0.1

INDEX_FILE = "index.json"
BOARDS_DIR = "boards"
BOARD_FILE = "board.json"
LEGACY_FILE = "kanban.json"
BACKUP_FILE = "kanban.v1.backup.json"
LOCK_FILE = ".kanban.lock"

DEFAULT_BOARD = "kanban"
DEFAULT_COLUMN = "tasks"
BOARD_TYPE_KANBAN = "kanban"
BOARD_TYPE_SPRINT = "sprint"

# Characters that can never appear in a directory name used as a folder.
_INVALID_FOLDER_CHARS = re.compile(r'[/\\\x00-\x1f]')


def safe_folder(name: str, default: str = "board") -> str:
    """
    Convert a board/column *title* into a directory name.

    The original case and spaces are preserved on purpose: existing projects
    already have folders such as ``To do`` or ``tasks``, and changing them would
    orphan every stored chat.

    Args:
        name: Board or column title.
        default: Value used when the title has no usable characters.

    Returns:
        A path separator free folder name.

    Example:
        >>> safe_folder("To do")
        'To do'
        >>> safe_folder("api/ui")
        'api-ui'
    """
    folder = _INVALID_FOLDER_CHARS.sub("-", str(name or "")).strip()
    folder = folder.strip(".").strip()
    return folder or default


def is_store_file(file_path: str) -> bool:
    """
    Tell whether *file_path* is part of the storage itself (not a chat).

    ``.codx/tasks`` holds both the chats and the catalogue, so any code that
    walks the tree for chats must skip ``index.json``, the legacy
    ``kanban.json`` and everything under ``boards/``.

    Args:
        file_path: Absolute or relative file path.

    Returns:
        True when the path belongs to the kanban storage.
    """
    base = os.path.basename(file_path)
    if base in (INDEX_FILE, LEGACY_FILE, BACKUP_FILE, LOCK_FILE):
        return True
    parts = os.path.normpath(file_path).split(os.sep)
    return BOARDS_DIR in parts

# Made with ❤️ by codx-junior