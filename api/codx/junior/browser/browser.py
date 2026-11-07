"""
Browser — single entry point for every Playwright usage in codx-junior.

Two responsibilities live here so the rest of the application never imports
playwright directly:

    1. ``Browser``: automation of a remote Chromium container through the
       Chrome DevTools Protocol (navigation, scripts, screenshots, page
       content).  The same browser is shown to users through the live VNC view.
    2. ``PdfPrinter`` / ``print_pdf``: rendering of pages with a local headless
       Chromium, used by the document converter (rich HTML slides -> PDF).

Shared helpers (availability check, event-loop safe runner, script
normalization, page size / margin parsing) are module level so every consumer
behaves the same way.

Missing Playwright components are installed on demand by
``ensure_playwright_ready``: the ``playwright`` package (``pip install``) and the
Chromium build (``playwright install chromium``), plus the system libraries
(``playwright install-deps``) when the browser cannot start because of them.
The installation happens once per process, is logged and can be disabled with
``CODX_BROWSER_AUTO_INSTALL=0``.

Chart:
    flowchart LR
        A[Browser session] --> B[DockerBrowserManager]
        B --> C[Browser\nCDP automation]
        D[doc_converter] --> E[print_pdf]
        E --> F{Chromium?}
        F -->|missing| G[ensure_playwright_ready\npip / playwright install]
        F -->|present| H[PdfPrinter\nheadless Chromium]
        G --> H
        H --> I[pdf]

Made with ❤️ by codx-junior
"""

import asyncio
import base64
import importlib
import logging
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from codx.junior.browser.model import BrowserSession
from codx.junior.browser.docker_browser_manager import DockerBrowserManager
from codx.junior.browser.recorder import RECORDER_SCRIPT, SNAPSHOT_SCRIPT

logger = logging.getLogger(__name__)

#: Label reported when a document was rendered by the headless browser.
BROWSER_ENGINE_LABEL = "playwright-chromium"

#: CSS media types that can be emulated before printing a page.
BROWSER_MEDIA_TYPES = ("screen", "print")

#: Wait strategy used when a page is opened.  ``networkidle`` is deliberately
#: not used: live applications keep websockets/long-polling open and the wait
#: can only end by timing out (the old code paid up to 30 s, then navigated a
#: second time).  ``domcontentloaded`` plus a short, best-effort ``load`` wait
#: is what makes an action feel instant.
BROWSER_WAIT_UNTIL = "domcontentloaded"
#: Fallback/load state waited for after the document is parsed.
BROWSER_WAIT_UNTIL_FALLBACK = "load"
#: Best-effort time (ms) allowed for the ``load`` state after DOM content.
BROWSER_LOAD_WAIT_MS = 5000
#: Timeout (ms) applied to navigation, selectors and printing.
BROWSER_TIMEOUT_MS = 30000

#: Chromium arguments required to run inside containers.
CHROMIUM_LAUNCH_ARGS = ("--no-sandbox", "--disable-dev-shm-usage")

#: Browser build used by the PDF renderer.
CHROMIUM_BROWSER_TYPE = "chromium"

#: Paper formats accepted by playwright's ``format`` option.
PDF_PAGE_FORMATS = (
    "A3", "A4", "A5", "A6", "B4", "B5",
    "Letter", "Legal", "Ledger", "Tabloid",
)

#: Page geometry of the slide deck preset: 16:9 at CSS pixels.
SLIDE_PAGE_SIZE = "1920x1080"

#: Environment flag used to disable the runtime installation.
PLAYWRIGHT_AUTO_INSTALL_ENV = "CODX_BROWSER_AUTO_INSTALL"
#: Values of :data:`PLAYWRIGHT_AUTO_INSTALL_ENV` that disable the installation.
_DISABLED_FLAGS = ("0", "false", "no", "off")

#: Timeout (seconds) for the pip/paywright installers (browser download).
PLAYWRIGHT_INSTALL_TIMEOUT_S = 900

#: Hint appended to the errors raised when the browser cannot be used.
PLAYWRIGHT_INSTALL_HINT = (
    "install it with 'pip install playwright' and download the browser with "
    "'playwright install chromium'"
)

#: Playwright error fragments meaning "the browser binary is missing".
_BROWSER_MISSING_HINTS = (
    "Executable doesn't exist",
    "playwright install",
    "Host system is missing dependencies",
    "Browser was not found",
)

#: Playwright/pip error fragments meaning "the OS libraries are missing".
_MISSING_DEPENDENCIES_HINTS = (
    "Host system is missing dependencies",
    "missing dependencies",
    "install-deps",
    "libnss3",
    "libatk",
)

# Runtime installation state: the installers are idempotent and only attempted
# once per process unless a forced retry is requested.
_package_install_lock = threading.Lock()
_package_install_attempted = False
_package_install_ok = False

_browser_install_lock = threading.Lock()
_browser_install_attempted = False
_browser_install_ok = False
_browser_install_error: Optional[str] = None


class BrowserUnavailableError(RuntimeError):
    """Raised when Playwright or its Chromium binary cannot be used."""


def _short_id(value: Optional[str]) -> str:
    """Safely shorten an id for logging (never raises on None/short ids)."""
    return (value or "?")[:8]


def _tail(text: Optional[str], limit: int = 400) -> str:
    """
    Collapse command output into a short single line, keeping the end.

    Args:
        text: Command stdout/stderr.
        limit: Maximum number of characters kept.

    Returns:
        str: Whitespace-normalized tail of the output.

    Example:
        >>> _tail("a\\n  b")
        'a b'
    """
    value = " ".join((text or "").split())
    return value[-limit:]


def _auto_install_enabled(auto_install: Optional[bool] = None) -> bool:
    """
    Resolve whether missing Playwright components may be installed.

    The explicit argument wins; otherwise :data:`PLAYWRIGHT_AUTO_INSTALL_ENV`
    decides (enabled by default).

    Args:
        auto_install: Explicit flag from the caller.

    Returns:
        bool: True when components may be installed at runtime.

    Example:
        >>> _auto_install_enabled(None)
        True
    """
    if auto_install is not None:
        return bool(auto_install)
    value = (os.environ.get(PLAYWRIGHT_AUTO_INSTALL_ENV) or "").strip().lower()
    if not value:
        # Installation is enabled unless explicitly disabled
        return True
    return value not in _DISABLED_FLAGS


def _is_browser_missing(message: str) -> bool:
    """Return True when a playwright error means the browser binary is absent."""
    return any(hint in message for hint in _BROWSER_MISSING_HINTS)


def _is_missing_dependencies(message: str) -> bool:
    """Return True when a playwright error means system libraries are absent."""
    return any(hint in message for hint in _MISSING_DEPENDENCIES_HINTS)


def playwright_available() -> bool:
    """
    Return True when the playwright package can be imported.

    The check is cheap and never installs anything: use
    :func:`ensure_playwright_ready` when the components must be installed.

    Returns:
        bool: True when playwright is importable.

    Example:
        >>> playwright_available()
        True
    """
    try:
        import playwright  # noqa: F401  (optional dependency, checked lazily)
        return True
    except Exception as ex:  # ImportError or a broken installation
        logger.debug("playwright is not available: %s", ex)
        return False


def browsers_path() -> str:
    """
    Return the folder where playwright stores the downloaded browsers.

    Args:
        None.

    Returns:
        str: ``PLAYWRIGHT_BROWSERS_PATH`` when set, otherwise the default
        cache folder (``~/.cache/ms-playwright``).

    Example:
        >>> browsers_path().endswith("ms-playwright")
        True
    """
    custom = (os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "").strip()
    if custom and custom != "0":
        return custom
    return os.path.join(os.path.expanduser("~"), ".cache", "ms-playwright")


def chromium_installed() -> bool:
    """
    Return True when a Chromium build is present on disk.

    This is a fast filesystem check (no browser launch): a broken build is
    still detected on launch and repaired by the install-retry path.

    Returns:
        bool: True when a ``chromium*`` folder exists in the browsers path.

    Example:
        >>> chromium_installed()
        True
    """
    folders = [browsers_path()]
    try:
        import playwright

        # PLAYWRIGHT_BROWSERS_PATH=0 keeps the browsers inside the package
        folders.append(
            os.path.join(
                os.path.dirname(playwright.__file__),
                "driver", "package", ".local-browsers",
            )
        )
    except Exception:  # pragma: no cover - package missing
        pass

    for folder in folders:
        try:
            entries = os.listdir(folder)
        except OSError:
            continue
        if any(entry.startswith(CHROMIUM_BROWSER_TYPE) for entry in entries):
            return True
    return False


def _run_command(args: List[str], timeout: int) -> subprocess.CompletedProcess:
    """
    Run an installer command capturing its output.

    Args:
        args: Command and arguments to execute.
        timeout: Maximum run time in seconds.

    Returns:
        subprocess.CompletedProcess: Result with ``stdout``/``stderr`` captured.

    Raises:
        Exception: Propagated when the command cannot be started.
    """
    logger.info("Running: %s", " ".join(args))
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def install_playwright_package(force: bool = False) -> bool:
    """
    Install the ``playwright`` Python package when it is missing.

    Args:
        force: Retry even when a previous attempt already failed.

    Returns:
        bool: True when the package is importable afterwards.

    Example:
        >>> install_playwright_package()  # doctest: +SKIP
        True
    """
    global _package_install_attempted, _package_install_ok

    with _package_install_lock:
        if _package_install_ok:
            return True
        if _package_install_attempted and not force:
            return False
        _package_install_attempted = True

        try:
            result = _run_command(
                [sys.executable, "-m", "pip", "install", "--no-input", "playwright"],
                timeout=PLAYWRIGHT_INSTALL_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            logger.error(
                "pip install playwright timed out after %ss", PLAYWRIGHT_INSTALL_TIMEOUT_S
            )
            return False
        except Exception as ex:
            logger.error("pip install playwright could not run: %s", ex)
            return False

        if result.returncode != 0:
            logger.error(
                "pip install playwright failed (%s): %s",
                result.returncode, _tail(result.stderr or result.stdout),
            )
            return False

        # Make the freshly installed package importable without a restart
        importlib.invalidate_caches()
        _package_install_ok = playwright_available()
        if _package_install_ok:
            logger.info("playwright package installed")
        return _package_install_ok


def install_playwright_browser(
    browser_type: str = CHROMIUM_BROWSER_TYPE,
    with_deps: bool = False,
    force: bool = False,
) -> bool:
    """
    Download a playwright browser build (``playwright install <browser>``).

    Args:
        browser_type: Browser to download (``chromium`` for PDF printing).
        with_deps: Also install the OS dependencies (``--with-deps``).
        force: Retry even when a previous attempt already failed.

    Returns:
        bool: True when the installer finished successfully.

    Example:
        >>> install_playwright_browser("chromium")  # doctest: +SKIP
        True
    """
    global _browser_install_attempted, _browser_install_ok, _browser_install_error

    with _browser_install_lock:
        if _browser_install_ok:
            return True
        if _browser_install_attempted and not force:
            return False
        _browser_install_attempted = True
        _browser_install_error = None

        if not playwright_available():
            _browser_install_error = "the playwright package is not installed"
            logger.error("cannot download %s: %s", browser_type, _browser_install_error)
            return False

        args = [sys.executable, "-m", "playwright", "install"]
        if with_deps:
            args.append("--with-deps")
        args.append(browser_type)

        try:
            result = _run_command(args, timeout=PLAYWRIGHT_INSTALL_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            _browser_install_error = "the browser download timed out"
            logger.error(
                "'playwright install %s' timed out after %ss",
                browser_type, PLAYWRIGHT_INSTALL_TIMEOUT_S,
            )
            return False
        except Exception as ex:
            _browser_install_error = str(ex)
            logger.error("'playwright install %s' could not run: %s", browser_type, ex)
            return False

        if result.returncode != 0:
            _browser_install_error = _tail(result.stderr or result.stdout)
            logger.error(
                "'playwright install %s' failed (%s): %s",
                browser_type, result.returncode, _browser_install_error,
            )
            return False

        _browser_install_ok = True
        logger.info("playwright %s browser installed", browser_type)
        return True


def install_playwright_deps(browser_type: str = CHROMIUM_BROWSER_TYPE) -> bool:
    """
    Install the OS libraries required by the browser (``playwright install-deps``).

    Usually needs root; failures are logged and reported as a False result so the
    caller can surface an actionable message.

    Args:
        browser_type: Browser whose dependencies are installed.

    Returns:
        bool: True when the command finished successfully.

    Example:
        >>> install_playwright_deps("chromium")  # doctest: +SKIP
        True
    """
    args = [sys.executable, "-m", "playwright", "install-deps", browser_type]
    try:
        result = _run_command(args, timeout=PLAYWRIGHT_INSTALL_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        logger.error("'playwright install-deps %s' timed out", browser_type)
        return False
    except Exception as ex:
        logger.error("'playwright install-deps %s' could not run: %s", browser_type, ex)
        return False

    if result.returncode != 0:
        logger.error(
            "'playwright install-deps %s' failed (%s): %s",
            browser_type, result.returncode, _tail(result.stderr or result.stdout),
        )
        return False

    logger.info("playwright %s system dependencies installed", browser_type)
    return True


def ensure_playwright_ready(
    auto_install: Optional[bool] = None,
    force_install: bool = False,
) -> bool:
    """
    Make sure Playwright and a Chromium build are available for PDF printing.

    Steps, each skipped when already satisfied:

        1. import the ``playwright`` package (``pip install playwright``);
        2. verify a Chromium build is on disk (``playwright install chromium``);
        3. install the OS libraries (``playwright install-deps chromium``) when the
           download failed because of them.

    Installation happens at most once per process unless ``force_install`` is
    requested, and can be disabled with ``CODX_BROWSER_AUTO_INSTALL=0``.

    Args:
        auto_install: Explicit installation flag (None reads the environment).
        force_install: Retry the browser download even when it was attempted.

    Returns:
        bool: True when Playwright can print PDFs.

    Example:
        >>> ensure_playwright_ready()
        True
    """
    auto = _auto_install_enabled(auto_install)

    if not playwright_available():
        if not auto or not install_playwright_package():
            return False

    if chromium_installed() and not force_install:
        return True

    if not auto:
        return False

    if install_playwright_browser(force=force_install):
        return True

    # A failed download often means the OS libraries are missing
    if _is_missing_dependencies(_browser_install_error or ""):
        if install_playwright_deps():
            return install_playwright_browser(force=True)

    return False


async def ensure_playwright_ready_async(
    auto_install: Optional[bool] = None,
    force_install: bool = False,
) -> bool:
    """
    Asynchronous wrapper of :func:`ensure_playwright_ready`.

    The installers are blocking (network + disk), so they run in a worker thread
    and never stall the event loop that owns the Playwright session.

    Args:
        auto_install: Explicit installation flag (None reads the environment).
        force_install: Retry the browser download even when it was attempted.

    Returns:
        bool: True when Playwright can print PDFs.

    Example:
        >>> await ensure_playwright_ready_async()
        True
    """
    return await asyncio.to_thread(ensure_playwright_ready, auto_install, force_install)


def _browser_unavailable_error(message: str) -> BrowserUnavailableError:
    """
    Build an actionable error from a raw Chromium launch/install failure.

    Args:
        message: Error reported by playwright.

    Returns:
        BrowserUnavailableError: Error with the appropriate fix instructions.

    Example:
        >>> str(_browser_unavailable_error("Executable doesn't exist"))
        'the headless browser is not available (...) ...'
    """
    if _is_missing_dependencies(message):
        return BrowserUnavailableError(
            "the headless browser is missing system dependencies ("
            + message
            + "); install them with 'playwright install-deps chromium'"
        )
    if _is_browser_missing(message):
        return BrowserUnavailableError(
            "the headless browser is not available ("
            + message
            + ") and could not be installed automatically; "
            + PLAYWRIGHT_INSTALL_HINT
        )
    return BrowserUnavailableError(
        "the headless browser could not be started (" + message + ")"
    )


def run_coroutine_sync(coro_factory: Callable[[], Any]) -> Any:
    """
    Run a coroutine factory to completion from synchronous code.

    Playwright's async API must own its event loop. When this is called from a
    context that already has a running loop (the agent executes synchronous
    tools inline) the coroutine runs in a dedicated thread with a fresh loop.

    Args:
        coro_factory: Callable returning a **new** coroutine (it is invoked
            inside the destination loop, so pass a factory, not a coroutine).

    Returns:
        Any: The coroutine's return value.

    Example:
        >>> run_coroutine_sync(lambda: render_page("file:///tmp/a.html"))
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No loop running: safe to own the thread's loop
        return asyncio.run(coro_factory())

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coro_factory())).result()


def normalize_script(script: Optional[str]) -> Optional[str]:
    """
    Normalize a user script into something playwright's ``page.evaluate`` accepts.

    Playwright evaluates strings as an expression (or as a function when the
    string starts with ``function``/``(``). Statements are wrapped into an arrow
    function so both the ``return ...`` and the expression styles work.

    Args:
        script: JavaScript provided by the caller.

    Returns:
        Optional[str]: The expression/function to evaluate, or None when empty.

    Example:
        >>> normalize_script("return document.title")
        '() => { return document.title }'
        >>> normalize_script("() => Reveal.slide(0)")
        '() => Reveal.slide(0)'
    """
    stripped = (script or "").strip()
    if not stripped:
        return None
    if stripped.startswith("return "):
        return f"() => {{ {stripped} }}"
    # Arrow functions and function declarations are passed through untouched
    if stripped.startswith(("(", "function", "async", "()")):
        return stripped
    if "\n" in stripped or ";" in stripped:
        return f"() => {{ {stripped} }}"
    return stripped


def page_break_css(selector: str) -> str:
    """
    Build the print stylesheet that starts a new page per matched element.

    Each selector is handled separately so comma separated selector lists keep
    working, and the last match never emits a trailing blank page.

    Args:
        selector: CSS selector whose matches each start a new PDF page.

    Returns:
        str: CSS to inject into the page ("" when the selector is empty).

    Example:
        >>> page_break_css("section")
        '@media print {\\n  section { break-after: page; ... }\\n}'
    """
    parts = [part.strip() for part in (selector or "").split(",") if part.strip()]
    if not parts:
        return ""

    rules = [
        f"  {part} {{ break-after: page; page-break-after: always; }}"
        for part in parts
    ]
    rules += [
        f"  {part}:last-of-type {{ break-after: auto; page-break-after: auto; }}"
        for part in parts
    ]
    return "@media print {\n" + "\n".join(rules) + "\n}\n"


def parse_page_size(page_size: Optional[str]) -> Dict[str, str]:
    """
    Convert a page size argument into playwright ``page.pdf`` options.

    Args:
        page_size: Paper format ('A4', 'Letter', ...) or explicit dimensions
            ('1920x1080', '13.33in x 7.5in').

    Returns:
        Dict[str, str]: Empty dict for the browser default, otherwise
        ``format`` or ``width``/``height``.

    Raises:
        ValueError: When the size cannot be parsed.

    Example:
        >>> parse_page_size("1920x1080")
        {'width': '1920px', 'height': '1080px'}
        >>> parse_page_size("A4")
        {'format': 'A4'}
    """
    size = (page_size or "").strip()
    if not size:
        return {}

    for page_format in PDF_PAGE_FORMATS:
        if size.lower() == page_format.lower():
            return {"format": page_format}

    lowered = size.lower()
    if "x" in lowered:
        width, _, height = lowered.partition("x")
        width, height = width.strip(), height.strip()
        if width and height:
            # Bare numbers are CSS pixels, units are kept as provided
            if width.replace(".", "", 1).isdigit() and height.replace(".", "", 1).isdigit():
                return {"width": f"{width}px", "height": f"{height}px"}
            return {"width": width, "height": height}

    raise ValueError(
        f"page_size '{page_size}' is not supported. Use a paper format "
        f"({', '.join(PDF_PAGE_FORMATS)}) or dimensions like '1920x1080' "
        "or '13.33in x 7.5in'"
    )


def parse_margin(margin: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Convert a margin argument into playwright ``page.pdf`` margin options.

    Args:
        margin: Single CSS length applied to every side, or four comma
            separated values (top,right,bottom,left).

    Returns:
        Optional[Dict[str, str]]: Margins per side, or None when not requested.

    Raises:
        ValueError: When the number of values is not 1 or 4.

    Example:
        >>> parse_margin("1cm")
        {'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'}
    """
    value = (margin or "").strip()
    if not value:
        return None

    parts = [part.strip() for part in value.split(",") if part.strip()]
    sides = ("top", "right", "bottom", "left")
    if len(parts) == 1:
        return {side: parts[0] for side in sides}
    if len(parts) == 4:
        return dict(zip(sides, parts))

    raise ValueError(
        "margin must be a single CSS length ('0', '1cm') or four comma separated "
        "values: top,right,bottom,left"
    )


def pdf_options(
    page_size: Optional[str] = None,
    landscape: Optional[bool] = None,
    print_background: Optional[bool] = None,
    margin: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build the playwright ``page.pdf`` options for the requested page layout.

    Args:
        page_size: Paper format or explicit dimensions.
        landscape: Print landscape (None keeps the browser default).
        print_background: Print CSS backgrounds (default True: rich documents
            and slides need it).
        margin: Page margins.

    Returns:
        Dict[str, Any]: Keyword arguments accepted by ``page.pdf``.

    Example:
        >>> pdf_options(page_size="1920x1080", landscape=True)
        {'print_background': True, 'landscape': True, 'width': '1920px', 'height': '1080px'}
    """
    options: Dict[str, Any] = {
        # Backgrounds carry most of the visual information of a rich document
        "print_background": True if print_background is None else bool(print_background),
    }
    if landscape is not None:
        options["landscape"] = bool(landscape)

    options.update(parse_page_size(page_size))

    margins = parse_margin(margin)
    if margins:
        options["margin"] = margins

    return options


def to_browser_target(target: str) -> str:
    """
    Resolve what playwright must open: URLs are kept, paths become file URIs.

    Args:
        target: ``http(s)://``, ``file://`` or a local file path.

    Returns:
        str: A URL playwright can navigate to.

    Raises:
        ValueError: When the target is empty.

    Example:
        >>> to_browser_target("/project/slides/deck.html")
        'file:///project/slides/deck.html'
    """
    if not target:
        raise ValueError("a page URL or file path is required")

    lowered = target.lower()
    if lowered.startswith(("http://", "https://", "file://", "data:", "about:")):
        return target
    return Path(target).resolve().as_uri()


class Browser:
    """
    High-level browser automation interface using Playwright.

    Manages Playwright context lifecycle and provides methods for page
    interaction (navigate, execute JS, take screenshots, etc.).

    ``connect()`` attaches to the *existing* page of the shared browser when one
    is available, so consecutive tool calls act on the same page the user is
    watching and controlling through the live VNC view.
    """

    def __init__(self, session: BrowserSession, docker_manager: DockerBrowserManager):
        """
        Initialize Browser.

        Args:
            session: BrowserSession with container info
            docker_manager: DockerBrowserManager instance
        """
        self.session = session
        self.docker_manager = docker_manager
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def connect(self) -> None:
        """
        Connect to the remote Chromium via the DevTools Protocol.

        The session's ``debug_url`` is a WebSocket URL served by the in-container
        CDP proxy (see ``DockerBrowserManager``).  Existing contexts/pages are
        reused so the shared browser state (current URL, DOM, logged-in
        sessions) is preserved across tool calls.

        Raises:
            RuntimeError: If connection fails.
        """
        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()

            debug_url = self.session.debug_url
            if not debug_url:
                raise RuntimeError("session has no debug_url (container is not running)")

            logger.info("Connecting to browser at: %s", debug_url)
            self.browser = await self.playwright.chromium.connect_over_cdp(debug_url)

            # Reuse an existing context/page when available (shared browser)
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
            else:
                self.context = await self.browser.new_context()

            pages = self.context.pages
            self.page = await self._select_active_page(pages)
            if not self.page:
                self.page = await self.context.new_page()

            # Co-browsing: the human may be looking at a tab that is not the
            # last one; prefer the session's remembered URL before guessing.
            await self.install_recorder()

            # Restore the requested start URL if Chromium opened an empty tab
            # (e.g. the initial target was still loading when the probe passed).
            if (
                (not self.page.url or self.page.url == "about:blank")
                and self.session.current_url
                and self.session.current_url not in ("about:blank", "chrome://newtab/")
            ):
                try:
                    await self.page.goto(
                        self.session.current_url,
                        wait_until=BROWSER_WAIT_UNTIL_FALLBACK,
                        timeout=BROWSER_TIMEOUT_MS,
                    )
                except Exception as ex:
                    logger.warning("Could not restore start URL %s: %s", self.session.current_url, ex)

            await self._sync_location()
            logger.info(
                "Browser connected: session %s (%s)",
                _short_id(self.session.id),
                self.session.current_url or "about:blank",
            )
            self.session.mark_active()

        except Exception as e:
            logger.exception("Failed to connect to browser")
            self.session.status = "error"
            self.session.error = str(e)
            raise RuntimeError(f"Browser connection failed: {e}")

    async def _select_active_page(self, pages):
        """
        Choose the page the user is actually looking at.

        A browser may keep background tabs (and Chromium sometimes opens an
        extra tab at startup).  Picking the last page blindly can make the AI
        drive a different tab than the live VNC view, so prefer the page whose
        document is visible/focused, then fall back to the last non-blank page.
        """
        if not pages:
            return None

        visible = []
        focused = []
        for page in pages:
            try:
                if await page.evaluate("document.visibilityState === 'visible'"):
                    visible.append(page)
                    if await page.evaluate("document.hasFocus()"):
                        focused.append(page)
            except Exception:
                continue

        if focused:
            return focused[-1]
        if visible:
            return visible[-1]

        # Reconnect after the driver was idle: the session remembers the page
        # the AI/user were on, so prefer it over an arbitrary last tab.
        remembered = (self.session.current_url or "").strip()
        if remembered:
            for page in reversed(pages):
                try:
                    if (page.url or "").strip() == remembered:
                        return page
                except Exception:
                    continue

        candidates = [
            page for page in pages
            if page.url and page.url not in ("about:blank", "chrome://newtab/")
        ]
        return candidates[-1] if candidates else pages[-1]

    async def _sync_location(self) -> None:
        """Refresh the session's cached URL/title from the live page."""
        if not self.page:
            return
        try:
            self.session.current_url = self.page.url or self.session.current_url
        except Exception:
            pass
        try:
            self.session.current_title = await self.page.title()
        except Exception:
            pass

    async def install_recorder(self) -> None:
        """Inject the co-browsing recorder into the current and future documents.

        The recorder captures clicks, edits, submits and scrolls performed by
        the human in the live VNC view.  It is idempotent (the page guard keeps a
        single instance) and must be re-applied to the current document because
        ``add_init_script`` only covers documents created afterwards.
        """
        if not self.context or not self.page:
            return
        try:
            await self.context.add_init_script(script=RECORDER_SCRIPT)
        except Exception as ex:
            logger.debug("Could not register the co-browsing recorder: %s", ex)
        try:
            await self.page.evaluate(RECORDER_SCRIPT)
        except Exception as ex:
            logger.debug("Could not install the co-browsing recorder in the page: %s", ex)

    async def install_recorder_on(self, page) -> None:
        """Install the recorder in one page (tabs opened before the injection)."""
        if page is None:
            return
        try:
            await page.evaluate(RECORDER_SCRIPT)
        except Exception as ex:
            logger.debug("Could not install the recorder in a tab: %s", ex)

    async def set_actor(self, actor: str) -> None:
        """Tag the next DOM events as ``ai`` or ``user`` (recorder attribution)."""
        if not self.page:
            return
        try:
            await self.page.evaluate(
                "(value) => { if (window.__codxRec) window.__codxRec.setActor(value); }",
                "ai" if actor == "ai" else "user",
            )
        except Exception:
            pass

    async def drain_events(self, page=None) -> Dict[str, Any]:
        """Drain the in-page recorder buffer (user events + current location)."""
        target = page or self.page
        if not target:
            return {}
        try:
            return await target.evaluate(
                "() => (window.__codxRec ? window.__codxRec.drain() : "
                "{events: [], url: location.href, title: document.title})"
            )
        except Exception as ex:
            logger.debug("Could not drain browser events: %s", ex)
            return {}

    async def get_snapshot(self) -> Dict[str, Any]:
        """Return a compact, model-friendly view of the current page.

        Unlike :meth:`get_content`, this stays small (interactive refs + main
        text + headings).  It also tags every interactive element with
        ``data-codx-ref`` so :meth:`click_ref` / :meth:`fill_ref` are stable.
        """
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            snapshot = await self.page.evaluate(SNAPSHOT_SCRIPT)
            await self._sync_location()
            self.session.mark_active()
            return snapshot or {}
        except Exception as e:
            raise RuntimeError(f"Snapshot failed: {e}")

    async def click_ref(self, ref: str) -> None:
        """Click an element previously tagged by :meth:`get_snapshot`."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        selector = f'[data-codx-ref="{str(ref).replace(chr(34), "")}"]'
        try:
            await self.highlight(selector)
            await self.page.click(selector, timeout=BROWSER_TIMEOUT_MS)
            await self._sync_location()
            self.session.mark_active()
        except Exception as e:
            raise RuntimeError(f"Click on ref {ref} failed: {e}")

    async def fill_ref(self, ref: str, text: str) -> None:
        """Fill an element previously tagged by :meth:`get_snapshot`."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        selector = f'[data-codx-ref="{str(ref).replace(chr(34), "")}"]'
        try:
            await self.page.fill(selector, text, timeout=BROWSER_TIMEOUT_MS)
            await self._sync_location()
            self.session.mark_active()
        except Exception as e:
            raise RuntimeError(f"Fill on ref {ref} failed: {e}")

    async def click_text(self, text: str) -> None:
        """Click the first element whose visible text matches *text*."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.get_by_text(str(text), exact=False).first.click(timeout=BROWSER_TIMEOUT_MS)
            await self._sync_location()
            self.session.mark_active()
        except Exception as e:
            raise RuntimeError(f"Click on text {text!r} failed: {e}")

    async def click_role(self, role: str, name: str) -> None:
        """Click an element by ARIA role and accessible name."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.get_by_role(role, name=name, exact=False).first.click(timeout=BROWSER_TIMEOUT_MS)
            await self._sync_location()
            self.session.mark_active()
        except Exception as e:
            raise RuntimeError(f"Click on role={role!r} name={name!r} failed: {e}")

    async def fill_label(self, label: str, text: str) -> None:
        """Fill an input by its associated label."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.get_by_label(str(label), exact=False).first.fill(text, timeout=BROWSER_TIMEOUT_MS)
            await self._sync_location()
            self.session.mark_active()
        except Exception as e:
            raise RuntimeError(f"Fill on label {label!r} failed: {e}")

    async def wait_for_url(self, url: str, timeout: int = 10000) -> None:
        """Wait until the page URL matches *url* (substring/glob accepted)."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.wait_for_url(f"**{url}**", timeout=timeout)
            await self._sync_location()
        except Exception as e:
            raise RuntimeError(f"Timeout waiting for URL {url!r}: {e}")

    async def wait_for_text(self, text: str, timeout: int = 10000) -> None:
        """Wait until *text* is visible on the page."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.get_by_text(str(text), exact=False).first.wait_for(
                state="visible", timeout=timeout
            )
            await self._sync_location()
        except Exception as e:
            raise RuntimeError(f"Timeout waiting for text {text!r}: {e}")

    def is_alive(self) -> bool:
        """True when the Playwright connection still has a usable page."""
        try:
            if not self.browser or not self.page:
                return False
            if not self.browser.is_connected():
                return False
            return not self.page.is_closed()
        except Exception:
            return False

    async def navigate(self, url: str) -> str:
        """
        Navigate to a URL and return the page title.

        ``networkidle`` is tried first (good for static apps) but many live
        applications keep websockets/polling open, so the wait strategy falls
        back to ``load`` instead of failing the whole navigation.
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            logger.info("Navigating to: %s", url)
            await self.page.goto(url, wait_until=BROWSER_WAIT_UNTIL, timeout=BROWSER_TIMEOUT_MS)
            # Many apps never reach ``networkidle``; wait for ``load`` briefly
            # and let the caller decide whether it needs an explicit selector.
            try:
                await self.page.wait_for_load_state(
                    BROWSER_WAIT_UNTIL_FALLBACK, timeout=BROWSER_LOAD_WAIT_MS
                )
            except Exception as ex:
                logger.debug("Page %s did not reach '%s' in %sms: %s", url,
                             BROWSER_WAIT_UNTIL_FALLBACK, BROWSER_LOAD_WAIT_MS, ex)
            await self._sync_location()
            self.session.mark_active()
            return self.session.current_title or ""
        except Exception as e:
            logger.exception("Navigation failed")
            raise RuntimeError(f"Navigation to {url} failed: {e}")

    async def execute_script(self, script: str) -> any:
        """
        Execute JavaScript in the page context.

        Args:
            script: JavaScript code to execute (use ``return ...`` to return a value)

        Returns:
            Result of script execution

        Raises:
            RuntimeError: If page not connected
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        expression = normalize_script(script)
        if not expression:
            return None

        try:
            result = await self.page.evaluate(expression)
            await self._sync_location()
            self.session.mark_active()
            return result
        except Exception as e:
            logger.exception("Script execution failed")
            raise RuntimeError(f"Script execution failed: {e}")

    async def get_screenshot(self, full_page: bool = True) -> str:
        """
        Take a screenshot of the current page.

        Args:
            full_page: Capture the whole scrollable page (default) or only the
                visible viewport.

        Returns:
            Base64-encoded PNG image (data: URI)

        Raises:
            RuntimeError: If page not connected
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            screenshot_bytes = await self.page.screenshot(full_page=bool(full_page))
            b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            self.session.mark_active()
            return f"data:image/png;base64,{b64}"
        except Exception as e:
            logger.exception("Screenshot failed")
            raise RuntimeError(f"Screenshot failed: {e}")

    async def get_content(self) -> str:
        """
        Get the current page HTML content.

        Returns:
            HTML string

        Raises:
            RuntimeError: If page not connected
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            content = await self.page.content()
            await self._sync_location()
            self.session.mark_active()
            return content
        except Exception as e:
            logger.exception("get_content failed")
            raise RuntimeError(f"get_content failed: {e}")

    async def get_text(self) -> str:
        """
        Get the visible text of the current page (``document.body.innerText``).

        Returns:
            Visible text

        Raises:
            RuntimeError: If page not connected
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            text = await self.page.evaluate(
                normalize_script("return document.body ? document.body.innerText : ''")
            )
            await self._sync_location()
            self.session.mark_active()
            return text
        except Exception as e:
            logger.exception("get_text failed")
            raise RuntimeError(f"get_text failed: {e}")

    async def get_links(self) -> List[Dict[str, str]]:
        """
        Return the links visible on the current page.

        Useful for agents that need to discover resources/navigation targets
        without downloading the full HTML.

        Returns:
            List of dictionaries with ``text``, ``href`` and ``title`` keys.
        """
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            links = await self.page.evaluate(
                normalize_script(
                    """
                    return Array.from(document.querySelectorAll('a[href]'))
                      .slice(0, 500)
                      .map(a => ({
                        text: (a.innerText || a.textContent || '').trim().slice(0, 200),
                        href: a.href,
                        title: (a.getAttribute('title') || '').slice(0, 200)
                      }));
                    """
                )
            )
            await self._sync_location()
            self.session.mark_active()
            return links or []
        except Exception as e:
            logger.exception("get_links failed")
            raise RuntimeError(f"get_links failed: {e}")

    async def highlight(self, selector: str, label: str = "AI") -> None:
        """Draw a short-lived highlight over an element before the AI acts.

        The human watches the same VNC page; a visible outline makes it obvious
        where a click is about to land (and debug a wrong selector).  Best
        effort: a page that blocks DOM changes must never break the action.
        """
        if not self.page:
            return
        try:
            await self.page.evaluate(
                """(args) => {
                    const el = document.querySelector(args.selector);
                    if (!el) return false;
                    const rect = el.getBoundingClientRect();
                    const old = document.getElementById('__codx_ai_highlight');
                    if (old) old.remove();
                    const box = document.createElement('div');
                    box.id = '__codx_ai_highlight';
                    Object.assign(box.style, {
                        position: 'fixed',
                        left: rect.left + 'px',
                        top: rect.top + 'px',
                        width: rect.width + 'px',
                        height: rect.height + 'px',
                        border: '2px solid #f59e0b',
                        boxShadow: '0 0 0 3px rgba(245,158,11,.30)',
                        borderRadius: '4px',
                        pointerEvents: 'none',
                        zIndex: '2147483647',
                        transition: 'opacity .2s ease'
                    });
                    const tag = document.createElement('div');
                    tag.textContent = args.label;
                    Object.assign(tag.style, {
                        position: 'absolute', left: '0', top: '-18px',
                        background: '#f59e0b', color: '#111', font: '600 11px system-ui',
                        padding: '1px 5px', borderRadius: '3px'
                    });
                    box.appendChild(tag);
                    document.body.appendChild(box);
                    setTimeout(() => {
                        box.style.opacity = '0';
                        setTimeout(() => box.remove(), 250);
                    }, 900);
                    return true;
                }""",
                {"selector": selector, "label": label},
            )
        except Exception as ex:
            logger.debug("Could not highlight %s: %s", selector, ex)

    async def click(self, selector: str) -> None:
        """
        Click an element.

        Args:
            selector: CSS selector

        Raises:
            RuntimeError: If page not connected or element not found
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            await self.highlight(selector)
            await self.page.click(selector)
            await self._sync_location()
            self.session.mark_active()
            logger.debug("Clicked: %s", selector)
        except Exception as e:
            logger.exception("Click failed for selector: %s", selector)
            raise RuntimeError(f"Click on {selector} failed: {e}")

    async def fill(self, selector: str, text: str) -> None:
        """
        Fill a text input.

        Args:
            selector: CSS selector
            text: Text to fill

        Raises:
            RuntimeError: If page not connected or element not found
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            await self.page.fill(selector, text)
            await self._sync_location()
            self.session.mark_active()
            logger.debug("Filled %s with text", selector)
        except Exception as e:
            logger.exception("Fill failed for selector: %s", selector)
            raise RuntimeError(f"Fill on {selector} failed: {e}")

    async def press(self, selector: str, key: str) -> None:
        """Press a keyboard key on an element (``Enter``, ``Tab``, ...)."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.press(selector, key)
            await self._sync_location()
            self.session.mark_active()
        except Exception as e:
            raise RuntimeError(f"Press {key} on {selector} failed: {e}")

    async def select(self, selector: str, value: str) -> None:
        """Select an option in a ``<select>`` element."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.select_option(selector, value)
            await self._sync_location()
            self.session.mark_active()
        except Exception as e:
            raise RuntimeError(f"Select {value} on {selector} failed: {e}")

    async def hover(self, selector: str) -> None:
        """Hover an element."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.hover(selector)
            self.session.mark_active()
        except Exception as e:
            raise RuntimeError(f"Hover on {selector} failed: {e}")

    async def scroll(self, x: int = 0, y: int = 0) -> None:
        """Scroll the page by the given pixel offsets."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.evaluate(
                normalize_script(f"window.scrollBy({int(x)}, {int(y)})")
            )
            self.session.mark_active()
        except Exception as e:
            raise RuntimeError(f"Scroll failed: {e}")

    async def wait_for_selector(self, selector: str, timeout: int = 5000) -> None:
        """
        Wait for element to appear.

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds

        Raises:
            RuntimeError: If element doesn't appear
        """
        if not self.page:
            raise RuntimeError("Browser not connected")

        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self._sync_location()
        except Exception as e:
            logger.exception("Wait for selector failed: %s", selector)
            raise RuntimeError(f"Timeout waiting for {selector}: {e}")

    async def go_back(self) -> str:
        """Go back in history and return the resulting title."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.go_back(wait_until=BROWSER_WAIT_UNTIL_FALLBACK, timeout=BROWSER_TIMEOUT_MS)
            await self._sync_location()
            self.session.mark_active()
            return self.session.current_title or ""
        except Exception as e:
            raise RuntimeError(f"Back navigation failed: {e}")

    async def go_forward(self) -> str:
        """Go forward in history and return the resulting title."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.go_forward(wait_until=BROWSER_WAIT_UNTIL_FALLBACK, timeout=BROWSER_TIMEOUT_MS)
            await self._sync_location()
            self.session.mark_active()
            return self.session.current_title or ""
        except Exception as e:
            raise RuntimeError(f"Forward navigation failed: {e}")

    async def reload(self) -> str:
        """Reload the current page and return the resulting title."""
        if not self.page:
            raise RuntimeError("Browser not connected")
        try:
            await self.page.reload(wait_until=BROWSER_WAIT_UNTIL_FALLBACK, timeout=BROWSER_TIMEOUT_MS)
            await self._sync_location()
            self.session.mark_active()
            return self.session.current_title or ""
        except Exception as e:
            raise RuntimeError(f"Reload failed: {e}")

    async def close(self) -> None:
        """
        Detach from the remote browser (the container keeps running).

        Closes only the Playwright connection — the shared Chromium page/state
        survives so it can be reused by the next call and remains visible in
        the user's live VNC view.
        """
        try:
            if self.context and self.browser and self.browser.contexts:
                # Do NOT close the shared context; only stop the local driver.
                pass
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser disconnected: session %s", _short_id(self.session.id))
        except Exception as e:
            logger.exception("Error closing browser: %s", e)

    def __repr__(self) -> str:
        return f"Browser(session={_short_id(self.session.id)}, connected={self.page is not None})"


class PdfPrinter:
    """
    Prints a rendered page to PDF with a local headless Chromium.

    Unlike :class:`Browser`, which drives the shared Chromium container, this
    launches its own headless Chromium so printing is isolated from the user
    session and works without Docker. JavaScript, modern CSS (flexbox/grid),
    custom fonts and background images are printed as a browser shows them,
    keeping text and links as vectors (no screenshots).

    The browser is installed automatically when missing (see
    :func:`ensure_playwright_ready`): the ``playwright`` package, the Chromium
    build and, when required, the system libraries.

    Args:
        pdf_options: Keyword arguments for ``page.pdf`` (see :func:`pdf_options`).
        media: CSS media to emulate before printing ('screen' or 'print').
        wait_for_selector: Selector to wait for before printing.
        wait_timeout_ms: Extra delay in milliseconds before printing, so
            animations and async rendering settle.
        script: JavaScript executed right before printing.
        page_break_selector: Selector whose matches each start a new page.
        prefer_css_page_size: Use the page ``@page`` CSS size when present.
        auto_install: Install the missing Playwright components (None reads
            ``CODX_BROWSER_AUTO_INSTALL``, enabled by default).

    Example:
        >>> printer = PdfPrinter(pdf_options=pdf_options(page_size="1920x1080"),
        ...                      media="screen",
        ...                      page_break_selector=".reveal .slides > section")
        >>> printer.print_target("slides/deck.html", "/project/slides/deck.pdf")
        'playwright-chromium'
    """

    def __init__(
        self,
        pdf_options: Optional[Dict[str, Any]] = None,
        media: Optional[str] = None,
        wait_for_selector: Optional[str] = None,
        wait_timeout_ms: int = 0,
        script: Optional[str] = None,
        page_break_selector: Optional[str] = None,
        prefer_css_page_size: bool = False,
        auto_install: Optional[bool] = None,
    ):
        normalized_media = (media or "").strip().lower() or None
        if normalized_media and normalized_media not in BROWSER_MEDIA_TYPES:
            raise ValueError(
                f"media '{media}' is not supported. "
                f"Use one of: {', '.join(BROWSER_MEDIA_TYPES)}"
            )

        self.pdf_options = dict(pdf_options or {})
        self.media = normalized_media
        self.wait_for_selector = wait_for_selector
        self.wait_timeout_ms = int(wait_timeout_ms or 0)
        self.script = normalize_script(script)
        self.page_break_selector = page_break_selector
        self.prefer_css_page_size = bool(prefer_css_page_size)
        self.auto_install = auto_install

    async def _navigate(self, page, url: str) -> None:
        """
        Open the page waiting for network idle, retrying with ``load``.

        Slide decks frequently poll or keep a websocket open, so ``networkidle``
        may never be reached; the retry keeps printing possible in that case.
        """
        try:
            await page.goto(url, wait_until=BROWSER_WAIT_UNTIL, timeout=BROWSER_TIMEOUT_MS)
        except Exception as ex:
            logger.warning(
                "networkidle wait failed (%s); retrying with '%s'",
                ex, BROWSER_WAIT_UNTIL_FALLBACK,
            )
            await page.goto(
                url, wait_until=BROWSER_WAIT_UNTIL_FALLBACK, timeout=BROWSER_TIMEOUT_MS
            )

    async def _launch(self, playwright):
        """
        Launch headless Chromium, installing the browser when it is missing.

        The launch is retried once after a successful installation, and once more
        after installing the system libraries when that was the cause.

        Args:
            playwright: Started playwright instance.

        Returns:
            The launched browser.

        Raises:
            BrowserUnavailableError: When the browser cannot be launched.
        """
        launch_args = list(CHROMIUM_LAUNCH_ARGS)

        try:
            return await playwright.chromium.launch(headless=True, args=launch_args)
        except Exception as ex:
            first_error = str(ex)

        if self.auto_install is False or not _is_browser_missing(first_error):
            raise _browser_unavailable_error(first_error)

        logger.warning("Chromium could not start (%s); installing it", first_error)
        if not await ensure_playwright_ready_async(auto_install=True, force_install=True):
            raise _browser_unavailable_error(first_error)

        try:
            return await playwright.chromium.launch(headless=True, args=launch_args)
        except Exception as ex:
            retry_error = str(ex)

        # A broken download usually means the OS libraries are missing
        if _is_missing_dependencies(retry_error):
            logger.warning("Chromium still failing (%s); installing system deps", retry_error)
            if await asyncio.to_thread(install_playwright_deps, CHROMIUM_BROWSER_TYPE):
                try:
                    return await playwright.chromium.launch(headless=True, args=launch_args)
                except Exception as ex:
                    retry_error = str(ex)

        raise _browser_unavailable_error(retry_error)

    async def print_async(self, target: str, output_file: str) -> str:
        """
        Render a URL or a local file and print it to ``output_file``.

        Args:
            target: URL (``http(s)://``/``file://``) or local file path.
            output_file: Absolute path of the PDF to write.

        Returns:
            str: Renderer label (:data:`BROWSER_ENGINE_LABEL`).

        Raises:
            BrowserUnavailableError: When Chromium cannot be used, even after
                installing the missing Playwright components.
        """
        # Install the missing components before importing playwright
        if self.auto_install is not False:
            await ensure_playwright_ready_async(self.auto_install)

        from playwright.async_api import async_playwright

        url = to_browser_target(target)

        async with async_playwright() as playwright:
            browser = await self._launch(playwright)
            try:
                page = await browser.new_page()
                if self.media:
                    await page.emulate_media(media=self.media)

                await self._navigate(page, url)

                if self.wait_for_selector:
                    await page.wait_for_selector(
                        self.wait_for_selector, timeout=BROWSER_TIMEOUT_MS
                    )

                if self.script:
                    await page.evaluate(self.script)

                if self.wait_timeout_ms:
                    await page.wait_for_timeout(self.wait_timeout_ms)

                if self.page_break_selector:
                    await page.add_style_tag(
                        content=page_break_css(self.page_break_selector)
                    )

                await page.pdf(
                    path=output_file,
                    prefer_css_page_size=self.prefer_css_page_size,
                    **self.pdf_options,
                )
            finally:
                await browser.close()

        logger.info("PDF printed with %s: %s", BROWSER_ENGINE_LABEL, output_file)
        return BROWSER_ENGINE_LABEL

    def print_target(self, target: str, output_file: str) -> str:
        """
        Synchronous, event-loop safe wrapper around :meth:`print_async`.

        Args:
            target: URL or local file path to render.
            output_file: Absolute path of the PDF to write.

        Returns:
            str: Renderer label (:data:`BROWSER_ENGINE_LABEL`).

        Raises:
            BrowserUnavailableError: When playwright or Chromium is missing and
                cannot be installed.
        """
        try:
            return run_coroutine_sync(lambda: self.print_async(target, output_file))
        except BrowserUnavailableError:
            raise
        except ImportError as ex:
            raise BrowserUnavailableError(
                "the playwright package is not installed and could not be installed "
                "automatically; " + PLAYWRIGHT_INSTALL_HINT
            ) from ex
        except Exception as ex:
            message = str(ex)
            if _is_browser_missing(message):
                raise _browser_unavailable_error(message) from ex
            raise


def print_pdf(
    target: str,
    output_file: str,
    slides: bool = False,
    page_size: Optional[str] = None,
    landscape: Optional[bool] = None,
    print_background: Optional[bool] = None,
    margin: Optional[str] = None,
    media: Optional[str] = None,
    wait_for_selector: Optional[str] = None,
    wait_timeout_ms: int = 0,
    script: Optional[str] = None,
    page_break_selector: Optional[str] = None,
    prefer_css_page_size: Optional[bool] = None,
    auto_install: Optional[bool] = None,
) -> str:
    """
    Print a page (URL or local file) to PDF with a local headless Chromium.

    This is the single printing entry point of the application: every Playwright
    detail (installation, launch, media emulation, page breaks, ``page.pdf``)
    stays inside this module.

    Args:
        target: URL (``http(s)://``/``file://``) or local file path to render.
        output_file: Absolute path of the PDF to write.
        slides: Apply the slide deck preset: 1920x1080 landscape pages, screen
            media, background graphics, zero margins and CSS page size. Every
            explicit option below overrides the preset.
        page_size: Paper format ('A4', 'Letter') or '1920x1080' / '13.33in x 7.5in'.
        landscape: Print landscape (defaults to True with ``slides``).
        print_background: Print CSS backgrounds (default True).
        margin: Page margin, one CSS length or four comma separated values.
        media: CSS media emulated before printing ('screen' or 'print').
        wait_for_selector: Selector to wait for before printing.
        wait_timeout_ms: Extra delay in milliseconds before printing.
        script: JavaScript executed right before printing.
        page_break_selector: Selector whose matches each start a new page.
        prefer_css_page_size: Use the page ``@page`` CSS size when present
            (defaults to True with ``slides``).
        auto_install: Install the missing Playwright components (None reads
            ``CODX_BROWSER_AUTO_INSTALL``, enabled by default).

    Returns:
        str: Renderer label (:data:`BROWSER_ENGINE_LABEL`).

    Raises:
        BrowserUnavailableError: When playwright or Chromium is missing and
            cannot be installed.
        ValueError: When a page size, margin or media value is invalid.

    Example:
        >>> print_pdf("slides/deck.html", "/project/slides/deck.pdf", slides=True,
        ...           page_break_selector=".reveal .slides > section")
        'playwright-chromium'
    """
    if slides:
        page_size = page_size or SLIDE_PAGE_SIZE
        landscape = True if landscape is None else landscape
        print_background = True if print_background is None else print_background
        margin = "0" if margin is None else margin
        media = media or "screen"
        prefer_css_page_size = True if prefer_css_page_size is None else prefer_css_page_size

    printer = PdfPrinter(
        pdf_options=pdf_options(
            page_size=page_size,
            landscape=landscape,
            print_background=print_background,
            margin=margin,
        ),
        media=media,
        wait_for_selector=wait_for_selector,
        wait_timeout_ms=wait_timeout_ms,
        script=script,
        page_break_selector=page_break_selector,
        prefer_css_page_size=bool(prefer_css_page_size),
        auto_install=auto_install,
    )
    return printer.print_target(target=target, output_file=output_file)

# Made with ❤️ by codx-junior