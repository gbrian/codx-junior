# Chat API Documentation

## Overview

The Chat API module provides FastAPI route handlers for managing chat interactions, messages, and kanban boards in the codx-junior project. It enables creating, updating, deleting, searching, and exporting chats with full-text search capabilities and merge-safe operations.

## Core Endpoints

### Chat Cancellation

#### `POST /chat/cancel`

Cancels an in-flight chat request using either a chat ID or cancellation token UUID.

**Request Payload:**
```json
{
  "chat_id": "<chat doc_id to cancel>",
  "token_id": "<cancellation token UUID>"
}
```

**Response:**
- Success: `{ "cancelled": true, "method": "chat_id"|"token_id" }`
- Failure: `{ "cancelled": false, "error": "..." }`

**Notes:**
- At least one key (chat_id or token_id) must be provided
- Uses the CANCELLATION_REGISTRY to perform actual cancellation

### Message Management

#### `POST /chats/message`

Adds a single message to a chat (merge-safe, idempotent).

**Request Payload:**
```json
{
  "chat_id": "<chat UUID>",
  "message": {
    "content": "...",
    "role": "user|assistant|system",
    "doc_id": "<optional UUID>",
    "...": "other Message fields"
  }
}
```

**Returns:** The updated Chat object with merged messages.

#### `PUT /chats/message`

Updates an existing message in a chat (merge-safe).

**Request Payload:**
```json
{
  "chat_id": "<chat UUID>",
  "message": {
    "doc_id": "<message UUID>",
    "content": "...",
    "role": "user|assistant|system",
    "...": "other Message fields"
  }
}
```

**Notes:**
- Messages are matched by doc_id
- If not found, the message is appended
- Returns the updated Chat object

#### `DELETE /chats/message`

Removes a message from a chat (merge-safe).

**Query Parameters:**
- `chat_id`: Chat UUID (required)
- `message_doc_id`: Message doc_id to remove (required)

**Returns:** The updated Chat object with the message removed.

### Chat Metadata

#### `POST /chats/metadata`

Updates chat metadata only (name, description, board, column, etc.) without touching messages.

**Request Payload:**
```json
{
  "chat_id": "<chat UUID>",
  "metadata": {
    "name": "...",
    "description": "...",
    "board": "...",
    "column": "...",
    "...": "other fields (excluding messages)"
  }
}
```

**Returns:** The updated Chat object.

### Chat Listing and Retrieval

#### `GET /chats`

Lists chats with optional filtering and export functionality.

**Query Parameters:**
- `file_path`: Load a specific chat by file path
- `id`: Load a specific chat by ID
- `export_format`: Export format (markdown, docx, pdf, excel, etc.)
- `from_date`: ISO-format date for filtering (list operation only)

**Returns:**
- Single Chat object if `id` or `file_path` is provided
- Export response with appropriate content-type if `export_format` is specified
- List of Chat objects otherwise

### Chat Search

#### `POST /chats/search`

Searches chats with full-text search, field-level filtering, and pagination.

**Request Payload:**
```json
{
  "query": "<search query string>",
  "from_date": "<ISO-format date, optional>",
  "to_date": "<ISO-format date, optional>",
  "page": 1,
  "page_size": 20,
  "filters": {}
}
```

**Response Structure:**
```json
{
  "results": [],
  "total": 0,
  "page": 1,
  "page_size": 20,
  "total_pages": 0,
  "has_next": false,
  "has_prev": false,
  "error": "string (if applicable)"
}
```

**Validation Rules:**
- Page must be >= 1
- Page size is clamped between 1 and 100
- Query parameter cannot be empty
- Dates must use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)

### Chat Operations

#### `POST /chats`

Main chat endpoint. Delegates to session for AI turn execution.

**Request:** Chat object data

**Process:**
1. Initializes Chat object from request data
2. Executes chat event notification
3. Calls `chat_with_project()` on the session
4. Saves the chat

**Returns:** Updated Chat object.

#### `POST /chats/from-url`

Initializes a chat from a URL. Delegates to session.

**Request:** Chat object data with URL information

**Process:**
1. Initializes Chat object
2. Calls `init_chat_from_url()` on the session
3. Saves the chat

**Returns:** Updated Chat object.

#### `POST /chats/sub-tasks`

Generates subtasks from chat content. Delegates to session.

**Request:** Chat object data

**Returns:** Generated tasks result from session.

#### `PUT /chats`

Saves a chat using the chat manager.

**Request:** Chat object data

**Query Parameters:**
- `chat_only`: Set to "1" to save only the chat without related data

**Returns:** Saved Chat object.

#### `DELETE /chats`

Deletes a chat by chat_id.

**Query Parameters:**
- `chat_id`: Chat ID to delete (required)

**Returns:** `{ "deleted": true }`

### Kanban Management

#### `GET /kanban`

Loads the kanban board. Delegates to chat_manager.

**Returns:** Kanban object.

#### `POST /kanban`

Saves kanban board configuration. Delegates to chat_manager.

**Request:** Kanban object data (JSON)

**Returns:** `{ "saved": true }`

#### `DELETE /kanban`

Deletes a kanban board.

**Query Parameters:**
- `kanban_title`: Title of the kanban board to delete (required)

**Returns:** `{ "deleted": true }`

## Error Handling

All endpoints implement comprehensive error handling with structured responses:
- Missing required parameters return appropriate error messages
- Invalid inputs (pagination, dates, etc.) return descriptive errors
- Unexpected exceptions are logged and returned with error details
- All error responses follow the pattern: `{ "error": "message" }`

## Dependencies

- **FastAPI**: Web framework for routing and request handling
- **CANCELLATION_REGISTRY**: Manages in-flight request cancellations
- **Chat Manager**: Handles all chat persistence and search operations
- **Message Model**: Database model for chat messages
- **Chat Model**: Database model for chat data

## Session Integration

All endpoints access the chat manager through `request.state.codx_junior_session`, which provides:
- `get_chat_manager()`: Access to chat persistence layer
- `chat_event()`: Event notification mechanism
- `chat_with_project()`: AI interaction execution
- `init_chat_from_url()`: URL-based chat initialization
- `generate_tasks()`: Task generation from chat
- `save_chat()`: Chat persistence

## Dependencies
**Imports from:** codx/junior/ai/cancellation.py, codx/junior/db.py, codx/junior/profiling/profiler.py
**Imported by:** codx/junior/app.py