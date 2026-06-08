from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import time


@dataclass
class TokenUsageEvent:
    """
    Represents a single LLM call with token consumption metadata.

    Fields:
        username:          The user who triggered the request.
        project_name:      The project context for the request.
        project_id:        The project identifier.
        model:             LLM model name used (e.g. "gpt-4o").
        provider:          LLM provider (e.g. "openai", "litellm").
        input_tokens:      Number of tokens in the prompt/input.
        output_tokens:     Number of tokens in the completion/output.
        total_tokens:      Sum of input + output tokens.
        duration_seconds:  Wall-clock seconds from first request to last chunk.
        timestamp:         Unix epoch timestamp of the event.
        iso_date:          ISO-8601 date string (YYYY-MM-DD) for partitioning.
        session_id:        Optional session/conversation identifier.
        tags:              Comma-separated tags associated with the request.
    """
    username: str
    project_name: str
    project_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)
    iso_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    session_id: Optional[str] = None
    tags: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TokenUsageEvent":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})