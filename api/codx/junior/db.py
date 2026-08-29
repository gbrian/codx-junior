import os
import logging
import re
import uuid
from slugify import slugify

from codx.junior.settings import CODXJuniorSettings

from pydantic import BaseModel, Field
from typing import Optional, List, Union, Any, Dict

from datetime import datetime
from enum import Enum

from codx.junior.model.model import PRView

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Message role constants
# Use these instead of literal strings to keep roles consistent everywhere.
# ---------------------------------------------------------------------------
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


class KanbanColumn(BaseModel):
    """Represents a column in a Kanban board."""
    doc_id: Optional[str] = Field(default=None)
    title: str = Field(default=None)
    color: Optional[str] = Field(default=None)
    index: int = Field(default=0)
    chats: List[str] = Field(default=[])


class Kanban(BaseModel):
    """Represents a Kanban board with columns and chats."""
    doc_id: Optional[str] = Field(default=None)
    title: str = Field(default=None)
    description: Optional[str] = Field(default=None)
    index: int = Field(default=0)
    columns: Optional[List[KanbanColumn]] = Field(default=[])
    created_at: str = Field(default_factory=lambda: str(datetime.now()))
    updated_at: str = Field(default_factory=lambda: str(datetime.now()))


class MessageTaskItem(Enum):
    """Enum for message task item types."""
    SUMMARY = "summary"


class ToolEvent(BaseModel):
    """
    Represents a tool execution event.
    
    Used to track tool calls, their execution status, and results.
    Attached to the assistant response message that triggered the tool call.
    """
    tool: str = Field(description="Name of the tool that was executed")
    tool_call_id: str = Field(description="Unique identifier for this tool call from the provider")
    status: str = Field(description="Execution status: 'running', 'done', or 'error'")
    request: Optional[Dict[str, Any]] = Field(default=None, description="Parsed JSON arguments sent to the tool")
    response: Optional[str] = Field(default=None, description="Truncated tool result preview")
    duration_ms: Optional[float] = Field(default=None, description="Execution time in milliseconds")
    error: Optional[str] = Field(default=None, description="Error details when status is 'error'")


class LifeCycleEvent(BaseModel):
    """
    Represents a lifecycle event in the agent run.
    
    Used to track agent run status changes and execution metrics.
    Attached to the assistant response message produced by the run.
    """
    status: str = Field(description="Lifecycle status: 'running', 'done', or 'error'")
    run_id: str = Field(description="Unique identifier for the agent run")
    duration_ms: Optional[float] = Field(default=None, description="Execution time in milliseconds")
    error: Optional[str] = Field(default=None, description="Error details when status is 'error'")


class Message(BaseModel):
    """
    A single chat message.

    Tool and run-lifecycle events emitted while generating an assistant
    response are ASSOCIATED with that response message (they are NOT separate
    chat messages):

    - ``tool_events``:      one :class:`ToolEvent` per tool call executed
                            during this response, updated in place
                            (running → done/error).
    - ``lifecycle_events``: one :class:`LifeCycleEvent` per agent run
                            performed to produce this response.

    Both lists are streamed in real time together with the message and are
    persisted with the chat.
    """
    doc_id: Optional[str] = Field(default=None)
    role: str = Field(default='')
    task_item: str = Field(default='')
    content: str = Field(default='')
    think: Optional[str] = Field(default=None)
    hide: bool = Field(default=False)
    is_answer: bool = Field(default=False)
    improvement: bool = Field(default=False)
    created_at: str = Field(default_factory=lambda: str(datetime.now()))
    updated_at: str = Field(default_factory=lambda: str(datetime.now()))
    images: List[str] = Field(default=[])
    files: List[str] = Field(default=[])
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Free-form supplementary metadata (timings, model, analytics...)")
    tool_events: List[ToolEvent] = Field(default=[], description="Tool execution events associated with this response message")
    lifecycle_events: List[LifeCycleEvent] = Field(default=[], description="Agent run lifecycle events associated with this response message")
    profiles: List[str] = Field(default=[])
    user: Optional[str] = Field(default=None)
    knowledge_topics: List[str] = Field(description="This message will be indexed for knowledge and tagged with this topics", default=[])
    done: Optional[bool] = Field(default=True, description="Indicates if user is done writing")
    is_thinking: Optional[bool] = Field(default=False)
    disable_knowledge: Optional[bool] = Field(default=False)
    read_by: List[str] = Field(default=[])
    error: Optional[str] = Field(default=None)
    linked_chat_ids: Optional[List[str]] = Field(default=[], description="Linked chat ids")


class ChatHistoryEntry(BaseModel):
    """Represents a historical entry in a chat with timestamp, summary, and associated message IDs."""
    timestamp: str = Field(default_factory=lambda: str(datetime.now()), description="Timestamp when this history entry was generated")
    summary: str = Field(default='', description="Summary of this history entry")
    message_ids: List[str] = Field(default=[], description="List of message IDs associated with this history entry")


class ChatId(BaseModel):
    """Represents a reference to a chat in another project."""
    chat_id: str = Field(default=None, description="Chat id")
    project_id: str = Field(default=None, description="Defines the project which this chat belongs")


class Chat(BaseModel):
    """Represents a chat session with messages, metadata, and kanban board associations."""
    id: Optional[str] = Field(default=None)
    doc_id: Optional[str] = Field(default=None)
    project_id: Optional[str] = Field(default=None, description="Defines the project which this chat works, see owner_project_id for the project where the chat was created")
    owner_project_id: Optional[str] = Field(default=None, description="Project owner.")
    parent_id: Optional[str] = Field(default=None, description="Parent chat")
    linked_chat_ids: Optional[List[str]] = Field(default=[], description="Linked chat ids")
    parent_owner_project_id: Optional[str] = Field(default=None, description="Parent chat project owner.")
    parent_project_id: Optional[str] = Field(default=None, description="Parent chat project id")
    child_index: Optional[int] = Field(default=0, description="Child index. Used to sort chat content among other siblings")
    message_id: Optional[str] = Field(default=None, description="Parent message for threads")
    status: str = Field(default='')
    # tags: Optional[List[str]] = Field(default=[], description="Informative set of tags")
    file_list: List[str] = Field(default=[])
    check_lists: Optional[List[dict]] = Field(default=[])
    profiles: List[str] = Field(default=[])
    users: List[str] = Field(default=[])
    name: str = Field(default='')
    pinned: Optional[bool] = Field(default=False)
    description: str = Field(default='')
    messages: List[Message] = Field(default=[])
    created_at: str = Field(default_factory=lambda: str(datetime.now()))
    updated_at: str = Field(default_factory=lambda: str(datetime.now()))
    mode: str = Field(default='chat')
    kanban_id: str = Field(default='')
    column_id: str = Field(default='')
    board: str = Field(default='')
    column: str = Field(default='')
    columns: List[KanbanColumn] = Field(default=[])
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
    history: List[ChatHistoryEntry] = Field(default=[], description="Historical entries of this chat")
    auto_initialize: Optional[bool] = Field(
        default=False,
        description=(
            "Indicates this is a new chat that has not been initialized yet. "
            "When True, AI will auto-fill board, column and name fields on first response."
        )
    )
    ignore_parent_knowledge: Optional[bool] = Field(
        default=False,
        description="When True, disconnects from parent chat knowledge/context and only uses own messages"
    )
    ignore_parent_files: Optional[bool] = Field(
        default=False,
        description="When True, excludes parent chat file list from the working context"
    )


PROJECT_DATABASES = {}


class CODXJuniorDB:
    """
    Database manager for CODXJunior using TinyDB.
    
    Handles persistence of kanban boards, columns, and chats with table-level caching.
    """

    def __init__(self, settings: CODXJuniorSettings) -> None:
        """
        Initialize the database manager.
        
        Args:
            settings: CODXJuniorSettings instance with configuration
        """
        self.settings: CODXJuniorSettings = settings
        self.index_name: str = re.sub('[^a-zA-Z0-9\._]', '', slugify(self.settings.codx_path))
        self.db_path: str = f"{self.settings.codx_path}/{self.index_name}.db.json"
        self.client = PROJECT_DATABASES.get(self.settings.abs_project_path, None)
        if not self.client:
            self.init_client()
        self.kanban_table = self.client.table('kanban', cache_size=0)
        self.column_table = self.client.table('column', cache_size=0)
        self.chat_table = self.client.table('chat', cache_size=0)

    def init_client(self) -> None:
        """
        Initialize TinyDB client if not already initialized.
        
        Reuses existing client from PROJECT_DATABASES cache to avoid
        multiple connections to the same database file.
        """
        if self.client is None:
            logger.info("Connected to database: %s", self.settings.abs_project_path)
            self.client = TinyDB(self.db_path, sort_keys=True, indent=4, separators=(',', ': '))
            PROJECT_DATABASES[self.settings.abs_project_path] = self.client

    def reset(self) -> None:
        """
        Reset the database by removing the database file and reinitializing.
        
        Useful for clearing all data and starting fresh.
        """
        logger.info("Reseting DB %s", self.settings.abs_project_path)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            PROJECT_DATABASES[self.settings.abs_project_path] = None
            self.init_client()

    def save_kanban(self, kanban: Kanban) -> Kanban:
        """
        Save a kanban to the database.
        
        If kanban has no doc_id, creates a new one with UUID and timestamps.
        Otherwise updates the existing kanban record.
        
        Args:
            kanban: Kanban instance to save
            
        Returns:
            The saved Kanban instance with doc_id
        """
        if not kanban.doc_id:
            kanban.doc_id = str(uuid.uuid4())
            kanban.created_at = str(datetime.now())
            kanban.updated_at = str(datetime.now())
            self.kanban_table.insert(kanban.model_dump())
            logger.debug("Inserted new kanban: %s", kanban.doc_id)
        else:
            kanban.updated_at = str(datetime.now())
            self.kanban_table.update(kanban.model_dump(), where('doc_id') == kanban.doc_id)
            logger.debug("Updated kanban: %s", kanban.doc_id)
        return self.get_kanban(kanban.doc_id)

    def get_kanban(self, kanban_id: str) -> Kanban:
        """
        Retrieve a kanban by its ID.
        
        Args:
            kanban_id: The doc_id of the kanban to retrieve
            
        Returns:
            The Kanban instance
        """
        result = self.kanban_table.get(where('doc_id') == kanban_id)
        if result is None:
            logger.warning("Kanban not found: %s", kanban_id)
            return None
        return Kanban(**result)

    def get_all_kankan(self) -> List[Kanban]:
        """
        Retrieve all kanbans from the database.
        
        Returns:
            List of all Kanban instances
        """
        return [Kanban(**kanban) for kanban in self.kanban_table.all()]

    def get_kanban_chats(self, kanban_id: str, column_id: str) -> List[Chat]:
        """
        Load all chats from a specific column of a kanban.
        
        Args:
            kanban_id: The kanban ID to filter by
            column_id: The column ID to filter by
            
        Returns:
            List of Chat instances matching the filters
        """
        from tinydb import where
        results = self.chat_table.search(
            (where('kanban_id') == kanban_id) & (where('column_id') == column_id)
        )
        return [Chat(**chat) for chat in results]

    def get_chat(self, chat_id: str) -> Chat:
        """
        Retrieve a chat by its ID.
        
        Args:
            chat_id: The doc_id of the chat to retrieve
            
        Returns:
            The Chat instance
        """
        from tinydb import where
        result = self.chat_table.get(where('doc_id') == chat_id)
        if result is None:
            logger.warning("Chat not found: %s", chat_id)
            return None
        return Chat(**result)

    def save_chat(self, chat: Chat) -> None:
        """
        Save a chat to the database.
        
        If chat has no doc_id, creates a new one with UUID and timestamps.
        Otherwise updates the existing chat record.
        
        Args:
            chat: Chat instance to save
        """
        from tinydb import where
        if not chat.doc_id:
            chat.doc_id = str(uuid.uuid4())
            chat.created_at = str(datetime.now())
            chat.updated_at = str(datetime.now())
            self.chat_table.insert(chat.model_dump())
            logger.debug("Inserted new chat: %s", chat.doc_id)
        else:
            chat.updated_at = str(datetime.now())
            self.chat_table.update(chat.model_dump(), where('doc_id') == chat.doc_id)
            logger.debug("Updated chat: %s", chat.doc_id)


# Made with ❤️ by codx-junior