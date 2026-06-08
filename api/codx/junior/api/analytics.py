"""
Analytics router – token usage endpoints.

User-scoped endpoints return data filtered to the authenticated user.
Admin-only endpoints return data across all users and require the ``admin``
role (enforced via the ``require_admin`` dependency).

Route layout
------------
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
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from codx.junior.api import require_admin, get_current_session
from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.globals import ANALYTICS_DATA_PATH
from codx.junior.analytics import Analytics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# ── Shared Analytics instance ──────────────────────────────────────────────────

_analytics: Optional[Analytics] = None


def _get_analytics() -> Analytics:
    """Return (or lazily create) the shared Analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = Analytics(analytics_path=ANALYTICS_DATA_PATH)
    return _analytics


# ── User-scoped endpoints ──────────────────────────────────────────────────────


@router.get("/dates", response_model=List[str], summary="List dates with recorded usage (own data)")
def list_dates(
    user: CodxUser = Depends(get_authenticated_user),
) -> List[str]:
    """
    Return all ISO dates (``YYYY-MM-DD``) for which the authenticated user
    has recorded token usage.
    """
    analytics = _get_analytics()
    # Filter available dates down to those that actually contain data for this user
    all_dates = analytics.list_available_dates()
    # Return dates where the user has at least one event
    user_dates = []
    for date in all_dates:
        events = analytics.storage.read_events(
            start_date=date,
            end_date=date,
            username=user.username,
        )
        if events:
            user_dates.append(date)
    return user_dates


@router.get("/total", response_model=Dict[str, int], summary="Total token usage (own data)")
def get_total(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    user: CodxUser = Depends(get_authenticated_user),
) -> Dict[str, int]:
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
    user: CodxUser = Depends(get_authenticated_user),
) -> List[Dict[str, Any]]:
    """
    Return per-day aggregated token usage for the authenticated user.

    Returns:
        List of ``{date, input_tokens, output_tokens, total_tokens, calls}``
        sorted by date ascending.
    """
    analytics = _get_analytics()
    return analytics.get_daily_usage(
        start_date=start_date,
        end_date=end_date,
        username=user.username,
        project_name=project_name,
    )


@router.get("/by-model", response_model=Dict[str, Dict[str, int]], summary="Usage by model (own data)")
def get_by_model(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    user: CodxUser = Depends(get_authenticated_user),
) -> Dict[str, Dict[str, int]]:
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
    response_model=Dict[str, int],
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
) -> Dict[str, int]:
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
    _: CodxUser = Depends(require_admin),
) -> List[Dict[str, Any]]:
    """
    Return per-day aggregated token usage across all users.

    Requires admin role.

    Returns:
        List of ``{date, input_tokens, output_tokens, total_tokens, calls}``
        sorted by date ascending.
    """
    analytics = _get_analytics()
    return analytics.get_daily_usage(
        start_date=start_date,
        end_date=end_date,
        username=username,
        project_name=project_name,
    )


@router.get(
    "/admin/by-user",
    response_model=Dict[str, Dict[str, int]],
    summary="[Admin] Usage grouped by user",
)
def admin_get_by_user(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    project_id: Optional[str] = Query(None, description="Filter by project id"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Dict[str, int]]:
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
    response_model=Dict[str, Dict[str, int]],
    summary="[Admin] Usage grouped by project",
)
def admin_get_by_project(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    username: Optional[str] = Query(None, description="Filter by username"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Dict[str, int]]:
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
    response_model=Dict[str, Dict[str, int]],
    summary="[Admin] Usage grouped by model",
)
def admin_get_by_model(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Dict[str, int]]:
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

# Made with ❤️ by codx-junior