# Database and Data Storage Module

## Overview

This module provides the database layer for the CODX Junior application, handling persistent storage of chats, kanban boards, and related entities. It uses a JSON-based database approach with in-memory caching to manage project-specific data.

---

## Data Models

### KanbanColumn

Represents a single column within a Kanban board.

| Field    | Type            | Default | Description                          |
|----------|-----------------|---------|--------------------------------------|
| `doc_id` | `Optional[str]` | `None`  | Unique identifier                    |
| `title`  | `str`           | `None`  | Column title                         |
| `color`  | `Optional[str]` | —       | Display color                        |
| `index`  | `int`           | `0`     | Sort order index                     |
| `chats`  | `List[str]`     | `[]`    | List of chat IDs within this column  |

---

### Kanban

Represents a Kanban board containing multiple columns.

| Field         | Type                        | Default        | Description               |
|---------------|-----------------------------|----------------|---------------------------|
| `doc_id`      | `Optional[str]`             | `None`         | Unique identifier         |
| `title`       | `str`                       | `None`         | Board title               |
| `description` | `Optional[str]`             | —              | Board description         |
| `index`       | `int`                       | `0`            | Sort order index          |
| `columns`     | `Optional[List[KanbanColumn]]` | `[]`        | Columns in the board      |
| `created_at`  | `str`                       | Current time   | Creation timestamp        |
| `updated_at`  | `str`                       | Current time   | Last update timestamp     |

---

### Message

Represents a single message within a chat conversation.

| Field                | Type              | Default        | Description                                              |
|----------------------|-------------------|----------------|----------------------------------------------------------|
| `doc_id`             | `Optional[str]`   | `None`         | Unique identifier                                        |
| `role`               | `str`             | `''`           | Message role (e.g., user, assistant)                     |
| `task_item`          | `str`             | `''`           | Associated task item                                     |
| `content`            | `str`             | `''`           | Message text content                                     |
| `think`              | `Optional[str]`   | `''`           | Internal reasoning content                               |
| `hide`               | `bool`            | `False`        | Whether the message is hidden                            |
| `is_answer`          | `bool`            | `False`        | Marks message as an answer                               |
| `improvement`        | `bool`            | `False`        | Marks message as an improvement                          |
| `created_at`         | `str`             | Current time   | Creation timestamp                                       |
| `updated_at`         | `str`             | Current time   | Last update timestamp                                    |
| `images`             | `List[str]`       | `[]`           | Attached image references                                |
| `files`              | `List[str]`       | `[]`           | Attached file references                                 |
| `meta_data`          | `Optional[dict]`  | `{}`           | Arbitrary metadata                                       |
| `profiles`           | `List[str]`       | `[]`           | Associated profiles                                      |
| `user`               | `Optional[str]`   | `None`         | User identifier                                          |
| `knowledge_topics`   | `List[str]`       | `[]`           | Topics for knowledge indexing                            |
| `done`               | `Optional[bool]`  | `True`         | Indicates if the user has finished writing               |
| `is_thinking`        | `Optional[bool]`  | `False`        | Indicates an active thinking state                       |
| `disable_knowledge`  | `Optional[bool]`  | `False`        | Disables knowledge indexing for this message             |
| `read_by`            | `List[str]`       | `[]`           | Users who have read this message                         |
| `error`              | `Optional[str]`   | `None`         | Error details if applicable                              |
| `linked_chat_ids`    | `Optional[List[str]]` | `[]`      | IDs of linked chats                                      |

---

### MessageTaskItem

An enumeration defining task item types for messages.

| Value     | Description                  |
|-----------|------------------------------|
| `SUMMARY` | Represents a summary task    |

---

### ChatHistoryEntry

Represents a historical snapshot entry within a chat.

| Field         | Type        | Default        | Description                                          |
|---------------|-------------|----------------|------------------------------------------------------|
| `timestamp`   | `str`       | Current time   | When this history entry was generated                |
| `summary`     | `str`       | `''`           | Summary of the history entry                         |
| `message_ids` | `List[str]` | `[]`           | Message IDs associated with this history entry       |

---

### ChatId

A lightweight reference model identifying a chat and its project.

| Field        | Type  | Description                                 |
|--------------|-------|---------------------------------------------|
| `chat_id`    | `str` | Chat identifier                             |
| `project_id` | `str` | Project to which this chat belongs          |

---

### Chat

The primary model representing a chat session, including its messages, metadata, and board placement.

| Field                    | Type                        | Default        | Description                                                                 |
|--------------------------|-----------------------------|----------------|-----------------------------------------------------------------------------|
| `id`                     | `Optional[str]`             | `None`         | Identifier                                                                  |
| `doc_id`                 | `Optional[str]`             | `None`         | Database document identifier                                                |
| `project_id`             | `Optional[str]`             | `None`         | Project this chat works in                                                  |
| `owner_project_id`       | `Optional[str]`             | `None`         | Project where the chat was created                                          |
| `parent_id`              | `Optional[str]`             | `None`         | Parent chat identifier                                                      |
| `linked_chat_ids`        | `Optional[List[str]]`       | `[]`           | Linked chat IDs                                                             |
| `parent_owner_project_id`| `Optional[str]`             | `None`         | Parent chat's owner project                                                 |
| `parent_project_id`      | `Optional[str]`             | `None`         | Parent chat's project ID                                                    |
| `child_index`            | `Optional[int]`             | `0`            | Sort index among sibling chats                                              |
| `message_id`             | `Optional[str]`             | `None`         | Parent message for threaded chats                                           |
| `status`                 | `str`                       | `''`           | Chat status                                                                 |
| `file_list`              | `List[str]`                 | `[]`           | Associated files                                                            |
| `check_lists`            | `Optional[List[dict]]`      | `[]`           | Check lists                                                                 |
| `profiles`               | `List[str]`                 | `[]`           | Associated profiles                                                         |
| `users`                  | `List[str]`                 | `[]`           | Participating users                                                         |
| `name`                   | `str`                       | `''`           | Chat name                                                                   |
| `pinned`                 | `Optional[bool]`            | `False`        | Whether the chat is pinned                                                  |
| `description`            | `str`                       | `''`           | Chat description                                                            |
| `messages`               | `List[Message]`             | `[]`           | List of messages in the chat                                                |
| `created_at`             | `str`                       | Current time   | Creation timestamp                                                          |
| `updated_at`             | `str`                       | Current time   | Last update timestamp                                                       |
| `mode`                   | `str`                       | `'chat'`       | Chat mode                                                                   |
| `kanban_id`              | `str`                       | `''`           | Associated Kanban board ID                                                  |
| `column_id`              | `str`                       | `''`           | Associated Kanban column ID                                                 |
| `board`                  | `str`                       | `''`           | Board name                                                                  |
| `column`                 | `str`                       | `''`           | Column name                                                                 |
| `columns`                | `List[KanbanColumn]`        | `[]`           | Embedded columns                                                            |
| `chat_index`             | `Optional[int]`             | `0`            | Chat sort index                                                             |
| `url`                    | `str`                       | `''`           | Associated URL                                                              |
| `branch`                 | `str`                       | `''`           | Associated Git branch                                                       |
| `file_path`              | `str`                       | `''`           | Associated file path                                                        |
| `llm_model`              | `Optional[str]`             | `''`           | LLM model used in this chat                                                 |
| `visibility`             | `Optional[str]`             | `''`           | Chat visibility setting                                                     |
| `remote_url`             | `Optional[str]`             | `''`           | Remote URL reference                                                        |
| `knowledge_topics`       | `List[str]`                 | `[]`           | Topics for knowledge indexing                                               |
| `chat_links`             | `List[ChatId]`              | `[]`           | Linked chat references                                                      |
| `pr_view`                | `Optional[dict]`            | `{}`           | Pull request view data                                                      |
| `history`                | `List[ChatHistoryEntry]`    | `[]`           | Historical entries of the chat                                              |
| `auto_initialize`        | `Optional[bool]`            | `False`        | When `True`, AI auto-fills board, column, and name on first response        |
| `ignore_parent_knowledge`| `Optional[bool]`            | `False`        | When `True`, disconnects from parent chat knowledge and uses own messages only |
| `ignore_parent_files`    | `Optional[bool]`            | `False`        | When `True`, excludes parent chat file list from the working context        |

---

## Database Layer

### Project Database Cache

A module-level dictionary `PROJECT_DATABASES` is maintained to cache active database connections per project path, preventing redundant re-initialization.

```python
PROJECT_DATABASES = {}
```

---

### CODXJuniorDB

The main database class that manages all read and write operations for a given project.

#### Initialization

```python
CODXJuniorDB(settings: CODXJuniorSettings)
```

Upon initialization, the class:
- Derives a sanitized `index_name` from the project's `codx_path` using slugification and regex cleanup.
- Constructs the `db_path` as `{codx_path}/{index_name}.db.json`.
- Checks `PROJECT_DATABASES` for an existing connection and calls `init_client()` if none is found.
- Sets up three tables: `kanban_table`, `column_table`, and `chat_table`, each with `cache_size=0`.

#### Methods

##### `init_client()`
Initializes the TinyDB client if not already connected, stores it in `PROJECT_DATABASES`, and logs the connection event.

##### `reset()`
Resets the database by:
1. Removing the database file from disk if it exists.
2. Clearing the cached client entry in `PROJECT_DATABASES`.
3. Calling `init_client()` to reinitialize a fresh database.

##### `save_kanban(kanban: Kanban) -> Kanban`
Persists a `Kanban` instance to the database.
- If `doc_id` is not set, generates a new UUID, sets timestamps, and inserts the record.
- If `doc_id` exists, updates the timestamp and replaces the existing record.
- Returns the saved `Kanban` by calling `get_kanban()`.

##### `get_kanban(kanban_id: str) -> Kanban`
Retrieves a single `Kanban` record matching the given `kanban_id`.

##### `get_all_kankan() -> List[Kanban]`
Returns all `Kanban` records stored in the database.

##### `get_kanban_chats(kanban_id: str, column_id: str) -> List[Chat]`
Returns all `Chat` records belonging to a specific Kanban board and column, filtered by `kanban_id` and `column_id`.

##### `get_chat(chat_id: str) -> Chat`
Retrieves a single `Chat` record matching the given `chat_id`.

##### `save_chat(chat: Chat)`
Persists a `Chat` instance to the database.
- If `doc_id` is not set, generates a new UUID, sets timestamps, and inserts the record.
- If `doc_id` exists, updates the timestamp and replaces the existing record.

---

## Storage Format

The database is stored as a formatted JSON file at:

```
{codx_path}/{index_name}.db.json
```

The file is written with `sort_keys=True`, an indent of `4`, and custom separators `(',', ': ')` for human-readable output.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/model/model.py
**Imported by:** codx/junior/agents/git_issues_agent.py, codx/junior/api/chat.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/chat/chat_export.py, codx/junior/chat/chat_knowledge.py, codx/junior/chat_manager.py, codx/junior/engine/chat_engine_actions.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/engine/wiki_engine.py, codx/junior/events/event_manager.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/mentions/mention_manager.py, codx/junior/sio/model.py, codx/junior/tools/code_writer.py, tests/db/test_db.py