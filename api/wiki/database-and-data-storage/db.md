# Database Models and Data Storage

## Overview

This module defines the core data models used in the CODX Junior API for managing chat sessions, messages, attachments, and kanban boards. All models are built using Pydantic's `BaseModel` for validation and serialization.

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `ROLE_USER` | "user" | Role identifier for user messages |
| `ROLE_ASSISTANT` | "assistant" | Role identifier for assistant messages |
| `MAX_IMAGE_SIZE_MB` | 50 | Maximum allowed image size in megabytes |
| `MAX_IMAGE_SIZE_BYTES` | 52428800 | Maximum allowed image size in bytes |

## Core Models

### ChatAttachment

Represents an image stored in chat or message with file metadata and base64 encoded data.

**Fields:**
- `file_name` (str): Original file name of the image
- `file_type` (str): MIME type (e.g., 'image/png', 'image/jpeg')
- `file_size` (int): File size in bytes
- `base64_data` (str): Base64 encoded image data
- `uploaded_at` (str): Timestamp when image was uploaded

**Validations:**
- File size cannot exceed 50MB
- Allowed MIME types: `image/png`, `image/jpeg`, `image/jpg`, `image/gif`, `image/webp`, `image/svg+xml`

### Message

Represents a single chat message with content, attachments, and event tracking.

**Key Fields:**
- `doc_id` (str, optional): Document identifier
- `role` (str): Message author role (user or assistant)
- `content` (str): Message text content
- `think` (str, optional): Internal reasoning or thoughts
- `hide` (bool): Whether message is hidden from display
- `is_answer` (bool): Whether message is marked as an answer
- `attachments` (List[ChatAttachment]): Images attached to this message
- `files` (List[str]): File references
- `created_at` (str): Creation timestamp
- `updated_at` (str): Last update timestamp
- `meta_data` (Dict, optional): Free-form supplementary metadata (timings, model, analytics)
- `tool_events` (List[ToolEvent]): Tool execution events associated with this response
- `lifecycle_events` (List[LifeCycleEvent]): Agent run lifecycle events
- `knowledge_topics` (List[str]): Topics for knowledge indexing
- `done` (bool): Whether user finished writing
- `is_thinking` (bool): Whether message is in thinking state
- `disable_knowledge` (bool): Disables knowledge indexing for this message
- `read_by` (List[str]): User IDs who have read this message
- `linked_chat_ids` (List[str]): References to linked chats

### ToolEvent

Tracks tool execution events during assistant response generation.

**Fields:**
- `tool` (str): Name of the executed tool
- `tool_call_id` (str): Unique identifier for the tool call
- `status` (str): Execution status ('running', 'done', or 'error')
- `request` (Dict, optional): Parsed JSON arguments sent to the tool
- `response` (str, optional): Truncated tool result preview
- `duration_ms` (float, optional): Execution time in milliseconds
- `error` (str, optional): Error details when status is 'error'

### LifeCycleEvent

Tracks agent run lifecycle events and execution metrics.

**Fields:**
- `status` (str): Lifecycle status ('running', 'done', or 'error')
- `run_id` (str): Unique identifier for the agent run
- `duration_ms` (float, optional): Execution time in milliseconds
- `error` (str, optional): Error details when status is 'error'

### Chat

Represents a complete chat session with messages, metadata, and kanban board associations.

**Key Fields:**
- `id` (str, optional): Chat identifier
- `doc_id` (str, optional): Document identifier
- `project_id` (str, optional): Project where chat operates
- `owner_project_id` (str, optional): Project where chat was created
- `parent_id` (str, optional): Parent chat reference
- `linked_chat_ids` (List[str]): References to linked chats
- `message_id` (str, optional): Parent message for threads
- `status` (str): Chat status
- `name` (str): Chat display name
- `description` (str): Chat description
- `messages` (List[Message]): Chat message history
- `tags` (List[str]): Informative tags
- `profiles` (List[str]): Associated profiles
- `users` (List[str]): Associated users
- `created_at` (str): Creation timestamp
- `updated_at` (str): Last update timestamp
- `mode` (str): Chat mode (default: 'chat')
- `kanban_id` (str): Associated kanban board identifier
- `llm_model` (str, optional): Language model used
- `visibility` (str, optional): Chat visibility setting
- `attachments` (List[ChatAttachment]): Chat-level attachments
- `knowledge_topics` (List[str]): Topics for knowledge indexing
- `history` (List[ChatHistoryEntry]): Historical entries with summaries
- `auto_initialize` (bool): Auto-fill board and column on first response
- `ignore_parent_knowledge` (bool): Disconnect from parent knowledge context
- `ignore_parent_files` (bool): Exclude parent file list from context

### KanbanColumn

Represents a column in a Kanban board.

**Fields:**
- `doc_id` (str, optional): Document identifier
- `title` (str): Column title
- `color` (str, optional): Column display color
- `index` (int): Column order position
- `chats` (List[str]): Chat IDs in this column

### Kanban

Represents a complete Kanban board with columns and chats.

**Fields:**
- `doc_id` (str, optional): Document identifier
- `title` (str): Board title
- `description` (str, optional): Board description
- `index` (int): Board order position
- `columns` (List[KanbanColumn]): Board columns
- `created_at` (str): Creation timestamp
- `updated_at` (str): Last update timestamp

### ChatHistoryEntry

Represents a historical entry in a chat with summary and associated messages.

**Fields:**
- `timestamp` (str): When this history entry was generated
- `summary` (str): Summary of the history entry
- `message_ids` (List[str]): Message IDs associated with this entry

### ChatId

Represents a reference to a chat in another project.

**Fields:**
- `chat_id` (str): Chat identifier
- `project_id` (str): Project containing the chat

## Event Association Pattern

Tool and lifecycle events emitted during assistant response generation are associated with the response message rather than stored as separate messages. Both event lists are:
- Streamed in real time with the message
- Updated in place (running → done/error)
- Persisted with the chat

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/model/model.py
**Imported by:** codx/junior/agents/git_issues_agent.py, codx/junior/api/chat.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/chat/chat_export.py, codx/junior/chat/chat_knowledge.py, codx/junior/chat_manager.py, codx/junior/engine/chat_engine_actions.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/engine/wiki_engine.py, codx/junior/events/event_manager.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/mentions/mention_manager.py, codx/junior/sio/model.py, codx/junior/tools/code_writer.py, tests/db/test_db.py