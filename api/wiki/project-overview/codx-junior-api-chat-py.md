# Chat API Documentation

## Overview

The Chat API provides endpoints for managing chat sessions, messages, and search functionality within the codx-junior project. It implements cancellation support for in-flight requests, message management, chat retrieval, and comprehensive search capabilities.

## Endpoints

### Chat Cancellation

**POST** `/chat/cancel`

Cancels an in-flight chat request by either chat ID or cancellation token UUID.

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

**Flow:**
1. Check if `chat_id` is provided and attempt cancellation
2. If no token found for `chat_id`, fall back to `token_id`
3. Return appropriate response based on cancellation result

---

### Message Management

**POST** `/chats/message`

Adds a single message to a chat in a merge-safe, idempotent manner. Used during AI turns to persist events without overwriting concurrent updates.

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

**Response:**
- Success: Updated Chat object with merged messages
- Failure: `{ "error": "..." }`

---

### Chat Retrieval

**GET** `/chats`

Lists chats with optional filtering and export functionality.

**Query Parameters:**
- `file_path`: Load a specific chat by file path
- `id`: Load a specific chat by ID
- `export_format`: Export format (markdown, docx, pdf, excel, etc.)
- `from_date`: ISO-format date for filtering (list operation only)

**Response:**
- Single Chat object if `id` or `file_path` is provided
- Export response (file download) if `export_format` is provided
- List of Chat objects otherwise

---

### Chat Search

**POST** `/chats/search`

Performs full-text search across chats with field-level filtering and pagination.

**Request Payload:**
```json
{
    "query": "<search query string>",
    "from_date": "<ISO-format date, optional>",
    "to_date": "<ISO-format date, optional>",
    "page": 1,
    "page_size": 20,
    "filters": {
        "search_name": true,
        "search_description": true,
        "search_messages": true,
        "search_message_metadata": true,
        "search_history": true,
        "search_files": true,
        "search_model": true,
        "search_status": true,
        "search_mode": true
    }
}
```

**Filter Flags:**
- All flags default to `true` (search enabled) when omitted
- Set to `false` to exclude that field category
- Allows fine-grained control similar to email filter dialogs

**Search Coverage:**
- Chat name, description, status, mode
- Message content and thinking field
- Message user, profiles, knowledge topics
- File list and LLM model
- Chat history summaries

**Response:**
```json
{
    "results": [
        {
            "chat": { "...": "chat object" },
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
- Query cannot be empty

---

### Chat Creation and Management

**POST** `/chats`

Creates and initiates a chat session with the project.

**POST** `/chats/from-url`

Creates a chat from an external URL.

**POST** `/chats/sub-tasks`

Generates subtasks for a given chat.

**PUT** `/chats`

Saves an existing chat. Query parameter `chatonly=1` saves only chat data without related information.

**DELETE** `/chats`

Deletes a chat by `chat_id` query parameter.

---

### Kanban Board Management

**GET** `/kanban`

Retrieves the current kanban board configuration.

**POST** `/kanban`

Updates the kanban board configuration.

**DELETE** `/kanban`

Deletes a kanban board by `kanban_title` query parameter.

---

## Error Handling

All endpoints implement comprehensive error handling:
- Missing or invalid parameters return descriptive error messages
- Exceptions are logged with context information
- Search operations provide empty results with error details on failure

## Dependencies
**Imports from:** codx/junior/ai/cancellation.py, codx/junior/db.py, codx/junior/profiling/profiler.py
**Imported by:** codx/junior/app.py