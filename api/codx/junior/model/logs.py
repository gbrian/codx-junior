"""
Pydantic models for AI raw log records.

These models reflect the exact schema written by
:class:`~codx.junior.ai.raw_logger.RawAILogger` and read back by
:class:`~codx.junior.ai.raw_log_reader.RawLogReader`.

Diagram:
--------
```mermaid
classDiagram
    class RawLogRecord {
        +str log_id
        +str timestamp
        +str direction
        +str status
        +str request_id
        +Optional[str] parent_request_id
        +str provider
        +str model
        +str base_url
        +str username
        +str project
        +Optional[str] session_id
        +str tags
        +Optional[float] duration_seconds
        +Optional[RawLogPayload] payload
    }

    class RequestPayload {
        +Dict kwargs
        +List messages
    }

    class ResponsePayload {
        +str content
        +Optional[str] finish_reason
        +Dict tool_calls
    }

    class ErrorPayload {
        +str error_type
        +str error_message
    }

    class RawLogPayload {
        +Optional[Dict] kwargs
        +Optional[List] messages
        +Optional[str] content
        +Optional[str] finish_reason
        +Optional[Dict] tool_calls
        +Optional[str] error_type
        +Optional[str] error_message
    }

    RawLogRecord --> RawLogPayload
    RawLogPayload --|> RequestPayload : request direction
    RawLogPayload --|> ResponsePayload : response direction
    RawLogPayload --|> ErrorPayload : error status
```
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Payload sub-models ─────────────────────────────────────────────────────────


class RequestPayload(BaseModel):
    """
    Payload logged for an outgoing AI **request**.

    Written by :meth:`~codx.junior.ai.raw_logger.RawAILogger.log_request`.
    """

    kwargs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional keyword arguments passed to the completion call "
                    "(e.g. temperature, stream, tools). Excludes the messages list.",
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="The OpenAI-compatible messages array sent to the model.",
    )


class ResponsePayload(BaseModel):
    """
    Payload logged for a successful AI **response**.

    Written by :meth:`~codx.junior.ai.raw_logger.RawAILogger.log_response`.
    """

    content: str = Field(
        default="",
        description="Reconstructed full text content from streamed chunks.",
    )
    finish_reason: Optional[str] = Field(
        default=None,
        description="Final finish_reason from the last stream chunk "
                    "(e.g. 'stop', 'tool_calls', 'length').",
    )
    tool_calls: Dict[str, Any] = Field(
        default_factory=dict,
        description="Accumulated tool-call data dict keyed by tool-call id.",
    )


class ErrorPayload(BaseModel):
    """
    Payload logged when a request **fails or is cancelled**.

    Written by :meth:`~codx.junior.ai.raw_logger.RawAILogger.log_error`.
    """

    error_type: str = Field(
        default="",
        description="Exception class name (e.g. 'TimeoutError', 'CancelledError').",
    )
    error_message: str = Field(
        default="",
        description="String representation of the exception.",
    )


class RawLogPayload(BaseModel):
    """
    Union-like payload model that can represent request, response, or error
    payloads.  Fields from all three variants are present and optional so that
    a single model can deserialise any record without knowing its direction
    or status up front.
    """

    # ── Request fields ─────────────────────────────────────────────────────
    kwargs: Optional[Dict[str, Any]] = Field(
        default=None,
        description="[request] Keyword args passed to the completion call.",
    )
    messages: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="[request] OpenAI-compatible messages array.",
    )

    # ── Response fields ────────────────────────────────────────────────────
    content: Optional[str] = Field(
        default=None,
        description="[response] Reconstructed full text content.",
    )
    finish_reason: Optional[str] = Field(
        default=None,
        description="[response] finish_reason from the last stream chunk.",
    )
    tool_calls: Optional[Dict[str, Any]] = Field(
        default=None,
        description="[response] Accumulated tool-call data.",
    )

    # ── Error fields ───────────────────────────────────────────────────────
    error_type: Optional[str] = Field(
        default=None,
        description="[error] Exception class name.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="[error] String representation of the exception.",
    )


# ── Top-level record model ─────────────────────────────────────────────────────


class RawLogRecord(BaseModel):
    """
    Full representation of a single line in a ``*_raw_ai.jsonl`` file.

    The ``log_id`` field is **not** written by :class:`RawAILogger`; it is
    injected by :class:`~codx.junior.ai.raw_log_reader.RawLogReader` using
    the pattern ``<YYYY-MM-DD>:<line_index>``.

    Status constants (mirrored from :mod:`codx.junior.ai.raw_logger`):

    - ``"success"``   – request completed normally.
    - ``"cancelled"`` – request was cancelled before completion.
    - ``"error"``     – request failed with an exception.
    """

    # ── Reader-injected ────────────────────────────────────────────────────
    log_id: str = Field(
        description="Synthetic unique id: '<YYYY-MM-DD>:<line_index>'.",
    )

    # ── Core envelope fields (written by RawAILogger._base_record) ─────────
    timestamp: str = Field(
        description="ISO-8601 UTC timestamp of when the record was written.",
    )
    direction: str = Field(
        description="'request' for outgoing calls, 'response' for replies/errors.",
    )
    status: str = Field(
        description="Outcome status: 'success' | 'cancelled' | 'error'.",
    )
    request_id: str = Field(
        description="Unique UUID that pairs a request record with its response record.",
    )
    parent_request_id: Optional[str] = Field(
        default=None,
        description="request_id of the parent call when spawned from a tool-call response.",
    )
    provider: str = Field(
        description="Provider identifier, e.g. 'openai', 'litellm'.",
    )
    model: str = Field(
        description="Model name used for the completion call.",
    )
    base_url: str = Field(
        description="API base URL of the provider endpoint.",
    )
    username: str = Field(
        description="Requesting user (or 'anonymous').",
    )
    project: str = Field(
        description="Project name associated with the request.",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session or conversation id.",
    )
    tags: str = Field(
        default="",
        description="Comma-separated tag string.",
    )

    # ── Response-only top-level field ──────────────────────────────────────
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Wall-clock duration in seconds. Present on response/error records only.",
    )

    # ── Payload ────────────────────────────────────────────────────────────
    payload: Optional[RawLogPayload] = Field(
        default=None,
        description="Direction-specific payload. See RawLogPayload for field details.",
    )


# ── List / pagination wrappers ─────────────────────────────────────────────────


class RawLogRecordSummary(BaseModel):
    """
    Lightweight summary of a :class:`RawLogRecord` suitable for list views.

    The ``payload`` is replaced with a short ``payload_preview`` string to
    keep response sizes manageable when listing many records.
    """

    log_id: str
    timestamp: str
    direction: str
    status: str
    request_id: str
    parent_request_id: Optional[str] = None
    provider: str
    model: str
    base_url: str
    username: str
    project: str
    session_id: Optional[str] = None
    tags: str = ""
    duration_seconds: Optional[float] = None
    payload_preview: Optional[str] = Field(
        default=None,
        description="First 200 characters of the payload string representation.",
    )
    tools: Optional[dict]


class RawLogListResponse(BaseModel):
    """Paginated list of :class:`RawLogRecordSummary` items."""

    items: List[RawLogRecordSummary]
    total: int = Field(description="Total number of records matching the filters.")
    page: int = Field(description="Current 1-based page number.")
    page_size: int = Field(description="Number of items per page.")
    has_more: bool = Field(description="True when further pages exist.")


class PurgeRequest(BaseModel):
    """Request body for bulk log deletion."""

    start_date: Optional[str] = Field(
        default=None,
        description="Inclusive lower bound YYYY-MM-DD.",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Inclusive upper bound YYYY-MM-DD.",
    )
    username: Optional[str] = Field(default=None, description="Filter by username.")
    project: Optional[str] = Field(default=None, description="Filter by project name.")
    model: Optional[str] = Field(default=None, description="Filter by model name.")
    provider: Optional[str] = Field(default=None, description="Filter by provider name.")


class PurgeResponse(BaseModel):
    """Response body returned after a purge operation."""

    ok: bool
    deleted: int = Field(description="Number of log records deleted.")