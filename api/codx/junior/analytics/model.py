from dataclasses import dataclass, field, asdict, fields
from datetime import datetime
from typing import Optional, List, Any, Dict
import time


@dataclass
class TokenUsageEvent:
    """
    Represents a single LLM call with token consumption metadata.

    Fields:
        username:              The user who triggered the request.
        project_name:          The project context for the request.
        project_id:            The project identifier.
        model:                 LLM model name used (e.g. "gpt-4o").
        provider:              LLM provider (e.g. "openai", "litellm").
        input_tokens:          Number of tokens in the prompt/input.
        output_tokens:         Number of tokens in the completion/output.
        total_tokens:          Sum of input + output tokens.
        duration_seconds:      Wall-clock seconds from first request to last chunk.
        timestamp:             Unix epoch timestamp of the event.
        iso_date:              ISO-8601 date string (YYYY-MM-DD) for partitioning.
        session_id:            Optional session/conversation identifier.
        tags:                  Comma-separated tags associated with the request.
        input_k_tokens_cxjcoins:   Price per 1K input tokens in CXJ coins (from AISettings).
        output_k_tokens_cxjcoins:  Price per 1K output tokens in CXJ coins (from AISettings).
        total_cxjcoins:        Total cost in CXJ coins for this event.
        request_id:            Request id for traceability
        tokens_from_provider:  Token count comes from provider's response, else they are calculated
        chat_id:               Chat identifier for linking to chat sessions
    """
    username: str
    project_name: str
    project_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)
    iso_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    session_id: Optional[str] = None
    tags: str = ""
    input_k_tokens_cxjcoins: float = 0.0
    output_k_tokens_cxjcoins: float = 0.0
    total_cxjcoins: float = 0.0
    request_id: str = None
    tokens_from_provider: bool = False
    chat_id: Optional[str] = None

    def __post_init__(self):
        """Compute total_cxjcoins from input/output tokens and their respective prices if not set."""
        if self.total_cxjcoins == 0.0:
            input_cost = (self.input_tokens / 1000.0) * self.input_k_tokens_cxjcoins
            output_cost = (self.output_tokens / 1000.0) * self.output_k_tokens_cxjcoins
            self.total_cxjcoins = input_cost + output_cost

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TokenUsageEvent":
        """
        Build a TokenUsageEvent from a dict, tolerating old/missing/incorrect fields.

        Backwards-compatibility rules:
        - Old records may have 'k_tokens_cxjcoins' instead of the split fields;
          in that case both input and output prices are set to that value.
        - Any field that is missing or of an incompatible type falls back to
          the dataclass default (or default_factory) for that field.
        """
        field_defaults: dict = {}
        for f in fields(cls):
            if f.default is not f.default_factory:
                field_defaults[f.name] = f.default
            elif f.default_factory is not f.default_factory:
                pass

        cleaned: dict = {}
        legacy_k = data.get("k_tokens_cxjcoins")
        known_fields = {f.name: f for f in fields(cls)}

        for name, f in known_fields.items():
            raw = data.get(name)

            if raw is None and name in ("input_k_tokens_cxjcoins", "output_k_tokens_cxjcoins"):
                raw = legacy_k

            if raw is None:
                continue

            try:
                target_type = f.type
                origin = getattr(target_type, "__origin__", None)
                if origin is type(None):
                    cleaned[name] = raw
                    continue

                if target_type in (int, float, str, bool):
                    cleaned[name] = target_type(raw)
                elif target_type == Optional[str] or str(target_type) in ("typing.Optional[str]", "Optional[str]"):
                    cleaned[name] = str(raw) if raw is not None else None
                else:
                    cleaned[name] = raw
            except (TypeError, ValueError):
                pass

        return cls(**cleaned)


@dataclass
class ToolUsageEvent:
    """
    Represents a single tool execution with metadata.

    Fields:
        name:              Tool function name (e.g., "project_search").
        username:          User who triggered the tool.
        project_name:      Project context for the tool call.
        project_id:        Project identifier.
        time_taken:        Execution duration in seconds.
        success:           Boolean flag indicating successful execution.
        error_message:     Error details if execution failed (None if successful).
        chat_id:           Reference to the parent chat/conversation session.
        request_id:        Traceability link to the LLM request that triggered the tool.
        timestamp:         Unix epoch timestamp of when the tool was executed.
        iso_date:          ISO-8601 date string (YYYY-MM-DD) for partitioning.
    """
    name: str
    username: str
    project_name: str
    project_id: str
    time_taken: float
    success: bool
    error_message: Optional[str] = None
    chat_id: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    iso_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ToolUsageEvent":
        """
        Build a ToolUsageEvent from a dict, tolerating missing/incorrect fields.

        Any field that is missing or of an incompatible type falls back to
        the dataclass default (or default_factory) for that field.
        """
        cleaned: dict = {}
        known_fields = {f.name: f for f in fields(cls)}

        for name, f in known_fields.items():
            raw = data.get(name)

            if raw is None:
                continue

            try:
                target_type = f.type
                origin = getattr(target_type, "__origin__", None)
                if origin is type(None):
                    cleaned[name] = raw
                    continue

                if target_type in (int, float, str, bool):
                    cleaned[name] = target_type(raw)
                elif target_type == Optional[str] or str(target_type) in ("typing.Optional[str]", "Optional[str]"):
                    cleaned[name] = str(raw) if raw is not None else None
                else:
                    cleaned[name] = raw
            except (TypeError, ValueError):
                pass

        return cls(**cleaned)


@dataclass
class ChatSessionEvent:
    """
    Represents a chat session with full context for traceability.

    Captures the complete chat lifecycle including profiles, files, parent relationships,
    and iteration data. Enables reconstruction of full request-response chains from
    analytics data. Can be updated incrementally as the chat progresses.

    Fields:
        chat_id:               Unique chat identifier (from chat.id).
        chat_name:             Human-readable chat name.
        username:              User who created/executed the chat.
        project_name:          Project context name.
        project_id:            Project identifier.
        mode:                  Chat mode ('task', 'agent', 'vibe', 'chat').
        profiles:              List of profile names applied to this chat.
        files:                 List of file paths accessed during chat.
        parent_chat_id:        Parent chat ID if this is a nested chat (optional).
        iteration:             Current agent iteration number.
        max_iterations:        Maximum iterations allowed for agent mode.
        llm_model:             LLM model used for this chat.
        parent_request_id:     Parent request ID if spawned from tool call (optional).
        session_id:            Session identifier for grouping chats (optional).
        started_at:            Unix timestamp when chat started.
        ended_at:              Unix timestamp when chat ended (optional).
        duration_seconds:      Total chat duration in seconds.
        input_message_count:   Number of input messages in chat.
        output_message_count:  Number of output messages in chat.
        cancelled:             Whether the chat was cancelled.
        error:                 Error message if chat failed (optional).
        timestamp:             Unix timestamp for storage partitioning.
        iso_date:              ISO-8601 date string (YYYY-MM-DD) for partitioning.
    """
    chat_id: str
    chat_name: str
    username: str
    project_name: str
    project_id: str
    mode: str
    profiles: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    parent_chat_id: Optional[str] = None
    iteration: int = 0
    max_iterations: int = 0
    llm_model: str = ""
    parent_request_id: Optional[str] = None
    session_id: Optional[str] = None
    started_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    ended_at: Optional[float] = None
    duration_seconds: float = 0.0
    input_message_count: int = 0
    output_message_count: int = 0
    cancelled: bool = False
    error: Optional[str] = None
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    iso_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ChatSessionEvent":
        """
        Build a ChatSessionEvent from a dict, tolerating missing/incorrect fields.

        Any field that is missing or of an incompatible type falls back to
        the dataclass default (or default_factory) for that field.
        """
        cleaned: dict = {}
        known_fields = {f.name: f for f in fields(cls)}

        for name, f in known_fields.items():
            raw = data.get(name)

            if raw is None:
                continue

            try:
                target_type = f.type
                origin = getattr(target_type, "__origin__", None)

                if origin is type(None):
                    cleaned[name] = raw
                    continue

                if origin is list:
                    if isinstance(raw, list):
                        cleaned[name] = raw
                    else:
                        cleaned[name] = [raw] if raw else []
                    continue

                if target_type in (int, float, str, bool):
                    cleaned[name] = target_type(raw)
                elif target_type == Optional[str] or str(target_type) in ("typing.Optional[str]", "Optional[str]"):
                    cleaned[name] = str(raw) if raw is not None else None
                else:
                    cleaned[name] = raw
            except (TypeError, ValueError):
                pass

        return cls(**cleaned)


# ── ADDED: Enriched response types for chat-aware analytics ───────────────────


@dataclass
class EnrichedTokenUsageEvent:
    """
    TokenUsageEvent enriched with associated ChatSessionEvent metadata.

    Merges token usage data with chat context for comprehensive analytics views.
    Allows users/admins to understand token consumption in the context of specific chats.

    Fields:
        token_event:    The base TokenUsageEvent.
        chat_session:   Associated ChatSessionEvent (if chat_id was present), else None.
    """
    token_event: TokenUsageEvent
    chat_session: Optional[ChatSessionEvent] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict with nested structure."""
        return {
            "token_event": self.token_event.to_dict(),
            "chat_session": self.chat_session.to_dict() if self.chat_session else None,
        }


@dataclass
class EnrichedToolUsageEvent:
    """
    ToolUsageEvent enriched with associated ChatSessionEvent metadata.

    Merges tool execution data with chat context for comprehensive tool analytics.
    Allows users/admins to understand tool usage in the context of specific chats.

    Fields:
        tool_event:     The base ToolUsageEvent.
        chat_session:   Associated ChatSessionEvent (if chat_id was present), else None.
    """
    tool_event: ToolUsageEvent
    chat_session: Optional[ChatSessionEvent] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict with nested structure."""
        return {
            "tool_event": self.tool_event.to_dict(),
            "chat_session": self.chat_session.to_dict() if self.chat_session else None,
        }


@dataclass
class ChatMetrics:
    """
    Aggregated metrics for token usage and tool execution within a chat session.

    Provides a summary view of resource consumption and tool execution
    statistics for a complete chat lifecycle.

    Fields:
        total_input_tokens:      Sum of input tokens across all LLM calls in chat.
        total_output_tokens:     Sum of output tokens across all LLM calls in chat.
        total_tokens:            Sum of all tokens (input + output).
        llm_calls:               Count of LLM requests made in chat.
        total_llm_duration_seconds: Sum of all LLM request durations.
        total_cxjcoins:          Total cost in CXJ coins for all LLM calls.
        tool_calls:              Count of tool executions in chat.
        successful_tool_calls:   Count of successful tool executions.
        failed_tool_calls:       Count of failed tool executions.
        total_tool_duration_seconds: Sum of all tool execution durations.
        avg_tool_duration_seconds: Average tool execution duration.
    """
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0
    total_llm_duration_seconds: float = 0.0
    total_cxjcoins: float = 0.0
    tool_calls: int = 0
    successful_tool_calls: int = 0
    failed_tool_calls: int = 0
    total_tool_duration_seconds: float = 0.0
    avg_tool_duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return asdict(self)


@dataclass
class ChatContextSummary:
    """
    Complete chat context with session info and aggregated metrics.

    Provides a high-level summary of a chat session including metadata,
    resource consumption, and tool execution statistics. Ideal for
    dashboard and summary views.

    Fields:
        chat_session:   The ChatSessionEvent containing chat metadata.
        metrics:        Aggregated ChatMetrics for the session.
        llm_request_count: Number of LLM requests in session (for detail queries).
        tool_call_count: Number of tool calls in session (for detail queries).
    """
    chat_session: ChatSessionEvent
    metrics: ChatMetrics
    llm_request_count: int = 0
    tool_call_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict with nested structure."""
        return {
            "chat_session": self.chat_session.to_dict(),
            "metrics": self.metrics.to_dict(),
            "llm_request_count": self.llm_request_count,
            "tool_call_count": self.tool_call_count,
        }

# Made with ❤️ by codx-junior