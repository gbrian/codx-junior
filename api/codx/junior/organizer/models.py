"""
Typed models for the chat organization decision process.

An "organization decision" answers a single closed question:

    On which board — and inside which column — should this chat live?

The models are engine-agnostic on purpose: any decision engine (a local typed
model, an LLM prompt, a rule set, ...) must return a :class:`ChatOrganization`
that is validated against the project's own catalogue
(:class:`OrganizationContext`), so an engine can never invent a board or a
column that does not exist.

```mermaid
classDiagram
    class OrganizationContext {
        +List~BoardInfo~ boards
        +str default_board
        +str default_column
        +board_names() List~str~
        +columns_for(board) List~str~
        +all_columns() List~str~
        +canonical_board(name) Optional~str~
        +canonical_column(board, column) Optional~str~
        +is_complete() bool
    }
    class BoardInfo {
        +str name
        +str description
        +List~BoardColumn~ columns
    }
    class BoardColumn {
        +str title
    }
    class ChatOrganization {
        +str board
        +str column
        +Optional~str~ priority
        +str engine
        +Optional~float~ confidence
        +bool abstained
        +str reason
        +as_metadata() dict
    }
    OrganizationContext "1" o-- "many" BoardInfo
    BoardInfo "1" o-- "many" BoardColumn
```
"""

import logging
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Defaults mirroring codx.junior.chat_manager (used when nothing is decided).
DEFAULT_BOARD = "kanban"
DEFAULT_COLUMN = "tasks"

# Column a caller may use to park a chat when no engine can decide confidently.
REVIEW_COLUMN = "review"

# Allowed task priorities (mirrors the Chat.priority field description).
PRIORITIES = ["high", "medium", "low"]


class BoardColumn(BaseModel):
    """A single column belonging to a board."""

    title: str = Field(default="", description="Column title as shown on the board")


class BoardInfo(BaseModel):
    """A board and the columns it exposes (built from ``tasks/kanban.json``)."""

    name: str = Field(default="", description="Board name (used as the chat folder name)")
    description: str = Field(default="", description="Free text describing the board purpose")
    columns: List[BoardColumn] = Field(
        default_factory=list, description="Columns available on this board"
    )

    def column_titles(self) -> List[str]:
        """Return the non-empty column titles of this board."""
        return [c.title for c in self.columns if c.title and c.title.strip()]


class OrganizationContext(BaseModel):
    """
    The catalogue of valid chat destinations.

    Built from the project's kanban configuration so every engine decides
    against the *same* closed set of boards and columns.
    """

    boards: List[BoardInfo] = Field(
        default_factory=list, description="Boards available in the project"
    )
    default_board: str = Field(default=DEFAULT_BOARD)
    default_column: str = Field(default=DEFAULT_COLUMN)

    # -- lookup helpers -----------------------------------------------------

    def board_names(self) -> List[str]:
        """Return the names of all known boards."""
        return [b.name for b in self.boards if b.name]

    def columns_for(self, board: Optional[str]) -> List[str]:
        """Return the column titles of *board* (empty when the board is unknown)."""
        canonical = self.canonical_board(board)
        if not canonical:
            return []
        found = next((b for b in self.boards if b.name == canonical), None)
        return found.column_titles() if found else []

    def all_columns(self) -> List[str]:
        """Union of every column title across all boards (de-duplicated, ordered)."""
        seen, columns = set(), []
        for board in self.boards:
            for title in board.column_titles():
                if title.lower() not in seen:
                    seen.add(title.lower())
                    columns.append(title)
        return columns

    def has_board(self, name: Optional[str]) -> bool:
        """True when *name* matches a known board (case-insensitive)."""
        return self.canonical_board(name) is not None

    @staticmethod
    def _normalize(value: Optional[str]) -> str:
        return (value or "").strip().lower()

    def canonical_board(self, name: Optional[str]) -> Optional[str]:
        """Return the board name as spelled in the catalogue (case-insensitive)."""
        wanted = self._normalize(name)
        if not wanted:
            return None
        return next(
            (b.name for b in self.boards if self._normalize(b.name) == wanted), None
        )

    def canonical_column(self, board: Optional[str], column: Optional[str]) -> Optional[str]:
        """Return the column title as spelled on *board* (case-insensitive)."""
        wanted = self._normalize(column)
        if not wanted:
            return None
        return next(
            (c for c in self.columns_for(board) if self._normalize(c) == wanted), None
        )

    def first_column(self, board: Optional[str]) -> Optional[str]:
        """Return the first column of *board* (used as a safe fallback)."""
        columns = self.columns_for(board)
        return columns[0] if columns else None

    def is_complete(self) -> bool:
        """True when there is at least one board exposing at least one column."""
        return any(b.column_titles() for b in self.boards)


class ChatOrganization(BaseModel):
    """
    A validated proposal of where a chat should live.

    ``engine`` records which decision engine produced the proposal
    (``"structured"``, ``"llm"``, ...) so behaviour can be traced and changed
    without touching callers. ``abstained`` means the engine had no confident
    match and the caller should keep trying the next engine.
    """

    board: str = Field(default="", description="Target board name")
    column: str = Field(default="", description="Target column title")
    priority: Optional[str] = Field(
        default=None, description="Task priority: 'high' | 'medium' | 'low'"
    )
    engine: str = Field(default="", description="Engine that produced this decision")
    confidence: Optional[float] = Field(
        default=None, description="Engine confidence in [0, 1] when available"
    )
    abstained: bool = Field(
        default=False, description="Engine refused to decide; caller should fall back"
    )
    reason: str = Field(default="", description="Human readable explanation (logging)")

    def as_metadata(self, include_priority: bool = True) -> dict:
        """
        Shape the decision as an ``ChatManager.update_chat_metadata`` payload.

        :param include_priority: Include ``priority`` when the engine provided one.
        :return: Dict with ``board``/``column`` (and optionally ``priority``).
        """
        metadata = {"board": self.board, "column": self.column}
        if include_priority and self.priority:
            metadata["priority"] = self.priority
        return metadata


# Made with ❤️ by codx-junior