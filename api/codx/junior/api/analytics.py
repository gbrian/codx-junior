"""
Analytics router – token usage endpoints.

User-scoped endpoints return data filtered to the authenticated user.
Admin-only endpoints return data across all users and require the ``admin``
role (enforced via the ``require_admin`` dependency).

Route layout
------------
GET /api/analytics/me                      – today's and current month's usage (own data)
GET /api/analytics/dates                   – list available dates (own data)
GET /api/analytics/total                   – total usage (own data)
GET /api/analytics/daily                   – daily breakdown (own data)
GET /api/analytics/by-model                – usage grouped by model (own data)

GET /api/analytics/admin/dates             – list available dates (all users)
GET /api/analytics/admin/total             – total usage (all users)
GET /api/analytics/admin/daily             – daily breakdown (all users)
GET /api/analytics/admin/by-user           – usage grouped by user (admin)
GET /api/analytics/admin/by-project        – usage grouped by project (admin)
GET /api/analytics/admin/by-model          – usage grouped by model (admin)

GET /api/analytics/admin/pricing           – list providers+models with pricing info (admin)
PUT /api/analytics/admin/pricing/provider/{provider_name}  – update provider pricing (admin)
PUT /api/analytics/admin/pricing/model/{provider_name}/{model_name} – update model pricing (admin)
POST /api/analytics/admin/pricing/recalculate – rewrite historical events with new pricing (admin)

ENRICHED ENDPOINTS (Chat-aware Analytics - Admin Only)
──────────────────────────────────────────────────────
GET /api/analytics/admin/chat-sessions     – list all chat sessions with metrics (admin)
GET /api/analytics/admin/chat-sessions/{chat_id} – get specific chat with full context (admin)
GET /api/analytics/admin/chat-sessions/{chat_id}/messages – get archived and tool call messages (admin)
GET /api/analytics/admin/chat-sessions/{chat_id}/complete-context – get complete context (admin)

DECISION MODEL ANALYTICS ENDPOINTS
──────────────────────────────────
GET  /api/analytics/decisions              – decision-model events (own data)
GET  /api/analytics/decisions/metrics      – aggregated decision metrics (own data)
GET  /api/analytics/admin/decisions        – decision-model events (all users)
POST /api/analytics/admin/decisions/search – search decision-model events (all users)
GET  /api/analytics/admin/decisions/metrics – aggregated decision metrics (all users)
GET  /api/analytics/admin/chat-sessions/{chat_id}/decisions – decisions for a chat (admin)

DECISION MODEL LOGS ENDPOINTS
─────────────────────────────
GET  /api/analytics/decision-model-logs               – decision-model events rendered as log
                                                        records (own data)
GET  /api/analytics/decision-model-logs/{log_id}      – single decision-model log (own data)
GET  /api/analytics/admin/decision-model-logs         – decision-model events rendered as log
                                                        records (all users)
GET  /api/analytics/admin/decision-model-logs/{log_id} – single decision-model log (all users)

The ``/decision-model-logs`` routes expose the decision events in the
``{records, models, summary}`` shape log viewers expect, so clients that ask
for decision-model logs get the same payload from every deployment. Extra
query parameters sent by those clients (``codx_path``, …) are ignored; the
decision events are already scoped by ``project_name`` / ``project_id``.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from codx.junior.api import require_admin, get_current_session
from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.globals import ANALYTICS_DATA_PATH
from codx.junior.analytics import Analytics
from codx.junior.analytics.model import (
    ChatContextSummary,
    ChatMetrics,
    EnrichedTokenUsageEvent,
    EnrichedToolUsageEvent,
)
from codx.junior.analytics.decision_model import (
    DecisionModelEventList,
    DecisionModelMetrics,
    DecisionModelQuery,
)
from codx.junior.global_settings import (
    read_global_settings,
    write_global_settings
)
from codx.junior.model.ai_model import AIModelPrice

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# ── Date format constant ───────────────────────────────────────────────────────

DATE_FORMAT = "%Y-%m-%d"

# ── Shared Analytics instance ──────────────────────────────────────────────────

_analytics: Optional[Analytics] = None


def _get_analytics() -> Analytics:
    """Return (or lazily create) the shared Analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = Analytics(analytics_path=ANALYTICS_DATA_PATH)
    return _analytics


# ── Helpers ────────────────────────────────────────────────────────────────────


def _get_model_price(provider, ai_model_name: str) -> Dict[str, Optional[float]]:
    """
    Resolve pricing for a model from provider.price_list, falling back to
    provider-level defaults.

    Args:
        provider: AIProvider instance.
        ai_model_name: The provider-side model name (AIModel.ai_model or AIModel.name).

    Returns:
        Dict with keys ``input_k_tokens_cxjcoins`` and ``output_k_tokens_cxjcoins``.
    """
    price_entry = next(
        (p for p in (provider.price_list or []) if p.model_name == ai_model_name),
        None,
    )
    if price_entry is not None:
        return {
            "input_k_tokens_cxjcoins": price_entry.input_price_per_1k_tokens,
            "output_k_tokens_cxjcoins": price_entry.output_price_per_1k_tokens,
        }
    # Fall back to provider-level defaults
    return {
        "input_k_tokens_cxjcoins": provider.input_k_tokens_cxjcoins,
        "output_k_tokens_cxjcoins": provider.output_k_tokens_cxjcoins,
    }


# KEPT: Helper to enrich token events with chat session data
def _enrich_token_event(analytics: Analytics, token_event) -> EnrichedTokenUsageEvent:
    """
    Enrich a TokenUsageEvent with associated ChatSessionEvent if chat_id is present.

    Args:
        analytics: Analytics instance for querying chat sessions.
        token_event: TokenUsageEvent to enrich.

    Returns:
        EnrichedTokenUsageEvent with optional chat_session.
    """
    chat_session = None
    if token_event.chat_id:
        chat_sessions = analytics.storage.read_chat_sessions(chat_id=token_event.chat_id)
        if chat_sessions:
            # Use the most recent session event for this chat
            chat_session = chat_sessions[-1]

    return EnrichedTokenUsageEvent(
        token_event=token_event,
        chat_session=chat_session,
    )


# KEPT: Helper to enrich tool events with chat session data
def _enrich_tool_event(analytics: Analytics, tool_event) -> EnrichedToolUsageEvent:
    """
    Enrich a ToolUsageEvent with associated ChatSessionEvent if chat_id is present.

    Args:
        analytics: Analytics instance for querying chat sessions.
        tool_event: ToolUsageEvent to enrich.

    Returns:
        EnrichedToolUsageEvent with optional chat_session.
    """
    chat_session = None
    if tool_event.chat_id:
        chat_sessions = analytics.storage.read_chat_sessions(chat_id=tool_event.chat_id)
        if chat_sessions:
            # Use the most recent session event for this chat
            chat_session = chat_sessions[-1]

    return EnrichedToolUsageEvent(
        tool_event=tool_event,
        chat_session=chat_session,
    )


# KEPT: Helper to compute aggregated metrics for a chat session
def _compute_chat_metrics(
    analytics: Analytics,
    chat_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> ChatMetrics:
    """
    Compute aggregated token and tool metrics for a specific chat session.

    Args:
        analytics: Analytics instance.
        chat_id: The chat identifier.
        start_date: Optional date filter for token/tool events.
        end_date: Optional date filter for token/tool events.

    Returns:
        ChatMetrics with aggregated consumption and execution statistics.
    """
    metrics = ChatMetrics()

    # Fetch and aggregate LLM requests
    llm_requests = analytics.storage.read_events(
        chat_id=chat_id,
        start_date=start_date,
        end_date=end_date,
    )
    for req in llm_requests:
        metrics.total_input_tokens += req.input_tokens
        metrics.total_output_tokens += req.output_tokens
        metrics.total_tokens += req.total_tokens
        metrics.llm_calls += 1
        metrics.total_llm_duration_seconds += req.duration_seconds
        metrics.total_cxjcoins += req.total_cxjcoins

    # Fetch and aggregate tool calls
    tool_calls = analytics.storage.read_tool_events(
        chat_id=chat_id,
        start_date=start_date,
        end_date=end_date,
    )
    for tool in tool_calls:
        metrics.tool_calls += 1
        if tool.success:
            metrics.successful_tool_calls += 1
        else:
            metrics.failed_tool_calls += 1
        metrics.total_tool_duration_seconds += tool.time_taken

    # Compute average tool duration
    if metrics.tool_calls > 0:
        metrics.avg_tool_duration_seconds = (
            metrics.total_tool_duration_seconds / metrics.tool_calls
        )

    return metrics


# KEPT: Helper to compute detailed tool metrics by tool name
def _compute_tool_metrics_by_name(
    tool_calls: List,
) -> Dict[str, Dict[str, Any]]:
    """
    Compute detailed execution metrics for tools grouped by tool name.

    Analyzes individual tool executions to provide insights into success rates,
    performance, and error patterns per tool.

    Args:
        tool_calls: List of ToolUsageEvent objects.

    Returns:
        Dict mapping tool_name → {
            total_calls, successful, failed, success_rate,
            total_duration, avg_duration, min_duration, max_duration,
            error_details
        }
    """
    tool_metrics: Dict[str, Dict[str, Any]] = {}

    for tool in tool_calls:
        if tool.name not in tool_metrics:
            tool_metrics[tool.name] = {
                "total_calls": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0,
                "error_details": [],
            }

        metrics = tool_metrics[tool.name]
        metrics["total_calls"] += 1

        if tool.success:
            metrics["successful"] += 1
        else:
            metrics["failed"] += 1
            if tool.error_message:
                metrics["error_details"].append({
                    "timestamp": tool.timestamp,
                    "error_message": tool.error_message,
                })

        metrics["total_duration"] += tool.time_taken
        metrics["min_duration"] = min(metrics["min_duration"], tool.time_taken)
        metrics["max_duration"] = max(metrics["max_duration"], tool.time_taken)

    # Compute derived metrics
    for tool_name in tool_metrics:
        m = tool_metrics[tool_name]
        if m["total_calls"] > 0:
            m["avg_duration"] = m["total_duration"] / m["total_calls"]
            m["success_rate"] = (m["successful"] / m["total_calls"]) * 100.0

        # Clean up infinity values
        if m["min_duration"] == float('inf'):
            m["min_duration"] = 0.0

    return tool_metrics


# ── Pricing request models ─────────────────────────────────────────────────────


class PricingUpdateRequest(BaseModel):
    input_k_tokens_cxjcoins: Optional[float] = None
    output_k_tokens_cxjcoins: Optional[float] = None


class RecalculateRequest(BaseModel):
    provider: str
    model: str
    start_date: str
    end_date: str
    input_k_tokens_cxjcoins: float
    output_k_tokens_cxjcoins: float


# ── Decision-model log models & helpers ────────────────────────────────────────
#
# Decision-model events (see codx.junior.analytics.decision_model) are stored
# as one record per model invocation. Log viewers, however, consume a flatter
# shape – ``{records, models, summary}`` – so the ``/decision-model-logs``
# endpoints render the events as log records. Everything below is that
# rendering layer: the response models and the event → record mapper.

# Characters per token used to approximate token usage when an event does not
# carry explicit counters (the ``token_stats`` fields are named *estimated* for
# that reason).
CHARS_PER_TOKEN = 4


def _estimate_tokens(text: Optional[str]) -> int:
    """Approximate the token count of a text block (``len(text) // 4``)."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def _event_field(event, name: str, default: Any = None) -> Any:
    """
    Read a field from a stored decision event.

    Storage may hand back pydantic models (the usual case) or plain dicts, so
    both are supported. ``None`` always falls back to ``default``.
    """
    value = event.get(name) if isinstance(event, dict) else getattr(event, name, None)
    return default if value is None else value


class DecisionModelLogRecord(BaseModel):
    """
    A single decision-model invocation, rendered as a log record.

    Mirrors the shape produced by the AI-log endpoints so a single log viewer
    can render both: ``prompt`` is the state the model reasoned about,
    ``decision`` its answer, ``reasoning`` the human readable explanation.
    """

    id: str = Field(default="", description="Decision event id")
    timestamp: float = Field(default=0.0, description="Unix timestamp (UTC)")
    direction: str = Field(
        default="response", description="'request' or 'response'"
    )
    provider: str = Field(
        default="", description="Engine that produced the decision"
    )
    model: str = Field(default="", description="Decision model name/variant")
    decision: str = Field(default="", description="Chosen answer")
    reasoning: str = Field(default="", description="Human readable explanation")
    prompt: str = Field(
        default="", description="State the model reasoned about"
    )
    tags: str = Field(default="", description="Comma separated tags")
    session_id: Optional[str] = Field(
        default=None, description="Session/chat the decision belongs to"
    )
    input_tokens: int = Field(default=0, description="Prompt tokens (estimated)")
    output_tokens: int = Field(default=0, description="Answer tokens (estimated)")
    duration_seconds: float = Field(
        default=0.0, description="Wall-clock seconds for the decision call"
    )
    cached: bool = Field(default=False, description="Served from cache")
    error: bool = Field(default=False, description="The call failed")
    error_message: Optional[str] = Field(
        default=None, description="Failure message when ``error`` is set"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Decision metadata (type, probs, confidence, abstention…)",
    )


class DecisionModelLogsSummary(BaseModel):
    """Aggregated statistics for the matching decision-model log records."""

    total_log_records: int = Field(default=0, description="Matching records")
    total_requests: int = Field(
        default=0, description="Decision calls (one per record)"
    )
    total_responses: int = Field(
        default=0, description="Calls that produced an answer"
    )
    total_duration_seconds: float = Field(
        default=0.0, description="Sum of all decision durations"
    )
    average_request_duration_seconds: float = Field(
        default=0.0, description="Mean decision duration"
    )
    token_stats: Dict[str, int] = Field(
        default_factory=dict,
        description=(
            "total_estimated_input_tokens / total_estimated_output_tokens / "
            "total_estimated_tokens"
        ),
    )


class DecisionModelLogsResponse(BaseModel):
    """
    Client response model for ``/decision-model-logs``.

    ``records`` holds the requested page (newest first, ordered by timestamp),
    ``total`` the full match count before pagination and ``models`` every model
    seen in the *unpaginated* result so clients can build a model filter.
    """

    records: List[DecisionModelLogRecord] = Field(
        default_factory=list, description="Decision log records (newest first)"
    )
    models: List[str] = Field(
        default_factory=list, description="Distinct decision models found"
    )
    summary: DecisionModelLogsSummary = Field(
        default_factory=DecisionModelLogsSummary,
        description="Aggregated statistics for the matching records",
    )
    total: int = Field(
        default=0, description="Total matching records (before pagination)"
    )
    limit: Optional[int] = Field(default=None, description="Applied limit")
    offset: int = Field(default=0, description="Applied offset")


def _decision_event_to_log_record(event) -> DecisionModelLogRecord:
    """
    Render a stored decision event as a log record.

    Token counters are taken from the event ``details`` when the engine
    recorded them and approximated from the text lengths otherwise.
    """
    details = dict(_event_field(event, "details", {}) or {})

    choice = _event_field(event, "choice", "") or ""
    if not choice and _event_field(event, "choices", {}):
        choice = ", ".join(
            f"{key}: {value}" for key, value in _event_field(event, "choices", {}).items()
        )
    if not choice and _event_field(event, "abstained", False):
        choice = "(abstained)"

    state = _event_field(event, "state", "") or ""

    input_tokens = int(details.get("input_tokens") or 0) or _estimate_tokens(state)
    output_tokens = int(details.get("output_tokens") or 0) or _estimate_tokens(choice)

    return DecisionModelLogRecord(
        id=_event_field(event, "event_id", "") or "",
        timestamp=float(_event_field(event, "timestamp", 0.0) or 0.0),
        direction="response",
        provider=_event_field(event, "engine", "") or "",
        model=_event_field(event, "model", "") or "",
        decision=choice,
        reasoning=_event_field(event, "reason", "") or "",
        prompt=state,
        tags=_event_field(event, "tags", "") or "",
        session_id=_event_field(event, "session_id", None)
                    or _event_field(event, "chat_id", None),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_seconds=float(_event_field(event, "duration_seconds", 0.0) or 0.0),
        cached=bool(details.get("cached", False)),
        error=not bool(_event_field(event, "success", True)),
        error_message=_event_field(event, "error", None),
        details={
            "decision_type": _event_field(event, "decision_type", ""),
            "engine": _event_field(event, "engine", ""),
            "questions": _event_field(event, "questions", []),
            "choices": _event_field(event, "choices", {}),
            "probs": _event_field(event, "probs", {}),
            "confidence": _event_field(event, "confidence", None),
            "abstained": _event_field(event, "abstained", False),
            "chat_id": _event_field(event, "chat_id", None),
            "request_id": _event_field(event, "request_id", None),
            "username": _event_field(event, "username", ""),
            "project_name": _event_field(event, "project_name", ""),
            "project_id": _event_field(event, "project_id", ""),
            **details,
        },
    )


def _build_decision_logs_response(
    events: List,
    limit: Optional[int] = None,
    offset: int = 0,
    direction: Optional[str] = None,
) -> DecisionModelLogsResponse:
    """
    Build a paginated ``{records, models, summary}`` payload from raw events.

    Records are sorted newest first (this feeds a log viewer) and the summary
    is computed over the *whole* filtered set, not just the requested page.
    """
    records = [_decision_event_to_log_record(event) for event in (events or [])]
    records.sort(key=lambda record: record.timestamp or 0.0, reverse=True)

    if direction:
        wanted = direction.strip().lower()
        records = [record for record in records if record.direction == wanted]

    total = len(records)
    total_duration = sum(record.duration_seconds or 0.0 for record in records)
    input_tokens = sum(record.input_tokens or 0 for record in records)
    output_tokens = sum(record.output_tokens or 0 for record in records)

    summary = DecisionModelLogsSummary(
        total_log_records=total,
        total_requests=total,
        total_responses=sum(1 for record in records if not record.error),
        total_duration_seconds=round(total_duration, 3),
        average_request_duration_seconds=(
            round(total_duration / total, 3) if total else 0.0
        ),
        token_stats={
            "total_estimated_input_tokens": input_tokens,
            "total_estimated_output_tokens": output_tokens,
            "total_estimated_tokens": input_tokens + output_tokens,
        },
    )

    offset = max(0, offset or 0)
    page = records[offset:] if offset else records
    if limit is not None:
        page = page[:limit]

    return DecisionModelLogsResponse(
        records=page,
        models=sorted({record.model for record in records if record.model}),
        summary=summary,
        total=total,
        limit=limit,
        offset=offset,
    )


def _read_decision_logs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    chat_id: Optional[str] = None,
    decision_type: Optional[str] = None,
    engine: Optional[str] = None,
    model: Optional[str] = None,
    username: Optional[str] = None,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
    success: Optional[bool] = None,
    session_id: Optional[str] = None,
    tags: Optional[str] = None,
    direction: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> DecisionModelLogsResponse:
    """
    Read decision events and render them as a decision-model log payload.

    Filters supported by the storage layer (dates, chat, decision type, engine,
    model, user, project, success) are pushed down to it; ``session_id`` and
    ``tags`` are matched in memory because the storage does not index them
    (``tags`` is a comma separated value and matches any of the requested tags).
    """
    analytics = _get_analytics()
    events = analytics.storage.read_decision_events(
        start_date=start_date,
        end_date=end_date,
        chat_id=chat_id,
        decision_type=decision_type,
        engine=engine,
        model=model,
        username=username,
        project_name=project_name,
        project_id=project_id,
        success=success,
    )

    if session_id:
        events = [
            event for event in events
            if (_event_field(event, "session_id", None)
                or _event_field(event, "chat_id", None)) == session_id
        ]

    if tags:
        wanted_tags = {tag.strip().lower() for tag in tags.split(",") if tag.strip()}
        events = [
            event for event in events
            if wanted_tags.intersection(
                tag.strip().lower()
                for tag in (_event_field(event, "tags", "") or "").split(",")
                if tag.strip()
            )
        ]

    return _build_decision_logs_response(
        events, limit=limit, offset=offset, direction=direction
    )


def _find_decision_log(
    log_id: str, username: Optional[str] = None
) -> Optional[DecisionModelLogRecord]:
    """
    Look up a single decision log by event id.

    Event ids are not indexed, so this scans the stored decision events — it is
    meant for one-off client lookups, not for listing.
    """
    analytics = _get_analytics()
    events = analytics.storage.read_decision_events(username=username)
    for event in events or []:
        if _event_field(event, "event_id", "") == log_id:
            return _decision_event_to_log_record(event)
    return None


# ── User-scoped endpoints ──────────────────────────────────────────────────────


@router.get(
    "/me",
    response_model=Dict[str, Any],
    summary="Current user metrics for today and the current month",
)
def get_my_metrics(
    user: CodxUser = Depends(get_authenticated_user),
) -> Dict[str, Any]:
    """
    Return token usage metrics for the authenticated user scoped to:

    * **today** – usage recorded on the current calendar day.
    * **current_month** – usage recorded from the 1st of the current month
      up to and including today.

    Returns::

        {
            "username": "<username>",
            "today": {
                "date": "YYYY-MM-DD",
                "input_tokens": <int>,
                "output_tokens": <int>,
                "total_tokens": <int>,
                "calls": <int>
            },
            "current_month": {
                "start_date": "YYYY-MM-01",
                "end_date": "YYYY-MM-DD",
                "input_tokens": <int>,
                "output_tokens": <int>,
                "total_tokens": <int>,
                "calls": <int>
            }
        }
    """
    analytics = _get_analytics()

    today: date = datetime.utcnow().date()
    today_str: str = today.strftime(DATE_FORMAT)

    # First day of the current month
    month_start: date = today.replace(day=1)
    month_start_str: str = month_start.strftime(DATE_FORMAT)

    logger.debug(
        "Fetching metrics for user %s: today=%s, month_start=%s",
        user.username,
        today_str,
        month_start_str,
    )

    today_usage: Dict[str, Any] = analytics.get_total_usage(
        start_date=today_str,
        end_date=today_str,
        username=user.username,
    )

    month_usage: Dict[str, Any] = analytics.get_total_usage(
        start_date=month_start_str,
        end_date=today_str,
        username=user.username,
    )

    return {
        "username": user.username,
        "today": {
            "date": today_str,
            **today_usage,
        },
        "current_month": {
            "start_date": month_start_str,
            "end_date": today_str,
            **month_usage,
        },
    }


@router.get("/dates", response_model=List[str], summary="List dates with recorded usage (own data)")
def list_dates(
    user: CodxUser = Depends(get_authenticated_user),
) -> List[str]:
    """
    Return all ISO dates (``YYYY-MM-DD``) for which the authenticated user
    has recorded token usage.
    """
    analytics = _get_analytics()
    all_dates = analytics.list_available_dates()
    user_dates = []
    for date_str in all_dates:
        events = analytics.storage.read_events(
            start_date=date_str,
            end_date=date_str,
            username=user.username,
        )
        if events:
            user_dates.append(date_str)
    return user_dates


@router.get("/total", response_model=Dict[str, Any], summary="Total token usage (own data)")
def get_total(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    user: CodxUser = Depends(get_authenticated_user),
) -> Dict[str, Any]:
    """
    Return total token consumption for the authenticated user.

    Returns:
        ``{input_tokens, output_tokens, total_tokens, calls}``
    """
    analytics = _get_analytics()
    return analytics.get_total_usage(
        start_date=start_date,
        end_date=end_date,
        username=user.username,
        project_name=project_name,
        model=model,
    )


@router.get("/daily", response_model=List[Dict[str, Any]], summary="Daily token usage breakdown (own data)")
def get_daily(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    grouping: str = Query("day", description="Grouping level: minute, hour, or day"),
    user: CodxUser = Depends(get_authenticated_user),
) -> List[Dict[str, Any]]:
    """
    Return per-period aggregated token usage for the authenticated user.

    Args:
        grouping: Time grouping level - 'minute', 'hour', or 'day'. Default: 'day'

    Returns:
        List of ``{period, input_tokens, output_tokens, total_tokens, calls}``
        sorted by period ascending.
    """
    analytics = _get_analytics()
    return analytics.get_daily_usage(
        start_date=start_date,
        end_date=end_date,
        username=user.username,
        project_name=project_name,
        grouping=grouping,
    )


@router.get("/by-model", response_model=Dict[str, Dict[str, Any]], summary="Usage by model (own data)")
def get_by_model(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    user: CodxUser = Depends(get_authenticated_user),
) -> Dict[str, Dict[str, Any]]:
    """
    Return token usage aggregated by model name for the authenticated user.

    Returns:
        ``{model_name: {input_tokens, output_tokens, total_tokens, calls}}``
    """
    analytics = _get_analytics()
    return analytics.get_usage_by_model(
        start_date=start_date,
        end_date=end_date,
        username=user.username,
        project_name=project_name,
    )


# ── Decision-model analytics (own data) ────────────────────────────────────────


@router.get(
    "/decisions",
    response_model=DecisionModelEventList,
    summary="Decision-model events recorded for the current user",
)
def get_my_decisions(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    chat_id: Optional[str] = Query(None, description="Filter by chat id"),
    decision_type: Optional[str] = Query(None, description="Filter by decision type"),
    engine: Optional[str] = Query(None, description="Filter by engine"),
    model: Optional[str] = Query(None, description="Filter by decision model"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    success: Optional[bool] = Query(None, description="Filter by success flag"),
    limit: Optional[int] = Query(None, description="Max events to return"),
    offset: int = Query(0, description="Number of events to skip"),
    user: CodxUser = Depends(get_authenticated_user),
) -> DecisionModelEventList:
    """
    Return decision-model analytics events recorded for the authenticated user.

    A decision-model event is one invocation of a typed decider (e.g. the
    ``vegaml`` engine used to organize chats): the state it reasoned about, its
    answers, calibrated probabilities, confidence and whether it abstained.

    Returns:
        ``DecisionModelEventList`` (paginated, ordered by timestamp).
    """
    analytics = _get_analytics()
    events = analytics.storage.read_decision_events(
        start_date=start_date,
        end_date=end_date,
        chat_id=chat_id,
        decision_type=decision_type,
        engine=engine,
        model=model,
        username=user.username,
        project_name=project_name,
        success=success,
    )
    return DecisionModelEventList.from_events(events, limit=limit, offset=offset)


@router.get(
    "/decisions/metrics",
    response_model=DecisionModelMetrics,
    summary="Decision-model metrics for the current user",
)
def get_my_decision_metrics(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    decision_type: Optional[str] = Query(None, description="Filter by decision type"),
    group_by: str = Query("model", description="Grouping key: model, engine, or decision_type"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    user: CodxUser = Depends(get_authenticated_user),
) -> DecisionModelMetrics:
    """
    Return aggregated decision-model metrics for the authenticated user.

    Returns:
        ``DecisionModelMetrics`` with per-group calls, success/abstain counts,
        durations and average confidence.
    """
    analytics = _get_analytics()
    metrics = analytics.get_decision_metrics(
        start_date=start_date,
        end_date=end_date,
        decision_type=decision_type,
        group_by=group_by,
        username=user.username,
        project_name=project_name,
    )
    return DecisionModelMetrics.from_metrics(group_by=group_by, metrics=metrics)


# ── Decision-model logs (own data) ─────────────────────────────────────────────


@router.get(
    "/decision-model-logs",
    response_model=DecisionModelLogsResponse,
    summary="Decision-model logs for the current user",
)
def get_my_decision_model_logs(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    chat_id: Optional[str] = Query(None, description="Filter by chat id"),
    decision_type: Optional[str] = Query(None, description="Filter by decision type"),
    engine: Optional[str] = Query(None, description="Filter by engine"),
    model: Optional[str] = Query(None, description="Filter by decision model"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    project_id: Optional[str] = Query(None, description="Filter by project id"),
    success: Optional[bool] = Query(None, description="Filter by success flag"),
    session_id: Optional[str] = Query(None, description="Filter by session/chat id"),
    tags: Optional[str] = Query(None, description="Comma separated tags to match"),
    direction: Optional[str] = Query(None, description="'request' or 'response'"),
    limit: Optional[int] = Query(None, description="Max records to return"),
    offset: int = Query(0, description="Number of records to skip"),
    user: CodxUser = Depends(get_authenticated_user),
) -> DecisionModelLogsResponse:
    """
    Return the decision-model logs recorded for the authenticated user.

    Same decision events as ``GET /decisions``, but rendered in the
    ``{records, models, summary}`` shape log viewers consume: each record
    exposes the prompt (``state``), the chosen answer, the reasoning, timing,
    (estimated) token usage and failure details.

    Returns:
        ``DecisionModelLogsResponse`` (records newest first, paginated).
    """
    return _read_decision_logs(
        start_date=start_date,
        end_date=end_date,
        chat_id=chat_id,
        decision_type=decision_type,
        engine=engine,
        model=model,
        username=user.username,
        project_name=project_name,
        project_id=project_id,
        success=success,
        session_id=session_id,
        tags=tags,
        direction=direction,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/decision-model-logs/{log_id}",
    response_model=DecisionModelLogRecord,
    summary="Single decision-model log for the current user",
)
def get_my_decision_model_log(
    log_id: str,
    user: CodxUser = Depends(get_authenticated_user),
) -> DecisionModelLogRecord:
    """
    Return the decision-model log with the given (event) id.

    Raises HTTP 404 when no event with that id was recorded for the user.
    """
    record = _find_decision_log(log_id, username=user.username)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Decision log '{log_id}' not found.",
        )
    return record


# ── Admin endpoints ────────────────────────────────────────────────────────────


@router.get(
    "/admin/dates",
    response_model=List[str],
    summary="[Admin] List all dates with recorded usage",
)
def admin_list_dates(
    _: CodxUser = Depends(require_admin),
) -> List[str]:
    """
    Return all ISO dates for which any token usage data is stored.

    Requires admin role.
    """
    return _get_analytics().list_available_dates()


@router.get(
    "/admin/total",
    response_model=Dict[str, Any],
    summary="[Admin] Total token usage across all users",
)
def admin_get_total(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    project_id: Optional[str] = Query(None, description="Filter by project id"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Return global total token consumption with optional filters.

    Requires admin role.

    Returns:
        ``{input_tokens, output_tokens, total_tokens, calls}``
    """
    analytics = _get_analytics()
    return analytics.get_total_usage(
        start_date=start_date,
        end_date=end_date,
        username=username,
        project_name=project_name,
        project_id=project_id,
        model=model,
    )


@router.get(
    "/admin/daily",
    response_model=List[Dict[str, Any]],
    summary="[Admin] Daily token usage breakdown across all users",
)
def admin_get_daily(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    grouping: str = Query("day", description="Grouping level: minute, hour, or day"),
    _: CodxUser = Depends(require_admin),
) -> List[Dict[str, Any]]:
    """
    Return per-period aggregated token usage across all users.

    Args:
        grouping: Time grouping level - 'minute', 'hour', or 'day'. Default: 'day'

    Requires admin role.

    Returns:
        List of ``{period, input_tokens, output_tokens, total_tokens, calls}``
        sorted by period ascending.
    """
    analytics = _get_analytics()
    return analytics.get_daily_usage(
        start_date=start_date,
        end_date=end_date,
        username=username,
        project_name=project_name,
        grouping=grouping,
    )


@router.get(
    "/admin/by-user",
    response_model=Dict[str, Dict[str, Any]],
    summary="[Admin] Usage grouped by user",
)
def admin_get_by_user(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    project_id: Optional[str] = Query(None, description="Filter by project id"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Dict[str, Any]]:
    """
    Return token usage aggregated by username across all users.

    Requires admin role.

    Returns:
        ``{username: {input_tokens, output_tokens, total_tokens, calls}}``
    """
    analytics = _get_analytics()
    return analytics.get_usage_by_user(
        start_date=start_date,
        end_date=end_date,
        project_name=project_name,
        project_id=project_id,
    )


@router.get(
    "/admin/by-project",
    response_model=Dict[str, Dict[str, Any]],
    summary="[Admin] Usage grouped by project",
)
def admin_get_by_project(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    username: Optional[str] = Query(None, description="Filter by username"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Dict[str, Any]]:
    """
    Return token usage aggregated by project name across all users.

    Requires admin role.

    Returns:
        ``{project_name: {input_tokens, output_tokens, total_tokens, calls}}``
    """
    analytics = _get_analytics()
    return analytics.get_usage_by_project(
        start_date=start_date,
        end_date=end_date,
        username=username,
    )


@router.get(
    "/admin/by-model",
    response_model=Dict[str, Dict[str, Any]],
    summary="[Admin] Usage grouped by model",
)
def admin_get_by_model(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Dict[str, Any]]:
    """
    Return token usage aggregated by model name across all users.

    Requires admin role.

    Returns:
        ``{model_name: {input_tokens, output_tokens, total_tokens, calls}}``
    """
    analytics = _get_analytics()
    return analytics.get_usage_by_model(
        start_date=start_date,
        end_date=end_date,
        username=username,
        project_name=project_name,
    )


# ── Admin-scoped enriched endpoints (Chat Analytics - Admin Only) ──────────────


@router.get(
    "/admin/chat-sessions",
    response_model=List[Dict[str, Any]],
    summary="[Admin] List all chat sessions with metrics",
)
def admin_get_chat_sessions(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    project_id: Optional[str] = Query(None, description="Filter by project id"),
    _: CodxUser = Depends(require_admin),
) -> List[Dict[str, Any]]:
    """
    Return all chat sessions across all users with aggregated metrics.

    Enables admin users to analyze chat activity, resource consumption, and
    tool usage across the entire platform. Results can be filtered by date range,
    username, and/or project.

    Each chat session includes:
    - Chat metadata (name, mode, profiles, files, iteration info, etc.)
    - Aggregated metrics (total tokens, LLM calls, tool calls, durations, costs)

    Requires admin role.

    Returns:
        List of ``ChatContextSummary`` objects (as dicts) ordered by chat start time.
    """
    analytics = _get_analytics()

    # Read all chat sessions matching filters
    all_chats = analytics.storage.read_chat_sessions(
        start_date=start_date,
        end_date=end_date,
        username=username,
        project_name=project_name,
        project_id=project_id,
    )

    summaries: List[Dict[str, Any]] = []
    for chat_session in all_chats:
        metrics = _compute_chat_metrics(
            analytics,
            chat_id=chat_session.chat_id,
            start_date=start_date,
            end_date=end_date,
        )

        llm_requests = analytics.storage.read_events(chat_id=chat_session.chat_id)
        tool_calls = analytics.storage.read_tool_events(chat_id=chat_session.chat_id)

        summary = ChatContextSummary(
            chat_session=chat_session,
            metrics=metrics,
            llm_request_count=len(llm_requests),
            tool_call_count=len(tool_calls),
        )
        summaries.append(summary.to_dict())

    logger.debug(
        "Admin retrieved %d chat sessions (filters: username=%s project=%s)",
        len(summaries),
        username,
        project_name,
    )

    return summaries


@router.get(
    "/admin/chat-sessions/{chat_id}",
    response_model=Dict[str, Any],
    summary="[Admin] Get chat with full context including detailed tool information",
)
def admin_get_chat_context(
    chat_id: str,
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Retrieve a complete chat session with all associated LLM requests and detailed tool information.

    Admin endpoint: provides visibility into any chat session for audit and analysis.
    Enables reconstruction of the full request-response chain and comprehensive tool execution
    history for a specific chat.

    Returns:
        Dict with:
            - chat_session: ChatSessionEvent metadata
            - metrics: ChatMetrics aggregated from linked requests/tools
            - llm_requests: List of TokenUsageEvent (enriched with chat_session)
            - tool_calls: List of ToolUsageEvent (enriched with chat_session)
            - tool_metrics: Dict with aggregated metrics per tool name including:
                * total_calls, successful, failed, success_rate
                * total_duration, avg_duration, min_duration, max_duration
                * error_details for failed executions

    Requires admin role.

    Raises:
        HTTP 404 if chat not found.
    """
    analytics = _get_analytics()

    # Fetch chat session
    chat_sessions = analytics.storage.read_chat_sessions(chat_id=chat_id)
    if not chat_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Chat '{chat_id}' not found.",
        )

    chat_session = chat_sessions[-1]  # Most recent session event

    # Compute metrics and fetch associated requests/tools
    metrics = _compute_chat_metrics(
        analytics,
        chat_id=chat_id,
        start_date=start_date,
        end_date=end_date,
    )

    llm_requests = analytics.storage.read_events(
        chat_id=chat_id,
        start_date=start_date,
        end_date=end_date,
    )

    tool_calls = analytics.storage.read_tool_events(
        chat_id=chat_id,
        start_date=start_date,
        end_date=end_date,
    )

    # Enrich events with chat session context
    enriched_requests = [_enrich_token_event(analytics, req) for req in llm_requests]
    enriched_tools = [_enrich_tool_event(analytics, tool) for tool in tool_calls]

    # Compute detailed tool metrics
    tool_metrics = _compute_tool_metrics_by_name(tool_calls)

    logger.info(
        "Admin retrieved chat context: chat_id=%s user=%s llm_requests=%d tool_calls=%d "
        "unique_tools=%d",
        chat_id,
        chat_session.username,
        len(enriched_requests),
        len(enriched_tools),
        len(tool_metrics),
    )

    return {
        "chat_session": chat_session.to_dict(),
        "metrics": metrics.to_dict(),
        "llm_requests": [req.to_dict() for req in enriched_requests],
        "tool_calls": [tool.to_dict() for tool in enriched_tools],
        "tool_metrics": tool_metrics,
    }


@router.get(
    "/admin/chat-sessions/{chat_id}/messages",
    response_model=Dict[str, Any],
    summary="[Admin] Get archived and tool call messages for any chat",
)
def admin_get_chat_messages(
    chat_id: str,
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    request_id: Optional[str] = Query(None, description="Filter by request id"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Retrieve all messages (archived and tool call) for any chat.

    Admin endpoint: provides visibility into any chat for audit and debugging.
    Can filter by request_id to retrieve messages for a specific LLM request.

    Requires admin role.

    Returns:
        Dict with:
            - llm_messages: List of ArchivedMessage
            - tool_messages: List of ToolCallMessage
            - total_llm_messages: Count of archived messages
            - total_tool_messages: Count of tool call messages

    Raises:
        HTTP 404 if chat not found.
    """
    analytics = _get_analytics()

    # Verify chat exists
    chat_sessions = analytics.storage.read_chat_sessions(chat_id=chat_id)
    if not chat_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Chat '{chat_id}' not found.",
        )

    # Fetch archived and tool call messages with optional request_id filter
    llm_messages = analytics.get_archived_messages_for_chat(
        chat_id=chat_id,
        start_date=start_date,
        end_date=end_date,
        request_id=request_id,
    )

    tool_messages = analytics.get_tool_call_messages_for_chat(
        chat_id=chat_id,
        start_date=start_date,
        end_date=end_date,
    )

    logger.info(
        "Admin retrieved messages for chat: chat_id=%s request_id=%s llm_messages=%d tool_messages=%d",
        chat_id,
        request_id,
        len(llm_messages),
        len(tool_messages),
    )

    return {
        "llm_messages": [msg.to_dict() for msg in llm_messages],
        "tool_messages": [msg.to_dict() for msg in tool_messages],
        "total_llm_messages": len(llm_messages),
        "total_tool_messages": len(tool_messages),
    }


@router.get(
    "/admin/chat-sessions/{chat_id}/complete-context",
    response_model=Dict[str, Any],
    summary="[Admin] Get complete chat context including all messages",
)
def admin_get_complete_chat_context(
    chat_id: str,
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Retrieve the complete context for any chat including metadata, metrics, and all messages.

    Admin endpoint: provides comprehensive visibility into any chat for audit and debugging.

    Requires admin role.

    Returns:
        Dict with:
            - chat_session: ChatSessionEvent metadata
            - metrics: ChatMetrics aggregated consumption
            - llm_requests: List of TokenUsageEvent (the usage records)
            - llm_messages: List of ArchivedMessage (the actual content)
            - tool_calls: List of ToolUsageEvent (the usage records)
            - tool_messages: List of ToolCallMessage (with args/results)
            - tool_metrics: Aggregated metrics per tool name

    Raises:
        HTTP 404 if chat not found.
    """
    analytics = _get_analytics()

    # Verify chat exists
    chat_sessions = analytics.storage.read_chat_sessions(chat_id=chat_id)
    if not chat_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Chat '{chat_id}' not found.",
        )

    complete_context = analytics.get_chat_complete_context(
        chat_id=chat_id,
        start_date=start_date,
        end_date=end_date,
    )

    logger.info(
        "Admin retrieved complete chat context: chat_id=%s llm_requests=%d "
        "tool_calls=%d llm_messages=%d",
        chat_id,
        len(complete_context["llm_requests"]),
        len(complete_context["tool_calls"]),
        len(complete_context["llm_requests_messages"]),
    )

    # Standardize key names for consistency
    return {
        "chat_session": complete_context["chat_session"],
        "metrics": complete_context["metrics"],
        "llm_requests": complete_context["llm_requests"],
        "llm_messages": complete_context["llm_requests_messages"],
        "tool_calls": complete_context["tool_calls"],
        "tool_messages": complete_context["tool_call_messages"],
        "tool_metrics": complete_context["tool_metrics"],
    }


# ── Admin-scoped decision-model analytics (Admin Only) ─────────────────────────


@router.get(
    "/admin/decisions",
    response_model=DecisionModelEventList,
    summary="[Admin] List decision-model analytics events across all users",
)
def admin_get_decisions(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    chat_id: Optional[str] = Query(None, description="Filter by chat id"),
    decision_type: Optional[str] = Query(None, description="Filter by decision type"),
    engine: Optional[str] = Query(None, description="Filter by engine"),
    model: Optional[str] = Query(None, description="Filter by decision model"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    project_id: Optional[str] = Query(None, description="Filter by project id"),
    success: Optional[bool] = Query(None, description="Filter by success flag"),
    limit: Optional[int] = Query(None, description="Max events to return"),
    offset: int = Query(0, description="Number of events to skip"),
    _: CodxUser = Depends(require_admin),
) -> DecisionModelEventList:
    """
    Return decision-model analytics events across all users.

    Enables admins to audit the decision process (typed deciders and LLM
    fallbacks): what was asked, what was answered, calibrated probabilities,
    abstentions, failures and timings.

    Requires admin role.

    Returns:
        ``DecisionModelEventList`` (paginated, ordered by timestamp).
    """
    analytics = _get_analytics()
    events = analytics.storage.read_decision_events(
        start_date=start_date,
        end_date=end_date,
        chat_id=chat_id,
        decision_type=decision_type,
        engine=engine,
        model=model,
        username=username,
        project_name=project_name,
        project_id=project_id,
        success=success,
    )
    return DecisionModelEventList.from_events(events, limit=limit, offset=offset)


@router.post(
    "/admin/decisions/search",
    response_model=DecisionModelEventList,
    summary="[Admin] Search decision-model analytics events across all users",
)
def admin_search_decisions(
    body: DecisionModelQuery,
    _: CodxUser = Depends(require_admin),
) -> DecisionModelEventList:
    """
    Search decision-model analytics events using a JSON filter body.

    Same data as ``GET /admin/decisions`` but with a request body, which is
    convenient for clients that build complex filter sets programmatically.

    Requires admin role.

    Returns:
        ``DecisionModelEventList`` (paginated, ordered by timestamp).
    """
    analytics = _get_analytics()
    events = analytics.storage.read_decision_events(**body.filters())
    return DecisionModelEventList.from_events(
        events, limit=body.limit, offset=body.offset
    )


@router.get(
    "/admin/decisions/metrics",
    response_model=DecisionModelMetrics,
    summary="[Admin] Aggregated decision-model analytics metrics across all users",
)
def admin_get_decision_metrics(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    decision_type: Optional[str] = Query(None, description="Filter by decision type"),
    group_by: str = Query("model", description="Grouping key: model, engine, or decision_type"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    _: CodxUser = Depends(require_admin),
) -> DecisionModelMetrics:
    """
    Return aggregated decision-model metrics across all users.

    Requires admin role.

    Returns:
        ``DecisionModelMetrics`` with per-group calls, success/failure/abstain
        counts, durations and average confidence.
    """
    analytics = _get_analytics()
    metrics = analytics.get_decision_metrics(
        start_date=start_date,
        end_date=end_date,
        decision_type=decision_type,
        group_by=group_by,
        username=username,
        project_name=project_name,
    )
    return DecisionModelMetrics.from_metrics(group_by=group_by, metrics=metrics)


@router.get(
    "/admin/chat-sessions/{chat_id}/decisions",
    response_model=DecisionModelEventList,
    summary="[Admin] Get decision-model events for a chat",
)
def admin_get_chat_decisions(
    chat_id: str,
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    decision_type: Optional[str] = Query(None, description="Filter by decision type"),
    limit: Optional[int] = Query(None, description="Max events to return"),
    offset: int = Query(0, description="Number of events to skip"),
    _: CodxUser = Depends(require_admin),
) -> DecisionModelEventList:
    """
    Retrieve the decision-model events recorded for a specific chat.

    Provides the complete audit trail of the decision process (typed deciders
    and LLM fallbacks) for one chat, complementing the existing chat context
    and message endpoints.

    Requires admin role.

    Returns:
        ``DecisionModelEventList`` (paginated, ordered by timestamp).
    """
    analytics = _get_analytics()
    events = analytics.get_decisions_by_chat(
        chat_id=chat_id,
        start_date=start_date,
        end_date=end_date,
        decision_type=decision_type,
    )
    return DecisionModelEventList.from_events(events, limit=limit, offset=offset)


# ── Admin-scoped decision-model logs (Admin Only) ──────────────────────────────


@router.get(
    "/admin/decision-model-logs",
    response_model=DecisionModelLogsResponse,
    summary="[Admin] Decision-model logs across all users",
)
def admin_get_decision_model_logs(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    chat_id: Optional[str] = Query(None, description="Filter by chat id"),
    decision_type: Optional[str] = Query(None, description="Filter by decision type"),
    engine: Optional[str] = Query(None, description="Filter by engine"),
    model: Optional[str] = Query(None, description="Filter by decision model"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    project_id: Optional[str] = Query(None, description="Filter by project id"),
    success: Optional[bool] = Query(None, description="Filter by success flag"),
    session_id: Optional[str] = Query(None, description="Filter by session/chat id"),
    tags: Optional[str] = Query(None, description="Comma separated tags to match"),
    direction: Optional[str] = Query(None, description="'request' or 'response'"),
    limit: Optional[int] = Query(None, description="Max records to return"),
    offset: int = Query(0, description="Number of records to skip"),
    _: CodxUser = Depends(require_admin),
) -> DecisionModelLogsResponse:
    """
    Return decision-model logs across all users.

    Enables admins to audit the decision process from the log viewer: what was
    asked (``prompt``), what was answered (``decision``), the reasoning trace,
    calibrations (in ``details``), timings, abstentions and failures.

    Requires admin role.

    Returns:
        ``DecisionModelLogsResponse`` (records newest first, paginated).
    """
    return _read_decision_logs(
        start_date=start_date,
        end_date=end_date,
        chat_id=chat_id,
        decision_type=decision_type,
        engine=engine,
        model=model,
        username=username,
        project_name=project_name,
        project_id=project_id,
        success=success,
        session_id=session_id,
        tags=tags,
        direction=direction,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/admin/decision-model-logs/{log_id}",
    response_model=DecisionModelLogRecord,
    summary="[Admin] Get a single decision-model log",
)
def admin_get_decision_model_log(
    log_id: str,
    _: CodxUser = Depends(require_admin),
) -> DecisionModelLogRecord:
    """
    Return the decision-model log with the given (event) id, for any user.

    Requires admin role.

    Raises:
        HTTP 404 if no event with that id was recorded.
    """
    record = _find_decision_log(log_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Decision log '{log_id}' not found.",
        )
    return record


# ── Admin pricing endpoints ────────────────────────────────────────────────────


@router.get(
    "/admin/pricing",
    summary="[Admin] List providers and models with current pricing",
)
async def get_pricing(
    _: CodxUser = Depends(require_admin),
):
    """
    Return providers and models that have analytics data, along with their
    current pricing resolved from provider.price_list (falling back to
    provider-level defaults).

    Requires admin role.
    """
    global_settings = read_global_settings()
    analytics = _get_analytics()

    by_model_data = analytics.get_usage_by_model()
    active_keys = set(by_model_data.keys())

    result = []
    for provider in global_settings.ai_providers:
        models = []
        for m in global_settings.ai_models:
            if m.ai_provider != provider.name or m.name not in active_keys:
                continue
            provider_model_name = m.ai_model or m.name
            pricing = _get_model_price(provider, provider_model_name)
            models.append({
                "name": m.name,
                "ai_model": m.ai_model,
                "input_k_tokens_cxjcoins": pricing["input_k_tokens_cxjcoins"],
                "output_k_tokens_cxjcoins": pricing["output_k_tokens_cxjcoins"],
            })

        if models:
            result.append({
                "name": provider.name,
                "input_k_tokens_cxjcoins": provider.input_k_tokens_cxjcoins,
                "output_k_tokens_cxjcoins": provider.output_k_tokens_cxjcoins,
                "models": models,
            })

    return result


@router.put(
    "/admin/pricing/provider/{provider_name}",
    summary="[Admin] Update provider-level pricing",
)
async def update_provider_pricing(
    provider_name: str,
    body: PricingUpdateRequest,
    _: CodxUser = Depends(require_admin),
):
    """
    Update the token pricing for a specific AI provider.

    Requires admin role.
    """
    global_settings = read_global_settings()

    provider_found = False
    for provider in global_settings.ai_providers:
        if provider.name == provider_name:
            if body.input_k_tokens_cxjcoins is not None:
                provider.input_k_tokens_cxjcoins = body.input_k_tokens_cxjcoins
            if body.output_k_tokens_cxjcoins is not None:
                provider.output_k_tokens_cxjcoins = body.output_k_tokens_cxjcoins
            provider_found = True
            break

    if not provider_found:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{provider_name}' not found.",
        )

    write_global_settings(global_settings)
    return {"ok": True}


@router.put(
    "/admin/pricing/model/{provider_name}/{model_name}",
    summary="[Admin] Update model-level pricing",
)
async def update_model_pricing(
    provider_name: str,
    model_name: str,
    body: PricingUpdateRequest,
    _: CodxUser = Depends(require_admin),
):
    """
    Update the token pricing for a specific AI model within a provider.
    Pricing is stored exclusively in provider.price_list keyed by the
    provider-side model name (AIModel.ai_model or AIModel.name).

    Returns ``{"ok": True}`` if the model record was found and updated.
    Raises HTTP 404 if no matching model is found.

    Requires admin role.
    """
    global_settings = read_global_settings()

    ai_model = next(
        (m for m in global_settings.ai_models
         if m.ai_provider == provider_name and m.name == model_name),
        None,
    )

    if ai_model is None:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found for provider '{provider_name}'.",
        )

    provider_model_name = ai_model.ai_model or model_name

    provider_found = False
    for provider in global_settings.ai_providers:
        if provider.name == provider_name:
            if provider.price_list is None:
                provider.price_list = []

            price_entry = next(
                (p for p in provider.price_list if p.model_name == provider_model_name),
                None,
            )

            if price_entry is not None:
                if body.input_k_tokens_cxjcoins is not None:
                    price_entry.input_price_per_1k_tokens = body.input_k_tokens_cxjcoins
                if body.output_k_tokens_cxjcoins is not None:
                    price_entry.output_price_per_1k_tokens = body.output_k_tokens_cxjcoins
            else:
                provider.price_list.append(
                    AIModelPrice(
                        model_name=provider_model_name,
                        input_price_per_1k_tokens=body.input_k_tokens_cxjcoins or 0.0,
                        output_price_per_1k_tokens=body.output_k_tokens_cxjcoins or 0.0,
                    )
                )
            provider_found = True
            break

    if not provider_found:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{provider_name}' not found.",
        )

    write_global_settings(global_settings)
    return {"ok": True}


@router.post(
    "/admin/pricing/recalculate",
    summary="[Admin] Recalculate historical events with new pricing",
)
async def recalculate_pricing(
    body: RecalculateRequest,
    _: CodxUser = Depends(require_admin),
):
    """
    Rewrite historical analytics events with updated pricing for a given
    provider/model within a specified date range.

    Requires admin role.
    """
    analytics = _get_analytics()

    res = analytics.storage.rewrite_events_for_date_range(
        provider=body.provider,
        model=body.model,
        start_date=body.start_date,
        end_date=body.end_date,
        input_k_tokens_cxjcoins=body.input_k_tokens_cxjcoins,
        output_k_tokens_cxjcoins=body.output_k_tokens_cxjcoins,
    )
    return {"ok": res}

# Made with ❤️ by codx-junior