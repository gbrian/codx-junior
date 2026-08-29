# Chat Manager Module Documentation

## Overview

The Chat Manager module is responsible for chat persistence, retrieval, and management within the CODX API. It provides both full-chat operations and granular, merge-safe message operations that allow updates during AI turns without losing concurrent changes.

## Key Features

### Full-Chat Operations
- **Save and load** complete chat conversations with metadata
- **Automatic directory structure** creation for board/column organization
- **Legacy format migration** from YAML to JSON
- **Chat discovery** by ID, board, column, or name

### Granular Message Operations
The module exposes merge-safe message operations designed for real-time updates during AI execution:

- **`add_message`** — Appends a message idempotently (skips duplicates by `doc_id`)
- **`update_message`** — Updates an existing message or appends if not found
- **`remove_message`** — Removes a message while preserving concurrent updates

These operations are optimized for hot-path usage (tool events, throttled stream persists) and never lose concurrent changes through intelligent merging.

### Search Capabilities
The `search_chats` method provides full-text search across all chat data with:
- **Keyword matching** across chat name, description, messages, files, model, and history
- **Time-frame filtering** using `from_date` and `to_date` parameters
- **Pagination support** with configurable page size

### Chat Export
- **Multi-format export** (markdown, DOCX, PDF, Excel)
- **Recursive traversal** of linked and child chats
- **Markdown generation** with optional message filtering

## Merge Strategy

The module implements a last-writer-wins conflict resolution strategy per message (keyed by `doc_id`):

1. When persisting changes, stored and incoming messages are compared
2. If a `doc_id` exists in both, the version with the newer `updated_at` timestamp wins
3. New messages are appended in their original order
4. Message ordering is preserved from the stored version

### Timestamp Normalization

The module handles two historical timestamp formats:
- `str(datetime.now())` with space separator (Message default)
- `datetime.isoformat()` with T separator (from granular operations)

The `_parse_timestamp` helper parses both formats to ensure correct comparison, preventing lexicographic string comparison errors where ISO format would always win regardless of actual time.

## Performance Optimization

The `_load_stored_chat` method uses a fast-path optimization for frequently-called granular operations:

- **Direct file reading** when `chat.file_path` is known, valid, and within the manager's tree
- **Fallback to tree scanning** (`find_by_id`) only when necessary (moved/renamed chats)
- **Significant reduction** in I/O overhead during AI turns with multiple message updates

## Core Methods

### Path Helpers
- `get_chat_file(chat)` — Build canonical file path
- `chat_paths(last_update)` — Get all chat files, optionally filtered by modification time
- `chat_board_column_name_from_path(file_path)` — Parse metadata from file path

### Chat Listing and Discovery
- `list_chats(from_date)` — Return sorted chat metadata (no messages)
- `find_by_id(chat_id)` — Locate and load a chat by UUID
- `find_chats(last_update)` — Query chats with filters
- `last_chats()` — Get up to three recently modified chats

### Chat Operations
- `save_chat(chat, chat_only)` — Persist chat with board/column defaults and event emission
- `load_chat(board, column, chat_name)` — Load by location or return empty chat
- `load_chat_from_path(chat_file, chat_only)` — Load from JSON file
- `delete_chat(file_path, chat_id)` — Remove chat file from disk

### Kanban Management
- `load_kanban()` — Load project kanban configuration
- `save_kanban(kanban)` — Persist kanban state
- `load_kanban_from_file(kanban_file)` — Load with legacy format migration
- `delete_kanban(kanban_title)` — Remove entire board directory
- `chat_count()` — Count total chat files

### Export and Traversal
- `export_chat(chat_id, export_format)` — Export to specified format
- `build_markdown_document(chat_id)` — Generate markdown from chat tree
- `traverse_chat_messages(chat_id, all_chats)` — Recursively traverse linked and child chats

## Multi-Project Support

The module supports cross-project chat ownership through the `owner_project_id` field. When a chat belongs to a different project, the `_resolve_owner_manager` method returns a ChatManager scoped to the owner project, ensuring persistence lands in the correct location.

## Initialization

```python
manager = ChatManager(settings=project_settings, event_manager=optional_event_manager)
```

- **settings** — Project-level configuration containing project ID and paths
- **event_manager** — Optional shared EventManager; created if not supplied
- Creates required directory structure (`tasks/kanban/tasks` by default)

## Event Emission

The module integrates with the EventManager to emit `chat_changed` events after successful save operations, enabling real-time synchronization across the system.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/db.py, codx/junior/utils/utils.py, codx/junior/profiling/profiler.py, codx/junior/chat/chat_export.py, codx/junior/events/event_manager.py, codx/junior/project/project_discover.py
**Imported by:** codx/junior/chat/chat_engine.py, codx/junior/engine/session.py, codx/junior/mentions/mention_manager.py, codx/junior/metrics/codx_junior_metrics.py