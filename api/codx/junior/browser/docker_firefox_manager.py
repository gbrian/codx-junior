"""
DockerFirefoxManager — manages Firefox Docker container lifecycle.

Handles container creation, connection setup, and cleanup with Traefik routing.
Uses linuxserver/firefox image, connects to codx-junior_default network,
and configures Traefik labels for routing without explicit port mappings.

Lifecycle semantics
-------------------
- ``stop_container(session, remove=True)``  : stop + remove (full teardown).
- ``stop_container(session, remove=False)`` : stop only — the container is kept
  so it can be started again with ``restart_container`` (state preserved).
- ``restart_container(session)``            : starts an existing (stopped)
  container, or recreates it if the container no longer exists.
"""

import logging
import os
import subprocess
import time
from typing import Optional, List
from pathlib import Path

from codx.junior.browser.model import BrowserSession

logger = logging.getLogger(__name__)


class DockerFirefoxManager:
    """
    Orchestrates Firefox Docker containers for browser automation.

    Each session gets a dedicated container with:
    - Traefik routing labels for VNC access (HTTP)
    - Chrome DevTools Protocol exposed on container port 9222
    - Connected to codx-junior_default network
    - Persistent profile volume for session state

    Docker image: lscr.io/linuxserver/firefox:latest
    Network: codx-junior_default (shared with codx-junior)
    """

    DOCKER_IMAGE = "lscr.io/linuxserver/firefox:latest"
    DOCKER_NETWORK = "codx-junior_default"
    MAX_SESSIONS = 10
    AUTH_MIDDLEWARE = "codx-junior-auth"

    def __init__(self, browser_sessions_path: str, traefik_domain: Optional[str] = None):
        """
        Initialize the Docker manager.

        Args:
            browser_sessions_path: Base path for browser session data (e.g., .codx/browser_sessions/)
            traefik_domain: Traefik domain for routing (e.g., app.example.com)
        """
        self.browser_sessions_path = browser_sessions_path
        self.traefik_domain = traefik_domain or os.environ.get("CODX_JUNIOR_DOMAIN", "localhost")
        os.makedirs(browser_sessions_path, exist_ok=True)
        logger.debug(
            "DockerFirefoxManager initialized at '%s' (domain: %s)",
            browser_sessions_path,
            self.traefik_domain,
        )

    # -------------------------------------------------------------------------
    # Container lifecycle
    # -------------------------------------------------------------------------

    def start_container(self, session: BrowserSession) -> BrowserSession:
        """
        Start a new Firefox Docker container for the session.

        Creates profile directory, starts container with Traefik labels,
        waits for readiness, then updates session with connection details.

        Args:
            session: BrowserSession with id set

        Returns:
            Updated BrowserSession with container_id and URLs

        Raises:
            RuntimeError: If container startup fails
        """
        session_folder = self._get_session_folder(session.id)
        profile_path = os.path.join(session_folder, "firefox_profile")
        os.makedirs(profile_path, exist_ok=True)

        container_name = f"browser_{session.id[:8]}"
        traefik_path_prefix = f"/browser/{session.id}"

        try:
            # Build traefik labels
            router_name = f"codx-junior-browser-{session.id[:8]}"
            traefik_labels = self._build_traefik_labels(
                router_name=router_name,
                session_id=session.id,
                path_prefix=traefik_path_prefix,
            )

            # Build docker run command
            cmd = [
                "docker",
                "run",
                "-d",  # detached mode
                "--name", container_name,
                "--network", self.DOCKER_NETWORK,
                "-e", "PUID=1000",
                "-e", "PGID=1000",
                "-e", "TZ=Etc/UTC",
                "-v", f"{profile_path}:/home/abc/.mozilla",  # Firefox profile
                "--shm-size=2gb",  # Prevent browser rendering crashes
            ]

            # Add traefik labels
            for label in traefik_labels:
                cmd.extend(["-l", label])

            cmd.append(self.DOCKER_IMAGE)

            logger.info(
                "Starting Firefox container: %s (network: %s, path: %s)",
                container_name,
                self.DOCKER_NETWORK,
                traefik_path_prefix,
            )
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                raise RuntimeError(f"Docker run failed: {result.stderr}")

            container_id = result.stdout.strip()
            logger.info("Container started: %s (ID: %s)", container_name, container_id[:12])

            # Wait for container to be ready
            self._wait_for_container_ready(container_id, timeout=15)

            # Update session with connection details
            session.container_id = container_id
            session.container_name = container_name
            session.browser_profile_path = profile_path
            session.traefik_domain = self.traefik_domain
            session.traefik_path_prefix = traefik_path_prefix
            session.vnc_url = f"http://{self.traefik_domain}{traefik_path_prefix}"
            session.debug_url = "ws://localhost:9222"  # Local development; adjust for production
            session.status = "running"
            session.error = None
            session.mark_active()

            return session

        except Exception as e:
            logger.exception("Failed to start Firefox container")
            session.status = "error"
            session.error = str(e)
            raise

    def stop_container(self, session: BrowserSession, remove: bool = True) -> None:
        """
        Stop a Firefox container, optionally removing it.

        Args:
            session: BrowserSession with container_id set
            remove: When True (default) the container is stopped **and removed**
                (full teardown). When False the container is only stopped so it
                can be started again with :meth:`restart_container`.
        """
        if not session or not session.container_id:
            logger.warning(
                "Cannot stop session %s: no container_id",
                session.id[:8] if session else "?",
            )
            return

        try:
            logger.info(
                "Stopping container: %s (remove=%s)", session.container_id[:12], remove
            )
            subprocess.run(
                ["docker", "stop", session.container_id],
                capture_output=True,
                timeout=15,
            )
            if remove:
                subprocess.run(
                    ["docker", "rm", session.container_id],
                    capture_output=True,
                    timeout=10,
                )
                session.container_id = None
            session.status = "stopped"
            logger.info("Container stopped: %s", session.container_id)
        except Exception as e:
            logger.exception("Error stopping container: %s", e)
            session.status = "error"
            session.error = f"Stop failed: {e}"

    def restart_container(self, session: BrowserSession) -> BrowserSession:
        """
        Restart a stopped session, recreating the container if needed.

        If the container still exists (previously stopped with
        ``stop_container(remove=False)``) it is simply started again, preserving
        the profile. If the container was removed, a fresh container is created
        from the same session folder (profile is preserved on disk).

        Args:
            session: BrowserSession to restart

        Returns:
            Updated BrowserSession

        Raises:
            RuntimeError: If restart fails
        """
        if session.container_id and self._container_exists(session.container_id):
            try:
                logger.info("Restarting container: %s", session.container_id[:12])
                subprocess.run(
                    ["docker", "start", session.container_id],
                    capture_output=True,
                    timeout=15,
                )
                self._wait_for_container_ready(session.container_id, timeout=15)
                session.status = "running"
                session.error = None
                session.mark_active()
                return session
            except Exception as e:
                logger.exception("Failed to restart existing container")
                session.status = "error"
                session.error = str(e)
                raise

        # Container gone → recreate it (profile on disk is preserved)
        logger.info("Container missing for session %s; recreating", session.id[:8])
        session.container_id = None
        return self.start_container(session)

    def remove_container(self, session: BrowserSession) -> None:
        """Stop and remove the container (alias of stop_container(remove=True))."""
        self.stop_container(session, remove=True)

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def _container_exists(self, container_id: str) -> bool:
        """Return True when the given container (id or name) still exists."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.Id}}", container_id],
                capture_output=True,
                text=True,
                timeout=5,
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
        Build Traefik Docker labels for routing.

        Args:
            router_name: Unique router name for this container
            session_id: Session ID
            path_prefix: URL path prefix (e.g., /browser/<session_id>)

        Returns:
            List of label strings for docker run -l flag
        """
        labels = [
            "traefik.enable=true",
            f"traefik.http.routers.{router_name}.rule=Host(`{self.traefik_domain}`) && PathPrefix(`{path_prefix}`)",
            f"traefik.http.routers.{router_name}.service={router_name}-service",
            f"traefik.http.services.{router_name}-service.loadbalancer.server.port=3000",
            f"traefik.http.services.{router_name}-service.loadbalancer.server.scheme=http",
            f"traefik.http.middlewares.{router_name}-path.replacepathregex.regex=^{path_prefix}/(.*)",
            f"traefik.http.middlewares.{router_name}-path.replacepathregex.replacement=/$1",
            f"traefik.http.routers.{router_name}.middlewares={router_name}-path,{self.AUTH_MIDDLEWARE}",
        ]
        return labels

    def _wait_for_container_ready(self, container_id: str, timeout: int = 15) -> None:
        """
        Wait for container to be ready (health check).

        Args:
            container_id: Docker container ID
            timeout: Maximum wait time in seconds

        Raises:
            TimeoutError: If container doesn't become ready in time
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["docker", "exec", container_id, "test", "-S", "/tmp/.X11-unix/X0"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    logger.debug("Container %s is ready", container_id[:12])
                    return
            except Exception:
                pass
            time.sleep(1)

        raise TimeoutError(f"Container {container_id[:12]} failed to become ready in {timeout}s")

    def cleanup_all_containers(self) -> None:
        """
        Stop all Firefox browser containers (cleanup on shutdown).
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "-q", "--filter", "name=browser_"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                container_ids = result.stdout.strip().split("\n")
                for cid in filter(None, container_ids):
                    try:
                        subprocess.run(
                            ["docker", "stop", cid],
                            capture_output=True,
                            timeout=5,
                        )
                        subprocess.run(
                            ["docker", "rm", cid],
                            capture_output=True,
                            timeout=5,
                        )
                        logger.info("Cleaned up container: %s", cid[:12])
                    except Exception as e:
                        logger.warning("Failed to cleanup container %s: %s", cid[:12], e)
        except Exception as e:
            logger.warning("Error during cleanup_all_containers: %s", e)