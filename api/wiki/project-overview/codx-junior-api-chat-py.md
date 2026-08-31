# Chat API Documentation

## Overview

The Chat API provides endpoints for managing chat conversations, messages, and kanban boards within the codx-junior project. It enables full CRUD operations on chats, message management, search capabilities, and export functionality.

## Core Endpoints

### Chat Management

#### Cancel In-Flight Chat Request
**POST** `/chat/cancel`

Cancels an active chat request by chat ID or cancellation token UUID.

**Request Payload:**
```json
{
  "chat_id": "<chat doc_id to cancel>",
  "token_id": "<cancellation token UUID>"
}
```

**Response:**
```json
{
  "cancelled": true,
  "method": "chat_id|token_id"
}
```

At least one identifier (chat_id or token_id) must be provided. The endpoint uses the `CANCELLATION_REGISTRY` to manage active cancellation tokens.

---

#### List or Retrieve Chats
**GET** `/chats`

Retrieves chats with optional filtering, export, or single-chat retrieval.

**Query Parameters:**
- `file_path`: Load a specific chat by file path
- `id`: Load a specific chat by ID
- `export_format`: Export format (markdown, docx, pdf, excel, etc.)
- `from_date`: ISO-format date for filtering (list operation only)

**Response:**
- Single Chat object (when `id` or `file_path` provided)
- File download (when `export_format` provided)
- List of Chat objects (default)

---

#### Create/Execute Chat
**POST** `/chats`

Initiates a chat with the project and delegates AI turn execution to the session.

**Request Payload:**
```json
{
  "chat_id": "<UUID>",
  "messages": [...],
  ...
}
```

**Response:** Updated Chat object with AI responses

---

#### Save Chat
**PUT** `/chats`

Persists a chat to storage with optional message filtering.

**Query Parameters:**
- `chat_only`: Set to "1" to save only chat metadata without messages

**Request Payload:**
```json
{
  "chat_id": "<UUID>",
  ...
}
```

**Response:** Saved Chat object

---

#### Delete Chat
**DELETE** `/chats`

Removes a chat from storage.

**Query Parameters:**
- `chat_id`: Chat UUID to delete

**Response:**
```json
{
  "deleted": true
}
```

---

### Message Operations

#### Add Message
**POST** `/chats/message`

Adds a new message to a chat (merge-safe, idempotent).

**Request Payload:**
```json
{
  "chat_id": "<chat UUID>",
  "message": {
    "content": "...",
    "role": "user|assistant|system",
    "doc_id": "<optional UUID>",
    ...
  }
}
```

**Response:** Updated Chat object with merged messages

---

#### Update Message
**PUT** `/chats/message`

Updates an existing message in a chat (merge-safe). Messages are matched by doc_id; if not found, the message is appended.

**Request Payload:**
```json
{
  "chat_id": "<chat UUID>",
  "message": {
    "doc_id": "<message UUID>",
    "content": "...",
    "role": "user|assistant|system",
    ...
  }
}
```

**Response:** Updated Chat object

---

#### Remove Message
**DELETE** `/chats/message`

Removes a message from a chat (merge-safe).

**Query Parameters:**
- `chat_id`: Chat UUID
- `message_doc_id`: Message doc_id to remove

**Response:** Updated Chat object with message removed

---

### Chat Metadata

#### Update Chat Metadata
**POST** `/chats/metadata`

Updates chat metadata (name, description, board, column, etc.) without modifying messages.

**Request Payload:**
```json
{
  "chat_id": "<chat UUID>",
  "metadata": {
    "name": "...",
    "description": "...",
    "board": "...",
    "column": "...",
    ...
  }
}
```

**Response:** Updated Chat object

---

### Search and Advanced Operations

#### Search Chats
**POST** `/chats/search`

Performs full-text search on chats with field-level filtering and pagination.

**Request Payload:**
```json
{
  "query": "<search query string>",
  "from_date": "<ISO-format date, optional>",
  "to_date": "<ISO-format date, optional>",
  "page": 1,
  "page_size": 20,
  "filters": { ... }
}
```

**Response:**
```json
{
  "results": [...],
  "total": 0,
  "page": 1,
  "page_size": 20,
  "total_pages": 0,
  "has_next": false,
  "has_prev": false
}
```

Page size is capped at 100. Query parameter cannot be empty. Date format must be ISO (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).

---

#### Initialize Chat from URL
**POST** `/chats/from-url`

Initializes a chat session by loading content from a URL.

**Request Payload:**
```json
{
  "chat_id": "<UUID>",
  "url": "...",
  ...
}
```

**Response:** Chat object with loaded content

---

#### Generate Subtasks
**POST** `/chats/sub-tasks`

Generates subtasks from an existing chat using AI analysis.

**Request Payload:**
```json
{
  "chat_id": "<UUID>",
  ...
}
```

**Response:** Generated tasks/subtasks

---

### Kanban Board Operations

#### Load Kanban
**GET** `/kanban`

Retrieves the current kanban board state.

**Response:** Kanban board object

---

#### Save Kanban
**POST** `/kanban`

Persists kanban board state (columns, tasks, etc.).

**Request Payload:**
```json
{
  "title": "...",
  "columns": [...],
  ...
}
```

**Response:**
```json
{
  "saved": true
}
```

---

#### Delete Kanban
**DELETE** `/kanban`

Removes a kanban board.

**Query Parameters:**
- `kanban_title`: Title of the kanban board to delete

**Response:**
```json
{
  "deleted": true
}
```

---

## Session Integration

All endpoints require access to `codx_junior_session` via `request.state`, which provides:
- `get_chat_manager()`: Returns the ChatManager for database operations
- `chat_event()`: Logs chat-related events
- `chat_with_project()`: Executes AI chat logic
- `save_chat()`: Persists chat state
- `generate_tasks()`: AI-powered task generation
- `init_chat_from_url()`: URL-based chat initialization

---

## Error Handling

All endpoints include comprehensive exception handling with structured error responses:

```json
{
  "error": "<error message>"
}
```

Common error scenarios:
- Missing required parameters (chat_id, message, etc.)
- Chat not found
- Invalid pagination or date formats
- Unexpected server errors

Errors are logged via the `logger` module with context-specific information.

---

## Key Features

- **Merge-Safe Operations**: Message add/update/remove operations are designed to be merge-safe and idempotent
- **Flexible Retrieval**: Support for single-chat retrieval by ID or file path
- **Export Support**: Multiple export formats (markdown, docx, pdf, excel)
- **Pagination**: Search results support configurable page-based pagination
- **Cancellation Support**: In-flight requests can be cancelled via chat_id or token_id
- **Kanban Integration**: Dedicated endpoints for kanban board management

## Dependencies
**Imports from:** codx/junior/ai/cancellation.py, codx/junior/db.py, codx/junior/profiling/profiler.py
**Imported by:** codx/junior/app.py