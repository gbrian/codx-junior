"""Data models for the guardrail subsystem.

These models carry detection signals (severity, category, reason) and the
deterministic decision produced by the policy engine. Severity levels are
ordered by ``SEVERITY_WEIGHTS`` so escalation can be computed cumulatively.
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GuardrailSeverity(str, Enum):
    """Severity of a detected guardrail violation."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SEVERITY_WEIGHTS: Dict[GuardrailSeverity, float] = {
    GuardrailSeverity.INFO: 0.0,
    GuardrailSeverity.LOW: 1.0,
    GuardrailSeverity.MEDIUM: 3.0,
    GuardrailSeverity.HIGH: 7.0,
    GuardrailSeverity.CRITICAL: 100.0,
}


class GuardrailAction(str, Enum):
    """Action the policy engine decided to take."""

    PASS = "pass"
    REFUSE = "refuse"
    BLOCK = "block"


class GuardrailDetection(BaseModel):
    """A single detection signal produced by a detector."""

    severity: GuardrailSeverity
    category: str = Field(
        description="Detection category: injection | secret | scope | tool | output"
    )
    reason: str = ""
    confidence: Optional[float] = Field(default=None)
    excerpt: str = Field(default="", description="Short excerpt of the offending text")


class GuardrailVerdict(BaseModel):
    """Aggregated decision produced by the policy engine."""

    action: GuardrailAction = GuardrailAction.PASS
    blocked: bool = False
    disable_tools: bool = False
    risk_score: float = 0.0
    highest_severity: Optional[GuardrailSeverity] = None
    detections: List[GuardrailDetection] = Field(default_factory=list)
    refusal_message: str = ""
    scope_instructions: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation for message meta_data."""
        return self.model_dump(mode="json")