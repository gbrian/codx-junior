"""Rendering escalation for pages that need JavaScript.

The static fetch is the default: it is free and fast. Rendering is the
exception, and it happens in two steps, cheapest first:

1. a **lite engine** (:mod:`codx.junior.browser.lite_engine`: Lightpanda, then
   Obscura) when one is installed — dozens of MB, milliseconds;
2. **Chromium** (Playwright, headless, installed automatically) otherwise.

Chromium is launched here and never touched directly by the tools: Playwright
stays inside the browser stack, and this module returns the same
:class:`~codx.junior.web.extract.ExtractedContent` as the static path.

Made with ❤️ by codx-junior
"""

import logging
from typing import List, Optional

from codx.junior.web.extract import (
    ExtractedContent,
    clean_markdown,
    extract_content,
    text_from_markdown,
)

logger = logging.getLogger(__name__)


def _browser_module():
    """Import the shared browser helpers lazily (keeps Playwright optional)."""
    from codx.junior.browser import browser as playwright_browser

    return playwright_browser


async def render_html_async(
    url: str,
    wait_timeout_ms: int = 0,
    wait_for_selector: Optional[str] = None,
    script: Optional[str] = None,
    auto_install: Optional[bool] = None,
) -> str:
    """Render ``url`` with a local headless Chromium and return its HTML.

    Args:
        url: Page URL.
        wait_timeout_ms: Extra delay after load so async rendering settles.
        wait_for_selector: Selector to wait for before reading the DOM.
        script: JavaScript evaluated right before reading the DOM.
        auto_install: Install the missing Playwright components (None reads
            ``CODX_BROWSER_AUTO_INSTALL``, enabled by default).

    Returns:
        str: Serialized DOM (``page.content()``).

    Raises:
        BrowserUnavailableError: When Chromium cannot be started.
    """
    pw = _browser_module()

    if auto_install is not False:
        await pw.ensure_playwright_ready_async(auto_install)

    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(
                headless=True, args=list(pw.CHROMIUM_LAUNCH_ARGS)
            )
        except Exception as ex:
            message = str(ex)
            if auto_install is False:
                raise pw.BrowserUnavailableError(
                    f"headless Chromium could not start: {message}"
                ) from ex
            logger.warning("Chromium could not start (%s); installing components", message)
            if not await pw.ensure_playwright_ready_async(auto_install=True, force_install=True):
                raise pw.BrowserUnavailableError(
                    f"headless Chromium could not start: {message}"
                ) from ex
            browser = await playwright.chromium.launch(
                headless=True, args=list(pw.CHROMIUM_LAUNCH_ARGS)
            )

        try:
            page = await browser.new_page()
            try:
                await page.goto(
                    url, wait_until=pw.BROWSER_WAIT_UNTIL, timeout=pw.BROWSER_TIMEOUT_MS
                )
            except Exception as ex:
                logger.warning(
                    "wait '%s' failed for %s (%s); retrying with '%s'",
                    pw.BROWSER_WAIT_UNTIL, url, ex, pw.BROWSER_WAIT_UNTIL_FALLBACK,
                )
                await page.goto(
                    url,
                    wait_until=pw.BROWSER_WAIT_UNTIL_FALLBACK,
                    timeout=pw.BROWSER_TIMEOUT_MS,
                )

            if wait_for_selector:
                await page.wait_for_selector(
                    wait_for_selector, timeout=pw.BROWSER_TIMEOUT_MS
                )
            if script:
                await page.evaluate(script)
            if wait_timeout_ms:
                await page.wait_for_timeout(int(wait_timeout_ms))

            return await page.content()
        finally:
            await browser.close()


def render_html(
    url: str,
    wait_timeout_ms: int = 0,
    wait_for_selector: Optional[str] = None,
    script: Optional[str] = None,
    auto_install: Optional[bool] = None,
) -> str:
    """Synchronous, event-loop safe wrapper around :func:`render_html_async`."""
    pw = _browser_module()
    try:
        return pw.run_coroutine_sync(
            lambda: render_html_async(
                url,
                wait_timeout_ms=wait_timeout_ms,
                wait_for_selector=wait_for_selector,
                script=script,
                auto_install=auto_install,
            )
        )
    except pw.BrowserUnavailableError:
        raise
    except ImportError as ex:
        raise pw.BrowserUnavailableError(
            "the playwright package is not installed and could not be installed automatically"
        ) from ex


def fetch_with_lite_engine(
    url: str,
    settings=None,
    notes: Optional[List[str]] = None,
) -> Optional[ExtractedContent]:
    """Render ``url`` with the configured lite engine, if any.

    Args:
        url: Page URL.
        settings: ``WebSettings`` (read from the current configuration when
            omitted).
        notes: List that receives a human readable failure reason.

    Returns:
        Optional[ExtractedContent]: Content, or ``None`` when no engine is
        available or it returned nothing.
    """
    from codx.junior.browser.lite_engine import load_engine
    from codx.junior.web.settings import load_web_settings

    config = settings or load_web_settings()
    engine = load_engine(config.lite_engine)
    if engine is None:
        return None

    try:
        markdown = engine.fetch(url, dump="markdown")
    except Exception as ex:
        logger.warning("lite engine '%s' failed for %s: %s", engine.name, url, ex)
        if notes is not None:
            notes.append(f"lite engine '{engine.name}': {ex}")
        return None

    if not (markdown or "").strip():
        if notes is not None:
            notes.append(f"lite engine '{engine.name}' returned no content")
        return None

    cleaned = clean_markdown(markdown)
    return ExtractedContent(
        url=url,
        markdown=cleaned,
        text=text_from_markdown(cleaned),
        extractor=f"lite-{engine.name}",
    )


def fetch_with_chromium(
    url: str,
    include_images: bool = True,
    wait_timeout_ms: int = 0,
    notes: Optional[List[str]] = None,
) -> Optional[ExtractedContent]:
    """Render ``url`` with Chromium and extract its content.

    Args:
        url: Page URL.
        include_images: Keep image references in the markdown.
        wait_timeout_ms: Extra delay before reading the DOM.
        notes: List that receives a human readable failure reason.

    Returns:
        Optional[ExtractedContent]: Content, or ``None`` when Chromium is not
        available.
    """
    try:
        html = render_html(url, wait_timeout_ms=wait_timeout_ms)
    except Exception as ex:
        logger.warning("Chromium escalation failed for %s: %s", url, ex)
        if notes is not None:
            notes.append(f"chromium: {ex}")
        return None

    content = extract_content(html, url=url, include_images=include_images)
    content.extractor = f"chromium+{content.extractor}" if content.extractor else "chromium"
    return content


def fetch_rendered(
    url: str,
    settings=None,
    include_images: bool = True,
    wait_timeout_ms: int = 0,
    notes: Optional[List[str]] = None,
) -> Optional[ExtractedContent]:
    """Render ``url``: lite engine first, Chromium as the fallback.

    Args:
        url: Page URL.
        settings: ``WebSettings`` (read from the current configuration when
            omitted).
        include_images: Keep image references in the markdown.
        wait_timeout_ms: Extra delay applied to the Chromium path.
        notes: List that receives the failure reasons of both attempts.

    Returns:
        Optional[ExtractedContent]: Content, or ``None`` when nothing could be
        rendered.
    """
    content = fetch_with_lite_engine(url, settings=settings, notes=notes)
    if content is not None:
        return content
    return fetch_with_chromium(
        url,
        include_images=include_images,
        wait_timeout_ms=wait_timeout_ms,
        notes=notes,
    )