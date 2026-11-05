# Workspaces: running container apps through Traefik

**Status:** review of the working tree (including the in-progress `traefik/` and
`dsh` integration work).
**Goal:** admins and project admins can create a workspace with its own folder
(compose, images, scripts, assets), start its containers, publish each app on a
workspace path, and open it inside codx-junior — e.g. DeepSeek Harness
(`dsh`) in a container at `/ws/<workspace>/dsh/`.

---

## 1. Verdict

The domain model and the UI direction are good, and the new custom-Traefik-rule
builder is a solid base. **The runtime is not connected to it yet.**

* Workspace **creation returns 500** on every call: the API instantiates a
  manager with the wrong constructor and calls a method that no longer exists.
* There is **no lifecycle API** at all (start/stop/status/logs), although the
  UI and the docs already use one.
* Workspace **files are not on a persistent, host-visible volume** in the
  shipped installer, so `docker compose` bind mounts and `build:` contexts
  cannot resolve on the host.
* Traefik **cannot reach workspace containers** as shipped: the engine connects
  a container name that does not exist, and workspace services never join a
  network Traefik is on.
* The Traefik **auth middleware is a stub** (`/api/forward-auth` returns
  `"ok"`), and the browser authenticates API calls with a Bearer header, not a
  cookie — so proxied apps are effectively public.
* **Project admins cannot use the workspace management endpoints**; everything
  except `/workspaces/accessible` is `require_admin` (global role only).
* Custom workspaces **never receive Traefik labels**: labels are only rendered
  by two built-in templates.

In short: treat the current workspaces feature as a **prototype/UI shell**, and
rebuild the runtime path around a single manager + engine, a generated compose
override, and a real session cookie for proxied apps.

---

## 2. What exists today

| Layer | Files | State |
| --- | --- | --- |
| Model | `api/codx/junior/workspaces/model.py`, `api/codx/junior/model/workspace.py` | One model, but `WorkspaceApp.path` is overloaded (public prefix **or** target URL) and there is no compose-service mapping. |
| Persistence A | `api/codx/junior/workspaces/workspace_manager.py` | Project-scoped `.codx/workspaces/<id>/<id>.workspace`; no lifecycle; missing `asyncio` import; `folder_path` becomes an absolute path on load. |
| Persistence B | `api/codx/junior/workspaces/manager.py` | Global-settings registry + compose start/stop. **Not used by the API.** |
| Lifecycle | `api/codx/junior/workspaces/engines/compose.py` | Implemented (`start/stop/status/logs`) but unreachable; hardcodes the wrong Traefik container name. |
| API | `api/codx/junior/api/workspaces.py` | CRUD + flat file endpoints. Create is broken; no lifecycle/routes/launch endpoints. |
| Templates | `api/codx/junior/workspaces/templates.py`, `templates/` | Jinja templates for `dev-stack` / `static-site`; `custom` generates nothing. |
| AI generator | `api/codx/junior/workspaces/workspace_file_generator.py` | Duplicates templates; asks the model to add a second Traefik service; not wired to a safe path. |
| Traefik rules | `api/codx/junior/traefik/*`, `api/codx/junior/api/traefik.py` | Good builder and project/global stores; all endpoints admin-only; depends on labels that custom workspaces never get. |
| UI | `client/src/components/workspaces/*`, `client/src/api/modules/workspaces.js` | Calls endpoints that do not exist or have different payloads. |
| Installer | `codx-junior-installer/codx-junior/docker-compose.yaml`, `traefik/traefik.yaml` | Docker socket + HTTP provider present; no workspaces volume; Traefik container name `traefik-codx-junior`, engine expects `codx-junior-traefik`. |

The wiki (`api/wiki/engine-module/codx-junior-workspaces-manager-py.md`)
describes a third variant: a `WorkspaceManager(settings, engine=None)` façade with
`create_workspace`, `start_workspace`, `provision`, `workspace.json`, etc. That
is the design the code should converge on; today it is only documentation.

---

## 3. Blocking findings (P0)

### P0-1. Workspace creation always fails

`api/codx/junior/api/workspaces.py:231`:

```python
workspace_manager = WorkspaceManager()
if not workspace_manager.create_workspace_files(new_workspace):
```

`api/codx/junior/workspaces/workspace_manager.py:41` requires `settings`:

```python
def __init__(self, settings: CODXJuniorSettings):
```

and the class has no `create_workspace_files` method (the wiki documents one
from an older implementation). The request therefore raises `TypeError` before
anything is persisted.

**Fix:** one manager façade, `WorkspaceManager(settings=None)` for global
workspaces, with `create_workspace`, `update_workspace`, `start`, `stop`,
`status`, `logs`, `delete`, and `provision`. Remove the other manager.

### P0-2. There is no lifecycle API

`api/codx/junior/api/workspaces.py` exposes only:

```
GET    /workspaces/accessible
GET    /workspaces
POST   /workspaces
PUT    /workspaces/{id}
DELETE /workspaces/{id}
GET    /workspaces/{id}/files
GET    /workspaces/{id}/files/{filename}
PUT    /workspaces/{id}/files/{filename}
DELETE /workspaces/{id}/files/{filename}
```

The UI calls `POST /workspaces/{id}/start`, `POST /{id}/stop`,
`GET /{id}/status`, `GET /{id}/logs`, `POST /{id}/generate-files`,
`GET /workspaces/{id}`, `GET /workspaces/templates` — all 404.
`DELETE` only removes the settings entry; containers, networks and the folder
stay behind.

**Fix:** add the endpoints (and route tests) listed in §5.1.

### P0-3. The workspace UI is wired to a different API

| UI call (`client/src/api/modules/workspaces.js`) | Backend reality |
| --- | --- |
| `GET /api/workspaces` | exists, but admin-only (project admins get 403) |
| `GET /api/workspaces/{id}` | missing |
| `POST /api/workspaces` | 500 (P0-1); drops `template`, `env`, `resources`, `use_sysbox` because the request model does not have them |
| `PUT /api/workspaces` (no id) | backend expects `PUT /api/workspaces/{id}` → 405 |
| `DELETE /api/workspaces/{id}` | exists, but leaks containers/files |
| `POST /api/workspaces/templates` | missing |
| `POST /api/workspaces/{id}/start` / `stop` | missing |
| `GET /api/workspaces/{id}/status` / `logs` | missing |
| `POST /api/workspaces/{id}/generate-files` | missing |
| `GET /api/workspaces/{id}/files?path=` | backend ignores `path` and returns a flat `List[WorkspaceFileResponse]`; UI expects `{files, folders}` |
| `GET /api/workspaces/{id}/files/{path}` | backend blocks `/` (no nested files); returns `{filename, content}`; UI expects `{path, content}` |
| `POST /api/workspaces/{id}/files/{path}` | backend only accepts `PUT`; body is `{filename, content}` vs UI `{content}` |

**Fix:** make the API module the contract and update both sides; add a
contract test that calls every method of `workspacesModule` against a
`TestClient`.

### P0-4. Workspace files are not persistent or host-visible

* `api/codx/junior/globals.py:63` defaults
  `CODX_JUNIOR_WORKSPACES_FOLDER` to
  `/home/codx-junior/codx-junior-global-settings.json/workspaces` — a path
  under a JSON *file* name, not a mounted volume.
* `codx-junior-installer/codx-junior/docker-compose.yaml` mounts
  `/home/codx-junior-projects`, the settings volume, the docker socket and the
  repo — **no workspaces volume**.
* `docker compose` is executed by the API container. Relative `build.context`,
  `volumes: ./data:/data` and `env_file: .env` are resolved by the CLI from the
  API container's filesystem and then sent to the host daemon. Unless the
  workspace root is mounted at the **same absolute path** on host and API
  container, Docker receives paths that do not exist on the host.

This also means a container restart loses all workspace files (they live in the
API container's writable layer).

**Fix:** create a first-class host folder, mount it identity (`host ==
container`), and make it configurable:

```yaml
# installer compose, api + api-background
- /home/codx-junior-workspaces:/home/codx-junior-workspaces
environment:
  - CODX_JUNIOR_WORKSPACES_FOLDER=/home/codx-junior-workspaces
```

Document that this must be a host bind mount, not a named volume, if compose
files use bind mounts or builds. Add a startup validation that the folder is
writable and that its container path equals the host path (or configure a
`CODX_JUNIOR_WORKSPACES_HOST_PATH` translation, but identity is simpler).

### P0-5. Traefik cannot reach workspace containers

`api/codx/junior/workspaces/engines/compose.py:14`:

```python
TRAEFIK_CONTAINER_NAME = "codx-junior-traefik"
```

The shipped installer names it `traefik-codx-junior`
(`codx-junior-installer/codx-junior/docker-compose.yaml:203`). The connect call
silently fails, and every workspace runs on its own `codx-ws-<slug>` network
that Traefik has never joined. Docker-provider labels are ignored for
containers on a network Traefik is not attached to.

Additionally, the engine uses `docker network connect` only at `start`; if
Traefik restarts, all connections are lost and nothing reconciles them.

**Fix (recommended):** a shared external Traefik network, e.g.
`codx-junior-traefik`, attached to the Traefik container and to every workspace
app service by the generated compose override. Set
`traefik.docker.network=codx-junior-traefik` on each service. Make the network
name and the Traefik container name env-configurable
(`CODX_JUNIOR_TRAEFIK_NETWORK`, `CODX_JUNIOR_TRAEFIK_CONTAINER`) and discover
them from the Traefik container when unset (`traefik/docker.py` already lists
its networks).

The alternative (per-workspace network + connect Traefik) still needs the
correct name, reconciliation on startup, and a lock, but keeps tenant
isolation. Whichever you choose, write it down and test it.

**Deployment constraint:** workspace containers and Traefik must share the same
Docker daemon. The `codx-junior-dind` variant runs codx-junior (and its
workspaces) inside an inner `dockerd`; an outer Traefik cannot route to those
containers. Either run Traefik inside the same dind, or keep the host-socket
deployment for workspaces.

### P0-6. Proxied apps are not authenticated

`api/codx/junior/api/users.py:28`:

```python
@router.get("/forward-auth")
async def proxy_forward_auth(request: Request):
    ...
    return "ok"
```

The installer wires `codx-junior-auth` to this endpoint, so every generated
workspace route is public. The docs currently say the apps are "protected by
codx-junior's login"; that is not true.

The second half of the problem: the SPA authenticates with a Bearer header
(`client/src/api/connection.js`, `Authentication: Bearer <token>`), while a
browser navigating to an app URL sends **cookies**, not that header. So even a
real forward-auth implementation could not read the current credential.

`users.py` does set a `codx-session` cookie, but only on an *already
authenticated* call (`users.py:185`) and without `HttpOnly`/`Secure`; a fresh
login response does not set it.

**Fix:**
1. On successful login/OAuth, set a signed, `HttpOnly`, `Secure`,
   `SameSite=Lax` session cookie (path `/`) in addition to the Bearer token.
2. Implement `/api/forward-auth` to validate that cookie, resolve
   `X-Forwarded-Uri` → workspace/app, check workspace and app roles, and return
   `401` (or a redirect to the login page) or `200` with
   `X-Codx-User`/`X-Codx-Role` headers.
3. Configure the middleware with
   `forwardAuth.authResponseHeaders=X-Codx-User,X-Codx-Role` and
   `trustForwardHeader=true`.
4. Decide how an unauthenticated iframe is handled: forward a 302 to the
   codx-junior login page with a `redirect` parameter, or use Traefik's
   `errors` middleware. A bare 401 inside an iframe is a blank box.
5. Test with a real app: anonymous → 401/redirect; member → 200; wrong role →
   403; owner/project admin → 200.

Also note apps open in an **iframe** (`client/src/components/windowManager/AppWindow.vue`).
Cookies must be same-site (or `SameSite=None; Secure` for cross-site), and the
proxied app must not send `X-Frame-Options: DENY` / a restrictive
`frame-ancestors`. Add an optional per-app headers middleware to strip or
override those headers when the app is iframe-hosted.

### P0-7. Project admins have no path through the API

Every workspace management and Traefik endpoint uses `require_admin`
(`api/codx/junior/api/__init__.py:20`), which only checks
`user.role == "admin"`. Only the read-only `/workspaces/accessible` endpoint
uses the regular authenticated user. Project admins are represented by
`CodxUser.projects[].permissions == "admin"`
(`api/codx/junior/model/user.py:182`,
`api/codx/junior/security/user_management.py:205`), and the client already
exposes `isProjectAdmin` (`client/src/api/api.js:984`).

**Fix:** add a permission dependency:

```python
def require_workspace_admin(workspace_id: str,
                            user: CodxUser = Depends(get_authenticated_user)):
    workspace = get_workspace_or_404(workspace_id)
    if can_manage_workspace(user, workspace):
        return user
    raise HTTPException(403, "Workspace admin access required")
```

with `can_manage_workspace` allowing global admins and project admins of the
workspace's owner/attached projects (see §4.5). Use it for start/stop, files,
update, delete; use a read-level dependency for view/list. Add
`require_project_admin(project_id)` for project Traefik rules. Update the UI:
`ProjectSettings.vue` currently hides the Traefik tab unless global
`isAdmin` (`ProjectSettings.vue:858,867`); it should also show it for
`isProjectAdmin`.

### P0-8. Custom workspaces never receive Traefik labels

`workspaces/templates.py:render_template` returns immediately for
`template == "custom"`, and `DockerComposeEngine.traefik_labels` is only called
from the two `.j2` templates. `workspaces/manager.py`'s docstring says the
manager "exposes helpers to inject those labels automatically", but no such
injection exists.

If an admin uploads a hand-written compose for a "complex" workspace (the
explicit use case), nothing connects its services to Traefik unless the admin
writes labels by hand — and even then the service is not on Traefik's network.

**Fix:** generate a compose **override** from `Workspace.apps` instead of
editing the user's compose (see §4.5). It adds labels and the Traefik network
to the declared service. This also makes the existing custom-rule target
`workspace_app → <router-id>@docker` reliable.

---

## 4. Correctness gaps to fix while touching the code (P1)

1. **`path` is overloaded.** For container apps it is a public prefix; for
   external apps it is the target URL. `is_external_url(app.path)` is used as a
   type discriminator in `traefik/builder.py` and in the UI. Split into
   `path` + `target_url`/`target_type` (§4.2). This removes a whole class of
   bugs in the builder, the UI, and the compose templates.
2. **No compose-service mapping.** `WorkspaceApp` has `container_name` (legacy,
   unused) but no `service`. A workspace with several services cannot say
   "this app is `dsh` on port 3080". The templates apply every app's labels to
   every service, which is wrong for multi-service workspaces. Add
   `WorkspaceApp.service`.
3. **Label/builder drift.** `DockerComposeEngine.traefik_labels`
   (`compose.py:55`) and `traefik/builder.py:63-98` compute router IDs with
   slightly different sanitisation (`_` handling), and the builder expects
   `codx-ws-<slug>-<app>@docker`. One function must own the ID and labels.
4. **Labels for external-URL apps.** Both templates loop over all apps,
   including external-URL apps, and emit a load-balancer port from
   `app.port=None`. Only container apps belong in compose labels; URL apps are
   published by the HTTP provider.
5. **Strip middleware edge cases.** The generated regex
   `^<prefix>/(.*)` does not match the bare prefix (`/ws/x/app`), and
   `PathPrefix('/app')` also matches `/appfoo`. Use
   `Path('/app') || PathPrefix('/app/')` and a strip regex like
   `^/app(?:/(.*))?$` → `/${1}` (the builder's `_strip_middleware` already does
   this; reuse it).
6. **No `Host` rule for container apps.** Generated labels only use
   `PathPrefix`, so the app is reachable on any host Traefik serves. Add
   `Host(<domain>)` (configurable per workspace/app) or document the choice.
7. **No entrypoints/TLS.** The labels never set `entrypoints` or
   `tls.certresolver`. Traefik attaches the router to every entrypoint; the
   `websecure` leg has no certificate configuration. Generate explicit
   `web` + `websecure` routers (or one router on `web` with a redirect
   middleware), with `tls.certresolver=sslresolver` where TLS is enabled.
8. **No `traefik.docker.network`.** A service attached to both the compose
   default network and the Traefik network may be routed to the wrong IP.
9. **No `passHostHeader` control.** Default is `true` (what DSH needs); the
   HTTP provider sets `passHostHeader: false` for external apps, which can
   break apps that build absolute URLs or check `Host`. Make it configurable.
10. **Status parsing assumes JSONL.** `compose.py:104` parses one JSON object per
    line. `docker compose ps --format json` returns a JSON **array** in recent
    Compose releases. Handle both.
11. **Delete is incomplete.** API delete removes only the settings entry; the
    global manager's delete stops compose and removes the folder. Unify:
    `down -v --remove-orphans`, disconnect/delete the network, optionally keep
    volumes, delete files only with an explicit flag.
12. **File API is flat and path handling is unsafe.**
    `workspace_manager.py:185` uses `requested_path.startswith(workspace_folder)`,
    which accepts `/workspaces-evil`; symlinks escape; the API's
    `_get_workspace_dir` does not validate `folder_path` containment. Use
    `Path.resolve()` + `is_relative_to(root)` and `lstat`/`O_NOFOLLOW` for
    every read/write. Support nested paths, uploads, binary files, size limits
    and atomic writes.
13. **Two managers, three generations.** `workspaces/manager.py`,
    `workspaces/workspace_manager.py`, and the wiki describe different APIs.
    Consolidate (P0-1). The wiki already has the target façade; implement it.
14. **AI generation conflicts with the platform.** `DOCKER_COMPOSE_PROMPT`
    asks for "a Traefik reverse proxy service", a second proxy inside the
    workspace. The generated nginx.conf is never wired to anything. Either
    drop the AI generator from the create path (templates + override are
    deterministic) or constrain it to app-level Dockerfiles and validate the
    result. Never let AI write files outside the workspace or overwrite
    `compose.codx.yaml`.
15. **Environment injection.** `_compose_env` merges `workspace.env` into the
    subprocess environment. A workspace editor could inject `COMPOSE_FILE`,
    `DOCKER_HOST`, `PATH`, `LD_PRELOAD`, etc. Only allow a safe subset for
    interpolation, and keep app env in the compose file.
16. **Concurrent settings writes.** `GlobalSettingsManager.write_section`
    writes directly (no temp file + rename, no lock). Two workspace updates can
    lose data or corrupt the section. Add a file lock or move each workspace to
    its own JSON file and treat the settings list as an index.
17. **Default workspace is not provisioned.** `DEFAULT_WORKSPACE` points at
    `folder_path=codx-junior-workspace-default` with apps at
    `/workspace-default/*`, but the shipped installer never copies the legacy
    `codx-junior-installer/codx-junior/workspaces/codx-junior-workspace-default`
    folder to the workspaces root. Seed it on install/migrate.
18. **Compose resources.** `WorkspaceResources` is only rendered into the
    `static-site` template's `deploy.resources.limits`; `dev-stack` and
    `custom` ignore CPU/memory. Apply limits in the generated override
    (`cpus`, `mem_limit`, `shm_size`, `pids_limit`) so they work for every
    template.
19. **No `sysbox` preflight.** `dev-stack` uses `runtime: sysbox-runc`.
    If Sysbox is not installed on the host, `compose up` fails with a cryptic
    error. Check `docker info` runtimes and fail with an actionable message.
20. **Docs are ahead of the code.** `docs/features/workspaces.md` says start,
    stop, restart and logs work; they do not. Update after the runtime lands.

---

## 5. Target design

### 5.1. Two scopes, two stores

Project workspaces and infrastructure services have different owners and
lifetimes, so they must not share one settings list:

* **Project workspaces** are stored in the owning project's settings
  (`CODXJuniorSettings.workspaces`, persisted in `.codx/project.json`) and in
  `<project>/.codx/workspaces/<id>/`. They travel with the project, so a new
  installation can provision them from the project repository.
* **Infrastructure services** are stored in the global settings
  (`GlobalSettings.services`) and in the global services root. They are
  installed once per codx-junior instance and shared by projects.

A small **runtime registry** merges both stores for the API, home menu and
Traefik builder. It is a read-through cache, never a second writable source of
truth. Project settings are canonical for project workspaces; global settings
are canonical for services. Do not keep a project workspace in global settings
as well.

Directory naming: use the **id**, not a user-supplied path:

```
<project>/.codx/workspaces/<workspace-id>/
  workspace.json            # optional legacy record; spec lives in project.json
  docker-compose.yaml       # user-owned, never rewritten
  compose.codx.yaml         # generated override (labels, network, limits)
  .env                      # local secrets (0600, gitignored)
  .env.example              # portable env contract
  images/<app>/Dockerfile   # optional build contexts
  assets/                   # icons, scripts, config templates
  runtime/                  # generated state (launch URLs, last status)

$CODX_JUNIOR_SERVICES_FOLDER/<service-id>/
  docker-compose.yaml
  compose.codx.yaml
  .env / .env.example
  ...
```

Keep `folder_path` as a legacy/display slug and add an immutable `slug` for
URLs, compose project names and networks. Validate the slug
(`^[a-z0-9][a-z0-9-]{1,62}$`) and never use it as a filesystem path component
without validation.

### 5.2. Model changes

```python
class WorkspaceApp(BaseModel):
    id: str
    name: str
    description: str = ""
    icon: str = ""
    service: str = ""                 # compose service name (required for complex ws)
    port: Optional[int] = None        # container port; mutually exclusive with target_url
    target_url: str = ""              # external URL
    scheme: Literal["http", "https"] = "http"
    path: str = ""                    # public mount; derived as /ws/<slug>/<id> when empty
    host: str = ""                    # optional dedicated host
    strip_prefix: bool = True
    pass_host_header: bool = True
    websocket: bool = True
    entrypoints: List[str] = ["web", "websecure"]
    tls: bool = False
    transport: str = ""               # e.g. insecure-skip-verify@file
    roles: List[str] = []
    healthcheck: str = ""
    launch: Literal["url", "token", "none"] = "url"

class Workspace(BaseModel):
    id: str
    slug: str
    name: str
    description: str = ""
    owner_project_id: Optional[str] = None
    project_ids: List[str] = []
    user_ids: List[str] = []
    apps: List[WorkspaceApp] = []
    template: str = "custom"
    env: Dict[str, str] = {}
    resources: WorkspaceResources = ...
    use_sysbox: bool = False
    security: WorkspaceSecurity = ...  # allow_unsafe, allowed_registries, ...
    status: WorkspaceStatus = STOPPED
    last_error: Optional[str] = None
    updated_at: Optional[str] = None
```

Keep a `folder_path` compatibility property mapping to `slug` until the UI and
stored settings are migrated. Migrate existing `path` values that are URLs to
`target_url` and derive the public path.

### 5.3. Compose override contract

Never rewrite `docker-compose.yaml`. Generate
`<workspace>/compose.codx.yaml` and run:

```bash
docker compose -p codx-ws-<short-id> \
  -f docker-compose.yaml \
  -f compose.codx.yaml \
  up -d --remove-orphans
```

The override:

* attaches each app service to the shared Traefik network with a stable alias;
* emits one router/service per app, using the same `router_id` as the custom
  rule builder;
* adds resource limits and `security_opt: no-new-privileges:true` defaults;
* does **not** touch URL apps (HTTP provider owns them);
* is regenerated on every start and on workspace/app update (atomic write).

Example:

```yaml
# compose.codx.yaml — generated, do not edit
services:
  dsh:
    networks:
      codx-junior-traefik:
        aliases: [codx-ws-abc123-dsh]
    labels:
      traefik.enable: "true"
      traefik.docker.network: "codx-junior-traefik"
      traefik.http.routers.codx-ws-abc123-dsh.rule: >-
        Host(`app.example.com`) && (Path(`/ws/dsh/dsh`) || PathPrefix(`/ws/dsh/dsh/`))
      traefik.http.routers.codx-ws-abc123-dsh.entrypoints: "web"
      traefik.http.routers.codx-ws-abc123-dsh.service: "codx-ws-abc123-dsh"
      traefik.http.routers.codx-ws-abc123-dsh.middlewares: "codx-ws-abc123-dsh-strip,codx-junior-auth"
      traefik.http.services.codx-ws-abc123-dsh.loadbalancer.server.port: "3080"
      traefik.http.middlewares.codx-ws-abc123-dsh-strip.replacepathregex.regex: "^/ws/dsh/dsh(?:/(.*))?$"
      traefik.http.middlewares.codx-ws-abc123-dsh-strip.replacepathregex.replacement: "/${1}"

networks:
  codx-junior-traefik:
    external: true
```

Validation: parse the user compose (PyYAML), verify every `app.service` exists,
and reject an app with neither `port` nor `target_url`. If an app has no
`service` and the compose has exactly one service, use it; otherwise fail with
a clear message.

**Do not** let the override be edited from the UI; mark it read-only in the file
browser.

### 5.4. Traefik route contract

* **Canonical path:** `/ws/<workspace-slug>/<app-slug>/` (trailing slash).
  Keep the existing `app.path` as an override for the legacy default
  workspace (`/workspace-default/...`). Validate uniqueness across all
  workspaces and reserve `/api`, `/traefik`, `/socket.io`, `/`.
* **Optional host mode:** `<app-slug>.<workspace-slug>.<domain>` for apps that
  cannot live under a path. Use the same routers/middlewares. This is the
  escape hatch for apps with absolute-root assets or `Host` checks.
* Always add `Path(...) || PathPrefix(.../)` and a strip regex that also matches
  the bare prefix.
* Generate `web` and `websecure` routers explicitly; set
  `tls.certresolver` for `websecure` (configurable).
* Set `traefik.docker.network` for every container app.
* Keep `passHostHeader=true` unless the app explicitly needs `false`.
* Feed the **same** ID/label functions to the compose override and to
  `traefik/builder.py`; delete the duplicate helpers.
* The HTTP provider stays the mechanism for `target_url` apps and custom rules.
  Its config is polled every 10s, so document the propagation delay and provide
  a "refresh" button in the UI (the preview endpoint already exists).
* The builder's `workspace_app` target should resolve to
  `<router-id>@docker` only after verifying the label service exists; otherwise
  show the same issue it shows for a missing app.

### 5.5. Permissions matrix

| Action | Global admin | Project admin (owner) | Project admin (attached) | Workspace user | Other |
| --- | --- | --- | --- | --- | --- |
| View workspace | yes | yes | yes | if in `user_ids` or project member | no |
| Open app | yes | yes | yes | if role allowed | no |
| Start / stop | yes | yes | yes (configurable) | no | no |
| Edit settings/files | yes | yes | no | no | no |
| Delete workspace | yes | yes | no | no | no |
| Project Traefik rules | yes | yes | no | no | no |
| Global Traefik rules | yes | no | no | no | no |

Implement `can_manage_workspace` and `can_view_workspace` in one module and use
them in the API and in `/api/forward-auth`. Do not rely on the UI filtering
(`api/workspaces.py:146`, `app.py:423` mutate copies and are bypassable).

### 5.6. File API

```
GET    /api/workspaces/{id}/files?path=            → { path, files: [...], folders: [...] }
GET    /api/workspaces/{id}/file?path=             → { path, content, encoding }
PUT    /api/workspaces/{id}/file?path=             → { content } (atomic)
DELETE /api/workspaces/{id}/file?path=
POST   /api/workspaces/{id}/files/upload?path=     → multipart
GET    /api/workspaces/{id}/files/download?path=
```

Rules:

* `path` is always relative to the workspace root; reject absolute paths,
  `..`, symlinks and NUL bytes. Resolve and check `is_relative_to(root)`.
* Max size per file and per workspace; stream uploads to a temp file and rename.
* Binary files: return metadata + base64 or a download URL, not `str`.
* `.env` and `workspace.json`: never include contents in list responses;
  require manage permission to read; redact in logs.
* `compose.codx.yaml`, `runtime/` are read-only through the API.
* Do not follow symlinks (`O_NOFOLLOW`), and set `0o600` on written files.

### 5.7. DSH example (the concrete acceptance case)

DSH's web app is compatible with a prefix-stripping proxy, with four
constraints from its own implementation:

* it injects `<base href="./">`, so relative assets/API/WebSocket URLs follow
  the external prefix;
* the token exchange only accepts `GET /` (which is what `/ws/dsh/` becomes
  after stripping) and then redirects to `./`, dropping the token;
* it rejects wildcard binds (`--host 0.0.0.0`) and non-loopback Host/Origin
  unless `--trusted-host` names the public authority;
* every request needs either the launch token or the signed cookie minted from
  it, and the cookie is bound to the public authority.

Workspace folder:

```
workspaces/<id>/
  docker-compose.yaml
  compose.codx.yaml        # generated
  image/Dockerfile
  image/entrypoint.sh
```

`image/entrypoint.sh`:

```sh
#!/bin/sh
set -eu
exec dsh --profile web --no-open \
  --host "$(hostname -i | awk '{print $1}')" \
  --port 3080 \
  --public-url "https://${CODX_JUNIOR_DOMAIN}/ws/dsh/" \
  --trusted-host "${CODX_JUNIOR_DOMAIN}"
```

App configuration:

```yaml
apps:
  - id: dsh
    name: DeepSeek Harness
    service: dsh
    port: 3080
    path: /ws/dsh
    strip_prefix: true
    pass_host_header: true   # DSH checks Host/Origin
    websocket: true
    launch: token
    roles: [admin]
```

Traefik route (generated):

```
Host(domain) && (Path(`/ws/dsh`) || PathPrefix(`/ws/dsh/`))
  → strip ^/ws/dsh(?:/(.*))?$ → /${1}
  → codx-junior-auth
  → dsh:3080
```

**Launch token:** codx-junior must open the tokenized URL, not the bare prefix.
Two options:

1. Extend the existing `dsh-codx-junior` bridge (it already injects
   `webServer` and uses `ctx.get`) with
   `GET /codx-junior/launch-url` that returns
   `connection.authenticatedUrl(publicUrl)`. codx-junior calls it with the
   shared bridge secret and redirects the iframe.
2. Scrape the `dsh web:` line from `docker compose logs dsh` on start and store
   it in `runtime/<app>.launch-url`.

Option 1 is robust across restarts. Add
`GET /api/workspaces/{id}/apps/{app_id}/launch` returning the URL (or a 302).
Without this, a user opening `/ws/dsh/` gets DSH's 401 page.

**Bridge URL:** the codx-junior DSH integration currently defaults to
`http://127.0.0.1:3080` (`integrations/dsh.py`). The containerized DSH is
reachable as `http://<container-alias>:3080` on the Traefik network (or the
workspace network). Store the bridge URL per workspace/app and pass it to
`DshConfig`; `127.0.0.1` is the API container, not DSH.

**Double auth:** codx-junior's forward-auth runs first, then DSH's own cookie.
That is acceptable for the first version, but document it. If DSH's login page
appears inside the iframe, the user has two sessions.

---

## 6. Change list by area

### 6.1 Backend

| File | Change |
| --- | --- |
| `api/codx/junior/workspaces/model.py` | Add `slug`, `owner_project_id`, `WorkspaceApp.service/target_url/host/strip_prefix/pass_host_header/websocket/entrypoints/tls/transport/launch/healthcheck`, `Workspace.security`; keep `folder_path` compatibility. |
| `api/codx/junior/workspaces/workspace_manager.py` | Replace with the documented façade: constructor `(settings=None, engine=None)`, `create/update/delete`, `start/stop/restart`, `status/logs`, `provision`, `files`, `lock`; import `asyncio`; use `Path.resolve().is_relative_to`. |
| `api/codx/junior/workspaces/manager.py` | Delete, or reduce to the global persistence adapter. Do not keep two lifecycle managers. |
| `api/codx/junior/workspaces/engines/compose.py` | Use `-f docker-compose.yaml -f compose.codx.yaml`; configurable project/network/Traefik names; handle array JSON from `compose ps`; reconciliation; locking; `down -v` on delete; sysbox preflight; resource limits. |
| `api/codx/junior/workspaces/engines/labels.py` (new) | One source for router IDs, labels, strip middleware, and the compose override. Used by the engine and `traefik/builder.py`. |
| `api/codx/junior/workspaces/templates.py` | Keep Jinja for built-ins, but render the override separately; do not put labels in `.j2` service definitions. Add a `dsh` template. |
| `api/codx/junior/workspaces/workspace_file_generator.py` | Remove "Traefik service" from the prompt; scope generation to app Dockerfiles; validate output; never write `compose.codx.yaml`. |
| `api/codx/junior/api/workspaces.py` | Fix create/update payloads; add GET one, templates, start/stop/restart/status/logs/generate/launch; tree file API; permission dependencies; delete cleanup; route ordering (`/accessible` before `/{id}`). |
| `api/codx/junior/api/workspace_models.py` | Make request/response models match the client; add `WorkspaceSummary` without secrets. |
| `api/codx/junior/traefik/builder.py` | Use the shared label module; remove `workspace_app_key`/`external_app_key` drift; honor `entrypoints`, `tls`, `passHostHeader`, `host`; verify label service existence. |
| `api/codx/junior/traefik/manager.py` | Filter targets by project for project admins; add `require_project_admin` to project rule endpoints; include workspaces by owner. |
| `api/codx/junior/api/users.py` | Real `/api/forward-auth`; set `codx-session` on login/OAuth with `HttpOnly/Secure/SameSite`; resolve path → workspace/app and enforce roles. |
| `api/codx/junior/api/__init__.py` | Add `require_project_admin`, `require_workspace_admin`, `require_workspace_view`. |
| `api/codx/junior/globals.py` | Fix the default `CODX_JUNIOR_WORKSPACES_FOLDER`; add traefik network/container env vars. |
| `api/codx/junior/app.py` | Use the shared workspace access helper instead of duplicating filters; register auth/socket events for status. |

### 6.2 Frontend

| File | Change |
| --- | --- |
| `client/src/api/modules/workspaces.js` | Align with the final endpoints; add `launch`, `restart`, `templates`, nested files, upload. |
| `client/src/components/workspaces/*` | Add `service`, route mode (path/host), strip/pass-host/websocket, launch; show real status/logs; poll status after start; file tree editor (not the project file browser). |
| `client/src/components/workspaces/WorkspaceFileEditor.vue` | Use the workspace file API, not `FileExplorerPanel(rootPath=folder_path)`. |
| `client/src/components/workspaces/WorkspacesList.vue` | Handle 403 for non-admins; use the accessible/manageable list; show project filter. |
| `client/src/views/ProjectSettings.vue` | Show the Traefik tab for `isProjectAdmin`, not only `isAdmin`. |
| `client/src/components/workspaces/WorkspaceCard.vue` | "Open" uses `path`/`launch`; show the workspace path and copy button. |
| `client/src/components/traefik/*` | Target picker filtered by project; show generated workspace routes; "open app"; project-admin save. |

### 6.3 Installer / deployment

| File | Change |
| --- | --- |
| `codx-junior-installer/codx-junior/docker-compose.yaml` | Identity-mount the workspaces root; env `CODX_JUNIOR_WORKSPACES_FOLDER`, `CODX_JUNIOR_TRAEFIK_NETWORK`, `CODX_JUNIOR_TRAEFIK_CONTAINER`; add `group_add` for the docker socket if needed; add the shared Traefik network; keep the HTTP provider endpoint. |
| `codx-junior-installer/codx-junior/.env.example` | Document the new variables. |
| `codx-junior-installer/codx-junior/api/Dockerfile.api` | Ensure `docker` CLI + compose plugin are installed (the current Dockerfile does not install them; `install_api.sh` calls `codx docker`, whose implementation is outside this repo — verify). |
| `codx-junior-installer/codx-junior/traefik/traefik.yaml` | Keep the HTTP provider; ensure the Docker provider sees the shared network; add `forwardAuth.authResponseHeaders` in the installer labels. |
| `codx-junior-installer/codx-junior/workspaces/*` | Seed/migrate the legacy default workspace into the new root; keep the legacy compose as a `custom` example. |
| `codx-junior-installer/codx-junior-dind/*` | Document that an outer Traefik cannot route to containers in an inner daemon; either run Traefik inside or don't use dind for workspaces. |

### 6.4 Docs / tests

* Update `docs/features/workspaces.md` to match reality; add a "Container apps
  and Traefik" page with the path/host contract and the DSH recipe.
* Add `docs/features/workspaces-dsh.md` (or extend `dsh-sync.md`).
* Tests:
  * unit: slug/path validation, permission matrix, compose override snapshot,
    label/builder ID equality, strip regex, URL-app exclusion;
  * API: create/update/start/stop/status/logs/files with mocked subprocess;
    status parser for JSON array and JSONL; path traversal;
  * frontend: workspaces API module contract;
  * integration (Docker): nginx workspace + Traefik route + auth 401/200;
    DSH smoke (launch URL, cookie, iframe).

---

## 7. Phased delivery

### Phase 0 — make it not broken (1–2 days)

1. Consolidate the manager; fix create; add `GET /workspaces/{id}`.
2. Fix the UI/API contract (`update`, files, status) and the create payload.
3. Mount the workspaces root and fix the default folder.
4. Fix Traefik container/network names and attach strategy.
5. Add `require_workspace_admin` / `require_project_admin` and client gating.

**Acceptance:** create a workspace from the UI, see it in the list, edit its
compose, start it, see `running`, read logs, stop it, delete it without
orphans.

### Phase 1 — publish container apps (2–4 days)

1. Generate `compose.codx.yaml` with labels/network/limits.
2. Add the shared Traefik network and `traefik.docker.network`.
3. Add path/host route contract, entrypoints/TLS, strip middleware.
4. Implement the real session cookie + `/api/forward-auth` + RBAC.
5. Add `GET /{id}/apps/{app}/launch`.

**Acceptance:** a custom workspace with one service is reachable at
`/ws/<slug>/<app>/`; anonymous → 401/redirect; member → 200; project admin can
start/stop and see it; route survives an API/Traefik restart.

### Phase 2 — complex workspaces / DSH (3–5 days)

1. Add `service`, multiple apps, nested file API, uploads, build contexts.
2. Add the DSH template and launch-url bridge endpoint.
3. Add status reconciliation, async start + socket events, compose policy.
4. Add sysbox preflight and resource limits.

**Acceptance:** DSH runs in a container, is reachable at `/ws/dsh/`, opens in
the codx-junior iframe, and its codx-junior bridge works over the container
network.

### Phase 3 — hardening / scale

Per-app host routing, custom domains/TLS, quotas, per-workspace networks,
backup/export, remote Docker, audit log, image allowlist.

---

## 8. Open decisions

1. **Global vs project storage.** Resolved: project workspaces live in the
   project settings (`project.json` + `.codx/workspaces`); infrastructure
   services live in global settings. The runtime registry is read-only and
   merges both. Truly shared multi-project environments are modelled as
   services, not as a project workspace.
2. **Shared vs per-workspace network.** Shared Traefik network is simpler and
   reliable; per-workspace networks give isolation but need connect/reconcile.
3. **Path vs host routing.** `/ws/<slug>/<app>/` satisfies the requirement;
   host mode is the escape hatch for apps that cannot live under a prefix.
4. **Project-admin trust.** Running arbitrary compose with the host Docker
   socket is root-equivalent. Choose: (a) project admins get a validated
   compose policy (recommended), or (b) only global admins can run arbitrary
   compose and project admins can only start/stop pre-approved workspaces.
5. **Launch tokens.** Exposing DSH's tokenized URL to the iframe is required;
   decide whether it is returned only to users who pass the workspace ACL and
   whether it is logged.
6. **Workspace secrets.** `.env` is currently plain text. Decide whether to add
   an encrypted secret store or document file permissions as the boundary.

---

## 9. References

* `api/codx/junior/api/workspaces.py`
* `api/codx/junior/workspaces/model.py`
* `api/codx/junior/workspaces/workspace_manager.py`
* `api/codx/junior/workspaces/manager.py`
* `api/codx/junior/workspaces/engines/compose.py`
* `api/codx/junior/traefik/builder.py`
* `api/codx/junior/api/traefik.py`
* `api/codx/junior/api/users.py`
* `client/src/api/modules/workspaces.js`
* `client/src/components/workspaces/`
* `codx-junior-installer/codx-junior/docker-compose.yaml`
* `docs/features/workspaces.md`
* `dsh-codx-junior/` (bridge plugin)
* `api/codx/junior/integrations/dsh.py`
