"""
DockerFirefoxManager — manages Firefox Docker container lifecycle.

Handles container creation, connection setup, and cleanup with Traefik routing.
Uses linuxserver/firefox image, connects to codx-junior_default network,
and configures Traefik labels for routing without explicit port mappings.
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

    Docker image: linuxserver/firefox
    Network: codx-junior_default (shared with codx-junior)
    """

    DOCKER_IMAGE = "lscr.io/linuxserver/firefox:latest"
    DOCKER_NETWORK = "codx-junior_default"
    MAX_SESSIONS = 10

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
            self.traefik_domain
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
                path_prefix=traefik_path_prefix
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
                traefik_path_prefix
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
            session.debug_url = f"ws://localhost:9222"  # Local development; adjust for production
            session.status = "running"
            session.error = None
            session.mark_active()

            return session

        except Exception as e:
            logger.exception("Failed to start Firefox container")
            session.status = "error"
            session.error = str(e)
            raise

    def stop_container(self, session: BrowserSession) -> None:
        """
        Stop and remove a Firefox container.

        Args:
            session: BrowserSession with container_id set
        """
        if not session.container_id:
            logger.warning("Cannot stop session %s: no container_id", session.id[:8])
            return

        try:
            logger.info("Stopping container: %s", session.container_id[:12])
            subprocess.run(
                ["docker", "stop", session.container_id],
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ["docker", "rm", session.container_id],
                capture_output=True,
                timeout=10,
            )
            session.status = "stopped"
            logger.info("Container stopped: %s", session.container_id[:12])
        except Exception as e:
            logger.exception("Error stopping container %s: %s", session.container_id[:12], e)
            session.status = "error"
            session.error = f"Stop failed: {e}"

    def restart_container(self, session: BrowserSession) -> BrowserSession:
        """
        Restart an existing container (preserves profile).

        Args:
            session: BrowserSession with container_id set

        Returns:
            Updated BrowserSession

        Raises:
            RuntimeError: If restart fails
        """
        if not session.container_id:
            raise RuntimeError("Cannot restart: no container_id")

        try:
            logger.info("Restarting container: %s", session.container_id[:12])
            subprocess.run(
                ["docker", "start", session.container_id],
                capture_output=True,
                timeout=10,
            )
            self._wait_for_container_ready(session.container_id, timeout=15)
            session.status = "running"
            session.error = None
            session.mark_active()
            return session
        except Exception as e:
            logger.exception("Failed to restart container")
            session.status = "error"
            session.error = str(e)
            raise

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

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
        path_prefix: str
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
            f"traefik.http.routers.{router_name}.middlewares={router_name}-path",
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