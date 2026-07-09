import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from codx.junior.analytics.model import TokenUsageEvent, ToolUsageEvent
from codx.junior.analytics.storage import AnalyticsStorage
from codx.junior.globals import ANALYTICS_DATA_PATH

logger = logging.getLogger(__name__)


class Analytics:
    """
    High-level API for recording and querying LLM token usage and tool usage analytics.

    The global analytics path is read from
    ``codx.junior.globals.ANALYTICS_DATA_PATH`` which is sourced from the
    ``CODX_JUNIOR_API_ANALYTICS_DATA_PATH`` environment variable.

    Diagram:
    classDiagram
        class Analytics {
            +AnalyticsStorage storage
            +record_token_usage(username, project_name, project_id, model, provider, input_tokens, output_tokens, duration_seconds, session_id, tags, k_tokens_cxjcoins)
            +record_tool_usage(name, username, project_name, project_id, time_taken, success, error_message, chat_id, request_id)
            +get_usage_by_user(start_date, end_date) Dict
            +get_usage_by_project(start_date, end_date) Dict
            +get_usage_by_model(start_date, end_date) Dict
            +get_daily_usage(start_date, end_date, username, project_name, grouping) List
            +get_total_usage(start_date, end_date, username, project_name) Dict
            +list_available_dates() List[str]
            +get_tools_by_chat(chat_id) List
            +get_tool_metrics(start_date, end_date, tool_name, username, project_name) Dict
            +get_tool_usage_by_user(start_date, end_date, project_name) Dict
            +get_tool_usage_by_project(start_date, end_date, username) Dict
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
        tokens_from_provider: bool = False
    ) -> TokenUsageEvent:
        """
        Record a single LLM call's token consumption.

        Args:
            username:           User who triggered the call.
            project_name:       Project context.
            project_id:         Project identifier.
            model:              LLM model name.
            provider:           LLM provider identifier.
            input_tokens:       Prompt token count.
            output_tokens:      Completion token count.
            duration_seconds:   Wall-clock seconds for the full request/response cycle.
            session_id:         Optional conversation/session id.
            tags:               Comma-separated tag string from request headers.
            input_k_tokens_cxjcoins:  Price per 1K tokens in CXJ coins (from AISettings).
            output_k_tokens_cxjcoins:  Price per 1K tokens in CXJ coins (from AISettings).

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
            tokens_from_provider=tokens_from_provider
        )
        self.storage.write(event)
        logger.info(
            "Analytics recorded: user=%s project=%s model=%s in=%d out=%d total=%d "
            "duration=%.2fs cxjcoins=%.4f",
            username,
            project_name,
            model,
            input_tokens,
            output_tokens,
            event.total_tokens,
            duration_seconds,
            event.total_cxjcoins,
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
            "Tool usage recorded: tool=%s user=%s project=%s success=%s time_taken=%.3fs",
            name,
            username,
            project_name,
            success,
            time_taken,
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
            bucket["tokens_from_provider"] = bucket["tokens_from_provider"] or getattr(event, "tokens_from_provider", False)
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
                result[key]["avg_time_taken"] = result[key]["total_time_taken"] / result[key]["calls"]

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
            totals["tokens_from_provider"] = totals["tokens_from_provider"] or getattr(event, "tokens_from_provider", False)
        return totals

    def list_available_dates(self) -> List[str]:
        """
        Return all ISO dates for which analytics data is available.

        Returns:
            Sorted list of ``YYYY-MM-DD`` strings.
        """
        return self.storage.list_available_dates()

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