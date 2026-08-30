# Chat Manager Documentation

## Overview

The Chat Manager module is responsible for chat persistence and management within the CODX Junior system. It provides a comprehensive suite of operations ranging from simple full-chat save/load functionality to granular, merge-safe message operations that can be safely executed during active AI turns.

## Key Features

### Full-Chat Operations
- **Save and load complete chats** with automatic board/column defaults and ID assignment
- **Chat listing** with optional date filtering
- **Chat search** with full-text capabilities, time-frame filtering, and pagination
- **Kanban board management** for organizing chats

### Granular Message Operations
The module exposes merge-safe message operations designed for real-time updates during AI execution:

- **`add_message`** — Appends a message to a chat with immediate persistence (idempotent by `doc_id`)
- **`update_message`** — Updates an existing message matched by `doc_id`, or appends if not found
- **`remove_message`** — Removes a message while preserving concurrent updates
- **`update_chat_metadata`** — Updates chat metadata without touching messages

### Merge Strategy

The module implements a last-writer-wins merge strategy per message (keyed by `doc_id`):

1. When persisting mid-turn changes, the stored chat is reloaded
2. Message lists are merged by comparing `updated_at` timestamps
3. If a message's `doc_id` exists in both stored and incoming messages, the one with the newer timestamp wins
4. New incoming messages are appended in their original order
5. Messages without a `doc_id` receive one automatically

### Timestamp Handling

Timestamps historically exist in two formats:
- `str(datetime.now())` — space separator (Message default)
- `datetime.isoformat()` — T separator (used by granular operations)

The `_parse_timestamp` function normalizes both formats to enable correct datetime comparison. Raw string comparison was incorrect because the 'T' variant always lexicographically beats the space variant, allowing older messages to overwrite newer ones.

## Core Methods

### Chat Persistence

**`save_chat(chat, chat_only=False)`**
Persists a chat to disk with the following behaviors:
- Assigns default board/column if missing
- Generates a chat ID if not present
- Updates `updated_at` timestamp
- When `chat_only=True`, preserves stored messages (metadata-only update)
- Handles migration from legacy YAML format
- Cleans up old file paths if the chat was moved
- Emits a "changed" event through the EventManager

**`store_chat(chat)`**
Writes a chat to its `file_path` as JSON.

**`delete_chat(file_path=None, chat_id=None)`**
Removes a chat file from disk, with safety checks to prevent deletion outside the chat directory.

### Chat Retrieval

**`load_chat(board, column=None, chat_name=None)`**
Loads a chat by board/column/name, returning an empty Chat object if not found.

**`load_chat_from_path(chat_file, chat_only=False)`**
Loads a Chat from a JSON file. When `chat_only=True`, the returned chat has an empty message list.

**`find_by_id(chat_id)`**
Locates and loads a chat by its UUID.

**`list_chats(from_date=None)`**
Returns a sorted list of all chats (metadata only, no messages), optionally filtered by modification date and sorted by index/`updated_at` in descending order.

### Search Operations

**`search_chats(query, from_date=None, to_date=None, page=1, page_size=20)`**
Provides full-text search across chat data, delegating to the `ChatSearcher` class. Supports:
- Case-insensitive substring matching
- Date range filtering (from/to dates are inclusive)
- Pagination with configurable page size
- Returns a dictionary with paginated results and metadata

### Message Operations

**`add_message(chat, message)`**
Appends a message to a chat with immediate merge-safe persistence. The operation is idempotent: if a message with the same `doc_id` already exists on the chat, it is not added twice. Used for real-time event notifications (tool usage, run lifecycle).

**`update_message(chat, message)`**
Updates an existing message matched by `doc_id`, or appends it if not found. Useful for streaming partial responses and tool event updates.

**`remove_message(chat, message_doc_id)`**
Removes the message identified by `message_doc_id` while applying the removal on top of the merged message list, ensuring no concurrent changes are lost.

**`update_chat_metadata(chat, metadata)`**
Updates chat metadata fields (name, description, board, column, etc.) without modifying messages. Returns the persisted chat.

### Internal Helpers

**`_load_stored_chat(chat)`**
Loads the persisted version of a chat with a fast-path optimization. When `chat.file_path` is valid and within the manager's directory tree, it reads directly; otherwise falls back to `find_by_id`. This optimization is critical for hot-path code invoked on every tool event during AI turns.

**`_persist_chat_messages(chat)`**
Merge-safe persistence used by granular message operations. Reloads the stored chat, merges message lists to prevent mid-turn saves from clobbering concurrent updates, then delegates to `save_chat`.

**`_merge_message_lists(stored_messages, incoming_messages)`**
Merges two message lists by `doc_id` using `updated_at` to determine which version wins. Preserves stored message ordering; new incoming messages are appended in their original relative order.

## Path Management

**`get_chat_file(chat)`**
Builds the canonical file path for a chat using the pattern:
```
{chat_path}/{board}/{column}/{slugified_name}.{id}.json
```

**`chat_paths(last_update=None)`**
Returns chat file paths, optionally filtering by last update time. Searches for both `.yaml` and `.json` files.

**`chat_board_column_name_from_path(file_path)`**
Parses board, column, and name components from a chat file path.

## Owner Project Resolution

**`_resolve_owner_manager(chat)`**
Returns the ChatManager owning a chat. When a chat belongs to a different project (via `owner_project_id`), a manager scoped to that project is returned, ensuring persistence lands in the correct location.

## Kanban Management

**`load_kanban()`**
Loads the project's kanban configuration from a JSON file with automatic defaults when missing.

**`save_kanban(kanban)`**
Persists kanban configuration to disk.

**`delete_kanban(kanban_title)`**
Removes an entire kanban board directory.

**`load_kanban_from_file(kanban_file)`**
Loads kanban state from a JSON file, applying defaults and handling legacy format migration.

**`chat_count()`**
Returns the total number of chat files on disk.

**`last_chats()`**
Returns up to three chats modified within the last two days.

## Chat Export

**`build_markdown_document(chat_id)`**
Traverses a chat and its descendants, generating a markdown document. Messages with `hide=True` are excluded.

**`traverse_chat_messages(chat_id, all_chats)`**
Recursively traverses messages in a chat and its descendants, following both linked chats (via `message_id`) and child chats (via `parent_id`).

**`export_chat(chat_id, export_format)`**
Exports a chat and its descendants to a specified format (markdown, docx, pdf, excel), returning an `ExportedDocument` with the exported content.

## Constants

- **`DEFAULT_BOARD`** — `"kanban"` — Default board name for new chats
- **`DEFAULT_COLUMN`** — `"tasks"` — Default column name for new chats

## Integration

The module relies on the following contracts with `ChatEventBridge`:

- `add_message` inserts idempotently, skipping in-memory duplicates by `doc_id`
- `update_message` matches by `doc_id` and appends if missing
- Both operations merge against the stored chat, ensuring concurrent updates are never lost

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/db.py, codx/junior/utils/utils.py, codx/junior/profiling/profiler.py, codx/junior/chat/chat_export.py, codx/junior/events/event_manager.py, codx/junior/project/project_discover.py
**Imported by:** codx/junior/chat/chat_engine.py, codx/junior/engine/session.py, codx/junior/mentions/mention_manager.py, codx/junior/metrics/codx_junior_metrics.py