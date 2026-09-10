import os
import logging
import re
import uuid
from slugify import slugify

from codx.junior.settings import CODXJuniorSettings

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union, Any, Dict

from datetime import datetime
from enum import Enum

from codx.junior.model.model import PRView

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
MAX_IMAGE_SIZE_MB = 50
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024


class ChatAttachment(BaseModel):
    """Represents an image stored in chat or message with file metadata and base64 data."""
    file_name: str = Field(description="Original file name of the image")
    file_type: str = Field(description="MIME type (e.g., 'image/png', 'image/jpeg')")
    file_size: int = Field(description="File size in bytes")
    base64_data: str = Field(description="Base64 encoded image data")
    uploaded_at: str = Field(default_factory=lambda: str(datetime.now()), description="Timestamp when image was uploaded")
    
    @validator('file_size')
    def validate_file_size(cls, v):
        if v > MAX_IMAGE_SIZE_BYTES:
            raise ValueError(f"Image size exceeds maximum allowed size of {MAX_IMAGE_SIZE_MB}MB")
        return v
    
    @validator('file_type')
    def validate_file_type(cls, v):
        allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/svg+xml']
        if v not in allowed_types:
            raise ValueError(f"Image type '{v}' not allowed. Allowed types: {', '.join(allowed_types)}")
        return v


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


class RecipeStep(BaseModel):
    """
    A single step within a recipe.
    
    A recipe is composed of ordered RecipeSteps. Each step maps to a Chat
    that contains the actual interaction, tool calls, and results.
    """
    step_index: int = Field(
        ...,
        description="Order of execution (0-based)"
    )
    chat_id: Optional[str] = Field(
        default=None,
        description="Reference to the Chat containing step content, messages, and execution state"
    )
    name: str = Field(
        ...,
        description="Human-readable step name"
    )
    description: str = Field(
        default="",
        description="What this step does and its purpose"
    )
    step_type: str = Field(
        default="action",
        description="'instruction' (read-only guidance), 'exercise' (user does), 'validation' (check), 'action' (automated)"
    )
    is_required: bool = Field(
        default=True,
        description="Must be completed to advance. False = optional step"
    )
    success_criteria: Optional[str] = Field(
        default=None,
        description="Natural language or structured criteria to mark step as 'completed'"
    )
    estimated_duration_seconds: Optional[int] = Field(
        default=None,
        description="Hint for user: ~how long should this step take?"
    )
    meta_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Step-specific config, parameters, or context"
    )


class RecipeMetrics(BaseModel):
    """Aggregated metrics for a recipe instance execution."""
    total_steps: int = Field(default=0)
    completed_steps: int = Field(default=0)
    skipped_steps: int = Field(default=0)
    failed_steps: int = Field(default=0)
    total_duration_seconds: Optional[int] = Field(default=None)
    created_at: str = Field(default_factory=lambda: str(datetime.now()))
    updated_at: str = Field(default_factory=lambda: str(datetime.now()))
    last_completed_step_index: Optional[int] = Field(default=None)
    completion_percent: int = Field(default=0)


class Recipe(BaseModel):
    """
    A reusable recipe: an ordered set of steps to accomplish a goal.
    
    A recipe is a template or instance depending on `is_template`:
    
    - **Template** (`is_template=True`): Master copy, immutable, discovered and cloned
    - **Instance** (`is_template=False`): Live user/automation run, tracks progress
    
    Recipe types:
    - 'tutorial': Interactive step-by-step learning
    - 'automation': Unattended background job (e.g., "Keep docs updated")
    - 'workflow': Multi-step manual procedure (e.g., "Code review checklist")
    - 'playbook': Structured troubleshooting or investigation
    """
    id: Optional[str] = Field(default=None, description="Unique recipe ID")
    name: str = Field(..., description="Recipe name")
    description: str = Field(default="", description="What this recipe accomplishes")
    goal: Optional[str] = Field(
        default=None,
        description="High-level outcome or success target"
    )
    recipe_type: str = Field(
        default="workflow",
        description="'tutorial', 'automation', 'workflow', 'playbook', custom..."
    )
    is_template: bool = Field(
        default=False,
        description="True = master template, False = live instance"
    )
    template_id: Optional[str] = Field(
        default=None,
        description="If instance, points to template recipe_id"
    )
    version: str = Field(
        default="1.0.0",
        description="Semantic versioning for templates"
    )
    steps: List[RecipeStep] = Field(
        default=[],
        description="Ordered list of recipe steps"
    )
    tags: List[str] = Field(
        default=[],
        description="Categorization: 'documentation', 'debugging', 'onboarding', etc."
    )
    owner: Optional[str] = Field(
        default=None,
        description="User who created/owns this recipe"
    )
    created_at: str = Field(
        default_factory=lambda: str(datetime.now())
    )
    updated_at: str = Field(
        default_factory=lambda: str(datetime.now())
    )
    # Storage location
    project_id: Optional[str] = Field(
        default=None,
        description="Associated project, if any"
    )
    kanban_board: str = Field(
        default="recipes",
        description="Board name for recipe organization"
    )
    kanban_column: str = Field(
        default="active",
        description="Column: 'templates', 'active', 'archived', etc."
    )
    # Execution & progress
    metrics: Optional[RecipeMetrics] = Field(
        default=None,
        description="Progress and performance metrics (only on instances)"
    )
    auto_execute: Optional[bool] = Field(
        default=False,
        description="If True and type='automation', run unattended on schedule"
    )
    auto_execute_schedule: Optional[str] = Field(
        default=None,
        description="Cron or interval for auto_execute (e.g., '0 0 * * 0' for weekly)"
    )
    # Linking
    related_recipe_ids: Optional[List[str]] = Field(
        default=[],
        description="Other recipes this one depends on or recommends"
    )
    # Free-form extensibility
    meta_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Custom fields: tool config, automation params, playbook branching logic, etc."
    )


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
    attachments: List[ChatAttachment] = Field(default=[], description="Attachments for this message")
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
    # Recipe fields
    recipe_step_index: Optional[int] = Field(
        default=None,
        description="Index of the recipe step this message belongs to"
    )
    recipe_step_action: Optional[str] = Field(
        default=None,
        description="Action context for this message: 'instruction', 'hint', 'validation', 'result'"
    )
    recipe_requires_acknowledgment: Optional[bool] = Field(
        default=None,
        description="When True, user/system must explicitly acknowledge this message to proceed"
    )


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
    """
    Represents a chat session with messages, metadata, and kanban board associations.
    
    Extended to support recipes: a chat can be either a standalone conversation
    or part of a recipe (tutorial, automation, workflow, etc.).
    """
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
    attachments: List[ChatAttachment] = Field(default=[], description="Attachments for this chat")
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
    # Recipe integration
    recipe_id: Optional[str] = Field(
        default=None,
        description="The recipe this chat belongs to (links to Recipe.id)"
    )
    recipe_step_index: Optional[int] = Field(
        default=None,
        description="Which step within the recipe (maps to Recipe.steps[n])"
    )


# Made with ❤️ by codx-junior