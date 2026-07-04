from pydantic import BaseModel, Field
from typing import List, Optional


class WorkspaceApp(BaseModel):
    id: str = Field(default="")
    name: str = Field(default="")
    description: str = Field(default="")
    icon: str = Field(default="")
    path: str = Field(default="")
    port: Optional[str] = Field(default="")
    is_vnc: Optional[bool] = Field(default=False)
    container_name: str = Field(default="")
    roles: List[str] = Field(default=[])


class Workspace(BaseModel):
    id: str = Field(default="")
    name: str = Field(default="")
    description: str = Field(default="")
    project_ids: List[str] = Field(default=[])
    apps: Optional[List[WorkspaceApp]] = Field(default=[])
    updated_at: Optional[str] = Field(default=None)
    folder_path: str = Field(default="", description="Folder name under CODX_JUNIOR_WORKSPACES_FOLDER where workspace files are stored")
    user_ids: Optional[List[str]] = Field(default=[], description="Allowed user accounts (empty means all users)")


DEFAULT_WORKSPACE = Workspace(**{
    "name": "codx-junior",
    "description": "Default codx-junior workspace",
    "folder_path": "codx-junior-workspace-default",
    "apps": [
        { 
        "icon": "fa-solid fa-code",
        "name": "Coder",
        "description": "Coder coding environment",
        "path": "/workspace-default/coder/",
        "roles": ["admin"]
        },
        { 
        "icon": "fa-solid fa-desktop",
        "name": "Desktop",
        "description": "Virtual desktop",
        "path": "/workspace-default/preview/index.html",
        "roles": ["admin"]
        },
        { 
        "icon": "https://framerusercontent.com/images/GtfMdzyrMj6FQY6lGLqI6bh2LYM.png",
        "name": "LiteLLM",
        "description": "LiteLLM Models manager",
        "path": "/litellm/ui",
        "roles": ["admin"]
        },
    ],
    "project_ids": ["*"]
})