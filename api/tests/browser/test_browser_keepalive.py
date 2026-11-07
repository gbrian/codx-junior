"""Tests for the keep-alive tab and the browser recovery path.

Chromium exits when its last window is closed, so the session must (a) keep a
protected tab open and (b) recover when the browser process is already gone.
Playwright is not required: the tests drive fake pages/contexts that mimic the
parts of the API the tab layer relies on (``context.pages``, ``new_page()``,
``page.title()``, ``page.goto()``, ``page.set_content()``, ``page.close()``).
"""

import asyncio

import pytest

from codx.junior.browser import browser_manager as browser_manager_module
from codx.junior.browser import tabs as browser_tabs
from codx.junior.browser.browser_manager import BrowserManager
from codx.junior.browser.model import BrowserSession


class _FakeSession:
    """Minimal BrowserSession stand-in (only the fields the tab layer touches)."""

    def __init__(self, current_url=None):
        self.id = "12345678-aaaa-bbbb-cccc-ddddeeeeffff"
        self.current_url = current_url
        self.current_title = None
        self.active_calls = 0

    def mark_active(self):
        self.active_calls += 1


class _FakePage:
    def __init__(self, url="about:blank", title="", context=None):
        self.url = url
        self._title = title
        self._closed = False
        self.context = context
        self.front_calls = 0
        self.navigations = []
        self.content = None

    async def title(self):
        return self._title

    def is_closed(self):
        return self._closed

    async def bring_to_front(self):
        self.front_calls += 1

    async def goto(self, url, wait_until=None, timeout=None):
        self.navigations.append(url)
        self.url = url
        return None

    async def set_content(self, html, wait_until=None):
        self.content = html
        self._title = browser_tabs.KEEP_ALIVE_TITLE if "keep this tab open" in html else self._title

    async def close(self):
        self._closed = True
        if self.context and self in self.context.pages:
            self.context.pages.remove(self)


class _FakeContext:
    def __init__(self, pages=None):
        self.pages = list(pages or [])

    async def new_page(self):
        page = _FakePage(context=self)
        self.pages.append(page)
        return page


class _FakeBrowser:
    """Connected Browser double: context, active page and session."""

    def __init__(self, pages=None, current_url=None):
        pages = list(pages) if pages else [_FakePage(url="https://a.test", title="A")]
        self.context = _FakeContext(pages)
        for page in pages:
            page.context = self.context
        self.page = pages[0]
        self.session = _FakeSession(current_url=current_url)
        self.browser = None

    async def navigate(self, url):
        self.page.url = url
        self.page._title = f"title of {url}"
        return self.page._title


def _run(coroutine):
    return asyncio.run(coroutine)


# ---------------------------------------------------------------------------
# Keep-alive tab
# ---------------------------------------------------------------------------

def test_ensure_keep_alive_tab_creates_it_once_and_keeps_the_working_tab_active():
    working = _FakePage(url="https://a.test", title="A")
    browser = _FakeBrowser([working])

    tab = _run(browser_tabs.ensure_keep_alive_tab(browser))

    assert tab["keep_alive"] is True
    assert tab["active"] is False
    assert tab["url"] == browser_tabs.KEEP_ALIVE_URL
    assert len(browser.context.pages) == 2
    # The tab the AI/user work on stays the active one (live view follows it)
    assert browser.page is working

    keep_alive = browser.context.pages[1]
    assert keep_alive.content and browser_tabs.KEEP_ALIVE_TITLE in keep_alive.content

    # Idempotent: a second call never adds another tab
    again = _run(browser_tabs.ensure_keep_alive_tab(browser))
    assert again["index"] == tab["index"]
    assert len(browser.context.pages) == 2


def test_keep_alive_tab_is_the_only_tab_when_the_others_were_closed():
    browser = _FakeBrowser([_FakePage(url="about:blank", title="")])

    _run(browser_tabs.ensure_keep_alive_tab(browser))
    working = browser.context.pages[0]
    _run(browser_tabs.close_tab(browser, 0))

    assert browser.page is not working
    assert browser_tabs.is_keep_alive_page(browser.page)
    assert len(browser.context.pages) == 1


def test_list_tabs_flags_the_keep_alive_tab():
    working = _FakePage(url="https://a.test", title="A")
    keep_alive = _FakePage(url=browser_tabs.KEEP_ALIVE_URL, title=browser_tabs.KEEP_ALIVE_TITLE)
    browser = _FakeBrowser([working, keep_alive])

    tabs = _run(browser_tabs.list_tabs(browser))

    assert [tab["keep_alive"] for tab in tabs] == [False, True]
    text = browser_tabs.format_tabs(tabs)
    assert "[keep-alive: do not close]" in text


def test_close_tab_refuses_the_keep_alive_tab():
    working = _FakePage(url="https://a.test", title="A")
    keep_alive = _FakePage(url=browser_tabs.KEEP_ALIVE_URL, title=browser_tabs.KEEP_ALIVE_TITLE)
    browser = _FakeBrowser([working, keep_alive])

    with pytest.raises(RuntimeError) as error:
        _run(browser_tabs.close_tab(browser, 1))

    assert "keep-alive" in str(error.value)
    assert len(browser.context.pages) == 2


def test_close_tab_refuses_the_last_tab():
    browser = _FakeBrowser([_FakePage(url="https://a.test", title="A")])

    with pytest.raises(RuntimeError) as error:
        _run(browser_tabs.close_tab(browser, 0))

    assert "last tab" in str(error.value)
    assert len(browser.context.pages) == 1


def test_close_tab_activates_the_next_tab():
    first = _FakePage(url="https://a.test", title="A")
    second = _FakePage(url="https://b.test", title="B")
    third = _FakePage(url="https://c.test", title="C")
    browser = _FakeBrowser([first, second, third])

    tab = _run(browser_tabs.close_tab(browser, 1))

    assert tab["closed_index"] == 1
    assert second.is_closed() is True
    assert browser.page is third
    assert browser.session.current_url == "https://c.test"


# ---------------------------------------------------------------------------
# Page recovery
# ---------------------------------------------------------------------------

def test_ensure_page_reopens_the_last_url_when_every_tab_was_closed():
    browser = _FakeBrowser([_FakePage(url="https://a.test", title="A")],
                           current_url="https://example.com/report")
    browser.context.pages.clear()
    browser.page = None

    page = _run(browser_tabs.ensure_page(browser))

    assert browser.context.pages == [page]
    assert browser.page is page
    assert page.navigations == ["https://example.com/report"]
    assert browser.session.current_url == "https://example.com/report"


def test_ensure_page_does_not_navigate_when_asked_not_to_restore():
    browser = _FakeBrowser(current_url="https://example.com/report")
    browser.context.pages.clear()
    browser.page = None

    page = _run(browser_tabs.ensure_page(browser, restore=False))

    assert page.navigations == []
    assert page.url == "about:blank"


def test_list_tabs_recovers_a_browser_without_tabs():
    browser = _FakeBrowser()
    browser.context.pages.clear()
    browser.page = None

    tabs = _run(browser_tabs.list_tabs(browser))

    assert len(tabs) == 1
    assert tabs[0]["active"] is True


def test_open_tab_navigates_and_focuses_the_new_page():
    browser = _FakeBrowser()

    tab = _run(browser_tabs.open_tab(browser, "https://new.test"))

    assert tab["index"] == 1
    assert tab["active"] is True
    assert browser.page is browser.context.pages[1]
    assert browser.page.front_calls == 1


def test_open_tab_enforces_the_tab_limit(monkeypatch):
    monkeypatch.setattr(browser_tabs, "MAX_TABS", 2)
    browser = _FakeBrowser([_FakePage(), _FakePage()])

    with pytest.raises(RuntimeError):
        _run(browser_tabs.open_tab(browser, "https://new.test"))


def test_tab_helpers_require_a_connected_browser():
    class _Disconnected:
        context = None
        page = None

    with pytest.raises(RuntimeError):
        _run(browser_tabs.list_tabs(_Disconnected()))
    with pytest.raises(RuntimeError):
        _run(browser_tabs.ensure_keep_alive_tab(_Disconnected()))


# ---------------------------------------------------------------------------
# BrowserManager recovery
# ---------------------------------------------------------------------------

class _RecoveredBrowser(_FakeBrowser):
    """Browser double whose first connection attempt fails (dead Chromium)."""

    fail_first = True
    attempts = 0

    def __init__(self, session, docker_manager):
        super().__init__()
        self.manager = docker_manager
        type(self).attempts += 1

    async def connect(self):
        if type(self).fail_first and type(self).attempts == 1:
            raise RuntimeError("Browser connection failed: Connection refused")
        return None

    async def close(self):
        return None


def _manager(tmp_path):
    manager = BrowserManager.__new__(BrowserManager)
    manager.sessions_path = str(tmp_path)
    manager.settings = type("Settings", (), {"project_id": "project-1"})()
    manager.docker_manager = type("Docker", (), {"stop_container": lambda self, *args, **kwargs: None, "restart_container": lambda self, target: target})()
    return manager


def test_connect_browser_restarts_a_dead_browser_and_retries(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    session = BrowserSession(name="Dead browser", container_id="abc", status="running")
    restarted = []

    _RecoveredBrowser.fail_first = True
    _RecoveredBrowser.attempts = 0
    monkeypatch.setattr(browser_manager_module, "Browser", _RecoveredBrowser)
    monkeypatch.setattr(
        manager, "_restart_browser", lambda target, reason="recover": restarted.append(target.id) or target
    )

    browser = _run(manager.connect_browser(session))

    assert restarted == [session.id]
    assert _RecoveredBrowser.attempts == 2
    # The protected tab is ensured on every connection
    assert browser_tabs.keep_alive_page(browser) is not None


def test_connect_browser_does_not_restart_without_a_container(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    session = BrowserSession(name="No container", status="error")

    _RecoveredBrowser.fail_first = True
    _RecoveredBrowser.attempts = 0
    monkeypatch.setattr(browser_manager_module, "Browser", _RecoveredBrowser)
    monkeypatch.setattr(
        manager, "_restart_browser", lambda target, reason="recover": pytest.fail("must not restart")
    )

    with pytest.raises(RuntimeError):
        _run(manager.connect_browser(session))


def test_restart_session_relaunches_chromium_and_restores_the_keep_alive_tab(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    session = BrowserSession(name="Restart", container_id="abc", status="running")
    calls = []

    monkeypatch.setattr(manager, "get_session", lambda session_id: session)
    monkeypatch.setattr(manager, "_save_session_file", lambda target: calls.append("save"))
    monkeypatch.setattr(
        manager, "log_activity", lambda target, **kwargs: calls.append(kwargs["action"])
    )
    monkeypatch.setattr(
        manager.docker_manager,
        "stop_container",
        lambda target, remove=True: calls.append(("stop", remove)),
    )
    monkeypatch.setattr(
        manager.docker_manager, "restart_container", lambda target: calls.append("start") or target
    )
    monkeypatch.setattr(
        manager, "_open_keep_alive_tab", lambda target: calls.append("keep-alive")
    )

    restarted = _run(manager.restart_session(session.id))

    assert restarted is session
    # The container is stopped and started again: that relaunches Chromium
    assert ("stop", False) in calls
    assert "start" in calls
    assert "restart" in calls
    # The keep-alive tab/recorder are ensured by the persistent runtime on its
    # next connection, not by opening a second Playwright connection here.
    assert "keep-alive" not in calls


def test_open_keep_alive_tab_is_skipped_without_a_ready_browser(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    monkeypatch.setattr(
        manager, "_ensure_keep_alive_tab_async", lambda target: pytest.fail("must not connect")
    )

    # Stopped session: no debug_url, nothing to do
    manager._open_keep_alive_tab(BrowserSession(name="Stopped", status="stopped"))