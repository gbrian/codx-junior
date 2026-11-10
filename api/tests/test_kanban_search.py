"""
Tests for the project-wide Kanban task search.

The tests use lightweight chats (``SimpleNamespace``) and the real cache module,
so they exercise the scoring, filtering, pagination and facet building without a
database.

Run with::

    cd api && pytest tests/test_kanban_search.py -q
"""

from types import SimpleNamespace

import pytest

from codx.junior.kanban import search


def chat(
    chat_id,
    name="",
    description="",
    board="Work",
    column="Todo",
    status="todo",
    priority="",
    profiles=None,
    users=None,
    assignees=None,
    sprints=None,
    tags=None,
    messages=None,
    updated_at="2026-01-01T10:00:00",
    mode="task",
    is_template=False,
    **kwargs,
):
    """Build the subset of ``Chat`` the search touches."""
    return SimpleNamespace(
        id=chat_id,
        name=name,
        description=description,
        board=board,
        column=column,
        status=status,
        priority=priority,
        profiles=profiles or [],
        users=users or [],
        assignees=assignees or [],
        sprints=sprints or [],
        tags=tags or [],
        messages=messages or [],
        updated_at=updated_at,
        created_at=updated_at,
        mode=mode,
        is_template=is_template,
        owner_project_id="p1",
        project_id="p1",
        due_date="",
        progress=0,
        run_id=None,
        run_status=None,
        cost=0.0,
        **kwargs,
    )


class FakeChatManager:
    """In-memory ChatManager with the list method used by the index."""

    def __init__(self, tasks_path, chats):
        self.chat_path = str(tasks_path)
        self._chats = chats

    def list_chats(self):
        return list(self._chats)


@pytest.fixture(autouse=True)
def _clear_cache():
    search.clear_cache()
    yield
    search.clear_cache()


def manager(tmp_path, chats):
    return FakeChatManager(tmp_path, chats)


def test_search_matches_name_description_and_requires_all_terms(tmp_path):
    mgr = manager(tmp_path, [
        chat("a", name="Login timeout", description="30s timeout on login"),
        chat("b", name="Login button", description="CSS only"),
        chat("c", name="Checkout", description="login timeout regression"),
    ])

    result = search.search_tasks(mgr, "login timeout")

    assert result["total"] == 2
    assert [item["id"] for item in result["results"]] == ["a", "c"]
    # The name match scores above the description match on the same query.
    assert result["results"][0]["id"] == "a"
    assert "timeout" in result["results"][0]["snippet"].lower()


def test_search_filters_board_status_priority_profile_and_assignee(tmp_path):
    mgr = manager(tmp_path, [
        chat("a", name="One", profiles=["backend"], users=["ana"], priority="high"),
        chat("b", name="Two", board="Bugs", status="doing", profiles=["ui"],
             assignees=["bob"], priority="low"),
        chat("c", name="Three", sprints=["Sprint 1"], status="done"),
    ])

    assert search.search_tasks(mgr, board="bugs")["total"] == 1
    assert search.search_tasks(mgr, board="sprint 1")["total"] == 1
    assert search.search_tasks(mgr, status="doing")["total"] == 1
    assert search.search_tasks(mgr, priority="high")["total"] == 1
    assert search.search_tasks(mgr, profile="backend")["total"] == 1
    assert search.search_tasks(mgr, assignee="bob")["total"] == 1
    assert search.search_tasks(mgr, column="Todo")["total"] == 3


def test_search_excludes_done_only_when_requested(tmp_path):
    mgr = manager(tmp_path, [
        chat("a", name="Open", status="todo"),
        chat("b", name="Closed", status="done"),
    ])

    assert search.search_tasks(mgr, include_done=True)["total"] == 2
    assert search.search_tasks(mgr, include_done=False)["total"] == 1
    assert search.search_tasks(mgr, include_done=False)["results"][0]["id"] == "a"


def test_search_excludes_templates_and_channels(tmp_path):
    mgr = manager(tmp_path, [
        chat("a", name="Real"),
        chat("b", name="Template", is_template=True),
        chat("c", name="Channel", mode="channel"),
    ])

    result = search.search_tasks(mgr, "")
    assert [item["id"] for item in result["results"]] == ["a"]


def test_search_paginates_and_reports_facets(tmp_path):
    mgr = manager(tmp_path, [
        chat("a", name="Alpha", profiles=["backend"], updated_at="2026-01-03T00:00:00"),
        chat("b", name="Beta", profiles=["ui"], board="Bugs",
             updated_at="2026-01-02T00:00:00"),
        chat("c", name="Gamma", profiles=["backend"], status="done",
             updated_at="2026-01-01T00:00:00"),
    ])

    first = search.search_tasks(mgr, "", limit=2, offset=0)
    second = search.search_tasks(mgr, "", limit=2, offset=2)

    assert first["total"] == 3
    assert len(first["results"]) == 2
    assert len(second["results"]) == 1
    assert set(first["facets"]["profiles"]) == {"backend", "ui"}
    assert "Bugs" in first["facets"]["boards"]
    assert "done" in first["facets"]["statuses"]


def test_search_sorts_by_score_then_recency(tmp_path):
    mgr = manager(tmp_path, [
        chat("old", name="Deploy pipeline", updated_at="2025-01-01T00:00:00"),
        chat("new", name="Deploy pipeline notes", updated_at="2026-01-01T00:00:00"),
        chat("hit", name="Deploy", updated_at="2024-01-01T00:00:00"),
    ])

    result = search.search_tasks(mgr, "deploy")
    # A name that starts with the term wins over longer names, regardless of age.
    assert result["results"][0]["id"] == "hit"
    # Within the same score, the newest task comes first.
    assert [item["id"] for item in result["results"][1:]] == ["new", "old"]


def test_search_empty_query_returns_recent_tasks_first(tmp_path):
    mgr = manager(tmp_path, [
        chat("old", name="Old", updated_at="2025-01-01T00:00:00"),
        chat("new", name="New", updated_at="2026-01-01T00:00:00"),
    ])

    result = search.search_tasks(mgr, "")
    assert [item["id"] for item in result["results"]] == ["new", "old"]


def test_index_cache_is_used_and_can_be_cleared(tmp_path, monkeypatch):
    mgr = manager(tmp_path, [chat("a", name="One")])
    calls = {"count": 0}

    original = mgr.list_chats

    def counted():
        calls["count"] += 1
        return original()

    monkeypatch.setattr(mgr, "list_chats", counted)

    search.build_index(mgr)
    search.build_index(mgr)
    assert calls["count"] == 1

    search.clear_cache()
    search.build_index(mgr)
    assert calls["count"] == 2
