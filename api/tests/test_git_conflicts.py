"""
Conflict detection and resolution tests.

Covers the merge and rebase flows that stop on conflicts and the three ways out
of them: manual resolution (content or ours/theirs), AI resolution and aborting
the pending operation. The tests run against real git repositories created in a
temporary folder, so the porcelain parsing, the index stages and the continue
commands are exercised end to end.
"""

import asyncio
import os
import subprocess
from types import SimpleNamespace

import pytest

from codx.junior.engine.git_conflicts import GitConflictEngine


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class FakeSettings:
    """The subset of CODXJuniorSettings used by the git engines."""

    def __init__(self, path: str):
        self.abs_project_path = path
        self.codx_path = os.path.join(path, ".codx")
        self.project_name = "git-conflicts-test"
        self.project_id = "project-conflicts"
        self.is_git_root = True
        self.git_user_name = "Git Conflict Test"
        self.git_user_email = "git-conflict@example.com"
        self.git_access_token = ""
        self.git_worktrees_path = ""


class FakeAI:
    """AI double returning a canned resolved file."""

    def __init__(self, answer):
        self.answer = answer
        self.prompts = []

    async def a_chat(self, prompt=None, headers=None):
        self.prompts.append(prompt)
        return [SimpleNamespace(content=self.answer)]


class FakeSession:
    """Session facade used by the engine constructors."""

    def __init__(self, settings, ai=None):
        self.settings = settings
        self.ai = ai or FakeAI("")

    def get_ai(self, llm_model=None):
        return self.ai


def run_git(repo, *args, env=None, check=True):
    """Run git in *repo* with a deterministic identity."""
    full_env = os.environ.copy()
    full_env.update({
        "GIT_AUTHOR_NAME": "Git Conflict Test",
        "GIT_AUTHOR_EMAIL": "git-conflict@example.com",
        "GIT_COMMITTER_NAME": "Git Conflict Test",
        "GIT_COMMITTER_EMAIL": "git-conflict@example.com",
    })
    if env:
        full_env.update(env)
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=check,
        env=full_env,
    )


def write_file(repo, relative, content):
    path = os.path.join(repo, relative)
    os.makedirs(os.path.dirname(path) or repo, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def read_file(repo, relative):
    with open(os.path.join(repo, relative), "r", encoding="utf-8") as handle:
        return handle.read()


def commit_file(repo, relative, content, message):
    write_file(repo, relative, content)
    run_git(repo, "add", relative)
    run_git(repo, "commit", "-m", message)


def make_engine(repo, ai=None, engine_class=GitConflictEngine):
    settings = FakeSettings(repo)
    session = FakeSession(settings, ai=ai)
    return engine_class(session=session)


def init_repo(path):
    """Create a minimal git repository without shelling out to ``git init``.

    Some sandboxed environments forbid the ``chmod`` call git performs while
    writing its config, so the metadata is written directly. The resulting
    repository is a regular non-bare checkout and every later git command works
    normally.
    """
    os.makedirs(os.path.join(path, ".git", "objects"), exist_ok=True)
    os.makedirs(os.path.join(path, ".git", "refs", "heads"), exist_ok=True)
    write_file(path, ".git/HEAD", "ref: refs/heads/main\n")
    write_file(
        path,
        ".git/config",
        "[core]\n"
        "\trepositoryformatversion = 0\n"
        "\tfilemode = false\n"
        "\tbare = false\n"
        "\tlogallrefupdates = true\n",
    )


@pytest.fixture()
def repo(tmp_path):
    """Repository with a base commit on `main`."""
    path = str(tmp_path / "repo")
    os.makedirs(path)
    init_repo(path)
    commit_file(path, "app.py", "line 1\nbase\nline 3\n", "base commit")
    return path


def create_merge_conflict(repo):
    """Create divergent `main`/`feature` changes on the same line."""
    run_git(repo, "checkout", "-b", "feature")
    commit_file(repo, "app.py", "line 1\nfeature\nline 3\n", "feature change")
    run_git(repo, "checkout", "main")
    commit_file(repo, "app.py", "line 1\nmain\nline 3\n", "main change")


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def test_merge_detects_conflicts_and_keeps_the_operation(repo):
    """A kept merge reports the unmerged file plus its markers and content."""
    create_merge_conflict(repo)
    engine = make_engine(repo)

    result = engine.merge_branches("feature", "main", keep_conflicts=True)

    assert result["success"] is False
    assert result["conflicted"] is True
    assert result["conflicts"] == ["app.py"]
    assert result["conflict_state"]["operation"] == "merge"

    state = engine.get_conflicts()
    assert state["in_progress"] is True
    assert state["operation"] == "merge"
    assert state["unresolved_count"] == 1
    conflict = state["conflicts"][0]
    assert conflict["path"] == "app.py"
    assert conflict["code"] == "UU"
    assert conflict["has_markers"] is True
    assert conflict["marker_count"] == 1
    assert "<<<<<<<" in conflict["content"]
    assert ">>>>>>>" in conflict["content"]
    assert conflict["stages"] == {"base": True, "ours": True, "theirs": True}

    info = engine.get_repo_info()
    assert info["in_conflict"] is True
    assert info["conflicts"] == ["app.py"]


def test_clean_no_commit_merge_is_pending_without_conflicts(repo):
    """A clean `--no-commit` merge is in progress but has no unmerged files."""
    run_git(repo, "checkout", "-b", "feature")
    commit_file(repo, "feature.txt", "feature\n", "feature change")
    run_git(repo, "checkout", "main")
    engine = make_engine(repo)

    result = engine.merge_branches("feature", "main", no_commit=True)
    assert result["success"] is True
    assert result["no_commit"] is True

    state = engine.get_conflicts()
    assert state["in_progress"] is True
    assert state["has_conflicts"] is False
    assert state["operation"] == "merge"
    assert state["conflicts"] == []
    assert state["unresolved_count"] == 0
    assert state["can_continue"] is True

    info = engine.get_repo_info()
    assert info["operation_in_progress"] is True
    assert info["has_conflicts"] is False
    assert info["in_conflict"] is True

    # The operation can be finished without any conflict resolution.
    continued = engine.continue_operation()
    assert continued["success"] is True
    assert engine.get_conflicts()["in_progress"] is False


def test_merge_conflict_is_still_aborted_by_default(repo):
    """The old abort-on-conflict behaviour is preserved without keep_conflicts."""
    create_merge_conflict(repo)
    engine = make_engine(repo)

    result = engine.merge_branches("feature", "main")

    assert result["success"] is False
    assert result["conflicted"] is False
    assert result["conflicts"] == ["app.py"]
    state = engine.get_conflicts()
    assert state["in_progress"] is False
    assert state["conflicts"] == []


# ---------------------------------------------------------------------------
# Manual resolution
# ---------------------------------------------------------------------------


def test_manual_resolution_then_continue_commits_the_merge(repo):
    """Writing the merged content and continuing creates the merge commit."""
    create_merge_conflict(repo)
    engine = make_engine(repo)
    engine.merge_branches("feature", "main", keep_conflicts=True)

    resolved = engine.resolve_conflict("app.py", "line 1\nmerged\nline 3\n")

    assert resolved["success"] is True
    assert resolved["resolved"] is True
    assert resolved["remaining"] == 0
    assert resolved["state"]["can_continue"] is True
    assert read_file(repo, "app.py") == "line 1\nmerged\nline 3\n"

    continued = engine.continue_operation()

    assert continued["success"] is True
    assert continued["conflicted"] is False
    assert engine.get_conflicts()["in_progress"] is False
    parents = run_git(repo, "log", "-1", "--format=%P").stdout.split()
    assert len(parents) == 2
    assert read_file(repo, "app.py") == "line 1\nmerged\nline 3\n"


def test_resolution_rejects_leftover_markers(repo):
    """Content that still holds conflict markers is never written or staged."""
    create_merge_conflict(repo)
    engine = make_engine(repo)
    engine.merge_branches("feature", "main", keep_conflicts=True)

    result = engine.resolve_conflict(
        "app.py", "<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> feature\n"
    )

    assert result["success"] is False
    assert "conflict markers" in result["errors"][0]
    assert engine.get_conflicts()["unresolved_count"] == 1


def test_take_theirs_resolves_the_conflict(repo):
    """Taking a side checks the stage out and stages the resolution."""
    create_merge_conflict(repo)
    engine = make_engine(repo)
    engine.merge_branches("feature", "main", keep_conflicts=True)

    result = engine.resolve_conflict("app.py", strategy="theirs")

    assert result["success"] is True
    assert result["remaining"] == 0
    assert read_file(repo, "app.py") == "line 1\nfeature\nline 3\n"


def test_mark_resolved_stages_a_file_edited_outside_the_view(repo):
    """`stage` keeps an already edited file and marks it resolved."""
    create_merge_conflict(repo)
    engine = make_engine(repo)
    engine.merge_branches("feature", "main", keep_conflicts=True)

    write_file(repo, "app.py", "line 1\nedited outside\nline 3\n")
    result = engine.resolve_conflict("app.py", strategy="stage")

    assert result["success"] is True
    assert result["remaining"] == 0


def test_conflicted_merge_defers_worktree_removal_until_continue(repo, tmp_path):
    """A delete-worktree merge keeps the checkout until the merge is finished."""
    create_merge_conflict(repo)
    worktree_path = str(tmp_path / "wt-feature")
    run_git(repo, "worktree", "add", worktree_path, "feature")

    engine = make_engine(repo)
    result = engine.merge_branches(
        "feature", "main", keep_conflicts=True, delete_worktree=True
    )

    assert result["conflicted"] is True
    assert os.path.exists(worktree_path)
    state = engine.get_conflicts()
    assert state["pending_cleanup"]["source_branch"] == "feature"
    assert state["pending_cleanup"]["delete_worktree"] is True

    engine.resolve_conflict("app.py", "line 1\nmerged\nline 3\n")
    continued = engine.continue_operation()

    assert continued["success"] is True
    assert continued["worktree_removed"] is True
    assert not os.path.exists(worktree_path)
    assert engine.get_conflicts()["pending_cleanup"] == {}
    branches = run_git(repo, "branch", "--format=%(refname:short)").stdout.split()
    assert "feature" in branches


def test_abort_restores_the_repository(repo):
    """Aborting a kept merge removes MERGE_HEAD and the unmerged entries."""
    create_merge_conflict(repo)
    engine = make_engine(repo)
    engine.merge_branches("feature", "main", keep_conflicts=True)

    result = engine.abort_operation()

    assert result["success"] is True
    state = engine.get_conflicts()
    assert state["in_progress"] is False
    assert state["conflicts"] == []
    assert not os.path.exists(os.path.join(repo, ".git", "MERGE_HEAD"))
    assert run_git(repo, "status", "--porcelain").stdout.strip() == ""


def test_abort_restores_the_local_changes_stashed_before_the_merge(repo):
    """The auto-stash kept while the merge is stuck is popped on abort."""
    commit_file(repo, "notes.txt", "original\n", "add notes")
    create_merge_conflict(repo)
    write_file(repo, "notes.txt", "local edit\n")
    engine = make_engine(repo)

    merge = engine.merge_branches("feature", "main", keep_conflicts=True)
    assert merge["stash_kept"] is True
    assert engine.get_conflicts()["stash_kept"] is True

    result = engine.abort_operation()

    assert result["success"] is True
    assert result["stash_restored"] is True
    assert read_file(repo, "notes.txt") == "local edit\n"
    assert engine.get_conflicts()["stash_kept"] is False


def test_squash_merge_conflict_keeps_the_squash_state(repo):
    """A stalled squash merge can be resolved and committed without MERGE_HEAD."""
    create_merge_conflict(repo)
    engine = make_engine(repo)

    result = engine.merge_branches("feature", "main", squash=True, keep_conflicts=True)

    assert result["conflicted"] is True
    state = engine.get_conflicts()
    assert state["operation"] == "merge"
    assert state["squash"] is True
    assert state["conflicts"]
    assert os.path.exists(os.path.join(repo, ".git", "SQUASH_MSG"))
    assert not os.path.exists(os.path.join(repo, ".git", "MERGE_HEAD"))

    engine.resolve_conflict("app.py", "line 1\nsquashed\nline 3\n")
    resolved_state = engine.get_conflicts()
    assert resolved_state["can_commit"] is True
    assert resolved_state["can_continue"] is False

    continued = engine.continue_operation()
    assert continued["success"] is True
    assert engine.get_conflicts()["in_progress"] is False
    parents = run_git(repo, "log", "-1", "--format=%P").stdout.split()
    assert len(parents) == 1


def test_squash_merge_abort_removes_the_squash_marker(repo):
    """Aborting a stalled squash merge leaves no stale SQUASH_MSG behind."""
    create_merge_conflict(repo)
    engine = make_engine(repo)
    engine.merge_branches("feature", "main", squash=True, keep_conflicts=True)

    result = engine.abort_operation()

    assert result["success"] is True
    assert not os.path.exists(os.path.join(repo, ".git", "SQUASH_MSG"))
    assert engine.get_conflicts()["in_progress"] is False
    assert run_git(repo, "status", "--porcelain").stdout.strip() == ""


# ---------------------------------------------------------------------------
# AI resolution
# ---------------------------------------------------------------------------


def test_ai_resolution_applies_the_merged_file_and_continues(repo):
    """The AI answer is written, staged and can finish the merge."""
    create_merge_conflict(repo)
    ai = FakeAI("line 1\nfeature and main\nline 3\n")
    engine = make_engine(repo, ai=ai)
    engine.merge_branches("feature", "main", keep_conflicts=True)

    result = asyncio.run(
        engine.resolve_conflicts_with_ai(instructions="keep both changes")
    )

    assert result["success"] is True
    assert result["applied"] is True
    assert result["files"][0]["path"] == "app.py"
    assert read_file(repo, "app.py") == "line 1\nfeature and main\nline 3\n"
    assert engine.get_conflicts()["unresolved_count"] == 0

    prompt = ai.prompts[0]
    assert "<base_version>" in prompt
    assert "<ours_version>" in prompt
    assert "<theirs_version>" in prompt
    assert "<<<<<<<" in prompt
    assert "keep both changes" in prompt

    continued = engine.continue_operation()
    assert continued["success"] is True
    assert engine.get_conflicts()["in_progress"] is False


def test_ai_answer_with_markers_is_rejected(repo):
    """A model answer that still has conflict markers is never applied."""
    create_merge_conflict(repo)
    ai = FakeAI("<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> feature\n")
    engine = make_engine(repo, ai=ai)
    engine.merge_branches("feature", "main", keep_conflicts=True)

    result = asyncio.run(engine.resolve_conflicts_with_ai())

    assert result["success"] is False
    assert result["applied"] is False
    assert "conflict markers" in result["errors"][0]
    assert engine.get_conflicts()["unresolved_count"] == 1


def test_ai_resolution_can_only_suggest(repo):
    """`apply=False` returns the content without touching the repository."""
    create_merge_conflict(repo)
    ai = FakeAI("suggested content\n")
    engine = make_engine(repo, ai=ai)
    engine.merge_branches("feature", "main", keep_conflicts=True)

    result = asyncio.run(engine.resolve_conflicts_with_ai(apply=False))

    assert result["files"][0]["content"] == "suggested content\n"
    assert result["files"][0]["applied"] is False
    assert engine.get_conflicts()["unresolved_count"] == 1
    assert "suggested content" not in read_file(repo, "app.py")


# ---------------------------------------------------------------------------
# Rebase
# ---------------------------------------------------------------------------


def test_rebase_conflict_can_be_resolved_and_continued(repo):
    """A conflicting rebase stays in progress and continues after resolving."""
    create_merge_conflict(repo)
    run_git(repo, "checkout", "feature")
    engine = make_engine(repo)

    result = engine.rebase_branch("main", keep_conflicts=True)

    assert result["success"] is False
    assert result["conflicted"] is True
    state = engine.get_conflicts()
    assert state["operation"] == "rebase"
    assert state["rebase_branch"] == "feature"
    assert state["conflicts"][0]["path"] == "app.py"

    resolved = engine.resolve_conflict("app.py", "line 1\nrebased\nline 3\n")
    assert resolved["success"] is True
    assert resolved["state"]["can_continue"] is True

    continued = engine.continue_operation()
    assert continued["success"] is True
    assert engine.get_conflicts()["in_progress"] is False
    assert run_git(repo, "branch", "--show-current").stdout.strip() == "feature"
    assert read_file(repo, "app.py") == "line 1\nrebased\nline 3\n"


# ---------------------------------------------------------------------------
# Marker parsing
# ---------------------------------------------------------------------------


def test_diff3_conflict_markers_are_parsed():
    """The diff3 base section is exposed with its own label."""
    engine = GitConflictEngine.__new__(GitConflictEngine)
    content = (
        "before\n"
        "<<<<<<< HEAD\n"
        "ours line\n"
        "||||||| base\n"
        "base line\n"
        "=======\n"
        "theirs line\n"
        ">>>>>>> feature\n"
        "after\n"
    )

    blocks = engine._parse_conflict_blocks(content)

    assert len(blocks) == 1
    assert blocks[0]["ours_label"] == "HEAD"
    assert blocks[0]["base_label"] == "base"
    assert blocks[0]["theirs_label"] == "feature"
    assert blocks[0]["ours"] == "ours line\n"
    assert blocks[0]["base"] == "base line\n"
    assert blocks[0]["theirs"] == "theirs line\n"
