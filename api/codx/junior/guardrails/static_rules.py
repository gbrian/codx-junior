"""Deterministic, near-zero-cost guardrail detectors.

These run before any LLM call and catch the most common prompt-injection and
secret-extraction attempts with regular expressions. They are intentionally
conservative: only obvious patterns are flagged at HIGH severity.
"""
import re
from typing import List

from codx.junior.guardrails.models import (
    GuardrailDetection,
    GuardrailSeverity,
)

# Patterns that clearly indicate an attempt to override the assistant's
# instructions or role.
_HIGH_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|rules|messages)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(DAN|an?\s+unfiltered|a\s+different\s+model)", re.IGNORECASE),
    re.compile(r"(reveal|show|print|disclose|repeat)\s+(your\s+)?(system\s+prompt|hidden\s+instructions|initial\s+instructions|developer\s+message)", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(your\s+)?(rules|instructions|guidelines)", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+are|to\s+be|that\s+you\s+are)", re.IGNORECASE),
]

# Patterns that warrant suspicion but may have legitimate uses.
_MEDIUM_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"\bDAN\s+mode\b", re.IGNORECASE),
    re.compile(r"bypass\s+(your\s+)?(content\s+)?(filter|safety|guardrail|restrictions)", re.IGNORECASE),
]

_SECRET_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(api[_-]?key|api[_-]?secret|access[_-]?token|auth[_-]?token|refresh[_-]?token)\b", re.IGNORECASE),
    re.compile(r"\b(environment\s+variables|\.env(\s+file)?)\b", re.IGNORECASE),
    re.compile(r"\b(private\s+key|secret\s+key)\b", re.IGNORECASE),
]


def _excerpt(text: str, match: re.Match, radius: int = 40) -> str:
    """Return a short excerpt around *match* for audit logging."""
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    return text[start:end]


def detect_input(text: str) -> List[GuardrailDetection]:
    """Run static input detectors and return any detections found."""
    detections: List[GuardrailDetection] = []

    for pattern in _HIGH_INJECTION_PATTERNS:
        match = pattern.search(text or "")
        if match:
            detections.append(GuardrailDetection(
                severity=GuardrailSeverity.HIGH,
                category="injection",
                reason=f"matched high-severity injection pattern: {pattern.pattern}",
                excerpt=_excerpt(text or "", match),
            ))
            break

    if not any(d.severity == GuardrailSeverity.HIGH for d in detections):
        for pattern in _MEDIUM_INJECTION_PATTERNS:
            match = pattern.search(text or "")
            if match:
                detections.append(GuardrailDetection(
                    severity=GuardrailSeverity.MEDIUM,
                    category="injection",
                    reason=f"matched medium-severity injection pattern: {pattern.pattern}",
                    excerpt=_excerpt(text or "", match),
                ))
                break

    for pattern in _SECRET_PATTERNS:
        match = pattern.search(text or "")
        if match:
            detections.append(GuardrailDetection(
                severity=GuardrailSeverity.MEDIUM,
                category="secret",
                reason=f"matched secret-extraction pattern: {pattern.pattern}",
                excerpt=_excerpt(text or "", match),
            ))
            break

    return detections


def detect_output(text: str) -> List[GuardrailDetection]:
    """Run static output detectors (e.g. leaked secrets / echoed injections)."""
    detections: List[GuardrailDetection] = []

    for pattern in _SECRET_PATTERNS:
        match = pattern.search(text or "")
        if match:
            detections.append(GuardrailDetection(
                severity=GuardrailSeverity.HIGH,
                category="secret",
                reason=f"response contains a potential secret: {pattern.pattern}",
                excerpt=_excerpt(text or "", match),
            ))
            break

    # The model echoing an obvious instruction-override is a strong signal
    # that it was successfully jailbroken.
    for pattern in _HIGH_INJECTION_PATTERNS:
        match = pattern.search(text or "")
        if match:
            detections.append(GuardrailDetection(
                severity=GuardrailSeverity.MEDIUM,
                category="output",
                reason=f"response echoed an injection pattern: {pattern.pattern}",
                excerpt=_excerpt(text or "", match),
            ))
            break

    return detections