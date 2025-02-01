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
    doc_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
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
    doc_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    status: str = Field(default='')
    tags: List[str] = Field(default=[])
    file_list: List[str] = Field(default=[])
    profiles: List[str] = Field(default=[])
    name: str = Field(default='')
    messages: List[Message] = Field(default=[])
    created_at: str = Field(default=str(datetime.now()))
    updated_at: str = Field(default=str(datetime.now()))
    mode: str = Field(default='chat')
    board: str = Field(default='')
    column: str = Field(default='')
    chat_index: Optional[int] = Field(default=0)
    live_url: str = Field(default='')
    branch: str = Field(default='')
    file_path: str = Field(default='')

class KanbanColumn(BaseModel):
    doc_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    color: Optional[str]
    index: int = Field(default=0)
    chats: List[str]

class Kanban(BaseModel):
    doc_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str]
    index: int = Field(default=0)
    columns: List[KanbanColumn]
    created_at: str = Field(default=str(datetime.now()))
    updated_at: str = Field(default=str(datetime.now()))

PROJECT_DATABASES = {}

class CODXJuniorDB:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.index_name = re.sub('[^a-zA-Z0-9\._]', '', slugify(self.settings.codx_path))
        self.db_path = f"{self.settings.codx_path}/{self.index_name}.db.json"
        self.client = PROJECT_DATABASES.get(self.settings.project_path)
        if not self.client:
            self.client = TinyDB(self.db_path, sort_keys=True, indent=4, separators=(',', ': '))
            PROJECT_DATABASES[self.settings.project_path] = self.client
        self.kanban_table = self.client.table('kanban', cache_size=0)
        self.chats_table = self.client.table('chats', cache_size=0)

    # Kanban CRUD Operations

    def create_kanban(self, kanban: Kanban) -> Optional[Kanban]:
        logger.debug(f"Creating kanban: {kanban.title}")
        kanban.created_at = str(datetime.now())
        kanban.updated_at = str(datetime.now())
        self.kanban_table.insert(kanban.model_dump())
        return kanban

    def get_kanban(self, kanban_id: str) -> Optional[Kanban]:
        logger.debug(f"Getting kanban with ID: {kanban_id}")
        data = self.kanban_table.get(where('doc_id') == kanban_id)
        return Kanban(**data) if data else None

    def update_kanban(self, kanban: Kanban) -> Optional[Kanban]:
        logger.debug(f"Updating kanban with ID: {kanban.doc_id} with data: {kanban}")
        kanban.updated_at = str(datetime.now())
        self.kanban_table.update(kanban.model_dump(), where('doc_id') == kanban.doc_id)
        return self.get_kanban(kanban.doc_id)

    def delete_kanban(self, kanban: Kanban):
        logger.debug(f"Deleting kanban with ID: {kanban.doc_id}")
        self.kanban_table.remove(where('doc_id') == kanban.doc_id)

    # Chat CRUD Operations

    def create_chat(self, chat: Chat) -> Optional[Chat]:
        logger.debug(f"Creating chat: {chat.name}")
        chat.created_at = str(datetime.now())
        chat.updated_at = str(datetime.now())
        self.chats_table.insert(chat.model_dump())
        return self.get_chat(chat.doc_id)

    def get_chat(self, chat_id: str) -> Optional[Chat]:
        logger.debug(f"Getting chat with ID: {chat_id}")
        data = self.chats_table.get(where('doc_id') == chat_id)
        return Chat(**data) if data else None

    def update_chat(self, chat: Chat) -> Optional[Chat]:
        logger.debug(f"Updating chat with ID: {chat.doc_id} with data: {chat}")
        chat.updated_at = str(datetime.now())
        self.chats_table.update(chat.model_dump(), where('doc_id') == chat.doc_id)
        return self.get_chat(chat.doc_id)

    def delete_chat(self, chat: Chat):
        logger.debug(f"Deleting chat with ID: {chat.doc_id}")
        self.chats_table.remove(where('doc_id') == chat.doc_id)