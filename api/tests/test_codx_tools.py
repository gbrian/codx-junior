"""Tests for the codebase / .codx control-plane separation.

The project tree has two namespaces and the tools must not mix them:

* ``project_*`` searches the codebase and never sees ``.codx``.
* ``search_codx`` searches the control plane (tasks, profiles, sessions, ...)
  and never sees source files or databases.
"""

import os

import pytest

from codx.junior.chat.chat_engine import ChatEngine
from codx.junior.tools import project_tools
from codx.junior.tools.codx_tools import search_codx
from codx.junior.tools.project_structure import project_structure, read_folder
from codx.junior.tools.project_tools import (
    is_codx_path,
    is_codx_relative_path,
    project_glob,
    project_grep,
    project_search,
)


class FakeSettings:
    """The subset of CODXJuniorSettings used by these tools."""

    def __init__(self, path):
        self.abs_project_path = str(path)
        self.codx_path = os.path.join(str(path), ".codx")
        self.project_name = "codx-tools-test"
        self.project_id = "codx-tools-test"

    def get_ignore_patterns(self):
        return [".git", ".codx", "node_modules"]

    def get_sub_projects(self):
        return []


@pytest.fixture
def project(tmp_path):
    """A project with code, tasks, a profile, a session, db/logs and secrets."""
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.py").write_text(
        "def needle():\n    return 'needle in code'\n", encoding="utf-8"
    )

    codx = root / ".codx"
    task_dir = codx / "tasks" / "maintenance" / "To Do"
    task_dir.mkdir(parents=True)
    (task_dir / "wallet.task.json").write_text(
        """{
  "id": "task-1",
  "name": "Wallet task",
  "description": "Fix the wallet needle",
  "board": "maintenance",
  "column": "To Do",
  "status": "todo",
  "user": {"username": "secret-user"},
  "messages": [
    {"role": "user", "content": "the wallet needle is broken"}
  ]
}
""",
        encoding="utf-8",
    )

    profiles = codx / "profiles"
    profiles.mkdir()
    (profiles / "reviewer.profile").write_text(
        """{
  "name": "reviewer",
  "description": "Reviews pull requests with needle",
  "content": "You review code.",
  "tools": ["project_read_file"],
  "tags": ["review"]
}
""",
        encoding="utf-8",
    )

    session_dir = codx / "browser_sessions" / "sess-1"
    session_dir.mkdir(parents=True)
    (session_dir / "sess-1.session").write_text(
        """{
  "id": "sess-1",
  "name": "Browser session needle",
  "description": "A desktop session",
  "kind": "linux"
}
""",
        encoding="utf-8",
    )
    (session_dir / "activity.jsonl").write_text(
        '{"action": "create", "params": {"name": "needle"}}\n',
        encoding="utf-8",
    )

    (codx / "db").mkdir()
    (codx / "db" / "milvus.db").write_text("needle in a database", encoding="utf-8")
    (codx / "logs").mkdir()
    (codx / "logs" / "app.log").write_text("needle in a log\n", encoding="utf-8")

    workspace = codx / "workspaces" / "ws-1"
    workspace.mkdir(parents=True)
    (workspace / "ws-1.workspace").write_text(
        '{"id": "ws-1", "name": "workspace", "description": "needle workspace"}',
        encoding="utf-8",
    )
    (workspace / ".env").write_text("SECRET=supersecret-needle\n", encoding="utf-8")

    return FakeSettings(root)


def test_codx_path_detection_is_component_based():
    assert is_codx_relative_path(".codx") is True
    assert is_codx_relative_path(".codx/tasks/a.json") is True
    assert is_codx_relative_path("docs/about.codx.md") is False
    assert is_codx_path("/project", "/project/.codx/tasks/a.json") is True


def test_structure_excludes_codx_and_points_to_search(project):
    output = project_structure(settings=project)

    assert "main.py" in output
    assert "**src**/" in output
    assert ".codx/tasks" not in output
    assert "search_codx" in output


def test_read_folder_codx_redirects_instead_of_listing(project):
    output = read_folder(path=".codx", settings=project)

    assert "control plane" in output
    assert "search_codx" in output
    assert "tasks/" not in output.split("search_codx")[0]


def test_codebase_glob_and_grep_never_include_codx(project):
    glob_output = project_glob("**/*.json", settings=project).llm_response
    assert ".codx/tasks" not in glob_output

    grep_output = project_grep("needle", settings=project).llm_response
    assert "src/main.py" in grep_output
    assert ".codx/tasks" not in grep_output


def test_project_search_never_matches_codx_paths(project, monkeypatch):
    class _EmptyDB:
        def search(self, query, _limit=10):
            return []

    class _FakeKnowledge:
        def __init__(self, settings):
            self.settings = settings

        def get_db(self):
            return _EmptyDB()

    monkeypatch.setattr(project_tools, "Knowledge", _FakeKnowledge)

    response = project_search("wallet", settings=project)

    assert "wallet" in response.llm_response.lower()
    assert ".codx/tasks" not in response.llm_response


def test_profile_allowlist_gets_the_read_only_investigation_tools():
    """A saved profile must not hide grep/glob/changes/search_codx."""
    tools = ChatEngine._ensure_investigation_tools(
        None, ["project_read_file", "project_search"]
    )

    for name in (
        "project_grep", "project_glob", "project_changes", "search_codx",
    ):
        assert name in tools

    # Profiles that cannot read project files are not modified.
    assert ChatEngine._ensure_investigation_tools(None, ["fetch_webpage"]) == [
        "fetch_webpage"
    ]


def test_search_codx_inventory_lists_modules_not_databases(project):
    response = search_codx(query="", settings=project)

    assert ".codx control plane" in response.llm_response
    assert "**tasks**" in response.llm_response
    assert "**profiles**" in response.llm_response
    assert "**browser_sessions**" in response.llm_response
    assert "milvus.db" not in response.llm_response
    assert "**logs**" not in response.llm_response


def test_search_codx_finds_control_plane_content_and_json_fields(project):
    response = search_codx(query="needle", settings=project)

    text = response.llm_response
    assert "Fix the wallet needle" in text
    assert "— name" in text
    assert "messages[0].content" in text
    assert "reviewer" in text
    assert "Browser session needle" in text
    assert ".codx/tasks/" in text
    # Source code is not part of the control plane.
    assert "src/main.py" not in text
    # The database and the sensitive .env are never searched.
    assert "milvus.db" not in text
    assert "supersecret-needle" not in text


def test_search_codx_scopes_to_one_module(project):
    tasks = search_codx(query="wallet", modules=["tasks"], settings=project)
    assert "Wallet task" in tasks.llm_response
    assert "reviewer" not in tasks.llm_response

    profiles = search_codx(query="needle", modules=["profiles"], settings=project)
    assert "reviewer" in profiles.llm_response
    assert "Wallet task" not in profiles.llm_response


def test_search_codx_module_aliases(project):
    response = search_codx(
        query="needle", modules=["browser"], settings=project
    )
    assert "Browser session needle" in response.llm_response


def test_search_codx_logs_are_opt_in(project):
    default = search_codx(query="needle", settings=project)
    assert "app.log" not in default.llm_response

    logs = search_codx(query="needle", modules=["logs"], settings=project)
    assert "app.log" in logs.llm_response


def test_search_codx_rejects_databases_with_a_warning(project):
    response = search_codx(query="needle", modules=["db"], settings=project)

    assert "not text-searchable" in response.llm_response
    assert "milvus.db" not in response.llm_response


def test_search_codx_regex_and_invalid_regex(project):
    match = search_codx(
        query="needl[ae]", modules=["tasks"], mode="regex", settings=project
    )
    assert "wallet needle" in match.llm_response

    invalid = search_codx(query="[", mode="regex", settings=project)
    assert "Invalid regular expression" in invalid.user_response


def test_search_codx_no_match_is_explicit(project):
    response = search_codx(
        query="zzzz-not-here", modules=["profiles"], settings=project
    )

    assert "No matches" in response.llm_response
    assert "project_grep" in response.llm_response
