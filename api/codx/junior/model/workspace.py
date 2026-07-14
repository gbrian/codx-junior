# Compatibility shim: models moved to codx.junior.workspaces.model
from codx.junior.workspaces.model import (
    Workspace,
    WorkspaceApp,
    WorkspaceResources,
    WorkspaceStatus,
)

DEFAULT_WORKSPACE = Workspace(**{
    "name": "codx-junior",
    "description": "Default codx-junior workspace",
    "folder_path": "codx-junior-workspace-default",
    "template": "custom",
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