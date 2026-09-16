"""
WorkspaceManager — docker-compose based workspace lifecycle manager.

Each workspace lives in its own subdirectory under CODX_JUNIOR_WORKSPACES_FOLDER:

    <workspaces_root>/<workspace.folder_path>/
        docker-compose.yaml   ← user-managed, defines all services
        .env                  ← optional, injected into compose
        Dockerfile            ← optional, if building custom images
        ...

Traefik integration
-------------------
Services in docker-compose.yaml must declare Traefik labels themselves
OR use external URLs which are handled by the HTTP provider in traefik.py.

For container-port apps, users add labels like:
    - "traefik.enable=true"
    - "traefik.http.routers.<id>.rule=PathPrefix(`/ws/<slug>/<app>`)"
    - "traefik.http.services.<id>.loadbalancer.server.port=<port>"

This manager exposes helpers to inject those labels automatically when
workspace.apps is populated and the service name matches the app.
"""

import logging
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List
from uuid import uuid4
from datetime import datetime, timezone

from codx.junior.globals import CODX_JUNIOR_WORKSPACES_FOLDER
from codx.junior.global_settings import read_global_settings, write_global_settings, write_settings_section
from codx.junior.workspaces.model import Workspace, WorkspaceStatus

logger = logging.getLogger(__name__)

CODX_JUNIOR_DOMAIN = os.environ.get("CODX_JUNIOR_DOMAIN", "localhost")


class WorkspaceEngine:
    """Low-level filesystem helpers for a workspace directory."""

    def __init__(self, workspaces_root: Path):
        self.workspaces_root = workspaces_root

    def workspace_dir(self, workspace: Workspace) -> Path:
        """Absolute path to the workspace folder."""
        return (self.workspaces_root / workspace.folder_path).resolve()

    def compose_file(self, workspace: Workspace) -> Path:
        return self.workspace_dir(workspace) / "docker-compose.yaml"

    def ensure_dir(self, workspace: Workspace) -> Path:
        d = self.workspace_dir(workspace)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def destroy(self, workspace: Workspace) -> None:
        """Remove the workspace directory entirely."""
        d = self.workspace_dir(workspace)
        if d.exists():
            shutil.rmtree(d)
            logger.info("Removed workspace directory: %s", d)


class WorkspaceManager:
    """
    Manages workspace lifecycle using docker-compose.

    Each workspace is a folder containing a docker-compose.yaml and any
    support files (.env, Dockerfile, scripts, …).  Users are responsible
    for the content of those files; this manager only orchestrates
    start / stop / status / logs via the docker compose CLI.
    """

    def __init__(self, settings=None):
        # settings parameter kept for API compatibility; manager is global-settings-based
        self._workspaces_root = Path(CODX_JUNIOR_WORKSPACES_FOLDER)
        self._workspaces_root.mkdir(parents=True, exist_ok=True)
        self.engine = WorkspaceEngine(self._workspaces_root)

    # ------------------------------------------------------------------
    # Persistence helpers (read / write global settings)
    # ------------------------------------------------------------------

    def _load_all(self) -> List[Workspace]:
        return read_global_settings().workspaces or []

    def _save_all(self, workspaces: List[Workspace]) -> None:
        write_settings_section("workspaces", [w.dict() for w in workspaces])

    def _save_one(self, workspace: Workspace) -> None:
        all_ws = self._load_all()
        updated = [workspace if w.id == workspace.id else w for w in all_ws]
        if workspace.id not in {w.id for w in all_ws}:
            updated = all_ws + [workspace]
        self._save_all(updated)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def list_workspaces(self) -> List[Workspace]:
        return self._load_all()

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        return next((w for w in self._load_all() if w.id == workspace_id), None)

    def create_workspace(self, workspace: Workspace) -> Workspace:
        """
        Persist a new workspace and create its directory on disk.

        The caller supplies the workspace definition; we assign a fresh id
        and create the folder.  No docker-compose.yaml is written — the user
        provides that via the file API or direct upload.
        """
        if not workspace.folder_path:
            raise ValueError("workspace.folder_path is required")

        existing = self._load_all()
        if any(w.folder_path == workspace.folder_path for w in existing):
            raise ValueError(f"A workspace with folder_path '{workspace.folder_path}' already exists")

        workspace.id = workspace.id or str(uuid4())
        workspace.updated_at = datetime.now(timezone.utc).isoformat()
        workspace.status = WorkspaceStatus.STOPPED

        self.engine.ensure_dir(workspace)
        logger.info("Created workspace '%s' at %s", workspace.name, self.engine.workspace_dir(workspace))

        self._save_all(existing + [workspace])
        return workspace

    def update_workspace(self, workspace: Workspace, reprovision: bool = False) -> Workspace:
        """Update workspace metadata. reprovision=True re-runs directory setup."""
        workspace.updated_at = datetime.now(timezone.utc).isoformat()
        if reprovision:
            self.engine.ensure_dir(workspace)
        self._save_one(workspace)
        return workspace

    def delete_workspace(self, workspace_id: str) -> None:
        """Stop the workspace (if running), remove its directory, and delete from settings."""
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return
        try:
            self._compose_down(workspace)
        except Exception as ex:
            logger.warning("Could not stop workspace '%s' before deletion: %s", workspace_id, ex)
        self.engine.destroy(workspace)
        all_ws = [w for w in self._load_all() if w.id != workspace_id]
        self._save_all(all_ws)
        logger.info("Deleted workspace '%s'", workspace_id)

    # ------------------------------------------------------------------
    # Lifecycle (docker compose up / down)
    # ------------------------------------------------------------------

    def start_workspace(self, workspace_id: str) -> Workspace:
        """Run `docker compose up -d` in the workspace folder."""
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace '{workspace_id}' not found")

        compose_file = self.engine.compose_file(workspace)
        if not compose_file.exists():
            raise FileNotFoundError(
                f"docker-compose.yaml not found for workspace '{workspace.name}'. "
                "Upload one via the file API before starting."
            )

        workspace.status = WorkspaceStatus.STARTING
        self._save_one(workspace)

        try:
            self._compose_up(workspace)
            workspace.status = WorkspaceStatus.RUNNING
        except Exception as ex:
            workspace.status = WorkspaceStatus.ERROR
            logger.exception("Failed to start workspace '%s': %s", workspace_id, ex)
        finally:
            workspace.updated_at = datetime.now(timezone.utc).isoformat()
            self._save_one(workspace)

        return workspace

    def stop_workspace(self, workspace_id: str) -> Workspace:
        """Run `docker compose stop` in the workspace folder."""
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError(f"Workspace '{workspace_id}' not found")

        try:
            self._compose_down(workspace)
            workspace.status = WorkspaceStatus.STOPPED
        except Exception as ex:
            workspace.status = WorkspaceStatus.ERROR
            logger.exception("Failed to stop workspace '%s': %s", workspace_id, ex)
        finally:
            workspace.updated_at = datetime.now(timezone.utc).isoformat()
            self._save_one(workspace)

        return workspace

    def workspace_status(self, workspace_id: str) -> str:
        """Return current status by checking running containers via `docker compose ps`."""
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return WorkspaceStatus.STOPPED.value

        compose_file = self.engine.compose_file(workspace)
        if not compose_file.exists():
            return WorkspaceStatus.STOPPED.value

        try:
            result = self._run_compose(workspace, ["ps", "--services", "--filter", "status=running"])
            running_services = [s.strip() for s in result.stdout.strip().splitlines() if s.strip()]
            if running_services:
                return WorkspaceStatus.RUNNING.value
            return WorkspaceStatus.STOPPED.value
        except Exception as ex:
            logger.error("Error checking workspace status '%s': %s", workspace_id, ex)
            return WorkspaceStatus.ERROR.value

    def workspace_logs(self, workspace_id: str, tail: int = 200) -> str:
        """Return `docker compose logs --tail=N` output."""
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            return ""

        try:
            result = self._run_compose(workspace, ["logs", f"--tail={tail}", "--no-color"])
            return result.stdout or result.stderr or ""
        except Exception as ex:
            logger.error("Error fetching logs for workspace '%s': %s", workspace_id, ex)
            return str(ex)

    # ------------------------------------------------------------------
    # Internal docker compose helpers
    # ------------------------------------------------------------------

    def _compose_env(self, workspace: Workspace) -> dict:
        """Merge process env with workspace.env for compose subprocess."""
        env = {**os.environ}
        for k, v in (workspace.env or {}).items():
            env[k] = str(v)
        return env

    def _run_compose(self, workspace: Workspace, args: List[str]) -> subprocess.CompletedProcess:
        """
        Run `docker compose <args>` inside the workspace directory.
        Raises subprocess.CalledProcessError on non-zero exit.
        """
        workspace_dir = self.engine.workspace_dir(workspace)
        cmd = ["docker", "compose", "--project-name", workspace.compose_project] + args
        logger.debug("Running: %s (cwd=%s)", " ".join(cmd), workspace_dir)

        result = subprocess.run(
            cmd,
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            timeout=120,
            env=self._compose_env(workspace),
        )
        if result.returncode != 0:
            logger.error(
                "docker compose %s failed for workspace '%s':\n%s",
                args[0], workspace.name, result.stderr
            )
            raise subprocess.CalledProcessError(
                result.returncode, cmd, result.stdout, result.stderr
            )
        return result

    def _compose_up(self, workspace: Workspace) -> None:
        self._run_compose(workspace, ["up", "-d", "--remove-orphans"])

    def _compose_down(self, workspace: Workspace) -> None:
        self._run_compose(workspace, ["stop"])