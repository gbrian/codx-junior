"""
Tool execution cache manager for SmolAgent.

Caches tool results based on tool name and arguments hash to avoid
re-executing identical tool calls within the same conversation.
Cached results are transparent to the model and don't count towards
tool execution limits.
"""
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Cache entry structure
CacheEntry = Tuple[Any, bool]  # (result, was_successful)


# Parameters injected by SmolAgent at execution time. They are NOT part of the
# model-visible call identity: including them makes the store key differ from
# the lookup key (and a pydantic settings object is not JSON serialisable), so
# they are removed before hashing.
_INJECTED_PARAMETER_KEYS = frozenset({"settings", "session", "chat_id", "tool_cache"})


class ToolCache:
    """
    In-memory cache for tool execution results within a single conversation.

    Cache key is a SHA256 hash of `(tool_name, json.dumps(params))` to ensure
    identical tool calls always hit the cache regardless of parameter order.
    Runtime parameters injected by the agent (``settings``, ``session``,
    ``chat_id``, ``tool_cache``) are excluded from the key so a stored result
    can be matched by the lookup performed with the model arguments.

    Cached results:
    - Bypass tool loop guards (don't count towards max_tool_calls)
    - Emit TOOL_START/END events with `cached=True` for observability
    - Are immediately sent to the model without re-execution
    """

    def __init__(self) -> None:
        """Initialize an empty tool cache."""
        self._cache: Dict[str, CacheEntry] = {}
        self._hit_count: int = 0
        self._miss_count: int = 0

    def get_cache_key(
        self, tool_name: str, params: Dict[str, Any]
    ) -> str:
        """
        Generate a deterministic cache key from tool name and parameters.

        Uses SHA256 hash of (tool_name, sorted JSON params) to ensure
        identical calls always produce the same key, regardless of dict
        order or minor JSON formatting differences.

        Args:
            tool_name: Name of the tool function.
            params:    Arguments dictionary passed to the tool.

        Returns:
            A SHA256 hex digest string.
        """
        try:
            # Sort keys to ensure consistent hashing regardless of dict order.
            # Injected runtime parameters are not model input and must not
            # change the call identity.
            cache_params = {
                key: value
                for key, value in (params or {}).items()
                if key not in _INJECTED_PARAMETER_KEYS
            }
            params_json = json.dumps(
                cache_params,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            )
            cache_key_input = f"{tool_name}:{params_json}"
            return hashlib.sha256(
                cache_key_input.encode("utf-8")
            ).hexdigest()
        except (TypeError, ValueError) as ex:
            # If params can't be serialized, return None to skip caching
            logger.debug(
                "ToolCache: cannot generate cache key for '%s': %s",
                tool_name,
                ex,
            )
            return ""

    def get(self, tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Retrieve a cached tool result if available.

        Args:
            tool_name: Name of the tool function.
            params:    Arguments dictionary.

        Returns:
            Cached result if found, otherwise ``None``.
        """
        cache_key = self.get_cache_key(tool_name, params)
        if not cache_key:
            return None

        if cache_key in self._cache:
            result, was_successful = self._cache[cache_key]
            self._hit_count += 1
            logger.debug(
                "ToolCache: HIT for tool '%s' (key=%s, success=%s)",
                tool_name,
                cache_key[:8],
                was_successful,
            )
            return result

        self._miss_count += 1
        return None

    def set(
        self, tool_name: str, params: Dict[str, Any], result: Any, success: bool
    ) -> None:
        """
        Store a tool result in the cache.

        Both successful and failed results are cached to avoid
        re-executing tools that previously failed with the same arguments.

        Args:
            tool_name: Name of the tool function.
            params:    Arguments dictionary.
            result:    The result returned by the tool (or error message).
            success:   Whether the tool executed successfully.
        """
        cache_key = self.get_cache_key(tool_name, params)
        if not cache_key:
            return

        self._cache[cache_key] = (result, success)
        logger.debug(
            "ToolCache: SET for tool '%s' (key=%s, success=%s)",
            tool_name,
            cache_key[:8],
            success,
        )

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.debug("ToolCache: cache cleared")

    def stats(self) -> Dict[str, int]:
        """
        Return cache statistics for analytics.

        Returns:
            Dict with ``hits``, ``misses``, ``size`` and ``hit_rate`` (0-100).
        """
        total = self._hit_count + self._miss_count
        hit_rate = (
            int((self._hit_count / total) * 100) if total > 0 else 0
        )
        return {
            "hits": self._hit_count,
            "misses": self._miss_count,
            "size": len(self._cache),
            "hit_rate": hit_rate,
        }

# Made with ❤️ by codx-junior