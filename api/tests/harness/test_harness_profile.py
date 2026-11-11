"""
Tests for the codx-junior harness profile and process supervision assets.

Checks that:

* the built-in ``codx-junior`` profile exists and declares the all-tools
  marker,
* the workspace copy of the profile stays in sync with the built-in one,
* the ``supervisor.conf`` at the repository root supervises every harness
  process with autorestart (the ``codx-junior-api-background`` program name
  matches the one the harness watchdog restarts).

Run with::

    cd api && pytest tests/harness/test_harness_profile.py -q
"""

import json
import os
from pathlib import Path

from codx.junior.model.profile import Profile

# api/tests/harness -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]

BUILTIN_PROFILE = (
    REPO_ROOT / "api" / "codx" / "junior" / "profiles" / "codx-junior" / "codx-junior.profile"
)
BUILTIN_CONTENT = (
    REPO_ROOT / "api" / "codx" / "junior" / "profiles" / "codx-junior" / "codx-junior.md"
)
WORKSPACE_PROFILE = REPO_ROOT / ".codx" / "profiles" / "codx-junior" / "codx-junior.profile"
SUPERVISOR_CONF = REPO_ROOT / "supervisor.conf"


def test_builtin_profile_exists_and_parses():
    assert BUILTIN_PROFILE.is_file()
    data = json.loads(BUILTIN_PROFILE.read_text(encoding="utf-8"))
    profile = Profile(**data)
    assert profile.name == "codx-junior"
    assert profile.tools == ["*"]
    assert profile.description
    assert "software_developer" in profile.team


def test_builtin_profile_instructions_exist():
    assert BUILTIN_CONTENT.is_file()
    content = BUILTIN_CONTENT.read_text(encoding="utf-8")
    assert "codx-junior harness" in content
    assert "orchestrator(action=\"start\")" in content
    assert "orchestrator(action=\"finish\"" in content


def test_workspace_copy_matches_builtin():
    assert WORKSPACE_PROFILE.is_file()
    assert (
        WORKSPACE_PROFILE.read_text(encoding="utf-8")
        == BUILTIN_PROFILE.read_text(encoding="utf-8")
    )


def test_supervisor_conf_supervises_all_processes_with_autorestart():
    assert SUPERVISOR_CONF.is_file()
    conf = SUPERVISOR_CONF.read_text(encoding="utf-8")
    for program in ("codx-junior-api", "codx-junior-api-background", "codx-junior-client"):
        assert f"[program:{program}]" in conf, f"missing program {program}"
    assert conf.count("autorestart=true") == 3
    # The watchdog restarts this exact program name.
    from codx.junior.harness.watchdog import BACKGROUND_PROGRAM

    assert BACKGROUND_PROGRAM == "codx-junior-api-background"
    assert f"[program:{BACKGROUND_PROGRAM}]" in conf
