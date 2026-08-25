# Database and Data Storage

## Overview

This module provides database management functionality for CODXJunior using TinyDB. It handles persistence of kanban boards, columns, and chats with table-level caching capabilities.

## Core Components

### Message Role Constants

The module defines standard message role constants to maintain consistency across the application:

- `ROLE_USER = "user"` - Messages from users
- `ROLE_ASSISTANT = "assistant"` - Messages from the AI assistant
- `ROLE_TOOL = "tool"` - Tool execution and lifecycle event notifications

These constants should be used instead of literal strings throughout the codebase.

### Data Models

#### KanbanColumn

Represents a single column in a Kanban board with the following properties:

- `doc_id` - Optional document identifier
- `title` - Column title
- `color` - Optional color designation
- `index` - Column position
- `chats` - List of associated chat IDs

#### Kanban

Represents a complete Kanban board with:

- `doc_id` - Document identifier
- `title` - Board title
- `description` - Optional board description
- `index` - Board position
- `columns` - List of KanbanColumn objects
- `created_at` and `updated_at` - Timestamps

#### Message

A single chat message with extensive properties for supporting various communication types:

- `doc_id` - Document identifier
- `role` - Message role (user, assistant, or tool)
- `content` - Message text content
- `think` - Optional thinking/reasoning content
- `images` and `files` - Associated media
- `tool_event` - Optional tool execution event details
- `lifecycle_event` - Optional lifecycle event details
- `knowledge_topics` - Topics for knowledge indexing
- `done` - Indicates if user has finished writing
- `is_thinking` - Indicates active thinking state
- `disable_knowledge` - Flag to exclude from knowledge indexing
- `read_by` - List of users who have read the message
- `linked_chat_ids` - References to related chats

#### ToolEvent

Tracks tool execution events with:

- `tool` - Name of the executed tool
- `tool_call_id` - Unique identifier from the provider
- `status` - Execution status (running, done, or error)
- `request` - Parsed JSON arguments
- `response` - Truncated result preview
- `duration_ms` - Execution time in milliseconds
- `error` - Error details when applicable

#### LifeCycleEvent

Represents agent run lifecycle changes with:

- `status` - Lifecycle status (running, done, or error)
- `run_id` - Unique run identifier
- `duration_ms` - Execution time in milliseconds
- `error` - Error details when applicable

#### Chat

Represents a complete chat session with:

- `doc_id` - Document identifier
- `project_id` - Project context
- `owner_project_id` - Project owner reference
- `parent_id` - Parent chat reference for threads
- `linked_chat_ids` - Related chat references
- `name` - Chat name
- `description` - Chat description
- `messages` - List of Message objects
- `file_list` - Associated files
- `profiles` and `users` - Access control
- `kanban_id` and `column_id` - Kanban board association
- `knowledge_topics` - Topics for knowledge indexing
- `pr_view` - Pull request information
- `history` - ChatHistoryEntry records
- `auto_initialize` - Flag for new chat initialization
- `ignore_parent_knowledge` - Flag to disconnect from parent context
- `ignore_parent_files` - Flag to exclude parent files

### Database Manager

#### CODXJuniorDB

The main database manager class provides:

**Initialization**

```python
def __init__(self, settings: CODXJuniorSettings) -> None
```

Initializes the database manager with configuration from CODXJuniorSettings. Creates connections to three tables: kanban, column, and chat with disabled caching.

**Client Initialization**

```python
def init_client(self) -> None
```

Initializes the TinyDB client on first use. Reuses existing connections from PROJECT_DATABASES cache to avoid multiple connections to the same database file.

**Database Reset**

```python
def reset(self) -> None
```

Removes the database file and reinitializes, useful for clearing all data and starting fresh.

**Kanban Operations**

- `save_kanban(kanban: Kanban) -> Kanban` - Persists a kanban board, generating new UUID and timestamps for new records
- `get_kanban(kanban_id: str) -> Kanban` - Retrieves a kanban by its ID
- `get_all_kankan() -> List[Kanban]` - Retrieves all kanbans from the database
- `get_kanban_chats(kanban_id: str, column_id: str) -> List[Chat]` - Loads all chats from a specific column

**Chat Operations**

- `save_chat(chat: Chat) -> None` - Persists a chat, generating new UUID and timestamps for new records
- `get_chat(chat_id: str) -> Chat` - Retrieves a chat by its ID

## Key Features

- **Caching Strategy** - Tables are initialized with cache_size=0 to ensure data consistency
- **Automatic Timestamps** - Creation and update timestamps are automatically managed
- **UUID Generation** - New records receive unique identifiers automatically
- **Project Isolation** - Database connections are cached per project path to prevent conflicts
- **Hierarchical Relationships** - Support for parent-child chat relationships and kanban associations

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/model/model.py
**Imported by:** codx/junior/agents/git_issues_agent.py, codx/junior/api/chat.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/chat/chat_export.py, codx/junior/chat/chat_knowledge.py, codx/junior/chat_manager.py, codx/junior/engine/chat_engine_actions.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/engine/wiki_engine.py, codx/junior/events/event_manager.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/mentions/mention_manager.py, codx/junior/sio/model.py, codx/junior/tools/code_writer.py, tests/db/test_db.py