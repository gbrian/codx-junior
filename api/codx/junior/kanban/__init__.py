"""
Kanban catalogue package.

The kanban catalogue (boards, sprints and columns) lives in the project's
``.codx/tasks`` folder and is accessed through :class:`KanbanStore`, which owns
the v2 on-disk layout, the cross-process lock, the migration from the legacy
single ``kanban.json`` file and the folder resolution used to store chats.

Why this package is import-safe
-------------------------------
The previous ``__init__`` imported ``kanban.board_status_review`` — a module
that does not exist in this repository — so **any** ``import
codx.junior.kanban`` raised ``ModuleNotFoundError`` and took down every caller.
The public names are now resolved lazily through :func:`__getattr__`: importing
the package is free, and a missing optional submodule only fails when the
symbol is actually used.

Public API:

    - :class:`KanbanStore`          : v2 catalogue persistence (load/save/lock).
    - :func:`resolve_folders`       : title -> immutable folder resolution.
    - :data:`DEFAULT_BOARD` / :data:`DEFAULT_COLUMN` : catalogue defaults.

Made with ❤️ by codx-junior
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_LAZY_EXPORTS = {
    "KanbanStore": ("codx.junior.kanban.store", "KanbanStore"),
    "resolve_folders": ("codx.junior.kanban.store", None),  # handled below
    "DEFAULT_BOARD": ("codx.junior.kanban.model", "DEFAULT_BOARD"),
    "DEFAULT_COLUMN": ("codx.junior.kanban.model", "DEFAULT_COLUMN"),
    "STORE_VERSION": ("codx.junior.kanban.model", "STORE_VERSION"),
    "safe_folder": ("codx.junior.kanban.model", "safe_folder"),
}

__all__ = [
    "KanbanStore",
    "resolve_folders",
    "DEFAULT_BOARD",
    "DEFAULT_COLUMN",
    "STORE_VERSION",
    "safe_folder",
]


def resolve_folders(tasks_path: str, board: str, column: str = None):
    """
    Resolve the storage folders of a board/column without instantiating a store.

    Convenience helper for callers that only need the path of a task.

    Args:
        tasks_path: Absolute ``<codx_path>/tasks`` folder.
        board: Board title (``Chat.board``).
        column: Column title (``Chat.column``).

    Returns:
        Tuple ``(board_folder, column_folder)``.
    """
    from codx.junior.kanban.store import KanbanStore

    return KanbanStore(tasks_path=tasks_path).resolve_folders(
        board=board, column=column
    )


def __getattr__(name: str) -> Any:
    """
    Resolve the public names lazily (PEP 562).

    Args:
        name: Attribute being accessed.

    Returns:
        The imported attribute.

    Raises:
        AttributeError: When the name is not part of the public API.
    """
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module_name, attribute = target
    module = import_module(module_name)
    return getattr(module, name if attribute is None else attribute)

# Made with ❤️ by codx-junior