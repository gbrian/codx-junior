"""
Item ref tool for codx-junior.

Lets a model build **clickable links** to codx-junior items — chats/tasks,
messages, kanban boards and columns, profiles, project files and projects —
without ever composing the format itself.

Design notes
------------
    - **The format lives in code.** Every ref is produced by
      :mod:`codx.junior.refs`; this tool only resolves the labels and the
      existence of the items, so the model copies a string instead of
      generating a URL.
    - **Labels come from the server.** When the caller does not provide one, the
      chat name / message first line / board name is read from the project, so
      the link never shows a hallucinated description.
    - **Existence is checked where it is cheap.** Chats and messages are loaded
      from the :class:`~codx.junior.chat_manager.ChatManager`; a missing item is
      reported (``exists: false``) so the model does not publish a dead link.
      Boards, columns, profiles and files are emitted as given: their existence
      is verified by ``GET /api/refs/resolve`` (the same path the client uses
      before navigating).
    - **Bulk friendly.** ``items`` builds several links in one call (a task
      list, a board column, ...) so linking does not cost a tool call per item.
    - **The answer must repeat the link.** Tool output is attached to the
      response message as a collapsible property (``ToolEvent.output``), never
      merged into ``Message.content``, so ``llm_response`` carries the ready-to-
      insert Markdown and asks for it verbatim.

Made with ❤️ by codx-junior
"""

import json
import logging

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from codx.junior.refs import (
    ENTITY_BOARD,
    ENTITY_CHAT,
    ENTITY_COLUMN,
    ENTITY_FILE,
    ENTITY_MESSAGE,
    ENTITY_PROFILE,
    ENTITY_PROJECT,
    board_ref,
    chat_label,
    chat_ref,
    file_ref,
    link,
    message_label,
    message_ref,
    profile_ref,
    project_ref,
    ref_for,
    short_id,
)

from .model import ToolResponse

if TYPE_CHECKING:
    from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

# Entities the tool can build links for (``message``/``column`` need a parent).
VALID_ENTITIES = [
    ENTITY_CHAT,
    ENTITY_MESSAGE,
    ENTITY_BOARD,
    ENTITY_COLUMN,
    ENTITY_PROFILE,
    ENTITY_FILE,
    ENTITY_PROJECT,
]

# Maximum number of links built in a single call.
MAX_ITEMS: int = 25

# Maximum characters of a label (mirrors refs.MAX_LABEL_CHARS-ish behaviour).
MAX_LABEL_CHARS: int = 120

# Note appended to every model-facing payload: tool output may be collapsed in
# the UI, so the model has to re-emit the link in its own answer.
MODEL_NOTE: str = (
    "Insert each 'markdown' value VERBATIM in your answer (tool output may be "
    "rendered collapsed, so the link is only visible if you repeat it). Never "
    "build or invent a ref by yourself."
)


def _resolve_chat_manager(**kwargs):
    """
    Return the ChatManager of the current execution context.

    Reuses the resolution used by ``project_manager`` (active session →
    injected session → project settings) so both tools always read the same
    project tree.

    Args:
        **kwargs: Tool keyword arguments (``settings``/``session`` injected by
            the agent runtime).

    Returns:
        A ready ChatManager, or ``None`` when no project context is available.
    """
    from .project_manager_tools import _resolve_chat_manager as resolve_manager

    try:
        return resolve_manager(**kwargs)
    except ValueError as ex:
        logger.warning("item_ref: no project context available: %s", ex)
        return None


def _current_project_id(settings: Optional["CODXJuniorSettings"]) -> Optional[str]:
    """Return the current project id, when available."""
    return getattr(settings, "project_id", None) if settings else None


def _find_chat(chat_manager, chat_id: Optional[str]):
    """
    Load a chat by id, tolerating a missing manager/id.

    Args:
        chat_manager: ChatManager (may be None).
        chat_id: Chat id.

    Returns:
        The Chat, or None.
    """
    if chat_manager is None or not chat_id:
        return None
    try:
        return chat_manager.find_by_id(chat_id=chat_id)
    except Exception as ex:  # pragma: no cover - defensive: broken store
        logger.warning("item_ref: could not load chat '%s': %s", chat_id, ex)
        return None


def _find_message(chat, message_id: Optional[str]):
    """
    Return the message with *message_id* from *chat*.

    Args:
        chat: Chat object (may be None).
        message_id: Message ``doc_id``.

    Returns:
        The Message, or None.
    """
    if chat is None or not message_id:
        return None
    return next(
        (msg for msg in (chat.messages or []) if msg.doc_id == message_id),
        None,
    )


def _build_entry(
    entity: str,
    item_id: str,
    chat_id: Optional[str] = None,
    board: Optional[str] = None,
    label: Optional[str] = None,
    project_hint: Optional[str] = None,
    chat_manager=None,
) -> Dict[str, Any]:
    """
    Resolve one item into a ref + label + existence entry.

    Args:
        entity: Entity name (see :data:`VALID_ENTITIES`).
        item_id: Primary identifier.
        chat_id: Parent chat id (messages).
        board: Parent board name (columns).
        label: Explicit label (wins over the resolved one).
        project_hint: Project to add to the ref when it is not the current one.
        chat_manager: ChatManager used to resolve labels/existence.

    Returns:
        Dict with ``entity``, ``id``, ``label``, ``ref``, ``markdown`` and
        ``exists`` (``None`` when existence cannot be checked here).
    """
    entity = (entity or "").strip().lower()
    item_id = str(item_id or "").strip()

    resolved_label = ""
    exists: Optional[bool] = None
    ref = ""

    if entity == ENTITY_CHAT:
        chat = _find_chat(chat_manager, item_id)
        resolved_label = chat_label(chat) if chat is not None else ""
        exists = chat is not None
        ref = chat_ref(item_id, project_id=project_hint)

    elif entity == ENTITY_MESSAGE:
        chat = _find_chat(chat_manager, chat_id)
        message = _find_message(chat, item_id)
        resolved_label = message_label(message) if message is not None else ""
        exists = message is not None
        ref = message_ref(chat_id, item_id, project_id=project_hint)

    elif entity == ENTITY_BOARD:
        resolved_label = item_id
        ref = board_ref(item_id, project_id=project_hint)

    elif entity == ENTITY_COLUMN:
        resolved_label = item_id
        ref = ref_for(ENTITY_COLUMN, item_id, board=board, project_id=project_hint)

    elif entity == ENTITY_PROFILE:
        resolved_label = item_id
        ref = profile_ref(item_id, project_id=project_hint)

    elif entity == ENTITY_FILE:
        resolved_label = item_id
        ref = file_ref(item_id, project_id=project_hint)

    elif entity == ENTITY_PROJECT:
        resolved_label = item_id
        ref = project_ref(item_id)

    else:
        raise ValueError(
            f"Unknown entity '{entity}' (valid entities: "
            f"{', '.join(VALID_ENTITIES)})"
        )

    final_label = (label or "").strip() or resolved_label or short_id(item_id) or item_id
    return {
        "entity": entity,
        "id": item_id,
        "chat_id": chat_id or None,
        "board": board or None,
        "label": final_label,
        "ref": ref,
        "markdown": link(final_label, ref, max_chars=MAX_LABEL_CHARS),
        "exists": exists,
    }


def _normalize_items(
    items: Optional[List[Dict[str, Any]]],
    entity: Optional[str],
    item_id: Optional[str],
    chat_id: Optional[str],
    board: Optional[str],
    label: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Normalize the bulk and single-item forms into one list of requests.

    Args:
        items: Bulk form (list of dicts).
        entity: Single-item entity.
        item_id: Single-item identifier.
        chat_id: Single-item parent chat id.
        board: Single-item parent board name.
        label: Single-item label.

    Returns:
        List of request dicts with ``entity``, ``id``, ``chat_id``, ``board``
        and ``label``.

    Raises:
        ValueError: When nothing is provided or too many items are requested.
    """
    requests: List[Dict[str, Any]] = []

    for item in items or []:
        if not isinstance(item, dict):
            raise ValueError("'items' must be a list of objects")
        requests.append(
            {
                "entity": item.get("entity"),
                "id": item.get("id"),
                "chat_id": item.get("chat_id"),
                "board": item.get("board"),
                "label": item.get("label"),
            }
        )

    if not requests:
        if not entity or not item_id:
            raise ValueError(
                "Provide either 'items' or both 'entity' and 'id'"
            )
        requests.append(
            {
                "entity": entity,
                "id": item_id,
                "chat_id": chat_id,
                "board": board,
                "label": label,
            }
        )

    if len(requests) > MAX_ITEMS:
        raise ValueError(
            f"Too many items ({len(requests)}): the maximum per call is {MAX_ITEMS}"
        )

    return requests


def item_ref(
    items: Optional[List[Dict[str, Any]]] = None,
    entity: Optional[str] = None,
    id: Optional[str] = None,  # noqa: A002 - the schema property is 'id'
    chat_id: Optional[str] = None,
    board: Optional[str] = None,
    label: Optional[str] = None,
    project_id: Optional[str] = None,
    settings: Optional["CODXJuniorSettings"] = None,
    session: Optional[Any] = None,
) -> ToolResponse:
    """
    Build clickable refs (Markdown links) to codx-junior items.

    Two forms are accepted:

    - **Bulk**: ``items=[{"entity": "chat", "id": "..."}, ...]`` (max 25).
    - **Single**: ``entity`` + ``id`` (+ ``chat_id`` for messages, ``board``
      for columns).

    Labels are resolved from the project when not provided, and chats/messages
    are checked for existence so the model does not publish a dead link.

    Args:
        items: Bulk requests (each with ``entity``, ``id``, optional
            ``chat_id``, ``board`` and ``label``).
        entity: Entity of the single form: ``chat``, ``message``, ``board``,
            ``column``, ``profile``, ``file`` or ``project``.
        id: Identifier of the single form: ``Chat.id`` for chats,
            ``Message.doc_id`` for messages, the name for boards/columns/
            profiles, the path for files and the project id for projects.
        chat_id: Parent chat id (required for ``entity='message'``).
        board: Parent board name (required for ``entity='column'``).
        label: Explicit link label (defaults to the resolved name/excerpt).
        project_id: Project to add to the ref. Defaults to the current project;
            only emitted when it differs from it.
        settings: CODXJuniorSettings instance (injected by SmolAgent).
        session: Active session (injected by SmolAgent).

    Returns:
        ToolResponse with the ready-to-insert Markdown links (user) and the
        machine-readable JSON payload (model).

    Raises:
        ValueError: When no item is provided, an entity is unknown or a
            required parent (``chat_id``/``board``) is missing.

    Example:
        >>> item_ref(entity="chat", id="5f0e1a2b-...")
        >>> item_ref(items=[
        ...     {"entity": "message", "id": "<doc_id>", "chat_id": "<chat_id>"},
        ...     {"entity": "board", "id": "Engine"},
        ... ])
    """
    resolved_project = (project_id or "").strip() or _current_project_id(settings)
    chat_manager = _resolve_chat_manager(settings=settings, session=session)

    requests = _normalize_items(
        items=items,
        entity=entity,
        item_id=id,
        chat_id=chat_id,
        board=board,
        label=label,
    )

    entries: List[Dict[str, Any]] = []
    problems: List[str] = []

    for request in requests:
        try:
            entries.append(
                _build_entry(
                    entity=request["entity"],
                    item_id=request["id"],
                    chat_id=request["chat_id"],
                    board=request["board"],
                    label=request["label"],
                    project_hint=None,
                    chat_manager=chat_manager,
                )
            )
        except ValueError as ex:
            # A single bad item must not discard the links already built.
            problems.append(str(ex))
            logger.warning("item_ref: %s", ex)

    if not entries:
        raise ValueError(
            "No link could be built: " + "; ".join(problems or ["no items provided"])
        )

    # Qualified project: only when the caller asked for another project. Items
    # resolved through the current ChatManager already live in the current
    # project, so the plain ref is enough for them.
    if project_id and project_id.strip() and project_id.strip() != _current_project_id(settings):
        for entry in entries:
            try:
                entry["ref"] = ref_for(
                    entry["entity"],
                    entry["id"],
                    chat_id=entry.get("chat_id"),
                    board=entry.get("board"),
                    project_id=project_id.strip(),
                )
                entry["markdown"] = link(
                    entry["label"], entry["ref"], max_chars=MAX_LABEL_CHARS
                )
            except ValueError as ex:
                logger.warning("item_ref: could not qualify ref with project: %s", ex)

    missing = [entry for entry in entries if entry.get("exists") is False]

    user_lines = ["🔗 **Item refs**", ""]
    user_lines.extend(f"- {entry['markdown']}" for entry in entries)
    if missing:
        user_lines.extend(
            [
                "",
                "⚠️ Not found in this project (link would be dead): "
                + ", ".join(f"`{entry['id']}`" for entry in missing),
            ]
        )

    llm_payload = {
        "count": len(entries),
        "links": entries,
        "missing": [entry["id"] for entry in missing],
        "note": MODEL_NOTE,
    }

    logger.info(
        "item_ref: built %d link(s) (%d missing) for project '%s'",
        len(entries),
        len(missing),
        resolved_project,
    )

    return ToolResponse(
        user_response="\n".join(user_lines),
        llm_response=json.dumps(llm_payload, indent=2, default=str),
    )


# Tool JSON definition
ITEM_REF_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "item_ref",
        "description": (
            "Build clickable links (refs) to codx-junior items: chats/tasks, chat "
            "messages, kanban boards and their columns, profiles, project files and "
            "projects. "
            "\n\nALWAYS use this tool instead of writing an id, a path or a URL by "
            "hand: the returned 'markdown' value is the ONLY valid link format, and "
            "the label is resolved from the project so it is never invented. "
            "\n\nUse the bulk form ('items') to link several items in a single call "
            "(e.g. a list of tasks). Copy each 'markdown' value verbatim into your "
            "answer: tool output may be rendered collapsed, so a link that is not "
            "repeated in your text will not be visible to the user. "
            "\n\nA message link always requires its chat ('chat_id'), because "
            "messages are stored inside the chat file."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": (
                        f"Bulk form: up to {MAX_ITEMS} items to link in one call. "
                        "When provided, 'entity'/'id' are ignored."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "entity": {
                                "type": "string",
                                "enum": VALID_ENTITIES,
                                "description": "Type of the item to link."
                            },
                            "id": {
                                "type": "string",
                                "description": (
                                    "Chat id, message doc_id, board/column/profile "
                                    "name, file path or project id."
                                )
                            },
                            "chat_id": {
                                "type": "string",
                                "description": (
                                    "Parent chat id. Required when entity='message'."
                                )
                            },
                            "board": {
                                "type": "string",
                                "description": (
                                    "Parent board name. Required when entity='column'."
                                )
                            },
                            "label": {
                                "type": "string",
                                "description": (
                                    "Optional link label. Defaults to the item name "
                                    "or the message excerpt resolved by the server."
                                )
                            }
                        },
                        "required": ["entity", "id"]
                    }
                },
                "entity": {
                    "type": "string",
                    "enum": VALID_ENTITIES,
                    "description": (
                        "Single form: type of the item to link. "
                        "'chat' covers chats and tasks (a task is a chat)."
                    )
                },
                "id": {
                    "type": "string",
                    "description": (
                        "Single form: Chat.id for chats, Message.doc_id for messages, "
                        "name for boards/columns/profiles, path for files, project id "
                        "for projects."
                    )
                },
                "chat_id": {
                    "type": "string",
                    "description": "Parent chat id. Required when entity='message'."
                },
                "board": {
                    "type": "string",
                    "description": "Parent board name. Required when entity='column'."
                },
                "label": {
                    "type": "string",
                    "description": (
                        "Optional link label (max "
                        f"{MAX_LABEL_CHARS} characters). Defaults to the item name "
                        "resolved by the server."
                    )
                },
                "project_id": {
                    "type": "string",
                    "description": (
                        "Project the items belong to. Defaults to the current project; "
                        "set it only when linking items from another project."
                    )
                }
            },
            "required": []
        }
    }
}

# Made with ❤️ by codx-junior