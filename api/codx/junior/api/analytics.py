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

    # Build a fast provider lookup
    provider_map = {p.name: p for p in global_settings.ai_providers}

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

    # Locate the AIModel to resolve the provider-side model name
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

    # Resolve the provider-side model name
    provider_model_name = ai_model.ai_model or model_name

    # Update provider.price_list
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