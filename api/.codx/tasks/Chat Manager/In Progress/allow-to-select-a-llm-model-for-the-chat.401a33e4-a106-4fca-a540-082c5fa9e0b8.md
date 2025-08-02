# [[{"id": "401a33e4-a106-4fca-a540-082c5fa9e0b8", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/db.py", "/shared/codx-junior/api/codx/junior/chat/chat_engine.py"], "check_lists": [], "profiles": ["software_developer"], "users": ["admin"], "name": "Allow to select a llm model for the chat", "description": "In this conversation, we enhanced the `chat_manager.py` and `db.py` files of the codx-junior API. The primary change focused on allowing the definition of an `llm_model` for each chat. Throughout the updates, coding best practices were implemented, such as adding comprehensive logging, utilizing constants for default models, improving file handling accuracy, and updating database schema to accommodate new attributes. Additionally, error handling was made more specific, and the code was refactored for improved readability and maintainability.", "created_at": "2025-08-02 04:27:46.606650", "updated_at": "2025-08-02T09:47:19.200558", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Chat Manager", "column": "In Progress", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Chat Manager/In Progress/allow-to-select-a-llm-model-for-the-chat.401a33e4-a106-4fca-a540-082c5fa9e0b8.md", "llm_model": "mercury", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "bdde8dfe-7a4e-46b2-bfc0-68fdf0478af8", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-08-02 04:27:46.604534", "updated_at": "2025-08-02 04:27:46.604558", "images": [], "files": ["/shared/codx-junior/api/codx/junior/chat_manager.py", "/shared/codx-junior/api/codx/junior/db.py"], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true}]]
@file://db.py @file://chat_manager.py Allow to define an llm_model per chat, and use it in the ChaManagement
## [[{"doc_id": "aa1993cf-896f-4b47-8216-c08f31eb53d3", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-08-02 04:27:46.604534", "updated_at": "2025-08-02 04:27:46.604558", "images": [], "files": [], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true}]]
Generate diff file with the requiered changes
## [[{"doc_id": "fc3dcc8e-ea67-478c-a474-53543a67a774", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-08-02 04:27:46.604534", "updated_at": "2025-08-02 04:27:46.604558", "images": [], "files": [], "meta_data": {"time_taken": 59.24721693992615, "first_chunk_time_taken": 0.00020956993103027344, "model": "gpt-4o"}, "profiles": ["software_developer", "software_developer"], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false}]]
```python
/shared/codx-junior/api/codx/junior/chat_manager.py
import logging
import pathlib
import os
import json
import uuid
import shutil

from slugify import slugify
from collections import deque

from datetime import datetime, timezone, timedelta
from codx.junior.settings import CODXJuniorSettings

from codx.junior.db import Chat, Message
from codx.junior.utils.utils import write_file

from codx.junior.globals import (
    find_project_by_name
)

from codx.junior.profiling.profiler import profile_function
from typing import List, Optional

logger = logging.getLogger(__name__)

DEFAULT_BOARD = "kanban"
DEFAULT_COLUMN = "tasks"
DEFAULT_MODEL = "gpt-3.5-turbo"  # Default model for chat interactions

class ChatManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.chat_path = f"{settings.codx_path}/tasks"
        os.makedirs(self.chat_path, exist_ok=True)
        os.makedirs(f"{self.chat_path}/{DEFAULT_BOARD}/{DEFAULT_COLUMN}", exist_ok=True)

    def get_chat_file(self, chat: Chat) -> str:
        chat_file = f"{self.chat_path}/{chat.board}/{chat.column}/{slugify(chat.name)}.{chat.id}.md"
        return chat_file

    def chat_paths(self) -> List[str]:
        return [str(file_path) for file_path in pathlib.Path(self.chat_path).rglob("*.md")]

    def chat_board_column_name_from_path(self, file_path: str) -> (Optional[str], Optional[str], Optional[str]):
        chat_parts = file_path.replace(self.chat_path, "").split("/")[1:]
        if len(chat_parts) != 3:
            return None, None, None
        
        name = chat_parts[-1].replace(".md", "")
        column = chat_parts[-2]
        board = chat_parts[-3]
        return board, column, name

    @profile_function
    def list_chats(self) -> List[Chat]:
        file_paths = self.chat_paths()
        
        def list_chat_chat_info(file_path: str) -> Optional[Chat]:
            try:
                return self.load_chat_from_path(chat_file=file_path, chat_only=True)
            except (IOError, json.JSONDecodeError) as ex:
                logger.exception("Error loading chat %s", ex)
                return None
            
        return sorted(
            filter(None, [list_chat_chat_info(file_path) for file_path in file_paths]),
            key=lambda x: str(x.chat_index or x.updated_at),
            reverse=True
        )

    def save_chat(self, chat: Chat, chat_only: bool = False) -> Chat:
        chat.board = chat.board or DEFAULT_BOARD
        chat.column = chat.column or DEFAULT_COLUMN
        chat.id = chat.id or str(uuid.uuid4())
        chat.model = chat.model or DEFAULT_MODEL
        chat.updated_at = datetime.now().isoformat()
        
        current_chat = self.find_by_id(chat_id=chat.id)
        if chat_only and current_chat:
            chat.messages = current_chat.messages
        
        users = {msg.user for msg in chat.messages if msg.user}
        profiles = {p for msg in chat.messages for p in msg.profiles}
        chat.users = list(users)
        chat.profiles = list(profiles)

        chat_file = self.get_chat_file(chat)
        logger.info("Save chat %s at %s", chat.id, chat_file)
        write_file(chat_file, self.serialize_chat(chat))

        if current_chat and chat_file != current_chat.file_path:
            logger.info("Save chat, current_chat %s at %s", current_chat.id, current_chat.file_path)
            self.delete_chat(current_chat.file_path)

        return chat

    def delete_chat(self, file_path: Optional[str] = None, chat_id: Optional[str] = None) -> None:
        logger.info("Removing chat by file_path: %s - chat_id: %s", file_path, chat_id)
        
        if chat_id:
            chat = self.find_by_id(chat_id)
            file_path = chat.file_path if chat else None

        if file_path and os.path.isfile(file_path) and file_path.startswith(self.chat_path):
            logger.info("Removing chat at %s", file_path)
            os.remove(file_path)
        else:
            logger.error("Removing chat error %s", file_path)

    def load_chat(self, board: str, column: Optional[str] = None, chat_name: Optional[str] = None) -> Chat:
        chat = Chat(board=board, column=column, name=chat_name)
        chat_file = self.get_chat_file(chat)
        if not os.path.isfile(chat_file):
            chat.file_path = chat_file
            return chat
        return self.load_chat_from_path(chat_file=chat_file)

    @profile_function
    def load_chat_from_path(self, chat_file: str, chat_only: bool = False) -> Chat:
        board, column, name = self.chat_board_column_name_from_path(chat_file)
        
        # Adjust file path and properties if necessary
        if not board or not column:
            new_chat_file = f"{self.chat_path}/{DEFAULT_BOARD}/{DEFAULT_COLUMN}/{name}.md"
            if chat_file:
                logger.info("load_chat_from_path rename chat file %s -> %s", chat_file, new_chat_file)
                os.rename(chat_file, new_chat_file)
            chat_file = new_chat_file
            board = DEFAULT_BOARD
            column = DEFAULT_COLUMN

        chat = None
        with open(chat_file, 'r', encoding='utf-8') as f:
            logger.info("load_chat_from_path chat_only open file %s", chat_file) 
            content = f.read()
            chat = self.deserialize_chat(content=content, chat_only=chat_only)

        if not chat.created_at:
            stats = os.stat(chat_file)
            chat.created_at = str(datetime.fromtimestamp(stats.st_ctime, tz=timezone.utc))
            chat.updated_at = str(datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc))
        chat.board = board
        chat.column = column
        chat.file_path = chat_file
        return chat

    def serialize_chat(self, chat: Chat) -> str:
        chat_json = {**chat.__dict__}
        del chat_json["messages"]  
        header = f"# [[{json.dumps(chat_json)}]]"
        
        def serialize_message(message: Message) -> str:
            if not message.created_at:
                message.created_at = datetime.now().isoformat()
            message_json = {**message.__dict__}
            del message_json["content"]
            return "\n".join([
                f"## [[{json.dumps(message_json)}]]",
                message.content
            ])
        
        messages = [serialize_message(message) for message in chat.messages]
        chat_content = "\n".join([header] + messages)
        return chat_content

    def delete_kanban(self, kanban_title: str) -> None:
        shutil.rmtree(f"{self.chat_path}/{kanban_title}")

    @profile_function
    def deserialize_chat(self, content: str, chat_only: bool = False) -> Chat:
        logger.info("deserialize_chat content length: %d", len(content))
        lines = content.split("\n")
        chat_json = json.loads(lines[0][4:-2])
        chat = Chat(**chat_json)
        chat.messages = []
        
        if not chat_only:
            chat_message = None
            for line in lines[1:]:
                if line.startswith("## [[{") and line.endswith("}]]"):
                    chat_message = Message(**json.loads(line[5:-2]))
                    chat_message.content = ""
                    chat.messages.append(chat_message)
                    continue
                if chat_message:
                    chat_message.content = line if not chat_message.content else "\n".join([chat_message.content, line])
        return chat

    def chat_count(self) -> int:
        return len(self.chat_paths())

    def last_chats(self) -> List[Chat]:
        last_days = (datetime.now() - timedelta(days=2)).timestamp()
        chat_paths = [{
            "chat_path": chat_path,
            "updated_at": os.stat(chat_path).st_ctime
        } for chat_path in self.chat_paths()]
        chat_paths = [c for c in chat_paths if c["updated_at"] > last_days] 
        last_updated_chats = sorted(
            chat_paths,
            key=lambda x: x["updated_at"],
            reverse=True
        )[:3]
        return [self.load_chat_from_path(chat_file=c["chat_path"]) for c in last_updated_chats]

    def find_by_id(self, chat_id: str) -> Optional[Chat]:
        if chat_id:
            file_path = next((path for path in self.chat_paths() if chat_id in path), None)
            if file_path:
                return self.load_chat_from_path(chat_file=file_path)
        return None

    def load_kanban_from_file(self, kanban_file: str) -> dict:
        kanban = {
            "version": 0.1,
            "boards": {},
            "tags": {}
        }
        if os.path.isfile(kanban_file):
            with open(kanban_file, 'r', encoding='utf-8') as f:
                kanban = json.loads(f.read())
            version = kanban.get("version", None)
            if not version:
                kanban = {
                    "version": 0.1,
                    "boards": kanban,
                    "tags": {}
                }
        return kanban

    @profile_function
    def load_kanban(self) -> dict:
        kanban_file = f"{self.chat_path}/kanban.json"
        logger.info("load_kanban %s", kanban_file)
        all_chats = self.list_chats()
        kanban = self.load_kanban_from_file(kanban_file=kanban_file)
        
        all_board_dirs = [board for board in os.listdir(f"{self.chat_path}") \
                            if os.path.isdir(f"{self.chat_path}/{board}")]
        save_kanban = False
        boards = kanban["boards"]
        logger.info("Process boards %s", kanban_file)
        
        for board in {chat.board for chat in all_chats} | set(all_board_dirs):
            if not boards.get(board):
                boards[board] = {}
            if not boards[board].get("columns"):
                boards[board]["columns"] = []

            all_board_columns = [col for col in os.listdir(f"{self.chat_path}/{board}") \
                        if os.path.isdir(f"{self.chat_path}/{board}/{col}")]
            board_columns = boards[board]["columns"]
            for col in {chat.column for chat in all_chats if chat.board == board} | set(all_board_columns):
                if not [c for c in board_columns if c["title"] == col]:
                    board_columns.append({"title": col})
                    save_kanban = True

            for col in board_columns:
                if not col.get("id"):
                    col["id"] = str(uuid.uuid4())
                    save_kanban = True

        if save_kanban:
            self.save_kanban(kanban)
        return kanban

    def save_kanban(self, kanban: dict) -> None:
        kanban_file = f"{self.chat_path}/kanban.json"
        with open(kanban_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(kanban, ensure_ascii=False))

```

```python
/shared/codx-junior/api/codx/junior/db.py
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
from enum import Enum

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-3.5-turbo"  # Default model for chat interactions

class MessageTaskItem(Enum):
    SUMMARY = "summary"

class Message(BaseModel):
    doc_id: Optional[str] = Field(default=None)
    role: str = Field(default='')
    task_item: str = Field(default='')
    content: str = Field(default='')
    think: Optional[str] = Field(default='')
    hide: bool = Field(default=False)
    improvement: bool = Field(default=False)
    created_at: str = Field(default_factory=lambda: str(datetime.now()))
    updated_at: str = Field(default_factory=lambda: str(datetime.now()))
    images: List[str] = Field(default_factory=list)
    files: List[str] = Field(default_factory=list)
    meta_data: Optional[dict] = Field(default_factory=dict)
    profiles: List[str] = Field(default_factory=list)
    user: Optional[str] = Field(default=None)
    knowledge_topics: List[str] = Field(default_factory=list, description="This message will be indexed for knowledge and tagged with this topics")
    done: Optional[bool] = Field(default=True, description="Indicates if user is done writing")
    is_thinking: Optional[bool] = Field(default=False)
    disable_knowledge: Optional[bool] = Field(default=False)

class Chat(BaseModel):
    id: Optional[str] = Field(default=None)
    doc_id: Optional[str] = Field(default=None)
    project_id: Optional[str] = Field(default=None, description="Defines the project which this chat belongs")
    parent_id: Optional[str] = Field(default=None, description="Parent chat")
    status: str = Field(default='')
    tags: List[str] = Field(default_factory=list, description="Informative set of tags")
    file_list: List[str] = Field(default_factory=list)
    check_lists: Optional[List[dict]] = Field(default_factory=list)
    profiles: List[str] = Field(default_factory=list)
    users: List[str] = Field(default_factory=list)
    name: str = Field(default='')
    description: str = Field(default='')
    messages: List[Message] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: str(datetime.now()))
    updated_at: str = Field(default_factory=lambda: str(datetime.now()))
    mode: str = Field(default='chat')
    kanban_id: str = Field(default='')
    column_id: str = Field(default='')
    board: str = Field(default='')
    column: str = Field(default='')
    chat_index: Optional[int] = Field(default=0)
    url: str = Field(default='')
    branch: str = Field(default='')
    file_path: str = Field(default='')
    model: Optional[str] = Field(default_factory=lambda: DEFAULT_MODEL)
    visibility: Optional[str] = Field(default='')
    remote_url: Optional[str] = Field(default='')
    knowledge_topics: List[str] = Field(default_factory=list, description="This chat will be indexed for knowledge and tagged with this topics")
    
class KanbanColumn(BaseModel):
    doc_id: Optional[str] = Field(default=None)
    title: str = Field(default=None)
    color: Optional[str] = None
    index: int = Field(default=0)

class Kanban(BaseModel):
    doc_id: Optional[str] = Field(default=None)
    title: str = Field(default=None)
    description: Optional[str] = None
    index: int = Field(default=0)
    columns: Optional[List[KanbanColumn]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: str(datetime.now()))
    updated_at: str = Field(default_factory=lambda: str(datetime.now()))

PROJECT_DATABASES = {}

class CODXJuniorDB:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.index_name = re.sub('[^a-zA-Z0-9\._]', '', slugify(self.settings.codx_path))
        self.db_path = f"{self.settings.codx_path}/{self.index_name}.db.json"
        self.client = PROJECT_DATABASES.get(self.settings.project_path)
        if not self.client:
            self.init_client()
        self.kanban_table = self.client.table('kanban', cache_size=0)
        self.column_table = self.client.table('column', cache_size=0)
        self.chat_table = self.client.table('chat', cache_size=0)

    def init_client(self) -> None:
        if self.client is None:
            logger.info("Connected to database: %s", self.settings.project_path)
            self.client = TinyDB(self.db_path, sort_keys=True, indent=4, separators=(',', ': '))
            PROJECT_DATABASES[self.settings.project_path] = self.client
        
    def reset(self) -> None:
        logger.info("Reseting DB %s", self.settings.project_path)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            PROJECT_DATABASES[self.settings.project_path] = None
            self.init_client()

    def save_kanban(self, kanban: Kanban) -> Kanban:
        """Save a kanban to the database, if kanban has not doc_id, create a new one"""
        if not kanban.doc_id:
            kanban.doc_id = str(uuid.uuid4())
            kanban.created_at = str(datetime.now())
        kanban.updated_at = str(datetime.now())
        self.kanban_table.upsert(kanban.model_dump(), where('doc_id') == kanban.doc_id)
        return self.get_kanban(kanban.doc_id)

    def get_kanban(self, kanban_id: str) -> Kanban:
        return Kanban(**self.kanban_table.get(where('doc_id') == kanban_id))

    def get_all_kankan(self) -> List[Kanban]:
        return [Kanban(**kanban) for kanban in self.kanban_table.all()]

    def get_kanban_chats(self, kanban_id: str, column_id: str) -> List[Chat]:
        """Load all chats from a column of a kanban"""
        return [Chat(**chat) for chat in self.chat_table.search((where('kanban_id') == kanban_id) & (where('column_id') == column_id))]
    
    def get_chat(self, chat_id: str) -> Chat:
        return Chat(**self.chat_table.get(where('doc_id') == chat_id))

    def save_chat(self, chat: Chat) -> None:
        """Save a chat to the database, if chat has not doc_id, create a new one"""
        if not chat.doc_id:
            chat.doc_id = str(uuid.uuid4())
            chat.created_at = str(datetime.now())
        chat.updated_at = str(datetime.now())
        self.chat_table.upsert(chat.model_dump(), where('doc_id') == chat.doc_id)

```