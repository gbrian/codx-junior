"""
Model catalogue shared by codx-junior and harness adapters.

Harnesses are not allowed to invent their own model names. The models a task
may select come from ``GlobalSettings.ai_models``, the same catalogue SmolAgent
uses through :func:`codx.junior.global_settings.get_model_settings`.

An :class:`~codx.junior.model.ai_model.AIModel` can carry a harness-specific
mapping in ``metadata``:

```yaml
metadata:
  dsh:
    provider: deepseek-official
    model: deepseek-flash
  claude-code:
    model: sonnet
  codex:
    model: gpt-5
```

``provider``/``model`` are the harness-side identifiers; ``name`` is always the
codx-junior model name the user selects. When no mapping exists the adapter
falls back to ``ai_provider`` / ``ai_model`` and the harness may reject it; that
error is surfaced to the user instead of silently running another model.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from codx.junior.global_settings import get_model, get_model_settings, read_global_settings

logger = logging.getLogger(__name__)


class HarnessModelError(ValueError):
    """The requested harness model is not in codx-junior's catalogue."""


def _model_type(model: Any) -> str:
    value = getattr(model, "model_type", "")
    return str(getattr(value, "value", value) or "")


def _harness_mapping(model: Any, kind: str) -> Dict[str, Any]:
    metadata = getattr(model, "metadata", None) or {}
    if not isinstance(metadata, dict):
        return {}
    direct = metadata.get(kind)
    if isinstance(direct, dict):
        return dict(direct)
    harness = metadata.get("harness")
    if isinstance(harness, dict) and isinstance(harness.get(kind), dict):
        return dict(harness[kind])
    return {}


def _pricing(model: Any, global_settings: Any = None) -> Dict[str, Any]:
    """Best-effort cxjcoins prices; a missing provider must not hide a model."""
    try:
        settings = get_model_settings(model.name, global_settings=global_settings)
        return {
            "input_k_tokens_cxjcoins": settings.input_k_tokens_cxjcoins,
            "output_k_tokens_cxjcoins": settings.output_k_tokens_cxjcoins,
        }
    except Exception as ex:  # pragma: no cover - provider may not be loaded
        logger.debug("harness model '%s' has no resolved pricing: %s", model.name, ex)
        return {"input_k_tokens_cxjcoins": None, "output_k_tokens_cxjcoins": None}


def model_view(model: Any, kind: str = "dsh") -> Dict[str, Any]:
    """Serialize one catalogue model for the harness UI/API."""
    mapping = _harness_mapping(model, kind)
    settings = getattr(model, "settings", None)
    return {
        "name": model.name,
        "ai_provider": model.ai_provider,
        "ai_model": model.ai_model or model.name,
        "model_type": _model_type(model),
        "tags": list(getattr(model, "tags", None) or []),
        "context_length": getattr(settings, "context_length", 0) or 0,
        "pricing": _pricing(model, read_global_settings()),
        "harness": {
            kind: {
                "provider": mapping.get("provider") or model.ai_provider,
                "model": mapping.get("model") or model.ai_model or model.name,
                "reasoning_effort": mapping.get("reasoning_effort"),
                "mapped": bool(mapping),
            }
        },
    }


def list_llm_models(kind: str = "dsh") -> List[Dict[str, Any]]:
    """Return every LLM model defined in codx-junior, for *kind*."""
    global_settings = read_global_settings()
    models = [
        model
        for model in (getattr(global_settings, "ai_models", None) or [])
        if _model_type(model) == "llm"
    ]
    return [model_view(model, kind=kind) for model in models]


def resolve_model(name: Optional[str]) -> Optional[Any]:
    """
    Find one LLM model by codx-junior name or provider model id.

    ``None``/empty means "use the harness default" and returns ``None``.
    """
    requested = str(name or "").strip()
    if not requested:
        return None
    model = get_model(requested, read_global_settings())
    if model is None or _model_type(model) != "llm":
        raise HarnessModelError(f"model '{requested}' is not an LLM model defined in codx-junior")
    return model


def harness_model_payload(name: Optional[str], kind: str = "dsh") -> Optional[Dict[str, Any]]:
    """
    Build the harness-facing selection for one codx-junior model.

    Returns ``None`` when no model was requested. The payload always carries the
    codx-junior ``name`` for auditability and the harness-side identifiers under
    ``provider``/``model``.
    """
    model = resolve_model(name)
    if model is None:
        return None
    view = model_view(model, kind=kind)
    selection = view["harness"][kind]
    return {
        "name": model.name,
        "provider": selection["provider"],
        "model": selection["model"],
        "reasoning_effort": selection["reasoning_effort"],
        "mapped": selection["mapped"],
    }
