import logging
from typing import Any, Dict, List, Optional

from codx.junior.analytics.model import TokenUsageEvent
from codx.junior.analytics.storage import AnalyticsStorage
from codx.junior.globals import ANALYTICS_DATA_PATH

logger = logging.getLogger(__name__)


class Analytics:
    """
    High-level API for recording and querying LLM token usage analytics.

    The global analytics path is read from
    ``codx.junior.globals.ANALYTICS_DATA_PATH`` which is sourced from the
    ``CODX_JUNIOR_API_ANALYTICS_DATA_PATH`` environment variable.

    Diagram:
    classDiagram
        class Analytics {
            +AnalyticsStorage storage
            +record_token_usage(username, project_name, project_id, model, provider, input_tokens, output_tokens, duration_seconds, session_id, tags, k_tokens_cxjcoins)
            +get_usage_by_user(start_date, end_date) Dict
            +get_usage_by_project(start_date, end_date) Dict
            +get_usage_by_model(start_date, end_date) Dict
            +get_daily_usage(start_date, end_date, username, project_name) List
            +get_total_usage(start_date, end_date, username, project_name) Dict
            +list_available_dates() List[str]
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
        request_id: str = None
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
            request_id=request_id
            # total_cxjcoins is computed automatically in __post_init__
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
                                total_duration_seconds, total_cxjcoins}.
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
                }
            bucket = result[key]
            bucket["input_tokens"] += event.input_tokens
            bucket["output_tokens"] += event.output_tokens
            bucket["total_tokens"] += event.total_tokens
            bucket["calls"] += 1
            bucket["total_duration_seconds"] += event.duration_seconds
            bucket["total_cxjcoins"] += event.total_cxjcoins
        return result

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
                            total_duration_seconds, total_cxjcoins}]
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
                                total_duration_seconds, total_cxjcoins}]
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
                         total_duration_seconds, total_cxjcoins}]
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
    ) -> List[Dict[str, Any]]:
        """
        Return per-day aggregated token usage.

        Args:
            start_date:   Inclusive ISO date lower bound.
            end_date:     Inclusive ISO date upper bound.
            username:     Optional user filter.
            project_name: Optional project filter.

        Returns:
            List of dicts [{date, input_tokens, output_tokens, total_tokens, calls,
                            total_duration_seconds, total_cxjcoins}]
            ordered by date ascending.
        """
        events = self.storage.read_events(
            start_date=start_date,
            end_date=end_date,
            username=username,
            project_name=project_name,
        )
        aggregated = self._aggregate(events, lambda e: e.iso_date)
        return [
            {"date": date, **counts}
            for date, counts in sorted(aggregated.items())
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
                            total_duration_seconds, total_cxjcoins.
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
        }
        for event in events:
            totals["input_tokens"] += event.input_tokens
            totals["output_tokens"] += event.output_tokens
            totals["total_tokens"] += event.total_tokens
            totals["calls"] += 1
            totals["total_duration_seconds"] += event.duration_seconds
            totals["total_cxjcoins"] += event.total_cxjcoins
        return totals

    def list_available_dates(self) -> List[str]:
        """
        Return all ISO dates for which analytics data is available.

        Returns:
            Sorted list of ``YYYY-MM-DD`` strings.
        """
        return self.storage.list_available_dates()