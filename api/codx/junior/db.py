import os
import logging
import re
import uuid
from slugify import slugify

from codx.junior.settings import CODXJuniorSettings
from tinydb import TinyDB, Query, where

from pydantic import BaseModel, Field
from typing import Optional, List

from datetime import datetime


logger = logging.getLogger(__name__)

class Message(BaseModel):
    doc_id: Optional[str] = Field(default=None)
    role: str = Field(default='')
    task_item: str = Field(default='')
    content: str = Field(default='')
    hide: bool = Field(default=False)
    improvement: bool = Field(default=False)
    created_at: str = Field(default=str(datetime.now()))
    updated_at: str = Field(default=str(datetime.now()))
    images: List[str] = Field(default=[])
    files: List[str] = Field(default=[])

class Chat(BaseModel):
    id: Optional[str] = Field(default=None)
    doc_id: Optional[str] = Field(default=None)
    project_id: Optional[str] = Field(default=None, description="Defines the project which this chat belongs")
    parent_id: Optional[str] = Field(default=None, description="Parent chat")
    status: str = Field(default='')
    tags: List[str] = Field(default=[], description="Informative set of tags")
    file_list: List[str] = Field(default=[])
    profiles: List[str] = Field(default=[])
    name: str = Field(default='')
    messages: List[Message] = Field(default=[])
    created_at: str = Field(default=str(datetime.now()))
    updated_at: str = Field(default=str(datetime.now()))
    mode: str = Field(default='chat')
    kanban_id: str = Field(default='')
    column_id: str = Field(default='')
    board: str = Field(default='')
    column: str = Field(default='')
    chat_index: Optional[int] = Field(default=0)
    live_url: str = Field(default='')
    branch: str = Field(default='')
    file_path: str = Field(default='')

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
