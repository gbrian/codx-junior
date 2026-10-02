# Chat Manager Documentation

## Overview

The Chat Manager module is responsible for chat persistence, retrieval, and management within the CODX Junior project. It provides both full-chat operations and granular, merge-safe message operations that support concurrent updates during AI turns without data loss.

## Core Responsibilities

### Chat Persistence
- Full-chat save/load operations via `save_chat()` and `load_chat()`
- Granular message operations (`add_message()`, `update_message()`, `remove_message()`)
- Merge-safe persistence that prevents data loss during concurrent updates
- Support for chat metadata updates via `update_chat_metadata()`

### Chat Retrieval & Discovery
- List chats with optional time-based filtering
- Search chats with full-text capabilities
- Find chats by ID, board, column, or name
- Load chat data from various storage formats (JSON, YAML legacy)

### Additional Features
- Full-text search across chat data with time-frame filtering and pagination
- Kanban board configuration management
- Chat export to multiple formats (markdown, DOCX, PDF, Excel)
- Event emission for chat changes
- Cross-project chat ownership resolution

## Key Concepts

### Message Merge Strategy

The module implements a last-writer-wins merge strategy when combining stored and in-memory messages. Each message is identified by a unique `doc_id`, and conflicts are resolved by comparing `updated_at` timestamps:

- **No conflict**: New messages are kept as-is
- **Conflict**: The message with the later `updated_at` timestamp wins
- **Message ordering**: Stored message order is preserved; new incoming messages are appended

This approach ensures that rapid, concurrent updates (such as tool-usage notifications and streamed partial responses) never result in data loss.

### Timestamp Normalization

Historical chat data contains timestamps in two formats:
- `str(datetime.now())` — space separator (Message default)
- `datetime.isoformat()` — T separator (stamped by granular operations)

The `_parse_timestamp()` function handles both formats to enable correct timestamp comparison. Without this normalization, raw string comparison would incorrectly favor the 'T' format lexicographically, potentially allowing older messages to overwrite newer ones.

### Hot-Path Optimization

Granular message operations are called frequently during AI turns (tool events, throttled stream persists). The `_load_stored_chat()` method includes a fast-path optimization:

- When `chat.file_path` is known and valid, it reads directly from disk
- Falls back to scanning the task tree via `find_by_id()` for moved/renamed chats
- Significantly reduces overhead on high-frequency operations

## Main Classes & Methods

### ChatManager

#### Initialization
```python
__init__(settings: CODXJuniorSettings, event_manager: Optional[EventManager] = None)
```
Initializes the manager and creates the required directory structure.

#### Message Operations

- **`add_message(chat, message)`**: Append a message to chat (idempotent by `doc_id`) and persist immediately
- **`update_message(chat, message)`**: Update an existing message by `doc_id` or append if not found
- **`remove_message(chat, message_doc_id)`**: Remove a message by `doc_id` and persist
- **`update_chat_metadata(chat, metadata)`**: Update chat metadata without modifying messages

#### Chat Persistence

- **`save_chat(chat, chat_only=False)`**: Persist chat to disk with board/column defaults, ID assignment, and event emission
- **`store_chat(chat)`**: Write chat to its `file_path` as JSON
- **`delete_chat(file_path=None, chat_id=None)`**: Delete a chat file from disk

#### Chat Loading

- **`load_chat(board, column, chat_name)`**: Load chat by location or return empty Chat
- **`load_chat_from_path(chat_file, chat_only=False)`**: Load Chat from JSON file
- **`find_by_id(chat_id)`**: Find and load a chat by UUID
- **`list_chats(from_date=None)`**: Return sorted list of all chats (metadata only)

#### Search & Discovery

- **`search_chats(query, from_date, to_date, page, page_size)`**: Full-text search with pagination
- **`find_chats(last_update=None)`**: Return chats based on filter criteria
- **`chat_paths(last_update=None)`**: Get chat file paths with optional time filtering
- **`chat_count()`**: Return total number of chat files on disk
- **`last_chats()`**: Return up to three chats modified within the last two days

#### Kanban Management

- **`load_kanban()`**: Load project's kanban configuration (profiled function)
- **`load_kanban_from_file(kanban_file)`**: Load kanban state with defaults
- **`save_kanban(kanban)`**: Persist kanban configuration to disk
- **`delete_kanban(kanban_title)`**: Remove entire kanban board directory

#### Chat Export

- **`export_chat(chat_id, export_format)`**: Export chat and descendants to specified format
- **`build_markdown_document(chat_id)`**: Generate markdown document from chat (excluding hidden messages)
- **`traverse_chat_messages(chat_id, all_chats)`**: Recursively traverse messages following links and child chats

#### Path Helpers

- **`get_chat_file(chat)`**: Build canonical file path for a chat
- **`chat_board_column_name_from_path(file_path)`**: Parse board, column, and name from file path

## Helper Functions

### `_parse_timestamp(value: Optional[str]) -> datetime`

Parses message timestamps in either historical format:
- Returns parsed datetime for valid timestamps
- Returns `datetime.min` for unparseable/missing values (sorts oldest)
- Ensures correct comparison regardless of timestamp format

## Integration Points

### Owned by ChatEventBridge
The module fulfills a contract with `codx.junior.chat.chat_event_bridge.ChatEventBridge`:
- `add_message()` is idempotent (skips duplicates by `doc_id`)
- `update_message()` matches by `doc_id` (appends if missing)
- Both operations merge against stored chat to prevent loss of concurrent updates

### Event Emission
- Emits `"changed"` events via `event_manager` when chats are saved
- Supports cross-project chat ownership via `_resolve_owner_manager()`

### Cross-Project Support
The `owner_project_id` field allows chats to be owned by different projects. The manager transparently resolves and forwards operations to the owning project's manager.

## Default Configuration

- **Default Board**: `"kanban"`
- **Default Column**: `"tasks"`
- **Chat Storage**: `{codx_path}/tasks/{board}/{column}/{slugified_name}.{id}.json`

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/db.py, codx/junior/utils/utils.py, codx/junior/profiling/profiler.py, codx/junior/chat/chat_export.py, codx/junior/events/event_manager.py, codx/junior/project/project_discover.py
**Imported by:** codx/junior/chat/chat_engine.py, codx/junior/engine/session.py, codx/junior/mentions/mention_manager.py, codx/junior/metrics/codx_junior_metrics.py