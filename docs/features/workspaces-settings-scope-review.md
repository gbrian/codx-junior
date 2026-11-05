# Workspaces settings: global services vs project workspaces

**Scope:** review of the workspace settings model after the routing review.
**Requirement:**

1. The **global** workspaces settings must let an admin add new **services** to
   the infrastructure.
2. A workspace that belongs to a **project** must live in that project's
   settings, so the project can be installed in a new codx-junior instance and
   bring its workspaces with it.

**Verdict:** the current model cannot satisfy both requirements because it has
only one store. `GlobalSettings.workspaces` holds every workspace, project
ownership is a filter (`project_ids`), and project settings have no
`workspaces` field at all. The project-scoped manager exists but the API never
uses it. The fix is a two-scope model:

| Scope | Settings store | File store | Owner |
| --- | --- | --- | --- |
| **Infrastructure service** | `GlobalSettings.services` | `$CODX_JUNIOR_SERVICES_FOLDER/<id>/` | global admin |
| **Project workspace** | `CODXJuniorSettings.workspaces` → `.codx/project.json` | `<project>/.codx/workspaces/<id>/` | project admin |

A read-only runtime registry merges both stores for the API, home menu and
Traefik builder. Each item has exactly one writable home.

---

## 1. Current state

| Item | Location | What it is today | Problem |
| --- | --- | --- | --- |
| `GlobalSettings.workspaces` | `api/codx/junior/model/model.py:304` | The **only** workspace list, persisted in `settings/workspaces.json`. Default `[DEFAULT_WORKSPACE]`. | Contains both infrastructure environments and project-owned workspaces. Global to the installation; not portable with a project. |
| `DEFAULT_WORKSPACE` | `api/codx/junior/model/workspace.py` | Coder / Desktop / LiteLLM / Traefik apps, `project_ids=["*"]`. | This is an **infrastructure** definition, but it is modelled as a workspace. |
| `workspace_start_port` / `workspace_end_port` | `model.py:305-306` | Port range settings. | Not used by any runtime code. |
| `workspace_docker_settings` | `model.py:307` | Arbitrary dict, edited by the old UI. | Not read by the engine. |
| `CODXJuniorSettings.workspaces` | **missing** | Project settings (`api/codx/junior/settings.py:57`) have no workspace field. | Project workspaces cannot travel in `project.json`. |
| `CODXJuniorProject.workspaces` | `api/codx/junior/settings.py:726` | Response-only `List[Dict]`, never populated by the backend. | Dead field; it suggests project workspaces exist when they do not. |
| `CODXJuniorSettings.get_project_workspaces()` | `settings.py:217` | Filters `GlobalSettings.workspaces` by `project_id`. | A view, not storage. Deleting the project leaves the workspace in global settings; cloning the project does not bring it. |
| Project workspace manager | `api/codx/junior/workspaces/workspace_manager.py:41` | Persists `<project>/.codx/workspaces/<id>/<id>.workspace` + files. | Correct direction, but the API does not use it; the spec is a separate file, not `project.json`; missing `asyncio` import; no lifecycle. |
| Session methods | `api/codx/junior/engine/session.py:204,328` | Already expose project-scoped `list/get/save/delete_workspace`. | Unused by the workspace API, which reads global settings. |
| Global workspace API | `api/codx/junior/api/workspaces.py:104` | Reads/writes `GlobalSettings.workspaces`. | Project workspaces are global. Create is broken (`WorkspaceManager()` at line 231). |
| `/api/projects` | `api/codx/junior/app.py:401` | Returns workspaces filtered from global. | Client store `API.allWorkspaces` is a global list; project settings never carry them. |
| Traefik view/config | `api/codx/junior/traefik/manager.py:229,271,294` | Builds routes from `GlobalSettings.workspaces`. | Project workspaces and services are not distinguished; no per-project source. |
| Global settings UI | `client/src/views/GlobalSettings.vue:84,164,198` | “Workspaces” tab edits `settings.workspaces` and saves the full global settings. | No way to add a service (image/compose/ports/routes), only an old name/projects/apps form. |
| Project settings UI | `client/src/views/ProjectSettings.vue:839` | No “Workspaces” tab. | Project admins cannot see or manage their workspaces. |
| Settings validation | `api/codx/junior/settings_manager.py:262` | `write_section` writes JSON directly; no section validators are registered. | A malformed `workspaces`/`services` entry can make `read_global_settings()` fall back to `GlobalSettings()` (`global_settings.py:104`), silently discarding settings. |

Existing evidence on disk: `.codx/workspaces/9e3d7f6b-.../` contains a
`.workspace` JSON, an empty `docker-compose.yaml`, `.env`, `nginx.conf` and an
`App/` folder. So the project-scoped store has been exercised, but its
definition is not in `project.json`, and the API ignores it.

---

## 2. Why the current split fails

* **Not portable.** Copying/cloning a project to a new instance copies the
  repository and `.codx`, but the workspace definitions live in the *old*
  instance's global settings. The new instance sees no project workspaces.
* **Not scoped.** A project admin cannot manage a workspace without being a
  global admin, because the only write path is the global settings endpoint.
* **No service catalog.** To add a new infrastructure service (e.g. DSH,
  LiteLLM, a shared database), an admin can only add another entry to the
  workspace list. There is no image/compose/ports/routes/env contract, no
  start/stop, and no distinction between “shared service” and “project
  environment”.
* **Confusing ownership.** `project_ids` is used both for “mount these
  projects into the container” and “show this workspace to these projects”. A
  workspace can be attached to several projects, so it cannot belong to one
  project's settings without a clear owner.
* **Runtime state in settings.** `Workspace.status`/`updated_at` are part of
  the model. If stored in `project.json`, every start/stop rewrites the project
  settings and produces noisy diffs.

---

## 3. Target model

Use **one runtime model with a scope discriminator** and **two settings
stores**. This keeps the compose/Traefik engine shared while giving each item a
single owner.

```python
class WorkspaceScope(str, Enum):
    SERVICE = "service"      # global infrastructure service
    PROJECT = "project"      # project-owned development workspace


class WorkspaceSpec(BaseModel):
    """Portable definition; safe to store in project.json / services.json."""
    id: str
    scope: WorkspaceScope = WorkspaceScope.PROJECT
    slug: str
    name: str
    description: str = ""
    icon: str = ""
    enabled: bool = True

    # Ownership / visibility
    owner_project_id: Optional[str] = None   # project scope
    project_ids: List[str] = []             # mounts (project) / visibility (service)

    # Runtime definition
    template: str = "custom"
    compose_file: str = "docker-compose.yaml"
    apps: List[WorkspaceApp] = []
    env: Dict[str, str] = {}                 # values or ${VAR} references
    env_required: List[str] = []             # portable contract
    resources: WorkspaceResources = ...
    use_sysbox: bool = False
    auto_start: bool = False
    security: WorkspaceSecurity = ...


class Workspace(WorkspaceSpec):
    """Runtime record: spec + live state, never persisted in project.json."""
    status: WorkspaceStatus = WorkspaceStatus.STOPPED
    last_error: str = ""
    updated_at: Optional[str] = None
```

Then:

```python
class GlobalSettings(BaseModel):
    # NEW: shared infrastructure services, added from Global Settings
    services: List[WorkspaceSpec] = []       # scope == SERVICE
    # DEPRECATED: migrated on startup, kept only for backward compatibility
    # workspaces: List[WorkspaceSpec] = []

class CODXJuniorSettings(BaseModel):
    # NEW: project-owned workspaces, persisted in .codx/project.json
    workspaces: List[WorkspaceSpec] = []     # scope == PROJECT
```

Alternative: a separate `InfraService` model if services grow fields that do
not apply to workspaces (replicas, ingress, registry credentials, host
constraints). Sharing `WorkspaceSpec` is the smaller change and reuses the
compose engine; start there and split later if needed.

### 3.1. Global settings: infrastructure services

`GlobalSettings.services` is the catalog the admin edits in **Global Settings →
Infrastructure services**. It must support:

* **Add service** from a template (`traefik`, `litellm`, `coder`, `desktop`,
  `dsh`, `postgres`, `redis`, `custom`) or a user-provided compose.
* Image or compose file, command, ports, public path/host, strip-prefix,
  auth/roles, env, volumes, networks, healthcheck, resources.
* Visibility: `project_ids` (`["*"]` = every project) used by the UI and by
  project workspace dependencies.
* Lifecycle: install/provision, start/stop/restart, status, logs.
* Routes: generated by the same Traefik label builder as workspaces; a service
  can also be external-URL only.
* The default Coder/Desktop/LiteLLM/Traefik environment is seeded here as
  **services** (`DEFAULT_SERVICES`), not as a global workspace.

Global services are per-instance. They do not travel with a project; export /
import or installer seeding is the portability mechanism for them.

### 3.2. Project settings: project workspaces

`CODXJuniorSettings.workspaces` is stored in `.codx/project.json` by
`save_project()` (`settings.py:623`). `project.json` is already committed
(`.codx/project.json` is not ignored by `.gitignore`), so the definitions travel
with the repository.

What goes in `project.json`:

* id, slug, name, description, template;
* apps (service/port/path/host/roles) and routes;
* resources, `use_sysbox`, `auto_start`;
* `env` references (`${VAR}`) and `env_required` — **never secret values**;
* compose file name / inline compose; image/build references.

What stays next to it in `.codx/workspaces/<id>/`:

* `docker-compose.yaml` (user-owned, committed);
* `compose.codx.yaml` (generated, gitignored or committed but read-only);
* `images/`, `assets/`, `scripts/` (committed);
* `.env.example` (committed), `.env` (local, gitignored);
* `runtime/` (generated, gitignored).

The `.codx/workspaces/<id>/<id>.workspace` file used today becomes redundant:
migrate its content into `project.json` and keep it only as a backup (or delete
it after migration).

### 3.3. Ownership rules

* A project workspace has exactly one `owner_project_id`. It may mount other
  projects through `project_ids`, but it is managed by the owner's admins.
* A truly shared, multi-project environment is a **service**, not a project
  workspace. If it must be project-owned, make it a workspace of the owner and
  let the other projects reference it; do not duplicate it in two stores.
* Project workspace IDs are UUIDs. The runtime registry can build a global
  index by scanning `find_all_projects()` and reading each
  `settings.workspaces`; no global ID list is needed.

---

## 4. Runtime registry (read-through)

Add a `WorkspaceRegistry` (or extend `traefik/project_cache.py`) that returns:

```python
{
  "services": [WorkspaceSpec(scope=SERVICE), ...],       # global settings
  "project_workspaces": [WorkspaceSpec(scope=PROJECT), ...],  # all projects
}
```

Rules:

* Project settings are canonical; the registry never writes them.
* Cache with a short TTL; invalidate immediately on project settings save
  (`api_save_settings` already calls `update_project_rules` — do the same for
  workspaces).
* Traefik `build_config`/`build_view` consumes the registry instead of
  `GlobalSettings.workspaces`.
* `/api/projects` returns the project's own `settings.workspaces` (not a global
  filter) plus the services visible to that project.
* Home menu / `/api/workspaces/accessible` merges both and filters by user
  access.

This preserves the global nature of Traefik and the Docker daemon while keeping
project data portable.

---

## 5. Adding a service (global settings)

### 5.1. Service spec

Reuse `WorkspaceSpec` with `scope=SERVICE`. Minimum fields:

| Field | Meaning |
| --- | --- |
| `id` / `slug` / `name` / `description` / `icon` | identity and display |
| `template` | `traefik`, `litellm`, `dsh`, `postgres`, `redis`, `custom` |
| `compose_file` or `image` + `command` | what to run |
| `apps[]` | public routes: service, port, path/host, strip, auth, roles |
| `env` / `env_required` / `.env` | configuration and secrets |
| `volumes` / `networks` | persistence and connectivity |
| `project_ids` | visibility (`["*"]` = all) |
| `auto_start` / `enabled` | lifecycle |
| `resources` / `security` | limits and policy |

### 5.2. Add-service flow

1. Admin opens **Global Settings → Infrastructure services → Add service**.
2. Chooses a template or “custom compose”.
3. Fills name/slug, image or compose, port and public path, env, visibility,
   auto-start.
4. Backend creates `$CODX_JUNIOR_SERVICES_FOLDER/<id>/`, renders the compose
   (if template), validates it, generates `compose.codx.yaml`, saves the spec in
   `GlobalSettings.services`, and returns it.
5. “Install/Start” runs the workspace engine (`compose up -d`), attaches the
   Traefik network and publishes the route.
6. Status/logs/route preview are the same endpoints as workspaces, scoped by
   `service`.

### 5.3. Example: DSH as an infrastructure service

```yaml
# GlobalSettings.services[0] (shape)
id: dsh
scope: service
slug: dsh
name: DeepSeek Harness
template: custom
project_ids: ["*"]
auto_start: true
apps:
  - id: dsh
    name: DSH
    service: dsh
    port: 3080
    path: /ws/dsh
    strip_prefix: true
    pass_host_header: true
    websocket: true
    launch: token
```

The folder contains the DSH `Dockerfile`, `entrypoint.sh`,
`docker-compose.yaml` and `.env.example`. The generated route, launch URL and
bridge configuration are the same as in the DSH section of
[workspaces-container-routing-review.md](workspaces-container-routing-review.md).

Project workspaces can declare a dependency on it:

```yaml
depends_on_services: [dsh]
```

The project workspace is still stored in `project.json`; only the shared DSH
service is global.

---

## 6. Project portability (new instance)

When the project is cloned/imported into a new codx-junior:

1. `.codx/project.json` carries `workspaces` specs.
2. `.codx/workspaces/<id>/` carries compose, Dockerfiles, assets and
   `.env.example`.
3. `find_all_projects()` discovers the project; the workspace registry sees the
   specs.
4. On project load (or “Install” in the UI), `provision`:
   * creates missing directories;
   * renders template files only when absent (never overwrites custom files);
   * checks `env_required` and reports missing variables instead of starting a
     broken container;
   * pulls/builds images;
   * optionally starts if `auto_start`.
5. The UI shows `not_installed` / `stopped` / `starting` / `running` /
   `degraded` (missing service dependency or env).

Commit / ignore contract:

| Path | Commit? | Why |
| --- | --- | --- |
| `.codx/project.json` | yes | workspace specs |
| `.codx/workspaces/<id>/docker-compose.yaml` | yes | user definition |
| `.codx/workspaces/<id>/images/`, `assets/`, `scripts/` | yes | build/run resources |
| `.codx/workspaces/<id>/.env.example` | yes | portable env contract |
| `.codx/workspaces/<id>/.env` | **no** | secrets |
| `.codx/workspaces/<id>/runtime/` | **no** | generated launch URLs/state |
| `.codx/workspaces/<id>/compose.codx.yaml` | optional | generated; safe to regenerate |

Add the ignore rules to `.gitignore`:

```gitignore
.codx/workspaces/*/.env
.codx/workspaces/*/runtime/
```

If the workspace uses an external image, a new instance must be able to pull it
(registry credentials); if it uses `build:`, the context is in the project.
Document `image`/`build` in the spec.

---

## 7. API changes

### 7.1. Services (global)

```
GET    /api/services
POST   /api/services
GET    /api/services/{id}
PUT    /api/services/{id}
DELETE /api/services/{id}
POST   /api/services/{id}/install
POST   /api/services/{id}/start|stop|restart
GET    /api/services/{id}/status
GET    /api/services/{id}/logs?tail=
GET    /api/services/{id}/files?path=
GET/PUT/DELETE /api/services/{id}/file?path=
GET    /api/services/{id}/routes
```

### 7.2. Project workspaces

```
GET    /api/projects/{project_id}/workspaces
POST   /api/projects/{project_id}/workspaces
GET    /api/projects/{project_id}/workspaces/{workspace_id}
PUT    /api/projects/{project_id}/workspaces/{workspace_id}
DELETE /api/projects/{project_id}/workspaces/{workspace_id}
POST   /api/projects/{project_id}/workspaces/{workspace_id}/provision
POST   /api/projects/{project_id}/workspaces/{workspace_id}/start|stop|restart
GET    /api/projects/{project_id}/workspaces/{workspace_id}/status
GET    /api/projects/{project_id}/workspaces/{workspace_id}/logs
GET/PUT/DELETE .../files / .../file
GET    .../apps/{app_id}/launch
```

### 7.3. Aggregate / compatibility

* `GET /api/workspaces` → merged services + project workspaces (optional
  `project_id`, `scope`); keep the old path for the home menu.
* `GET /api/workspaces/accessible` → merged, filtered by user.
* `GET /api/projects` → each project's `settings.workspaces` plus visible
  services; the client store already reads `API.allWorkspaces`, so update it to
  the new shape.
* `PUT /api/settings` (project) accepts `workspaces` and saves `project.json`.
  Prefer the dedicated endpoints to avoid lost updates when two admins edit
  different workspaces.
* `PUT /api/global/settings` accepts `services`; do not accept the deprecated
  `workspaces` field from new clients.
* Register section validators for `services` and `workspaces` so a bad entry
  cannot wipe global settings (`read_global_settings` currently falls back to
  defaults on validation errors).

### 7.4. Permissions

* Services: global admin only (`require_admin`).
* Project workspaces: `require_project_admin(project_id)` (global admin or
  `permissions == "admin"`), with read access for project members.
* Project workspace create: owner project admin; mounting another project
  requires access to that project.
* Service visibility: `project_ids` (`["*"]` = all); only the global admin can
  change a service.
* Workspace app roles: enforce in `/api/forward-auth` and in the app listing.

---

## 8. UI changes

### Global Settings

* Rename the **Workspaces** tab to **Infrastructure services** (or add
  **Services** next to it while migrating).
* Service cards: icon, name, image/compose, status, route, visibility,
  start/stop, logs, edit.
* “Add service” wizard: template, compose/image, port, path/host, env,
  visibility, auto-start.
* Remove the old `Workspaces.vue` editor from global settings; it edits the
  wrong store and has no service fields.
* Keep the global Traefik tab; it should show service routes plus read-only
  project workspace routes.

### Project Settings

* Add a **Workspaces** tab (visible to project admins).
* List/create/edit/delete; start/stop/restart; status/logs; file tree editor;
  “Install”/“Provision” action; “Open” app/launch.
* Show portability hints: required env, image/build, missing service
  dependencies, `not_installed`.
* Saving the tab goes through the project workspace endpoints (or
  `PUT /api/settings` with `workspaces`), never the global settings.

### Menus / store

* `API.allWorkspaces` should be the merged accessible list; group by
  project/service.
* Workspaces menu: project name as group for project workspaces; “Services”
  group for global services.
* `projectApps` should include project workspaces + visible services.

---

## 9. Migration

Run at startup (idempotent, logged, with a backup of the global settings
sections):

1. Read `GlobalSettings.workspaces` (old field).
2. For each item:
   * If `project_ids` has exactly one real project and no `"*"`: move it to that
     project's `settings.workspaces` (`owner_project_id` = that project),
     remove it from global.
   * If `project_ids == ["*"]` or it has multiple projects: convert it to a
     service (`scope=SERVICE`) in `GlobalSettings.services`.
   * If it is `DEFAULT_WORKSPACE`: seed it as the default service(s).
3. Move files:
   * project workspace: from `$CODX_JUNIOR_WORKSPACES_FOLDER/<folder_path>` to
     `<project>/.codx/workspaces/<id>` (copy, then remove after verification);
   * service: to `$CODX_JUNIOR_SERVICES_FOLDER/<id>`.
4. Remove the deprecated `workspaces` field from the global settings write path
   after all items are migrated (keep it readable for one release).
5. Remove `CODXJuniorProject.workspaces` (the dead response field) so the base
   `CODXJuniorSettings.workspaces` is the single field.
6. Change `get_project_workspaces()` to return `self.workspaces` plus visible
   services, not a global filter.
7. Seed `DEFAULT_SERVICES` on a fresh install (Coder, Desktop, LiteLLM,
   Traefik) so the default environment still appears.
8. Add a `settings_version` marker to run the migration once.

Rollback: keep the old `workspaces.json` section and the old folders until the
admin confirms; the migration should be re-runnable.

---

## 10. Tests

* Settings:
  * `project.json` round-trip preserves `workspaces` and does not include
    runtime status;
  * global `services` round-trip; malformed service returns 422, does not reset
    global settings;
  * migration: single-project vs `"*"` vs default; files moved; IDs/routes
    stable.
* API:
  * project workspace CRUD writes to the project, not global;
  * service CRUD writes to global, not project;
  * permissions: global admin, project admin, member, other project admin;
  * aggregate `/api/workspaces` and `/api/projects` shapes.
* Portability:
  * copy `project.json` + `.codx/workspaces` into a fresh project root;
    discovery/provision produces the same workspace IDs and routes;
  * missing `env_required` reports a clear error;
  * missing service dependency marks `degraded`.
* Traefik:
  * registry merges services + project workspaces;
  * project view filters by owner/visibility;
  * service and workspace route IDs do not collide.
* UI:
  * global services add/edit/start/stop;
  * project settings workspaces tab for `isProjectAdmin`;
  * home menu groups services and project workspaces.

---

## 11. Risks / open decisions

1. **Shared multi-project workspace.** Recommendation: one owner project; if
   truly shared, make it a service. Document this so admins do not expect a
   workspace in two project settings.
2. **`project.json` size.** Keep compose/files in `.codx/workspaces`, not
   inline. If a workspace has a huge compose, reference it by relative path.
3. **Secrets in portable projects.** Never store secret values in
   `project.json`; use `${VAR}` + `env_required` + local `.env`. Decide whether
   to add an encrypted secret store later.
4. **Global service portability.** Services are per-instance. Provide
   export/import (`GET/POST /api/services/export|import`) or seed them from the
   installer; do not pretend they travel with projects.
5. **Schema compatibility.** Keep `GlobalSettings.workspaces` readable for one
   release; do not keep it writable. Remove `CODXJuniorProject.workspaces` to
   avoid two fields with the same name.
6. **Validation.** Register section validators and make
   `read_global_settings()` fail per-section instead of silently replacing all
   settings with defaults.
7. **Runtime state.** Keep `status`/`last_error`/`updated_at` out of
   `project.json`; compute them from Docker or a local `runtime/state.json`.
8. **Service dependencies.** A project workspace that references a global
   service must show `degraded` when that service is missing on a new instance;
   do not fail the whole project load.

---

## 12. Phased plan

### Phase 1 — settings split (1–2 days)

* Add `CODXJuniorSettings.workspaces` + `GlobalSettings.services`.
* Remove the dead `CODXJuniorProject.workspaces`; fix `get_project_workspaces`.
* Persist project workspaces in `project.json`; keep runtime state out.
* Migration + backup + `settings_version`.
* Unit tests for round-trip and migration.

### Phase 2 — project workspaces end-to-end (2–3 days)

* Use `WorkspaceManager(settings)` from the project session in the API.
* Add `/api/projects/{id}/workspaces` CRUD + lifecycle + files + provision.
* Add Project Settings → Workspaces tab for project admins.
* `/api/projects` and the client store return project workspaces.
* Portability test (copy project).

### Phase 3 — infrastructure services (3–5 days)

* Add `GlobalSettings.services` model + service templates + folder.
* Add `/api/services` CRUD + lifecycle + routes.
* Global Settings → Infrastructure services UI; seed `DEFAULT_SERVICES`.
* Reuse the compose engine and Traefik label builder.
* Export/import services.

### Phase 4 — runtime registry + permissions (2–3 days)

* `WorkspaceRegistry` merges services + project workspaces.
* Traefik builder/view/targets use the registry; project filtering.
* `require_project_admin`; forward-auth RBAC.
* Home menu grouping and accessible endpoint.

### Phase 5 — hardening

* Service dependencies/degraded state, env validation, compose policy,
  observability, docs.

---

## 13. References

* `api/codx/junior/model/model.py:304` — `GlobalSettings.workspaces`
* `api/codx/junior/model/workspace.py` — `DEFAULT_WORKSPACE`
* `api/codx/junior/settings.py:57,217,623,726` — project settings
* `api/codx/junior/workspaces/workspace_manager.py:41` — project store
* `api/codx/junior/engine/session.py:204,328` — project workspace methods
* `api/codx/junior/api/workspaces.py:104,231` — global API
* `api/codx/junior/app.py:401` — project response
* `api/codx/junior/traefik/manager.py:229,271,294` — Traefik sources
* `api/codx/junior/settings_manager.py:262` — section writes
* `client/src/views/GlobalSettings.vue:84,198` — global UI
* `client/src/views/ProjectSettings.vue:839` — project UI
* `client/src/store/project.js:697` — `API.allWorkspaces`
* `docs/features/workspaces-container-routing-review.md` — runtime/routing review
