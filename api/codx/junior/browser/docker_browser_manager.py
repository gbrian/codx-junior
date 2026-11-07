"""
DockerBrowserManager — manages the Chromium co-browsing container lifecycle.

Each ``BrowserSession`` gets its own LinuxServer.io Chromium container.  The
container serves two endpoints:

* **Live view / user control** – the Selkies web desktop on port ``3000``,
  published through Traefik at ``/browser/<session_id>/``.  Users can click,
  type and navigate exactly like a local browser.
* **DevTools automation** – Chromium's CDP endpoint.  Chromium binds it to
  ``127.0.0.1`` only, so a small TCP proxy (``browser/cdp_proxy.py``) listens
  on the container network at port ``9223`` and forwards to ``9222``.  The API
  container (same Docker network) uses it through Playwright.

Lifecycle semantics
-------------------
- ``stop_container(session, remove=True)``  : stop + remove (full teardown).
- ``stop_container(session, remove=False)`` : stop only — the container is kept
  so it can be started again with ``restart_container`` (state preserved).
- ``restart_container(session)``            : starts an existing (stopped)
  container, or recreates it if the container no longer exists.

Configuration (environment variables)
-------------------------------------
``CODX_BROWSER_IMAGE``            Chromium image (default
                                  ``lscr.io/linuxserver/chromium:latest``).
``CODX_BROWSER_NETWORK``          Docker network (default
                                  ``codx-junior_default``).
``CODX_BROWSER_AUTO_PULL``        Pull the image when missing (default ``1``).
``CODX_BROWSER_PUBLIC_BASE_URL``  Override the public VNC base URL.
``CODX_BROWSER_AUTH_MIDDLEWARE``  Traefik auth middleware name
                                  (default ``codx-junior-auth``; empty disables).
``CODX_BROWSER_CDP_PROXY_PORT``   Proxy listen port inside the container
                                  (default ``9223``).
"""

import json
import logging
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse

from codx.junior.browser.model import BrowserSession

logger = logging.getLogger(__name__)

#: Default browser image.  Chromium (not Firefox) is required because
#: Playwright drives the shared browser through the Chrome DevTools Protocol.
DEFAULT_BROWSER_IMAGE = "lscr.io/linuxserver/chromium:latest"
DEFAULT_DOCKER_NETWORK = "codx-junior_default"
DEFAULT_CDP_PROXY_PORT = 9223
DEFAULT_VNC_PORT = 3000
CONTAINER_PREFIX = "browser_"
CONTAINER_LABEL = "codx-junior.browser"
CONTAINER_PROJECT_LABEL = "codx-junior.browser.project"
CONTAINER_SESSION_LABEL = "codx-junior.browser.session"
MAX_SESSIONS = 10
DOCKER_READY_TIMEOUT = 60


def _env_flag(name: str, default: bool = True) -> bool:
    """Read a boolean environment flag."""
    value = (os.environ.get(name) or "").strip().lower()
    if not value:
        return default
    return value not in ("0", "false", "no", "off")


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable with a safe fallback."""
    try:
        return int((os.environ.get(name) or "").strip() or default)
    except ValueError:
        return default


def _public_base_url() -> Optional[str]:
    """Return the configured public base URL for browser views (if any)."""
    return (os.environ.get("CODX_BROWSER_PUBLIC_BASE_URL") or "").strip().rstrip("/") or None


def _normalize_domain(value: str) -> str:
    """Accept ``host`` or ``https://host`` and return a clean scheme+host."""
    domain = (value or "").strip().rstrip("/")
    if domain.startswith(("http://", "https://")):
        return domain
    return f"http://{domain}"


class DockerBrowserManager:
    #: Exposed as a class attribute for callers enforcing the session quota.
    MAX_SESSIONS = MAX_SESSIONS

    """
    Orchestrates the Chromium containers used for co-browsing.

    A session's container has:

    - a persistent Chromium profile mounted at ``/config``,
    - a Traefik route for the Selkies live view (no path stripping; the image
      is started with ``SUBFOLDER=/browser/<session_id>/``),
    - the CDP proxy mounted read-only at ``/cdp_proxy.py``.
    """

    def __init__(
        self,
        browser_sessions_path: str,
        traefik_domain: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """
        Initialize the Docker manager.

        Args:
            browser_sessions_path: Base path for browser session data
                (e.g. ``.codx/browser_sessions/``).
            traefik_domain: Domain used in Traefik rules (defaults to
                ``CODX_JUNIOR_DOMAIN`` or ``localhost``).
            project_id: Project identifier used to scope container cleanup.
        """
        self.browser_sessions_path = browser_sessions_path
        self.traefik_domain = (traefik_domain or os.environ.get("CODX_JUNIOR_DOMAIN") or "localhost").strip()
        self.project_id = project_id
        self.image = (os.environ.get("CODX_BROWSER_IMAGE") or DEFAULT_BROWSER_IMAGE).strip()
        self.network = (os.environ.get("CODX_BROWSER_NETWORK") or DEFAULT_DOCKER_NETWORK).strip()
        self.cdp_proxy_port = _env_int("CODX_BROWSER_CDP_PROXY_PORT", DEFAULT_CDP_PROXY_PORT)
        self.vnc_port = _env_int("CODX_BROWSER_VNC_PORT", DEFAULT_VNC_PORT)
        self.auth_middleware = (os.environ.get("CODX_BROWSER_AUTH_MIDDLEWARE") or "codx-junior-auth").strip()
        self.auto_pull = _env_flag("CODX_BROWSER_AUTO_PULL", True)
        os.makedirs(browser_sessions_path, exist_ok=True)
        logger.debug(
            "DockerBrowserManager initialized at '%s' (domain: %s, image: %s)",
            browser_sessions_path,
            self.traefik_domain,
            self.image,
        )

    # -------------------------------------------------------------------------
    # Container lifecycle
    # -------------------------------------------------------------------------

    def start_container(self, session: BrowserSession) -> BrowserSession:
        """
        Start a Chromium container for the session and resolve its endpoints.

        Args:
            session: BrowserSession with ``id`` set.

        Returns:
            Updated BrowserSession with container id, VNC URL and CDP URL.

        Raises:
            RuntimeError: If the container cannot be started or does not become
                ready within :data:`DOCKER_READY_TIMEOUT` seconds.
        """
        session_folder = self._get_session_folder(session.id)
        profile_path = self._profile_path(session.id)
        os.makedirs(profile_path, exist_ok=True)
        self._ensure_owned(profile_path)

        container_name = f"{CONTAINER_PREFIX}{session.id[:8]}"
        path_prefix = self._path_prefix(session.id)
        router_name = f"codx-browser-{session.id[:8]}"

        self._ensure_image()

        try:
            self._remove_same_named_container(container_name)
            cmd = self._build_run_command(
                session=session,
                container_name=container_name,
                profile_path=profile_path,
                path_prefix=path_prefix,
                router_name=router_name,
            )
            logger.info(
                "Starting Chromium container: %s (image: %s, network: %s, path: %s)",
                container_name,
                self.image,
                self.network,
                path_prefix,
            )
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"Docker run failed: {result.stderr.strip() or result.stdout.strip()}")

            container_id = (result.stdout or "").strip()
            if not container_id:
                raise RuntimeError("Docker run returned an empty container id")

            session.container_id = container_id
            session.container_name = container_name
            session.browser_profile_path = profile_path
            session.engine = "chromium"
            session.traefik_domain = self.traefik_domain
            session.traefik_path_prefix = path_prefix
            session.vnc_url = self._build_vnc_url(session.id)
            session.vnc_path = path_prefix
            session.status = "running"
            session.error = None
            session.mark_active()

            self._wait_for_container_ready(container_name, timeout=DOCKER_READY_TIMEOUT)
            session.debug_url = self._resolve_debug_url(container_name)
            session.current_url = session.current_url or None
            logger.info(
                "Browser session %s ready (live view: %s, CDP: %s)",
                session.id[:8],
                session.vnc_url,
                session.debug_url,
            )
            return session

        except Exception as ex:
            logger.exception("Failed to start Chromium container")
            if session.container_id:
                # Don't leave a half-broken container behind
                self.stop_container(session, remove=True)
                session.container_id = None
            session.status = "error"
            session.error = str(ex)
            raise

    def stop_container(self, session: BrowserSession, remove: bool = True) -> None:
        """
        Stop a browser container, optionally removing it.

        Args:
            session: BrowserSession with ``container_id`` set.
            remove: When True (default) stop **and remove**. When False only
                stop, so :meth:`restart_container` can start it again.
        """
        if not session:
            return
        if not session.container_id:
            logger.warning(
                "Cannot stop session %s: no container_id",
                session.id[:8] if session.id else "?",
            )
            session.status = "stopped"
            return

        try:
            logger.info(
                "Stopping container: %s (remove=%s)",
                str(session.container_id)[:12],
                remove,
            )
            subprocess.run(
                ["docker", "stop", session.container_id],
                capture_output=True,
                timeout=30,
            )
            if remove:
                subprocess.run(
                    ["docker", "rm", "-f", session.container_id],
                    capture_output=True,
                    timeout=20,
                )
                session.container_id = None
                session.debug_url = None
            session.status = "stopped"
            session.error = None
            session.mark_active()
            logger.info("Container stopped: %s", str(session.container_id)[:12] if session.container_id else "-")
        except Exception as ex:
            logger.exception("Error stopping container: %s", ex)
            session.status = "error"
            session.error = f"Stop failed: {ex}"

    def restart_container(self, session: BrowserSession) -> BrowserSession:
        """
        Restart a stopped session, recreating the container if needed.

        An existing (stopped) container is started again, preserving the
        profile.  If the container was removed, a fresh container is created
        from the same session folder (the profile on disk is preserved).

        Args:
            session: BrowserSession to restart.

        Returns:
            Updated BrowserSession.

        Raises:
            RuntimeError: If restart fails.
        """
        if session.container_id and self._container_exists(session.container_id):
            try:
                logger.info("Restarting container: %s", str(session.container_id)[:12])
                result = subprocess.run(
                    ["docker", "start", session.container_id],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or "docker start failed")
                self._wait_for_container_ready(
                    session.container_name or session.container_id,
                    timeout=DOCKER_READY_TIMEOUT,
                )
                session.debug_url = self._resolve_debug_url(
                    session.container_name or session.container_id
                )
                session.status = "running"
                session.error = None
                session.mark_active()
                return session
            except Exception as ex:
                logger.exception("Failed to restart existing container")
                session.status = "error"
                session.error = str(ex)
                raise

        logger.info("Container missing for session %s; recreating", session.id[:8])
        session.container_id = None
        session.debug_url = None
        return self.start_container(session)

    def remove_container(self, session: BrowserSession) -> None:
        """Stop and remove the container (alias of ``stop_container(remove=True)``)."""
        self.stop_container(session, remove=True)

    def get_container_logs(self, session: BrowserSession, tail: int = 50) -> str:
        """Return the last ``tail`` lines of the session container logs."""
        if not session or not session.container_id:
            return ""
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(max(1, int(tail))), session.container_id],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return ((result.stdout or "") + (result.stderr or "")).strip()
        except Exception as ex:
            logger.warning("Could not read container logs: %s", ex)
            return ""

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def _profile_path(self, session_id: str) -> str:
        """Return the persistent Chromium profile folder for a session."""
        return os.path.join(self._get_session_folder(session_id), "chromium_profile")

    def _path_prefix(self, session_id: str) -> str:
        """Return the public Traefik path prefix (with trailing slash)."""
        return f"/browser/{session_id}/"

    def _build_vnc_url(self, session_id: str) -> str:
        """Build the public live-view URL for the session."""
        base = _public_base_url()
        if base:
            return f"{base}/browser/{session_id}/"
        return f"{_normalize_domain(self.traefik_domain)}/browser/{session_id}/"

    def _build_run_command(
        self,
        session: BrowserSession,
        container_name: str,
        profile_path: str,
        path_prefix: str,
        router_name: str,
    ) -> List[str]:
        """Build the ``docker run`` command for a session container."""
        proxy_script = self._prepare_cdp_proxy(session.id)
        url = (session.current_url or os.environ.get("CODX_BROWSER_START_URL") or "about:blank").strip()
        chrome_args = " ".join(
            arg for arg in [
                "--remote-debugging-port=9222",
                "--remote-allow-origins=*",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-session-crashed-bubble",
                "--disable-restore-session-state",
                "--start-maximized",
                "--window-size=1920,1080",
                url,
            ] if arg
        )

        cmd = [
            "docker",
            "run",
            "-d",
            "--name", container_name,
            "--network", self.network,
            "--label", f"{CONTAINER_LABEL}=true",
            "--label", f"{CONTAINER_PROJECT_LABEL}={self.project_id or ''}",
            "--label", f"{CONTAINER_SESSION_LABEL}={session.id}",
            "-e", f"PUID={os.getuid() or 1000}",
            "-e", f"PGID={os.getgid() or 1000}",
            "-e", "TZ=Etc/UTC",
            "-e", f"SUBFOLDER={path_prefix}",
            "-e", f"TITLE={self._container_title(session)}",
            "-e", f"CHROME_CLI={chrome_args}",
            "-v", f"{profile_path}:/config",
            "-v", f"{proxy_script}:/cdp_proxy.py:ro",
            "--shm-size=2gb",
            "--security-opt", "seccomp=unconfined",
            "--entrypoint", "/bin/bash",
        ]

        for label in self._build_traefik_labels(
            router_name=router_name,
            session_id=session.id,
            path_prefix=path_prefix,
        ):
            cmd.extend(["-l", label])

        cmd.extend([
            self.image,
            "-c",
            "python3 /cdp_proxy.py >/tmp/cdp-proxy.log 2>&1 & exec /init",
        ])
        return cmd

    @staticmethod
    def _container_title(session: BrowserSession) -> str:
        """Sanitize the session name for the container's page title."""
        name = (session.name or f"Browser {session.id[:8]}").strip()
        return f"codx-junior · {name}"[:120]

    def _prepare_cdp_proxy(self, session_id: str) -> str:
        """
        Copy the bundled CDP proxy into the session folder and return its path.

        The session folder is already bind-mounted into the browser container,
        so placing the script there avoids assuming anything about where the
        API source tree lives on the Docker host.
        """
        source = Path(__file__).with_name("cdp_proxy.py")
        target = Path(self._get_session_folder(session_id)) / "cdp_proxy.py"
        static_source = Path(__file__).parents[4] / "browser" / "cdp_proxy.py"
        if not source.exists() and static_source.exists():
            source = static_source
        if not source.exists():
            raise RuntimeError(
                f"CDP proxy script not found (looked for {source}); "
                "the browser container cannot be started"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return str(target)

    def _ensure_image(self) -> None:
        """Pull the browser image when it is missing (best effort configurable)."""
        try:
            inspect = subprocess.run(
                ["docker", "image", "inspect", self.image],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if inspect.returncode == 0:
                return
        except Exception as ex:
            logger.debug("Could not inspect image %s: %s", self.image, ex)

        if not self.auto_pull:
            raise RuntimeError(
                f"Docker image '{self.image}' is not available. Pull it with "
                f"'docker pull {self.image}' or set CODX_BROWSER_AUTO_PULL=1."
            )

        logger.info("Pulling browser image '%s' (first use may take a while)", self.image)
        try:
            result = subprocess.run(
                ["docker", "pull", self.image],
                capture_output=True,
                text=True,
                timeout=900,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        except Exception as ex:
            raise RuntimeError(
                f"Could not pull Docker image '{self.image}': {ex}. "
                f"Pull it manually with 'docker pull {self.image}'."
            ) from ex

    def _remove_same_named_container(self, container_name: str) -> None:
        """Remove a stale container with the same name (e.g. after a crash)."""
        try:
            result = subprocess.run(
                ["docker", "ps", "-aq", "--filter", f"name=^/{container_name}$"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            ids = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
            for cid in ids:
                subprocess.run(["docker", "rm", "-f", cid], capture_output=True, timeout=20)
        except Exception as ex:
            logger.debug("Could not remove stale container %s: %s", container_name, ex)

    def _container_exists(self, container_id: str) -> bool:
        """Return True when the given container (id or name) still exists."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.Id}}", container_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            return False

    def _get_session_folder(self, session_id: str) -> str:
        """Get the folder path for a session."""
        return os.path.join(self.browser_sessions_path, session_id)

    def _get_session_file_path(self, session_id: str) -> str:
        """Get the metadata file path for a session."""
        return os.path.join(self._get_session_folder(session_id), f"{session_id}.session")

    def _build_traefik_labels(
        self,
        router_name: str,
        session_id: str,
        path_prefix: str,
    ) -> List[str]:
        """
        Build Traefik Docker labels for the live-view route.

        The path prefix is **not** stripped: the container is started with
        ``SUBFOLDER=<path_prefix>`` so Selkies serves its assets and websocket
        endpoint under the same prefix.
        """
        host = urlparse(_normalize_domain(self.traefik_domain)).netloc or self.traefik_domain
        labels = [
            "traefik.enable=true",
            f"traefik.http.routers.{router_name}.rule=Host(`{host}`) && PathPrefix(`{path_prefix}`)",
            f"traefik.http.routers.{router_name}.service={router_name}-service",
            f"traefik.http.services.{router_name}-service.loadbalancer.server.port={self.vnc_port}",
            f"traefik.http.services.{router_name}-service.loadbalancer.server.scheme=http",
            f"traefik.docker.network={self.network}",
            f"traefik.http.routers.{router_name}.priority=200",
        ]
        if self.auth_middleware:
            labels.append(
                f"traefik.http.routers.{router_name}.middlewares={self.auth_middleware}"
            )
        return labels

    def _wait_for_container_ready(self, container_name: str, timeout: int = DOCKER_READY_TIMEOUT) -> None:
        """
        Wait until both the live view and the CDP proxy respond.

        Args:
            container_name: Docker container name (also its DNS name on the
                shared network).
            timeout: Maximum wait time in seconds.

        Raises:
            TimeoutError: If either endpoint is not reachable in time.
        """
        deadline = time.time() + timeout
        last_error = "not started"
        while time.time() < deadline:
            if not self._container_exists(container_name):
                raise RuntimeError(f"Browser container {container_name} exited before becoming ready")
            try:
                self._http_get(f"http://{container_name}:{self.vnc_port}/")
                # The proxy is usable only when Chromium's DevTools endpoint is
                # up behind it, so verify the JSON endpoint as well.
                self._http_json(f"http://{container_name}:{self.cdp_proxy_port}/json/version")
                logger.debug("Container %s is ready", container_name)
                return
            except Exception as ex:
                last_error = str(ex)
                time.sleep(1)

        raise TimeoutError(
            f"Browser container {container_name} failed to become ready in {timeout}s "
            f"(last error: {last_error})"
        )

    def _resolve_debug_url(self, container_name: str) -> str:
        """
        Resolve the CDP WebSocket URL through the in-container proxy.

        Chromium reports ``ws://127.0.0.1:9222/...``; rewrite the host to the
        container DNS name and the proxy port so the API container can reach it.
        """
        info = self._http_json(f"http://{container_name}:{self.cdp_proxy_port}/json/version")
        ws_url = (info or {}).get("webSocketDebuggerUrl")
        if not ws_url:
            raise RuntimeError("Chromium did not expose a webSocketDebuggerUrl")
        parsed = urlparse(ws_url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return f"ws://{container_name}:{self.cdp_proxy_port}{path}"

    @staticmethod
    def _http_get(url: str) -> bytes:
        """Fetch *url* with a short timeout (used as a readiness probe)."""
        request = urllib.request.Request(url, headers={"User-Agent": "codx-junior-browser-probe"})
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status >= 500:
                raise RuntimeError(f"HTTP {response.status} from {url}")
            return response.read(4096)

    @staticmethod
    def _http_json(url: str) -> dict:
        """Fetch and decode a JSON document (used for DevTools discovery)."""
        request = urllib.request.Request(url, headers={"User-Agent": "codx-junior-browser-probe"})
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _ensure_owned(path: str) -> None:
        """Best-effort make the profile writable by the container user."""
        try:
            # The browser container runs with the API process' uid/gid.
            os.chmod(path, 0o775)
        except OSError:
            pass

    def cleanup_all_containers(self) -> None:
        """
        Stop all browser containers belonging to this project.

        Cleanup on shutdown must never touch another project's containers, so
        the filter uses the project label set at creation time.
        """
        try:
            filters = ["--filter", f"label={CONTAINER_LABEL}=true"]
            if self.project_id:
                filters.extend(["--filter", f"label={CONTAINER_PROJECT_LABEL}={self.project_id}"])
            result = subprocess.run(
                ["docker", "ps", "-aq", *filters],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                logger.warning("Could not list browser containers: %s", result.stderr.strip())
                return
            for cid in [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]:
                try:
                    subprocess.run(["docker", "stop", cid], capture_output=True, timeout=20)
                    subprocess.run(["docker", "rm", "-f", cid], capture_output=True, timeout=20)
                    logger.info("Cleaned up browser container: %s", cid[:12])
                except Exception as ex:
                    logger.warning("Failed to cleanup container %s: %s", cid[:12], ex)
        except Exception as ex:
            logger.warning("Error during cleanup_all_containers: %s", ex)


#: Backwards-compatible alias.  Older code (and persisted documentation) used
#: the Firefox-specific name; the implementation now uses Chromium because
#: Playwright's CDP support requires it.
DockerFirefoxManager = DockerBrowserManager


# Made with ❤️ by codx-junior
