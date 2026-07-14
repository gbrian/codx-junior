from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator


class WorkspaceStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


class WorkspaceResources(BaseModel):
    cpus: Optional[str] = Field(default=None, description="CPU limit, e.g. '2'")
    memory: Optional[str] = Field(default=None, description="Memory limit, e.g. '4g'")
    shm_size: Optional[str] = Field(default="512m")


class WorkspaceApp(BaseModel):
    id: str = Field(default="")
    name: str = Field(default="")
    description: str = Field(default="")
    icon: str = Field(default="")
    path: str = Field(default="", description="Public path prefix routed by Traefik")
    port: Optional[int] = Field(default=None, description="Container port serving this app")
    scheme: str = Field(default="http", description="http or https (e.g. Kasm VNC uses https)")
    is_vnc: Optional[bool] = Field(default=False)
    container_name: str = Field(default="", description="Kept for backward compatibility")
    roles: List[str] = Field(default=[])

    @field_validator("port", mode="before")
    @classmethod
    def _coerce_port(cls, value):
        # Legacy persisted data stores port as str, sometimes ""
        if value in ("", None):
            return None
        return int(value)

class Workspace(BaseModel):
    id: str = Field(default="")
    name: str = Field(default="")
    description: str = Field(default="")
    template: str = Field(default="custom", description="Template id: static-site | dev-stack | custom")
    folder_path: str = Field(default="", description="Folder name under CODX_JUNIOR_WORKSPACES_FOLDER")
    project_ids: List[str] = Field(default=[], description="Projects mounted into the workspace")
    user_ids: List[str] = Field(default=[], description="Allowed users (empty = all users)")
    apps: List[WorkspaceApp] = Field(default=[])
    env: Dict[str, str] = Field(default={}, description="Extra environment variables")
    resources: WorkspaceResources = Field(default_factory=WorkspaceResources)
    use_sysbox: bool = Field(default=False, description="Run with sysbox-runc (systemd + inner Docker)")
    status: WorkspaceStatus = Field(default=WorkspaceStatus.STOPPED)
    updated_at: Optional[str] = Field(default=None)

    @property
    def slug(self) -> str:
        return self.folder_path

    @property
    def network_name(self) -> str:
        return f"codx-ws-{self.folder_path}"

    @property
    def compose_project(self) -> str:
        return f"codx-ws-{self.folder_path}"        