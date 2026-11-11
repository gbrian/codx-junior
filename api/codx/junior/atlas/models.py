"""
Plain data objects returned by the project atlas.

They are intentionally dependency-free (dataclasses only): tool rendering and
API serialization both consume them without pulling in pydantic or LangChain.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Evidence:
    """One locator the model can open directly."""

    path: str
    start_line: int = 1
    end_line: int = 1
    kind: str = "file"
    name: str = ""
    why: str = ""
    score: float = 0.0
    snippet: str = ""
    stale: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def location(self) -> str:
        if self.start_line and self.start_line > 0:
            if self.end_line and self.end_line != self.start_line:
                return f"{self.path}:{self.start_line}-{self.end_line}"
            return f"{self.path}:{self.start_line}"
        return self.path

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["location"] = self.location
        return data


@dataclass
class AtlasPacket:
    """Compact answer packet: answer + evidence + gaps + freshness."""

    query: str
    intent: str
    answer: str
    evidence: List[Evidence] = field(default_factory=list)
    reading_order: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    next_probes: List[str] = field(default_factory=list)
    confidence: float = 0.0
    generation: Dict[str, Any] = field(default_factory=dict)
    stale: bool = False
    #: Optional pre-rendered body (the map table is not an "answer" sentence).
    body: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "answer": self.answer,
            "confidence": round(float(self.confidence or 0.0), 2),
            "evidence": [item.to_dict() for item in self.evidence],
            "reading_order": list(self.reading_order),
            "gaps": list(self.gaps),
            "next_probes": list(self.next_probes),
            "generation": dict(self.generation),
            "stale": bool(self.stale),
            "body": self.body,
        }

    def to_markdown(self) -> str:
        """Render a token-efficient packet the model can act on."""
        if self.body:
            return self.body.strip()
        generation = self.generation or {}
        header = (
            f"> atlas: {len(self.evidence)} evidence(s) | "
            f"confidence {self.confidence:.2f} | "
            f"{generation.get('commit', 'no-git')}"
            f"{' +dirty' if generation.get('dirty') else ''} | "
            f"{'STALE' if self.stale else 'fresh'}"
        )
        lines: List[str] = [header, ""]

        if self.answer:
            lines.extend([f"**{self.answer}**", ""])

        if self.evidence:
            lines.append("### Evidence")
            for index, item in enumerate(self.evidence, 1):
                name = f" `{item.name}`" if item.name and item.name not in item.path else ""
                lines.append(
                    f"{index}. `{item.location}` — {item.kind}{name}"
                    f"{' — STALE' if item.stale else ''}"
                )
                if item.why:
                    lines.append(f"   - {item.why}")
                if item.snippet:
                    for snippet_line in item.snippet.splitlines()[:8]:
                        lines.append(f"   `{snippet_line}`")
            lines.append("")

        if self.reading_order:
            lines.append("### Reading order")
            for index, location in enumerate(self.reading_order, 1):
                lines.append(f"{index}. `{location}`")
            lines.append("")

        if self.gaps:
            lines.append("### Gaps")
            lines.extend(f"- {gap}" for gap in self.gaps)
            lines.append("")

        if self.next_probes:
            lines.append("### Next probes")
            lines.extend(f"- {probe}" for probe in self.next_probes)
            lines.append("")

        return "\n".join(lines).strip()


@dataclass
class AtlasHealth:
    """Index health, surfaced to the model and the API."""

    project: str = ""
    root: str = ""
    db_path: str = ""
    built_at: float = 0.0
    commit: str = ""
    dirty: bool = False
    index_version: int = 0
    files: int = 0
    symbols: int = 0
    routes: int = 0
    docs: int = 0
    tests: int = 0
    edges: int = 0
    domains: int = 0
    db_bytes: int = 0
    duration_seconds: float = 0.0
    truncated: bool = False
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = [
            f"> atlas health: {self.files} files, {self.symbols} symbols, "
            f"{self.edges} edges | {self.commit or 'no-git'}"
            f"{' +dirty' if self.dirty else ''}",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Project | `{self.project}` |",
            f"| Root | `{self.root}` |",
            f"| Files | {self.files} |",
            f"| Symbols | {self.symbols} |",
            f"| Routes | {self.routes} |",
            f"| Docs | {self.docs} |",
            f"| Tests | {self.tests} |",
            f"| Edges | {self.edges} |",
            f"| Domains | {self.domains} |",
            f"| Database | {self.db_bytes / 1024 / 1024:.1f} MB |",
            f"| Built in | {self.duration_seconds:.2f}s |",
        ]
        if self.truncated:
            lines.append("| Truncated | yes (file cap reached) |")
        if self.warnings:
            lines.extend(["", "### Warnings"] + [f"- {warning}" for warning in self.warnings])
        return "\n".join(lines)
