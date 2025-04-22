import logging
import subprocess
from typing import List
from codx.junior.model.model import Workspace
from codx.junior.settings import get_model_settings, get_provider_settings
from codx.junior.engine import find_all_projects

logger = logging.getLogger(__name__)

class WorkspaceManager:
    def __init__(self):
        self.global_settings = read_global_settings()
        self.workspaces = self.global_settings.workspaces
        self.all_projects = find_all_projects()

    def synchronize_workspaces(self):
        current_containers = self.get_running_containers()

        for workspace in self.workspaces:
            if workspace.id not in current_containers:
                self.create_workspace(workspace)
            elif not self.is_workspace_up_to_date(workspace, current_containers[workspace.id]):
                self.remove_workspace(workspace)
                self.create_workspace(workspace)

        self.detect_changes(current_containers)

    def get_running_containers(self) -> dict:
        result = subprocess.run(
            ["docker", "ps", "--filter", "label=workspace-id", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        container_list = result.stdout.strip().split("\n")
        return {container_name: self.inspect_container(container_name) for container_name in container_list}

    def inspect_container(self, container_name: str) -> dict:
        result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            text=True
        )
        container_details = result.stdout
        return container_details

    def is_workspace_up_to_date(self, workspace: Workspace, container_config: dict) -> bool:
        container_labels = container_config.get("Config", {}).get("Labels", {})
        container_updated_at = container_labels.get("updated_at")
        return container_updated_at == workspace.updated_at

    def create_workspace(self, workspace: Workspace):
        container_name = workspace.name.replace(" ", "_")
        image_name = "codx-junior:latest"
        shm_size = "4g"
        restart_policy = "unless-stopped"

        docker_command = [
            "docker", "run", "-d",
            "--name", container_name,
            "--label", f"workspace-id={workspace.id}",
            "--label", f"updated_at={workspace.updated_at}",
            "--shm-size", shm_size,
            "--restart", restart_policy
        ]

        # Additional logic to handle environment variables, volume mappings, etc.

        docker_command.append(image_name)
        subprocess.run(docker_command)

    def get_workspace_paths(self, workspace: Workspace):
        def get_project_path(project_id):
            return next((p for p in self.all_projects if p.project_id == project_id), None)
        return [get_project_path(project_id) for project_id in workspace.project_ids]

    def remove_workspace(self, workspace: Workspace):
        subprocess.run(["docker", "rm", "-f", workspace.name.replace(" ", "_")])

    def detect_changes(self, current_containers: dict):
        for workspace in self.workspaces:
            if workspace.id not in current_containers:
                self.create_workspace(workspace)
            else:
                self.remove_workspace(workspace)
                self.create_workspace(workspace)
