"""Regression tests for the tool dispatch contract of the browser script tools.

The tools are registered with ``project_settings=True``, so SmolAgent calls
them with ``settings=<CODXJuniorSettings>`` (and ``chat_id``) injected as
keyword arguments. A signature without ``**kwargs`` raises
``TypeError: ... unexpected keyword argument 'settings'`` **before** the body
runs, which is exactly the failure these tests lock down.
"""

import asyncio

import pytest

from codx.junior.tools.browser_script_tools import (
    BROWSER_SCRIPT_TOOLS,
    delete_browser_script,
    get_browser_script,
    list_browser_scripts,
    resolve_project_path,
    save_browser_script,
)


class _FakeSettings:
    """Minimal stand-in for CODXJuniorSettings (only project_path is used)."""

    def __init__(self, project_path):
        self.project_path = project_path


def _steps():
    return [
        {"action": "goto", "url": "https://github.com/login"},
        {"action": "click", "selector": "input[type=submit]"},
    ]


def _call(coroutine):
    return asyncio.run(coroutine)


@pytest.fixture
def project(tmp_path):
    project_path = tmp_path / "project"
    project_path.mkdir()
    return project_path


def test_resolve_project_path_prefers_injected_settings(project):
    assert resolve_project_path(settings=_FakeSettings(str(project))) == str(project)
    # explicit argument wins over settings
    assert resolve_project_path(project_path=str(project / "x"), settings=_FakeSettings("/elsewhere")) == str(
        project / "x"
    )


def test_tools_accept_injected_settings(project):
    """Every tool must tolerate settings/chat_id/unknown kwargs (dispatch)."""
    settings = _FakeSettings(str(project))

    saved = _call(
        save_browser_script(
            title="GitHub login",
            code=_steps(),
            site="github.com",
            settings=settings,
            chat_id="chat-1",
        )
    )
    assert "Browser script saved" in saved.llm_response

    listed = _call(list_browser_scripts(site="github.com", settings=settings, chat_id="chat-1"))
    assert "GitHub login" in listed.llm_response

    script_id = listed.llm_response.split("`")[1] if "`" in listed.llm_response else None
    loaded = _call(get_browser_script(title="GitHub login", site="github.com", settings=settings, chat_id="chat-1"))
    assert "GitHub login" in loaded.llm_response

    removed = _call(delete_browser_script(script_id=script_id, settings=settings, chat_id="chat-1"))
    assert "does not exist" in removed.llm_response or "moved to" in removed.llm_response


def test_tools_accept_arbitrary_injected_kwargs(project):
    """Future injected arguments must not break dispatch."""
    result = _call(list_browser_scripts(settings=_FakeSettings(str(project)), some_future_flag=True))
    assert result.llm_response


def test_registry_entries_declare_project_settings():
    for entry in BROWSER_SCRIPT_TOOLS:
        settings = entry["settings"]
        assert settings.get("project_settings") is True
        assert settings.get("async") is True or settings.get("is_async") is True