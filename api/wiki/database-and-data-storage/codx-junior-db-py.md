The `codx.junior.db` module provides database functionalities for the CODX Junior project, primarily focused on managing chat and kanban data.

## Database Models

The module defines several Pydantic models to represent the data structures stored in the database:

*   **`MessageTaskItem`**: An Enum for message task item types.
*   **`Message`**: Represents a single message within a chat. It includes fields for message content, role, timestamps, associated files, and metadata.
*   **`ChatId`**: A simple model to store a chat's ID and its associated project ID, used for linking chats.
*   **`Chat`**: Represents a chat conversation. It includes fields for chat metadata, messages, participants, status, and links to other chats or projects. It also supports integration with kanban boards and pull request views.
*   **`KanbanColumn`**: Represents a column within a kanban board, with fields for its title, color, and order.
*   **`Kanban`**: Represents a kanban board, including its title, description, and a list of `KanbanColumn` objects.

## `CODXJuniorDB` Class

The `CODXJuniorDB` class is the main interface for interacting with the project's database.

### Initialization

The database client is initialized using `TinyDB` and is stored in a global `PROJECT_DATABASES` dictionary to avoid redundant connections for the same project path. The `db_path` is derived from the project's settings.

### Database Operations

*   **`init_client()`**: Initializes the TinyDB client if it's not already connected for the current project.
*   **`reset()`**: Resets the database by removing the existing database file and re-initializing the client.
*   **`save_kanban(kanban: Kanban)`**: Saves a `Kanban` object to the database. If the `kanban` object doesn't have a `doc_id`, a new one is created. Otherwise, the existing record is updated.
*   **`get_kanban(kanban_id: str)`**: Retrieves a `Kanban` object from the database using its `doc_id`.
*   **`get_all_kankan()`**: Retrieves all `Kanban` objects from the database.
*   **`get_kanban_chats(kanban_id: str, column_id: str)`**: Retrieves all `Chat` objects associated with a specific kanban column.
*   **`get_chat(chat_id: str)`**: Retrieves a `Chat` object from the database using its `doc_id`.
*   **`save_chat(chat: Chat)`**: Saves a `Chat` object to the database. Similar to `save_kanban`, it creates a new record if `doc_id` is absent, or updates an existing one.

```python /codx/junior/db.py
import os
import logging
import re
import uuid
from slugify import slugify

from codx.junior.settings import CODXJuniorSettings

from pydantic import BaseModel, Field
from typing import Optional, List, Union

from datetime import datetime
from enum import Enum

from codx.junior.model.model import PRView

logger = logging.getLogger(__name__)

class MessageTaskItem(Enum):
    SUMMARY = "summary"

class Message(BaseModel):
    doc_id: Optional[str] = Field(default=None)
    role: str = Field(default='')
    task_item: str = Field(default='')
    content: str = Field(default='')
    think: Optional[str] = Field(default='')
    hide: bool = Field(default=False)
    is_answer: bool = Field(default=False)
    improvement: bool = Field(default=False)
    created_at: str = Field(default=str(datetime.now()))
    updated_at: str = Field(default=str(datetime.now()))
    images: List[str] = Field(default=[])
    files: List[str] = Field(default=[])
    meta_data: Optional[dict] = Field(default={})
    profiles: List[str] = Field(default=[])
    user: Optional[str] = Field(default=None)
    knowledge_topics: List[str] = Field(description="This message will be indexed for knowledge and tagged with this topics", default=[])
    done: Optional[bool] = Field(default=True, description="Indicates if user is done writing")
    is_thinking: Optional[bool] = Field(default=False)
    disable_knowledge: Optional[bool] = Field(default=False)
    read_by: List[str] = Field(default=[])
    error: Optional[str] = Field(default=None)

class ChatId(BaseModel):
    chat_id: str = Field(default=None, description="Chat id")
    project_id: str = Field(default=None, description="Defines the project which this chat belongs")
    
class Chat(BaseModel):
    id: Optional[str] = Field(default=None)
    doc_id: Optional[str] = Field(default=None)
    project_id: Optional[str] = Field(default=None, description="Defines the project which this chat belongs")
    owner_project_id: Optional[str] = Field(default=None, description="Project owner.")
    parent_id: Optional[str] = Field(default=None, description="Parent chat")
    parent_owner_project_id: Optional[str] = Field(default=None, description="Parent chat project owner.")
    parent_project_id: Optional[str] = Field(default=None, description="Parent chat project id")
    child_index: Optional[int] = Field(default=0, description="Child index. Used to sort chat content among other siblings")
    message_id: Optional[str] = Field(default=None, description="Parent message for threads")
    status: str = Field(default='')
    # tags: Optional[any] = Field(default=None, description="Informative set of tags")
    file_list: List[str] = Field(default=[])
    check_lists: Optional[List[dict]] = Field(default=[])
    profiles: List[str] = Field(default=[])
    users: List[str] = Field(default=[])
    name: str = Field(default='')
    pinned: Optional[bool] = Field(default=False)
    description: str = Field(default='')
    messages: List[Message] = Field(default=[])
    created_at: str = Field(default=str(datetime.now()))
    updated_at: str = Field(default=str(datetime.now()))
    mode: str = Field(default='chat')
    kanban_id: str = Field(default='')
    column_id: str = Field(default='')
    board: str = Field(default='')
    column: str = Field(default='')
    chat_index: Optional[int] = Field(default=0)
    url: str = Field(default='')
    branch: str = Field(default='')
    file_path: str = Field(default='')
    llm_model: Optional[str] = Field(default='')
    visibility: Optional[str] = Field(default='')
    remote_url: Optional[str] = Field(default='')
    knowledge_topics: List[str] = Field(description="This chat will be indexed for knowledge and tagged with this topics", default=[])
    chat_links: List[ChatId] = Field(default=[])
    pr_view: Optional[dict] = Field(default={}, description="Pull request view")
    

class KanbanColumn(BaseModel):
    doc_id: Optional[str] = Field(default=None)
    title: str = Field(default=None)
    color: Optional[str]
    index: int = Field(default=0)

class Kanban(BaseModel):
    doc_id: Optional[str] = Field(default=None)
    title: str = Field(default=None)
    description: Optional[str]
    index: int = Field(default=0)
    columns: Optional[List[KanbanColumn]] = Field(default=[])
    created_at: str = Field(default=str(datetime.now()))
    updated_at: str = Field(default=str(datetime.now()))

PROJECT_DATABASES = {}

class CODXJuniorDB:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.index_name = re.sub('[^a-zA-Z0-9\._]', '', slugify(self.settings.codx_path))
        self.db_path = f"{self.settings.codx_path}/{self.index_name}.db.json"
        self.client = PROJECT_DATABASES.get(self.settings.project_path, None)
        if not self.client:
            self.init_client()
        self.kanban_table = self.client.table('kanban', cache_size=0)
        self.column_table = self.client.table('column', cache_size=0)
        self.chat_table = self.client.table('chat', cache_size=0)

    def init_client(self):
        if self.client is None:
            logger.info(f"Connected to database: {self.settings.project_path}")
            self.client = TinyDB(self.db_path, sort_keys=True, indent=4, separators=(',', ': '))
            PROJECT_DATABASES[self.settings.project_path] = self.client
        
    def reset(self):
        logger.info(f"Reseting DB {self.settings.project_path}")
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            PROJECT_DATABASES[self.settings.project_path] = None
            self.init_client()

    def save_kanban(self, kanban: Kanban):
        """Save a kanban to the database, if kanban has not doc_id, create a new one"""
        if not kanban.doc_id:
            kanban.doc_id = str(uuid.uuid4())
            kanban.created_at = str(datetime.now())
            kanban.updated_at = str(datetime.now())
            self.kanban_table.insert(kanban.model_dump())            
        else:
            kanban.updated_at = str(datetime.now())
            self.kanban_table.update(kanban.model_dump(), where('doc_id') == kanban.doc_id)
        return self.get_kanban(kanban.doc_id)

    def get_kanban(self, kanban_id: str):
        return Kanban(**self.kanban_table.get(where('doc_id') == kanban_id))

    def get_all_kankan(self):
        return [Kanban(**kanban) for kanban in self.kanban_table.all()]

    def get_kanban_chats(self, kanban_id: str, column_id: str):
        """Load all chats from a column of a kanban"""
        return [Chat(**chat) for chat in self.chat_table.search(where('kanban_id') == kanban_id 
                                    and where('column_id') == column_id)]
    def get_chat(self, chat_id: str):
        return Chat(**self.chat_table.get(where('doc_id') == chat_id))

    def save_chat(self, chat: Chat):
        """Save a chat to the database, if chat has not doc_id, create a new one"""
        if not chat.doc_id:
            chat.doc_id = str(uuid.uuid4())
            chat.created_at = str(datetime.now())
            chat.updated_at = str(datetime.now())
            self.chat_table.insert(chat.model_dump())
        else:
            chat.updated_at = str(datetime.now())
            self.chat_table.update(chat.model_dump(), where('doc_id') == chat.doc_id)

            