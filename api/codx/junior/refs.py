"""
Item refs (quick refs): the single source of truth for the links models and
clients use to point at codx-junior items.

Why a module instead of instructions in the system prompt
---------------------------------------------------------
The model must never *compose* an item reference: it copies one from a tool
result or from the per-turn ``<item_refs>`` block. Keeping the grammar in code
means the format can change without touching a prompt, and that every builder
and parser (tools, API, post-processing) agrees on the exact same string.

Format
------
    codx://<entity>/<id>[/<sub-entity>/<sub-id>][?project=<project_id>]

    codx://chat/<chat_id>                            a chat or a task
    codx://chat/<chat_id>/message/<message_doc_id>   a message inside a chat
    codx://board/<board_name>                        a kanban board
    codx://board/<board_name>/column/<column_name>   a board column
    codx://profile/<profile_name>                    a profile
    codx://file/<project_relative_path>              a project file
    codx://project/<project_id>                      a project

``project`` is optional: when omitted the ref belongs to the project the client
is currently showing, so same-project links stay short. It is emitted when the
item lives somewhere else — chats can be owned by another project
(``Chat.owner_project_id``) and ``Chat.chat_links`` already models that.

Identifiers
-----------
    - chats/tasks: ``Chat.id`` (UUID). A task IS a chat, so there is no
      ``task`` entity.
    - messages: ``Message.doc_id`` (messages have no ``id``), always nested
      under their chat because messages are stored inside the chat file.
    - boards/columns: their **name** (``.codx/tasks/<board>/<column>/``),
      URL encoded. ``KanbanColumn.doc_id`` exists in the model but
      ``kanban.json`` is keyed by name, so names are today's only stable key.
    - profiles: profile name. files: project-relative path.

Rendering
---------
Refs are always rendered as Markdown links (``[label](codx://...)``) so any
renderer that does not understand the scheme still shows the label instead of a
raw URL. :func:`link` builds them with a sanitised label (no newlines, no
brackets, truncated) so a tool can never emit invalid Markdown.

Reverse direction
-----------------
:func:`parse_ref` / :func:`find_refs` are the only correct way to read a ref
back: client-side routing, ``GET /api/refs/resolve``, dead-link detection and
``Message.meta_data["refs"]`` extraction. A ref is a NAVIGATION HINT, never an
authorisation: the resolver must re-check existence and permissions.

Made with ❤️ by codx-junior
"""
import logging
import re

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import parse_qs, quote, unquote, urlsplit

logger = logging.getLogger(__name__)

# ── Scheme ─────────────────────────────────────────────────────────────────────

# Single scheme with the entity as the first path segment: adding an entity
# (or a sub-resource) never requires a new scheme nor a new client setting.
SCHEME: str = "codx"
URI_PREFIX: str = f"{SCHEME}://"

# ── Entities ───────────────────────────────────────────────────────────────────

ENTITY_CHAT: str = "chat"
ENTITY_MESSAGE: str = "message"
ENTITY_BOARD: str = "board"
ENTITY_COLUMN: str = "column"
ENTITY_PROFILE: str = "profile"
ENTITY_FILE: str = "file"
ENTITY_PROJECT: str = "project"

# Entities addressable as the FIRST path segment. ``message`` and ``column`` are
# NOT here on purpose: they only exist as sub-resources of a chat/board.
ENTITIES = (
    ENTITY_CHAT,
    ENTITY_BOARD,
    ENTITY_PROFILE,
    ENTITY_FILE,
    ENTITY_PROJECT,
)

# Allowed ``<entity>/<id>/<sub-entity>/<sub-id>`` combinations.
ALLOWED_SUB_ENTITIES: Dict[str, tuple] = {
    ENTITY_CHAT: (ENTITY_MESSAGE,),
    ENTITY_BOARD: (ENTITY_COLUMN,),
}

# Query parameter carrying the project the item belongs to.
PROJECT_PARAM: str = "project"

# ── Limits ─────────────────────────────────────────────────────────────────────

# Maximum characters of a link label. Long message excerpts would otherwise
# inflate the content and break the readability of the answer.
MAX_LABEL_CHARS: int = 120

# Characters of an id kept for display purposes ("quick ref" / short id).
SHORT_ID_CHARS: int = 8

# Matches a raw ref inside free text. Excludes whitespace and the characters
# that close a Markdown link so ``[t](codx://x)`` yields ``codx://x``.
_REF_PATTERN = re.compile(rf"{SCHEME}://[^\s<>()\[\]\"']+")

_WHITESPACE_PATTERN = re.compile(r"\s+")

# Trailing punctuation captured by _REF_PATTERN at the end of a sentence.
_TRAILING_PUNCTUATION = ".,;:!?"


# ── Value helpers ──────────────────────────────────────────────────────────────


def short_id(value: Any, chars: int = SHORT_ID_CHARS) -> str:
    """
    Return the short (display only) form of an item id.

    Short ids are a convenience for tables and labels: they are ambiguous by
    design and MUST NOT be used inside a ref (``ChatManager.find_by_id``
    matches ``chat_id in path``, so two chats sharing a prefix resolve to the
    first one found).

    Args:
        value: Item object (``.id``/``.doc_id``) or id string.
        chars: Number of characters to keep.

    Returns:
        The leading ``chars`` characters of the id, or an empty string.
    """
    identifier = _value_of(value, "id") or _value_of(value, "doc_id")
    return identifier[:chars] if identifier else ""


def _value_of(item: Any, attribute: str = "id") -> str:
    """
    Return the string value of *item* (either the attribute or *item* itself).

    Args:
        item: Model instance (Chat, Message, ...) or plain string.
        attribute: Attribute to read from a model instance.

    Returns:
        Stripped string value, or an empty string when unavailable.
    """
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    return str(getattr(item, attribute, "") or "").strip()


def _project_hint(item_project_id: Optional[str], current_project_id: Optional[str]) -> Optional[str]:
    """
    Return the project to add to a ref, or ``None`` when the current one works.

    Same-project refs stay short (no ``?project=``); a ref to an item owned by
    another project is qualified so the client can switch context before
    navigating.

    Args:
        item_project_id: Project that owns the item.
        current_project_id: Project the client is currently showing.

    Returns:
        The item project id when it differs from the current one, else None.
    """
    item_project = (item_project_id or "").strip()
    current_project = (current_project_id or "").strip()
    if not item_project or item_project == current_project:
        return None
    return item_project


def _encode(segment: Any) -> str:
    """Percent-encode a single path segment (``/`` and spaces included)."""
    return quote(str(segment if segment is not None else "").strip(), safe="")


# ── Builders ───────────────────────────────────────────────────────────────────


def _build_ref(
    entity: str,
    item_id: Any,
    sub_entity: Optional[str] = None,
    sub_id: Any = None,
    project_id: Optional[str] = None,
) -> str:
    """
    Assemble a ref from already-resolved parts.

    Args:
        entity: Entity name (``chat``, ``board``, ...).
        item_id: Primary identifier (chat id, board name, ...).
        sub_entity: Optional sub-resource entity (``message``, ``column``).
        sub_id: Sub-resource identifier (message doc_id, column name).
        project_id: Optional owning project.

    Returns:
        The ``codx://`` ref.

    Raises:
        ValueError: When the entity or the identifier is missing/invalid.
    """
    entity = (entity or "").strip().lower()
    identifier = str(item_id or "").strip()
    if not entity or not identifier:
        raise ValueError("A ref needs an entity and an id")
    if entity not in ENTITIES:
        raise ValueError(
            f"Unknown ref entity '{entity}' (valid entities: {', '.join(ENTITIES)})"
        )

    segments: List[Any] = [entity, identifier]

    sub_entity = (sub_entity or "").strip().lower()
    if sub_entity:
        if sub_entity not in ALLOWED_SUB_ENTITIES.get(entity, ()):
            raise ValueError(
                f"Entity '{entity}' does not accept sub-entity '{sub_entity}'"
                f" (valid: {', '.join(ALLOWED_SUB_ENTITIES.get(entity, ()))})"
            )
        sub_identifier = str(sub_id or "").strip()
        if not sub_identifier:
            raise ValueError(f"Sub-entity '{sub_entity}' needs an id")
        segments.extend([sub_entity, sub_identifier])

    ref = f"{URI_PREFIX}{'/'.join(_encode(segment) for segment in segments)}"
    if project_id and str(project_id).strip():
        ref = f"{ref}?{PROJECT_PARAM}={_encode(project_id)}"
    return ref


def chat_ref(chat: Any, project_id: Optional[str] = None) -> str:
    """
    Build the ref of a chat (or task, which is a chat).

    Args:
        chat: Chat object or chat id.
        project_id: Optional owning project id.

    Returns:
        ``codx://chat/<chat_id>`` (plus ``?project=`` when given).

    Example:
        >>> chat_ref("5f0e1a2b-...")
        'codx://chat/5f0e1a2b-...'
    """
    return _build_ref(ENTITY_CHAT, _value_of(chat, "id"), project_id=project_id)


def message_ref(chat: Any, message: Any, project_id: Optional[str] = None) -> str:
    """
    Build the ref of a message inside its chat.

    The chat is mandatory: messages are stored inside the chat file, so there is
    no way to resolve a message without knowing its chat.

    Args:
        chat: Chat object or chat id.
        message: Message object or ``doc_id``.
        project_id: Optional owning project id.

    Returns:
        ``codx://chat/<chat_id>/message/<message_doc_id>``.

    Raises:
        ValueError: When the chat id or the message ``doc_id`` is missing.
    """
    return _build_ref(
        ENTITY_CHAT,
        _value_of(chat, "id"),
        sub_entity=ENTITY_MESSAGE,
        sub_id=_value_of(message, "doc_id"),
        project_id=project_id,
    )


def board_ref(board: Any, project_id: Optional[str] = None) -> str:
    """
    Build the ref of a kanban board (boards are identified by name).

    Args:
        board: Board name (or a board dict/object with ``name``/``title``).
        project_id: Optional owning project id.

    Returns:
        ``codx://board/<board_name>``.
    """
    name = _value_of(board, "name") or _value_of(board, "title")
    return _build_ref(ENTITY_BOARD, name, project_id=project_id)


def column_ref(board: Any, column: Any, project_id: Optional[str] = None) -> str:
    """
    Build the ref of a column inside its board.

    Args:
        board: Board name (or board dict/object).
        column: Column name (or column dict with ``title``/``name``).
        project_id: Optional owning project id.

    Returns:
        ``codx://board/<board_name>/column/<column_name>``.

    Raises:
        ValueError: When the column name is missing.
    """
    column_name = _value_of(column, "title") or _value_of(column, "name")
    return _build_ref(
        ENTITY_BOARD,
        _value_of(board, "name") or _value_of(board, "title"),
        sub_entity=ENTITY_COLUMN,
        sub_id=column_name,
        project_id=project_id,
    )


def profile_ref(profile: Any, project_id: Optional[str] = None) -> str:
    """Build the ref of a profile (identified by name)."""
    return _build_ref(
        ENTITY_PROFILE,
        _value_of(profile, "name") or _value_of(profile, "id"),
        project_id=project_id,
    )


def file_ref(path: Any, project_id: Optional[str] = None) -> str:
    """
    Build the ref of a project file (identified by its project-relative path).

    Leading slashes are stripped so the same file always renders the same ref.
    """
    value = str(path or "").strip()
    return _build_ref(ENTITY_FILE, value.lstrip("/"), project_id=project_id)


def project_ref(project_id: Any) -> str:
    """Build the ref of a project (identified by its project id)."""
    return _build_ref(ENTITY_PROJECT, project_id)


def ref_for(
    entity: str,
    item_id: Any,
    chat_id: Optional[str] = None,
    board: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    """
    Build a ref from an entity name and its identifier.

    Generic entry point used by the ``item_ref`` tool so the tool never has to
    know how each ref is assembled.

    Args:
        entity: One of ``chat``, ``message``, ``board``, ``column``,
            ``profile``, ``file`` or ``project``.
        item_id: Primary id (chat id, message doc_id, board/profile name, path).
        chat_id: Parent chat id (required for ``message``).
        board: Parent board name (required for ``column``).
        project_id: Optional owning project id.

    Returns:
        The ref string.

    Raises:
        ValueError: When the entity is unknown or a required parent is missing.
    """
    entity = (entity or "").strip().lower()

    if entity == ENTITY_CHAT:
        return chat_ref(item_id, project_id=project_id)
    if entity == ENTITY_MESSAGE:
        if not chat_id:
            raise ValueError("A message ref requires the parent chat_id")
        return _build_ref(
            ENTITY_CHAT,
            chat_id,
            sub_entity=ENTITY_MESSAGE,
            sub_id=item_id,
            project_id=project_id,
        )
    if entity == ENTITY_BOARD:
        return board_ref(item_id, project_id=project_id)
    if entity == ENTITY_COLUMN:
        if not board:
            raise ValueError("A column ref requires the parent board")
        return _build_ref(
            ENTITY_BOARD,
            board,
            sub_entity=ENTITY_COLUMN,
            sub_id=item_id,
            project_id=project_id,
        )
    if entity == ENTITY_PROFILE:
        return profile_ref(item_id, project_id=project_id)
    if entity == ENTITY_FILE:
        return file_ref(item_id, project_id=project_id)
    if entity == ENTITY_PROJECT:
        return project_ref(item_id)

    raise ValueError(
        f"Unknown ref entity '{entity}' (valid entities: "
        f"{', '.join(ENTITIES + (ENTITY_MESSAGE, ENTITY_COLUMN))})"
    )


# ── Rendering ──────────────────────────────────────────────────────────────────


def sanitize_label(
    text: Any,
    max_chars: int = MAX_LABEL_CHARS,
    fallback: str = "item",
) -> str:
    """
    Make any text safe to use as the label of a Markdown link.

    Newlines are collapsed, backticks removed and square brackets replaced by
    parentheses: ``[`` / ``]`` inside a link label would terminate the label and
    produce broken Markdown.

    Args:
        text: Raw label (may contain Markdown, newlines, brackets...).
        max_chars: Maximum length of the label.
        fallback: Label used when *text* is empty.

    Returns:
        A single-line label, truncated with an ellipsis when too long.
    """
    value = _WHITESPACE_PATTERN.sub(" ", str(text or "")).strip()
    value = value.replace("`", "").replace("[", "(").replace("]", ")")
    if len(value) > max_chars:
        value = value[: max(1, max_chars - 1)].rstrip() + "…"
    return value or fallback


def link(label: Any, ref: str, max_chars: int = MAX_LABEL_CHARS) -> str:
    """
    Render a ref as a Markdown link with a sanitised label.

    Args:
        label: Human label (chat name, message excerpt, ...).
        ref: The ``codx://`` ref (see :func:`chat_ref` and friends).
        max_chars: Maximum label length.

    Returns:
        ``[label](ref)`` ready to be embedded in a message.
    """
    return f"[{sanitize_label(label, max_chars=max_chars)}]({ref})"


def chat_label(chat: Any) -> str:
    """Return the display label of a chat (its name, else its short id)."""
    name = _value_of(chat, "name")
    if name:
        return name
    identifier = _value_of(chat, "id")
    return f"Chat {identifier[:SHORT_ID_CHARS]}" if identifier else "Chat"


def message_label(message: Any, max_chars: int = 80) -> str:
    """
    Return a display label for a message: its first meaningful line.

    Args:
        message: Message object (may be None).
        max_chars: Maximum length of the label.

    Returns:
        First line of the content (truncated), or ``"<role> message"``.
    """
    content = str(getattr(message, "content", "") or "").strip()
    for line in content.splitlines():
        cleaned = line.strip().lstrip("#>*- ").strip()
        if cleaned:
            return sanitize_label(cleaned, max_chars=max_chars, fallback="message")
    role = str(getattr(message, "role", "") or "").strip() or "message"
    return sanitize_label(f"{role} message", max_chars=max_chars, fallback="message")


# ── Per-turn context block ─────────────────────────────────────────────────────


def render_context_block(
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    chat: Any = None,
    message: Any = None,
    boards: Optional[Iterable[Dict[str, Any]]] = None,
    max_boards: int = 8,
    max_columns: int = 6,
) -> str:
    """
    Render the ``<item_refs>`` block injected into the system message.

    This is what lets the model link to *itself* (the current chat and the
    response message being written) and to the current project/boards without
    calling any tool: the assistant response message exists before the AI call,
    so its ``doc_id`` is already known here.

    Only INSTRUCTIONS are in the block, never the format: every link is built by
    this module.

    Args:
        project_id: Current project id.
        project_name: Current project name (display only).
        chat: Chat being processed (``Chat`` object or None).
        message: Assistant response message being produced (or None).
        boards: Optional board catalogue (dicts with ``name`` and ``columns``),
            typically ``codx.junior.tools.project_manager_tools._boards_info``.
        max_boards: Maximum number of boards listed.
        max_columns: Maximum number of columns listed per board.

    Returns:
        The block, or an empty string when there is nothing to report.
    """
    current_project = (project_id or "").strip()
    lines: List[str] = []

    chat_id = _value_of(chat, "id")
    chat_project = _value_of(chat, "owner_project_id") or _value_of(chat, "project_id")

    if chat_id:
        lines.append(
            "- current_chat: "
            + link(
                chat_label(chat),
                chat_ref(chat_id, project_id=_project_hint(chat_project, current_project)),
            )
        )

    message_id = _value_of(message, "doc_id")
    if chat_id and message_id:
        lines.append(
            "- current_message (this answer): "
            + link(
                "this answer",
                message_ref(
                    chat_id,
                    message_id,
                    project_id=_project_hint(chat_project, current_project),
                ),
            )
        )

    for board in list(boards or [])[:max_boards]:
        name = _value_of(board, "name") or _value_of(board, "title")
        if not name:
            continue
        board_link = link(name, board_ref(name))
        columns = [
            link(column, column_ref(name, column))
            for column in (board.get("columns") or [])[:max_columns]
            if column
        ]
        lines.append(
            f"- board: {board_link}" + (f" (columns: {', '.join(columns)})" if columns else "")
        )

    if not lines:
        return ""

    header = [
        "<item_refs>",
        "Links to codx-junior items use the codx:// scheme, always as a Markdown link.",
        "Copy any ref/markdown value returned by a tool VERBATIM: never build or invent ids.",
    ]
    if project_name or current_project:
        header.append(
            f"current_project: {project_name or '-'} (id {current_project or '-'})"
        )
    return "\n".join(header + lines + ["</item_refs>"])


# ── Parsing ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ItemRef:
    """
    A parsed ``codx://`` ref.

    Attributes:
        entity: Entity name (``chat``, ``board``, ``profile``, ``file``,
            ``project``).
        id: Primary identifier (chat id, board/profile name, path, project id).
        sub_entity: Sub-resource entity (``message`` or ``column``), if any.
        sub_id: Sub-resource identifier (message ``doc_id`` or column name).
        project_id: Owning project declared by the ref, if any.
        raw: The original string.
    """

    entity: str
    id: str
    sub_entity: Optional[str] = None
    sub_id: Optional[str] = None
    project_id: Optional[str] = None
    raw: str = ""

    @property
    def is_message(self) -> bool:
        """True when the ref points at a message inside a chat."""
        return self.entity == ENTITY_CHAT and self.sub_entity == ENTITY_MESSAGE

    @property
    def is_column(self) -> bool:
        """True when the ref points at a column inside a board."""
        return self.entity == ENTITY_BOARD and self.sub_entity == ENTITY_COLUMN

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-ready view (used by the API and ``meta_data["refs"]``)."""
        return {
            "entity": self.entity,
            "id": self.id,
            "sub_entity": self.sub_entity,
            "sub_id": self.sub_id,
            "project_id": self.project_id,
            "raw": self.raw,
            "resolved_id": self.sub_id or self.id,
        }


def parse_ref(ref: str) -> Optional[ItemRef]:
    """
    Parse a ``codx://`` ref into an :class:`ItemRef`.

    Segments are split BEFORE unquoting, so an encoded ``/`` inside a board
    name (``Sprint%2F12``) does not break the path.

    Args:
        ref: The ref string (may be a full Markdown link's destination).

    Returns:
        The parsed ref, or ``None`` when it is not a valid item ref.
    """
    raw = str(ref or "").strip()
    if not raw.lower().startswith(URI_PREFIX):
        return None

    parts = urlsplit(raw)
    if parts.scheme.lower() != SCHEME:
        return None

    entity = (parts.netloc or "").strip().lower()
    segments = [segment for segment in parts.path.split("/") if segment]

    # Tolerate ``codx:///<entity>/<id>`` (empty netloc).
    if not entity and segments:
        entity = segments.pop(0).lower()

    if entity not in ENTITIES or not segments:
        return None

    item_id = unquote(segments[0]).strip()
    if not item_id:
        return None

    sub_entity: Optional[str] = None
    sub_id: Optional[str] = None
    if len(segments) >= 3:
        sub_entity = unquote(segments[1]).strip().lower()
        sub_id = unquote(segments[2]).strip() or None
        if sub_entity not in ALLOWED_SUB_ENTITIES.get(entity, ()) or not sub_id:
            return None

    project_values = parse_qs(parts.query).get(PROJECT_PARAM) or []
    project_id = project_values[0].strip() or None if project_values else None

    return ItemRef(
        entity=entity,
        id=item_id,
        sub_entity=sub_entity,
        sub_id=sub_id,
        project_id=project_id,
        raw=raw,
    )


def find_refs(text: str) -> List[ItemRef]:
    """
    Extract every valid item ref found in *text*, deduplicated and in order.

    Used to derive ``Message.meta_data["refs"]`` from the assistant answer (no
    schema change) and to detect dead links.

    Args:
        text: Any text, typically an assistant message content.

    Returns:
        The parsed refs, unique by raw string.
    """
    found: Dict[str, ItemRef] = {}
    for match in _REF_PATTERN.finditer(str(text or "")):
        candidate = match.group(0).rstrip(_TRAILING_PUNCTUATION)
        if candidate in found:
            continue
        parsed = parse_ref(candidate)
        if parsed is not None:
            found[candidate] = parsed
    return list(found.values())


__all__ = [
    "SCHEME",
    "URI_PREFIX",
    "ENTITY_CHAT",
    "ENTITY_MESSAGE",
    "ENTITY_BOARD",
    "ENTITY_COLUMN",
    "ENTITY_PROFILE",
    "ENTITY_FILE",
    "ENTITY_PROJECT",
    "ENTITIES",
    "PROJECT_PARAM",
    "MAX_LABEL_CHARS",
    "SHORT_ID_CHARS",
    "ItemRef",
    "chat_ref",
    "message_ref",
    "board_ref",
    "column_ref",
    "profile_ref",
    "file_ref",
    "project_ref",
    "ref_for",
    "sanitize_label",
    "link",
    "chat_label",
    "message_label",
    "short_id",
    "render_context_block",
    "parse_ref",
    "find_refs",
]

# Made with ❤️ by codx-junior