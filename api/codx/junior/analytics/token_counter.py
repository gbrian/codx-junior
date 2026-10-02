import logging
from typing import List

logger = logging.getLogger(__name__)

_tiktoken_available = False
try:
    import tiktoken
    _tiktoken_available = True
except ImportError:
    logger.warning("tiktoken not installed — using word-split token approximation")


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Estimate the number of tokens in *text* for *model*.

    Uses tiktoken when available; falls back to a rough word-split approximation
    (1 token ≈ 0.75 words) when tiktoken is not installed.

    Args:
        text:  The text to measure.
        model: Model name used to select the correct encoding in tiktoken.

    Returns:
        Integer token count estimate.
    """
    if not text:
        return 0

    if _tiktoken_available:
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Unknown model — fall back to cl100k_base (GPT-4 family default)
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

    # Fallback: 1 token ≈ 4 characters (common rule of thumb)
    return max(1, len(text) // 4)


def count_messages_tokens(messages: List[dict], model: str = "gpt-4o") -> int:
    """
    Estimate total token count for a list of OpenAI message dicts.

    Each message contributes its ``content`` tokens plus a small fixed overhead
    (4 tokens per message for role/formatting, as per OpenAI cookbook).

    Args:
        messages: List of ``{"role": ..., "content": ...}`` dicts.
        model:    Model name for encoding selection.

    Returns:
        Total estimated token count.
    """
    tokens = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            # Vision messages carry a list of content parts
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        tokens += count_tokens(str(content), model=model)
        tokens += 4  # per-message overhead: role + formatting
    tokens += 2  # reply priming tokens
    return tokens