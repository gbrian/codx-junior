"""
Traefik dynamic configuration provider + custom-rule maintenance API.

Traefik's ``providers.http`` polls ``GET /api/traefik/config`` every
``pollInterval`` seconds.  That endpoint is intentionally unauthenticated (it
must be reachable by the Traefik container on the internal network) and is
served from the project-rules snapshot, so it never waits for project
discovery.

The maintenance endpoints (``/traefik/routes``, ``/traefik/targets`` and the
global/project rule stores) are admin-only.

Storage
-------
* global rules -> ``GlobalSettings.traefik_rules``
* project rules -> ``CODXJuniorSettings.traefik_rules`` (``.codx/project.json``)

Both stores use the same ``TraefikRule`` model and the same UI component.

Endpoints
---------
GET    /api/traefik/config                       – HTTP provider (no auth)
GET    /api/traefik/routes                       – merged route read model
GET    /api/traefik/targets                      – workspace apps + containers
GET    /api/traefik/global/rules                 – global custom rules
PUT    /api/traefik/global/rules                 – replace global custom rules
GET    /api/traefik/projects/{project_id}/rules  – project custom rules
PUT    /api/traefik/projects/{project_id}/rules  – replace project custom rules
GET    /api/traefik/preview                      – generated config preview
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from codx.junior.api import require_admin
from codx.junior.model.model import CodxUser
from codx.junior.traefik import manager
from codx.junior.traefik.model import TraefikRule

logger = logging.getLogger(__name__)

router = APIRouter(tags=["traefik"])


class TraefikRulesRequest(BaseModel):
    """Body for the bulk rule-save endpoints."""

    rules: List[TraefikRule] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rules_payload(rules: List[TraefikRule]) -> dict:
    return {"rules": [rule.model_dump(mode="json") for rule in rules]}


def _value_error(ex: ValueError) -> HTTPException:
    message = str(ex)
    status = 404 if "not found" in message.lower() else 400
    return HTTPException(status_code=status, detail=message)


# ---------------------------------------------------------------------------
# HTTP provider
# ---------------------------------------------------------------------------


@router.get(
    "/traefik/config",
    summary="Traefik HTTP provider – dynamic configuration",
    include_in_schema=False,
)
def traefik_dynamic_config():
    """
    Polled by Traefik's ``providers.http`` every ``pollInterval``.

    Returns a Traefik-compatible dynamic configuration built from:

    * external-URL workspace apps;
    * global custom rules;
    * every project's custom rules (through a non-blocking snapshot).
    """
    try:
        return JSONResponse(content=manager.build_config())
    except Exception as ex:
        logger.exception("Error building Traefik dynamic config: %s", ex)
        # Return an empty-but-valid config so Traefik doesn't error out
        return JSONResponse(content={"http": {}})


# ---------------------------------------------------------------------------
# Maintenance UI
# ---------------------------------------------------------------------------


@router.get(
    "/traefik/routes",
    summary="[Admin] Merged workspace and custom Traefik routes",
)
def list_traefik_routes(
    project_id: Optional[str] = None,
    refresh: bool = False,
    user: CodxUser = Depends(require_admin),
):
    """
    Human-readable, merged view of every route Traefik can see.

    ``project_id`` scopes the view to one project: its rules become editable,
    global rules are inherited read-only, and workspace routes are filtered to
    the workspaces that mount the project.
    """
    try:
        view = manager.build_view(project_id=project_id, refresh=refresh)
    except ValueError as ex:
        raise _value_error(ex)
    # The route list does not need the full dynamic config; keep the payload
    # small. `preview` returns it for the debug modal.
    view.pop("config", None)
    return view


@router.get(
    "/traefik/targets",
    summary="[Admin] Targets available to a custom Traefik rule",
)
def list_traefik_targets(user: CodxUser = Depends(require_admin)):
    """Workspace apps, running containers and defaults for the rule editor."""
    return manager.target_catalog()


@router.get(
    "/traefik/preview",
    summary="[Admin] Preview the generated Traefik dynamic configuration",
)
def preview_traefik_config(
    project_id: Optional[str] = None,
    refresh: bool = False,
    user: CodxUser = Depends(require_admin),
):
    """Return the generated config, the route list and the issue list."""
    try:
        return manager.preview(project_id=project_id, refresh=refresh)
    except ValueError as ex:
        raise _value_error(ex)


# ---------------------------------------------------------------------------
# Rule stores
# ---------------------------------------------------------------------------


@router.get(
    "/traefik/global/rules",
    summary="[Admin] List global custom Traefik rules",
)
def get_global_traefik_rules(user: CodxUser = Depends(require_admin)):
    return _rules_payload(manager.get_global_rules())


@router.put(
    "/traefik/global/rules",
    summary="[Admin] Replace global custom Traefik rules",
)
def save_global_traefik_rules(
    body: TraefikRulesRequest,
    user: CodxUser = Depends(require_admin),
):
    try:
        rules = manager.save_global_rules(body.rules)
    except ValueError as ex:
        raise _value_error(ex)
    logger.info("Admin '%s' saved %d global Traefik rule(s)", user.username, len(rules))
    return _rules_payload(rules)


@router.get(
    "/traefik/projects/{project_id}/rules",
    summary="[Admin] List a project's custom Traefik rules",
)
def get_project_traefik_rules(
    project_id: str,
    user: CodxUser = Depends(require_admin),
):
    try:
        rules = manager.get_project_rules(project_id)
    except ValueError as ex:
        raise _value_error(ex)
    return _rules_payload(rules)


@router.put(
    "/traefik/projects/{project_id}/rules",
    summary="[Admin] Replace a project's custom Traefik rules",
)
def save_project_traefik_rules(
    project_id: str,
    body: TraefikRulesRequest,
    user: CodxUser = Depends(require_admin),
):
    try:
        rules = manager.save_project_rules(project_id, body.rules)
    except ValueError as ex:
        raise _value_error(ex)
    logger.info(
        "Admin '%s' saved %d Traefik rule(s) for project %s",
        user.username,
        len(rules),
        project_id,
    )
    return _rules_payload(rules)
