## CODX Junior Database Management documentation

This document describes the data models and the `CODXJuniorDB` class, which provides structured persistence and retrieval mechanisms for various features within the CODX Junior application. The module handles defining complex data structures using Pydantic models and managing interactions with the underlying database client (TinyDB).

### Data Models

The system uses several Pydantic models to enforce structure and consistency when handling core entities:

#### `KanbanColumn`
Represents a single column within a Kanban board.

| Field | Type | Description |
| :--- | :--- | :--- |
| `doc_id` | Optional[str] | Unique identifier for the document. |
| `title` | str | The title of the column. |
| `color` | Optional[str] | The visual color assigned to the column. |
| `index` | int | The sorting index of the column. |
| `chats` | List[str] | A list of chat IDs associated with this column. |

#### `Kanban`
Represents an entire Kanban board structure.

| Field | Type | Description |
| :--- | :--- | :--- |
| `doc_id` | Optional[str] | Unique identifier for the kanban board. |
| `title` | str | The title of the board. |
| `description` | Optional[str] | Detailed description of the board. |
| `index` | int | The sorting index of the board. |
| `columns` | List[`KanbanColumn`] | List of columns contained within the board. |
| `created_at` | str | Timestamp when the kanban was created. |
| `updated_at` | str | Timestamp last updated. |

#### `Message`
Represents a single message entry (e.g., in a chat).

| Field | Type | Description |
| :--- | :--- | :--- |
| `doc_id` | Optional[str] | Unique identifier for the message. |
| `role` | str | The role of the speaker (e.g., 'user', 'ai'). |
| `task_item` | str | A specific task item associated with the message. |
| `content` | str | The actual content written in the message. |
| `think` | Optional[str] | Content generated during thinking processes. |
| `hide` | bool | Flag to determine if the message should be visible (default: False). |
| `is_answer` | bool | Indicates if the message is an answer/response. |
| `improvement` | bool | Indicates if the message contains improvements. |
| `created_at` | str | Timestamp when the message was created. |
| `updated_at` | str | Timestamp of the last update. |
| `images` | List[str] | List of image paths/URIs included with the message. |
| `files` | List[str] | List of file paths/names associated with the message. |
| `knowledge_topics` | List[str] | Topics used to index the message for knowledge retrieval. |
| `done` | Optional[bool] | Indicates if the user is finished writing (default: True). |

#### `ChatHistoryEntry`
Tracks summary information about past chat sessions.

| Field | Type | Description |
| :--- | :--- | :--- |
| `timestamp` | str | Timestamp when this history entry was generated. |
| `summary` | str | A brief summary of the historical chat segment. |
| `message_ids` | List[str] | List of message IDs associated with this summary. |

#### `Chat`
Represents an overarching conversation thread or session.

| Field | Type | Description |
| :--- | :--- | :--- |
| `doc_id` | Optional[str] | Unique identifier for the chat. |
| `project_id` | Optional[str] | Defines the project the chat belongs to. |
| `owner_project_id` | Optional[str] | The ID of the project that owns this chat entry. |
| `parent_id` | Optional[str] | Reference to a parent chat conversation. |
| `linked_chat_ids` | List[str] | IDs of other chats linked to this one. |
| `child_index` | Optional[int] | Used to sort multiple related chat contents (siblings). |
| `status` | str | The current operational status of the chat. |
| `messages` | List[`Message`] | The sequence of individual messages within the chat. |
| `kanban_id` | str | Reference ID linking the chat to a specific Kanban board. |
| `columns` | List[`KanbanColumn`] | Columns associated with this chat context. |
| `history` | List[`ChatHistoryEntry`] | Historical entries of this chat. |

### CODXJuniorDB Class

The `CODXJuniorDB` class is the primary interface for managing database operations, ensuring that interactions are structured and scalable across different projects. It uses a dictionary (`PROJECT_DATABASES`) to potentially manage multiple database instances based on the project path (`self.settings.abs_project_path`).

#### Initialization
The constructor requires `CODXJuniorSettings` and initializes the connection using the specified absolute project path (`self.db_path`). It sets up three core tables: `kanban`, `column`, and `chat`.

**Constructor:** `__init__(self, settings: CODXJuniorSettings)`

#### Core Methods

*   **`reset(self) `**:
    *   Purpose: Removes the database file associated with the current project path.
    *   Action: Deletes the `.db.json` file and clears the pointer in `PROJECT_DATABASES`.
*   **Kanban Management:**
    *   **`save_kanban(self, kanban: Kanban)`**: Saves a Kanban board instance. If `doc_id` is missing, it generates a new UUID and sets timestamps. If `doc_id` exists, it updates the record with new data while preserving the ID.
    *   **`get_kanban(self, kanban_id: str)`**: Retrieves a single Kanban board by its document identifier (`doc_id`).
    *   **`get_all_kankan(self)`**: Fetches all stored `Kanban` objects from the database.
    *   **`get_kanban_chats(self, kanban_id: str, column_id: str)`**: Retrieves a list of `Chat` objects that belong to a specific Kanban board and column combination.
*   **Chat Management:**
    *   **`get_chat(self, chat_id: str)`**: Retrieves a single `Chat` object using its document identifier (`doc_id`).
    *   **`save_chat(self, chat: Chat)`**: Saves or updates a `Chat` session. Similar to `Kanban`, it supports creation (generating UUIDs and timestamps) or updating existing records based on the `doc_id`.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/model/model.py
**Imported by:** codx/junior/agents/git_issues_agent.py, codx/junior/api/chat.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/chat/chat_export.py, codx/junior/chat/chat_knowledge.py, codx/junior/chat_manager.py, codx/junior/engine/chat_engine_actions.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/engine/wiki_engine.py, codx/junior/events/event_manager.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/mentions/mention_manager.py, codx/junior/sio/model.py, codx/junior/tools/code_writer.py, tests/db/test_db.py