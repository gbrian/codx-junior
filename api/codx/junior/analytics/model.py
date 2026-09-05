import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TokenUsageEvent:
    """
    Record of a single LLM token consumption event.
    
    Tracks token usage, cost, and timing information for LLM requests
    within the context of a chat session.
    """
    
    username: str
    """User who triggered the request."""
    
    project_name: str
    """Project context name."""
    
    project_id: str
    """Project identifier."""
    
    model: str
    """LLM model name (e.g., 'gpt-4o')."""
    
    provider: str
    """LLM provider (e.g., 'openai')."""
    
    input_tokens: int
    """Number of tokens in the prompt/input."""
    
    output_tokens: int
    """Number of tokens in the completion/output."""
    
    total_tokens: int
    """Sum of input + output tokens."""
    
    duration_seconds: float = 0.0
    """Wall-clock duration of the LLM request."""
    
    session_id: Optional[str] = None
    """Optional session/conversation identifier."""
    
    tags: str = ""
    """Comma-separated tags associated with the request."""
    
    input_k_tokens_cxjcoins: float = 0.0
    """Price per 1K input tokens in CXJ coins."""
    
    output_k_tokens_cxjcoins: float = 0.0
    """Price per 1K output tokens in CXJ coins."""
    
    request_id: Optional[str] = None
    """Unique request identifier for traceability."""
    
    tokens_from_provider: bool = False
    """Whether token count comes from provider's response."""
    
    chat_id: Optional[str] = None
    """Chat identifier for linking to chat sessions."""
    
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    """Unix timestamp when the event occurred."""
    
    iso_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    """ISO date (YYYY-MM-DD) for file partitioning."""
    
    total_cxjcoins: float = 0.0
    """Total cost in CXJ coins for this event."""

    def __post_init__(self) -> None:
        """Recalculate total_cxjcoins from token counts and pricing."""
        if self.total_cxjcoins == 0.0:
            input_cost = (self.input_tokens / 1000.0) * self.input_k_tokens_cxjcoins
            output_cost = (self.output_tokens / 1000.0) * self.output_k_tokens_cxjcoins
            self.total_cxjcoins = input_cost + output_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TokenUsageEvent":
        """Create instance from dictionary."""
        return TokenUsageEvent(**data)


@dataclass
class ToolUsageEvent:
    """
    Record of a single tool execution event.
    
    Captures tool invocation, execution duration, and success/failure status
    within the context of a chat session.
    """
    
    name: str
    """Tool function name."""
    
    username: str
    """User who triggered the tool."""
    
    project_name: str
    """Project context name."""
    
    project_id: str
    """Project identifier."""
    
    time_taken: float
    """Execution duration in seconds."""
    
    success: bool
    """Whether the tool executed successfully."""
    
    error_message: Optional[str] = None
    """Error details if execution failed."""
    
    chat_id: Optional[str] = None
    """Chat identifier for linking to chat sessions."""
    
    tool_id: Optional[str] = None
    """Tool call ID for linking to specific tool invocations within a chat."""
    
    request_id: Optional[str] = None
    """Request ID linking to the LLM request that triggered the tool."""
    
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    """Unix timestamp when the tool was executed."""
    
    iso_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    """ISO date (YYYY-MM-DD) for file partitioning."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ToolUsageEvent":
        """Create instance from dictionary."""
        return ToolUsageEvent(**data)


@dataclass
class ChatSessionEvent:
    """
    Record of a complete chat session lifecycle.
    
    Captures metadata about a chat session including mode, profiles, files,
    and execution context for traceability and analytics.
    """
    
    chat_id: str
    """Unique chat identifier."""
    
    chat_name: str
    """Human-readable chat name."""
    
    username: str
    """User who created/executed the chat."""
    
    project_name: str
    """Project context name."""
    
    project_id: str
    """Project identifier."""
    
    mode: str
    """Chat mode ('task', 'agent', 'vibe', 'chat')."""
    
    profiles: List[str] = field(default_factory=list)
    """List of profile names applied to this chat."""
    
    files: List[str] = field(default_factory=list)
    """List of file paths accessed during chat."""
    
    parent_chat_id: Optional[str] = None
    """Parent chat ID if this is a nested chat."""
    
    iteration: int = 0
    """Current agent iteration number."""
    
    max_iterations: int = 0
    """Maximum iterations allowed for agent mode."""
    
    llm_model: str = ""
    """LLM model used for this chat."""
    
    parent_request_id: Optional[str] = None
    """Parent request ID if spawned from tool call."""
    
    session_id: Optional[str] = None
    """Session identifier for grouping chats."""
    
    cancelled: bool = False
    """Whether the chat was cancelled."""
    
    error: Optional[str] = None
    """Error message if chat failed."""
    
    duration_seconds: float = 0.0
    """Total chat duration in seconds."""
    
    input_message_count: int = 0
    """Number of input messages in chat."""
    
    output_message_count: int = 0
    """Number of output messages in chat."""
    
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    """Unix timestamp for storage partitioning."""
    
    iso_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    """ISO date (YYYY-MM-DD) for file partitioning."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ChatSessionEvent":
        """Create instance from dictionary."""
        return ChatSessionEvent(**data)


@dataclass
class ArchivedMessage:
    """
    Record of a complete message exchanged with the AI provider.
    
    Captures the full request-response cycle for traceability and audit.
    Links to chat and optionally to a tool call within that chat.
    
    Diagram:
    classDiagram
        class ArchivedMessage {
            +str message_id
            +str chat_id
            +Optional str request_id
            +Optional str tool_call_id
            +List request_messages
            +str response_content
            +int input_tokens
            +int output_tokens
            +float duration_seconds
            +Optional str error
            +float timestamp
            +str iso_date
        }
    """
    
    message_id: str
    """Unique identifier for this archived message."""
    
    chat_id: str
    """Parent chat identifier for linking."""
    
    username: str
    """User who triggered the message."""
    
    project_name: str
    """Project context."""
    
    project_id: str
    """Project identifier."""
    
    model: str
    """LLM model used."""
    
    provider: str
    """LLM provider."""
    
    request_messages: List[Dict[str, Any]]
    """Full list of messages sent to provider (including system prompt)."""
    
    response_content: str
    """Full response content from the provider."""
    
    request_id: Optional[str] = None
    """Unique request identifier linking to token usage event."""
    
    tool_call_id: Optional[str] = None
    """Tool call ID if this message was triggered by a tool call."""
    
    tool_name: Optional[str] = None
    """Name of the tool that triggered this message."""
    
    duration_seconds: float = 0.0
    """Wall-clock duration of the LLM request."""
    
    input_tokens: int = 0
    """Token count for the request."""
    
    output_tokens: int = 0
    """Token count for the response."""
    
    error: Optional[str] = None
    """Error message if the request failed."""
    
    cancelled: bool = False
    """Whether the request was cancelled."""
    
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    """Unix timestamp when the message was archived."""
    
    iso_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    """ISO date (YYYY-MM-DD) for file partitioning."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ArchivedMessage":
        """Create instance from dictionary."""
        return ArchivedMessage(**data)


@dataclass
class ToolCallMessage:
    """
    Record of all messages exchanged during a single tool call's execution.
    
    Captures the tool invocation parameters, execution result, and any
    messages exchanged with the AI model regarding this tool.
    
    Diagram:
    classDiagram
        class ToolCallMessage {
            +str message_id
            +str chat_id
            +str tool_call_id
            +str tool_name
            +Dict request_args
            +Any result
            +str result_sent_to_model
            +bool success
            +bool cached
            +Optional str error_message
            +float duration_seconds
            +float timestamp
            +str iso_date
        }
    """
    
    message_id: str
    """Unique identifier for this tool call message record."""
    
    chat_id: str
    """Parent chat identifier."""
    
    tool_call_id: str
    """The tool call ID from the AI provider."""
    
    tool_name: str
    """Name of the tool being executed."""
    
    username: str
    """User context."""
    
    project_name: str
    """Project context."""
    
    project_id: str
    """Project identifier."""
    
    request_args: Dict[str, Any]
    """Parsed arguments sent to the tool."""
    
    result: Any
    """Result returned by the tool (string, dict, ToolResponse, or error)."""
    
    result_sent_to_model: str
    """Normalized result string sent back to the model."""
    
    success: bool
    """Whether the tool executed successfully."""
    
    error_message: Optional[str] = None
    """Error details if execution failed."""
    
    duration_seconds: float = 0.0
    """Tool execution duration."""
    
    cached: bool = False
    """Whether this result was served from cache."""
    
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    """Unix timestamp when the tool was executed."""
    
    iso_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    """ISO date (YYYY-MM-DD) for file partitioning."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert result to JSON-serializable form
        try:
            data["result"] = json.dumps(data["result"], ensure_ascii=False)
        except (TypeError, ValueError):
            data["result"] = str(data["result"])
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ToolCallMessage":
        """Create instance from dictionary, restoring result from JSON."""
        # Restore result from JSON string
        if isinstance(data.get("result"), str):
            try:
                data["result"] = json.loads(data["result"])
            except (json.JSONDecodeError, ValueError):
                pass
        return ToolCallMessage(**data)


@dataclass
class ChatMetrics:
    """Aggregated metrics for a chat session."""
    
    total_input_tokens: int = 0
    """Sum of input tokens across all LLM calls."""
    
    total_output_tokens: int = 0
    """Sum of output tokens across all LLM calls."""
    
    total_tokens: int = 0
    """Sum of all tokens (input + output)."""
    
    llm_calls: int = 0
    """Count of LLM requests made in chat."""
    
    total_llm_duration_seconds: float = 0.0
    """Sum of all LLM request durations."""
    
    total_cxjcoins: float = 0.0
    """Total cost in CXJ coins for all LLM calls."""
    
    tool_calls: int = 0
    """Count of tool executions in chat."""
    
    successful_tool_calls: int = 0
    """Count of successful tool executions."""
    
    failed_tool_calls: int = 0
    """Count of failed tool executions."""
    
    total_tool_duration_seconds: float = 0.0
    """Sum of all tool execution durations."""
    
    avg_tool_duration_seconds: float = 0.0
    """Average tool execution duration."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ChatMetrics":
        """Create instance from dictionary."""
        return ChatMetrics(**data)


@dataclass
class EnrichedTokenUsageEvent:
    """Token usage event enriched with associated chat session context."""
    
    token_event: TokenUsageEvent
    """The base TokenUsageEvent."""
    
    chat_session: Optional[ChatSessionEvent] = None
    """Associated ChatSessionEvent if chat_id was present."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "token_event": self.token_event.to_dict(),
            "chat_session": self.chat_session.to_dict() if self.chat_session else None,
        }


@dataclass
class EnrichedToolUsageEvent:
    """Tool usage event enriched with associated chat session context."""
    
    tool_event: ToolUsageEvent
    """The base ToolUsageEvent."""
    
    chat_session: Optional[ChatSessionEvent] = None
    """Associated ChatSessionEvent if chat_id was present."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_event": self.tool_event.to_dict(),
            "chat_session": self.chat_session.to_dict() if self.chat_session else None,
        }


@dataclass
class ChatContextSummary:
    """Summary of a chat session with metrics and request counts."""
    
    chat_session: ChatSessionEvent
    """The ChatSessionEvent containing chat metadata."""
    
    metrics: ChatMetrics
    """Aggregated ChatMetrics for the session."""
    
    llm_request_count: int = 0
    """Number of LLM requests in session."""
    
    tool_call_count: int = 0
    """Number of tool calls in session."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chat_session": self.chat_session.to_dict(),
            "metrics": self.metrics.to_dict(),
            "llm_request_count": self.llm_request_count,
            "tool_call_count": self.tool_call_count,
        }

# Made with ❤️ by codx-junior