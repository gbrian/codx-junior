"""Tests for the LLM-facing project inspection tools.

Covers the behaviours that are easy to regress and expensive for a model to
diagnose: path sandboxing, bounded file reads, content search (grep), local
change inspection and the atomic write of ``apply_file_changes``.
"""

import os
import subprocess

import pytest

from codx.junior.tools import project_tools
from codx.junior.tools.apply_file_changes import apply_file_changes
from codx.junior.tools.project_tools import (
    is_path_within_project,
    path_to_absolute_project_path,
    project_changes,
    project_glob,
    project_grep,
    project_read_file,
    project_search,
    project_write_file,
)


class FakeSettings:
    """The subset of CODXJuniorSettings used by the project tools."""

    def __init__(self, path):
        self.abs_project_path = str(path)
        self.codx_path = os.path.join(str(path), ".codx")
        self.project_name = "project-tools-test"
        self.project_id = "project-tools-test"

    def get_ignore_patterns(self):
        return [".git", "node_modules"]

    def get_llm_settings(self, llm_model=None):  # pragma: no cover - not used
        raise RuntimeError("LLM settings are not used by these tools")


def run_git(repo, *args, env=None):
    """Run git with a deterministic identity."""
    full_env = os.environ.copy()
    full_env.update({
        "GIT_AUTHOR_NAME": "Project Tools Test",
        "GIT_AUTHOR_EMAIL": "tools@example.com",
        "GIT_COMMITTER_NAME": "Project Tools Test",
        "GIT_COMMITTER_EMAIL": "tools@example.com",
    })
    if env:
        full_env.update(env)
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
        env=full_env,
    ).stdout


@pytest.fixture
def project(tmp_path):
    """A small project tree with text, binary and nested files."""
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "sample.txt").write_text(
        "\n".join(f"line {index}" for index in range(1, 11)) + "\n",
        encoding="utf-8",
    )
    (root / "src" / "auth_service.py").write_text(
        "def alpha():\n"
        "    needle = 1\n"
        "    return needle\n",
        encoding="utf-8",
    )
    (root / "src" / "user_session.py").write_text(
        "SESSION_KEY = 'session'\n",
        encoding="utf-8",
    )
    (root / "docs" / "notes.md").write_text(
        "# Notes\n\nneedle in documentation\n",
        encoding="utf-8",
    )
    (root / "binary.bin").write_bytes(b"\x00\x01\x02binary")
    (root / "outside-sibling.txt").write_text("not here", encoding="utf-8")
    return FakeSettings(root)


# ---------------------------------------------------------------------------
# Path sandboxing
# ---------------------------------------------------------------------------


def test_path_within_project_rejects_sibling_prefix(project, tmp_path):
    """`/project-other` must not pass as a child of `/project`."""
    sibling = tmp_path / "project-other"
    sibling.mkdir()
    secret = sibling / "secret.txt"
    secret.write_text("secret", encoding="utf-8")

    assert is_path_within_project(project, str(secret)) is False

    resolved = path_to_absolute_project_path(project, str(secret))
    assert is_path_within_project(project, resolved) is True
    assert resolved != str(secret)


def test_read_outside_sibling_does_not_leak_file(project, tmp_path):
    sibling = tmp_path / "project-other"
    sibling.mkdir()
    (sibling / "secret.txt").write_text("TOP-SECRET", encoding="utf-8")

    response = project_read_file(
        str(sibling / "secret.txt"), settings=project
    )

    assert "TOP-SECRET" not in response.llm_response
    assert "File not found" in response.llm_response


def test_project_write_file_rejects_traversal(project):
    response = project_write_file(
        "../escaped.txt", "nope", settings=project
    )

    escaped = os.path.join(
        os.path.dirname(project.abs_project_path), "escaped.txt"
    )
    assert "must belong" in response.llm_response
    assert not os.path.exists(escaped)


# ---------------------------------------------------------------------------
# Bounded file reads
# ---------------------------------------------------------------------------


def test_read_file_range_and_line_numbers(project):
    response = project_read_file(
        "sample.txt",
        start_line=3,
        end_line=5,
        line_numbers=True,
        settings=project,
    )

    assert "lines 3-5 of 10" in response.llm_response
    assert "     3| line 3" in response.llm_response
    assert "     5| line 5" in response.llm_response
    assert "line 6" not in response.llm_response


def test_read_file_truncates_large_output(project):
    with open(os.path.join(project.abs_project_path, "big.txt"), "w",
              encoding="utf-8") as file:
        file.write("\n".join(f"row {index} " + "x" * 80 for index in range(200)))

    response = project_read_file("big.txt", max_chars=500, settings=project)

    assert "Truncated" in response.llm_response
    assert "start_line=" in response.llm_response
    assert "of 200" in response.llm_response
    assert len(response.llm_response) < 5000


def test_read_file_rejects_binary(project):
    response = project_read_file("binary.bin", settings=project)

    assert "binary" in response.llm_response.lower()
    assert "\x00" not in response.llm_response


def test_read_file_pattern_returns_only_matches_with_context(project):
    """A symbol search must not dump the whole file (the trace paged 4x)."""
    with open(
        os.path.join(project.abs_project_path, "src", "panel.py"),
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "\n".join([
                "def unrelated():",
                "    pass",
                "def setActiveTab(tab):",
                "    # activate",
                "    return tab",
                "def other():",
                "    pass",
                "def use_active():",
                "    setActiveTab('x')",
            ])
        )

    response = project_read_file(
        "src/panel.py", pattern="setActiveTab", context_lines=1, settings=project
    )

    assert "pattern `setActiveTab`" in response.llm_response
    assert "2 match(es)" in response.llm_response
    assert "     3| def setActiveTab(tab):" in response.llm_response
    assert "     9|     setActiveTab('x')" in response.llm_response
    # Line 1 is outside every context window: the whole file was NOT returned.
    assert "def unrelated" not in response.llm_response


def test_read_file_pattern_scope_and_no_match(project):
    no_match = project_read_file(
        "sample.txt", pattern="needle", settings=project
    )
    assert "0 match(es)" in no_match.llm_response
    assert "No line matches" in no_match.llm_response

    scoped = project_read_file(
        "sample.txt", pattern="line", start_line=8, end_line=10, settings=project
    )
    assert "lines 8-10 of 10" in scoped.llm_response
    assert "line 7" not in scoped.llm_response


def test_read_file_pattern_invalid_regex_falls_back_to_literal(project):
    with open(
        os.path.join(project.abs_project_path, "src", "call.py"),
        "w",
        encoding="utf-8",
    ) as file:
        file.write("result = fn(\n    value=1,\n)\n")

    response = project_read_file(
        "src/call.py", pattern="fn(", settings=project
    )

    assert "searched literally" in response.llm_response
    assert "1 match(es)" in response.llm_response
    assert "result = fn(" in response.llm_response


def test_read_file_outline_maps_declarations(project):
    with open(
        os.path.join(project.abs_project_path, "src", "panel.py"),
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "class Panel:\n"
            "    def setup(self):\n"
            "        pass\n"
            "    def render(self):\n"
            "        pass\n"
        )

    response = project_read_file("src/panel.py", outline=True, settings=project)

    assert "### Outline" in response.llm_response
    assert "requested" in response.llm_response
    assert response.llm_response.index("### Outline") < response.llm_response.index(
        "# src/panel.py"
    )
    assert "class Panel:" in response.llm_response
    assert "def setup" in response.llm_response


def test_read_file_auto_outline_for_large_file(project):
    body = []
    for index in range(140):
        body.append(f"def function_{index}():")
        body.append("    pass")
        body.append("")
    with open(
        os.path.join(project.abs_project_path, "src", "large.py"),
        "w",
        encoding="utf-8",
    ) as file:
        file.write("\n".join(body))

    response = project_read_file("src/large.py", settings=project)

    assert "### Outline" in response.llm_response
    assert "added automatically" in response.llm_response


def test_read_file_requested_range_does_not_nudge_more_reads(project):
    """The old hint told the model to continue reading after every range."""
    response = project_read_file(
        "sample.txt", start_line=3, end_line=5, settings=project
    )

    assert "more line(s) are available. Call project_read_file with" not in (
        response.llm_response
    )
    assert "Showing the requested range" in response.llm_response


# ---------------------------------------------------------------------------
# Content search (grep)
# ---------------------------------------------------------------------------


def test_grep_finds_literal_match_with_context(project):
    response = project_grep(
        "needle = 1", include="*.py", context_lines=1, settings=project
    )

    assert "src/auth_service.py" in response.llm_response
    assert "src/auth_service.py:2:    needle = 1" in response.llm_response
    assert "src/auth_service.py-1-def alpha():" in response.llm_response
    assert "notes.md" not in response.llm_response
    assert "1 match(es)" in response.user_response


def test_grep_regex_and_case_sensitivity(project):
    regex_response = project_grep(
        r"needle\s*=\s*\d",
        include="*.py",
        regex=True,
        settings=project,
    )
    assert "src/auth_service.py:2:" in regex_response.llm_response

    insensitive = project_grep("NEEDLE", include="*.md", settings=project)
    assert "docs/notes.md:3:" in insensitive.llm_response

    sensitive = project_grep(
        "NEEDLE", include="*.md", case_sensitive=True, settings=project
    )
    assert "0 match" in sensitive.user_response


def test_grep_respects_result_limit_and_single_file_path(project):
    single = project_grep(
        "needle", path="src/auth_service.py", settings=project
    )
    assert single.llm_response.count("auth_service.py:2:") == 1

    limited = project_grep("needle", max_results=1, settings=project)
    assert "1 match(es)" in limited.user_response


# ---------------------------------------------------------------------------
# File discovery (glob)
# ---------------------------------------------------------------------------


def test_project_glob_finds_files_and_respects_limit(project):
    response = project_glob("**/*.py", settings=project)

    assert "src/auth_service.py" in response.llm_response
    assert "src/user_session.py" in response.llm_response
    assert "notes.md" not in response.llm_response
    assert "2 file(s)" in response.user_response

    limited = project_glob("**/*", limit=1, settings=project)
    assert "1 file(s)" in limited.user_response


def test_project_glob_honors_gitignore(git_project):
    with open(os.path.join(git_project.abs_project_path, ".gitignore"),
              "w", encoding="utf-8") as file:
        file.write("ignored_dir/\n")
    ignored_dir = os.path.join(git_project.abs_project_path, "ignored_dir")
    os.makedirs(ignored_dir)
    with open(os.path.join(ignored_dir, "secret.py"), "w",
              encoding="utf-8") as file:
        file.write("secret\n")

    response = project_glob("**/*.py", settings=git_project)

    assert "ignored_dir/secret.py" not in response.llm_response


def test_project_glob_no_match_message(project):
    response = project_glob("**/*.nope", settings=project)
    assert "No files matched" in response.user_response


def test_read_file_start_line_beyond_end(project):
    response = project_read_file("sample.txt", start_line=99, settings=project)
    assert "beyond the end" in response.llm_response


def test_grep_invalid_regex(project):
    response = project_grep("[", regex=True, settings=project)
    assert "Invalid regular expression" in response.user_response


def test_project_glob_rejects_parent_escape(project):
    response = project_glob("../**/*.py", settings=project)
    assert "No files matched" in response.user_response


# ---------------------------------------------------------------------------
# Knowledge + path search
# ---------------------------------------------------------------------------


def test_project_search_matches_each_query_independently(project, monkeypatch):
    class _EmptyDB:
        def search(self, query, _limit=10):
            return []

    class _FakeKnowledge:
        def __init__(self, settings):
            self.settings = settings

        def get_db(self):
            return _EmptyDB()

    monkeypatch.setattr(project_tools, "Knowledge", _FakeKnowledge)

    response = project_search(["auth", "session"], settings=project)

    assert "auth_service.py" in response.llm_response
    assert "user_session.py" in response.llm_response
    assert "2 files matched" in response.user_response


def test_project_search_survives_knowledge_failure(project, monkeypatch):
    class _BrokenKnowledge:
        def __init__(self, settings):
            raise RuntimeError("milvus offline")

    monkeypatch.setattr(project_tools, "Knowledge", _BrokenKnowledge)

    response = project_search("auth", settings=project)

    assert "auth_service.py" in response.llm_response
    assert "milvus offline" in response.llm_response
    assert "1 warning" in response.user_response


def test_project_search_no_match_points_to_grep(project, monkeypatch):
    """A path/concept miss must not make the model retry the same search."""
    class _EmptyDB:
        def search(self, query, _limit=10):
            return []

    class _FakeKnowledge:
        def __init__(self, settings):
            self.settings = settings

        def get_db(self):
            return _EmptyDB()

    monkeypatch.setattr(project_tools, "Knowledge", _FakeKnowledge)

    response = project_search("setActiveTab", settings=project)

    assert "No results found" in response.llm_response
    assert "project_grep" in response.llm_response


# ---------------------------------------------------------------------------
# Local changes
# ---------------------------------------------------------------------------


@pytest.fixture
def git_project(project):
    run_git(project.abs_project_path, "init", "-q")
    run_git(project.abs_project_path, "config", "user.email", "tools@example.com")
    run_git(project.abs_project_path, "config", "user.name", "Project Tools Test")
    run_git(project.abs_project_path, "add", "-A")
    run_git(project.abs_project_path, "commit", "-qm", "base")
    return project


def test_project_changes_reports_worktree_staged_and_untracked(git_project):
    with open(os.path.join(git_project.abs_project_path, "sample.txt"),
              "a", encoding="utf-8") as file:
        file.write("changed\n")

    with open(os.path.join(git_project.abs_project_path, "staged.txt"),
              "w", encoding="utf-8") as file:
        file.write("staged line\n")
    run_git(git_project.abs_project_path, "add", "staged.txt")

    with open(os.path.join(git_project.abs_project_path, "new.txt"),
              "w", encoding="utf-8") as file:
        file.write("untracked line\n")

    response = project_changes(settings=git_project)

    assert "sample.txt" in response.user_response
    assert "staged.txt" in response.user_response
    assert "new.txt" in response.user_response
    assert "**modified**" in response.user_response
    assert "**added**" in response.user_response
    assert "**untracked**" in response.user_response

    assert "+changed" in response.llm_response
    assert "+staged line" in response.llm_response
    assert "+untracked line" in response.llm_response


def test_project_changes_scopes_and_path_filter(git_project):
    with open(os.path.join(git_project.abs_project_path, "sample.txt"),
              "a", encoding="utf-8") as file:
        file.write("worktree\n")
    with open(os.path.join(git_project.abs_project_path, "staged.txt"),
              "w", encoding="utf-8") as file:
        file.write("staged\n")
    run_git(git_project.abs_project_path, "add", "staged.txt")
    with open(os.path.join(git_project.abs_project_path, "new.txt"),
              "w", encoding="utf-8") as file:
        file.write("new\n")

    staged = project_changes(scope="staged", settings=git_project)
    assert "staged.txt" in staged.user_response
    assert "sample.txt" not in staged.user_response
    assert "new.txt" not in staged.user_response

    unstaged = project_changes(scope="unstaged", settings=git_project)
    assert "sample.txt" in unstaged.user_response
    assert "new.txt" in unstaged.user_response
    assert "staged.txt" not in unstaged.user_response

    untracked = project_changes(scope="untracked", settings=git_project)
    assert "new.txt" in untracked.user_response
    assert "sample.txt" not in untracked.user_response

    filtered = project_changes(paths="sample.txt", settings=git_project)
    assert "sample.txt" in filtered.user_response
    assert "staged.txt" not in filtered.user_response


def test_project_changes_outside_git(tmp_path):
    settings = FakeSettings(tmp_path)
    response = project_changes(settings=settings)
    assert "not a git repository" in response.user_response.lower()


def test_project_changes_invalid_scope(git_project):
    response = project_changes(scope="nope", settings=git_project)
    assert "Invalid scope" in response.user_response


# ---------------------------------------------------------------------------
# Edit application
# ---------------------------------------------------------------------------


def test_apply_file_changes_writes_to_disk(project):
    path = os.path.join(project.abs_project_path, "sample.txt")
    with open(path, "w", encoding="utf-8") as file:
        file.write("alpha\nbeta\n")

    response = apply_file_changes(
        "sample.txt",
        [{"search": "alpha", "replace": "ALPHA"}],
        settings=project,
    )

    with open(path, "r", encoding="utf-8") as file:
        assert file.read() == "ALPHA\nbeta\n"
    assert "Applied 1 change(s)" in response.llm_response


def test_apply_file_changes_preserves_file_mode(project):
    path = os.path.join(project.abs_project_path, "sample.txt")
    with open(path, "w", encoding="utf-8") as file:
        file.write("alpha\n")
    os.chmod(path, 0o755)

    apply_file_changes(
        "sample.txt",
        [{"search": "alpha", "replace": "ALPHA"}],
        settings=project,
    )

    assert os.stat(path).st_mode & 0o777 == 0o755


def test_apply_file_changes_conflict_leaves_file_untouched(project):
    path = os.path.join(project.abs_project_path, "sample.txt")
    with open(path, "w", encoding="utf-8") as file:
        file.write("alpha\nbeta\n")

    response = apply_file_changes(
        "sample.txt",
        [
            {"search": "alpha", "replace": "ALPHA"},
            {"search": "missing", "replace": "x"},
        ],
        settings=project,
    )

    with open(path, "r", encoding="utf-8") as file:
        assert file.read() == "alpha\nbeta\n"
    assert "Conflict" in response.llm_response
