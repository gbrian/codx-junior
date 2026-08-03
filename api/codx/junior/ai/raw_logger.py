import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from codx.junior.globals import CODX_JUNIOR_AI_RAW_LOG_PATH

logger = logging.getLogger(__name__)

FILE_DATE_FORMAT = "%Y-%m-%d"
_lock = threading.Lock()

# Status constants
STATUS_SUCCESS   = "success"
STATUS_CANCELLED = "cancelled"
STATUS_ERROR     = "error"


def _get_log_path() -> str:
    """Resolve the raw AI log directory from settings or environment."""
    path = CODX_JUNIOR_AI_RAW_LOG_PATH
    os.makedirs(path, exist_ok=True)
    return path or None


class RawAILogger:
    """
    Writes raw OpenAI request and response payloads to per-day JSONL files.

    File layout:
        <raw_log_path>/<YYYY-MM-DD>_raw_ai.jsonl

    Each line is a JSON object with the following top-level keys:
        - timestamp        : ISO-8601 UTC timestamp
        - direction        : "request" | "response"
        - status           : "success" | "cancelled" | "error"
        - request_id       : unique UUID per request/response pair
        - parent_request_id: request_id of the parent call when spawned from a tool call
        - provider         : e.g. "openai", "litellm"
        - model            : model name
        - base_url         : API base URL
        - username         : requesting user (or "anonymous")
        - project          : project name
        - session_id       : optional session/conversation id
        - tags             : comma-separated tag string
        - payload          : the raw dict being logged

    Diagram:
    classDiagram
        class RawAILogger {
            +str base_path
            +log_request(provider, model, base_url, username, project, session_id, tags, messages, kwargs, request_id, parent_request_id) str
            +log_response(provider, model, base_url, username, project, session_id, tags, content_parts, finish_reason, tool_calls, duration_seconds, request_id, parent_request_id, status)
            +log_error(provider, model, base_url, username, project, session_id, tags, error, duration_seconds, request_id, parent_request_id, status)
        }
    """

    def __init__(self):
        self.base_path = _get_log_path()
        logger.info("RawAILogger initialised at: %s", self.base_path)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _file_path(self) -> str:
        today = datetime.utcnow().strftime(FILE_DATE_FORMAT)
        return os.path.join(self.base_path, f"{today}_raw_ai.jsonl")

    def _write(self, record: Dict[str, Any]) -> None:
        """Append one JSON record to today's file (thread-safe)."""
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _lock:
            try:
                with open(self._file_path(), "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except Exception as ex:
                logger.error("RawAILogger._write failed: %s", ex)

    def _base_record(
        self,
        direction: str,
        provider: str,
        model: str,
        base_url: str,
        username: str,
        project: str,
        session_id: Optional[str],
        tags: str,
        request_id: str,
        parent_request_id: Optional[str],
        status: str = STATUS_SUCCESS,
    ) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "direction": direction,
            "status": status,
            "request_id": request_id,
            "parent_request_id": parent_request_id,
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "username": username,
            "project": project,
            "session_id": session_id,
            "tags": tags,
        }

    # ── Public API ─────────────────────────────────────────────────────────────

    def log_request(
        self,
        *,
        provider: str,
        model: str,
        base_url: str,
        username: str,
        project: str,
        session_id: Optional[str],
        tags: str,
        messages: List[Dict[str, Any]],
        kwargs: Dict[str, Any],
        request_id: str,
        parent_request_id: Optional[str] = None,
    ) -> None:
        """
        Log the full outgoing request payload.

        Args:
            provider:          Provider identifier (e.g. ``"openai"``).
            model:             Model name.
            base_url:          API endpoint base URL.
            username:          Requesting user.
            project:           Project name.
            session_id:        Optional session/conversation id.
            tags:              Comma-separated tag string.
            messages:          The ``openai_messages`` list sent to the API.
            kwargs:            Additional keyword args passed to
                            ``client.chat.completions.create``
                            (model, temperature, stream, tools, etc.).
            request_id:        Unique identifier for this request/response pair.
            parent_request_id: ``request_id`` of the parent call when this
                            request was spawned from a tool-call response.
        """
        # Exclude large/non-serialisable items from kwargs safely
        safe_kwargs = {k: v for k, v in kwargs.items() if k != "messages"}

        tools = None
        if "tools" in kwargs:
            tools = kwargs["tools"]
            # Remove the tools key from kwargs to avoid duplication in payload
            del safe_kwargs["tools"]

        record = self._base_record(
            direction="request",
            provider=provider,
            model=model,
            base_url=base_url,
            username=username,
            project=project,
            session_id=session_id,
            tags=tags,
            request_id=request_id,
            parent_request_id=parent_request_id,
            status=STATUS_SUCCESS,
        )
        record["payload"] = {
            "kwargs": safe_kwargs,
            "messages": messages,
            "tools": tools,
        }
        self._write(record)
        logger.debug(
            "RawAILogger.log_request: request_id=%s parent=%s provider=%s model=%s user=%s messages=%d",
            request_id, parent_request_id, provider, model, username, len(messages),
        )

    def log_response(
        self,
        *,
        provider: str,
        model: str,
        base_url: str,
        username: str,
        project: str,
        session_id: Optional[str],
        tags: str,
        content_parts: List[str],
        finish_reason: Optional[str] = None,
        tool_calls: Optional[Dict[str, Any]] = None,
        duration_seconds: float = 0.0,
        request_id: str,
        parent_request_id: Optional[str] = None,
        status: str = STATUS_SUCCESS,
    ) -> None:
        """
        Log the reassembled response payload after streaming is complete.

        Args:
            provider:          Provider identifier.
            model:             Model name.
            base_url:          API endpoint base URL.
            username:          Requesting user.
            project:           Project name.
            session_id:        Optional session/conversation id.
            tags:              Comma-separated tag string.
            content_parts:     Accumulated text chunks (joined to reconstruct content).
            finish_reason:     Final ``finish_reason`` from the last stream chunk.
            tool_calls:        Accumulated tool-call data dict (keyed by tool-call id).
            duration_seconds:  Total wall-clock duration of the streaming call.
            request_id:        Unique identifier matching the paired ``log_request`` call.
            parent_request_id: ``request_id`` of the parent call when this
                               request was spawned from a tool-call response.
            status:            Outcome status: "success" | "cancelled" | "error".
        """
        record = self._base_record(
            direction="response",
            provider=provider,
            model=model,
            base_url=base_url,
            username=username,
            project=project,
            session_id=session_id,
            tags=tags,
            request_id=request_id,
            parent_request_id=parent_request_id,
            status=status,
        )
        record["duration_seconds"] = duration_seconds
        record["payload"] = {
            "content": "".join(content_parts),
            "finish_reason": finish_reason,
            "tool_calls": tool_calls or {},
        }
        self._write(record)
        logger.debug(
            "RawAILogger.log_response: request_id=%s parent=%s status=%s provider=%s model=%s user=%s "
            "content_len=%d finish_reason=%s duration=%.2fs",
            request_id, parent_request_id, status, provider, model, username,
            len("".join(content_parts)),
            finish_reason,
            duration_seconds,
        )

    def log_error(
        self,
        *,
        provider: str,
        model: str,
        base_url: str,
        username: str,
        project: str,
        session_id: Optional[str],
        tags: str,
        error: Exception,
        duration_seconds: float = 0.0,
        request_id: str,
        parent_request_id: Optional[str] = None,
        status: str = STATUS_ERROR,
    ) -> None:
        """
        Log a failed or cancelled request that never produced a valid response.

        Args:
            provider:          Provider identifier.
            model:             Model name.
            base_url:          API endpoint base URL.
            username:          Requesting user.
            project:           Project name.
            session_id:        Optional session/conversation id.
            tags:              Comma-separated tag string.
            error:             The exception that caused the failure.
            duration_seconds:  Wall-clock time elapsed before the failure.
            request_id:        Unique identifier matching the paired ``log_request`` call.
            parent_request_id: ``request_id`` of the parent call.
            status:            "cancelled" or "error" (default ``"error"``).
        """
        record = self._base_record(
            direction="response",
            provider=provider,
            model=model,
            base_url=base_url,
            username=username,
            project=project,
            session_id=session_id,
            tags=tags,
            request_id=request_id,
            parent_request_id=parent_request_id,
            status=status,
        )
        record["duration_seconds"] = duration_seconds
        record["payload"] = {
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        self._write(record)
        logger.debug(
            "RawAILogger.log_error: request_id=%s parent=%s status=%s provider=%s model=%s user=%s "
            "error=%s duration=%.2fs",
            request_id, parent_request_id, status, provider, model, username,
            type(error).__name__,
            duration_seconds,
        )