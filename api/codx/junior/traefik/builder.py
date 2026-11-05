"""
Merge workspace routes and custom Traefik rules into one dynamic config.

The builder is deliberately independent from FastAPI, global settings and the
Docker daemon: it receives plain workspace/rule objects and returns:

* ``config`` – the JSON Traefik's HTTP provider expects;
* ``routes`` – a normalized read model used by the maintenance UI;
* ``issues`` – non-fatal problems that should be shown to the user.

Routing sources
---------------
1. Workspace apps whose ``path`` is an absolute URL -> router + service in the
   HTTP provider (existing behaviour).
2. Workspace apps with a container port -> read-only rows; the actual routing
   is still done by the Docker labels generated into the compose file.
3. Custom rules -> global rules plus each project's rules. URL and container
   targets get a generated load-balancer service. Workspace-app targets reuse
   the service that already exists in the Docker/HTTP provider.
"""

import logging
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from codx.junior.traefik.model import TraefikRule, TraefikTargetType

logger = logging.getLogger(__name__)

DEFAULT_DOMAIN = os.environ.get("CODX_JUNIOR_DOMAIN", "localhost")
DEFAULT_AUTH_MIDDLEWARE = os.environ.get(
    "CODX_JUNIOR_TRAEFIK_AUTH_MIDDLEWARE", "codx-junior-auth@docker"
)
DEFAULT_ENTRYPOINTS = ["web", "websecure"]

_PATH_PREFIX_RE = re.compile(r"PathPrefix\s*\(\s*`([^`]+)`\s*\)")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def is_external_url(path: str) -> bool:
    """Return True when ``path`` is an absolute HTTP/HTTPS URL."""
    return (path or "").startswith("http://") or (path or "").startswith("https://")


def sanitize_id(value: str, fallback: str = "rule") -> str:
    """
    Make a value safe for a Traefik router/service/middleware name.

    Traefik accepts letters, digits, ``-``, ``_`` and ``.``.  We keep the value
    readable (UUIDs keep their hyphens) and use *fallback* when nothing is left.
    """
    value = str(value or "").strip().lower()
    value = re.sub(r"[^a-z0-9_.-]+", "-", value).strip("-._")
    return value or fallback


def workspace_app_key(app: Any) -> str:
    """
    Key used by the workspace labels for an app.

    Mirrors ``DockerComposeEngine.traefik_labels``: app.id wins, otherwise the
    lower-cased name with spaces replaced by hyphens.  Do not add more
    sanitisation here: the custom rule has to reference the exact service name
    the labels define.
    """
    return app.id or ((app.name or "app").lower().replace(" ", "-"))


def external_app_key(app: Any) -> str:
    """Key used by the HTTP provider for an external-URL workspace app."""
    return ((app.id or app.name or "app").lower()
            .replace(" ", "-")
            .replace("_", "-"))


def external_router_id(workspace_slug: str, app: Any) -> str:
    return f"codx-ws-{workspace_slug}-{external_app_key(app)}"


def container_router_id(workspace_slug: str, app: Any) -> str:
    return f"codx-ws-{workspace_slug}-{workspace_app_key(app)}"


def workspace_router_id(workspace_slug: str, app: Any) -> str:
    if is_external_url(getattr(app, "path", "")):
        return external_router_id(workspace_slug, app)
    return container_router_id(workspace_slug, app)


def public_path(workspace_slug: str, app: Any) -> str:
    """Public path prefix of an external-URL workspace app."""
    return f"/ws/{workspace_slug}/{external_app_key(app)}"


def normalize_path_prefix(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if not value.startswith("/"):
        value = "/" + value
    if len(value) > 1:
        value = value.rstrip("/")
    return value


def extract_path_prefix(rule: str) -> str:
    """Read the first ``PathPrefix(`…`)`` from a Traefik rule expression."""
    match = _PATH_PREFIX_RE.search(rule or "")
    return normalize_path_prefix(match.group(1)) if match else ""


def resolve_path_prefix(
    rule: TraefikRule,
    app: Any = None,
    target_url: str = "",
) -> str:
    """
    Resolve the public prefix used by strip_prefix.

    Priority: explicit field -> rule expression -> workspace app path -> URL path.
    """
    prefix = normalize_path_prefix(rule.path_prefix)
    if prefix:
        return prefix

    prefix = extract_path_prefix(rule.rule)
    if prefix:
        return prefix

    if app is not None:
        app_path = getattr(app, "path", "") or ""
        if app_path and not is_external_url(app_path):
            return normalize_path_prefix(app_path)

    if target_url:
        return normalize_path_prefix(urlparse(target_url).path)

    return ""


def split_target_url(url: str) -> Tuple[str, str]:
    """
    Validate a target URL and split it into (load-balancer base, sub-path).

    ``http://host:8080/app`` -> (``http://host:8080``, ``/app``).
    Raises ``ValueError`` for an invalid URL.
    """
    parsed = urlparse((url or "").strip())
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        raise ValueError("Target URL must be an absolute http:// or https:// URL")
    base = f"{parsed.scheme.lower()}://{parsed.netloc}"
    subpath = (parsed.path or "").rstrip("/")
    return base, subpath


def _strip_middleware(name: str, prefix: str, target_subpath: str = "") -> Dict[str, Any]:
    """Build a replacePathRegex middleware that strips *prefix*."""
    prefix = normalize_path_prefix(prefix)
    target_subpath = (target_subpath or "").rstrip("/")
    if prefix == "/":
        # Stripping the root is a no-op, but the router still needs a valid
        # middleware declaration when the rule asked for one.
        return {
            name: {
                "replacePathRegex": {
                    "regex": "^(.*)$",
                    "replacement": "$1",
                }
            }
        }
    replacement = (
        f"{target_subpath}/${{1}}" if target_subpath else "/${1}"
    )
    return {
        name: {
            "replacePathRegex": {
                "regex": f"^{re.escape(prefix)}(/.*)?$",
                "replacement": replacement,
            }
        }
    }


def _balanced(rule: str) -> bool:
    """Cheap sanity check for the most common Traefik rule typos."""
    if (rule or "").count("`") % 2:
        return False
    depth = 0
    for char in rule or "":
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _rule_rule_issues(rule: TraefikRule, app: Any = None) -> List[str]:
    issues: List[str] = []
    if not (rule.rule or "").strip():
        issues.append("Rule expression is empty")
    elif not _balanced(rule.rule):
        issues.append("Rule expression has unbalanced backticks or parentheses")

    if rule.target_type == TraefikTargetType.URL:
        if not (rule.url or "").strip():
            issues.append("Target URL is required")
        else:
            try:
                split_target_url(rule.url)
            except ValueError as ex:
                issues.append(str(ex))
    elif rule.target_type == TraefikTargetType.WORKSPACE_APP:
        if not (rule.workspace_slug or "").strip():
            issues.append("Workspace is required")
        if not (rule.app_id or "").strip():
            issues.append("Workspace app is required")
        if app is None:
            issues.append("Workspace app not found")
        elif is_external_url(getattr(app, "path", "")):
            try:
                split_target_url(app.path)
            except ValueError as ex:
                issues.append(f"Workspace app URL: {ex}")
        elif not getattr(app, "port", None):
            issues.append("Workspace app has no container port and no external URL")
    elif rule.target_type == TraefikTargetType.CONTAINER:
        if not (rule.container_name or "").strip():
            issues.append("Container is required")
        if not rule.container_port:
            issues.append("Container port is required")
        elif not (0 < int(rule.container_port) < 65536):
            issues.append("Container port must be between 1 and 65535")
    return issues


def validate_rule_structure(rule: TraefikRule) -> List[str]:
    """
    Validate a rule for saving (does not check that the target still exists).

    Target existence is checked by the builder, so a rule can be saved while a
    container is stopped or a workspace app is temporarily missing; the UI
    shows the resulting issue instead of rejecting the whole settings save.
    """
    issues: List[str] = []
    if rule.enabled and not (rule.rule or "").strip():
        issues.append("Rule expression is empty")
    elif rule.rule and not _balanced(rule.rule):
        issues.append("Rule expression has unbalanced backticks or parentheses")

    if rule.target_type == TraefikTargetType.URL:
        if not (rule.url or "").strip():
            issues.append("Target URL is required")
        else:
            try:
                split_target_url(rule.url)
            except ValueError as ex:
                issues.append(str(ex))
    elif rule.target_type == TraefikTargetType.WORKSPACE_APP:
        if not (rule.workspace_slug or "").strip():
            issues.append("Workspace is required")
        if not (rule.app_id or "").strip():
            issues.append("Workspace app is required")
    elif rule.target_type == TraefikTargetType.CONTAINER:
        if not (rule.container_name or "").strip():
            issues.append("Container is required")
        if not rule.container_port:
            issues.append("Container port is required")
        elif not (0 < int(rule.container_port) < 65536):
            issues.append("Container port must be between 1 and 65535")
    return issues


# ---------------------------------------------------------------------------
# Workspace routes
# ---------------------------------------------------------------------------


def _workspace_base_row(workspace: Any, app: Any) -> Dict[str, Any]:
    return {
        "id": workspace_router_id(workspace.slug, app),
        "router_id": workspace_router_id(workspace.slug, app),
        "name": app.name or app.id or "App",
        "description": app.description or "",
        "source": "workspace",
        "scope": "workspace",
        "project_ids": list(getattr(workspace, "project_ids", None) or []),
        "workspace_id": workspace.id,
        "workspace_slug": workspace.slug,
        "workspace_name": workspace.name,
        "app_id": workspace_app_key(app),
        "app_name": app.name or "",
        "editable": False,
        "enabled": True,
        "entrypoints": [],
        "priority": None,
        "issues": [],
    }


def build_workspace_route(
    workspace: Any,
    app: Any,
    domain: str,
    auth_middleware: str,
) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Build one workspace route.

    Returns ``(row, routers, services, middlewares)``.  Container apps return no
    config entries because their routing is still owned by Docker labels.
    """
    routers: Dict[str, Any] = {}
    services: Dict[str, Any] = {}
    middlewares: Dict[str, Any] = {}
    row = _workspace_base_row(workspace, app)
    row["path_prefix"] = normalize_path_prefix(app.path) if not is_external_url(app.path) else ""

    rid = row["router_id"]

    if is_external_url(app.path):
        public = public_path(workspace.slug, app)
        try:
            base_url, ext_subpath = split_target_url(app.path)
        except ValueError as ex:
            row["issues"].append(str(ex))
            row["enabled"] = False
            row["target"] = app.path
            row["target_url"] = app.path
            row["managed_by"] = "http-provider"
            return row, routers, services, middlewares

        strip_id = f"{rid}-strip"
        middlewares.update(_strip_middleware(strip_id, public, ext_subpath))
        applied: List[str] = [strip_id]
        if auth_middleware:
            applied.append(auth_middleware)

        routers[rid] = {
            "rule": f"Host(`{domain}`) && PathPrefix(`{public}`)",
            "service": rid,
            "middlewares": applied,
            "entryPoints": list(DEFAULT_ENTRYPOINTS),
        }
        services[rid] = {
            "loadBalancer": {
                "servers": [{"url": base_url}],
                "passHostHeader": False,
            }
        }

        row.update({
            "managed_by": "http-provider",
            "rule": f"Host(`{domain}`) && PathPrefix(`{public}`)",
            "target_type": TraefikTargetType.WORKSPACE_APP.value,
            "target": app.path,
            "target_url": app.path,
            "middlewares": applied,
            "path_prefix": public,
            "entrypoints": list(DEFAULT_ENTRYPOINTS),
        })
        return row, routers, services, middlewares

    if app.port:
        row.update({
            "managed_by": "docker-labels",
            "rule": f"PathPrefix(`{normalize_path_prefix(app.path)}`)",
            "target_type": TraefikTargetType.WORKSPACE_APP.value,
            "target": f"container :{app.port}",
            "target_url": None,
            "middlewares": [
                f"{rid}-strip@docker",
                auth_middleware,
            ] if auth_middleware else [f"{rid}-strip@docker"],
            "path_prefix": normalize_path_prefix(app.path),
        })
        if not row["path_prefix"]:
            row["issues"].append("Workspace app path is empty")
        return row, routers, services, middlewares

    row.update({
        "managed_by": "docker-labels",
        "rule": "",
        "target_type": TraefikTargetType.WORKSPACE_APP.value,
        "target": "no port / external URL configured",
        "target_url": None,
        "middlewares": [],
    })
    row["issues"].append(
        "App has no port and no external URL; its route is defined by the "
        "workspace compose labels"
    )
    return row, routers, services, middlewares


# ---------------------------------------------------------------------------
# Custom routes
# ---------------------------------------------------------------------------


def _custom_router_id(rule: TraefikRule, scope: str, project_id: str, index: int) -> str:
    rule_key = sanitize_id(rule.id or f"rule-{index + 1}")
    if scope == "project" and project_id:
        return f"codx-rule-p-{sanitize_id(project_id)}-{rule_key}"
    return f"codx-rule-g-{rule_key}"


def _resolve_workspace_app(
    rule: TraefikRule,
    workspaces_by_slug: Dict[str, Any],
) -> Tuple[Any, Any]:
    workspace = workspaces_by_slug.get(rule.workspace_slug or "")
    if workspace is None:
        return None, None
    app_key = rule.app_id or ""
    for app in (getattr(workspace, "apps", None) or []):
        if workspace_app_key(app) == app_key:
            return workspace, app
    return workspace, None


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def build_custom_route(
    rule: TraefikRule,
    scope: str,
    project_id: Optional[str],
    project_name: Optional[str],
    workspaces_by_slug: Dict[str, Any],
    domain: str,
    auth_middleware: str,
    index: int,
) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Build one custom rule.

    Returns ``(row, routers, services, middlewares)``.  Disabled or invalid
    rules return a row with issues and no config entries.
    """
    routers: Dict[str, Any] = {}
    services: Dict[str, Any] = {}
    middlewares: Dict[str, Any] = {}

    rid = _custom_router_id(rule, scope, project_id or "", index)
    row: Dict[str, Any] = {
        "id": rule.id or f"rule-{index + 1}",
        "router_id": rid,
        "name": rule.name or rule.id or f"Rule {index + 1}",
        "description": rule.description or "",
        "source": "custom",
        "scope": scope,
        "project_id": project_id,
        "project_name": project_name,
        "editable": False,
        "enabled": bool(rule.enabled),
        "rule": rule.rule or "",
        "target_type": rule.target_type.value,
        "target": "",
        "target_url": "",
        "workspace_slug": rule.workspace_slug or "",
        "app_id": rule.app_id or "",
        "container_name": rule.container_name or "",
        "container_port": rule.container_port,
        "entrypoints": list(rule.entrypoints or []),
        "middlewares": [],
        "priority": rule.priority,
        "path_prefix": rule.path_prefix or "",
        "issues": [],
    }

    entrypoints = [entrypoint for entrypoint in (rule.entrypoints or []) if entrypoint]
    row["entrypoints"] = entrypoints

    app = None
    workspace = None
    base_url = ""
    target_subpath = ""
    service_name = rid
    service_entry: Optional[Dict[str, Any]] = None

    if rule.target_type == TraefikTargetType.URL:
        row["target"] = rule.url
        row["target_url"] = rule.url
        if (rule.url or "").strip():
            try:
                base_url, target_subpath = split_target_url(rule.url)
            except ValueError as ex:
                row["issues"].append(str(ex))
        if base_url:
            service_entry = {
                "loadBalancer": {
                    "servers": [{"url": base_url}],
                    "passHostHeader": False,
                }
            }
    elif rule.target_type == TraefikTargetType.WORKSPACE_APP:
        workspace, app = _resolve_workspace_app(rule, workspaces_by_slug)
        if workspace is not None and app is not None:
            row["target"] = f"{workspace.name} / {app.name or app.id}"
            row["workspace_slug"] = workspace.slug
            row["app_id"] = workspace_app_key(app)
            if is_external_url(getattr(app, "path", "")):
                service_name = external_router_id(workspace.slug, app)
                row["target_url"] = app.path
                try:
                    _, target_subpath = split_target_url(app.path)
                except ValueError:
                    target_subpath = ""
            else:
                service_name = f"{container_router_id(workspace.slug, app)}@docker"
                row["target_url"] = ""
        else:
            row["target"] = f"{rule.workspace_slug} / {rule.app_id}"
    elif rule.target_type == TraefikTargetType.CONTAINER:
        port = rule.container_port
        row["target"] = (
            f"{rule.container_name}:{port}" if rule.container_name and port
            else rule.container_name or ""
        )
        if rule.container_name and port:
            base_url = f"http://{rule.container_name}:{port}"
            row["target_url"] = base_url
            service_entry = {
                "loadBalancer": {
                    "servers": [{"url": base_url}],
                    "passHostHeader": False,
                }
            }

    row["issues"].extend(_rule_rule_issues(rule, app))

    # Middleware chain. Strip is generated by us (own name), auth is shared.
    applied: List[str] = []
    if rule.strip_prefix:
        prefix = resolve_path_prefix(rule, app=app, target_url=rule.url)
        if prefix:
            strip_id = f"{rid}-strip"
            middlewares.update(_strip_middleware(strip_id, prefix, target_subpath))
            applied.append(strip_id)
            row["path_prefix"] = prefix
        else:
            row["issues"].append(
                "Strip prefix is enabled but no path prefix could be determined"
            )
    if rule.auth and auth_middleware:
        applied.append(auth_middleware)
    applied.extend(rule.middlewares or [])
    applied = _dedupe(applied)
    row["middlewares"] = applied

    # Only publish when enabled and structurally valid. Target resolution
    # issues are fatal for the config but keep the row visible in the UI.
    critical = [
        issue for issue in row["issues"]
        if issue in (
            "Rule expression is empty",
            "Rule expression has unbalanced backticks or parentheses",
            "Target URL is required",
            "Workspace is required",
            "Workspace app is required",
            "Workspace app not found",
            "Container is required",
            "Container port is required",
            "Strip prefix is enabled but no path prefix could be determined",
        )
        or issue.startswith("Target URL must")
        or "Workspace app URL" in issue
        or "not found" in issue
        or "no container port" in issue
        or "must be between" in issue
    ]
    if rule.enabled and not critical:
        router: Dict[str, Any] = {
            "rule": rule.rule,
            "service": service_name,
        }
        if entrypoints:
            router["entryPoints"] = entrypoints
        if applied:
            router["middlewares"] = applied
        if rule.priority is not None:
            router["priority"] = rule.priority
        routers[rid] = router
        if service_entry is not None:
            services[rid] = service_entry

    return row, routers, services, middlewares


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_traefik(
    workspaces: Optional[List[Any]],
    global_rules: Optional[List[TraefikRule]],
    project_rule_sets: Optional[List[Dict[str, Any]]],
    domain: Optional[str] = None,
    auth_middleware: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build the merged Traefik config and the normalized route list.

    Args:
        workspaces: Every workspace (``Workspace`` objects).
        global_rules: Rules from ``GlobalSettings.traefik_rules``.
        project_rule_sets: ``[{project_id, project_name, rules: [...]}, ...]``.
            ``rules`` may contain ``TraefikRule`` objects or serialized dicts.
        domain: Host used by generated rules (defaults to ``CODX_JUNIOR_DOMAIN``).
        auth_middleware: Middleware name (defaults to
            ``codx-junior-auth@docker``; empty disables auth).
    """
    domain = domain or DEFAULT_DOMAIN
    auth_middleware = (
        DEFAULT_AUTH_MIDDLEWARE if auth_middleware is None else auth_middleware
    )

    routers: Dict[str, Any] = {}
    services: Dict[str, Any] = {}
    middlewares: Dict[str, Any] = {}
    rows: List[Dict[str, Any]] = []
    issues: List[str] = []

    workspaces_by_slug = {
        getattr(workspace, "slug", "") or "": workspace
        for workspace in (workspaces or [])
        if getattr(workspace, "slug", "")
    }

    # 1. Workspace routes ---------------------------------------------------
    for workspace in (workspaces or []):
        for app in (getattr(workspace, "apps", None) or []):
            row, r, s, m = build_workspace_route(
                workspace, app, domain=domain, auth_middleware=auth_middleware
            )
            rows.append(row)
            routers.update(r)
            services.update(s)
            middlewares.update(m)

    # 2. Global custom rules ------------------------------------------------
    for index, rule in enumerate(global_rules or []):
        try:
            row, r, s, m = build_custom_route(
                rule=rule,
                scope="global",
                project_id=None,
                project_name=None,
                workspaces_by_slug=workspaces_by_slug,
                domain=domain,
                auth_middleware=auth_middleware,
                index=index,
            )
        except Exception as ex:
            logger.exception("Cannot build global Traefik rule %s: %s", index, ex)
            issues.append(f"Global rule {index + 1}: {ex}")
            continue
        rows.append(row)
        routers.update(r)
        services.update(s)
        middlewares.update(m)

    # 3. Project custom rules ----------------------------------------------
    for project_set in (project_rule_sets or []):
        project_id = project_set.get("project_id")
        project_name = project_set.get("project_name") or project_id
        for index, raw_rule in enumerate(project_set.get("rules") or []):
            try:
                rule = (
                    raw_rule if isinstance(raw_rule, TraefikRule)
                    else TraefikRule(**raw_rule)
                )
                row, r, s, m = build_custom_route(
                    rule=rule,
                    scope="project",
                    project_id=project_id,
                    project_name=project_name,
                    workspaces_by_slug=workspaces_by_slug,
                    domain=domain,
                    auth_middleware=auth_middleware,
                    index=index,
                )
            except Exception as ex:
                logger.exception(
                    "Cannot build Traefik rule %s of project %s: %s",
                    index, project_id, ex,
                )
                issues.append(f"{project_name} rule {index + 1}: {ex}")
                continue
            rows.append(row)
            routers.update(r)
            services.update(s)
            middlewares.update(m)

    # Row-level issues stay on the row so the UI can show them next to the
    # route. The top-level list only carries failures that prevent a rule from
    # being built at all; manager.build_view merges both for the UI.
    http: Dict[str, Any] = {}
    if routers:
        http["routers"] = routers
    if services:
        http["services"] = services
    if middlewares:
        http["middlewares"] = middlewares

    return {
        "config": {"http": http},
        "routes": rows,
        "issues": issues,
        "domain": domain,
        "auth_middleware": auth_middleware,
    }


def filter_project_rules(
    project_rule_sets: List[Dict[str, Any]],
    project_id: Optional[str],
) -> List[Dict[str, Any]]:
    """Return only the requested project's rule set (or everything)."""
    if not project_id:
        return list(project_rule_sets or [])
    return [
        item for item in (project_rule_sets or [])
        if item.get("project_id") == project_id
    ]
