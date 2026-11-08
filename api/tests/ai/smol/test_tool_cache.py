"""
Tests for SmolAgent's per-conversation tool cache.

The cache key must be the MODEL-visible call identity: runtime parameters
injected by the agent (settings/session/chat_id/tool_cache) must not change it,
otherwise the result is stored under a key the loop lookup can never match.
"""
from types import SimpleNamespace

from codx.junior.ai.smol.tool_cache import ToolCache


def test_same_arguments_hit_the_cache():
    cache = ToolCache()
    cache.set("project_search", {"search": ["a", "b"]}, "result", success=True)

    assert cache.get("project_search", {"search": ["a", "b"]}) == "result"


def test_argument_order_does_not_matter():
    cache = ToolCache()
    cache.set("tool", {"a": 1, "b": 2}, "result", success=True)

    assert cache.get("tool", {"b": 2, "a": 1}) == "result"


def test_injected_runtime_parameters_do_not_change_the_key():
    """A result stored with injected params is found with the model args."""
    cache = ToolCache()
    injected = {
        "file_path": "a.py",
        "settings": SimpleNamespace(project_id="p"),
        "session": object(),
        "chat_id": "chat-1",
        "tool_cache": cache,
    }

    cache.set("project_read_file", injected, "content", success=True)

    assert cache.get("project_read_file", {"file_path": "a.py"}) == "content"
    assert cache.get_cache_key("t", injected) == cache.get_cache_key("t", {"file_path": "a.py"})


def test_unserializable_values_are_hashed_as_text():
    """A non-JSON value must not disable caching for the whole call."""
    cache = ToolCache()
    value = object()
    cache.set("tool", {"value": value}, "result", success=True)

    assert cache.get_cache_key("tool", {"value": value})
    assert cache.get("tool", {"value": value}) == "result"


def test_error_results_are_cached_too():
    cache = ToolCache()
    cache.set("tool", {"a": 1}, "boom", success=False)

    assert cache.get("tool", {"a": 1}) == "boom"


def test_stats_report_hits_and_misses():
    cache = ToolCache()
    cache.set("tool", {"a": 1}, "result", success=True)
    cache.get("tool", {"a": 1})
    cache.get("tool", {"a": 1})
    cache.get("tool", {"a": 2})

    stats = cache.stats()

    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["size"] == 1
    assert stats["hit_rate"] == 66
