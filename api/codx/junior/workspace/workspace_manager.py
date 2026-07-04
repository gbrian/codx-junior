import logging
import subprocess
import json
import shutil
from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime

from codx.junior.model.model import Workspace
from codx.junior.global_settings import read_global_settings
from codx.junior.engine import find_all_projects
from codx.junior.globals import CODX_JUNIOR_WORKSPACES_FOLDER, CODX_JUNIOR_DEFAULT_WORKSPACE_PATH

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages workspace lifecycle including Docker container orchestration and file generation."""

    def __init__(self):
        self.global_settings = read_global_settings()
        self.workspaces = self.global_settings.workspaces
        self.all_projects = find_all_projects()
        self.workspaces_folder = Path(CODX_JUNIOR_WORKSPACES_FOLDER)
        self.default_template_path = Path(CODX_JUNIOR_DEFAULT_WORKSPACE_PATH)

    def create_workspace_files(self, workspace: Workspace) -> bool:
        """
        Create workspace directory and copy default template files.
        
        Copies all files from CODX_JUNIOR_DEFAULT_WORKSPACE_PATH to the new workspace folder.
        This includes Dockerfile, docker-compose.yaml, .env, and any other template files.
        
        Args:
            workspace: Workspace model instance
            
        Returns:
            True if successful, False otherwise
        """
        try:
            workspace_dir = self.workspaces_folder / workspace.folder_path
            
            # Create workspace directory
            workspace_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Created workspace directory at %s", workspace_dir)
            
            # Copy default template files if template path exists
            if self.default_template_path.exists():
                if self.default_template_path.is_dir():
                    # Copy all files from template directory
                    for template_file in self.default_template_path.iterdir():
                        if template_file.is_file():
                            dest_file = workspace_dir / template_file.name
                            shutil.copy2(template_file, dest_file)
                            logger.info("Copied template file '%s' to workspace at %s", template_file.name, dest_file)
                        elif template_file.is_dir():
                            # Copy subdirectories recursively
                            dest_dir = workspace_dir / template_file.name
                            if dest_dir.exists():
                                shutil.rmtree(dest_dir)
                            shutil.copytree(template_file, dest_dir)
                            logger.info("Copied template directory '%s' to workspace at %s", template_file.name, dest_dir)
                    
                    logger.info("Successfully copied all template files for workspace '%s'", workspace.name)
                else:
                    logger.warning("Default template path exists but is not a directory: %s", self.default_template_path)
                    return False
            else:
                logger.warning("Default template path does not exist: %s", self.default_template_path)
                logger.info("Created empty workspace directory for '%s' at %s", workspace.name, workspace_dir)
            
            return True
            
        except Exception as e:
            logger.error("Failed to create workspace files for '%s': %s", workspace.name, str(e))
            return False

    def synchronize_workspaces(self):
        """Synchronize workspace containers with configured workspaces."""
        current_containers = self.get_running_containers()

        for workspace in self.workspaces:
            if workspace.id not in current_containers:
                self.create_workspace_container(workspace)
            elif not self.is_workspace_up_to_date(workspace, current_containers[workspace.id]):
                self.remove_workspace_container(workspace)
                self.create_workspace_container(workspace)

        self.detect_changes(current_containers)

    def get_running_containers(self) -> Dict[str, dict]:
        """Get all running Docker containers labeled with workspace-id."""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "label=workspace-id", "--format", "{{json .}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.warning("Failed to get running containers: %s", result.stderr)
                return {}
            
            containers = {}
            for line in result.stdout.strip().split("\n"):
                if line:
                    try:
                        container_data = json.loads(line)
                        workspace_id = container_data.get("Labels", {}).get("workspace-id")
                        if workspace_id:
                            containers[workspace_id] = container_data
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse container data: %s", line)
            
            return containers
        except Exception as e:
            logger.error("Error getting running containers: %s", str(e))
            return {}

    def inspect_container(self, container_name: str) -> Optional[dict]:
        """Inspect a Docker container by name."""
        try:
            result = subprocess.run(
                ["docker", "inspect", container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                container_info = json.loads(result.stdout)
                return container_info[0] if container_info else None
            return None
        except Exception as e:
            logger.error("Error inspecting container '%s': %s", container_name, str(e))
            return None

    def is_workspace_up_to_date(self, workspace: Workspace, container_data: dict) -> bool:
        """Check if container configuration matches workspace configuration."""
        try:
            labels = container_data.get("Labels", {})
            container_updated_at = labels.get("updated_at")
            return container_updated_at == workspace.updated_at
        except Exception as e:
            logger.error("Error checking workspace update status: %s", str(e))
            return False

    def create_workspace_container(self, workspace: Workspace):
        """Create and start a Docker container for a workspace."""
        try:
            container_name = workspace.name.replace(" ", "_").lower()
            image_name = "codxjunior/codx-junior-default-workspace:latest"
            shm_size = "4g"
            restart_policy = "unless-stopped"

            docker_command = [
                "docker", "run", "-d",
                "--name", container_name,
                "--label", f"workspace-id={workspace.id}",
                "--label", f"updated_at={workspace.updated_at or datetime.now().isoformat()}",
                "--shm-size", shm_size,
                "--restart", restart_policy,
                image_name
            ]

            result = subprocess.run(docker_command, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("Created workspace container '%s' for workspace '%s'", container_name, workspace.name)
            else:
                logger.error("Failed to create workspace container '%s': %s", container_name, result.stderr)
                
        except Exception as e:
            logger.error("Error creating workspace container for '%s': %s", workspace.name, str(e))

    def get_workspace_paths(self, workspace: Workspace) -> List[Path]:
        """Get project paths for all projects in a workspace."""
        def get_project_path(project_id):
            return next((p for p in self.all_projects if p.project_id == project_id), None)
        
        return [get_project_path(project_id) for project_id in workspace.project_ids if project_id != "*"]

    def remove_workspace_container(self, workspace: Workspace):
        """Remove a workspace Docker container."""
        try:
            container_name = workspace.name.replace(" ", "_").lower()
            result = subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Removed workspace container '%s'", container_name)
            else:
                logger.warning("Failed to remove workspace container '%s': %s", container_name, result.stderr)
        except Exception as e:
            logger.error("Error removing workspace container for '%s': %s", workspace.name, str(e))

    def detect_changes(self, current_containers: Dict[str, dict]):
        """Detect and handle changes in workspace configurations."""
        for workspace in self.workspaces:
            if workspace.id not in current_containers:
                logger.info("Workspace '%s' not found in running containers, creating...", workspace.name)
                self.create_workspace_container(workspace)
            else:
                container_data = current_containers[workspace.id]
                if not self.is_workspace_up_to_date(workspace, container_data):
                    logger.info("Workspace '%s' is outdated, updating...", workspace.name)
                    self.remove_workspace_container(workspace)
                    self.create_workspace_container(workspace)