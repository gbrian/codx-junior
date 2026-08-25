# Chat Manager Documentation

## Overview

The Chat Manager module is responsible for chat persistence and management within the CODX API. It provides both full-chat save/load operations and granular, merge-safe message operations that can be safely executed during an AI turn without overwriting concurrent updates.

## Key Features

### Full-Chat Operations
- Complete chat persistence and retrieval
- Metadata management and aggregation
- Legacy format migration

### Granular Message Operations
The module exposes merge-safe message operations designed to persist chat changes during an AI turn:
- `add_message`: Append a message to a chat
- `update_message`: Modify an existing message
- `remove_message`: Delete a message from a chat

These operations use a sophisticated merge strategy to prevent data loss during concurrent updates.

## Merge Strategy

The module implements a last-writer-wins conflict resolution strategy per message, identified by `doc_id`:

1. **New messages** are kept as-is
2. **Existing messages** are compared by `updated_at` timestamp
3. **Newer incoming messages** overwrite stored versions
4. **Stored message ordering** is preserved
5. **New incoming messages** are appended in their original relative order

This ensures that concurrent updates never regress or lose data.

## Core Classes

### ChatManager

The primary class managing chat persistence and retrieval for a given project.

#### Initialization

```python
def __init__(self, settings: CODXJuniorSettings, event_manager: Optional[EventManager] = None)
```

Creates required directory structure with default board ("kanban") and column ("tasks") locations.

#### Path Management

**`get_chat_file(chat: Chat) -> str`**
- Builds the canonical file path for a chat
- Returns absolute file path string

**`chat_paths(last_update: Optional[datetime] = None) -> List[str]`**
- Returns chat file paths with optional filtering by last update time
- Supports both legacy YAML and JSON formats

**`chat_board_column_name_from_path(file_path: str) -> tuple`**
- Parses board, column, and name from a chat file path
- Returns tuple of (board, column, name) or (None, None, None)

#### Chat Listing

**`list_chats(from_date: Optional[str] = None) -> List[Chat]`**
- Returns sorted list of all chats (metadata only, no messages)
- Accepts ISO-format date string to filter by modification date
- Results sorted by chat index or updated_at in descending order

#### Merge-Safe Message Operations

**`add_message(chat: Chat, message: Message) -> Chat`**
- Appends a message to chat and persists immediately
- Automatically assigns `doc_id` and `updated_at` timestamp
- Used for real-time event notifications during AI turns
- Returns persisted chat

**`update_message(chat: Chat, message: Message) -> Chat`**
- Updates existing message matched by `doc_id`
- Appends message if not found
- Persists with merge-safe strategy
- Returns persisted chat

**`remove_message(chat: Chat, message_doc_id: str) -> Chat`**
- Removes message identified by `message_doc_id`
- Applies removal on top of merged message list
- Ensures no concurrent changes are lost
- Returns persisted chat

**`_merge_message_lists(stored_messages: List[Message], incoming_messages: List[Message]) -> List[Message]`**
- Internal method implementing the merge strategy
- Compares messages by `doc_id` and `updated_at`
- Returns merged, ordered message list

#### Full-Chat Persistence

**`save_chat(chat: Chat, chat_only: bool = False) -> Chat`**
- Persists chat to disk with comprehensive handling:
  - Default board/column assignment
  - ID assignment and timestamp management
  - User and profile aggregation
  - Old file cleanup
  - Event emission
- When `chat_only=True`, preserves stored messages
- Transparently forwards to owner project's manager if needed
- Returns saved chat

**`store_chat(chat: Chat) -> None`**
- Writes chat to its file path as JSON
- Creates required directory structure

**`delete_chat(file_path: Optional[str] = None, chat_id: Optional[str] = None) -> None`**
- Deletes chat file from disk
- Accepts either direct file path or chat ID (resolved via `find_by_id`)
- Includes safety checks

#### Chat Loading

**`load_chat(board: str, column: Optional[str] = None, chat_name: Optional[str] = None) -> Chat`**
- Loads chat by board/column/name
- Returns empty Chat object if not found

**`load_chat_from_path(chat_file: str, chat_only: bool = False) -> Chat`**
- Loads Chat from JSON file
- When `chat_only=True`, returns chat with empty message list
- Sets owner_project_id from settings

**`find_by_id(chat_id: Optional[str]) -> Optional[Chat]`**
- Finds and loads chat by UUID
- Returns None if not found

#### Owner Project Resolution

**`_resolve_owner_manager(chat: Chat) -> ChatManager`**
- Returns ChatManager owning the chat
- When chat belongs to different project, returns manager scoped to that project
- Ensures persistence lands in correct location

#### Kanban Operations

**`load_kanban() -> dict`**
- Loads project's kanban configuration
- Returns kanban dict with `version`, `boards`, and `tags` keys

**`load_kanban_from_file(kanban_file: str) -> dict`**
- Loads kanban state from JSON file
- Applies defaults for missing values
- Handles legacy format migration

**`save_kanban(kanban: dict) -> None`**
- Persists kanban configuration to disk

**`delete_kanban(kanban_title: str) -> None`**
- Removes entire kanban board directory

#### Kanban Helpers

**`chat_count() -> int`**
- Returns total number of chat files on disk

**`last_chats() -> List[Chat]`**
- Returns up to three chats modified within last two days

#### Chat Querying

**`find_chats(last_update: Optional[datetime] = None) -> List[Chat]`**
- Returns chats based on optional last_update filter

#### Chat Export

**`traverse_chat_messages(chat_id: str, all_chats: List[Chat]) -> List[Message]`**
- Recursively traverses messages in chat and descendants
- Follows linked chats (via `message_id`) and child chats (via `parent_id`)
- Returns ordered list of messages

**`build_markdown_document(chat_id: str) -> str`**
- Traverses chat and generates markdown document
- Excludes messages with `hide=True`
- Returns markdown string

**`export_chat(chat_id: str, export_format: str) -> ExportedDocument`**
- Exports chat and descendants to specified format
- Supports formats: markdown, docx, pdf, excel
- Returns ExportedDocument containing exported content

## Chat Model

The Chat model includes:
- `id`: Unique identifier
- `board`: Kanban board name (defaults to "kanban")
- `column`: Kanban column name (defaults to "tasks")
- `name`: Chat name
- `messages`: List of Message objects
- `created_at`: Creation timestamp
- `updated_at`: Last modification timestamp
- `owner_project_id`: Reference to owning project
- `file_path`: Disk location
- `users`: Aggregated list of message users
- `profiles`: Aggregated list of message profiles

## Message Model

Messages include:
- `doc_id`: Unique message identifier
- `role`: Message role/type
- `content`: Message content
- `user`: User who sent the message
- `profiles`: Associated profiles
- `updated_at`: Timestamp
- `hide`: Flag to exclude from exports
- `message_id`: Link to related chat
- `parent_id`: Parent chat reference
- `child_index`: Child ordering index

## Error Handling

The module includes comprehensive error handling:
- Graceful fallback for missing owner projects
- Validation of file paths before deletion
- Exception logging during chat loading
- Safety checks on file operations

## Directory Structure

Default structure created by ChatManager:
```
{codx_path}/
└── tasks/
    └── kanban/
        └── tasks/
```

Chat files are organized as: `{board}/{column}/{slugified-name}.{id}.json`

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/db.py, codx/junior/utils/utils.py, codx/junior/profiling/profiler.py, codx/junior/chat/chat_export.py, codx/junior/events/event_manager.py, codx/junior/project/project_discover.py
**Imported by:** codx/junior/chat/chat_engine.py, codx/junior/engine/session.py, codx/junior/mentions/mention_manager.py, codx/junior/metrics/codx_junior_metrics.py