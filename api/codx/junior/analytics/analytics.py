import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from codx.junior.analytics.model import (
    TokenUsageEvent,
    ToolUsageEvent,
    ChatSessionEvent,
    ChatContextSummary,
    ChatMetrics,
    EnrichedTokenUsageEvent,
    EnrichedToolUsageEvent,
    ArchivedMessage,
    ToolCallMessage,
)
from codx.junior.analytics.storage import AnalyticsStorage
from codx.junior.globals import ANALYTICS_DATA_PATH

logger = logging.getLogger(__name__)


class Analytics:
    """
    High-level API for recording and querying LLM token usage, tool usage, and chat sessions.

    The global analytics path is read from
    ``codx.junior.globals.ANALYTICS_DATA_PATH`` which is sourced from the
    ``CODX_JUNIOR_API_ANALYTICS_DATA_PATH`` environment variable.

    Supports:
    - Token usage tracking (input/output tokens, cost)
    - Tool execution metrics (success rate, duration)
    - Chat session lifecycle recording
    - Complete message archival (request/response pairs)
    - Tool call execution history with arguments and results

    Diagram:
    classDiagram
        class Analytics {
            +AnalyticsStorage storage
            +record_token_usage(...)
            +record_tool_usage(...)
            +record_chat_session(...)
            +record_archived_message(...)
            +record_tool_call_message(...)
            +get_usage_by_user(...)
            +get_chat_sessions_by_user(...)
            +get_chat_with_requests(chat_id)
            +get_archived_messages_for_chat(chat_id)
            +get_tool_call_messages_for_chat(chat_id)
            +get_chat_complete_context(chat_id)
            +get_tool_metrics(...)
        }
    """

    def __init__(self, analytics_path: str = ANALYTICS_DATA_PATH):
        """
        Args:
            analytics_path: Global directory for analytics storage.  Pass
                            ``codx.junior.globals.ANALYTICS_DATA_PATH`` here.
        """
        self.storage = AnalyticsStorage(analytics_path=analytics_path)

    # ── Write ──────────────────────────────────────────────────────────────────

    def record_token_usage(
        self,
        *,
        username: str,
        project_name: str,
        project_id: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        duration_seconds: float = 0.0,
        session_id: Optional[str] = None,
        tags: str = "",
        input_k_tokens_cxjcoins: float = 0.0,
        output_k_tokens_cxjcoins: float = 0.0,
        request_id: str = None,
        tokens_from_provider: bool = False,
        chat_id: Optional[str] = None,
    ) -> TokenUsageEvent:
        """
        Record a single LLM call's token consumption.

        Args:
            username:                   User who triggered the call.
            project_name:               Project context.
            project_id:                 Project identifier.
            model:                      LLM model name.
            provider:                   LLM provider identifier.
            input_tokens:               Prompt token count.
            output_tokens:              Completion token count.
            duration_seconds:           Wall-clock seconds for the full request/response cycle.
            session_id:                 Optional conversation/session id.
            tags:                       Comma-separated tag string from request headers.
            input_k_tokens_cxjcoins:    Price per 1K tokens in CXJ coins (from AISettings).
            output_k_tokens_cxjcoins:   Price per 1K tokens in CXJ coins (from AISettings).
            request_id:                 Unique request identifier.
            tokens_from_provider:       Whether tokens came from provider or were calculated.
            chat_id:                    Chat context identifier for traceability.

        Returns:
            The persisted ``TokenUsageEvent``.
        """
        event = TokenUsageEvent(
            username=username,
            project_name=project_name,
            project_id=project_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            duration_seconds=duration_seconds,
            session_id=session_id,
            tags=tags,
            input_k_tokens_cxjcoins=input_k_tokens_cxjcoins,
            output_k_tokens_cxjcoins=output_k_tokens_cxjcoins,
            request_id=request_id,
            tokens_from_provider=tokens_from_provider,
            chat_id=chat_id,
        )
        self.storage.write(event)
        logger.info(
            "Analytics recorded: user=%s project=%s model=%s in=%d out=%d total=%d "
            "duration=%.2fs cxjcoins=%.4f chat_id=%s",
            username,
            project_name,
            model,
            input_tokens,
            output_tokens,
            event.total_tokens,
            duration_seconds,
            event.total_cxjcoins,
            chat_id,
        )
        return event

    def record_tool_usage(
        self,
        *,
        name: str,
        username: str,
        project_name: str,
        project_id: str,
        time_taken: float,
        success: bool,
        error_message: Optional[str] = None,
        chat_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> ToolUsageEvent:
        """
        Record a single tool execution event.

        Args:
            name:            Tool function name (e.g., "project_search").
            username:        User who triggered the tool.
            project_name:    Project context for the tool call.
            project_id:      Project identifier.
            time_taken:      Execution duration in seconds.
            success:         Boolean flag indicating successful execution.
            error_message:   Error details if execution failed (None if successful).
            chat_id:         Reference to the parent chat/conversation session.
            request_id:      Traceability link to the LLM request that triggered the tool.

        Returns:
            The persisted ``ToolUsageEvent``.
        """
        event = ToolUsageEvent(
            name=name,
            username=username,
            project_name=project_name,
            project_id=project_id,
            time_taken=time_taken,
            success=success,
            error_message=error_message,
            chat_id=chat_id,
            request_id=request_id,
        )
        self.storage.write_tool_event(event)
        logger.info(
            "Tool usage recorded: tool=%s user=%s project=%s success=%s time_taken=%.3fs chat_id=%s",
            name,
            username,
            project_name,
            success,
            time_taken,
            chat_id,
        )
        return event

    def record_chat_session(
        self,
        *,
        chat_id: str,
        chat_name: str,
        username: str,
        project_name: str,
        project_id: str,
        mode: str,
        profiles: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
        parent_chat_id: Optional[str] = None,
        iteration: int = 0,
        max_iterations: int = 0,
        llm_model: str = "",
        parent_request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        cancelled: bool = False,
        error: Optional[str] = None,
        duration_seconds: float = 0.0,
        input_message_count: int = 0,
        output_message_count: int = 0,
    ) -> ChatSessionEvent:
        """
        Record a chat session with full context for request traceability.

        Captures the complete chat lifecycle including profiles, files, parent relationships,
        and iteration data. Supports incremental recording — call this method at different
        points in the chat lifecycle (start, during processing, end) to progressively add
        information as it becomes available.

        Args:
            chat_id:             Unique chat identifier (from chat.id).
            chat_name:           Human-readable chat name.
            username:            User who created/executed the chat.
            project_name:        Project context name.
            project_id:          Project identifier.
            mode:                Chat mode ('task', 'agent', 'vibe', 'chat').
            profiles:            List of profile names applied to this chat.
            files:               List of file paths accessed during chat.
            parent_chat_id:      Parent chat ID if this is a nested chat.
            iteration:           Current agent iteration number.
            max_iterations:      Maximum iterations allowed for agent mode.
            llm_model:           LLM model used.
            parent_request_id:   Parent request ID if spawned from tool call.
            session_id:          Session identifier for grouping chats.
            cancelled:           Whether the chat was cancelled.
            error:               Error message if chat failed.
            duration_seconds:    Total chat duration in seconds.
            input_message_count: Number of input messages.
            output_message_count: Number of output messages.

        Returns:
            The persisted ``ChatSessionEvent``.
        """
        event = ChatSessionEvent(
            chat_id=chat_id,
            chat_name=chat_name,
            username=username,
            project_name=project_name,
            project_id=project_id,
            mode=mode,
            profiles=profiles or [],
            files=files or [],
            parent_chat_id=parent_chat_id,
            iteration=iteration,
            max_iterations=max_iterations,
            llm_model=llm_model,
            parent_request_id=parent_request_id,
            session_id=session_id,
            cancelled=cancelled,
            error=error,
            duration_seconds=duration_seconds,
            input_message_count=input_message_count,
            output_message_count=output_message_count,
        )
        self.storage.write_chat_session(event)
        logger.info(
            "Chat session recorded: chat_id=%s user=%s project=%s mode=%s profiles=%s "
            "files=%d duration=%.2fs cancelled=%s error=%s",
            chat_id,
            username,
            project_name,
            mode,
            profiles,
            len(files or []),
            duration_seconds,
            cancelled,
            error,
        )
        return event

    def record_archived_message(
        self,
        *,
        message_id: str,
        chat_id: str,
        username: str,
        project_name: str,
        project_id: str,
        model: str,
        provider: str,
        request_messages: List[Dict[str, Any]],
        response_content: str,
        request_id: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        duration_seconds: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        error: Optional[str] = None,
        cancelled: bool = False,
    ) -> ArchivedMessage:
        """
        Record a complete message exchanged with the AI provider.

        Captures the full request-response cycle for complete traceability
        and audit. Links to chat and optionally to a tool call.

        Args:
            message_id:       Unique identifier for this archived message.
            chat_id:          Parent chat identifier.
            username:         User who triggered the message.
            project_name:     Project context.
            project_id:       Project identifier.
            model:            LLM model used.
            provider:         LLM provider.
            request_messages: Full list of messages sent to the provider.
            response_content: Full response content from the provider.
            request_id:       Unique request identifier (for linking to token event).
            tool_call_id:     If triggered by a tool call, the tool_call_id.
            tool_name:        If triggered by a tool, the tool name.
            duration_seconds: Wall-clock duration.
            input_tokens:     Request token count.
            output_tokens:    Response token count.
            error:            Error message if failed.
            cancelled:        Whether the request was cancelled.

        Returns:
            The persisted ``ArchivedMessage``.
        """
        event = ArchivedMessage(
            message_id=message_id,
            chat_id=chat_id,
            username=username,
            project_name=project_name,
            project_id=project_id,
            model=model,
            provider=provider,
            request_messages=request_messages,
            response_content=response_content,
            request_id=request_id,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            duration_seconds=duration_seconds,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=error,
            cancelled=cancelled,
        )
        self.storage.write_archived_message(event)
        logger.info(
            "Archived message recorded: message_id=%s chat_id=%s model=%s request_id=%s "
            "tool_call_id=%s duration=%.2fs",
            message_id,
            chat_id,
            model,
            request_id,
            tool_call_id,
            duration_seconds,
        )
        return event

    def record_tool_call_message(
        self,
        *,
        message_id: str,
        chat_id: str,
        tool_call_id: str,
        tool_name: str,
        username: str,
        project_name: str,
        project_id: str,
        request_args: Dict[str, Any],
        result: Any,
        result_sent_to_model: str,
        success: bool,
        error_message: Optional[str] = None,
        duration_seconds: float = 0.0,
        cached: bool = False,
    ) -> ToolCallMessage:
        """
        Record a complete tool call execution with all messaging.

        Captures the tool invocation, execution result, and the normalised
        result sent back to the model for complete audit trail.

        Args:
            message_id:           Unique identifier for this tool call record.
            chat_id:              Parent chat identifier.
            tool_call_id:         The tool call ID from the AI provider.
            tool_name:            Name of the tool being executed.
            username:             User context.
            project_name:         Project context.
            project_id:           Project identifier.
            request_args:         Parsed arguments sent to the tool.
            result:               The raw result returned by the tool.
            result_sent_to_model: The normalised result string sent to model.
            success:              Whether the tool executed successfully.
            error_message:        Error details if execution failed.
            duration_seconds:     Tool execution duration.
            cached:               Whether this result was cached.

        Returns:
            The persisted ``ToolCallMessage``.
        """
        event = ToolCallMessage(
            message_id=message_id,
            chat_id=chat_id,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            username=username,
            project_name=project_name,
            project_id=project_id,
            request_args=request_args,
            result=result,
            result_sent_to_model=result_sent_to_model,
            success=success,
            error_message=error_message,
            duration_seconds=duration_seconds,
            cached=cached,
        )
        self.storage.write_tool_call_message(event)
        logger.info(
            "Tool call message recorded: message_id=%s chat_id=%s tool_call_id=%s "
            "tool_name=%s success=%s duration=%.3fs cached=%s",
            message_id,
            chat_id,
            tool_call_id,
            tool_name,
            success,
            duration_seconds,
            cached,
        )
        return event

    # ── Query helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _aggregate(
        events: List[TokenUsageEvent],
        key_fn,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate token counts from events grouped by a key function.

        Args:
            events: Source events.
            key_fn: Callable that extracts the grouping key from an event.

        Returns:
            Dict mapping key → {input_tokens, output_tokens, total_tokens, calls,
                                total_duration_seconds, total_cxjcoins, tokens_from_provider}.
        """
        result: Dict[str, Dict[str, Any]] = {}
        for event in events:
            key = key_fn(event)
            if key not in result:
                result[key] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "calls": 0,
                    "total_duration_seconds": 0.0,
                    "total_cxjcoins": 0.0,
                    "tokens_from_provider": False,
                }
            bucket = result[key]
            bucket["input_tokens"] += event.input_tokens
            bucket["output_tokens"] += event.output_tokens
            bucket["total_tokens"] += event.total_tokens
            bucket["calls"] += 1
            bucket["total_duration_seconds"] += event.duration_seconds
            bucket["total_cxjcoins"] += event.total_cxjcoins
            bucket["tokens_from_provider"] = bucket["tokens_from_provider"] or getattr(
                event, "tokens_from_provider", False
            )
        return result

    @staticmethod
    def _aggregate_tool_events(
        events: List[ToolUsageEvent],
        key_fn,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate tool event metrics grouped by a key function.

        Args:
            events: Source tool events.
            key_fn: Callable that extracts the grouping key from an event.

        Returns:
            Dict mapping key → {calls, successful, failed, total_time_taken, avg_time_taken}.
        """
        result: Dict[str, Dict[str, Any]] = {}
        for event in events:
            key = key_fn(event)
            if key not in result:
                result[key] = {
                    "calls": 0,
                    "successful": 0,
                    "failed": 0,
                    "total_time_taken": 0.0,
                    "avg_time_taken": 0.0,
                }
            bucket = result[key]
            bucket["calls"] += 1
            if event.success:
                bucket["successful"] += 1
            else:
                bucket["failed"] += 1
            bucket["total_time_taken"] += event.time_taken

        # Calculate averages
        for key in result:
            if result[key]["calls"] > 0:
                result[key]["avg_time_taken"] = (
                    result[key]["total_time_taken"] / result[key]["calls"]
                )

        return result

    @staticmethod
    def _get_grouping_key_fn(grouping: str):
        """
        Return key function based on grouping level.

        Args:
            grouping: One of 'minute', 'hour', or 'day'

        Returns:
            Callable that extracts the grouping key from a TokenUsageEvent
        """
        if grouping == "minute":
            return lambda e: datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d %H:%M")
        elif grouping == "hour":
            return lambda e: datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d %H:00")
        else:  # default to day
            return lambda e: datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d")

    # ── Public query API ───────────────────────────────────────────────────────

    def get_usage_by_user(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        project_name: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate token usage grouped by username.

        Args:
            start_date:   Inclusive ISO date lower bound.
            end_date:     Inclusive ISO date upper bound.
            project_name: Optional project filter.
            project_id:   Optional project id filter.

        Returns:
            Dict[username, {input_tokens, output_tokens, total_tokens, calls,
                            total_duration_seconds, total_cxjcoins, tokens_from_provider}]
        """
        events = self.storage.read_events(
            start_date=start_date,
            end_date=end_date,
            project_name=project_name,
            project_id=project_id,
        )
        return self._aggregate(events, lambda e: e.username)

    def get_usage_by_project(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate token usage grouped by project name.

        Args:
            start_date: Inclusive ISO date lower bound.
            end_date:   Inclusive ISO date upper bound.
            username:   Optional user filter.

        Returns:
            Dict[project_name, {input_tokens, output_tokens, total_tokens, calls,
                                total_duration_seconds, total_cxjcoins, tokens_from_provider}]
        """
        events = self.storage.read_events(
            start_date=start_date,
            end_date=end_date,
            username=username,
        )
        return self._aggregate(events, lambda e: e.project_name)

    def get_usage_by_model(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        username: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate token usage grouped by model name.

        Args:
            start_date:   Inclusive ISO date lower bound.
            end_date:     Inclusive ISO date upper bound.
            username:     Optional user filter.
            project_name: Optional project filter.

        Returns:
            Dict[model, {input_tokens, output_tokens, total_tokens, calls,
                         total_duration_seconds, total_cxjcoins, tokens_from_provider}]
        """
        events = self.storage.read_events(
            start_date=start_date,
            end_date=end_date,
            username=username,
            project_name=project_name,
        )
        return self._aggregate(events, lambda e: e.model)

    def get_daily_usage(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        username: Optional[str] = None,
        project_name: Optional[str] = None,
        grouping: str = "day",
    ) -> List[Dict[str, Any]]:
        """
        Return per-period aggregated token usage with configurable grouping.

        Args:
            start_date:   Inclusive ISO date lower bound.
            end_date:     Inclusive ISO date upper bound.
            username:     Optional user filter.
            project_name: Optional project filter.
            grouping:     Time grouping level: 'minute', 'hour', or 'day'. Default: 'day'

        Returns:
            List of dicts [{period, input_tokens, output_tokens, total_tokens, calls,
                            total_duration_seconds, total_cxjcoins, tokens_from_provider}]
            ordered by period ascending.
        """
        events = self.storage.read_events(
            start_date=start_date,
            end_date=end_date,
            username=username,
            project_name=project_name,
        )
        key_fn = self._get_grouping_key_fn(grouping)
        aggregated = self._aggregate(events, key_fn)
        return [
            {"period": period, **counts}
            for period, counts in sorted(aggregated.items())
        ]

    def get_total_usage(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        username: Optional[str] = None,
        project_name: Optional[str] = None,
        project_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return global token totals across all filtered events.

        Args:
            start_date:   Inclusive ISO date lower bound.
            end_date:     Inclusive ISO date upper bound.
            username:     Optional user filter.
            project_name: Optional project filter.
            project_id:   Optional project id filter.
            model:        Optional model filter.

        Returns:
            Dict with keys: input_tokens, output_tokens, total_tokens, calls,
                            total_duration_seconds, total_cxjcoins, tokens_from_provider.
        """
        events = self.storage.read_events(
            start_date=start_date,
            end_date=end_date,
            username=username,
            project_name=project_name,
            project_id=project_id,
            model=model,
        )
        totals: Dict[str, Any] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
            "total_duration_seconds": 0.0,
            "total_cxjcoins": 0.0,
            "tokens_from_provider": False,
        }
        for event in events:
            totals["input_tokens"] += event.input_tokens
            totals["output_tokens"] += event.output_tokens
            totals["total_tokens"] += event.total_tokens
            totals["calls"] += 1
            totals["total_duration_seconds"] += event.duration_seconds
            totals["total_cxjcoins"] += event.total_cxjcoins
            totals["tokens_from_provider"] = totals["tokens_from_provider"] or getattr(
                event, "tokens_from_provider", False
            )
        return totals

    def list_available_dates(self) -> List[str]:
        """
        Return all ISO dates for which analytics data is available.

        Returns:
            Sorted list of ``YYYY-MM-DD`` strings.
        """
        return self.storage.list_available_dates()

    # ── Chat Session Query API ─────────────────────────────────────────────────

    def get_chat_sessions_by_user(
        self,
        username: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> List[ChatSessionEvent]:
        """
        Get all chat sessions for a specific user in a date range.

        Args:
            username:     Username to filter by.
            start_date:   Inclusive ISO date lower bound.
            end_date:     Inclusive ISO date upper bound.
            project_name: Optional project filter.

        Returns:
            List of ``ChatSessionEvent`` objects ordered by timestamp.
        """
        return self.storage.read_chat_sessions(
            start_date=start_date,
            end_date=end_date,
            username=username,
            project_name=project_name,
        )

    def get_chat_with_requests(
        self,
        chat_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a complete chat session with all associated LLM requests and tool calls.

        Enables reconstruction of the full request-response chain for a chat.

        Args:
            chat_id:    The chat identifier to retrieve.
            start_date: Inclusive ISO date lower bound (filters token/tool events).
            end_date:   Inclusive ISO date upper bound (filters token/tool events).

        Returns:
            Dict with keys:
                - chat_session: ChatSessionEvent or None
                - llm_requests: List of TokenUsageEvent
                - tool_calls: List of ToolUsageEvent
        """
        chat_sessions = self.storage.read_chat_sessions(chat_id=chat_id)
        if not chat_sessions:
            logger.warning("No chat session found for chat_id=%s", chat_id)
            return {
                "chat_session": None,
                "llm_requests": [],
                "tool_calls": [],
            }

        # Take the latest session event for this chat (may have incremental updates)
        chat_session = chat_sessions[-1]

        llm_requests = self.storage.read_events(
            start_date=start_date,
            end_date=end_date,
            chat_id=chat_id,
        )

        tool_calls = self.storage.read_tool_events(
            start_date=start_date,
            end_date=end_date,
            chat_id=chat_id,
        )

        return {
            "chat_session": chat_session,
            "llm_requests": llm_requests,
            "tool_calls": tool_calls,
        }

    def get_archived_messages_for_chat(
        self,
        chat_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> List[ArchivedMessage]:
        """
        Get all archived messages for a specific chat.

        Provides complete request-response pairs exchanged with the LLM provider,
        enabling full audit trail and debugging of chat interactions.

        Args:
            chat_id:    The chat identifier.
            start_date: Optional date filter (inclusive).
            end_date:   Optional date filter (inclusive).
            request_id: Optional filter by request id.

        Returns:
            List of ``ArchivedMessage`` objects ordered by timestamp.
        """
        return self.storage.read_archived_messages(
            chat_id=chat_id,
            start_date=start_date,
            end_date=end_date,
            request_id=request_id,
        )

    def get_tool_call_messages_for_chat(
        self,
        chat_id: str,
        tool_call_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[ToolCallMessage]:
        """
        Get all tool call messages for a specific chat.

        Provides complete tool execution history with arguments, results, and
        normalized responses sent back to the model.

        Args:
            chat_id:      The chat identifier.
            tool_call_id: Optional filter by tool call id.
            start_date:   Optional date filter (inclusive).
            end_date:     Optional date filter (inclusive).

        Returns:
            List of ``ToolCallMessage`` objects ordered by timestamp.
        """
        return self.storage.read_tool_call_messages(
            chat_id=chat_id,
            tool_call_id=tool_call_id,
            start_date=start_date,
            end_date=end_date,
        )

    def get_chat_complete_context(
        self,
        chat_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get complete context for a chat including all messages, requests, and tool calls.

        Provides the most comprehensive view of a chat for audit and debugging,
        combining session metadata, token usage, archived messages, and tool
        execution history.

        Args:
            chat_id:    The chat identifier.
            start_date: Optional date filter for messages/requests.
            end_date:   Optional date filter for messages/requests.

        Returns:
            Dict with keys:
                - chat_session: ChatSessionEvent metadata
                - metrics: ChatMetrics aggregated data
                - llm_requests: List of TokenUsageEvent
                - llm_requests_messages: List of ArchivedMessage (the actual content)
                - tool_calls: List of ToolUsageEvent
                - tool_call_messages: List of ToolCallMessage (with args/results)
                - tool_metrics: Aggregated tool execution metrics by tool name
        """
        chat_sessions = self.storage.read_chat_sessions(chat_id=chat_id)
        if not chat_sessions:
            logger.warning("No chat session found for chat_id=%s", chat_id)
            return {
                "chat_session": None,
                "metrics": ChatMetrics().to_dict(),
                "llm_requests": [],
                "llm_requests_messages": [],
                "tool_calls": [],
                "tool_call_messages": [],
                "tool_metrics": {},
            }

        chat_session = chat_sessions[-1]

        llm_requests = self.storage.read_events(
            chat_id=chat_id,
            start_date=start_date,
            end_date=end_date,
        )

        tool_calls = self.storage.read_tool_events(
            chat_id=chat_id,
            start_date=start_date,
            end_date=end_date,
        )

        archived_messages = self.storage.read_archived_messages(
            chat_id=chat_id,
            start_date=start_date,
            end_date=end_date,
        )

        tool_call_messages = self.storage.read_tool_call_messages(
            chat_id=chat_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Compute metrics
        metrics = ChatMetrics()
        for req in llm_requests:
            metrics.total_input_tokens += req.input_tokens
            metrics.total_output_tokens += req.output_tokens
            metrics.total_tokens += req.total_tokens
            metrics.llm_calls += 1
            metrics.total_llm_duration_seconds += req.duration_seconds
            metrics.total_cxjcoins += req.total_cxjcoins

        for tool in tool_calls:
            metrics.tool_calls += 1
            if tool.success:
                metrics.successful_tool_calls += 1
            else:
                metrics.failed_tool_calls += 1
            metrics.total_tool_duration_seconds += tool.time_taken

        if metrics.tool_calls > 0:
            metrics.avg_tool_duration_seconds = (
                metrics.total_tool_duration_seconds / metrics.tool_calls
            )

        # Compute tool metrics by name
        tool_metrics = self._aggregate_tool_events(
            tool_calls,
            lambda e: e.name
        )

        return {
            "chat_session": chat_session.to_dict(),
            "metrics": metrics.to_dict(),
            "llm_requests": [req.to_dict() for req in llm_requests],
            "llm_requests_messages": [msg.to_dict() for msg in archived_messages],
            "tool_calls": [tool.to_dict() for tool in tool_calls],
            "tool_call_messages": [msg.to_dict() for msg in tool_call_messages],
            "tool_metrics": tool_metrics,
        }

    # ── Tool Usage Query API ───────────────────────────────────────────────────

    def get_tools_by_chat(
        self,
        chat_id: str,
    ) -> List[ToolUsageEvent]:
        """
        Get all tools executed in a specific chat/conversation.

        Args:
            chat_id: The chat/conversation session identifier.

        Returns:
            List of ``ToolUsageEvent`` objects ordered by timestamp.
        """
        return self.storage.read_tool_events(chat_id=chat_id)

    def get_tool_metrics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        tool_name: Optional[str] = None,
        username: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get aggregated tool execution metrics.

        Args:
            start_date:   Inclusive ISO date lower bound.
            end_date:     Inclusive ISO date upper bound.
            tool_name:    Filter by exact tool function name.
            username:     Filter by exact username.
            project_name: Filter by exact project name.

        Returns:
            Dict[tool_name, {calls, successful, failed, total_time_taken, avg_time_taken}]
        """
        events = self.storage.read_tool_events(
            start_date=start_date,
            end_date=end_date,
            tool_name=tool_name,
            username=username,
            project_name=project_name,
        )
        return self._aggregate_tool_events(events, lambda e: e.name)

    def get_tool_usage_by_user(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate tool usage grouped by username.

        Args:
            start_date:   Inclusive ISO date lower bound.
            end_date:     Inclusive ISO date upper bound.
            project_name: Optional project filter.

        Returns:
            Dict[username, {calls, successful, failed, total_time_taken, avg_time_taken}]
        """
        events = self.storage.read_tool_events(
            start_date=start_date,
            end_date=end_date,
            project_name=project_name,
        )
        return self._aggregate_tool_events(events, lambda e: e.username)

    def get_tool_usage_by_project(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate tool usage grouped by project name.

        Args:
            start_date: Inclusive ISO date lower bound.
            end_date:   Inclusive ISO date upper bound.
            username:   Optional user filter.

        Returns:
            Dict[project_name, {calls, successful, failed, total_time_taken, avg_time_taken}]
        """
        events = self.storage.read_tool_events(
            start_date=start_date,
            end_date=end_date,
            username=username,
        )
        return self._aggregate_tool_events(events, lambda e: e.project_name)

# Made with ❤️ by codx-junior