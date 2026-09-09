# Database and Data Storage

## Overview

The `db.py` module provides database management for CODXJunior using TinyDB. It handles persistence of kanban boards, columns, chats, and associated metadata with table-level caching capabilities.

## Core Components

### Data Models

#### ChatAttachment
Represents image data stored in chats or messages with file metadata.

**Fields:**
- `file_name` - Original file name of the image
- `file_type` - MIME type (image/png, image/jpeg, image/jpg, image/gif, image/webp, image/svg+xml)
- `file_size` - File size in bytes (max 50MB)
- `base64_data` - Base64 encoded image data
- `uploaded_at` - Timestamp when image was uploaded

**Validation:**
- File size cannot exceed 50MB (52,428,800 bytes)
- Only specified MIME types are allowed

#### KanbanColumn
Represents a column in a Kanban board.

**Fields:**
- `doc_id` - Optional document identifier
- `title` - Column title
- `color` - Optional color indicator
- `index` - Column position
- `chats` - List of associated chat IDs

#### Kanban
Represents a complete Kanban board with columns and metadata.

**Fields:**
- `doc_id` - Optional document identifier
- `title` - Board title
- `description` - Optional board description
- `index` - Board position
- `columns` - List of KanbanColumn instances
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

#### Message
Represents a single chat message with support for tool events and lifecycle tracking.

**Key Fields:**
- `doc_id` - Document identifier
- `role` - Message role ('user' or 'assistant')
- `content` - Message text content
- `think` - Optional thinking/reasoning content
- `attachments` - List of ChatAttachment instances
- `files` - List of associated file paths
- `tool_events` - ToolEvent instances for tool executions
- `lifecycle_events` - LifeCycleEvent instances for agent runs
- `knowledge_topics` - Topics for knowledge indexing
- `done` - Indicates if user finished writing
- `is_thinking` - Thinking state flag
- `disable_knowledge` - Flag to disable knowledge indexing
- `read_by` - List of users who read the message
- `linked_chat_ids` - References to related chats

**Related Events:**
- `ToolEvent` - Tracks tool execution with status, request, response, and error information
- `LifeCycleEvent` - Tracks agent run status, duration, and errors

#### Chat
Represents a complete chat session with messages and kanban associations.

**Key Fields:**
- `doc_id` - Document identifier
- `project_id` - Active project context
- `owner_project_id` - Project where chat was created
- `parent_id` - Parent chat for threads
- `message_id` - Parent message for threads
- `name` - Chat name
- `description` - Chat description
- `messages` - List of Message instances
- `status` - Current chat status
- `mode` - Chat mode (default: 'chat')
- `kanban_id` - Associated kanban board
- `column_id` - Associated kanban column
- `attachments` - List of ChatAttachment instances
- `knowledge_topics` - Topics for knowledge indexing
- `auto_initialize` - Auto-fill board/column/name on first response
- `ignore_parent_knowledge` - Disconnect from parent knowledge
- `ignore_parent_files` - Exclude parent file list
- `history` - ChatHistoryEntry list for historical tracking
- `chat_links` - References to chats in other projects

#### ChatHistoryEntry
Historical entry in a chat with summary and associated messages.

**Fields:**
- `timestamp` - When entry was generated
- `summary` - Summary content
- `message_ids` - Associated message identifiers

## Database Manager

### CODXJuniorDB

Main database manager class handling all persistence operations.

**Initialization:**
```python
db = CODXJuniorDB(settings: CODXJuniorSettings)
```

The manager automatically:
- Creates three TinyDB tables: kanban, column, and chat
- Reuses existing connections via PROJECT_DATABASES cache
- Configures JSON formatting (sort keys, indentation)

**Key Methods:**

#### `save_kanban(kanban: Kanban) -> Kanban`
Saves or updates a kanban board. Auto-generates doc_id and timestamps for new boards.

#### `get_kanban(kanban_id: str) -> Kanban`
Retrieves a kanban by its document ID.

#### `get_all_kankan() -> List[Kanban]`
Retrieves all kanbans from the database.

#### `get_kanban_chats(kanban_id: str, column_id: str) -> List[Chat]`
Loads all chats from a specific kanban column.

#### `save_chat(chat: Chat) -> None`
Saves or updates a chat. Auto-generates doc_id and timestamps for new chats.

#### `get_chat(chat_id: str) -> Chat`
Retrieves a chat by its document ID.

#### `reset() -> None`
Clears the database file and reinitializes the connection.

## Constants

- `ROLE_USER` - "user" - User message role identifier
- `ROLE_ASSISTANT` - "assistant" - Assistant message role identifier
- `MAX_IMAGE_SIZE_MB` - 50 - Maximum image attachment size in megabytes
- `MAX_IMAGE_SIZE_BYTES` - 52,428,800 - Maximum image attachment size in bytes

## Caching

The module implements connection-level caching through `PROJECT_DATABASES` dictionary to prevent multiple TinyDB connections to the same database file per project path.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/model/model.py
**Imported by:** codx/junior/agents/git_issues_agent.py, codx/junior/api/chat.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/chat/chat_export.py, codx/junior/chat/chat_knowledge.py, codx/junior/chat_manager.py, codx/junior/engine/chat_engine_actions.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/engine/wiki_engine.py, codx/junior/events/event_manager.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/mentions/mention_manager.py, codx/junior/sio/model.py, codx/junior/tools/code_writer.py, tests/db/test_db.py