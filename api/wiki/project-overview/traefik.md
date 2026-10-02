# Traefik Dynamic Configuration Provider

## Overview
This module exposes FastAPI endpoints that generate and serve Traefik‑compatible dynamic configuration for workspace applications. Traefik's `providers.http` polls `GET /api/traefik/config` at regular intervals to update routing rules. The configuration is built exclusively from apps whose `path` is an external HTTP/HTTPS URL; container‑port apps are handled separately by Traefik's docker label provider.

## Endpoints

### `GET /api/traefik/config`
- **Purpose**: Returns a Traefik dynamic configuration JSON constructed from all workspace apps with external URL paths.
- **Authentication**: No authentication required; the endpoint must be reachable only by the Traefik container on the internal Docker network.
- **Response**: A JSON object containing `http.routers`, `http.services`, and `http.middlewares`. If an error occurs, an empty but valid config `{"http": {}}` is returned to prevent Traefik from failing on poll.
- *Reference: `traefik_dynamic_config()` function*

### `GET /api/traefik/routes`
- **Purpose**: Provides a human‑readable summary of all active dynamic routes currently injected into Traefik via the HTTP provider.
- **Authentication**: Requires admin role (`require_admin` dependency).
- **Response**: A list of routes, each including `id`, `rule`, `target_url`, `middlewares`, and `entryPoints`, together with a total count.
- *Reference: `list_traefik_routes()` function*

## Routing Logic
- Apps whose `path` starts with `http://` or `https://` are treated as **external service URLs**. The public route prefix exposed by Traefik is `/ws/{workspace_slug}/{app_id}`. Traefik proxies requests to the external host, stripping this prefix and forwarding any remaining sub‑path.
- Apps without an `http(s)` prefix are **container‑port apps** and are excluded from this provider; their routing is managed by Traefik's docker label provider.
- *Reference: `_is_external_url()` and the routing section of `_build_dynamic_config()`*

## Configuration Generation
The `_build_dynamic_config()` function iterates all workspaces and apps, constructing Traefik routers, services, and middlewares for external‑URL apps:

- **Routers**: Defined by the rule `Host({CODX_JUNIOR_DOMAIN}) && PathPrefix({public_path})`, with entry points `web` and `websecure`, and a middleware chain that includes `codx-junior-auth` and a strip‑prefix middleware.
- **Services**: Configured with a load‑balancer pointing to the external host:port (derived from the URL’s scheme, host, and port), with `passHostHeader` disabled.
- **Middlewares**: A strip‑prefix middleware rewrites the incoming path to prepend the external URL’s sub‑path before forwarding, followed by the `codx-junior-auth` middleware.
- *Reference: `_router_id()`, `_public_path()`, `_build_dynamic_config()`*

## Authentication
All generated routes apply the `codx-junior-auth` middleware, as specified in the app routing logic and route summaries.

## Settings & Globals
- Data is sourced via `read_global_settings()`, which provides workspace and app information.
- The `CODX_JUNIOR_DOMAIN` environment variable (defaults to `localhost`) is used in router host rules.
- *Reference: `read_global_settings()`, `CODX_JUNIOR_DOMAIN`*