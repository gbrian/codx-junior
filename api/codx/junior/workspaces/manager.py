import json
import logging
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from typing import List, Optional

from codx.junior.settings import CODXJuniorSettings
from codx.junior.workspaces.model import Workspace, WorkspaceStatus
from codx.junior.workspaces.engines.base import WorkspaceEngine
from codx.junior.workspaces.engines.compose import DockerComposeEngine

logger = logging.getLogger(__name__)

WORKSPACE_METADATA_FILE = "workspace.json"


class WorkspaceManager:
    """Workspace orchestration façade: persistence + engine lifecycle.

    Workspaces belong to a project and are stored under
    [project_path]/.codx/workspaces (same pattern as ProfileManager).
    Each workspace lives in its own folder holding both its metadata
    (workspace.json) and its runtime files (docker-compose.yaml, ...).
    """

    def __init__(self, settings: CODXJuniorSettings, engine: Optional[WorkspaceEngine] = None):
        self.settings = settings
        self.workspaces_path = Path(f"{settings.codx_path}/workspaces")
        os.makedirs(self.workspaces_path, exist_ok=True)
        self.engine = engine or DockerComposeEngine(workspaces_folder=self.workspaces_path)

    # -- persistence ----------------------------------------------------

    def _metadata_file(self, workspace: Workspace) -> Path:
        return self.workspaces_path / workspace.folder_path / WORKSPACE_METADATA_FILE

    def list_workspaces(self) -> List[Workspace]:
        workspaces = []
        for metadata_file in self.workspaces_path.glob(f"*/{WORKSPACE_METADATA_FILE}"):
            try:
                workspaces.append(Workspace(**json.loads(metadata_file.read_text())))
            except Exception as ex:
                logger.exception("Error loading workspace: %s %s", metadata_file, ex)
        return workspaces

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        return next((w for w in self.list_workspaces() if w.id == workspace_id), None)

    def _save(self, workspace: Workspace) -> None:
        workspace.updated_at = datetime.now().isoformat()
        metadata_file = self._metadata_file(workspace)
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        metadata_file.write_text(json.dumps(workspace.model_dump(), indent=2))

    # -- lifecycle ------------------------------------------------------

    def create_workspace(self, workspace: Workspace) -> Workspace:
        if any(w.folder_path == workspace.folder_path for w in self.list_workspaces()):
            raise ValueError(f"Workspace folder_path '{workspace.folder_path}' already exists")
        workspace.id = workspace.id or str(uuid4())
        self.engine.provision(workspace)
        self._save(workspace)
        logger.info("Workspace '%s' created (template=%s)", workspace.name, workspace.template)
        return workspace

    def update_workspace(self, workspace: Workspace, reprovision: bool = False) -> Workspace:
        if reprovision:
            self.engine.provision(workspace)
        self._save(workspace)
        return workspace

    def delete_workspace(self, workspace_id: str) -> None:
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")
        # engine.destroy removes the workspace folder (metadata included)
        self.engine.destroy(workspace)

    def start_workspace(self, workspace_id: str) -> Workspace:
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")
        self.engine.start(workspace)
        workspace.status = self.engine.status(workspace)
        self._save(workspace)
        return workspace

    def stop_workspace(self, workspace_id: str) -> Workspace:
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")
        self.engine.stop(workspace)
        workspace.status = WorkspaceStatus.STOPPED
        self._save(workspace)
        return workspace

    def workspace_status(self, workspace_id: str) -> WorkspaceStatus:
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")
        return self.engine.status(workspace)

    def workspace_logs(self, workspace_id: str, tail: int = 200) -> str:
        workspace = self.get_workspace(workspace_id)
        if not workspace:
            raise ValueError("Workspace not found")
        return self.engine.logs(workspace, tail=tail)