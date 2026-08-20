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

ENRICHED ENDPOINTS (Chat-aware Analytics)
──────────────────────────────────────────
GET /api/analytics/chat-sessions           – list user's chat sessions with metrics (own data)
GET /api/analytics/chat-sessions/{chat_id} – get specific chat with full context (own data)

GET /api/analytics/admin/chat-sessions     – list all chat sessions with metrics (admin)
GET /api/analytics/admin/chat-sessions/{chat_id} – get specific chat with full context (admin)
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

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


# ADDED: Helper to enrich token events with chat session data
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


# ADDED: Helper to enrich tool events with chat session data
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


# ADDED: Helper to compute aggregated metrics for a chat session
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


# ADDED: User-scoped enriched endpoints ──────────────────────────────────────────


@router.get(
    "/chat-sessions",
    response_model=List[Dict[str, Any]],
    summary="List user's chat sessions with metrics (own data)",
)
def get_user_chat_sessions(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    user: CodxUser = Depends(get_authenticated_user),
) -> List[Dict[str, Any]]:
    """
    Return all chat sessions for the authenticated user with aggregated metrics.

    Each chat session includes:
    - Chat metadata (name, mode, profiles, files, iteration info, etc.)
    - Aggregated metrics (total tokens, LLM calls, tool calls, durations, costs)

    Filters can be applied to narrow results by date range and/or project.

    Returns:
        List of ``ChatContextSummary`` objects (as dicts) ordered by chat start time.
    """
    analytics = _get_analytics()

    chat_sessions = analytics.get_chat_sessions_by_user(
        username=user.username,
        start_date=start_date,
        end_date=end_date,
        project_name=project_name,
    )

    summaries: List[Dict[str, Any]] = []
    for chat_session in chat_sessions:
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
        "Retrieved %d chat sessions for user=%s",
        len(summaries),
        user.username,
    )

    return summaries


@router.get(
    "/chat-sessions/{chat_id}",
    response_model=Dict[str, Any],
    summary="Get chat with full context including requests and tools (own data)",
)
def get_user_chat_context(
    chat_id: str,
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    user: CodxUser = Depends(get_authenticated_user),
) -> Dict[str, Any]:
    """
    Retrieve a complete chat session with all associated LLM requests and tool calls.

    Enables reconstruction of the full request-response chain and tool execution
    history for a specific chat. Access control: users can only view their own chats.

    Returns:
        Dict with:
            - chat_session: ChatSessionEvent metadata
            - metrics: ChatMetrics aggregated from linked requests/tools
            - llm_requests: List of TokenUsageEvent (enriched with chat_session)
            - tool_calls: List of ToolUsageEvent (enriched with chat_session)

    Raises:
        HTTP 404 if chat not found or does not belong to the authenticated user.
    """
    analytics = _get_analytics()

    # Verify chat exists and belongs to user
    chat_sessions = analytics.storage.read_chat_sessions(chat_id=chat_id)
    if not chat_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Chat '{chat_id}' not found.",
        )

    chat_session = chat_sessions[-1]  # Most recent session event

    # Access control: user can only view their own chats
    if chat_session.username != user.username:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this chat.",
        )

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

    logger.info(
        "Retrieved chat context: chat_id=%s user=%s llm_requests=%d tool_calls=%d",
        chat_id,
        user.username,
        len(enriched_requests),
        len(enriched_tools),
    )

    return {
        "chat_session": chat_session.to_dict(),
        "metrics": metrics.to_dict(),
        "llm_requests": [req.to_dict() for req in enriched_requests],
        "tool_calls": [tool.to_dict() for tool in enriched_tools],
    }


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


# ADDED: Admin-scoped enriched endpoints ────────────────────────────────────────


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
    summary="[Admin] Get chat with full context including requests and tools",
)
def admin_get_chat_context(
    chat_id: str,
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Retrieve a complete chat session with all associated LLM requests and tool calls.

    Admin endpoint: provides visibility into any chat session for audit and analysis.
    Enables reconstruction of the full request-response chain and tool execution
    history for a specific chat.

    Returns:
        Dict with:
            - chat_session: ChatSessionEvent metadata
            - metrics: ChatMetrics aggregated from linked requests/tools
            - llm_requests: List of TokenUsageEvent (enriched with chat_session)
            - tool_calls: List of ToolUsageEvent (enriched with chat_session)

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

    logger.info(
        "Admin retrieved chat context: chat_id=%s user=%s llm_requests=%d tool_calls=%d",
        chat_id,
        chat_session.username,
        len(enriched_requests),
        len(enriched_tools),
    )

    return {
        "chat_session": chat_session.to_dict(),
        "metrics": metrics.to_dict(),
        "llm_requests": [req.to_dict() for req in enriched_requests],
        "tool_calls": [tool.to_dict() for tool in enriched_tools],
    }


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