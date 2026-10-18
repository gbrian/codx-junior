import os
import logging
import uuid
from slugify import slugify

from codx.junior.settings import CODXJuniorSettings

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any, Dict

from datetime import datetime
from enum import Enum

from codx.junior.model.agent import CostInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
MAX_IMAGE_SIZE_MB = 50
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

# Attachments are not image-only: the chat composer records voice notes and
# stores them as audio attachments (audio/webm, audio/ogg, audio/mp4 ...).
# The generic constants keep the same limit that was previously image-only.
MAX_ATTACHMENT_SIZE_MB = MAX_IMAGE_SIZE_MB
MAX_ATTACHMENT_SIZE_BYTES = MAX_IMAGE_SIZE_BYTES

ALLOWED_IMAGE_TYPES = [
    'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/svg+xml'
]
ALLOWED_AUDIO_TYPES = [
    'audio/webm', 'audio/ogg', 'audio/mp4', 'audio/mpeg', 'audio/wav',
    'audio/x-wav', 'audio/x-m4a', 'audio/m4a', 'audio/aac', 'audio/flac'
]
ALLOWED_ATTACHMENT_TYPES = ALLOWED_IMAGE_TYPES + ALLOWED_AUDIO_TYPES


class ChatAttachment(BaseModel):
    """Represents a media file (image or audio note) attached to a chat or message,
    with its metadata and base64 encoded data."""
    file_name: str = Field(description="Original file name of the attachment")
    file_type: str = Field(description="MIME type (e.g., 'image/png', 'audio/webm')")
    file_size: int = Field(description="File size in bytes")
    base64_data: str = Field(description="Base64 encoded file data")
    uploaded_at: str = Field(default_factory=lambda: str(datetime.now()), description="Timestamp when the attachment was uploaded")
    
    @validator('file_size')
    def validate_file_size(cls, v):
        if v > MAX_ATTACHMENT_SIZE_BYTES:
            raise ValueError(f"Attachment size exceeds maximum allowed size of {MAX_ATTACHMENT_SIZE_MB}MB")
        return v
    
    @validator('file_type')
    def validate_file_type(cls, v):
        # `MediaRecorder` reports the recording type together with its codec list
        # ("audio/webm;codecs=opus"). Attachments store the container type only,
        # so the parameters are stripped before validating (and persisting).
        media_type = (v or '').split(';')[0].strip().lower()
        if media_type not in ALLOWED_ATTACHMENT_TYPES:
            raise ValueError(
                f"Attachment type '{v}' not allowed. Allowed types: {', '.join(ALLOWED_ATTACHMENT_TYPES)}"
            )
        return media_type


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

    Tool output handling
    --------------------
    ``output`` carries the tool's user-facing content (``ToolResponse.user_response``).
    It is deliberately kept OUT of ``Message.content`` so the chat is not polluted:
    clients read it from this property and render it collapsed or hidden at their
    discretion.
    """
    tool: str = Field(description="Name of the tool that was executed")
    tool_call_id: str = Field(description="Unique identifier for this tool call from the provider")
    status: str = Field(description="Execution status: 'running', 'done', or 'error'")
    request: Optional[Dict[str, Any]] = Field(default=None, description="Parsed JSON arguments sent to the tool")
    response: Optional[str] = Field(default=None, description="Truncated tool result preview")
    output: Optional[str] = Field(
        default=None,
        description=(
            "User-facing output produced by the tool (ToolResponse.user_response). "
            "Kept OUT of Message.content so clients can render tool output collapsed "
            "or hidden. Only dual-response tools populate this field."
        )
    )
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
                            (running → done/error). Each event carries the
                            tool's user-facing ``output`` (see below) so clients
                            can render tool output collapsed/hidden without it
                            polluting ``content``.
    - ``lifecycle_events``: one :class:`LifeCycleEvent` per agent run
                            performed to produce this response.

    Both lists are streamed in real time together with the message and are
    persisted with the chat.

    **Tool output (`tool_events[].output`)**

    Tool output (``ToolResponse.user_response``) is NOT merged into
    ``content``. It is attached to the response message as the
    :attr:`ToolEvent.output` property (streamed live with every message event
    and persisted with the chat) so the client decides whether to show it
    inline, collapsed, or hidden.

    **Cost Tracking (`cost` / `cost_info` fields)**

    ``cost`` records the cost, in cxjcoins, of the AI iteration that produced
    this message. SmolAgent registers the FULL processing cost of the response
    here (every LLM round plus every tool cost reported via
    ``ToolResponse.cost``). ``ChatManager`` accumulates this value into
    :attr:`Chat.cost` when the message is added, so the chat budget
    (``Chat.estimation_cost``) is preserved even if the message is later
    deleted.

    ``cost_info`` carries the detailed breakdown (tokens, input/output/tool
    costs, chat budget state) produced by SmolAgent's typed
    :class:`AgentRunResult`. It is streamed to clients together with the
    message via ``message-event``.

    **Message Read Tracking (`read_by` field)**
    
    The `read_by` field tracks which users have viewed a message in collaborative chats.
    
    **Usage Context:**
    - Primarily for assistant messages (role='assistant') in multi-user chat environments
    - Indicates message delivery and read status to other users
    - User's own messages are excluded from tracking (message.user !== current_username)
    
    **Automatic Tracking:**
    - When a user scrolls past and views an assistant message from another user,
      their username is automatically added to the `read_by` list
    - Tracked via ChatEntry.vue which monitors viewport visibility
    - After 500ms idle time, calls `/api/chats/markMessageAsSeen` endpoint
    - Endpoint signature: POST /api/chats/markMessageAsSeen
      - Params: (chat_id, message_id, username)
      - Effect: Adds username to message.read_by list if not already present
    
    **Display Indicators:**
    - ChatMiniMap: Double-check marks
      - Gray checks (✓) = message unread by current user
      - Green checks (✓✓) = message read by current user
      - Only shown for assistant messages from other users
    - ChatSidebarNodeCompact/Extended: Unread badge
      - Shows count of unread assistant messages from others
      - Triggers awareness of new messages in the chat
    - Message Headers: Optional read status indicators
    
    **Initialization & Lifecycle:**
    - Always initialized as empty list [] when message is created
    - Populated over time as different users view the message
    - Never decreases (read state is permanent per user)
    - Cleared only if message is deleted
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
    attachments: List[ChatAttachment] = Field(default=[], description="Attachments for this message")
    files: List[str] = Field(default=[])
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Free-form supplementary metadata (timings, model, analytics...)")
    tool_events: List[ToolEvent] = Field(default=[], description="Tool execution events associated with this response message")
    lifecycle_events: List[LifeCycleEvent] = Field(default=[], description="Agent run lifecycle events associated with this response message")
    cost: float = Field(
        default=0.0,
        description=(
            "Cost in cxjcoins of the AI iteration that produced this message. "
            "SmolAgent registers the FULL processing cost here (all LLM rounds "
            "plus any tool cost) and ChatManager accumulates it into Chat.cost "
            "when the message is added."
        )
    )
    cost_info: Optional[CostInfo] = Field(
        default=None,
        description=(
            "Detailed cost/usage breakdown of the AI run that produced this "
            "message (tokens, input/output/tool costs, chat budget state). "
            "Streamed to clients via message-event. The numeric `cost` field is "
            "what ChatManager accumulates into Chat.cost."
        )
    )
    profiles: List[str] = Field(default=[])
    user: Optional[str] = Field(default=None)
    knowledge_topics: List[str] = Field(description="This message will be indexed for knowledge and tagged with this topics", default=[])
    done: Optional[bool] = Field(default=True, description="Indicates if user is done writing")
    is_thinking: Optional[bool] = Field(default=False)
    disable_knowledge: Optional[bool] = Field(default=False)
    read_by: List[str] = Field(default=[], description="List of usernames who have viewed this assistant message; automatically populated when users view the message")
    error: Optional[str] = Field(default=None)
    linked_chat_ids: Optional[List[str]] = Field(default=[], description="Linked chat ids")


class ChatHistoryEntry(BaseModel):
    """Represents a historical entry in a chat with timestamp, summary, and associated message IDs."""
    timestamp: str = Field(default_factory=lambda: str(datetime.now()), description="Timestamp when this history entry was generated")
    summary: str = Field(default='', description="Summary of this history entry")
    message_ids: List[str] = Field(default=[], description="List of message IDs associated with this history entry")


class ChatStatusEvent(BaseModel):
    """
    Append-only record of a single chat status transition.

    Registered by :class:`codx.junior.chat_manager.ChatManager` whenever
    ``Chat.status`` changes, so task-performance metrics (cycle time,
    throughput, reliability...) can be derived from a complete transition
    history instead of the single mutable ``Chat.status`` value.
    """
    doc_id: Optional[str] = Field(default=None, description="Unique identifier of this transition record")
    from_status: Optional[str] = Field(default=None, description="Previous status, None on the first record")
    to_status: str = Field(default='', description="New status")
    user: Optional[str] = Field(default=None, description="User that triggered the change, if any")
    at: str = Field(default_factory=lambda: str(datetime.now()), description="Timestamp of the transition")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Free-form supplementary metadata (source, reason...)")


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
    status_history: List[ChatStatusEvent] = Field(
        default=[],
        description=(
            "Append-only log of status transitions (from_status -> to_status) "
            "used to build performance metrics like cycle time and throughput. "
            "Maintained by ChatManager.save_chat whenever status changes."
        )
    )
    tags: Optional[List[str]] = Field(default=[], description="Informative set of tags")
    file_list: List[str] = Field(default=[])
    check_lists: Optional[List[dict]] = Field(default=[])
    profiles: List[str] = Field(default=[])
    users: List[str] = Field(default=[])
    name: str = Field(default='')
    pinned: Optional[bool] = Field(default=False)
    is_template: Optional[bool] = Field(default=False, description="Chat will be used as temlate")
    description: str = Field(default='')
    messages: List[Message] = Field(default=[])
    created_at: str = Field(default_factory=lambda: str(datetime.now()))
    updated_at: str = Field(default_factory=lambda: str(datetime.now()))
    mode: str = Field(default='chat')
    kanban_id: str = Field(default='')
    column_id: str = Field(default='')
    board: str = Field(default='')
    column: str = Field(default='')
    sprints: List[str] = Field(
        default=[],
        description=(
            "Identifiers of the sprint boards this chat belongs to. "
            "A chat/task can be part of multiple sprints; membership is used to "
            "filter which cards are shown on a 'sprint' type board. Persisted "
            "through the existing /api/chats/metadata endpoint."
        )
    )

    # ── Planning / task fields ─────────────────────────────────────────────
    # Persisted through the existing /api/chats/metadata endpoint
    # (ChatManager.update_chat_metadata uses setattr for known attributes).
    priority: Optional[str] = Field(
        default=None,
        description="Task priority: 'high' | 'medium' | 'low'"
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Task due date in ISO format (YYYY-MM-DD)"
    )
    progress: int = Field(
        default=0,
        description="Task completion percentage (0-100)"
    )
    assignees: List[str] = Field(
        default=[],
        description="Usernames assigned to this task (distinct from participants in 'users')"
    )
    sort_index: Optional[int] = Field(
        default=None,
        description="Manual ordering index within a board column"
    )

    columns: List[KanbanColumn] = Field(default=[])
    chat_index: Optional[int] = Field(default=0)
    url: str = Field(default='')
    branch: str = Field(default='')
    file_path: str = Field(default='')
    llm_model: Optional[str] = Field(default='')

    # ── Cost budget ────────────────────────────────────────────────────────
    estimation_cost: Optional[float] = Field(
        default=None,
        description=(
            "Estimated maximum cost (in cxjcoins) allowed for this chat. "
            "When the accumulated cost reaches this value, SmolAgent stops "
            "executing to keep the chat within budget. None (or <= 0) means "
            "no cost limit."
        )
    )
    cost: float = Field(
        default=0.0,
        description=(
            "Accumulated cost (in cxjcoins) spent on this chat. Updated by "
            "ChatManager whenever a message with a cost is added or updated. "
            "This value is MONOTONIC: deleting a message never reduces it, so "
            "the budget reflects everything the chat has actually spent."
        )
    )

    visibility: Optional[str] = Field(default='')
    remote_url: Optional[str] = Field(default='')
    attachments: List[ChatAttachment] = Field(default=[], description="Attachments for this chat")
    knowledge_topics: List[str] = Field(description="This chat will be indexed for knowledge and tagged with this topics", default=[])
    chat_links: List[ChatId] = Field(default=[])
    pr_view: Optional[dict] = Field(default={}, description="Pull request view")
    history: List[ChatHistoryEntry] = Field(default=[], description="Historical entries of this chat")
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session/conversation identifier used to link chat with AI request/response logs"
    )
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


# Made with ❤️ by codx-junior