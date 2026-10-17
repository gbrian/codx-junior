"""
Typed models for decision-model analytics.

Decision models are the local/typed deciders used by the chat organization
process (see :mod:`codx.junior.organizer`), for example the ``vegaml`` typed
runtime behind
:class:`codx.junior.organizer.engines.StructuredOrganizationEngine`.

Every time such a model is asked to decide something a
:class:`DecisionModelEvent` is persisted (see
:class:`codx.junior.analytics.storage.AnalyticsStorage`) so the decision can be
audited afterwards: what was asked, what the model answered, the calibrated
probabilities, whether it abstained and how long it took.

The shape mirrors :mod:`codx.junior.analytics.model` so the same storage and
query helpers can be reused.

The module also exposes the client-facing request/response models used by the
analytics API (:class:`DecisionModelQuery`, :class:`DecisionModelEventList` and
:class:`DecisionModelMetrics`) so both the read endpoints and their consumers
share the same contract.

```mermaid
classDiagram
    class DecisionModelEvent {
        +str event_id
        +float timestamp
        +str decision_type
        +str engine
        +str model
        +str username
        +str project_name
        +str project_id
        +Optional~str~ chat_id
        +str state
        +List~str~ questions
        +Dict~str,str~ choices
        +Dict~str,Dict~str,float~~ probs
        +Optional~str~ choice
        +Optional~float~ confidence
        +bool abstained
        +bool success
        +float duration_seconds
        +str iso_date
        +to_dict() dict
        +from_dict(data) DecisionModelEvent
    }
    class DecisionModelQuery {
        +date filters
        +int limit
        +int offset
        +filters() dict
    }
    class DecisionModelEventList {
        +List~DecisionModelEvent~ events
        +int total
        +Optional~int~ limit
        +int offset
        +from_events(events, limit, offset) DecisionModelEventList
    }
    class DecisionModelMetrics {
        +str group_by
        +Dict metrics
        +int total_calls
        +from_metrics(group_by, metrics) DecisionModelMetrics
    }
    DecisionModelEventList "1" o-- "many" DecisionModelEvent
```
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _utc_now_timestamp() -> float:
    """Current UTC time as a unix timestamp (float seconds)."""
    return datetime.utcnow().timestamp()


class DecisionModelEvent(BaseModel):
    """
    A single decision-model invocation.

    Records both the *input* the model reasoned about (``state``) and its
    *output* (``choices`` / ``probs`` / ``abstained`` / ``confidence``), plus
    the identifiers needed to correlate the decision with a chat, a request
    and the surrounding token/tool analytics events.
    """

    event_id: str = Field(
        default="", description="Unique identifier for this decision event"
    )
    timestamp: float = Field(
        default_factory=_utc_now_timestamp,
        description="Unix timestamp (UTC) the decision was taken",
    )
    decision_type: str = Field(
        default="",
        description="What is being decided (e.g. 'chat_organization')",
    )
    engine: str = Field(
        default="",
        description="Engine that produced the decision (e.g. 'structured')",
    )
    model: str = Field(
        default="",
        description="Decision model name/variant (e.g. '0.8b')",
    )

    username: str = Field(default="", description="User context")
    project_name: str = Field(default="", description="Project context name")
    project_id: str = Field(default="", description="Project identifier")
    chat_id: Optional[str] = Field(
        default=None, description="Chat the decision belongs to"
    )
    session_id: Optional[str] = Field(
        default=None, description="Optional conversation/session id"
    )
    request_id: Optional[str] = Field(
        default=None, description="Optional request id for traceability"
    )

    state: str = Field(
        default="", description="Textual state the model reasoned about"
    )
    questions: List[str] = Field(
        default_factory=list, description="Question keys asked to the model"
    )
    choices: Dict[str, str] = Field(
        default_factory=dict,
        description="Chosen answer per question key",
    )
    probs: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Calibrated probabilities per question key",
    )

    choice: Optional[str] = Field(
        default=None, description="Primary selected answer"
    )
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence of the primary answer in [0, 1] when available",
    )
    abstained: bool = Field(
        default=False, description="Model refused to decide"
    )

    success: bool = Field(
        default=True, description="Whether the model produced a usable answer"
    )
    error: Optional[str] = Field(
        default=None, description="Error message when the model failed"
    )
    duration_seconds: float = Field(
        default=0.0, description="Wall-clock seconds for the decision call"
    )
    reason: str = Field(
        default="", description="Human readable explanation (logging)"
    )
    tags: str = Field(
        default="", description="Comma-separated tags for filtering"
    )

    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw model output kept for forensic audit",
    )

    @property
    def iso_date(self) -> str:
        """UTC date (YYYY-MM-DD) the event belongs to (used for partitioning)."""
        return datetime.utcfromtimestamp(self.timestamp).strftime("%Y-%m-%d")

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-friendly dict."""
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionModelEvent":
        """Deserialise from a stored dict, ignoring unknown keys."""
        if not isinstance(data, dict):
            return cls()
        fields = getattr(cls, "model_fields", None) or getattr(cls, "__fields__", {})
        known = {key: value for key, value in data.items() if key in fields}
        return cls(**known)


class DecisionModelQuery(BaseModel):
    """
    Client request model for querying decision-model analytics.

    Every field is optional; omitted fields are treated as "no filter". Both
    the GET endpoints (query parameters) and the POST search endpoint (JSON
    body) accept these filters, so clients can pick whichever is convenient.

    ``limit``/``offset`` paginate the (timestamp-ordered) result set:
    ``total`` is always the full match count, ``events`` the requested slice.
    """

    start_date: Optional[str] = Field(
        default=None, description="Inclusive ISO date lower bound (YYYY-MM-DD)"
    )
    end_date: Optional[str] = Field(
        default=None, description="Inclusive ISO date upper bound (YYYY-MM-DD)"
    )
    chat_id: Optional[str] = Field(
        default=None, description="Filter by chat id"
    )
    decision_type: Optional[str] = Field(
        default=None, description="Filter by decision type"
    )
    engine: Optional[str] = Field(
        default=None, description="Filter by engine"
    )
    model: Optional[str] = Field(
        default=None, description="Filter by decision model"
    )
    username: Optional[str] = Field(
        default=None, description="Filter by username"
    )
    project_name: Optional[str] = Field(
        default=None, description="Filter by project name"
    )
    project_id: Optional[str] = Field(
        default=None, description="Filter by project id"
    )
    success: Optional[bool] = Field(
        default=None, description="Filter by success flag"
    )
    limit: Optional[int] = Field(
        default=None, description="Maximum number of events to return"
    )
    offset: int = Field(
        default=0, description="Number of events to skip (pagination)"
    )

    def filters(self) -> Dict[str, Any]:
        """Return only the storage-level filters (pagination excluded)."""
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "chat_id": self.chat_id,
            "decision_type": self.decision_type,
            "engine": self.engine,
            "model": self.model,
            "username": self.username,
            "project_name": self.project_name,
            "project_id": self.project_id,
            "success": self.success,
        }


class DecisionModelEventList(BaseModel):
    """Client response model: a (optionally paginated) list of decision events."""

    events: List[DecisionModelEvent] = Field(
        default_factory=list,
        description="Matching decision events ordered by timestamp",
    )
    total: int = Field(
        default=0,
        description="Total events matching the filters (before pagination)",
    )
    limit: Optional[int] = Field(
        default=None, description="Applied limit, when any"
    )
    offset: int = Field(default=0, description="Applied offset")

    @classmethod
    def from_events(
        cls,
        events: List[DecisionModelEvent],
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> "DecisionModelEventList":
        """Build a paginated response from a full, ordered list of events."""
        events = list(events or [])
        sliced = events[offset:] if offset else events
        if limit is not None:
            sliced = sliced[:limit]
        return cls(events=sliced, total=len(events), limit=limit, offset=offset)


class DecisionModelMetrics(BaseModel):
    """Client response model: aggregations across decision-model events."""

    group_by: str = Field(
        default="model", description="Key the metrics are grouped by"
    )
    metrics: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Aggregated metrics per group key",
    )
    total_calls: int = Field(
        default=0, description="Total decision calls across all groups"
    )

    @classmethod
    def from_metrics(
        cls,
        group_by: str,
        metrics: Dict[str, Dict[str, Any]],
    ) -> "DecisionModelMetrics":
        """Wrap the analytics aggregation result with a total call count."""
        metrics = metrics or {}
        total_calls = sum(
            int((bucket or {}).get("calls", 0) or 0)
            for bucket in metrics.values()
        )
        return cls(group_by=group_by, metrics=metrics, total_calls=total_calls)


# Made with ❤️ by codx-junior