# Chat API Documentation

## Overview

The Chat API provides endpoints for managing chat sessions, searching conversations, canceling requests, and organizing chats through a kanban board interface. This module serves as the primary router for chat-related operations in the codx-api project.

## Endpoints

### Chat Cancellation

#### POST `/chat/cancel`

Cancels an in-flight chat request using either a chat document ID or a cancellation token UUID.

**Request Payload:**
```json
{
    "chat_id": "<chat doc_id to cancel>",
    "token_id": "<cancellation token UUID>"
}
```

At least one key must be provided. When both are present, `chat_id` is attempted first.

**Response:**
- Success: `{ "cancelled": true, "method": "chat_id"|"token_id" }`
- Failure: `{ "cancelled": false, "error": "..." }`

**Behavior:**
- Attempts cancellation by `chat_id` first
- Falls back to `token_id` if no token is found for `chat_id`
- Returns an error if neither `chat_id` nor `token_id` produces a result

### Chat Listing and Retrieval

#### GET `/chats`

Lists chats with optional filtering, single chat retrieval, and export functionality.

**Query Parameters:**
- `file_path`: Load a specific chat by file path
- `id`: Load a specific chat by ID
- `export_format`: Export format (markdown, docx, pdf, excel, etc.)
- `from_date`: ISO-format date for filtering (list_chats only)

**Returns:**
- Single Chat object if `id` or `file_path` is provided
- Export response with appropriate content type if `export_format` is provided
- List of Chat objects otherwise

### Chat Search

#### POST `/chats/search`

Performs full-text search across chats with pagination support.

**Request Payload:**
```json
{
    "query": "<search query string>",
    "from_date": "<ISO-format date, optional>",
    "to_date": "<ISO-format date, optional>",
    "page": 1,
    "page_size": 20
}
```

**Search Scope:**
- Chat name, description, status, and mode
- Message content and thinking field
- Message user, profiles, and knowledge topics
- File list and LLM model
- Chat history summaries

**Response:**
```json
{
    "results": [
        {
            "chat": { ... },
            "relevance_score": 15.5,
            "matched_fields": ["name", "message_content"]
        }
    ],
    "total": 42,
    "page": 1,
    "page_size": 20,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
}
```

**Validation:**
- Page size is capped at 100 items per page
- Dates must be in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
- Query parameter cannot be empty

### Chat Operations

#### POST `/chats`

Creates and initiates a chat conversation with the project.

**Request:** Chat object data

**Process:**
1. Creates a Chat instance from request data
2. Triggers chat event with "Chatting with project..." message
3. Executes chat with project
4. Saves the chat

**Returns:** Chat object

#### POST `/chats/from-url`

Initializes a chat from a URL source.

**Request:** Chat object data with URL information

**Process:**
1. Creates a Chat instance
2. Initializes chat from provided URL
3. Saves the chat

**Returns:** Chat object

#### POST `/chats/sub-tasks`

Generates subtasks from a chat.

**Request:** Chat object data

**Returns:** Generated tasks

#### PUT `/chats`

Saves an existing chat with optional chat-only flag.

**Query Parameters:**
- `chatonly`: Set to "1" to save only chat data (optional)

**Request:** Updated Chat object data

#### DELETE `/chats`

Deletes a chat by ID.

**Query Parameters:**
- `chat_id`: ID of the chat to delete

### Kanban Board

#### GET `/kanban`

Retrieves the current kanban board layout.

**Returns:** Kanban board object

#### POST `/kanban`

Saves or updates the kanban board configuration.

**Request:** Kanban board object as JSON

#### DELETE `/kanban`

Deletes a kanban board by title.

**Query Parameters:**
- `kanban_title`: Title of the kanban board to delete

## Session Management

All endpoints access the chat manager and session data through `request.state.codx_junior_session`, which provides:
- `get_chat_manager()`: Returns the chat manager instance
- `chat_event()`: Logs chat events
- `chat_with_project()`: Executes chat interactions
- `save_chat()`: Persists chat data
- `list_chats()`: Retrieves all chats
- `delete_chat()`: Removes a chat
- `settings`: Access to session settings including project name

## Error Handling

The API provides comprehensive error responses including:
- Missing or invalid parameters
- Invalid date formats
- Missing chat or token data
- Unexpected search or operation errors

All errors are logged with appropriate severity levels (warning, error, info) for debugging and monitoring purposes.

## Dependencies
**Imports from:** codx/junior/ai/cancellation.py, codx/junior/db.py, codx/junior/profiling/profiler.py
**Imported by:** codx/junior/app.py