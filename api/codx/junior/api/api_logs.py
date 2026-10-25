"""
API performance logs router – HTTP call metrics backed by raw JSONL files.

API call performance events are written by the ``record_api_call`` helper in
``codx.junior.app`` (from the timing middleware) and read/filtered here via
:class:`~codx.junior.api_logs.api_logs.ApiLogs`.

User-scoped endpoints return metrics filtered to the authenticated user.
Admin-only endpoints return metrics across all users and require the ``admin``
role (enforced via the ``require_admin`` dependency).

Route layout
------------
GET /api/api-logs/dates                 – list dates with recorded calls (own data)
GET /api/api-logs/summary               – aggregated summary (own data)
GET /api/api-logs/daily                 – time-series breakdown (own data)
GET /api/api-logs/by-endpoint           – grouped by endpoint (own data)
GET /api/api-logs/by-status             – grouped by status code (own data)
GET /api/api-logs/slowest               – slowest calls (own data)
GET /api/api-logs/errors                – failed calls (own data)

GET /api/api-logs/admin/dates           – list dates (all users)
GET /api/api-logs/admin/summary         – aggregated summary (all users)
GET /api/api-logs/admin/daily           – time-series breakdown (all users)
GET /api/api-logs/admin/by-endpoint     – grouped by endpoint (admin)
GET /api/api-logs/admin/by-status       – grouped by status code (admin)
GET /api/api-logs/admin/by-user         – grouped by user (admin)
GET /api/api-logs/admin/by-project      – grouped by project (admin)
GET /api/api-logs/admin/slowest         – slowest calls (admin)
GET /api/api-logs/admin/errors          – failed calls (admin)

Diagram
-------
```mermaid
graph TD
    Client -->|GET /api/api-logs/summary| UserSummary
    Client -->|GET /api/api-logs/by-endpoint| UserByEndpoint
    Client -->|GET /api/api-logs/slowest| UserSlowest

    Client -->|GET /api/api-logs/admin/summary| AdminSummary
    Client -->|GET /api/api-logs/admin/by-user| AdminByUser
    Client -->|GET /api/api-logs/admin/by-project| AdminByProject

    UserSummary --> ApiLogs
    UserByEndpoint --> ApiLogs
    UserSlowest --> ApiLogs
    AdminSummary --> ApiLogs
    AdminByUser --> ApiLogs
    AdminByProject --> ApiLogs
```
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from codx.junior.api import require_admin
from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.globals import API_LOGS_DATA_PATH
from codx.junior.api_logs import ApiLogs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-logs", tags=["api-logs"])

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500

# ── Shared ApiLogs instance ────────────────────────────────────────────────────

_api_logs: Optional[ApiLogs] = None


def _get_api_logs() -> ApiLogs:
    """Return (or lazily create) the shared ApiLogs instance."""
    global _api_logs
    if _api_logs is None:
        _api_logs = ApiLogs(logs_path=API_LOGS_DATA_PATH)
    return _api_logs


# ── Helpers ────────────────────────────────────────────────────────────────────


def _filters(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    path: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
    username: Optional[str] = None,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
    min_duration_seconds: Optional[float] = None,
    errors_only: bool = False,
) -> Dict[str, Any]:
    """Build the filter dictionary consumed by :class:`ApiLogs` methods."""
    return {
        "start_date": start_date,
        "end_date": end_date,
        "path": path,
        "method": method,
        "status_code": status_code,
        "username": username,
        "project_name": project_name,
        "project_id": project_id,
        "min_duration_seconds": min_duration_seconds,
        "errors_only": errors_only,
    }


def _clamp_limit(limit: int) -> int:
    """Clamp ``limit`` to the allowed range ``[1, MAX_PAGE_SIZE]``."""
    return max(1, min(limit, MAX_PAGE_SIZE))


# ── User-scoped endpoints ──────────────────────────────────────────────────────


@router.get("/dates", response_model=List[str], summary="List dates with recorded calls (own data)")
def list_dates(
    user: CodxUser = Depends(get_authenticated_user),
) -> List[str]:
    """
    Return all ISO dates (``YYYY-MM-DD``) for which the authenticated user
    has recorded API calls.
    """
    api_logs = _get_api_logs()
    user_dates = []
    for date_str in api_logs.list_available_dates():
        events = api_logs.storage.read_events(
            start_date=date_str,
            end_date=date_str,
            username=user.username,
        )
        if events:
            user_dates.append(date_str)
    return user_dates


@router.get("/summary", response_model=Dict[str, Any], summary="Aggregated API metrics (own data)")
def get_summary(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    min_duration_seconds: Optional[float] = Query(None, description="Only calls slower than this"),
    user: CodxUser = Depends(get_authenticated_user),
) -> Dict[str, Any]:
    """
    Return aggregated API performance metrics for the authenticated user.
    """
    api_logs = _get_api_logs()
    return api_logs.get_summary(**_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        status_code=status_code, username=user.username, project_name=project_name,
        min_duration_seconds=min_duration_seconds,
    ))


@router.get("/daily", response_model=List[Dict[str, Any]], summary="Time-series metrics (own data)")
def get_daily(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    grouping: str = Query("day", description="Grouping: minute | hour | day"),
    user: CodxUser = Depends(get_authenticated_user),
) -> List[Dict[str, Any]]:
    """
    Return per-period aggregated metrics for the authenticated user.
    """
    api_logs = _get_api_logs()
    return api_logs.get_daily(grouping=grouping, **_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        status_code=status_code, username=user.username, project_name=project_name,
    ))


@router.get("/by-endpoint", response_model=Dict[str, Dict[str, Any]], summary="Metrics grouped by endpoint (own data)")
def get_by_endpoint(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    user: CodxUser = Depends(get_authenticated_user),
) -> Dict[str, Dict[str, Any]]:
    """
    Return metrics grouped by endpoint (path) for the authenticated user.
    """
    api_logs = _get_api_logs()
    return api_logs.get_by_endpoint(**_filters(
        start_date=start_date, end_date=end_date, method=method,
        status_code=status_code, username=user.username, project_name=project_name,
    ))


@router.get("/by-status", response_model=Dict[str, Dict[str, Any]], summary="Metrics grouped by status (own data)")
def get_by_status(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    user: CodxUser = Depends(get_authenticated_user),
) -> Dict[str, Dict[str, Any]]:
    """
    Return metrics grouped by HTTP status code for the authenticated user.
    """
    api_logs = _get_api_logs()
    return api_logs.get_by_status(**_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        username=user.username, project_name=project_name,
    ))


@router.get("/slowest", response_model=List[Dict[str, Any]], summary="Slowest calls (own data)")
def get_slowest(
    limit: int = Query(20, ge=1, le=MAX_PAGE_SIZE, description="Number of slowest calls"),
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    user: CodxUser = Depends(get_authenticated_user),
) -> List[Dict[str, Any]]:
    """
    Return the slowest API calls for the authenticated user.
    """
    api_logs = _get_api_logs()
    return api_logs.get_slowest(limit=_clamp_limit(limit), **_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        username=user.username, project_name=project_name,
    ))


@router.get("/errors", response_model=List[Dict[str, Any]], summary="Failed calls (own data)")
def get_errors(
    limit: int = Query(100, ge=1, le=MAX_PAGE_SIZE, description="Number of failed calls"),
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    user: CodxUser = Depends(get_authenticated_user),
) -> List[Dict[str, Any]]:
    """
    Return failed API calls (error or status >= 500) for the authenticated user.
    """
    api_logs = _get_api_logs()
    return api_logs.get_errors(limit=_clamp_limit(limit), **_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        username=user.username, project_name=project_name,
    ))


# ── Admin endpoints ────────────────────────────────────────────────────────────


@router.get("/admin/dates", response_model=List[str], summary="[Admin] List dates with recorded calls")
def admin_list_dates(
    _: CodxUser = Depends(require_admin),
) -> List[str]:
    """Return all ISO dates for which any API calls were recorded."""
    return _get_api_logs().list_available_dates()


@router.get("/admin/summary", response_model=Dict[str, Any], summary="[Admin] Aggregated API metrics")
def admin_get_summary(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    min_duration_seconds: Optional[float] = Query(None, description="Only calls slower than this"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Any]:
    """Return aggregated API performance metrics across all users."""
    api_logs = _get_api_logs()
    return api_logs.get_summary(**_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        status_code=status_code, username=username, project_name=project_name,
        min_duration_seconds=min_duration_seconds,
    ))


@router.get("/admin/daily", response_model=List[Dict[str, Any]], summary="[Admin] Time-series metrics")
def admin_get_daily(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    grouping: str = Query("day", description="Grouping: minute | hour | day"),
    _: CodxUser = Depends(require_admin),
) -> List[Dict[str, Any]]:
    """Return per-period aggregated metrics across all users."""
    api_logs = _get_api_logs()
    return api_logs.get_daily(grouping=grouping, **_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        status_code=status_code, username=username, project_name=project_name,
    ))


@router.get("/admin/by-endpoint", response_model=Dict[str, Dict[str, Any]], summary="[Admin] Metrics grouped by endpoint")
def admin_get_by_endpoint(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Dict[str, Any]]:
    """Return metrics grouped by endpoint (path) across all users."""
    api_logs = _get_api_logs()
    return api_logs.get_by_endpoint(**_filters(
        start_date=start_date, end_date=end_date, method=method,
        status_code=status_code, username=username, project_name=project_name,
    ))


@router.get("/admin/by-status", response_model=Dict[str, Dict[str, Any]], summary="[Admin] Metrics grouped by status")
def admin_get_by_status(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Dict[str, Any]]:
    """Return metrics grouped by HTTP status code across all users."""
    api_logs = _get_api_logs()
    return api_logs.get_by_status(**_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        username=username, project_name=project_name,
    ))


@router.get("/admin/by-user", response_model=Dict[str, Dict[str, Any]], summary="[Admin] Metrics grouped by user")
def admin_get_by_user(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Dict[str, Any]]:
    """Return metrics grouped by username across all users."""
    api_logs = _get_api_logs()
    return api_logs.get_by_user(**_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        project_name=project_name,
    ))


@router.get("/admin/by-project", response_model=Dict[str, Dict[str, Any]], summary="[Admin] Metrics grouped by project")
def admin_get_by_project(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    username: Optional[str] = Query(None, description="Filter by username"),
    _: CodxUser = Depends(require_admin),
) -> Dict[str, Dict[str, Any]]:
    """Return metrics grouped by project name across all users."""
    api_logs = _get_api_logs()
    return api_logs.get_by_project(**_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        username=username,
    ))


@router.get("/admin/slowest", response_model=List[Dict[str, Any]], summary="[Admin] Slowest calls")
def admin_get_slowest(
    limit: int = Query(20, ge=1, le=MAX_PAGE_SIZE, description="Number of slowest calls"),
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    _: CodxUser = Depends(require_admin),
) -> List[Dict[str, Any]]:
    """Return the slowest API calls across all users."""
    api_logs = _get_api_logs()
    return api_logs.get_slowest(limit=_clamp_limit(limit), **_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        username=username, project_name=project_name,
    ))


@router.get("/admin/errors", response_model=List[Dict[str, Any]], summary="[Admin] Failed calls")
def admin_get_errors(
    limit: int = Query(100, ge=1, le=MAX_PAGE_SIZE, description="Number of failed calls"),
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    path: Optional[str] = Query(None, description="Filter by exact path"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    _: CodxUser = Depends(require_admin),
) -> List[Dict[str, Any]]:
    """Return failed API calls (error or status >= 500) across all users."""
    api_logs = _get_api_logs()
    return api_logs.get_errors(limit=_clamp_limit(limit), **_filters(
        start_date=start_date, end_date=end_date, path=path, method=method,
        username=username, project_name=project_name,
    ))

# Made with ❤️ by codx-junior