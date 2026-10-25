import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from codx.junior.api_logs.model import ApiCallEvent
from codx.junior.api_logs.storage import ApiLogStorage
from codx.junior.globals import API_LOGS_DATA_PATH

logger = logging.getLogger(__name__)

# ── Groupings ─────────────────────────────────────────────────────────────────
#: Named bucket sizes understood by :meth:`ApiLogs.get_daily`, in seconds.
#:
#: Sub-minute buckets (``5s`` / ``10s`` / ``30s``) are what the live API
#: monitoring dashboard polls; ``minute`` / ``hour`` / ``day`` answer the
#: historical questions. A grouping is only a bucket SIZE: the router forwards
#: it verbatim and any ``<n>s`` / ``<n>m`` / ``<n>h`` / ``<n>d`` variant is
#: accepted too (see :func:`resolve_grouping_seconds`).
GROUPING_SECONDS: Dict[str, int] = {
    "1s": 1,
    "5s": 5,
    "10s": 10,
    "15s": 15,
    "30s": 30,
    "minute": 60,
    "5m": 300,
    "15m": 900,
    "hour": 3600,
    "day": 86400,
}

#: Bucket used when the caller does not request one.
DEFAULT_GROUPING = "day"

#: Unit suffixes accepted by :func:`resolve_grouping_seconds`.
_UNIT_SECONDS: Dict[str, int] = {
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
}

_GROUPING_RE = re.compile(r"^(?P<value>\d+)\s*(?P<unit>[a-z]+)$")

#: Largest bucket accepted, so a typo cannot ask for a one-bucket chart.
_MAX_GROUPING_SECONDS = 30 * 86400

#: Bucket label formats — the frontend parses these exact shapes.
_SECOND_FORMAT = "%Y-%m-%d %H:%M:%S"
_MINUTE_FORMAT = "%Y-%m-%d %H:%M"
_HOUR_FORMAT = "%Y-%m-%d %H:00"
_DAY_FORMAT = "%Y-%m-%d"


def resolve_grouping_seconds(grouping: Optional[str]) -> int:
    """
    Translate a grouping name into a bucket size in seconds.

    Accepts the named groupings (:data:`GROUPING_SECONDS`) and any
    ``<n>s`` / ``<n>m`` / ``<n>h`` / ``<n>d`` variant, so callers can ask for
    buckets the UI does not offer yet (``'45s'``, ``'2h'``…) without a code
    change. Unknown values fall back to :data:`DEFAULT_GROUPING`: a bad query
    parameter must never break the dashboard.

    Args:
        grouping: Grouping name, e.g. ``'5s'``, ``'10s'``, ``'30s'``,
                  ``'minute'``, ``'hour'``, ``'day'``.

    Returns:
        Bucket size in seconds (``1`` … ``2592000``).
    """
    value = str(grouping or "").strip().lower()
    if not value:
        return GROUPING_SECONDS[DEFAULT_GROUPING]
    if value in GROUPING_SECONDS:
        return GROUPING_SECONDS[value]

    seconds = 0
    match = _GROUPING_RE.match(value)
    if match:
        seconds = int(match.group("value")) * _UNIT_SECONDS.get(match.group("unit"), 0)

    if seconds <= 0:
        logger.warning(
            "resolve_grouping_seconds: unknown grouping %r — falling back to %r",
            grouping,
            DEFAULT_GROUPING,
        )
        return GROUPING_SECONDS[DEFAULT_GROUPING]

    return min(seconds, _MAX_GROUPING_SECONDS)


def _grouping_format(seconds: int) -> str:
    """
    Return the label format matching a bucket size.

    Args:
        seconds: Bucket size in seconds.

    Returns:
        ``strftime`` pattern producing the label the charts expect.
    """
    if seconds < 60:
        return _SECOND_FORMAT
    if seconds < 3600:
        return _MINUTE_FORMAT
    if seconds < 86400:
        return _HOUR_FORMAT
    return _DAY_FORMAT


class ApiLogs:
    """
    High-level API for recording and querying API call performance events.

    The global logs path is read from ``codx.junior.globals.API_LOGS_DATA_PATH``
    which is sourced from the ``CODX_JUNIOR_API_LOGS_DATA_PATH`` environment
    variable.

    Supports:
    - Recording every HTTP call duration, status and context
    - Aggregated summaries (calls, error rate, avg/min/max/p95 durations)
    - Grouping by endpoint, status code, user and project
    - Time-series aggregation with configurable buckets (1 s … day)
    - Slowest calls and failed calls listings

    Diagram:
    classDiagram
        class ApiLogs {
            +ApiLogStorage storage
            +record(...)
            +get_summary(...)
            +get_daily(...)
            +get_by_endpoint(...)
            +get_by_status(...)
            +get_by_user(...)
            +get_by_project(...)
            +get_slowest(...)
            +get_errors(...)
            +list_available_dates()
        }
    """

    def __init__(self, logs_path: str = API_LOGS_DATA_PATH):
        """
        Args:
            logs_path: Global directory for API performance storage. Pass
                       ``codx.junior.globals.API_LOGS_DATA_PATH`` here.
        """
        self.storage = ApiLogStorage(logs_path=logs_path)

    # ── Write ───────────────────────────────────────────────────────────────────

    def record(
        self,
        *,
        path: str,
        method: str,
        status_code: int,
        duration_seconds: float,
        endpoint: str = "",
        request_id: Optional[str] = None,
        username: str = "",
        project_name: str = "",
        project_id: str = "",
        session_id: Optional[str] = None,
        client_ip: str = "",
        query_string: str = "",
        request_size_bytes: int = 0,
        response_size_bytes: int = 0,
        error: Optional[str] = None,
    ) -> ApiCallEvent:
        """
        Record a single API call performance event.

        Args:
            path:                Request path (route template when available).
            method:              HTTP method.
            status_code:         Response status code.
            duration_seconds:    Wall-clock seconds to process the request.
            endpoint:            Matched route name, when available.
            request_id:          Unique request id (x-request-id header).
            username:            Authenticated user (empty when anonymous).
            project_name:        Project context name.
            project_id:          Project identifier.
            session_id:          Socket/session id (x-sid header).
            client_ip:           Client IP address.
            query_string:        Raw query string.
            request_size_bytes:  Request body size in bytes.
            response_size_bytes: Response body size in bytes.
            error:               Error message if the request failed.

        Returns:
            The persisted ``ApiCallEvent``.
        """
        event = ApiCallEvent(
            path=path,
            method=method,
            status_code=status_code,
            duration_seconds=duration_seconds,
            endpoint=endpoint,
            request_id=request_id,
            username=username,
            project_name=project_name,
            project_id=project_id,
            session_id=session_id,
            client_ip=client_ip,
            query_string=query_string,
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
            error=error,
        )
        self.storage.write(event)
        logger.debug(
            "ApiLogs recorded: %s %s status=%s duration=%.3fs user=%s",
            method,
            path,
            status_code,
            duration_seconds,
            username,
        )
        return event

    # ── Query helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _percentile(values: List[float], pct: float) -> float:
        """
        Compute the ``pct`` percentile (0..1) of a list of durations.

        Args:
            values: List of duration values.
            pct:    Percentile as a fraction in [0, 1] (e.g. 0.95 for p95).

        Returns:
            The interpolated percentile value, or 0.0 when the list is empty.
        """
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * pct
        f = int(k)
        c = min(f + 1, len(sorted_vals) - 1)
        if f == c:
            return sorted_vals[f]
        return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)

    @staticmethod
    def _summarize(events: List[ApiCallEvent]) -> Dict[str, Any]:
        """
        Compute aggregate statistics for a list of events.

        Returns:
            Dict with keys: calls, errors, error_rate, total_duration_seconds,
                            avg_duration_seconds, min_duration_seconds,
                            max_duration_seconds, p95_duration_seconds.
        """
        total = len(events)
        durations = [e.duration_seconds for e in events]
        errors = sum(1 for e in events if e.error or e.status_code >= 500)
        total_duration = sum(durations)
        return {
            "calls": total,
            "errors": errors,
            "error_rate": (errors / total) if total else 0.0,
            "total_duration_seconds": total_duration,
            "avg_duration_seconds": (total_duration / total) if total else 0.0,
            "min_duration_seconds": min(durations) if durations else 0.0,
            "max_duration_seconds": max(durations) if durations else 0.0,
            "p95_duration_seconds": ApiLogs._percentile(durations, 0.95),
        }

    @staticmethod
    def _aggregate(
        events: List[ApiCallEvent],
        key_fn,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate performance metrics grouped by a key function.

        Args:
            events: Source events.
            key_fn: Callable that extracts the grouping key from an event.

        Returns:
            Dict mapping key → {calls, errors, error_rate, total_duration_seconds,
                                avg_duration_seconds, min_duration_seconds,
                                max_duration_seconds, p95_duration_seconds}.
        """
        buckets: Dict[str, Dict[str, Any]] = {}
        durations_by_key: Dict[str, List[float]] = {}

        for event in events:
            key = key_fn(event)
            if key not in buckets:
                buckets[key] = {
                    "calls": 0,
                    "errors": 0,
                    "error_rate": 0.0,
                    "total_duration_seconds": 0.0,
                    "avg_duration_seconds": 0.0,
                    "min_duration_seconds": 0.0,
                    "max_duration_seconds": 0.0,
                    "p95_duration_seconds": 0.0,
                }
                durations_by_key[key] = []
            bucket = buckets[key]
            bucket["calls"] += 1
            if event.error or event.status_code >= 500:
                bucket["errors"] += 1
            bucket["total_duration_seconds"] += event.duration_seconds
            durations_by_key[key].append(event.duration_seconds)

        for key, bucket in buckets.items():
            durations = durations_by_key[key]
            calls = bucket["calls"]
            if calls > 0:
                bucket["avg_duration_seconds"] = bucket["total_duration_seconds"] / calls
                bucket["error_rate"] = bucket["errors"] / calls
            bucket["min_duration_seconds"] = min(durations) if durations else 0.0
            bucket["max_duration_seconds"] = max(durations) if durations else 0.0
            bucket["p95_duration_seconds"] = ApiLogs._percentile(durations, 0.95)

        return buckets

    @staticmethod
    def _bucket_start(moment: datetime, seconds: int) -> datetime:
        """
        Floor a timestamp (local time) to the start of its bucket.

        Flooring is computed from the START OF THE DAY rather than from the unix
        epoch: epoch alignment only matches the operator's clock when the UTC
        offset is a whole number of buckets (it is not, for instance, in a
        ``+05:30`` timezone).

        Args:
            moment:  Event timestamp (local time).
            seconds: Bucket size in seconds.

        Returns:
            Bucket start as a naive local ``datetime``.
        """
        if seconds >= 86400:
            days = seconds // 86400
            start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
            if days > 1:
                # Ordinal alignment keeps every bucket the same width, whatever
                # the month length.
                ordinal = start.toordinal()
                start = datetime.fromordinal(ordinal - (ordinal % days))
            return start

        day_start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        elapsed = int((moment - day_start).total_seconds())
        return day_start + timedelta(seconds=(elapsed // seconds) * seconds)

    @staticmethod
    def _get_grouping_key_fn(grouping: str):
        """
        Return the key function that maps an event to its time bucket.

        Bucket labels line up with what the operator sees on the clock:

        ============= ==================== ==========================
        grouping      bucket size          label
        ============= ==================== ==========================
        ``1s``        1 s                  ``YYYY-MM-DD HH:MM:SS``
        ``5s``        5 s                  ``YYYY-MM-DD HH:MM:SS``
        ``10s``       10 s                 ``YYYY-MM-DD HH:MM:SS``
        ``15s``       15 s                 ``YYYY-MM-DD HH:MM:SS``
        ``30s``       30 s                 ``YYYY-MM-DD HH:MM:SS``
        ``minute``    1 min                ``YYYY-MM-DD HH:MM``
        ``5m``/``15m`` 5 / 15 min          ``YYYY-MM-DD HH:MM``
        ``hour``      1 h                  ``YYYY-MM-DD HH:00``
        ``day``       1 d                  ``YYYY-MM-DD``
        ============= ==================== ==========================

        Args:
            grouping: Grouping name — one of the keys of
                      :data:`GROUPING_SECONDS`, or any ``<n>s`` / ``<n>m`` /
                      ``<n>h`` / ``<n>d`` variant.

        Returns:
            Callable that extracts the grouping key from an ApiCallEvent.
        """
        seconds = resolve_grouping_seconds(grouping)
        strftime_format = _grouping_format(seconds)

        def key(event: ApiCallEvent) -> str:
            moment = datetime.fromtimestamp(event.timestamp)
            return ApiLogs._bucket_start(moment, seconds).strftime(strftime_format)

        return key

    def _read(self, filters: Dict[str, Any]) -> List[ApiCallEvent]:
        """Read events forwarding every supported filter to storage."""
        return self.storage.read_events(
            start_date=filters.get("start_date"),
            end_date=filters.get("end_date"),
            path=filters.get("path"),
            method=filters.get("method"),
            status_code=filters.get("status_code"),
            username=filters.get("username"),
            project_name=filters.get("project_name"),
            project_id=filters.get("project_id"),
            min_duration_seconds=filters.get("min_duration_seconds"),
            errors_only=filters.get("errors_only", False),
        )

    # ── Public query API ────────────────────────────────────────────────────────

    def list_available_dates(self) -> List[str]:
        """
        Return all ISO dates for which API performance data is available.

        Returns:
            Sorted list of ``YYYY-MM-DD`` strings.
        """
        return self.storage.list_available_dates()

    def get_summary(self, **filters) -> Dict[str, Any]:
        """
        Return aggregate statistics across all filtered events.

        Args:
            **filters: start_date, end_date, path, method, status_code, username,
                       project_name, project_id, min_duration_seconds, errors_only.

        Returns:
            Dict with keys: calls, errors, error_rate, total_duration_seconds,
                            avg_duration_seconds, min_duration_seconds,
                            max_duration_seconds, p95_duration_seconds.
        """
        events = self._read(filters)
        return ApiLogs._summarize(events)

    def get_daily(self, grouping: str = DEFAULT_GROUPING, **filters) -> List[Dict[str, Any]]:
        """
        Return per-period aggregated metrics with configurable bucketing.

        Only buckets that actually contain calls are returned: the dashboard
        draws the gaps itself, and omitting them keeps a 24 h / 10 s query from
        shipping thousands of empty rows.

        Args:
            grouping:  Bucket size — ``'1s'``, ``'5s'``, ``'10s'``, ``'15s'``,
                       ``'30s'``, ``'minute'``, ``'5m'``, ``'15m'``, ``'hour'``
                       or ``'day'`` (default). Any ``<n>s`` / ``<n>m`` /
                       ``<n>h`` / ``<n>d`` variant is accepted as well; unknown
                       values fall back to ``'day'``.
            **filters: Same filters as ``get_summary``.

        Returns:
            List of dicts [{period, calls, errors, ...}] ordered by period
            ascending.
        """
        events = self._read(filters)
        key_fn = self._get_grouping_key_fn(grouping)
        aggregated = ApiLogs._aggregate(events, key_fn)
        return [
            {"period": period, **bucket}
            for period, bucket in sorted(aggregated.items())
        ]

    def get_by_endpoint(self, **filters) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate metrics grouped by request path (endpoint template).

        Args:
            **filters: Same filters as ``get_summary``.

        Returns:
            Dict[path, {calls, errors, error_rate, durations...}]
        """
        events = self._read(filters)
        return ApiLogs._aggregate(events, lambda e: e.path)

    def get_by_status(self, **filters) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate metrics grouped by HTTP status code.

        Args:
            **filters: Same filters as ``get_summary``.

        Returns:
            Dict[status_code(str), {calls, errors, error_rate, durations...}]
        """
        events = self._read(filters)
        return ApiLogs._aggregate(events, lambda e: str(e.status_code))

    def get_by_user(self, **filters) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate metrics grouped by username (``anonymous`` when empty).

        Args:
            **filters: Same filters as ``get_summary``.

        Returns:
            Dict[username, {calls, errors, error_rate, durations...}]
        """
        events = self._read(filters)
        return ApiLogs._aggregate(events, lambda e: e.username or "anonymous")

    def get_by_project(self, **filters) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate metrics grouped by project name (``unknown`` when empty).

        Args:
            **filters: Same filters as ``get_summary``.

        Returns:
            Dict[project_name, {calls, errors, error_rate, durations...}]
        """
        events = self._read(filters)
        return ApiLogs._aggregate(events, lambda e: e.project_name or "unknown")

    def get_slowest(self, limit: int = 20, **filters) -> List[Dict[str, Any]]:
        """
        Return the slowest calls, ordered by duration descending.

        Args:
            limit:     Maximum number of calls to return.
            **filters: Same filters as ``get_summary``.

        Returns:
            List of serialized ``ApiCallEvent`` dicts.
        """
        events = self._read(filters)
        events.sort(key=lambda e: e.duration_seconds, reverse=True)
        return [e.to_dict() for e in events[:limit]]

    def get_errors(self, limit: int = 100, **filters) -> List[Dict[str, Any]]:
        """
        Return failed calls (error or status >= 500), newest first.

        Args:
            limit:     Maximum number of calls to return.
            **filters: Same filters as ``get_summary``.

        Returns:
            List of serialized ``ApiCallEvent`` dicts.
        """
        filters = {**filters, "errors_only": True}
        events = self._read(filters)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in events[:limit]]


# Made with ❤️ by codx-junior