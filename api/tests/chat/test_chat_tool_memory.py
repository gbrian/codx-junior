"""
Tests for the cross-turn chat tool memory.

The memory is what stops the agent from re-running the same read/search tools
on every turn: these tests pin the deduplication, stale detection, budgets and
the "already inspected files" classification.
"""
import pytest

from codx.junior.chat.chat_tool_memory import (
    TOOL_MEMORY_MAX_CHARS,
    build_tool_memory_section,
    collect_tool_memory,
    is_file_read_tool,
    is_mutation_tool,
    is_read_tool,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fakes (the module only relies on attributes, so no DB/LangChain is needed)
# ──────────────────────────────────────────────────────────────────────────────


class FakeToolEvent:
    """Minimal stand-in for ``codx.junior.db.ToolEvent``."""

    def __init__(
        self,
        tool,
        request=None,
        status="done",
        response="",
        output="",
        error="",
    ):
        self.tool = tool
        self.request = request or {}
        self.status = status
        self.response = response
        self.output = output
        self.error = error


class FakeMessage:
    """Minimal stand-in for ``codx.junior.db.Message``."""

    def __init__(self, tool_events=None, hide=False, improvement=False, content=""):
        self.tool_events = tool_events or []
        self.hide = hide
        self.improvement = improvement
        self.content = content


def message(*events, **kwargs):
    """Build a fake message carrying *events*."""
    return FakeMessage(tool_events=list(events), **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# Classification
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "tool, read, file_read, mutation",
    [
        ("project_read_file", True, True, False),
        ("project_grep", True, False, False),
        ("project_glob", True, False, False),
        ("project_search", True, False, False),
        ("project_changes", True, False, False),
        ("apply_file_changes", False, False, True),
        ("project_write_file", False, False, True),
        ("create_chapter", False, False, True),
        ("save_browser_script", False, False, True),
        ("list_browser_scripts", True, False, False),
        ("fetch_webpage", False, False, False),
        # Whole-word matching: "thread" must not match "read".
        ("thread_manager", False, False, False),
    ],
)
def test_tool_classification(tool, read, file_read, mutation):
    """Read/discovery, file-content and mutation tools are told apart."""
    assert is_read_tool(tool) is read
    assert is_file_read_tool(tool) is file_read
    assert is_mutation_tool(tool) is mutation


# ──────────────────────────────────────────────────────────────────────────────
# Collection
# ──────────────────────────────────────────────────────────────────────────────


def test_collects_only_finished_tool_events():
    """Running tools and hidden/improvement messages are ignored."""
    messages = [
        message(FakeToolEvent("project_read_file", {"file_path": "a.py"}, response="a")),
        message(FakeToolEvent("project_read_file", {"file_path": "b.py"}, status="running")),
        message(FakeToolEvent("project_read_file", {"file_path": "c.py"}, response="c"), hide=True),
        message(FakeToolEvent("project_read_file", {"file_path": "d.py"}, response="d"), improvement=True),
    ]

    entries = collect_tool_memory(messages)

    assert [entry.request["file_path"] for entry in entries] == ["a.py"]
    assert entries[0].turn == 1


def test_entries_keep_chronological_turns():
    """Turn numbers follow the position of the message in the conversation."""
    messages = [
        message(FakeToolEvent("project_search", {"search": "alpha"}, response="x")),
        message(FakeToolEvent("project_grep", {"pattern": "beta"}, response="y")),
    ]

    entries = collect_tool_memory(messages)

    assert [entry.turn for entry in entries] == [1, 2]


# ──────────────────────────────────────────────────────────────────────────────
# Rendering
# ──────────────────────────────────────────────────────────────────────────────


def test_no_tool_events_produces_empty_section():
    """A conversation without tool events has no memory block."""
    section, stats = build_tool_memory_section([message(), message()])

    assert section == ""
    assert stats == {"calls": 0, "entries": 0, "rendered": 0, "files": 0, "chars": 0}


def test_duplicate_calls_are_collapsed_to_the_latest_result():
    """The same tool + args is reported once, with the latest result and count."""
    messages = [
        message(FakeToolEvent("project_read_file", {"file_path": "a.py"}, response="v1")),
        message(FakeToolEvent("project_read_file", {"file_path": "a.py"}, response="v2")),
        message(FakeToolEvent("project_read_file", {"file_path": "a.py"}, response="v3")),
    ]

    section, stats = build_tool_memory_section(messages)

    assert stats["calls"] == 3
    assert stats["entries"] == 1
    assert "v3" in section
    assert "v1" not in section
    assert "v2" not in section
    assert "called 3x" in section


def test_argument_order_is_irrelevant_for_deduplication():
    """Canonical arguments make dict key order irrelevant."""
    messages = [
        message(FakeToolEvent("project_grep", {"pattern": "x", "path": "src"}, response="one")),
        message(FakeToolEvent("project_grep", {"path": "src", "pattern": "x"}, response="two")),
    ]

    section, stats = build_tool_memory_section(messages)

    assert stats["entries"] == 1
    assert "two" in section
    assert "called 2x" in section


def test_already_inspected_files_index():
    """Read files are indexed; a grep scope is not a file that was read."""
    messages = [
        message(FakeToolEvent("project_read_file", {"file_path": "src/a.py"}, response="a")),
        message(FakeToolEvent("project_grep", {"pattern": "foo", "path": "src"}, response="match")),
    ]

    section, stats = build_tool_memory_section(messages)

    assert "Already inspected files" in section
    assert "- src/a.py (project_read_file, turn 1)" in section
    assert "- src (project_grep" not in section, "a grep scope is not a read file"
    assert stats["files"] == 1


def test_write_after_read_marks_the_read_stale():
    """A later write to the same file flags the previous read as stale."""
    messages = [
        message(FakeToolEvent("project_read_file", {"file_path": "src/a.py"}, response="old")),
        message(FakeToolEvent("project_write_file", {"file_path": "src/a.py", "content": "new"}, response="written")),
        message(FakeToolEvent("project_read_file", {"file_path": "src/a.py"}, response="new content")),
    ]

    section, _ = build_tool_memory_section(messages)

    # The write is not a read, so the file index points at the LAST read which
    # happened after the mutation and is therefore fresh.
    assert "src/a.py (project_read_file, turn 3" in section
    assert "STALE" not in section


def test_read_followed_by_write_is_stale():
    """A read whose file is modified later is explicitly marked stale."""
    messages = [
        message(FakeToolEvent("project_read_file", {"file_path": "src/a.py"}, response="old")),
        message(FakeToolEvent("apply_file_changes", {"file_path": "src/a.py", "changes": [{"search": "a", "replace": "b"}]}, response="ok")),
    ]

    section, _ = build_tool_memory_section(messages)

    assert "src/a.py (project_read_file, turn 1 — STALE" in section
    assert "the file changed afterwards" in section


def test_large_payload_arguments_are_abbreviated():
    """A write carrying a whole file reports its size, not its content."""
    big = "x" * 50_000
    messages = [
        message(FakeToolEvent("project_write_file", {"file_path": "a.py", "content": big}, response="ok")),
    ]

    section, _ = build_tool_memory_section(messages)

    assert "content=<50000 chars>" in section
    assert "x" * 1000 not in section


def test_result_is_truncated_head_and_tail():
    """A huge result keeps both its beginning and its end."""
    text = "HEAD-" + ("middle " * 5000) + "-TAIL"
    messages = [
        message(FakeToolEvent("project_read_file", {"file_path": "big.py"}, response=text)),
    ]

    section, _ = build_tool_memory_section(messages)

    assert "HEAD-" in section
    assert "-TAIL" in section
    assert "result truncated" in section


def test_block_never_exceeds_the_budget():
    """The rendered block is bounded even with many large results."""
    messages = [
        message(
            FakeToolEvent(
                "project_read_file",
                {"file_path": f"src/file_{index}.py"},
                response="content " * 2000,
            )
        )
        for index in range(50)
    ]

    section, stats = build_tool_memory_section(messages, max_chars=900)

    assert len(section) <= 900
    assert stats["entries"] == 50


def test_default_budget_covers_a_long_conversation():
    """The default budget is respected with 100 tool calls."""
    messages = [
        message(
            FakeToolEvent(
                "project_read_file",
                {"file_path": f"src/file_{index}.py"},
                response="content " * 2000,
            )
        )
        for index in range(100)
    ]

    section, stats = build_tool_memory_section(messages)

    assert len(section) <= TOOL_MEMORY_MAX_CHARS
    assert stats["calls"] == 100
    assert stats["entries"] == 100
    assert stats["rendered"] <= 40


def test_zero_budget_disables_the_block():
    """A zero budget is a supported way to disable the memory."""
    messages = [
        message(FakeToolEvent("project_read_file", {"file_path": "a.py"}, response="a")),
    ]

    section, _ = build_tool_memory_section(messages, max_chars=0)

    assert section == ""


def test_error_results_are_reported():
    """Failed tools are part of the memory so the model does not retry blindly."""
    messages = [
        message(FakeToolEvent("project_read_file", {"file_path": "a.py"}, status="error", error="missing file")),
    ]

    section, _ = build_tool_memory_section(messages)

    assert " missing file" in section
    assert "project_read_file(file_path=a.py) — error" in section


def test_output_is_used_when_response_is_empty():
    """Dual-response tools may only carry the user-facing output."""
    messages = [
        message(
            FakeToolEvent(
                "project_search",
                {"search": "authentication"},
                response="",
                output="Found auth in src/auth.py",
            )
        ),
    ]

    section, _ = build_tool_memory_section(messages)

    assert "Found auth in src/auth.py" in section
