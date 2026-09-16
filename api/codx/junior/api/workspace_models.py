"""
Workspace API — shared models, request/response schemas.

This module is the single source of truth for all payload and response
structures used by the Workspace API endpoints (``api/workspaces.py``).
Import everything workspace-related from here instead of reaching directly
into ``codx.junior.workspaces.model``.

Model hierarchy
---------------
::

    Workspace
    ├── id              str          Server-assigned UUID
    ├── name            str          Display name
    ├── description     str
    ├── template        str          "custom" | "static-site" | "dev-stack"
    ├── folder_path     str          Unique folder name under WORKSPACES_ROOT
    ├── project_ids     List[str]    Projects mounted into the workspace
    ├── user_ids        List[str]    Allowed usernames (empty = public)
    ├── apps            List[WorkspaceApp]
    │   ├── id          str
    │   ├── name        str
    │   ├── path        str          Public path prefix **or** external URL
    │   ├── port        int | None   Container port (docker-label routing)
    │   ├── scheme      "http"|"https"
    │   └── roles       List[str]   RBAC: empty = all roles
    ├── env             Dict[str,str]  Extra env vars passed to compose
    ├── resources       WorkspaceResources
    │   ├── cpus        str | None   e.g. "2"
    │   ├── memory      str | None   e.g. "4g"
    │   └── shm_size    str          default "512m"
    ├── use_sysbox      bool         Run with sysbox-runc
    ├── status          WorkspaceStatus  (server-managed)
    └── updated_at      str | None   ISO-8601 timestamp (server-managed)

Traefik routing — two modes
----------------------------
1. **Container-port apps** (``path`` is a plain path prefix, ``port`` is set):
   Users add Traefik labels directly in their ``docker-compose.yaml``::

       labels:
         - "traefik.enable=true"
         - "traefik.http.routers.myapp.rule=PathPrefix(`/ws/myws/myapp`)"
         - "traefik.http.services.myapp.loadbalancer.server.port=3000"
         - "traefik.http.routers.myapp.middlewares=codx-junior-auth"

2. **External-URL apps** (``path`` is ``http://`` or ``https://`` URL):
   The ``GET /api/traefik/config`` HTTP provider generates the route
   automatically.  The public path becomes ``/ws/{folder_path}/{app_id}``.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Re-export core models so consumers only need one import
from codx.junior.workspaces.model import (  # noqa: F401
    Workspace,
    WorkspaceApp,
    WorkspaceResources,
    WorkspaceStatus,
)


# ---------------------------------------------------------------------------
# Request / response schemas used by specific endpoints
# ---------------------------------------------------------------------------

class WorkspaceFileWriteRequest(BaseModel):
    """
    Body for ``POST /api/workspaces/{id}/file``.

    Writes (or overwrites) a file inside the workspace directory.
    Path traversal is blocked server-side — only paths within the workspace
    folder are accepted.

    Example::

        POST /api/workspaces/abc123/file?path=docker-compose.yaml
        {
            "content": "services:\\n  web:\\n    image: nginx\\n"
        }
    """

    content: str = Field(
        ...,
        description="Full UTF-8 text content to write to the file.",
        examples=["services:\n  web:\n    image: nginx\n"],
    )


class WorkspaceFileReadResponse(BaseModel):
    """
    Response for ``GET /api/workspaces/{id}/file``.

    Example::

        {
            "path": "docker-compose.yaml",
            "content": "services:\\n  web:\\n    image: nginx\\n"
        }
    """

    path: str = Field(..., description="Relative path inside the workspace directory.")
    content: str = Field(..., description="Full UTF-8 text content of the file.")


class WorkspaceFileWriteResponse(BaseModel):
    """Response for ``POST /api/workspaces/{id}/file``."""

    path: str = Field(..., description="Relative path that was written.")
    status: str = Field(default="saved", description="Always 'saved' on success.")


class WorkspaceStatusResponse(BaseModel):
    """
    Response for ``GET /api/workspaces/{id}/status``.

    Reflects the real-time container state by running ``docker compose ps``
    rather than reading the persisted ``Workspace.status`` field.

    Example::

        { "status": "running" }
    """

    status: str = Field(
        ...,
        description="One of: stopped | starting | running | error",
        examples=["running"],
    )


class WorkspaceLogsResponse(BaseModel):
    """
    Response for ``GET /api/workspaces/{id}/logs``.

    Returns combined stdout + stderr from ``docker compose logs``.

    Example::

        { "logs": "web_1  | Server listening on port 3000\\ndb_1   | ready\\n" }
    """

    logs: str = Field(
        ...,
        description="Raw log output from all containers in the workspace.",
    )


class WorkspaceDeleteResponse(BaseModel):
    """Response for ``DELETE /api/workspaces/{id}``."""

    status: str = Field(default="deleted")


