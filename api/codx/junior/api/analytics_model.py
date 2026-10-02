"""
Pydantic models for Analytics API responses.

These models define the exact types returned by all analytics endpoints,
ensuring type safety and proper documentation for both backend and client.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Token Usage Models ─────────────────────────────────────────────────────────

class TokenUsageMetrics(BaseModel):
    """Aggregated token usage metrics."""
    
    input_tokens: int = Field(description="Total input tokens")
    output_tokens: int = Field(description="Total output tokens")
    total_tokens: int = Field(description="Sum of input + output tokens")
    calls: int = Field(description="Number of LLM calls")
    total_duration_seconds: float = Field(description="Total duration in seconds")
    total_cxjcoins: float = Field(description="Total cost in CXJ coins")
    tokens_from_provider: bool = Field(description="Whether token count comes from provider")


class DailyUsageEntry(BaseModel):
    """Single day's aggregated usage."""
    
    period: str = Field(description="Time period (YYYY-MM-DD for day grouping)")
    input_tokens: int
    output_tokens: int
    total_tokens: int
    calls: int
    total_duration_seconds: float
    total_cxjcoins: float
    tokens_from_provider: bool


class UserMetrics(BaseModel):
    """User's token usage for today and current month."""
    
    username: str = Field(description="Username")
    today: TokenUsageMetrics = Field(description="Today's usage")
    current_month: TokenUsageMetrics = Field(description="Current month's usage")


# ── Chat Session Models ────────────────────────────────────────────────────────

class ChatSessionMetadata(BaseModel):
    """Chat session metadata."""
    
    chat_id: str = Field(description="Unique chat identifier")
    chat_name: str = Field(description="Human-readable chat name")
    username: str = Field(description="User who created the chat")
    project_name: str = Field(description="Project context name")
    project_id: str = Field(description="Project identifier")
    mode: str = Field(description="Chat mode (task, agent, vibe, chat)")
    profiles: List[str] = Field(default_factory=list, description="Applied profiles")
    files: List[str] = Field(default_factory=list, description="Accessed files")
    parent_chat_id: Optional[str] = Field(default=None, description="Parent chat if nested")
    iteration: int = Field(description="Current iteration number")
    max_iterations: int = Field(description="Maximum iterations")
    llm_model: str = Field(description="LLM model used")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    cancelled: bool = Field(description="Whether chat was cancelled")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    duration_seconds: float = Field(description="Total duration in seconds")
    input_message_count: int = Field(description="Number of input messages")
    output_message_count: int = Field(description="Number of output messages")
    timestamp: float = Field(description="Unix timestamp")
    iso_date: str = Field(description="ISO date YYYY-MM-DD")


class ChatMetrics(BaseModel):
    """Aggregated metrics for a chat session."""
    
    total_input_tokens: int = Field(description="Sum of input tokens")
    total_output_tokens: int = Field(description="Sum of output tokens")
    total_tokens: int = Field(description="Total tokens")
    llm_calls: int = Field(description="Number of LLM calls")
    total_llm_duration_seconds: float = Field(description="Total LLM duration")
    total_cxjcoins: float = Field(description="Total cost in CXJ coins")
    tool_calls: int = Field(description="Number of tool executions")
    successful_tool_calls: int = Field(description="Successful tool executions")
    failed_tool_calls: int = Field(description="Failed tool executions")
    total_tool_duration_seconds: float = Field(description="Total tool duration")
    avg_tool_duration_seconds: float = Field(description="Average tool duration")


class ChatContextSummary(BaseModel):
    """Summary of a chat session with metadata and metrics."""
    
    chat_session: ChatSessionMetadata = Field(description="Chat metadata")
    metrics: ChatMetrics = Field(description="Aggregated metrics")
    llm_request_count: int = Field(description="Number of LLM requests")
    tool_call_count: int = Field(description="Number of tool calls")


# ── Message Models ────────────────────────────────────────────────────────────

class ArchivedMessageData(BaseModel):
    """Complete message exchanged with AI provider."""
    
    message_id: str = Field(description="Unique message identifier")
    chat_id: str = Field(description="Parent chat identifier")
    username: str = Field(description="User who triggered the message")
    project_name: str = Field(description="Project context")
    project_id: str = Field(description="Project identifier")
    model: str = Field(description="LLM model used")
    provider: str = Field(description="LLM provider")
    request_messages: List[Dict[str, Any]] = Field(description="Messages sent to provider")
    response_content: str = Field(description="Full response content")
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    tool_call_id: Optional[str] = Field(default=None, description="Tool call ID if triggered by tool")
    tool_name: Optional[str] = Field(default=None, description="Tool name if applicable")
    duration_seconds: float = Field(description="Wall-clock duration")
    input_tokens: int = Field(description="Request token count")
    output_tokens: int = Field(description="Response token count")
    error: Optional[str] = Field(default=None, description="Error if failed")
    cancelled: bool = Field(description="Whether request was cancelled")
    timestamp: float = Field(description="Unix timestamp")
    iso_date: str = Field(description="ISO date YYYY-MM-DD")


class ToolCallMessageData(BaseModel):
    """Tool call execution record."""
    
    message_id: str = Field(description="Unique message identifier")
    chat_id: str = Field(description="Parent chat identifier")
    tool_call_id: str = Field(description="Tool call ID from AI provider")
    tool_name: str = Field(description="Name of tool executed")
    username: str = Field(description="User context")
    project_name: str = Field(description="Project context")
    project_id: str = Field(description="Project identifier")
    request_args: Dict[str, Any] = Field(description="Arguments sent to tool")
    result: Any = Field(description="Tool execution result (as JSON string in storage)")
    result_sent_to_model: str = Field(description="Normalized result sent to model")
    success: bool = Field(description="Whether tool executed successfully")
    error_message: Optional[str] = Field(default=None, description="Error details")
    duration_seconds: float = Field(description="Execution duration")
    cached: bool = Field(description="Whether result was cached")
    timestamp: float = Field(description="Unix timestamp")
    iso_date: str = Field(description="ISO date YYYY-MM-DD")


class ChatMessagesResponse(BaseModel):
    """Response containing all messages for a chat."""
    
    llm_messages: List[ArchivedMessageData] = Field(description="Archived LLM messages")
    tool_messages: List[ToolCallMessageData] = Field(description="Tool call messages")
    total_llm_messages: int = Field(description="Count of LLM messages")
    total_tool_messages: int = Field(description="Count of tool messages")


# ── Tool Metrics Models ────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    """Single error that occurred during tool execution."""
    
    timestamp: float = Field(description="When error occurred")
    error_message: str = Field(description="Error message")


class ToolExecutionMetrics(BaseModel):
    """Execution metrics for a single tool."""
    
    total_calls: int = Field(description="Total number of calls")
    successful: int = Field(description="Successful executions")
    failed: int = Field(description="Failed executions")
    success_rate: float = Field(description="Success rate percentage (0-100)")
    total_duration: float = Field(description="Total execution time in seconds")
    avg_duration: float = Field(description="Average execution time")
    min_duration: float = Field(description="Minimum execution time")
    max_duration: float = Field(description="Maximum execution time")
    error_details: List[ErrorDetail] = Field(default_factory=list, description="Failed execution details")


class ToolMetricsMap(BaseModel):
    """Metrics for all tools executed in a chat."""
    
    __root__: Dict[str, ToolExecutionMetrics] = Field(
        description="Map of tool_name → ToolExecutionMetrics"
    )

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, key):
        return self.__root__[key]


# ── Chat Context Models ────────────────────────────────────────────────────────

class LLMRequestRecord(BaseModel):
    """Single LLM request usage record."""
    
    username: str
    project_name: str
    project_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    duration_seconds: float
    session_id: Optional[str]
    tags: str
    input_k_tokens_cxjcoins: float
    output_k_tokens_cxjcoins: float
    request_id: Optional[str]
    tokens_from_provider: bool
    chat_id: Optional[str]
    timestamp: float
    iso_date: str
    total_cxjcoins: float


class ToolCallRecord(BaseModel):
    """Single tool execution usage record."""
    
    name: str
    username: str
    project_name: str
    project_id: str
    time_taken: float
    success: bool
    error_message: Optional[str]
    chat_id: Optional[str]
    tool_id: Optional[str]
    request_id: Optional[str]
    timestamp: float
    iso_date: str


class ChatCompleteContext(BaseModel):
    """Complete context for a single chat including all related data."""
    
    chat_session: ChatSessionMetadata = Field(description="Chat session metadata")
    metrics: ChatMetrics = Field(description="Aggregated metrics")
    llm_requests: List[LLMRequestRecord] = Field(description="LLM request usage records")
    llm_messages: List[ArchivedMessageData] = Field(description="Archived LLM messages")
    tool_calls: List[ToolCallRecord] = Field(description="Tool execution usage records")
    tool_messages: List[ToolCallMessageData] = Field(description="Tool call execution records")
    tool_metrics: Dict[str, ToolExecutionMetrics] = Field(description="Aggregated tool metrics by name")


class ChatContextWithToolDetails(BaseModel):
    """Chat context with enriched tool information."""
    
    chat_session: ChatSessionMetadata = Field(description="Chat session metadata")
    metrics: ChatMetrics = Field(description="Aggregated metrics")
    llm_requests: List[LLMRequestRecord] = Field(description="LLM request records")
    tool_calls: List[ToolCallRecord] = Field(description="Tool call records")
    tool_metrics: Dict[str, ToolExecutionMetrics] = Field(description="Detailed tool execution metrics")


# ── Aggregation Models ─────────────────────────────────────────────────────────

class AggregatedUsageByKey(BaseModel):
    """Token usage aggregated by a specific key (user, project, model)."""
    
    __root__: Dict[str, TokenUsageMetrics] = Field(
        description="Map of key → TokenUsageMetrics"
    )

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, key):
        return self.__root__[key]


# ── List Response Models ───────────────────────────────────────────────────────

class DatesList(BaseModel):
    """List of available dates with data."""
    
    __root__: List[str] = Field(
        description="List of YYYY-MM-DD date strings"
    )

    def __iter__(self):
        return iter(self.__root__)

    def __len__(self):
        return len(self.__root__)


class ChatSessionsList(BaseModel):
    """List of chat sessions with metrics."""
    
    __root__: List[ChatContextSummary] = Field(
        description="List of chat sessions with their summaries"
    )

    def __iter__(self):
        return iter(self.__root__)

    def __len__(self):
        return len(self.__root__)


# ── Pricing Models ─────────────────────────────────────────────────────────────

class ModelPricingInfo(BaseModel):
    """Pricing information for a single model."""
    
    name: str = Field(description="Model name")
    ai_model: Optional[str] = Field(default=None, description="Provider-side model name")
    input_k_tokens_cxjcoins: float = Field(description="Input price per 1K tokens")
    output_k_tokens_cxjcoins: float = Field(description="Output price per 1K tokens")


class ProviderPricingInfo(BaseModel):
    """Pricing information for a provider and its models."""
    
    name: str = Field(description="Provider name")
    input_k_tokens_cxjcoins: float = Field(description="Provider-level input price per 1K tokens")
    output_k_tokens_cxjcoins: float = Field(description="Provider-level output price per 1K tokens")
    models: List[ModelPricingInfo] = Field(description="Model-level pricing overrides")


class PricingList(BaseModel):
    """List of providers with their pricing information."""
    
    __root__: List[ProviderPricingInfo] = Field(
        description="List of providers with models and pricing"
    )

    def __iter__(self):
        return iter(self.__root__)

    def __len__(self):
        return len(self.__root__)

# Made with ❤️ by codx-junior