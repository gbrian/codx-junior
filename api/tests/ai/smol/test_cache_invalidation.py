"""
Tests for the tool-cache invalidation policy.

A cache hit must never hide a write: pure reads keep the per-run cache, while
mutations and unknown tools clear it (safe-by-default).
"""
import pytest

from codx.junior.ai.smol.smol_agent import _tool_invalidates_cache


@pytest.mark.parametrize(
    "tool, invalidates",
    [
        # Pure reads keep the cache.
        ("project_search", False),
        ("project_read_file", False),
        ("project_grep", False),
        ("project_glob", False),
        ("project_changes", False),
        ("fetch_webpage", False),
        ("duckduckgo_search", False),
        ("docker_ps", False),
        ("docker_logs", False),
        ("docker_stats", False),
        ("docker_inspect", False),
        ("docker_images", False),
        ("repository_status", False),
        ("repository_log", False),
        # Mutations clear it (even when the name contains a read-ish word).
        ("project_write_file", True),
        ("apply_file_changes", True),
        ("restore_changes", True),
        ("create_chapter", True),
        ("save_browser_script", True),
        ("delete_browser_script", True),
        ("code_writer", True),
        # Stateful / unified tools that are not known pure reads clear it.
        ("docker_start", True),
        ("docker_stop", True),
        ("docker_restart", True),
        ("docker_run", True),
        ("docker_container", True),
        ("start_session", True),
        ("browse_action", True),
        ("finish_session", True),
        ("profile_learning", True),
        # Unknown tools default to invalidating (safe).
        ("some_new_stateful_tool", True),
    ],
)
def test_cache_invalidation_policy(tool, invalidates):
    assert _tool_invalidates_cache(tool) is invalidates


def test_thread_name_is_not_mistaken_for_a_read():
    """Whole-word matching: 'thread' must not match 'read'."""
    assert _tool_invalidates_cache("thread_manager") is True
