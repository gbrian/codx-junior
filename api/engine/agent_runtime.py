"""
Unified logging, event emission and cancellation for agent runs.
Wraps openai_ai without modifying it: openai_ai's stream/tool callbacks
are adapted onto AgentRunContext.
"""
import json
import logging
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Iterator

logger = logging.getLogger("codx.agent")


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class AgentCancelled(Exception):
    """Raised at checkpoints when the run has been cancelled."""


class InsufficientFundsError(Exception):
    """Raised by the wallet pre-flight check."""


# --------------------------------------------------------------------------- #
# Cancellation
# --------------------------------------------------------------------------- #
class CancellationToken:
    """Thread-safe cancellation token. cancel() may be called from any thread
    (e.g. a Socket.IO 'stop' handler) while the agent loop runs elsewhere."""

    def __init__(self):
        self._event = threading.Event()
        self.reason: str | None = None

    def cancel(self, reason: str = "user_requested"):
        self.reason = reason
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self):
        if self._event.is_set():
            raise AgentCancelled(self.reason or "cancelled")


# --------------------------------------------------------------------------- #
# Events
# --------------------------------------------------------------------------- #
class AgentEventType(str, Enum):
    RUN_START = "run_start"
    RUN_END = "run_end"
    RUN_ERROR = "run_error"
    RUN_CANCELLED = "run_cancelled"
    LLM_REQUEST = "llm_request"
    LLM_CHUNK = "llm_chunk"
    LLM_USAGE = "llm_usage"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_ERROR = "tool_error"
    WALLET_CHECK = "wallet_check"


@dataclass
class AgentEvent:
    type: AgentEventType
    run_id: str
    project_id: str
    payload: dict = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"type": self.type.value, "run_id": self.run_id,
                "project_id": self.project_id, "ts": self.ts, **self.payload}


# --------------------------------------------------------------------------- #
# Analytics (tokens & tools) — fed automatically by emit()
# --------------------------------------------------------------------------- #
@dataclass
class RunAnalytics:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_calls: dict = field(default_factory=dict)   # name -> {count, errors, total_ms}

    def on_event(self, event: AgentEvent):
        p = event.payload
        if event.type == AgentEventType.LLM_USAGE:
            self.prompt_tokens += p.get("prompt_tokens", 0)
            self.completion_tokens += p.get("completion_tokens", 0)
        elif event.type in (AgentEventType.TOOL_END, AgentEventType.TOOL_ERROR):
            stats = self.tool_calls.setdefault(
                p.get("tool", "unknown"), {"count": 0, "errors": 0, "total_ms": 0.0})
            stats["count"] += 1
            stats["total_ms"] += p.get("duration_ms", 0.0)
            if event.type == AgentEventType.TOOL_ERROR:
                stats["errors"] += 1

    def summary(self) -> dict:
        return {"prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.prompt_tokens + self.completion_tokens,
                "tools": self.tool_calls}


# --------------------------------------------------------------------------- #
# Run context — the single object passed through the agent loop
# --------------------------------------------------------------------------- #
class AgentRunContext:
    def __init__(self, project_id: str,
                 listeners: list[Callable[[AgentEvent], Any]] | None = None,
                 chunk_emit_every: float = 0.25):
        self.run_id = uuid.uuid4().hex[:12]
        self.project_id = project_id
        self.token = CancellationToken()
        self.analytics = RunAnalytics()
        self._listeners = list(listeners or [])
        self._chunk_emit_every = chunk_emit_every  # throttle chunk events to UI
        self._last_chunk_emit = 0.0

    # -- events ------------------------------------------------------------ #
    def add_listener(self, fn: Callable[[AgentEvent], Any]):
        self._listeners.append(fn)

    def emit(self, type_: AgentEventType, **payload):
        event = AgentEvent(type_, self.run_id, self.project_id, payload)
        # 1. structured log — one line, machine-parseable, correlated by run_id
        logger.info(json.dumps(event.to_dict(), default=str))
        # 2. analytics
        self.analytics.on_event(event)
        # 3. fan-out — a broken listener must NEVER kill the run
        for fn in self._listeners:
            try:
                fn(event)
            except Exception:
                logger.exception("agent event listener failed (run=%s)", self.run_id)

    # -- cancellation ------------------------------------------------------ #
    def cancel(self, reason: str = "user_requested"):
        self.token.cancel(reason)

    def checkpoint(self):
        """Call anywhere it's safe to abort. Raises AgentCancelled."""
        self.token.raise_if_cancelled()

    def guard_stream(self, chunks: Iterable) -> Iterator:
        """Wrap an LLM stream: checks cancellation on EVERY chunk and emits
        throttled chunk events so the UI shows live progress."""
        for chunk in chunks:
            self.checkpoint()
            now = time.time()
            if now - self._last_chunk_emit >= self._chunk_emit_every:
                self._last_chunk_emit = now
                self.emit(AgentEventType.LLM_CHUNK, preview=str(chunk)[:120])
            yield chunk

    # -- tool instrumentation ---------------------------------------------- #
    @contextmanager
    def tool(self, name: str, **args):
        self.checkpoint()
        self.emit(AgentEventType.TOOL_START, tool=name, args=args)
        start = time.time()
        try:
            yield
        except AgentCancelled:
            raise
        except Exception as ex:
            self.emit(AgentEventType.TOOL_ERROR, tool=name,
                      duration_ms=(time.time() - start) * 1000, error=str(ex))
            raise
        else:
            self.emit(AgentEventType.TOOL_END, tool=name,
                      duration_ms=(time.time() - start) * 1000)

    # -- run lifecycle ------------------------------------------------------ #
    @contextmanager
    def run(self, wallet=None, estimated_cost: float = 0.0):
        # wallet pre-flight check BEFORE any tokens are spent
        if wallet is not None:
            balance = wallet.get_balance()
            self.emit(AgentEventType.WALLET_CHECK,
                      balance=balance, estimated_cost=estimated_cost)
            if balance < estimated_cost:
                raise InsufficientFundsError(
                    f"balance {balance} < estimated cost {estimated_cost}")

        self.emit(AgentEventType.RUN_START)
        try:
            yield self
        except AgentCancelled as ex:
            self.emit(AgentEventType.RUN_CANCELLED, reason=str(ex),
                      analytics=self.analytics.summary())
        except Exception as ex:
            self.emit(AgentEventType.RUN_ERROR, error=str(ex),
                      analytics=self.analytics.summary())
            raise
        else:
            self.emit(AgentEventType.RUN_END, analytics=self.analytics.summary())