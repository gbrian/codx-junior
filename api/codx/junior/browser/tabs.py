"""
Tab (page) management for the shared browser session.

The browser container is a real Chromium window: the user watches it through the
live VNC view while the AI drives it over CDP, so tabs are a **shared** resource.
Opening, selecting and closing them must be visible in that same window.

``Browser`` (``codx.junior.browser.browser``) owns the connection and the page
automation primitives; this module adds the tab primitives it deliberately does
not cover, operating on a connected ``Browser``:

    tabs = await list_tabs(browser)         # every tab + active flag
    tab  = await open_tab(browser, url)     # new tab, navigated and focused
    tab  = await switch_tab(browser, index) # move the AI (and the user) to it
    tab  = await close_tab(browser, index)  # close one, activate the next

Keep-alive tab
--------------
Chromium exits when its **last window closes**, and the container keeps running
(the desktop session is still alive), so the live view stays up while the
browser window is gone: neither the user nor the AI can reach the page again
until the browser process is restarted.

To make that impossible by accident, every session owns one **keep-alive tab**
(``about:blank#codx-keep-alive``, titled "codx-junior · keep this tab open"):

- ``ensure_keep_alive_tab`` creates it once and reactivates the working tab, so
  closing every other tab leaves the window (and Chromium) alive;
- ``close_tab`` refuses to close it;
- ``ensure_page`` reopens a page when, despite the guard, the browser ends up
  with no tabs at all (see ``BrowserManager.connect_browser`` for the full
  recovery of a dead browser).

Conventions
-----------
- the *tab index* is the position of the page in ``context.pages`` (stable while
  no tab is opened or closed); that is what the agent tools expose;
- ``browser.page`` always points at the tab the AI drives;
- every selection is brought to front, so the live view shows the tab the AI is
  working on (co-browsing);
- the keep-alive tab and the last tab are never closed: closing them would close
  the browser window the user is watching.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: Hard cap on the tabs an agent may open (they are all visible to the user).
MAX_TABS = 20

#: Fragment identifying the protected tab (survives reconnections).
KEEP_ALIVE_FRAGMENT = "codx-keep-alive"
#: URL of the protected tab (``about:blank`` + marker fragment).
KEEP_ALIVE_URL = f"about:blank#{KEEP_ALIVE_FRAGMENT}"
#: Title of the protected tab (what the user reads in the tab strip).
KEEP_ALIVE_TITLE = "codx-junior · keep this tab open"
#: Content of the protected tab: explains why it must stay open.
KEEP_ALIVE_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{KEEP_ALIVE_TITLE}</title>
  <style>
    html, body {{ height: 100%; margin: 0; }}
    body {{
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; gap: .75rem; padding: 2rem;
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      background: #101418; color: #e6edf3;
    }}
    h1 {{ margin: 0; font-size: 1.25rem; font-weight: 600; }}
    p {{ margin: 0; max-width: 34rem; text-align: center; font-size: .875rem; color: #9aa7b4; }}
    code {{ font-size: .8rem; color: #7cc4ff; }}
  </style>
</head>
<body>
  <h1>{KEEP_ALIVE_TITLE}</h1>
  <p>
    This tab keeps the browser window open while you and the AI work.
    Do not close it: the browser (and this live view) would disappear.
  </p>
  <p><code>codx-junior</code></p>
</body>
</html>"""

#: Timeout (ms) used when restoring a page after the browser lost every tab.
RECOVER_TIMEOUT_MS = 15000


def _session_label(browser) -> str:
    """Short session id used in the log lines (never raises)."""
    session = getattr(browser, "session", None)
    return str(getattr(session, "id", "") or "?")[:8]


def _is_closed(page) -> bool:
    """Return True when the page is already closed (never raises)."""
    try:
        return bool(page.is_closed())
    except Exception:
        return False


def open_pages(browser) -> List[Any]:
    """
    Return the open tabs of a connected browser.

    Args:
        browser: Connected :class:`Browser`.

    Returns:
        List[Any]: Playwright pages, in the browser's tab order.

    Raises:
        RuntimeError: When the browser is not connected.

    Example:
        >>> open_pages(browser)  # doctest: +SKIP
        [<Page url='https://example.com'>]
    """
    context = getattr(browser, "context", None)
    if context is None:
        raise RuntimeError("Browser not connected (call start_session first)")
    return [page for page in list(context.pages) if not _is_closed(page)]


def page_url(page) -> str:
    """Return the page URL, or ``about:blank`` when it cannot be read."""
    try:
        return page.url or "about:blank"
    except Exception:
        return "about:blank"


def is_keep_alive_page(page) -> bool:
    """
    Return True when *page* is the session's protected (keep-alive) tab.

    Args:
        page: Playwright page.

    Returns:
        bool: True when the page carries :data:`KEEP_ALIVE_FRAGMENT`.

    Example:
        >>> is_keep_alive_page(page)  # doctest: +SKIP
        True
    """
    return KEEP_ALIVE_FRAGMENT in page_url(page)


def keep_alive_page(browser) -> Optional[Any]:
    """
    Return the session's protected tab, or None when it does not exist.

    Args:
        browser: Connected :class:`Browser`.

    Returns:
        Optional[Any]: The keep-alive page, or None.
    """
    for page in open_pages(browser):
        if is_keep_alive_page(page):
            return page
    return None


def active_tab_index(browser, pages: Optional[List[Any]] = None) -> int:
    """
    Return the index of the tab the AI is driving.

    Args:
        browser: Connected :class:`Browser`.
        pages: Already resolved tab list (avoids a second lookup).

    Returns:
        int: Index in ``pages``, or -1 when there are no tabs.
    """
    pages = open_pages(browser) if pages is None else pages
    page = getattr(browser, "page", None)
    for index, candidate in enumerate(pages):
        if candidate is page:
            return index
    return len(pages) - 1 if pages else -1


def page_index(browser, page) -> int:
    """Return the position of *page* in the tab list (-1 when not tracked)."""
    try:
        return open_pages(browser).index(page)
    except (ValueError, RuntimeError):
        return -1


async def describe_tab(browser, page, index: int) -> Dict[str, Any]:
    """
    Build the tab descriptor returned to the agent tools.

    Args:
        browser: Connected :class:`Browser` (used to flag the active tab).
        page: Playwright page.
        index: Position of the page in the tab list.

    Returns:
        Dict with ``index``, ``id``, ``url``, ``title``, ``active``, ``closed``
        and ``keep_alive``.
    """
    url = page_url(page)
    try:
        title = (await page.title()) or ""
    except Exception:
        title = ""
    return {
        "index": index,
        "id": f"tab-{index}",
        "url": url,
        "title": title.strip(),
        "active": page is getattr(browser, "page", None),
        "closed": _is_closed(page),
        "keep_alive": is_keep_alive_page(page),
    }


async def _sync_location(browser, page) -> None:
    """
    Mirror the tab URL/title into the session (summaries, audit and UI read it).

    Kept out of ``Browser`` on purpose: tab handling must not depend on that
    class' private helpers.
    """
    session = getattr(browser, "session", None)
    if session is None:
        return
    try:
        session.current_url = page.url or session.current_url
    except Exception:
        pass
    try:
        session.current_title = await page.title()
    except Exception:
        pass
    try:
        session.mark_active()
    except Exception:
        pass


async def _activate(browser, page) -> None:
    """Make *page* the page the AI drives and the tab the user sees."""
    browser.page = page
    try:
        await page.bring_to_front()
    except Exception as ex:
        # Not fatal: the tab is still drivable, only the focus hint was lost.
        logger.debug("bring_to_front failed: %s", ex)
    await _sync_location(browser, page)


async def ensure_page(browser, restore: bool = True):
    """
    Return a drivable page, recreating one when every tab was closed.

    Chromium can be left with zero tabs (the user closed them all). The browser
    process may still be alive, so instead of failing every subsequent action a
    fresh tab is opened (restoring the session's last URL when asked).

    Args:
        browser: Connected :class:`Browser`.
        restore: Navigate the new tab to ``session.current_url`` (default).

    Returns:
        Page: The page the AI must drive (``browser.page`` is updated).

    Raises:
        RuntimeError: When the browser is not connected.
    """
    context = getattr(browser, "context", None)
    if context is None:
        raise RuntimeError("Browser not connected (call start_session first)")

    pages = open_pages(browser)
    if pages:
        current = getattr(browser, "page", None)
        if current in pages:
            return current
        browser.page = pages[-1]
        return browser.page

    page = await context.new_page()
    browser.page = page

    session = getattr(browser, "session", None)
    target = (getattr(session, "current_url", None) or "").strip() if restore else ""
    if target and target not in ("about:blank", "chrome://newtab/"):
        try:
            await page.goto(target, wait_until="load", timeout=RECOVER_TIMEOUT_MS)
        except Exception as ex:
            logger.warning("Could not restore '%s' after reopening a tab: %s", target, ex)

    await _sync_location(browser, page)
    logger.warning(
        "Session %s had no tabs left; reopened %s",
        _session_label(browser), target or "about:blank",
    )
    return page


async def ensure_keep_alive_tab(browser) -> Optional[Dict[str, Any]]:
    """
    Make sure the protected tab that keeps the browser window open exists.

    The tab is created once per session and never activated: the tab the AI is
    driving (and the user is watching) keeps the focus.

    Args:
        browser: Connected :class:`Browser`.

    Returns:
        Optional[Dict[str, Any]]: Descriptor of the protected tab, or None when
        it cannot be created (the session keeps working without it).

    Raises:
        RuntimeError: When the browser is not connected.
    """
    context = getattr(browser, "context", None)
    if context is None:
        raise RuntimeError("Browser not connected (call start_session first)")

    existing = keep_alive_page(browser)
    if existing is not None:
        return await describe_tab(browser, existing, page_index(browser, existing))

    previous = getattr(browser, "page", None)
    if previous is not None and _is_closed(previous):
        previous = None

    try:
        page = await context.new_page()
        try:
            await page.goto(KEEP_ALIVE_URL, wait_until="load", timeout=RECOVER_TIMEOUT_MS)
        except Exception as ex:
            logger.debug("Could not open %s: %s", KEEP_ALIVE_URL, ex)
        try:
            # Gives the tab its title/explanation (the URL keeps the marker)
            await page.set_content(KEEP_ALIVE_HTML)
        except Exception as ex:
            logger.debug("Could not set the keep-alive content: %s", ex)
    except Exception as ex:
        logger.warning("Could not create the keep-alive tab: %s", ex)
        return None

    if previous is not None:
        # Keep driving (and showing) the tab that was active before
        await _activate(browser, previous)
    else:
        browser.page = page

    logger.info("Keep-alive tab ready for session %s", _session_label(browser))
    return await describe_tab(browser, page, page_index(browser, page))


async def list_tabs(browser) -> List[Dict[str, Any]]:
    """
    Return every open tab; the one the AI drives carries ``active: True``.

    Args:
        browser: Connected :class:`Browser`.

    Returns:
        List[Dict[str, Any]]: One descriptor per tab, in tab order.

    Example:
        >>> await list_tabs(browser)  # doctest: +SKIP
        [{'index': 0, 'url': 'https://example.com', 'active': True, ...}]
    """
    if not open_pages(browser):
        await ensure_page(browser)
    pages = open_pages(browser)
    return [await describe_tab(browser, page, index) for index, page in enumerate(pages)]


async def open_tab(browser, url: Optional[str] = None) -> Dict[str, Any]:
    """
    Open a new tab, focus it and (optionally) navigate to *url*.

    The current tab is left untouched, so the agent can keep a reference page
    open while working on another one.

    Args:
        browser: Connected :class:`Browser`.
        url: Optional URL opened in the new tab (``file:///home/<project>/...``
            works for shared project folders).

    Returns:
        Dict[str, Any]: Descriptor of the new (now active) tab.

    Raises:
        RuntimeError: When the browser is not connected or :data:`MAX_TABS` is
            already reached.
        RuntimeError: When the navigation fails.
    """
    pages = open_pages(browser)
    if len(pages) >= MAX_TABS:
        raise RuntimeError(
            f"Too many open tabs ({len(pages)}); close one with close_tab first"
        )

    context = getattr(browser, "context", None)
    page = await context.new_page()
    await _activate(browser, page)
    if url:
        # navigate() keeps the networkidle -> load fallback and syncs the session
        await browser.navigate(url)

    index = active_tab_index(browser)
    logger.info(
        "Opened tab %s (%s) in session %s",
        index, url or "about:blank", _session_label(browser),
    )
    return await describe_tab(browser, page, index)


async def switch_tab(browser, index: Optional[int] = None) -> Dict[str, Any]:
    """
    Make the tab at *index* the one the AI drives and the user sees.

    Args:
        browser: Connected :class:`Browser`.
        index: Tab index (0-based). ``None`` keeps the active tab.

    Returns:
        Dict[str, Any]: Descriptor of the selected tab.

    Raises:
        RuntimeError: When the browser is not connected.
        ValueError: When *index* is not a number or is out of range.
    """
    if not open_pages(browser):
        await ensure_page(browser)
    pages = open_pages(browser)

    if index is None:
        target = active_tab_index(browser, pages)
    else:
        try:
            target = int(index)
        except (TypeError, ValueError):
            raise ValueError(f"tab index '{index}' is not a number")
    if target < 0 or target >= len(pages):
        raise ValueError(f"tab index {index} is out of range (0-{len(pages) - 1})")

    page = pages[target]
    await _activate(browser, page)
    logger.info("Switched to tab %s of session %s", target, _session_label(browser))
    return await describe_tab(browser, page, target)


async def close_tab(browser, index: Optional[int] = None) -> Dict[str, Any]:
    """
    Close a tab and activate the one that takes its place.

    Two tabs are protected: the last one (closing it closes the window the user
    is watching) and the keep-alive tab (closing it removes the protection that
    keeps Chromium alive when the user closes everything else).

    Args:
        browser: Connected :class:`Browser`.
        index: Tab index (0-based). ``None`` closes the active tab.

    Returns:
        Dict[str, Any]: Descriptor of the newly active tab plus ``closed_index``,
        ``closed_url`` and ``closed_title``.

    Raises:
        RuntimeError: When the browser is not connected, has no tabs, only one
            tab is left, or the selected tab is the keep-alive tab.
        ValueError: When *index* is not a number or is out of range.
    """
    pages = open_pages(browser)
    if not pages:
        raise RuntimeError("The browser has no open tabs")
    if len(pages) <= 1:
        raise RuntimeError(
            "Cannot close the last tab: it would close the browser window the user "
            "is watching. Navigate it somewhere else or open another tab first"
        )

    if index is None:
        target = active_tab_index(browser, pages)
    else:
        try:
            target = int(index)
        except (TypeError, ValueError):
            raise ValueError(f"tab index '{index}' is not a number")
    if target < 0 or target >= len(pages):
        raise ValueError(f"tab index {index} is out of range (0-{len(pages) - 1})")

    page = pages[target]
    if is_keep_alive_page(page):
        raise RuntimeError(
            "Refusing to close the keep-alive tab: it prevents the browser window "
            "from disappearing. Work in another tab instead of closing this one"
        )

    closed = await describe_tab(browser, page, target)
    await page.close()

    remaining = open_pages(browser)
    if not remaining:
        # Should not happen (the keep-alive tab is protected and the tab count was
        # checked), but never leave the session without a page.
        await ensure_page(browser)
        remaining = open_pages(browser)

    # The tab that now occupies the freed position becomes active
    next_index = min(target, len(remaining) - 1)
    await _activate(browser, remaining[next_index])
    logger.info(
        "Closed tab %s of session %s (active tab: %s)",
        target, _session_label(browser), next_index,
    )

    result = await describe_tab(browser, remaining[next_index], next_index)
    result["closed_index"] = target
    result["closed_url"] = closed.get("url")
    result["closed_title"] = closed.get("title")
    return result


def format_tabs(tabs: List[Dict[str, Any]]) -> str:
    """
    Render tabs as one line each, marking the active tab with ``*``.

    Args:
        tabs: Descriptors returned by :func:`list_tabs`.

    Returns:
        str: Plain text listing (``*`` = tab the AI is driving).

    Example:
        >>> print(format_tabs([{"index": 0, "title": "A", "url": "https://a", "active": True}]))
        * [0] A — https://a
    """
    if not tabs:
        return "(no open tabs)"
    lines = []
    for tab in tabs:
        marker = "*" if tab.get("active") else "-"
        title = tab.get("title") or "(untitled)"
        suffix = " [keep-alive: do not close]" if tab.get("keep_alive") else ""
        lines.append(
            f"{marker} [{tab.get('index')}] {title} — {tab.get('url') or 'about:blank'}{suffix}"
        )
    return "\n".join(lines)


# Made with ❤️ by codx-junior