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
import shutil
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

    def __init__(self, settings, profiles=None, chat_manager=None):
        self.settings = settings
        self.profile_manager = FakeProfileManager(profiles or [])
        self.chat_manager = chat_manager
        self.ai = FakeAI()

    def get_profile_manager(self, settings=None):
        return self.profile_manager

    def get_ai(self, llm_model=None):
        return self.ai

    def get_chat_manager(self):
        return self.chat_manager


class FakeChatManager:
    """Return one in-memory task from a placeholder chat file."""

    def __init__(self, chat, chat_file):
        self.chat = chat
        self.chat_file = chat_file

    def chat_paths(self):
        return [self.chat_file]

    def load_chat_from_path(self, chat_file, chat_only=False):
        return self.chat


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
# .gitignore editor
# ---------------------------------------------------------------------------


def test_gitignore_editor_reads_and_writes_the_checkout_file(repo):
    """The editor loads an empty document and saves a new `.gitignore`."""
    engine, _session = make_engine(repo)

    initial = engine.get_gitignore()
    assert initial["success"] is True
    assert initial["exists"] is False
    assert initial["content"] == ""

    saved = engine.save_gitignore("dist/\n")
    assert saved["success"] is True
    assert saved["exists"] is True
    assert engine.get_gitignore()["content"] == "dist/\n"


def test_gitignore_add_anchors_and_dedupes_patterns(repo):
    """Files and folders are anchored at the root and never duplicated."""
    write_file(repo, "build/out.txt", "generated\n")
    write_file(repo, "app.py", "print('one')\n")

    engine, _session = make_engine(repo)
    first = engine.add_to_gitignore([
        {"path": "build", "is_dir": True},
        {"path": "app.py", "is_dir": False},
    ])

    assert first["success"] is True
    assert first["added"] == ["/build/", "/app.py"]
    assert "/build/" in first["content"].splitlines()
    assert "/app.py" in first["content"].splitlines()

    second = engine.add_to_gitignore([
        {"path": "build", "is_dir": True},
        {"path": "app.py", "is_dir": False},
    ])
    assert second["success"] is True
    assert second["added"] == []
    assert second["skipped"] == ["/build/", "/app.py"]


def test_gitignore_add_rejects_paths_outside_the_checkout(repo):
    """The ignore file can never reference files outside the repository."""
    engine, _session = make_engine(repo)
    result = engine.add_to_gitignore([{"path": "../outside.txt"}])

    assert result["success"] is False
    assert "Invalid path" in " ".join(result["errors"])


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


def test_validator_maps_the_profiles_associated_with_each_file(repo):
    """Every file carries the profiles matched by its own `file_match`."""
    py_profile = FakeProfile(
        "py_reviewer", file_match=r"app\.py$", category="agent-validator"
    )
    js_profile = FakeProfile(
        "js_reviewer", file_match=r"app\.js$", category="agent-validator"
    )
    write_file(repo, "app.py", "print('changed')\n")
    write_file(repo, "app.js", "console.log('changed')\n")

    engine, _session = make_engine(
        repo,
        profiles=[py_profile, js_profile],
        engine_class=GitValidatorEngine,
    )
    context = engine.get_validation_context(source="local")
    by_path = {entry["path"]: entry for entry in context["files"]}

    assert by_path["app.py"]["profiles"] == ["py_reviewer"]
    assert by_path["app.js"]["profiles"] == ["js_reviewer"]
    assert context["default_profiles"] == ["js_reviewer", "py_reviewer"]


def test_validator_correlates_the_tasks_that_changed_a_file(repo, tmp_path):
    """A task whose mutation tool wrote a file is offered as review context."""
    profile = FakeProfile(
        "py_reviewer", file_match=r"app\.py$", category="agent-validator"
    )
    write_file(repo, "app.py", "print('changed')\n")

    message = SimpleNamespace(
        role="user",
        content="Please update app.py",
        files=[],
        hide=False,
        created_at="2024-02-01T10:00:00",
        updated_at="2024-02-01T10:00:00",
        tool_events=[
            SimpleNamespace(
                tool="project_apply_file_changes",
                status="done",
                request={"file_path": "app.py"},
            )
        ],
    )
    chat = SimpleNamespace(
        id="task-1",
        name="Update app",
        description="Update the app entrypoint",
        status="done",
        board="board",
        column="done",
        branch="",
        mode="task",
        updated_at="2024-02-01T10:01:00",
        file_list=[],
        profiles=["py_reviewer"],
        messages=[message],
    )
    chat_file = tmp_path / "task-1.json"
    chat_file.write_text("{}", encoding="utf-8")

    settings = FakeSettings(repo)
    session = FakeSession(
        settings,
        profiles=[profile],
        chat_manager=FakeChatManager(chat, str(chat_file)),
    )
    engine = GitValidatorEngine(session=session)
    context = engine.get_validation_context(source="local")

    assert context["task_count"] == 1
    task = context["tasks"][0]
    assert task["name"] == "Update app"
    assert task["files"][0]["path"] == "app.py"
    assert "modified" in task["files"][0]["evidence"]

    result = asyncio.run(
        engine.validate_changes(profiles=["py_reviewer"], source="local")
    )
    prompt = session.ai.prompts[0]
    assert "Tasks that changed these files" in prompt
    assert "Update app" in prompt
    # Task text is explicitly untrusted (prompt-injection guard).
    assert "prompt-injection" in prompt.lower()
    assert result["task_count"] == 1


# ---------------------------------------------------------------------------
# Merge modes
# ---------------------------------------------------------------------------


def add_feature_branch(repo, name="feature", filenames=("feature.txt",)):
    """Branch off main and commit one file per name."""
    run_git(repo, "checkout", "-b", name)
    for index, filename in enumerate(filenames, start=1):
        commit_file(
            repo,
            filename,
            f"content {index}\n",
            f"2024-02-0{index}T10:00:00 +0000",
        )
    run_git(repo, "checkout", "main")


def test_merge_without_commit_leaves_the_result_staged(repo):
    """`no_commit` checks out the target and stages the merge, without a commit."""
    add_feature_branch(repo)
    head_before = run_git(repo, "rev-parse", "HEAD").strip()

    engine, _session = make_engine(repo)
    result = engine.merge_branches(
        from_branch="feature", to_branch="main", no_commit=True
    )

    assert result["success"] is True
    assert result["no_commit"] is True
    assert result["committed"] is False
    assert result["commit"] == ""
    assert run_git(repo, "rev-parse", "HEAD").strip() == head_before
    # The merge result waits in the index, ready for the composer
    assert "feature.txt" in run_git(
        repo, "diff", "--cached", "--name-only"
    ).splitlines()
    # A regular no-commit merge keeps the merge state for the eventual commit
    assert run_git(repo, "rev-parse", "--verify", "MERGE_HEAD").strip()


def test_merge_accepts_commit_false_as_the_no_commit_alias(repo):
    """`commit=False` is accepted as a spelling of `no_commit=True`."""
    add_feature_branch(repo)

    engine, _session = make_engine(repo)
    result = engine.merge_branches(
        from_branch="feature", to_branch="main", commit=False
    )

    assert result["success"] is True
    assert result["no_commit"] is True
    assert result["committed"] is False


def test_squash_merge_creates_a_single_commit(repo):
    """A squash merge collapses the source commits into one target commit."""
    add_feature_branch(repo, filenames=("one.txt", "two.txt"))
    main_count_before = run_git(repo, "rev-list", "--count", "main").strip()

    engine, _session = make_engine(repo)
    result = engine.merge_branches(
        from_branch="feature",
        to_branch="main",
        squash=True,
        message="feat: squashed feature",
    )

    assert result["success"] is True
    assert result["squashed"] is True
    assert result["committed"] is True
    assert run_git(repo, "log", "-1", "--format=%s", "main").strip() == (
        "feat: squashed feature"
    )
    # Exactly one new commit on main, with a single parent (no merge commit)
    assert run_git(repo, "rev-list", "--count", "main").strip() == str(
        int(main_count_before) + 1
    )
    parents = run_git(repo, "log", "-1", "--format=%P", "main").split()
    assert len(parents) == 1
    assert run_git(repo, "status", "--porcelain").strip() == ""
    # The source branch keeps its original commits
    assert run_git(repo, "rev-list", "--count", "feature").strip() == "3"


def test_squash_merge_without_commit_stages_the_changes(repo):
    """`squash` + `no_commit` stages the squashed changes and records no merge."""
    add_feature_branch(repo)

    engine, _session = make_engine(repo)
    result = engine.merge_branches(
        from_branch="feature", to_branch="main", squash=True, no_commit=True
    )

    assert result["success"] is True
    assert result["squashed"] is True
    assert result["no_commit"] is True
    assert result["committed"] is False
    assert "feature.txt" in run_git(
        repo, "diff", "--cached", "--name-only"
    ).splitlines()
    # A squash merge never writes MERGE_HEAD
    merge_head = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "MERGE_HEAD"],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    assert merge_head.returncode != 0


def test_merge_removes_the_source_worktree_when_requested(repo, tmp_path):
    """`delete_worktree` removes the checkout and keeps the merged branch."""
    worktree_path = str(tmp_path / "wt-feature")
    run_git(repo, "worktree", "add", "-b", "feature", worktree_path, "main")
    commit_file(
        worktree_path, "feature.txt", "feature\n", "2024-02-01T10:00:00 +0000"
    )

    engine, _session = make_engine(repo)
    result = engine.merge_branches(
        from_branch="feature", to_branch="main", delete_worktree=True
    )

    assert result["success"] is True
    assert result["worktree_removed"] is True
    assert not os.path.exists(worktree_path)
    assert os.path.exists(os.path.join(repo, "feature.txt"))
    branches = run_git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert "feature" in branches


def test_merge_delete_branch_removes_its_worktree_first(repo, tmp_path):
    """Deleting the merged branch also removes the worktree holding it."""
    worktree_path = str(tmp_path / "wt-feature")
    run_git(repo, "worktree", "add", "-b", "feature", worktree_path, "main")
    commit_file(
        worktree_path, "feature.txt", "feature\n", "2024-02-01T10:00:00 +0000"
    )

    engine, _session = make_engine(repo)
    result = engine.merge_branches(
        from_branch="feature", to_branch="main", delete_branch=True
    )

    assert result["success"] is True
    assert result["worktree_removed"] is True
    assert result["branch_deleted"] is True
    assert not os.path.exists(worktree_path)
    branches = run_git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert "feature" not in branches


# ---------------------------------------------------------------------------
# Worktree removal
# ---------------------------------------------------------------------------


def test_remove_worktree_keeps_the_branch(repo, tmp_path):
    """`remove_worktree` deletes the checkout only and keeps the branch."""
    worktree_path = str(tmp_path / "wt-feature")
    run_git(repo, "worktree", "add", "-b", "feature", worktree_path, "main")

    engine, _session = make_engine(repo)
    result = engine.remove_worktree(branch="feature")

    assert result["success"] is True
    assert result["removed"] is True
    assert result["branch"] == "feature"
    assert not os.path.exists(worktree_path)
    branches = run_git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert "feature" in branches


def test_remove_worktree_unlocks_and_removes_a_locked_checkout(repo, tmp_path):
    """A locked worktree is unlocked before retrying the removal."""
    worktree_path = str(tmp_path / "wt-feature")
    run_git(repo, "worktree", "add", "-b", "feature", worktree_path, "main")
    run_git(repo, "worktree", "lock", worktree_path)

    engine, _session = make_engine(repo)
    result = engine.remove_worktree(branch="feature")

    assert result["success"] is True
    assert result["removed"] is True
    assert not os.path.exists(worktree_path)


def test_remove_worktree_rejects_the_main_checkout(repo):
    """The main checkout can never be removed through the worktree action."""
    engine, _session = make_engine(repo)
    result = engine.remove_worktree(path=repo)

    assert result["success"] is False
    assert result["removed"] is False
    assert "main checkout" in " ".join(result["errors"]).lower()


def test_remove_worktree_rejects_unknown_paths(repo):
    """Only registered worktrees can be removed (no arbitrary directories)."""
    engine, _session = make_engine(repo)
    result = engine.remove_worktree(path="/tmp/not-a-registered-worktree")

    assert result["success"] is False
    assert "No worktree registered" in " ".join(result["errors"])


def test_worktrees_mark_the_main_checkout_from_a_subdirectory(repo, monkeypatch):
    """A subproject path resolves the real git root: main is not a worktree."""
    api_dir = os.path.join(repo, "api")
    os.makedirs(api_dir, exist_ok=True)

    # The parent project is unknown (e.g. registered behind another mount
    # alias): the engine must ask git for the top-level instead of treating the
    # subdirectory as the repository root.
    monkeypatch.setattr(
        "codx.junior.engine.git_engine.find_project_parents", lambda project: []
    )
    engine, _session = make_engine(api_dir)
    engine.settings.is_git_root = False

    assert engine._get_repo_root() == repo
    worktrees = engine.list_worktrees(include_changes=False)
    main = next(item for item in worktrees if item["path"] == repo)
    assert main["is_main"] is True
    assert "main checkout" in " ".join(
        engine.remove_worktree(path=repo)["errors"]
    ).lower()


def test_remove_worktree_resolves_a_subproject_checkout(repo, tmp_path, monkeypatch):
    """Deleting a worktree from a subproject still targets the repo root."""
    worktree_path = str(tmp_path / "wt-feature")
    run_git(repo, "worktree", "add", "-b", "feature", worktree_path, "main")

    api_dir = os.path.join(repo, "api")
    os.makedirs(api_dir, exist_ok=True)
    monkeypatch.setattr(
        "codx.junior.engine.git_engine.find_project_parents", lambda project: []
    )
    engine, _session = make_engine(api_dir)
    engine.settings.is_git_root = False

    result = engine.remove_worktree(branch="feature")

    assert result["success"] is True
    assert not os.path.exists(worktree_path)


def test_remove_worktree_falls_back_to_the_branch_for_a_stale_path(repo, tmp_path):
    """A stale path from the UI must not hide an existing worktree."""
    worktree_path = str(tmp_path / "wt-feature")
    run_git(repo, "worktree", "add", "-b", "feature", worktree_path, "main")

    engine, _session = make_engine(repo)
    result = engine.remove_worktree(
        branch="feature", path=str(tmp_path / "moved-away")
    )

    assert result["success"] is True
    assert result["path"] == worktree_path
    assert not os.path.exists(worktree_path)


def test_remove_worktree_prunes_a_missing_checkout(repo, tmp_path):
    """A folder deleted outside git can still be unregistered from the view."""
    worktree_path = str(tmp_path / "wt-feature")
    run_git(repo, "worktree", "add", "-b", "feature", worktree_path, "main")
    shutil.rmtree(worktree_path)

    engine, _session = make_engine(repo)
    result = engine.remove_worktree(path=worktree_path)

    assert result["success"] is True
    assert not any(
        item["path"] == worktree_path
        for item in engine.list_worktrees(include_changes=False)
    )


def test_remove_worktree_rejects_the_checkout_in_use(repo, tmp_path, monkeypatch):
    """The project checked out by the view cannot be deleted from under it."""
    worktree_path = str(tmp_path / "wt-feature")
    run_git(repo, "worktree", "add", "-b", "feature", worktree_path, "main")

    main_settings = FakeSettings(repo)
    main_settings.is_git_root = True
    settings = FakeSettings(worktree_path)
    settings.is_git_root = False
    monkeypatch.setattr(
        "codx.junior.engine.git_engine.find_project_parents",
        lambda project: [main_settings],
    )

    engine = GitValidatorEngine(session=FakeSession(settings))
    result = engine.remove_worktree(path=worktree_path)

    assert result["success"] is False
    assert "checkout in use" in " ".join(result["errors"]).lower()


# Made with ❤️ by codx-junior
