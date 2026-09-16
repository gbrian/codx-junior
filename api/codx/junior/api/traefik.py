"""
Traefik dynamic configuration provider endpoint.

Traefik's ``providers.http`` polls ``GET /api/traefik/config`` every
``pollInterval`` seconds. This endpoint builds a Traefik-compatible dynamic
configuration JSON object from all workspace apps.

App routing logic
-----------------
- If ``app.path`` starts with ``http://`` or ``https://``, it is treated as
  an **external service URL** (e.g. ``http://194.93.48.9:8080/app``).
  The public route prefix is derived as: ``/ws/{workspace_slug}/{app_id}``.
  Traefik proxies requests to the external URL, stripping the public prefix
  and forwarding to the external host + any sub-path it contains.

- Otherwise ``app.path`` is the standard public path prefix and ``app.port``
  is the container port (workspace-network routing, managed via docker labels).
  These are skipped here — docker label provider handles them.

Auth middleware (``codx-junior-auth``) is applied to all generated routes.

Endpoints
---------
GET /api/traefik/config   – Traefik HTTP provider (no auth, internal network)
GET /api/traefik/routes   – Admin summary of active dynamic routes
"""

import logging
import os
from typing import Any, Dict
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from codx.junior.global_settings import read_global_settings
from codx.junior.model.model import CodxUser
from codx.junior.api import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(tags=["traefik"])

CODX_JUNIOR_DOMAIN = os.environ.get("CODX_JUNIOR_DOMAIN", "localhost")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_external_url(path: str) -> bool:
    """Return True when path is an absolute HTTP/HTTPS URL (external service)."""
    return path.startswith("http://") or path.startswith("https://")


def _router_id(workspace_slug: str, app_id: str) -> str:
    """Stable, Traefik-safe router/service/middleware ID for a workspace app."""
    safe_app = (app_id or "app").lower().replace(" ", "-").replace("_", "-")
    return f"codx-ws-{workspace_slug}-{safe_app}"


def _public_path(workspace_slug: str, app_id: str) -> str:
    """Public path prefix exposed by Traefik for an external-URL app."""
    safe_app = (app_id or "app").lower().replace(" ", "-").replace("_", "-")
    return f"/ws/{workspace_slug}/{safe_app}"


def _build_dynamic_config() -> Dict[str, Any]:
    """
    Iterate all workspaces and build a Traefik dynamic config dict.

    Only apps whose ``path`` is an external URL are included — container-port
    apps are already handled by Traefik's docker label provider.
    """
    global_settings = read_global_settings()

    routers: Dict[str, Any] = {}
    services: Dict[str, Any] = {}
    middlewares: Dict[str, Any] = {}

    for workspace in (global_settings.workspaces or []):
        slug = (workspace.folder_path or workspace.id or "").strip()
        if not slug:
            continue

        for app in (workspace.apps or []):
            if not _is_external_url(app.path):
                # Container-port apps are handled by docker label provider
                continue

            service_url = app.path  # e.g. http://194.93.48.9:8080/app
            rid = _router_id(slug, app.id or app.name)
            public_path = _public_path(slug, app.id or app.name)

            parsed = urlparse(service_url)
            scheme = parsed.scheme                        # http | https
            host = parsed.hostname or ""
            port = parsed.port or (443 if scheme == "https" else 80)
            ext_subpath = parsed.path.rstrip("/")         # e.g. /app  (may be empty)

            # Base URL for the Traefik load-balancer (no sub-path)
            lb_url = f"{scheme}://{host}:{port}"

            # -- Strip-prefix middleware: remove the public prefix before forwarding
            strip_mid = f"{rid}-strip"
            middlewares[strip_mid] = {
                "replacePathRegex": {
                    "regex": f"^{public_path}(/.*)?$",
                    "replacement": f"{ext_subpath}/${{1}}",  # prepend external sub-path
                }
            }

            applied_middlewares = [strip_mid, "codx-junior-auth"]

            # -- Router
            routers[rid] = {
                "rule": f"Host(`{CODX_JUNIOR_DOMAIN}`) && PathPrefix(`{public_path}`)",
                "service": rid,
                "middlewares": applied_middlewares,
                "entryPoints": ["web", "websecure"],
            }

            # -- Service
            services[rid] = {
                "loadBalancer": {
                    "servers": [{"url": lb_url}],
                    "passHostHeader": False,
                }
            }

            logger.debug(
                "Traefik dynamic config: %s  %s  →  %s",
                rid, public_path, service_url,
            )

    return {
        "http": {
            **({"routers": routers} if routers else {}),
            **({"services": services} if services else {}),
            **({"middlewares": middlewares} if middlewares else {}),
        }
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/traefik/config",
    summary="Traefik HTTP provider – dynamic configuration",
    include_in_schema=False,   # internal endpoint, exclude from public docs
)
def traefik_dynamic_config():
    """
    Polled by Traefik's ``providers.http`` every ``pollInterval``.

    Returns a Traefik-compatible dynamic configuration JSON built from all
    workspace apps whose ``path`` is an external HTTP/HTTPS URL.

    No authentication — must be reachable by the Traefik container on the
    internal Docker network only.
    """
    try:
        config = _build_dynamic_config()
        return JSONResponse(content=config)
    except Exception as ex:
        logger.exception("Error building Traefik dynamic config: %s", ex)
        # Return an empty-but-valid config so Traefik doesn't error out
        return JSONResponse(content={"http": {}})


@router.get(
    "/traefik/routes",
    summary="[Admin] List active Traefik dynamic routes from workspace apps",
)
def list_traefik_routes(user: CodxUser = Depends(require_admin)):
    """
    Human-readable summary of all routes currently injected into Traefik
    via the HTTP provider.  Requires admin role.
    """
    config = _build_dynamic_config()
    http = config.get("http", {})
    routers = http.get("routers", {})
    services = http.get("services", {})

    routes = []
    for rid, rconf in routers.items():
        svc = services.get(rid, {})
        servers = svc.get("loadBalancer", {}).get("servers", [])
        routes.append({
            "id": rid,
            "rule": rconf.get("rule"),
            "target_url": servers[0].get("url") if servers else None,
            "middlewares": rconf.get("middlewares", []),
            "entryPoints": rconf.get("entryPoints", []),
        })

    return {"routes": routes, "total": len(routes)}