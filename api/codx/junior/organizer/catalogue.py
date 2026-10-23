"""
Builds the chat destination catalogue (boards + columns) from the project's
kanban configuration.

``ChatManager.load_kanban()`` reads ``<codx_path>/tasks/kanban.json`` whose
shape is::

    {
      "version": 0.1,
      "boards": {
        "<board name>": {
          "description": "Backlog board",
          "columns": [{"title": "Backlog", "id": "..."}, ...]
        }
      },
      "tags": {}
    }

The catalogue is the *single source of truth* for valid destinations, so a
decision engine can be validated against real boards without inventing names.
"""

import logging
from typing import Any, List, Optional

from codx.junior.organizer.models import (
    DEFAULT_BOARD,
    DEFAULT_COLUMN,
    BoardColumn,
    BoardInfo,
    OrganizationContext,
)

logger = logging.getLogger(__name__)


def _column_title(column: Any) -> str:
    """
    Normalise a kanban column entry to its title.

    Columns are ``{"title": ...}`` dicts in ``tasks/kanban.json``; older
    configurations may still store plain strings.
    """
    if isinstance(column, dict):
        return column.get("title") or ""
    return str(column or "")


def build_context_from_kanban(
    kanban: Optional[dict],
    default_board: str = DEFAULT_BOARD,
    default_column: str = DEFAULT_COLUMN,
) -> OrganizationContext:
    """
    Convert a ``ChatManager.load_kanban()`` payload into an OrganizationContext.

    Missing/ malformed entries are skipped rather than raising, so a partially
    broken ``kanban.json`` never breaks the organization process.

    :param kanban: Kanban payload (``{"version", "boards", "tags"}``).
    :param default_board: Board used as default when nothing is decided.
    :param default_column: Column used as default when nothing is decided.
    :return: The validated destination catalogue.
    """
    boards: List[BoardInfo] = []
    raw_boards = (kanban or {}).get("boards") or {}

    for name, board in raw_boards.items():
        board = board if isinstance(board, dict) else {}
        columns: List[BoardColumn] = []
        for column in board.get("columns") or []:
            title = _column_title(column)
            if title and title.strip():
                columns.append(BoardColumn(title=title.strip()))
        boards.append(
            BoardInfo(
                name=name,
                description=board.get("description") or "",
                columns=columns,
            )
        )

    if not boards:
        logger.warning("No boards found in the project kanban configuration")

    context = OrganizationContext(
        boards=boards,
        default_board=default_board,
        default_column=default_column,
    )
    logger.debug(
        "Organization catalogue: %d boards, %d distinct columns",
        len(context.boards),
        len(context.all_columns()),
    )
    return context


def build_context(chat_manager) -> OrganizationContext:
    """
    Build the destination catalogue for a project.

    :param chat_manager: A ``codx.junior.chat_manager.ChatManager`` instance.
    :return: The validated destination catalogue (empty when loading fails).
    """
    kanban = None
    try:
        kanban = chat_manager.load_kanban()
    except Exception as ex:  # never let catalogue loading break a chat
        logger.warning("Could not load kanban configuration: %s", ex)
    return build_context_from_kanban(kanban)


# Made with ❤️ by codx-junior