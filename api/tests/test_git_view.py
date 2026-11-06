"""
Git view engine tests.

Covers the repository-view behaviour that is easy to break and has no UI-free
coverage:

* branches are ordered by latest commit (not alphabetically),
* each worktree exposes the files changed inside its own checkout,
* the local-changes review payload (working tree vs current branch),
* the Validator context defaults the profiles from the changed files.
"""

import asyncio
import os
import re
import subprocess
from types import SimpleNamespace

import pytest

from codx.junior.engine.git_validator import GitValidatorEngine


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class FakeSettings:
    """The subset of CODXJuniorSettings used by the git engines."""

    def __init__(self, path: str):
        self.abs_project_path = path
        self.codx_path = os.path.join(path, ".codx")
        self.project_name = "git-view-test"
        self.project_id = "project-1"
        self.is_git_root = True
        self.git_user_name = "Git View Test"
        self.git_user_email = "git-view@example.com"
        self.git_access_token = ""
        self.git_worktrees_path = ""


class FakeProfile:
    """Minimal profile understood by the validator."""

    def __init__(self, name, file_match="", category="", content=""):
        self.name = name
        self.description = f"{name} profile"
        self.category = category
        self.avatar = ""
        self.file_match = file_match
        self.use_knowledge = False
        self.content = content


class FakeProfileManager:
    """Profile manager with the two methods the validator uses."""

    def __init__(self, profiles):
        self.profiles = profiles

    def list_all_profiles(self):
        return list(self.profiles)

    def get_file_profiles_by_file_path(self, file_path, profiles=None):
        candidates = profiles if profiles is not None else self.list_all_profiles()
        return [
            profile for profile in candidates
            if profile.file_match and re.search(profile.file_match, file_path)
        ]


class FakeAI:
    """Records the prompt and answers a canned review."""

    def __init__(self):
        self.prompts = []

    async def a_chat(self, prompt=None, headers=None):
        self.prompts.append(prompt)
        return [SimpleNamespace(content="# Review\n\nAPPROVED")]


class FakeSession:
    """Session facade used by the engine constructors."""

    def __init__(self, settings, profiles=None):
        self.settings = settings
        self.profile_manager = FakeProfileManager(profiles or [])
        self.ai = FakeAI()

    def get_profile_manager(self, settings=None):
        return self.profile_manager

    def get_ai(self, llm_model=None):
        return self.ai


def run_git(repo, *args, env=None):
    """Run git in *repo* with a deterministic identity."""
    full_env = os.environ.copy()
    full_env.update({
        "GIT_AUTHOR_NAME": "Git View Test",
        "GIT_AUTHOR_EMAIL": "git-view@example.com",
        "GIT_COMMITTER_NAME": "Git View Test",
        "GIT_COMMITTER_EMAIL": "git-view@example.com",
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


def write_file(repo, relative, content):
    path = os.path.join(repo, relative)
    os.makedirs(os.path.dirname(path) or repo, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def commit_file(repo, relative, content, date):
    write_file(repo, relative, content)
    run_git(repo, "add", relative)
    run_git(
        repo,
        "commit",
        "-m",
        f"change {relative}",
        env={
            "GIT_AUTHOR_DATE": date,
            "GIT_COMMITTER_DATE": date,
        },
    )


@pytest.fixture()
def repo(tmp_path):
    """A repository with a `main` branch and one commit."""
    path = str(tmp_path / "repo")
    os.makedirs(path)
    run_git(path, "init", "-b", "main")
    commit_file(path, "app.py", "print('one')\n", "2024-01-01T10:00:00 +0000")
    return path


def make_engine(repo, profiles=None, engine_class=GitValidatorEngine):
    settings = FakeSettings(repo)
    session = FakeSession(settings, profiles=profiles)
    return engine_class(session=session), session


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------


def test_branches_are_sorted_by_latest_commit(repo):
    """The newest branch tip comes first, not the alphabetical name."""
    run_git(repo, "checkout", "-b", "z-old")
    commit_file(repo, "old.txt", "old\n", "2024-01-02T10:00:00 +0000")

    run_git(repo, "checkout", "main")
    commit_file(repo, "main.txt", "new\n", "2024-06-01T10:00:00 +0000")

    engine, _session = make_engine(repo)
    branches = engine.get_repo_branches()

    assert branches[0] == "main"
    assert "z-old" in branches
    # `for-each-ref` returns the commit date, which is the sorting key
    assert branches.index("main") < branches.index("z-old")


# ---------------------------------------------------------------------------
# Worktrees
# ---------------------------------------------------------------------------


def test_worktrees_list_includes_their_file_changes(repo, tmp_path):
    """Every worktree reports the files changed in its own checkout."""
    worktree_path = str(tmp_path / "wt-feature")
    run_git(repo, "worktree", "add", "-b", "feature", worktree_path, "main")

    # Change a tracked file and add an untracked one inside the worktree
    write_file(worktree_path, "app.py", "print('changed in worktree')\n")
    write_file(worktree_path, "new.txt", "new\n")

    engine, _session = make_engine(repo)
    worktrees = engine.list_worktrees()
    feature = next(item for item in worktrees if item["path"] == worktree_path)

    assert feature["branch"] == "feature"
    assert feature["changes"]["dirty"] is True
    assert feature["changes"]["file_count"] == 2
    paths = {
        entry["path"]
        for entry in feature["changes"]["staged"] + feature["changes"]["unstaged"]
    }
    assert paths == {"app.py", "new.txt"}

    # The main worktree has its own (empty) status
    main = next(item for item in worktrees if item.get("is_main"))
    assert main["changes"]["file_count"] == 0


# ---------------------------------------------------------------------------
# Local changes review
# ---------------------------------------------------------------------------


def test_local_changes_include_staged_unstaged_and_untracked(repo):
    """The local review payload has one entry per changed file."""
    write_file(repo, "app.py", "print('two')\n")
    write_file(repo, "new.txt", "brand new\n")

    engine, _session = make_engine(repo)
    changes = engine.get_local_changes()

    assert changes["compare_type"] == "local"
    assert changes["base_branch"] == "HEAD"
    files = changes["branch_file_and_commits"]
    assert set(files) == {"app.py", "new.txt"}
    assert "+print('two')" in files["app.py"]["diff"]
    assert "new file mode" in files["new.txt"]["diff"]
    assert any(
        item["file_name"] == "new.txt" for item in changes["pr_details"]
    )


def test_repo_changes_honours_the_local_sentinel(repo):
    """`to_branch=local` is the review of the working tree against a branch."""
    write_file(repo, "app.py", "print('local change')\n")

    engine, _session = make_engine(repo)
    changes = engine.get_repo_changes(from_branch="main", to_branch="local")

    assert changes["compare_type"] == "local"
    assert changes["base_branch"] == "main"
    assert "app.py" in changes["branch_file_and_commits"]
    assert "local change" in changes["branch_file_and_commits"]["app.py"]["diff"]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def test_validator_defaults_profiles_from_changed_files(repo):
    """A file matched by a profile becomes the default reviewer profile."""
    profile = FakeProfile(
        "py_reviewer", file_match=r"app\.py$", category="agent-validator"
    )
    write_file(repo, "app.py", "print('changed')\n")

    engine, _session = make_engine(repo, profiles=[profile], engine_class=GitValidatorEngine)
    context = engine.get_validation_context(source="local")

    assert context["default_profiles"] == ["py_reviewer"]
    assert context["default_profiles_source"] == "files"
    assert context["file_count"] == 1
    assert context["files"][0]["path"] == "app.py"


def test_validator_runs_the_ai_with_the_selected_profile(repo):
    """The AI receives the profile content and the patch and reports a review."""
    profile = FakeProfile(
        "py_reviewer",
        file_match=r"app\.py$",
        category="agent-validator",
        content="Check Python correctness carefully.",
    )
    write_file(repo, "app.py", "print('changed')\n")

    engine, session = make_engine(
        repo, profiles=[profile], engine_class=GitValidatorEngine
    )
    result = asyncio.run(
        engine.validate_changes(profiles=["py_reviewer"], source="local")
    )

    assert result["success"] is True
    assert result["review"].startswith("# Review")
    assert result["profiles"] == ["py_reviewer"]
    prompt = session.ai.prompts[0]
    assert "Check Python correctness carefully." in prompt
    assert "print('changed')" in prompt


# Made with ❤️ by codx-junior
