"""
Persistence and read-model orchestration for custom Traefik rules.

The same rule model is stored in two places:

* ``GlobalSettings.traefik_rules`` for global rules;
* ``CODXJuniorSettings.traefik_rules`` (``.codx/project.json``) for project
  rules.

The API exposes bulk save endpoints (`PUT .../rules`) and this module is the
single place that validates, normalizes and persists a rule list.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from codx.junior.global_settings import read_global_settings, write_settings_section
from codx.junior.project.project_discover import find_project_by_id
from codx.junior.traefik.builder import (
    DEFAULT_AUTH_MIDDLEWARE,
    DEFAULT_DOMAIN,
    DEFAULT_ENTRYPOINTS,
    build_traefik,
    is_external_url,
    public_path,
    sanitize_id,
    validate_rule_structure,
    workspace_app_key,
)
from codx.junior.traefik.docker import list_running_containers
from codx.junior.traefik.model import TraefikRule
from codx.junior.traefik.project_cache import (
    get_project_rule_sets,
    refresh_project_rules,
    update_project_rules,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validation / normalization
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_rules(rules: Optional[List[TraefikRule]]) -> List[TraefikRule]:
    """
    Validate and normalize a rule list before persisting it.

    * assigns ids to new rules;
    * rejects duplicate (or duplicate-after-sanitization) ids;
    * fills timestamps;
    * rejects structurally invalid rules with a readable message.
    """
    normalized: List[TraefikRule] = []
    seen_ids = set()
    seen_router_keys = set()
    problems: List[str] = []

    for index, rule in enumerate(rules or []):
        if isinstance(rule, dict):
            rule = TraefikRule(**rule)

        if not (rule.id or "").strip():
            rule.id = uuid4().hex[:12]
        rule.id = rule.id.strip()

        if rule.id in seen_ids:
            problems.append(f"Duplicate rule id '{rule.id}'")
            continue
        router_key = sanitize_id(rule.id)
        if router_key in seen_router_keys:
            problems.append(f"Duplicate rule id after normalization '{rule.id}'")
            continue
        seen_ids.add(rule.id)
        seen_router_keys.add(router_key)

        issues = validate_rule_structure(rule)
        if issues:
            label = rule.name or rule.id or f"rule {index + 1}"
            problems.extend(f"{label}: {issue}" for issue in issues)
            continue

        if not rule.created_at:
            rule.created_at = _now()
        rule.updated_at = _now()
        normalized.append(rule)

    if problems:
        raise ValueError("; ".join(problems))
    return normalized


# ---------------------------------------------------------------------------
# Read / write stores
# ---------------------------------------------------------------------------


def get_global_rules() -> List[TraefikRule]:
    return list(read_global_settings().traefik_rules or [])


def save_global_rules(rules: Optional[List[TraefikRule]]) -> List[TraefikRule]:
    normalized = normalize_rules(rules)
    write_settings_section(
        "traefik_rules",
        [rule.model_dump(mode="json") for rule in normalized],
    )
    logger.info("Saved %d global Traefik rule(s)", len(normalized))
    return normalized


def get_project_rules(project_id: str) -> List[TraefikRule]:
    settings = find_project_by_id(project_id)
    if settings is None:
        raise ValueError(f"Project '{project_id}' not found")
    return list(settings.traefik_rules or [])


def save_project_rules(
    project_id: str,
    rules: Optional[List[TraefikRule]],
) -> List[TraefikRule]:
    settings = find_project_by_id(project_id)
    if settings is None:
        raise ValueError(f"Project '{project_id}' not found")

    normalized = normalize_rules(rules)
    settings.traefik_rules = normalized
    saved = settings.save_project()
    update_project_rules(saved)
    logger.info(
        "Saved %d Traefik rule(s) for project '%s' (%s)",
        len(normalized),
        getattr(saved, "project_name", ""),
        project_id,
    )
    return list(saved.traefik_rules or normalized)


# ---------------------------------------------------------------------------
# Read model
# ---------------------------------------------------------------------------


def _route_stats(routes: List[Dict[str, Any]], issues: List[str]) -> Dict[str, int]:
    return {
        "total": len(routes),
        "workspace": sum(1 for row in routes if row.get("source") == "workspace"),
        "global": sum(
            1 for row in routes
            if row.get("source") == "custom" and row.get("scope") == "global"
        ),
        "project": sum(
            1 for row in routes
            if row.get("source") == "custom" and row.get("scope") == "project"
        ),
        "enabled": sum(1 for row in routes if row.get("enabled")),
        "disabled": sum(1 for row in routes if not row.get("enabled")),
        "issues": len(issues),
    }


def _apply_editability(routes: List[Dict[str, Any]], project_id: Optional[str]) -> None:
    """
    Mark custom rows editable only in the storage that owns them.

    * global view (``project_id is None``): global rules editable, project rules
      read-only;
    * project view: that project's rules editable, global rules read-only.
    """
    for row in routes:
        if row.get("source") != "custom":
            row["editable"] = False
            continue
        if row.get("scope") == "global":
            row["editable"] = project_id is None
        else:
            row["editable"] = bool(
                project_id and row.get("project_id") == project_id
            )


def build_view(
    project_id: Optional[str] = None,
    refresh: bool = False,
) -> Dict[str, Any]:
    """
    Build the merged route read model for the maintenance UI.

    Args:
        project_id: When set, the view is scoped to that project (global rules
            are inherited read-only and only that project's rules are shown).
        refresh: Force project discovery before building (admin endpoint only).
    """
    global_settings = read_global_settings()

    if project_id:
        # Project view: read the project's settings directly so the tab always
        # shows what is stored in its project.json (the cache is only needed by
        # the global Traefik poll).
        if refresh:
            refresh_project_rules(wait=True)
        settings = find_project_by_id(project_id)
        if settings is None:
            raise ValueError(f"Project '{project_id}' not found")
        update_project_rules(settings)
        project_sets = [{
            "project_id": settings.project_id,
            "project_name": settings.project_name or settings.project_id,
            "rules": [
                rule.model_dump(mode="json")
                for rule in (settings.traefik_rules or [])
            ],
        }]
    else:
        if refresh:
            refresh_project_rules(wait=True)
        project_sets = get_project_rule_sets()

    result = build_traefik(
        workspaces=global_settings.workspaces,
        global_rules=list(global_settings.traefik_rules or []),
        project_rule_sets=project_sets,
    )
    if project_id:
        # The project view only shows workspace routes that belong to the
        # project (or to all projects). The generated config remains global —
        # Traefik has no project concept — but the UI stays focused.
        result["routes"] = [
            row for row in result["routes"]
            if row.get("source") != "workspace"
            or project_id in (row.get("project_ids") or [])
            or "*" in (row.get("project_ids") or [])
        ]
    _apply_editability(result["routes"], project_id)
    # Recompute the row issues after filtering so the project view does not
    # report problems from routes it does not display. Keep the builder's
    # top-level issues (rules that could not be built at all).
    builder_issues = list(result.get("issues") or [])
    result["issues"] = builder_issues + [
        f"{row.get('name') or row.get('id')}: {issue}"
        for row in result["routes"]
        for issue in (row.get("issues") or [])
    ]
    result["stats"] = _route_stats(result["routes"], result["issues"])
    result["defaults"] = {
        "domain": result["domain"],
        "auth_middleware": result["auth_middleware"],
        "entrypoints": list(DEFAULT_ENTRYPOINTS),
    }
    result["project_id"] = project_id
    return result


def build_config() -> Dict[str, Any]:
    """
    Build only the dynamic config for the Traefik HTTP provider.

    This path is polled every 10 seconds, so it uses the project-rules snapshot
    and never waits for project discovery.
    """
    global_settings = read_global_settings()
    result = build_traefik(
        workspaces=global_settings.workspaces,
        global_rules=list(global_settings.traefik_rules or []),
        project_rule_sets=get_project_rule_sets(),
    )
    config = result["config"]
    # KasmVNC containers serve HTTPS with a self-signed certificate.  A shared
    # transport (referenced from Docker labels as ``codx-insecure@http``) keeps
    # those routes working without teaching every route its own transport.
    http = config.setdefault("http", {})
    http.setdefault("serversTransports", {})["codx-insecure"] = {
        "insecureSkipVerify": True,
    }
    return config


# ---------------------------------------------------------------------------
# Target catalog (rule editor)
# ---------------------------------------------------------------------------


def target_catalog() -> Dict[str, Any]:
    """
    Return every target the rule editor can select.

    Workspace apps come from global settings; containers come from the Docker
    daemon (empty with an ``error`` when Docker is unavailable).
    """
    global_settings = read_global_settings()

    workspaces = []
    for workspace in (global_settings.workspaces or []):
        apps = []
        for app in (workspace.apps or []):
            external = is_external_url(app.path)
            apps.append({
                "id": workspace_app_key(app),
                "name": app.name or app.id,
                "path": app.path,
                "route_path": public_path(workspace.slug, app) if external else app.path,
                "port": app.port,
                "external": external,
                "targetable": bool(external or app.port),
            })
        workspaces.append({
            "id": workspace.id,
            "slug": workspace.slug,
            "name": workspace.name,
            "project_ids": list(workspace.project_ids or []),
            "apps": apps,
        })

    docker = list_running_containers()
    return {
        "workspaces": workspaces,
        "containers": docker.get("containers") or [],
        "traefik_networks": docker.get("traefik_networks") or [],
        "error": docker.get("error"),
        "defaults": {
            "domain": os.environ.get("CODX_JUNIOR_DOMAIN", DEFAULT_DOMAIN),
            "auth_middleware": os.environ.get(
                "CODX_JUNIOR_TRAEFIK_AUTH_MIDDLEWARE", DEFAULT_AUTH_MIDDLEWARE
            ),
            "entrypoints": list(DEFAULT_ENTRYPOINTS),
        },
    }


def preview(project_id: Optional[str] = None, refresh: bool = False) -> Dict[str, Any]:
    """
    Return the generated config plus the issue list.

    The config is always the **full** global config (what Traefik actually
    polls), even when the request comes from a project settings tab: a project
    only owns part of the routing, but Traefik consumes all of it.
    """
    view = build_view(project_id=None, refresh=refresh)
    return {
        "config": view["config"],
        "routes": view["routes"],
        "issues": view["issues"],
        "stats": view["stats"],
    }
