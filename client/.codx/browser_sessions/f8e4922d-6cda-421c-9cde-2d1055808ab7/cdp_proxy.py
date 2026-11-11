"""
Small TCP proxy used to expose Chromium's DevTools endpoint to the Docker network.

Chromium only binds its DevTools HTTP/WebSocket server to ``127.0.0.1`` and it
also validates the ``Host`` header (non-loopback hosts are rejected).  Since the
codx-junior API runs in a *different* container, neither the endpoint nor the
WebSocket handshake is reachable directly.

This script runs inside the browser container and:

    API container ─► 0.0.0.0:9223 (proxy) ─► 127.0.0.1:9222 (DevTools)

The first HTTP request of every downstream connection has its ``Host`` header
rewritten to a loopback value (required by Chromium), then the connection is
tunnelled byte-for-byte so WebSocket frames and Chrome DevTools Protocol
messages pass through untouched.

Only the Python standard library is used, so it runs on the upstream
LinuxServer.io Chromium image without a custom Docker build.

Chromium supervisor
-------------------
The container outlives the browser: Chromium **exits when its last window (tab)
is closed**, while X, the desktop session and this proxy keep running.  The live
view then stays up with no browser window and a dead DevTools endpoint.

Because this process already owns that endpoint, it also supervises the browser:

- endpoint reachable but **no page target** (every tab was closed) -> a new tab
  is opened through ``/json/new``, which brings the window back instantly;
- endpoint unreachable for ``CDP_GUARD_DEAD_THRESHOLD`` consecutive checks
  (Chromium exited) -> the s6 service owning the browser is restarted
  (``s6-svc -r`` then ``-u``), which relaunches Chromium with the mounted
  profile and the container's ``CHROME_CLI`` start URL;
- a startup grace period and a restart cooldown prevent restart storms, and no
  failure can ever take the proxy down (each tick is isolated).

Stable browser id
-----------------
Playwright connects to ``ws://…/devtools/browser/<id>`` and that id changes every
time Chromium restarts, so a cached WebSocket URL becomes stale (404) and the
caller has to fall back to restarting the whole container.  The proxy rewrites
the ``/devtools/browser/<id>`` path of the incoming handshake to the id the
browser currently reports, keeping the endpoint stable across browser restarts.
Best effort: when the current id cannot be read the path is left untouched.

Environment variables:
    CDP_PROXY_LISTEN_HOST  Host/interface to listen on (default ``0.0.0.0``).
    CDP_PROXY_LISTEN_PORT  Exposed proxy port (default ``9223``).
    CDP_TARGET_HOST        DevTools host (default ``127.0.0.1``).
    CDP_TARGET_PORT        DevTools port (default ``9222``).
    CDP_REWRITE_HOST       Value written in the ``Host`` header (default
                           ``127.0.0.1:9222``).
    CDP_GUARD              Keep the browser alive (default ``1``; ``0`` disables).
    CDP_GUARD_INTERVAL     Seconds between checks (default ``2``).
    CDP_GUARD_GRACE        Seconds to wait after start before acting (default ``30``).
    CDP_GUARD_DEAD_THRESHOLD  Unreachable checks before restarting (default ``3``).
    CDP_GUARD_COOLDOWN     Minimum seconds between two browser restarts (default ``15``).
    CDP_GUARD_HTTP_TIMEOUT Timeout of the local DevTools requests (default ``3``).
    CDP_STABLE_BROWSER_ID  Rewrite the browser id (default ``1``; ``0`` disables).
"""

import asyncio
import contextlib
import functools
import json
import logging
import os
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

LISTEN_HOST = os.environ.get("CDP_PROXY_LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("CDP_PROXY_LISTEN_PORT", "9223"))
TARGET_HOST = os.environ.get("CDP_TARGET_HOST", "127.0.0.1")
TARGET_PORT = int(os.environ.get("CDP_TARGET_PORT", "9222"))
REWRITE_HOST = os.environ.get("CDP_REWRITE_HOST", f"{TARGET_HOST}:{TARGET_PORT}")
CHUNK_SIZE = 64 * 1024
MAX_HEADER_BYTES = 64 * 1024

#: Path prefix of the browser WebSocket endpoint reported by ``/json/version``.
BROWSER_WS_PREFIX = "/devtools/browser/"
#: Seconds the current browser id is cached before asking Chromium again.
BROWSER_ID_TTL = 2.0

#: s6-overlay may be installed in different layouts depending on the base image.
SERVICE_DIR_ROOTS = ("/run/service", "/run/s6-rc/servicedirs", "/var/run/s6/services")
#: ``s6-svc`` is either on PATH or in the s6-overlay command folder.
S6_BINARIES = ("s6-svc", "/command/s6-svc")
#: Timeout (seconds) of a single ``s6-svc`` call.
S6_TIMEOUT = 5.0


def _env_flag(name: str, default: bool = True) -> bool:
    """Read a boolean environment flag (``0``/``false``/``no``/``off`` disable)."""
    value = (os.environ.get(name) or "").strip().lower()
    if not value:
        return default
    return value not in ("0", "false", "no", "off")


def _env_float(name: str, default: float) -> float:
    """Read a float environment variable with a safe fallback."""
    try:
        return float((os.environ.get(name) or "").strip() or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable with a safe fallback."""
    try:
        return int((os.environ.get(name) or "").strip() or default)
    except ValueError:
        return default


#: Keep the browser window alive (supervisor).
GUARD_ENABLED = _env_flag("CDP_GUARD", True)
#: Seconds between two supervisor checks.
GUARD_INTERVAL = max(0.5, _env_float("CDP_GUARD_INTERVAL", 2.0))
#: Seconds after start during which the browser is allowed to boot.
GUARD_GRACE = max(0.0, _env_float("CDP_GUARD_GRACE", 30.0))
#: Consecutive unreachable checks before the browser is restarted.
GUARD_DEAD_THRESHOLD = max(1, _env_int("CDP_GUARD_DEAD_THRESHOLD", 3))
#: Minimum seconds between two browser restarts.
GUARD_COOLDOWN = max(0.0, _env_float("CDP_GUARD_COOLDOWN", 15.0))
#: Timeout of the local DevTools requests made by the supervisor.
GUARD_HTTP_TIMEOUT = max(0.5, _env_float("CDP_GUARD_HTTP_TIMEOUT", 3.0))
#: Failed ``/json/new`` attempts before bouncing the browser service.
GUARD_OPEN_RETRY_LIMIT = max(1, _env_int("CDP_GUARD_OPEN_RETRY_LIMIT", 2))
#: Rewrite the browser id so a cached WebSocket URL survives a browser restart.
STABLE_BROWSER_ID = _env_flag("CDP_STABLE_BROWSER_ID", True)

logging.basicConfig(level=logging.INFO, format="[cdp-proxy] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Local DevTools requests
# ---------------------------------------------------------------------------


def _http_json(
    url: str,
    method: str = "GET",
    timeout: Optional[float] = None,
    payload: Optional[bytes] = None,
) -> Any:
    """
    Call a local DevTools endpoint and decode its JSON body.

    A local Chromium answers ``/json/new`` with an empty or non JSON body on some
    builds, so an unparseable body is reported as None instead of an error: the
    HTTP status is what matters for those calls.

    Args:
        url: Absolute URL (always ``127.0.0.1`` based).
        method: HTTP method (``PUT`` is required by ``/json/new``).
        timeout: Request timeout in seconds (None uses the guard default).
        payload: Optional request body (an empty body is sent for ``PUT``).

    Returns:
        Any: Decoded JSON, or None when the body is empty/not JSON.

    Raises:
        urllib.error.URLError: When the endpoint cannot be reached.
        urllib.error.HTTPError: When the endpoint answers with an error status.

    Example:
        >>> _http_json("http://127.0.0.1:9222/json/version")["Browser"]
        'Chrome/120.0.0.0'
    """
    request = urllib.request.Request(
        url,
        data=payload,
        method=method,
        headers={"User-Agent": "codx-junior-cdp"},
    )
    with urllib.request.urlopen(
        request, timeout=GUARD_HTTP_TIMEOUT if timeout is None else timeout
    ) as response:
        body = response.read()

    if not body or not body.strip():
        return None
    try:
        return json.loads(body.decode("utf-8", errors="replace"))
    except ValueError:
        return None


def devtools_status(host: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
    """
    Probe the local browser: is DevTools alive and does it have any tab?

    Args:
        host: DevTools host (defaults to :data:`TARGET_HOST`).
        port: DevTools port (defaults to :data:`TARGET_PORT`).

    Returns:
        Dict[str, Any]: ``alive`` (DevTools answers), ``pages`` (number of page
        targets) and ``error`` when something failed.

    Example:
        >>> devtools_status()["alive"]
        True
    """
    base = f"http://{host or TARGET_HOST}:{port or TARGET_PORT}"

    try:
        _http_json(f"{base}/json/version")
    except Exception as ex:
        return {"alive": False, "pages": 0, "error": str(ex)}

    try:
        targets = _http_json(f"{base}/json/list")
    except Exception as ex:
        # The version endpoint answered but the target list did not: the browser
        # is up but not usable yet (still starting). Never treated as dead.
        return {"alive": True, "pages": 0, "error": str(ex)}

    pages = [
        target for target in (targets or [])
        if str(target.get("type") or "") == "page" and not target.get("closed")
    ]
    return {
        "alive": True,
        "pages": len(pages),
        "urls": [page.get("url") for page in pages][:5],
    }


def open_tab(url: str = "about:blank", host: Optional[str] = None, port: Optional[int] = None) -> bool:
    """
    Open a tab in the running browser (brings the window back when it had none).

    Recent Chromium only accepts ``PUT`` on ``/json/new``; older builds accept
    ``GET``, so both are tried.

    Args:
        url: URL opened in the new tab.
        host: DevTools host (defaults to :data:`TARGET_HOST`).
        port: DevTools port (defaults to :data:`TARGET_PORT`).

    Returns:
        bool: True when the tab could be created.

    Example:
        >>> open_tab()  # doctest: +SKIP
        True
    """
    target = f"http://{host or TARGET_HOST}:{port or TARGET_PORT}/json/new?{url}"
    for method in ("PUT", "GET"):
        try:
            _http_json(target, method=method, payload=b"" if method == "PUT" else None)
            return True
        except Exception as ex:
            logger.debug("Could not open a tab with %s: %s", method, ex)
    return False


# ---------------------------------------------------------------------------
# Browser window restart (s6 service)
# ---------------------------------------------------------------------------


def chromium_service_dirs(roots: Optional[Any] = None) -> List[str]:
    """
    Find the s6 service directories that own the browser.

    The container runs s6-overlay, so the browser is a supervised service
    (``svc-chromium`` on LinuxServer.io images) and can be relaunched without
    touching X or the desktop session.

    Args:
        roots: Roots to scan (defaults to :data:`SERVICE_DIR_ROOTS`).

    Returns:
        List[str]: Existing service directories whose name mentions chromium or
        the browser, in discovery order.

    Example:
        >>> chromium_service_dirs(("/run/service",))
        ['/run/service/svc-chromium']
    """
    found: List[str] = []
    for root in (SERVICE_DIR_ROOTS if roots is None else roots):
        try:
            entries = sorted(os.listdir(root))
        except OSError:
            continue
        for name in entries:
            lowered = name.lower()
            if "chrom" not in lowered and "browser" not in lowered:
                continue
            path = os.path.join(root, name)
            if os.path.isdir(path) and path not in found:
                found.append(path)
    return found


def _run_s6_command(flag: str, service_dir: str) -> bool:
    """
    Send one ``s6-svc`` command to a service directory.

    Args:
        flag: ``-r`` (restart) or ``-u`` (bring up).
        service_dir: Live s6 service directory.

    Returns:
        bool: True when ``s6-svc`` could be executed successfully.

    Example:
        >>> _run_s6_command("-r", "/run/service/svc-chromium")
        True
    """
    for binary in S6_BINARIES:
        try:
            result = subprocess.run(
                [binary, flag, service_dir],
                capture_output=True,
                text=True,
                timeout=S6_TIMEOUT,
            )
        except FileNotFoundError:
            continue
        except Exception as ex:
            logger.warning("s6-svc %s %s failed: %s", flag, service_dir, ex)
            return False
        if result.returncode == 0:
            return True
        logger.debug(
            "s6-svc %s %s exited %s: %s",
            flag, service_dir, result.returncode, (result.stderr or "").strip(),
        )
    return False


def restart_chromium_service(
    dirs: Optional[List[str]] = None,
    runner: Optional[Callable[[str, str], bool]] = None,
) -> bool:
    """
    Relaunch Chromium inside the running container.

    ``-r`` restarts a running service and ``-u`` brings up a stopped one; both
    are sent because s6 ignores the one that does not apply, so a browser that
    exited on its own is covered by the same call.

    Args:
        dirs: Service directories (defaults to :func:`chromium_service_dirs`).
        runner: Command runner (defaults to :func:`_run_s6_command`), injectable
            for tests.

    Returns:
        bool: True when at least one command was accepted.

    Example:
        >>> restart_chromium_service()  # doctest: +SKIP
        True
    """
    targets = chromium_service_dirs() if dirs is None else list(dirs)
    runner = runner or _run_s6_command

    if not targets:
        logger.warning(
            "Chromium supervisor: no s6 service found (looked in %s); "
            "the browser cannot be relaunched from inside the container",
            ", ".join(SERVICE_DIR_ROOTS),
        )
        return False

    accepted = False
    for service_dir in targets:
        for flag in ("-r", "-u"):
            if runner(flag, service_dir):
                accepted = True
    if accepted:
        logger.info("Chromium supervisor: relaunched the browser (%s)", ", ".join(targets))
    return accepted


# ---------------------------------------------------------------------------
# Chromium supervisor
# ---------------------------------------------------------------------------


class ChromiumSupervisor:
    """
    Keeps the shared browser alive from inside the container.

    Each ``check()`` performs one isolated probe and, at most, one repair:

        alive + tabs        -> nothing to do (``ok``)
        alive + no tabs     -> reopen a tab (``opened``), or bounce the service
                               when new tabs keep failing (``restarted``)
        unreachable         -> count failures and, on the threshold, bounce the
                               browser service (``restarted``)

    ``run()`` repeats ``check()`` every ``interval`` seconds in a worker thread,
    so a slow probe never blocks the CDP tunnelling done by the same process.

    Args:
        interval: Seconds between checks.
        grace: Seconds after start during which nothing is done (browser boot).
        dead_threshold: Consecutive unreachable checks before restarting.
        cooldown: Minimum seconds between two restarts.
        probe: Status probe (defaults to :func:`devtools_status`).
        opener: Tab opener (defaults to :func:`open_tab`).
        restarter: Browser restarter (defaults to :func:`restart_chromium_service`).
        clock: Monotonic clock, injectable for tests.

    Example:
        >>> supervisor = ChromiumSupervisor(grace=0, probe=lambda: {"alive": True, "pages": 1})
        >>> supervisor.check()["action"]
        'ok'
    """

    def __init__(
        self,
        interval: Optional[float] = None,
        grace: Optional[float] = None,
        dead_threshold: Optional[int] = None,
        cooldown: Optional[float] = None,
        probe: Optional[Callable[[], Dict[str, Any]]] = None,
        opener: Optional[Callable[[], bool]] = None,
        restarter: Optional[Callable[[], bool]] = None,
        clock: Optional[Callable[[], float]] = None,
    ):
        self.interval = GUARD_INTERVAL if interval is None else max(0.05, float(interval))
        self.grace = GUARD_GRACE if grace is None else max(0.0, float(grace))
        self.dead_threshold = (
            GUARD_DEAD_THRESHOLD if dead_threshold is None else max(1, int(dead_threshold))
        )
        self.cooldown = GUARD_COOLDOWN if cooldown is None else max(0.0, float(cooldown))

        self.probe = probe or devtools_status
        self.opener = opener or open_tab
        self.restarter = restarter or restart_chromium_service
        self.clock = clock or time.monotonic

        self.grace_until = self.clock() + self.grace
        self.consecutive_failures = 0
        self.open_failures = 0
        self.next_restart_at = 0.0
        self.restarts = 0
        self.opened_tabs = 0
        self.stopped = False

    # -- state machine ------------------------------------------------------

    def check(self) -> Dict[str, Any]:
        """
        Probe the browser once and repair it when needed.

        Returns:
            Dict[str, Any]: The action taken, with the relevant counters:
            ``ok``, ``grace``, ``opened``, ``open_failed``, ``unreachable``,
            ``restarted``, ``restart_failed`` or ``restart_cooldown``.

        Example:
            >>> ChromiumSupervisor(grace=0, probe=lambda: {"alive": False, "pages": 0}).check()["action"]
            'unreachable'
        """
        now = self.clock()
        if now < self.grace_until:
            return {
                "action": "grace",
                "remaining": round(self.grace_until - now, 1),
            }

        status = self.probe() or {}
        if status.get("alive"):
            self.consecutive_failures = 0
            if int(status.get("pages") or 0) > 0:
                self.open_failures = 0
                return {"action": "ok", "pages": int(status.get("pages") or 0)}

            # The browser is up but every tab was closed: reopening one brings
            # the window back without restarting anything.
            if self.opener():
                self.open_failures = 0
                self.opened_tabs += 1
                logger.info("Chromium supervisor: every tab was closed, reopened one")
                return {"action": "opened", "reason": "no open tabs"}

            self.open_failures += 1
            if self.open_failures >= GUARD_OPEN_RETRY_LIMIT:
                return self._restart("the window shows no tabs and new tabs fail")
            return {
                "action": "open_failed",
                "attempts": self.open_failures,
                "reason": str(status.get("error") or "no open tabs"),
            }

        self.consecutive_failures += 1
        if self.consecutive_failures < self.dead_threshold:
            return {
                "action": "unreachable",
                "failures": self.consecutive_failures,
                "threshold": self.dead_threshold,
                "reason": str(status.get("error") or "devtools endpoint unreachable"),
            }
        return self._restart(str(status.get("error") or "devtools endpoint unreachable"))

    def _restart(self, reason: str) -> Dict[str, Any]:
        """Relaunch the browser service, honouring the restart cooldown."""
        now = self.clock()
        if now < self.next_restart_at:
            return {
                "action": "restart_cooldown",
                "reason": reason,
                "retry_in": round(self.next_restart_at - now, 1),
            }

        self.next_restart_at = now + self.cooldown
        self.consecutive_failures = 0
        self.open_failures = 0

        if not self.restarter():
            logger.warning("Chromium supervisor: could not relaunch the browser (%s)", reason)
            return {"action": "restart_failed", "reason": reason}

        self.restarts += 1
        # The browser id changes with the relaunch: the cached WebSocket path is
        # now stale and must be resolved again.
        invalidate_browser_path()
        logger.warning("Chromium supervisor: relaunched the browser (%s)", reason)
        return {"action": "restarted", "reason": reason}

    # -- loop ---------------------------------------------------------------

    async def run(self, stop_event: Optional[Any] = None) -> None:
        """
        Supervise the browser until stopped.

        Args:
            stop_event: Optional ``asyncio.Event`` used to end the loop.
        """
        logger.info(
            "Chromium supervisor started (interval=%ss, grace=%ss, threshold=%s, cooldown=%ss)",
            self.interval, self.grace, self.dead_threshold, self.cooldown,
        )
        while not self.stopped:
            if stop_event is not None and stop_event.is_set():
                break
            try:
                result = await _run_blocking(self.check)
                self._log(result)
            except Exception as ex:
                # A broken probe must never stop the proxy from tunnelling.
                logger.exception("Chromium supervisor check failed: %s", ex)
            await asyncio.sleep(self.interval)

    @staticmethod
    def _log(result: Dict[str, Any]) -> None:
        """Log one check result at the level its severity deserves."""
        action = result.get("action")
        if action in ("opened", "restarted", "restart_failed", "open_failed"):
            logger.warning(
                "Chromium supervisor: %s (%s)", action, result.get("reason") or ""
            )
        else:
            logger.debug("Chromium supervisor: %s", result)


async def _run_blocking(func: Callable[..., Any], *args: Any) -> Any:
    """
    Run a blocking callable in the default executor.

    ``asyncio.to_thread`` is not used on purpose: it requires Python 3.9 while the
    browser image may ship an older interpreter.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args))


# ---------------------------------------------------------------------------
# Stable browser id
# ---------------------------------------------------------------------------

#: Cached ``/devtools/browser/<id>`` path reported by the running browser.
_browser_path_cache: Dict[str, Any] = {"path": None, "expires_at": 0.0}


def invalidate_browser_path() -> None:
    """Forget the cached browser id (called after a browser relaunch)."""
    _browser_path_cache["path"] = None
    _browser_path_cache["expires_at"] = 0.0


def current_browser_path() -> Optional[str]:
    """
    Return the WebSocket path of the browser that is running right now.

    Returns:
        Optional[str]: ``/devtools/browser/<id>``, or None when it cannot be read.

    Example:
        >>> current_browser_path()  # doctest: +SKIP
        '/devtools/browser/5c2c…'
    """
    now = time.monotonic()
    cached = _browser_path_cache.get("path")
    if cached and now < _browser_path_cache.get("expires_at", 0.0):
        return cached

    try:
        info = _http_json(f"http://{TARGET_HOST}:{TARGET_PORT}/json/version")
    except Exception as ex:
        logger.debug("Could not read the current browser id: %s", ex)
        return None

    path = urlparse((info or {}).get("webSocketDebuggerUrl") or "").path or ""
    if not path.startswith(BROWSER_WS_PREFIX):
        return None

    _browser_path_cache["path"] = path
    _browser_path_cache["expires_at"] = now + BROWSER_ID_TTL
    return path


def rewrite_request_line(line: str, browser_path: Optional[str] = None) -> str:
    """
    Point a ``/devtools/browser/<id>`` request to the browser running now.

    The id changes on every Chromium restart, so a WebSocket URL cached by a
    client (Playwright's ``debug_url``) becomes stale. Rewriting it keeps the
    endpoint usable across browser restarts.

    Args:
        line: HTTP request line (``GET /devtools/browser/<id> HTTP/1.1``).
        browser_path: Path to use (None leaves the request untouched).

    Returns:
        str: The request line to send.

    Example:
        >>> rewrite_request_line("GET /devtools/browser/old HTTP/1.1", "/devtools/browser/new")
        'GET /devtools/browser/new HTTP/1.1'
    """
    if not browser_path:
        return line
    parts = line.split(" ")
    if len(parts) < 3 or not parts[1].startswith(BROWSER_WS_PREFIX):
        return line
    method, _, version = parts[0], parts[1], " ".join(parts[2:])
    return f"{method} {browser_path} {version}"


# ---------------------------------------------------------------------------
# Tunnelling
# ---------------------------------------------------------------------------


def _rewrite_headers(raw: bytes, browser_path: Optional[str] = None) -> bytes:
    """
    Replace the HTTP ``Host`` header of a request with :data:`REWRITE_HOST`.

    Args:
        raw: The request line plus headers, ending with ``\\r\\n\\r\\n``.
        browser_path: Optional current ``/devtools/browser/<id>`` path used to
            refresh a stale browser id in the request line.

    Returns:
        The same request with a single loopback ``Host`` header.
    """
    text = raw.decode("latin-1", errors="replace")
    lines = text.split("\r\n")
    if not lines:
        return raw

    rewritten = [rewrite_request_line(lines[0], browser_path)]
    for line in lines[1:]:
        if not line:
            continue
        if line.lower().startswith("host:"):
            continue
        rewritten.append(line)
    # Insert right after the request line: proxy tools expect Host early.
    rewritten.insert(1, f"Host: {REWRITE_HOST}")
    return ("\r\n".join(rewritten) + "\r\n\r\n").encode("latin-1")


async def _read_http_headers(reader: asyncio.StreamReader) -> bytes:
    """Read the first HTTP request headers (up to the terminating blank line)."""
    data = b""
    while b"\r\n\r\n" not in data and len(data) < MAX_HEADER_BYTES:
        chunk = await reader.read(4096)
        if not chunk:
            break
        data += chunk
    return data


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Copy every chunk from *reader* to *writer* until EOF or error."""
    try:
        while True:
            data = await reader.read(CHUNK_SIZE)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def _handle(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter) -> None:
    """Rewrite the first request's Host header and tunnel the connection."""
    try:
        raw_headers = await _read_http_headers(client_reader)
        if not raw_headers:
            client_writer.close()
            return

        # Keep a cached /devtools/browser/<id> usable after a browser restart.
        browser_path = None
        if STABLE_BROWSER_ID and BROWSER_WS_PREFIX.encode() in raw_headers:
            try:
                browser_path = await _run_blocking(current_browser_path)
            except Exception as ex:
                logger.debug("Could not resolve the current browser id: %s", ex)

        marker = b"\r\n\r\n"
        if marker in raw_headers:
            headers, _, extra = raw_headers.partition(marker)
            raw_headers = _rewrite_headers(headers + marker, browser_path)
            if extra:
                raw_headers += extra
        else:
            raw_headers = _rewrite_headers(raw_headers + marker, browser_path)

        target_reader, target_writer = await asyncio.open_connection(TARGET_HOST, TARGET_PORT)
        target_writer.write(raw_headers)
        await target_writer.drain()

        await asyncio.gather(
            _pipe(client_reader, target_writer),
            _pipe(target_reader, client_writer),
        )
    except Exception as ex:
        logger.warning("CDP proxy connection failed: %s", ex)
        try:
            client_writer.close()
        except Exception:
            pass


async def main() -> None:
    """Start the proxy and the browser supervisor, then serve forever."""
    server = await asyncio.start_server(_handle, LISTEN_HOST, LISTEN_PORT)
    sockets = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    logger.info("CDP proxy listening on %s -> %s:%s", sockets, TARGET_HOST, TARGET_PORT)

    guard_task = None
    if GUARD_ENABLED:
        guard_task = asyncio.ensure_future(ChromiumSupervisor().run())
    else:
        logger.info("Chromium supervisor disabled (CDP_GUARD=0)")

    try:
        async with server:
            await server.serve_forever()
    finally:
        if guard_task is not None:
            guard_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await guard_task


if __name__ == "__main__":
    asyncio.run(main())