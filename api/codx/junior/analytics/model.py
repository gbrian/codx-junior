from dataclasses import dataclass, field, asdict, fields
from datetime import datetime
from typing import Optional
import time


@dataclass
class TokenUsageEvent:
    """
    Represents a single LLM call with token consumption metadata.

    Fields:
        username:              The user who triggered the request.
        project_name:          The project context for the request.
        project_id:            The project identifier.
        model:                 LLM model name used (e.g. "gpt-4o").
        provider:              LLM provider (e.g. "openai", "litellm").
        input_tokens:          Number of tokens in the prompt/input.
        output_tokens:         Number of tokens in the completion/output.
        total_tokens:          Sum of input + output tokens.
        duration_seconds:      Wall-clock seconds from first request to last chunk.
        timestamp:             Unix epoch timestamp of the event.
        iso_date:              ISO-8601 date string (YYYY-MM-DD) for partitioning.
        session_id:            Optional session/conversation identifier.
        tags:                  Comma-separated tags associated with the request.
        input_k_tokens_cxjcoins:   Price per 1K input tokens in CXJ coins (from AISettings).
        output_k_tokens_cxjcoins:  Price per 1K output tokens in CXJ coins (from AISettings).
        total_cxjcoins:        Total cost in CXJ coins for this event.
        request_id:            Request id for tracebility
        tokens_from_provider:  Token count comes from provider's response, else they are calculated
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
    input_k_tokens_cxjcoins: float = 0.0
    output_k_tokens_cxjcoins: float = 0.0
    total_cxjcoins: float = 0.0
    request_id: str = None
    tokens_from_provider: bool = False

    def __post_init__(self):
        """Compute total_cxjcoins from input/output tokens and their respective prices if not set."""
        if self.total_cxjcoins == 0.0:
            input_cost = (self.input_tokens / 1000.0) * self.input_k_tokens_cxjcoins
            output_cost = (self.output_tokens / 1000.0) * self.output_k_tokens_cxjcoins
            self.total_cxjcoins = input_cost + output_cost

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TokenUsageEvent":
        """
        Build a TokenUsageEvent from a dict, tolerating old/missing/incorrect fields.

        Backwards-compatibility rules:
        - Old records may have 'k_tokens_cxjcoins' instead of the split fields;
          in that case both input and output prices are set to that value.
        - Any field that is missing or of an incompatible type falls back to
          the dataclass default (or default_factory) for that field.
        """
        # Collect field metadata for defaults
        field_defaults: dict = {}
        for f in fields(cls):
            if f.default is not f.default_factory:  # has a plain default
                field_defaults[f.name] = f.default
            elif f.default_factory is not f.default_factory:  # unreachable guard
                pass
            # fields with default_factory will be handled by the dataclass itself

        # Start with a clean copy to avoid mutating the original
        cleaned: dict = {}

        # Backwards-compat: map legacy 'k_tokens_cxjcoins' to both new fields
        legacy_k = data.get("k_tokens_cxjcoins")

        known_fields = {f.name: f for f in fields(cls)}

        for name, f in known_fields.items():
            raw = data.get(name)

            # Fall back to legacy field for the two pricing fields
            if raw is None and name in ("input_k_tokens_cxjcoins", "output_k_tokens_cxjcoins"):
                raw = legacy_k

            # If still missing, skip so the dataclass default / default_factory kicks in
            if raw is None:
                continue

            # Attempt type coercion; on failure fall back to dataclass default
            try:
                # Determine target type from annotation
                target_type = f.type
                # Handle Optional[X] -> use X
                origin = getattr(target_type, "__origin__", None)
                if origin is type(None):
                    cleaned[name] = raw
                    continue

                # Simple coercion for primitive types
                if target_type in (int, float, str, bool):
                    cleaned[name] = target_type(raw)
                elif target_type == Optional[str] or str(target_type) in ("typing.Optional[str]", "Optional[str]"):
                    cleaned[name] = str(raw) if raw is not None else None
                else:
                    cleaned[name] = raw
            except (TypeError, ValueError):
                # Skip field; dataclass will use its default
                pass

        return cls(**cleaned)