import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import List

from codx.junior.workspaces.model import Workspace, WorkspaceApp, WorkspaceStatus
from codx.junior.workspaces.engines.base import WorkspaceEngine

logger = logging.getLogger(__name__)

# Traefik container that must join each workspace network to route apps.
TRAEFIK_CONTAINER_NAME = "codx-junior-traefik"


class DockerComposeEngine(WorkspaceEngine):
    """Runs each workspace as an isolated docker compose project."""

    def __init__(self, workspaces_folder: Path):
        self.workspaces_folder = Path(workspaces_folder)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def workspace_dir(self, workspace: Workspace) -> Path:
        return self.workspaces_folder / workspace.folder_path

    def _compose(self, workspace: Workspace, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
        cmd = [
            "docker", "compose",
            "-p", workspace.compose_project,
            "-f", str(self.workspace_dir(workspace) / "docker-compose.yaml"),
            *args,
        ]
        logger.info("Workspace '%s': %s", workspace.slug, " ".join(cmd))
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              cwd=self.workspace_dir(workspace))

    def _connect_traefik(self, workspace: Workspace) -> None:
        """Attach the Traefik container to the workspace network so apps are routable."""
        subprocess.run(
            ["docker", "network", "connect", workspace.network_name, TRAEFIK_CONTAINER_NAME],
            capture_output=True, text=True, timeout=15,
        )  # idempotent: fails silently if already connected

    def _disconnect_traefik(self, workspace: Workspace) -> None:
        subprocess.run(
            ["docker", "network", "disconnect", workspace.network_name, TRAEFIK_CONTAINER_NAME],
            capture_output=True, text=True, timeout=15,
        )

    @staticmethod
    def traefik_labels(workspace: Workspace, app: WorkspaceApp) -> List[str]:
        """Generate Traefik routing labels for a workspace app."""
        rid = f"codx-ws-{workspace.slug}-{app.id or app.name.lower().replace(' ', '-')}"
        prefix = app.path.rstrip("/")
        labels = [
            "traefik.enable=true",
            f"traefik.http.routers.{rid}.rule=PathPrefix(`{prefix}`)",
            f"traefik.http.routers.{rid}.service={rid}",
            f"traefik.http.services.{rid}.loadbalancer.server.port={app.port}",
            f"traefik.http.middlewares.{rid}-strip.replacepathregex.regex=^{prefix}/(.*)",
            f"traefik.http.middlewares.{rid}-strip.replacepathregex.replacement=/$$1",
            f"traefik.http.routers.{rid}.middlewares={rid}-strip,codx-junior-auth",
        ]
        if app.scheme == "https":
            labels.append(f"traefik.http.services.{rid}.loadbalancer.server.scheme=https")
        return labels

    # ------------------------------------------------------------------
    # WorkspaceEngine implementation
    # ------------------------------------------------------------------

    def provision(self, workspace: Workspace) -> None:
        from codx.junior.workspaces.templates import render_template
        render_template(workspace, self.workspace_dir(workspace))

    def start(self, workspace: Workspace) -> None:
        result = self._compose(workspace, "up", "-d", "--build", timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start workspace '{workspace.slug}': {result.stderr}")
        self._connect_traefik(workspace)

    def stop(self, workspace: Workspace) -> None:
        result = self._compose(workspace, "stop")
        if result.returncode != 0:
            raise RuntimeError(f"Failed to stop workspace '{workspace.slug}': {result.stderr}")

    def destroy(self, workspace: Workspace) -> None:
        self._disconnect_traefik(workspace)
        self._compose(workspace, "down", "-v", "--remove-orphans")
        workspace_dir = self.workspace_dir(workspace)
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)

    def status(self, workspace: Workspace) -> WorkspaceStatus:
        result = self._compose(workspace, "ps", "--format", "json", timeout=15)
        if result.returncode != 0:
            return WorkspaceStatus.ERROR
        states = []
        for line in result.stdout.strip().splitlines():
            try:
                states.append(json.loads(line).get("State", ""))
            except json.JSONDecodeError:
                continue
        if not states:
            return WorkspaceStatus.STOPPED
        if all(s == "running" for s in states):
            return WorkspaceStatus.RUNNING
        if any(s in ("restarting", "created") for s in states):
            return WorkspaceStatus.STARTING
        return WorkspaceStatus.ERROR

    def logs(self, workspace: Workspace, tail: int = 200) -> str:
        result = self._compose(workspace, "logs", "--tail", str(tail), timeout=30)
        return result.stdout or result.stderr