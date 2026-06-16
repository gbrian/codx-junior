"""
AI Logs router – request/response log endpoints backed by raw JSONL files.

Raw AI logs are written by :class:`~codx.junior.ai.raw_logger.RawAILogger`
and read/filtered here via :class:`~codx.junior.ai.raw_log_reader.RawLogReader`.

User-scoped endpoints return logs filtered to the authenticated user.
Admin-only endpoints return logs across all users and require the ``admin``
role (enforced via the ``require_admin`` dependency).

Route layout
------------
GET  /api/logs/me                   – recent logs for the current user
GET  /api/logs/list                 – paginated list of logs (own data)
GET  /api/logs/{log_id}             – retrieve a specific log entry (own data)

GET  /api/logs/admin/list           – paginated list of logs (all users)
GET  /api/logs/admin/{log_id}       – retrieve any specific log entry (admin)
DELETE /api/logs/admin/{log_id}     – delete a specific log entry (admin)
DELETE /api/logs/admin/purge        – delete logs matching filters (admin)

Diagram
-------
```mermaid
graph TD
    Client -->|GET /api/logs/me| UserMetrics
    Client -->|GET /api/logs/list| UserList
    Client -->|GET /api/logs/:id| UserDetail

    Client -->|GET /api/logs/admin/list| AdminList
    Client -->|GET /api/logs/admin/:id| AdminDetail
    Client -->|DELETE /api/logs/admin/:id| AdminDelete
    Client -->|DELETE /api/logs/admin/purge| AdminPurge

    UserMetrics --> RawLogReader
    UserList --> RawLogReader
    UserDetail --> RawLogReader
    AdminList --> RawLogReader
    AdminDetail --> RawLogReader
    AdminDelete --> RawLogReader
    AdminPurge --> RawLogReader
```
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from codx.junior.api import require_admin, get_current_session
from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.ai.raw_log_reader import RawLogReader
from codx.junior.model.logs import (
    RawLogRecord,
    RawLogRecordSummary,
    RawLogListResponse,
    RawLogPayload,
    PurgeRequest,
    PurgeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
_PREVIEW_MAX_LEN = 200
_PREVIEW_SUFFIX = "..."

# ── Shared RawLogReader instance ───────────────────────────────────────────────

_raw_log_reader: Optional[RawLogReader] = None


def _get_reader() -> RawLogReader:
    """
    Return (or lazily create) the shared :class:`RawLogReader` instance.

    Returns:
        A ready-to-use :class:`RawLogReader`.
    """
    global _raw_log_reader
    if _raw_log_reader is None:
        _raw_log_reader = RawLogReader()
    return _raw_log_reader


# ── Helpers ────────────────────────────────────────────────────────────────────


def _build_payload(raw_payload: Optional[Dict[str, Any]]) -> Optional[RawLogPayload]:
    """
    Deserialise the raw ``payload`` dict from a JSONL record into a
    :class:`RawLogPayload` model.

    Args:
        raw_payload: The ``payload`` value from the JSONL record dict,
                     or ``None``.

    Returns:
        A :class:`RawLogPayload` instance, or ``None`` if input is ``None``.
    """
    if raw_payload is None:
        return None
    return RawLogPayload(**{k: v for k, v in raw_payload.items() if v is not None})


def _build_summary(record: Dict[str, Any]) -> RawLogRecordSummary:
    """
    Convert a raw JSONL record dict into a :class:`RawLogRecordSummary`.

    All envelope fields are mapped directly.  The ``payload`` is replaced
    with a truncated ``payload_preview`` string.

    Args:
        record: Raw record dict as returned by :class:`RawLogReader`.

    Returns:
        A populated :class:`RawLogRecordSummary`.
    """
    raw_payload = record.get("payload")
    payload_preview: Optional[str] = None
    if raw_payload is not None:
        raw_str = str(raw_payload)
        if len(raw_str) > _PREVIEW_MAX_LEN:
            payload_preview = raw_str[:_PREVIEW_MAX_LEN] + _PREVIEW_SUFFIX
        else:
            payload_preview = raw_str

    return RawLogRecordSummary(
        log_id=record.get("log_id", ""),
        timestamp=record.get("timestamp", ""),
        direction=record.get("direction", ""),
        status=record.get("status", ""),
        request_id=record.get("request_id", ""),
        parent_request_id=record.get("parent_request_id"),
        provider=record.get("provider", ""),
        model=record.get("model", ""),
        base_url=record.get("base_url", ""),
        username=record.get("username", ""),
        project=record.get("project", ""),
        session_id=record.get("session_id"),
        tags=record.get("tags", ""),
        duration_seconds=record.get("duration_seconds"),
        payload_preview=payload_preview,
    )


def _build_full_record(record: Dict[str, Any]) -> RawLogRecord:
    """
    Convert a raw JSONL record dict into a full :class:`RawLogRecord` model,
    including the deserialised ``payload``.

    Args:
        record: Raw record dict as returned by :class:`RawLogReader`.

    Returns:
        A fully populated :class:`RawLogRecord`.
    """
    return RawLogRecord(
        log_id=record.get("log_id", ""),
        timestamp=record.get("timestamp", ""),
        direction=record.get("direction", ""),
        status=record.get("status", ""),
        request_id=record.get("request_id", ""),
        parent_request_id=record.get("parent_request_id"),
        provider=record.get("provider", ""),
        model=record.get("model", ""),
        base_url=record.get("base_url", ""),
        username=record.get("username", ""),
        project=record.get("project", ""),
        session_id=record.get("session_id"),
        tags=record.get("tags", ""),
        duration_seconds=record.get("duration_seconds"),
        payload=_build_payload(record.get("payload")),
    )


def _paginate(
    items: List[Any],
    page: int,
    page_size: int,
) -> tuple:
    """
    Slice a list for pagination.

    Args:
        items:     Full list of items to paginate.
        page:      1-based page number.
        page_size: Number of items per page.

    Returns:
        Tuple of ``(page_items, has_more)``.
    """
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]
    has_more = end < len(items)
    return page_items, has_more


def _clamp_page_size(page_size: int) -> int:
    """
    Clamp ``page_size`` to the allowed range ``[1, MAX_PAGE_SIZE]``.

    Args:
        page_size: Requested page size.

    Returns:
        Clamped page size.
    """
    return max(1, min(page_size, MAX_PAGE_SIZE))


def _apply_direction_filter(
    records: List[Dict[str, Any]],
    direction: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Filter records by ``direction`` field if provided.

    Args:
        records:   List of raw record dicts.
        direction: Optional direction value (e.g. ``"request"`` / ``"response"``).

    Returns:
        Filtered list.
    """
    if not direction:
        return records
    return [r for r in records if r.get("direction") == direction]


# ── User-scoped endpoints ──────────────────────────────────────────────────────


@router.get(
    "/me",
    response_model=Dict[str, Any],
    summary="Recent AI request/response logs for the current user",
)
def get_my_logs(
    limit: int = Query(10, ge=1, le=100, description="Number of most recent logs to return"),
    user: CodxUser = Depends(get_authenticated_user),
) -> Dict[str, Any]:
    """
    Return the most recent AI request/response log entries for the
    authenticated user.

    Reads from raw JSONL files via :class:`~codx.junior.ai.raw_log_reader.RawLogReader`.

    Args:
        limit: Maximum number of log entries to return (default 10, max 100).

    Returns::

        {
            "username": "<username>",
            "recent_logs": [<RawLogRecordSummary>, ...],
            "count": <int>
        }
    """
    reader = _get_reader()

    logger.debug("Fetching recent logs for user '%s' (limit=%d)", user.username, limit)

    raw_records: List[Dict[str, Any]] = reader.read_events(username=user.username)

    # Sort descending by timestamp and take the most recent entries
    sorted_records = sorted(
        raw_records,
        key=lambda r: r.get("timestamp", ""),
        reverse=True,
    )
    recent = sorted_records[:limit]

    summaries = [_build_summary(record) for record in recent]

    logger.info(
        "Returning %d recent log entries for user '%s'",
        len(summaries),
        user.username,
    )

    return {
        "username": user.username,
        "recent_logs": [s.model_dump() for s in summaries],
        "count": len(summaries),
    }


@router.get(
    "/list",
    response_model=RawLogListResponse,
    summary="Paginated AI request/response logs (own data)",
)
def list_logs(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    project: Optional[str] = Query(None, description="Filter by project name"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    provider: Optional[str] = Query(None, description="Filter by provider name"),
    direction: Optional[str] = Query(None, description="Filter by direction: request | response"),
    session_id: Optional[str] = Query(None, description="Filter by session id"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    user: CodxUser = Depends(get_authenticated_user),
) -> RawLogListResponse:
    """
    Return a paginated list of AI request/response log entries for the
    authenticated user, read from raw JSONL files.

    Results are sorted by timestamp descending (most recent first).

    Args:
        start_date: Optional start of date range filter.
        end_date:   Optional end of date range filter.
        project:    Optional project name filter.
        model:      Optional model name filter.
        provider:   Optional provider name filter.
        direction:  Optional direction filter (``"request"`` / ``"response"``).
        session_id: Optional session id filter.
        page:       Page number starting from 1.
        page_size:  Number of items per page (max 500).

    Returns:
        A paginated :class:`RawLogListResponse`.
    """
    reader = _get_reader()
    clamped_size = _clamp_page_size(page_size)

    logger.debug(
        "Listing logs for user '%s' (start=%s end=%s project=%s model=%s provider=%s "
        "direction=%s session=%s page=%d size=%d)",
        user.username, start_date, end_date, project, model, provider,
        direction, session_id, page, clamped_size,
    )

    raw_records: List[Dict[str, Any]] = reader.read_events(
        start_date=start_date,
        end_date=end_date,
        username=user.username,
        project=project,
        model=model,
        provider=provider,
        session_id=session_id,
    )

    # direction is not supported natively by RawLogReader – apply post-filter
    raw_records = _apply_direction_filter(raw_records, direction)

    sorted_records = sorted(
        raw_records,
        key=lambda r: r.get("timestamp", ""),
        reverse=True,
    )

    total = len(sorted_records)
    page_records, has_more = _paginate(sorted_records, page, clamped_size)
    summaries = [_build_summary(record) for record in page_records]

    logger.info(
        "Returning page %d (%d items, total=%d) for user '%s'",
        page, len(summaries), total, user.username,
    )

    return RawLogListResponse(
        items=summaries,
        total=total,
        page=page,
        page_size=clamped_size,
        has_more=has_more,
    )


@router.get(
    "/{log_id}",
    response_model=RawLogRecord,
    summary="Retrieve a specific log entry (own data)",
)
def get_log(
    log_id: str,
    user: CodxUser = Depends(get_authenticated_user),
) -> RawLogRecord:
    """
    Retrieve the full details of a specific AI request/response log entry,
    including the full ``payload`` dict.

    Only returns the log if it belongs to the authenticated user.

    Args:
        log_id: The synthetic log id (``<YYYY-MM-DD>:<line_index>``).

    Returns:
        The full :class:`RawLogRecord` for the given ``log_id``.

    Raises:
        HTTPException 404: If the log entry is not found or belongs to a
            different user.
    """
    reader = _get_reader()

    logger.debug("Fetching log '%s' for user '%s'", log_id, user.username)

    record = reader.read_event_by_id(log_id=log_id)

    if record is None:
        logger.warning("Log '%s' not found", log_id)
        raise HTTPException(status_code=404, detail=f"Log '{log_id}' not found.")

    # Enforce ownership – users may only read their own logs
    if record.get("username") != user.username:
        logger.warning(
            "User '%s' attempted to access log '%s' owned by '%s'",
            user.username, log_id, record.get("username"),
        )
        # Return 404 to avoid leaking information about other users' logs
        raise HTTPException(status_code=404, detail=f"Log '{log_id}' not found.")

    return _build_full_record(record)


# ── Admin endpoints ────────────────────────────────────────────────────────────


@router.get(
    "/admin/list",
    response_model=RawLogListResponse,
    summary="[Admin] Paginated AI request/response logs across all users",
)
def admin_list_logs(
    start_date: Optional[str] = Query(None, description="Inclusive start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Inclusive end date YYYY-MM-DD"),
    username: Optional[str] = Query(None, description="Filter by username"),
    project: Optional[str] = Query(None, description="Filter by project name"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    provider: Optional[str] = Query(None, description="Filter by provider name"),
    direction: Optional[str] = Query(None, description="Filter by direction: request | response"),
    session_id: Optional[str] = Query(None, description="Filter by session id"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    _: CodxUser = Depends(require_admin),
) -> RawLogListResponse:
    """
    Return a paginated list of AI request/response log entries across all
    users, read from raw JSONL files.

    Results are sorted by timestamp descending (most recent first).

    Requires the ``admin`` role.

    Args:
        start_date: Optional start of date range filter.
        end_date:   Optional end of date range filter.
        username:   Optional username filter.
        project:    Optional project name filter.
        model:      Optional model name filter.
        provider:   Optional provider name filter.
        direction:  Optional direction filter (``"request"`` / ``"response"``).
        session_id: Optional session id filter.
        page:       Page number starting from 1.
        page_size:  Number of items per page (max 500).

    Returns:
        A paginated :class:`RawLogListResponse`.
    """
    reader = _get_reader()
    clamped_size = _clamp_page_size(page_size)

    logger.debug(
        "Admin listing logs (start=%s end=%s user=%s project=%s model=%s provider=%s "
        "direction=%s session=%s page=%d size=%d)",
        start_date, end_date, username, project, model, provider,
        direction, session_id, page, clamped_size,
    )

    raw_records: List[Dict[str, Any]] = reader.read_events(
        start_date=start_date,
        end_date=end_date,
        username=username,
        project=project,
        model=model,
        provider=provider,
        session_id=session_id,
    )

    # direction is not supported natively by RawLogReader – apply post-filter
    raw_records = _apply_direction_filter(raw_records, direction)

    sorted_records = sorted(
        raw_records,
        key=lambda r: r.get("timestamp", ""),
        reverse=True,
    )

    total = len(sorted_records)
    page_records, has_more = _paginate(sorted_records, page, clamped_size)
    summaries = [_build_summary(record) for record in page_records]

    logger.info(
        "Admin: returning page %d (%d items, total=%d)",
        page, len(summaries), total,
    )

    return RawLogListResponse(
        items=summaries,
        total=total,
        page=page,
        page_size=clamped_size,
        has_more=has_more,
    )


@router.get(
    "/admin/{log_id}",
    response_model=RawLogRecord,
    summary="[Admin] Retrieve any specific log entry",
)
def admin_get_log(
    log_id: str,
    _: CodxUser = Depends(require_admin),
) -> RawLogRecord:
    """
    Retrieve the full details of any AI request/response log entry,
    including the full ``payload`` dict.

    Requires the ``admin`` role.

    Args:
        log_id: The synthetic log id (``<YYYY-MM-DD>:<line_index>``).

    Returns:
        The full :class:`RawLogRecord` for the given ``log_id``.

    Raises:
        HTTPException 404: If the log entry is not found.
    """
    reader = _get_reader()

    logger.debug("Admin fetching log '%s'", log_id)

    record = reader.read_event_by_id(log_id=log_id)

    if record is None:
        logger.warning("Admin: log '%s' not found", log_id)
        raise HTTPException(status_code=404, detail=f"Log '{log_id}' not found.")

    return _build_full_record(record)


@router.delete(
    "/admin/{log_id}",
    response_model=PurgeResponse,
    summary="[Admin] Delete a specific log entry",
)
def admin_delete_log(
    log_id: str,
    _: CodxUser = Depends(require_admin),
) -> PurgeResponse:
    """
    Delete a specific AI request/response log entry by its synthetic
    ``log_id``.  The underlying JSONL line is removed and the file is
    rewritten without it.

    Requires the ``admin`` role.

    Args:
        log_id: The synthetic log id (``<YYYY-MM-DD>:<line_index>``).

    Returns:
        :class:`PurgeResponse` with ``deleted=1`` on success.

    Raises:
        HTTPException 404: If the log entry is not found.
    """
    reader = _get_reader()

    logger.debug("Admin deleting log '%s'", log_id)

    # Verify the record exists before attempting deletion
    record = reader.read_event_by_id(log_id=log_id)
    if record is None:
        logger.warning("Admin: log '%s' not found for deletion", log_id)
        raise HTTPException(status_code=404, detail=f"Log '{log_id}' not found.")

    deleted = reader.delete_event_by_id(log_id=log_id)

    logger.info("Admin: deleted log '%s' (result=%s)", log_id, deleted)

    return PurgeResponse(ok=True, deleted=1 if deleted else 0)


@router.delete(
    "/admin/purge",
    response_model=PurgeResponse,
    summary="[Admin] Bulk delete logs matching filters",
)
def admin_purge_logs(
    body: PurgeRequest,
    _: CodxUser = Depends(require_admin),
) -> PurgeResponse:
    """
    Bulk delete all AI request/response log entries matching the supplied
    filter criteria by rewriting the affected JSONL files.

    At least one filter field must be provided to prevent accidental deletion
    of all logs.

    Requires the ``admin`` role.

    Args:
        body: :class:`PurgeRequest` with optional ``start_date``,
              ``end_date``, ``username``, ``project``, ``model``, and
              ``provider`` filters.

    Returns:
        :class:`PurgeResponse` with the number of deleted entries.

    Raises:
        HTTPException 400: If no filters are provided.
    """
    # Safety guard – require at least one filter to avoid wiping all data
    filter_values = [
        body.start_date,
        body.end_date,
        body.username,
        body.project,
        body.model,
        body.provider,
    ]
    if not any(filter_values):
        raise HTTPException(
            status_code=400,
            detail=(
                "At least one filter (start_date, end_date, username, "
                "project, model, or provider) must be provided for a purge operation."
            ),
        )

    reader = _get_reader()

    logger.info(
        "Admin purging logs (start=%s end=%s user=%s project=%s model=%s provider=%s)",
        body.start_date, body.end_date, body.username,
        body.project, body.model, body.provider,
    )

    deleted_count: int = reader.delete_events(
        start_date=body.start_date,
        end_date=body.end_date,
        username=body.username,
        project=body.project,
        model=body.model,
        provider=body.provider,
    )

    logger.info("Admin purge complete: %d log entries deleted", deleted_count)

    return PurgeResponse(ok=True, deleted=deleted_count)

# Made with ❤️ by codx-junior