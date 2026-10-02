# Database and Data Storage

## Overview

This module provides database management for CODXJunior using TinyDB, handling persistence of kanban boards, columns, and chats with table-level caching.

## Core Components

### Message Role Constants

Two constants are defined to maintain consistency across the application:

- `ROLE_USER = "user"` - Represents user messages
- `ROLE_ASSISTANT = "assistant"` - Represents assistant messages

These constants should be used instead of literal strings throughout the codebase.

### Data Models

#### KanbanColumn

Represents a column in a Kanban board with the following properties:

- `doc_id` (optional): Document identifier
- `title`: Column title
- `color` (optional): Column color designation
- `index`: Position index within the kanban
- `chats`: List of associated chat IDs

#### Kanban

Represents a complete Kanban board with the following structure:

- `doc_id` (optional): Document identifier
- `title`: Board title
- `description` (optional): Board description
- `index`: Position index
- `columns` (optional): List of KanbanColumn objects
- `created_at`: Timestamp of creation
- `updated_at`: Timestamp of last update

#### Message

Represents a single chat message with comprehensive features:

**Basic Properties:**
- `doc_id` (optional): Document identifier
- `role`: Message sender role (user or assistant)
- `content`: Message text content
- `created_at`, `updated_at`: Timestamps

**Message Metadata:**
- `task_item`: Associated task item
- `think` (optional): Internal reasoning content
- `hide`: Whether to hide the message
- `is_answer`: Marks if this is an answer
- `improvement`: Indicates if this is an improvement
- `profiles`: Associated user profiles
- `user` (optional): User identifier
- `done` (optional): Whether user finished writing

**Content Properties:**
- `images`: List of associated image URLs
- `files`: List of associated file references
- `knowledge_topics`: Topics for knowledge indexing
- `disable_knowledge` (optional): Disables knowledge indexing

**Events and Metadata:**
- `tool_events`: List of ToolEvent objects tracking tool executions
- `lifecycle_events`: List of LifeCycleEvent objects tracking agent runs
- `meta_data` (optional): Free-form supplementary metadata
- `error` (optional): Error details if applicable
- `read_by`: List of users who read the message
- `linked_chat_ids` (optional): References to linked chats

#### ToolEvent

Tracks tool execution events attached to assistant responses:

- `tool`: Name of the executed tool
- `tool_call_id`: Unique identifier for the tool call
- `status`: Execution status (running, done, or error)
- `request` (optional): Parsed JSON arguments sent to the tool
- `response` (optional): Truncated tool result preview
- `duration_ms` (optional): Execution time in milliseconds
- `error` (optional): Error details when status is 'error'

#### LifeCycleEvent

Represents agent run status changes and execution metrics:

- `status`: Lifecycle status (running, done, or error)
- `run_id`: Unique identifier for the agent run
- `duration_ms` (optional): Execution time in milliseconds
- `error` (optional): Error details when status is 'error'

#### Chat

Represents a complete chat session with messages and metadata:

**Identification:**
- `id`, `doc_id` (optional): Document identifiers
- `project_id` (optional): Project where chat works
- `owner_project_id` (optional): Project where chat was created

**Hierarchy and Relations:**
- `parent_id` (optional): Parent chat reference
- `parent_owner_project_id`, `parent_project_id` (optional): Parent chat project references
- `child_index` (optional): Sorting index among siblings
- `message_id` (optional): Parent message for threads
- `linked_chat_ids` (optional): List of linked chat IDs

**Content and Structure:**
- `name`: Chat name
- `description`: Chat description
- `messages`: List of Message objects
- `status`: Chat status
- `mode`: Chat mode (default: 'chat')

**Kanban Integration:**
- `kanban_id`: Associated kanban ID
- `column_id`: Associated column ID
- `board`: Board identifier
- `column`: Column identifier
- `columns`: List of KanbanColumn objects
- `chat_index` (optional): Index within chat listing

**File and Knowledge Management:**
- `file_list`: List of associated file references
- `file_path`: File path reference
- `knowledge_topics`: Topics for knowledge indexing
- `ignore_parent_knowledge` (optional): Disconnects from parent knowledge when True
- `ignore_parent_files` (optional): Excludes parent files when True

**Additional Properties:**
- `created_at`, `updated_at`: Timestamps
- `pinned` (optional): Whether chat is pinned
- `profiles`, `users`: Associated profiles and users
- `url`, `branch`, `remote_url` (optional): Repository references
- `llm_model` (optional): Language model identifier
- `visibility` (optional): Chat visibility setting
- `check_lists` (optional): Associated checklists
- `chat_links`: References to chats in other projects
- `pr_view` (optional): Pull request view data
- `history`: Historical entries of the chat
- `auto_initialize` (optional): Auto-initialization flag for new chats

#### ChatHistoryEntry

Represents historical entries in a chat:

- `timestamp`: When the entry was generated
- `summary`: Summary of the history entry
- `message_ids`: Associated message IDs

#### ChatId

Represents a reference to a chat in another project:

- `chat_id`: The chat identifier
- `project_id`: The project this chat belongs to

### CODXJuniorDB Class

Main database manager class providing CRUD operations for kanban boards and chats.

#### Initialization

```python
def __init__(self, settings: CODXJuniorSettings) -> None
```

Initializes the database manager with:
- Settings configuration
- Database path derived from CODX path
- TinyDB client initialization
- Table setup for kanban, column, and chat data

The class uses a global `PROJECT_DATABASES` cache to reuse existing database connections and avoid multiple connections to the same database file.

#### Core Methods

**reset()**

Resets the database by removing the database file and reinitializing, useful for clearing all data and starting fresh.

**save_kanban(kanban: Kanban) -> Kanban**

Saves a kanban to the database:
- Creates new kanban with UUID and timestamps if no doc_id exists
- Updates existing kanban record if doc_id is present
- Returns the saved Kanban instance with doc_id

**get_kanban(kanban_id: str) -> Kanban**

Retrieves a kanban by its ID. Returns None if not found.

**get_all_kankan() -> List[Kanban]**

Retrieves all kanbans from the database.

**get_kanban_chats(kanban_id: str, column_id: str) -> List[Chat]**

Loads all chats from a specific column of a kanban, filtered by both kanban ID and column ID.

**get_chat(chat_id: str) -> Chat**

Retrieves a chat by its ID. Returns None if not found.

**save_chat(chat: Chat) -> None**

Saves a chat to the database:
- Creates new chat with UUID and timestamps if no doc_id exists
- Updates existing chat record if doc_id is present

## Usage Notes

- Message tool and lifecycle events are associated with assistant response messages and are streamed in real time, then persisted with the chat
- Both tool_events and lifecycle_events lists are updated in place as execution progresses (running → done/error)
- The database uses table-level caching with cache_size=0 for kanban, column, and chat tables

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/model/model.py
**Imported by:** codx/junior/agents/git_issues_agent.py, codx/junior/api/chat.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/chat/chat_export.py, codx/junior/chat/chat_knowledge.py, codx/junior/chat_manager.py, codx/junior/engine/chat_engine_actions.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/engine/wiki_engine.py, codx/junior/events/event_manager.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/mentions/mention_manager.py, codx/junior/sio/model.py, codx/junior/tools/code_writer.py, tests/db/test_db.py