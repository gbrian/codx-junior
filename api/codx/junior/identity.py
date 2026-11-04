"""
Identity primitives shared by the task / kanban / long-running machinery.

The project rule is: **ids are canonical, names and titles are only labels**.

* every persisted element has an immutable ``id`` (uuid),
* references between elements use ids (``Chat.parent_id``, ``Chat.root_id``,
  ``Chat.kanban_id``, ``Chat.column_id``),
* ``Chat.board`` / ``Chat.column`` / ``Chat.name`` are display labels.

This module owns the primitives the rest of the code must use to reason about
the ancestor chain of a task, so the invariant *"every task of a run shares the
same ancestor (the main task)"* is enforced in one place instead of being
re-implemented (and diverging) by every caller:

* :func:`resolve_root_id` - canonical root (main task) of a chat.
* :func:`is_descendant_of` - guard used by the long-running runner.
* :func:`link_parent` - creation helper used by ``TaskManager``.
* :func:`attach_root_id` - backfill helper.

``Chat.root_id`` is a CACHE of the walk: legacy chats have no value, so the walk
happens once and the result is backfilled on the in-memory chat; the caller
persists it the next time the chat is saved. A cache that is not the chat's own
id is returned without walking (cheap path for every tick of a run).

```mermaid
flowchart TD
    A[chat] --> B{parent_id?}
    B -->|no| C[root_id = chat.id]
    B -->|yes| D{root_id cached?}
    D -->|yes| E[return cache]
    D -->|no| F[walk parent_id up]
    F --> G{cycle or depth limit?}
    G -->|yes| H[stop: log warning, use last chat]
    G -->|no| I[topmost chat reached]
    I --> J[root_id = topmost.id, backfill chat.root_id]
    H --> J
```

Made with ❤️ by codx-junior
"""

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from codx.junior.chat_manager import ChatManager
    from codx.junior.db import Chat

logger = logging.getLogger(__name__)

# A corrupted parent chain must never make the process hang: the walk gives up
# after this many levels (deeper hierarchies are not a realistic task tree).
MAX_PARENT_DEPTH = 64


def attach_root_id(chat: Optional["Chat"], parent_chat: Optional["Chat"] = None) -> Optional[str]:
    """
    Compute (and stamp) the ``root_id`` of *chat* from its parent.

    Creation rules:

    * a chat without a parent is its own root (``root_id = chat.id``),
    * a child inherits ``parent.root_id`` when the parent already knows its
      root, and falls back to the parent id otherwise,
    * nothing is inherited from a parent that is not there.

    The value is stamped on the chat itself, so a caller that persists the chat
    right after creation stores the cache.

    Args:
        chat: The chat being created/updated (may be None).
        parent_chat: The parent chat, when it is already loaded.

    Returns:
        The resolved root id, or None when it cannot be determined.

    Example:
        >>> attach_root_id(child, parent)          # parent is the main task
        '<parent-id>'
        >>> attach_root_id(main_task, None)        # no parent: it is the root
        '<main-task-id>'
    """
    if chat is None:
        return None

    if parent_chat is None:
        root_id = chat.id or None
    else:
        root_id = getattr(parent_chat, "root_id", None) or parent_chat.id or None

    if root_id and chat.root_id != root_id:
        chat.root_id = root_id
    return root_id


def resolve_root_id(
    chat: Optional["Chat"],
    chat_manager: Optional["ChatManager"] = None,
) -> Optional[str]:
    """
    Return the canonical root (main task) id of *chat*.

    Resolution order:

    1. ``chat.root_id`` when it is already cached and differs from the chat's
       own id (a chat that is not a root has a foreign root id),
    2. the chat id itself when the chat has no ``parent_id``,
    3. a walk up ``parent_id`` (bounded by :data:`MAX_PARENT_DEPTH`, cycle safe)
       when a ``chat_manager`` was provided. The result is backfilled into
       ``chat.root_id`` so the next call is free.

    The walk is best-effort: a missing parent stops it and the last chat reached
    becomes the root, which keeps the invariant "there is always a root" true
    even for chats whose ancestors were deleted.

    Args:
        chat: The chat whose root to resolve (may be None).
        chat_manager: Manager used to load the parents. When it is missing, only
            cached/derived values are returned (no disk access).

    Returns:
        The root chat id, or None when *chat* is None.

    Example:
        >>> resolve_root_id(task_a11, chat_manager)   # A -> A.1 -> A.1.1
        '<root-A-id>'
    """
    if chat is None:
        return None

    cached = getattr(chat, "root_id", None)
    if cached and cached != chat.id:
        return cached

    if not chat.parent_id:
        if chat.id and chat.root_id != chat.id:
            chat.root_id = chat.id
        return chat.id

    if chat_manager is None or not chat.id:
        return cached or None

    current: Optional["Chat"] = chat
    visited = set()

    while current is not None and current.parent_id:
        if current.id in visited or len(visited) >= MAX_PARENT_DEPTH:
            logger.warning(
                "resolve_root_id: parent chain cycle/depth limit reached for "
                "chat '%s' (visited=%d)",
                chat.id,
                len(visited),
            )
            break
        visited.add(current.id)

        known_root = getattr(current, "root_id", None)
        if known_root and known_root != current.id and known_root != chat.id:
            # An ancestor already knows the root: stop walking.
            if chat.root_id != known_root:
                chat.root_id = known_root
            return known_root

        parent = chat_manager.find_by_id(chat_id=current.parent_id)
        if parent is None:
            logger.info(
                "resolve_root_id: parent '%s' of chat '%s' not found, using "
                "'%s' as root",
                current.parent_id,
                chat.id,
                current.id,
            )
            break
        current = parent

    root_id = (current.id if current is not None else None) or cached or None
    if root_id and chat.root_id != root_id:
        chat.root_id = root_id
        logger.info(
            "resolve_root_id: chat '%s' resolved to root '%s' (legacy cache "
            "backfilled)",
            chat.id,
            root_id,
        )
    return root_id


def is_descendant_of(
    chat: Optional["Chat"],
    root_id: Optional[str],
    chat_manager: Optional["ChatManager"] = None,
) -> bool:
    """
    Tell whether *chat* belongs to the tree rooted at *root_id*.

    This is the guard the long-running runner uses before processing a task: a
    task stored on the run board whose root is a different chat must never be
    processed by that run.

    Args:
        chat: The chat to check.
        root_id: The expected root (main task) id.
        chat_manager: Manager used to resolve the chain.

    Returns:
        True when the chat resolves to *root_id* (a root is its own descendant).

    Example:
        >>> is_descendant_of(task, main_task.id, chat_manager)
        True
    """
    if chat is None or not root_id:
        return False
    return resolve_root_id(chat=chat, chat_manager=chat_manager) == root_id


def link_parent(
    chat: "Chat",
    parent_chat: Optional["Chat"] = None,
) -> "Chat":
    """
    Link *chat* to *parent_chat* keeping the ancestor invariant.

    Sets ``parent_id`` (when a parent is given and the chat does not already
    define one) and stamps ``root_id`` through :func:`attach_root_id`.

    Args:
        chat: The chat being created (mutated in place).
        parent_chat: The parent chat, when available.

    Returns:
        The same chat, for chaining.
    """
    if parent_chat is not None and not chat.parent_id and parent_chat.id:
        chat.parent_id = parent_chat.id
    attach_root_id(chat=chat, parent_chat=parent_chat)
    return chat

# Made with ❤️ by codx-junior
