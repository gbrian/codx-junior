"""
Docker infrastructure router (`/api/infra/*`).

Every route is **admin-only**: listing containers is harmless, but start/stop/
kill, container creation and any prune/removal are privileged operations. The
JSON contract is the one consumed by `client/src/api/modules/infra.js` (its
`INFRA_ENDPOINTS` array is the machine-readable version of the table below).

Route layout
------------
GET    /api/infra/hosts                      – Docker endpoints known to the API
GET    /api/infra/summary                    – host gauges + object counts
GET    /api/infra/containers                 – list (host, state, stack, q, stats)
GET    /api/infra/containers/{cid}           – container detail
GET    /api/infra/containers/{cid}/logs      – recent log lines (tail)
GET    /api/infra/containers/{cid}/stats     – CPU/memory series
POST   /api/infra/containers/{cid}/actions   – start|stop|restart|pause|unpause|kill
POST   /api/infra/containers                 – create & run a container
DELETE /api/infra/containers/{cid}           – remove a container
GET    /api/infra/stacks                     – compose projects (runtime + project scan)
POST   /api/infra/stacks/{name}/actions      – up|stop|restart|build|pull|down
GET    /api/infra/stacks/{name}/logs         – aggregated compose logs
GET    /api/infra/project/docker             – compose files + Dockerfiles of the active project
POST   /api/infra/project/dockerfiles/build  – build one discovered Dockerfile
GET    /api/infra/images                     – images
GET    /api/infra/volumes                    – volumes
GET    /api/infra/networks                   – networks
GET    /api/infra/events                     – recent daemon events
DELETE /api/infra/images/{id}                – remove one image
DELETE /api/infra/volumes/{name}             – remove one volume
DELETE /api/infra/networks/{id}              – remove one network
POST   /api/infra/maintenance/prune          – prune images|volumes|networks|build_cache|system

Note that container actions and stack actions are **different** operations: a
container action talks to the Engine API, a stack action shells out to
``docker compose`` (see `codx/junior/infra/compose.py`), because compose has no
Engine API equivalent.

Example
-------
```bash
# List running containers with live usage
curl -b "auth=…" "https://codx.local/api/infra/containers?host=host-local&state=running"

# Restart a container
curl -X POST -b "auth=…" -H 'Content-Type: application/json' \
     -d '{"action":"restart"}' \
     "https://codx.local/api/infra/containers/codx-junior/actions"

# Bring a compose project up (creates the missing containers) and tail its logs
curl -X POST -b "auth=…" -H 'Content-Type: application/json' \
     -d '{"action":"up","host_id":"host-local"}' \
     "https://codx.local/api/infra/stacks/codx-junior/actions"
curl -b "auth=…" "https://codx.local/api/infra/stacks/codx-junior/logs?tail=200"

# Scan the ACTIVE project for compose files and Dockerfiles, then start a
# compose project that has no container yet by passing its file path
curl -b "auth=…" "https://codx.local/api/infra/project/docker?host=host-local"
curl -X POST -b "auth=…" -H 'Content-Type: application/json' \
     -d '{"action":"up","path":"/projects/app/docker-compose.yml"}' \
     "https://codx.local/api/infra/stacks/app/actions"

# Build one discovered Dockerfile
curl -X POST -b "auth=…" -H 'Content-Type: application/json' \
     -d '{"path":"/projects/app/Dockerfile","tag":"app:dev"}' \
     "https://codx.local/api/infra/project/dockerfiles/build"

# Reclaim space: dangling images older than 7 days
curl -X POST -b "auth=…" -H 'Content-Type: application/json' \
     -d '{"target":"images","dangling_only":true,"older_than_days":7}' \
     "https://codx.local/api/infra/maintenance/prune"
```

Diagram
-------
flowchart LR
    A[Admin UI] -->|cookie auth| B{Router}
    B -->|require_admin| C[InfraManager]
    C --> D[DockerClient]
    D --> E[(Docker daemon)]
    B -->|stack actions| F[compose.py]
    F -->|docker compose CLI| E
    B -->|project scan| G[discovery.py]
    B -->|Dockerfile build| H[dockerfiles.py]
    H -->|docker build| E
"""

import logging
import os
from typing import Any, Dict, List, NoReturn, Optional, Tuple, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from codx.junior.api import require_admin
from codx.junior.infra import (
    DockerAPIError,
    DockerUnavailable,
    get_infra_manager,
)
from codx.junior.infra import compose as compose_stacks
from codx.junior.infra import discovery
from codx.junior.infra import dockerfiles as dockerfile_builder
from codx.junior.infra.models import (
    InfraActionRequest,
    InfraContainer,
    InfraContainerList,
    InfraContainerLogs,
    InfraCreateContainerRequest,
    InfraDockerfile,
    InfraEventList,
    InfraHostList,
    InfraImageList,
    InfraNetworkList,
    InfraOk,
    InfraProjectDocker,
    InfraProjectDockerfileBuildRequest,
    InfraProjectDockerfileBuildResult,
    InfraProjectInfo,
    InfraPruneRequest,
    InfraPruneResult,
    InfraStack,
    InfraStackActionRequest,
    InfraStackList,
    InfraStackLogs,
    InfraStats,
    InfraSummary,
    InfraVolumeList,
)
from codx.junior.model.model import CodxUser
from codx.junior.project.project_discover import get_all_projects_snapshot, is_path_child_of

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/infra", tags=["infra"])


# ── Helpers ────────────────────────────────────────────────────────────────────


def _raise_http(ex: Exception) -> NoReturn:
    """
    Translate infrastructure exceptions into HTTP errors.

    Mapping:
      * ``DockerUnavailable`` → 503 (daemon/socket/compose CLI not available)
      * ``DockerAPIError`` 403/404/409 → forwarded with the same status
        (predefined network, missing resource/stack, resource still in use)
      * ``DockerAPIError`` 504 → forwarded (a compose command timed out)
      * other ``DockerAPIError`` → 502 (daemon or compose rejected the operation)
      * ``KeyError`` → 404 (unknown host id)
      * ``ValueError`` → 400 (invalid request)
      * anything else → 500
    """
    if isinstance(ex, DockerUnavailable):
        raise HTTPException(status_code=503, detail=str(ex)) from ex

    if isinstance(ex, DockerAPIError):
        if ex.status_code in (403, 404, 409, 504):
            raise HTTPException(status_code=ex.status_code, detail=ex.message) from ex
        raise HTTPException(
            status_code=502, detail=f"Docker error: {ex.message}"
        ) from ex

    if isinstance(ex, KeyError):
        raise HTTPException(
            status_code=404, detail=f"Unknown host: {ex.args[0]}"
        ) from ex

    if isinstance(ex, ValueError):
        raise HTTPException(status_code=400, detail=str(ex)) from ex

    logger.exception("Infra request failed: %s", ex)
    raise HTTPException(status_code=500, detail=str(ex)) from ex


# ── Active project scan context ────────────────────────────────────────────────


def _project_scan_roots(
    request: Request,
) -> Tuple[Optional[Any], List[discovery.ScanRoot]]:
    """
    Resolve the scan roots of the ACTIVE codx-junior project.

    The active project is the one the request is scoped by (``codx_path`` query
    parameter / ``x-codx-path`` header, resolved by the app middleware). The
    roots are:

    * the project checkout (``abs_project_path``);
    * every registered project nested inside it (a "child project");
    * every project named in ``project_dependencies`` (even when it lives
      outside the checkout).

    The global project snapshot is used instead of ``get_sub_projects()``
    because the latter re-walks the whole checkout on every call; the snapshot
    is already maintained by the project discovery thread.

    Args:
        request: Incoming request (``request.state.codx_junior_session``).

    Returns:
        ``(settings, roots)``; ``(None, [])`` when the request is not scoped to
        a project, in which case the caller falls back to the runtime-only view.
    """
    session = getattr(request.state, "codx_junior_session", None)
    settings = getattr(session, "settings", None)
    if settings is None:
        return None, []

    codx_path = getattr(settings, "codx_path", "") or ""
    root = (
        getattr(settings, "abs_project_path", "")
        or getattr(settings, "project_path", "")
        or (os.path.dirname(codx_path) if codx_path else "")
    )
    if not root:
        return settings, []

    roots: List[discovery.ScanRoot] = [
        discovery.ScanRoot(
            path=root,
            project=getattr(settings, "project_name", "") or os.path.basename(root),
        )
    ]

    raw_dependencies = getattr(settings, "project_dependencies", "") or ""
    if isinstance(raw_dependencies, (list, tuple, set)):
        dependencies = {str(name).strip() for name in raw_dependencies if str(name).strip()}
    else:
        dependencies = {
            name.strip() for name in str(raw_dependencies).split(",") if name.strip()
        }
    try:
        snapshot = get_all_projects_snapshot() or {}
    except Exception as ex:  # discovery must never break the Docker view
        logger.debug("Cannot read the project snapshot: %s", ex)
        snapshot = {}

    for project in snapshot.values():
        project_path = getattr(project, "abs_project_path", "") or ""
        project_name = getattr(project, "project_name", "") or ""
        if not project_path or not project_name:
            continue
        if project_name in dependencies or is_path_child_of(project_path, root):
            roots.append(discovery.ScanRoot(path=project_path, project=project_name))

    return settings, discovery.normalize_scan_roots(roots)


def _project_info(settings: Any) -> InfraProjectInfo:
    """Build the project descriptor returned by the scan endpoint."""
    return InfraProjectInfo(
        name=getattr(settings, "project_name", "") or "",
        path=getattr(settings, "abs_project_path", "") or "",
        codx_path=getattr(settings, "codx_path", "") or "",
    )


def _dockerfile_model(asset: discovery.DockerfileAsset) -> InfraDockerfile:
    """Map a discovered Dockerfile dataclass into the API model."""
    return InfraDockerfile(
        name=asset.name,
        path=asset.path,
        relative_path=asset.relative_path,
        directory=asset.directory,
        context=asset.context,
        project=asset.project,
        project_root=asset.project_root,
        base_images=list(asset.base_images),
        stages=list(asset.stages),
        stage_count=asset.stage_count,
        has_dockerignore=asset.has_dockerignore,
        compose_project=asset.compose_project,
        compose_service=asset.compose_service,
    )


# ── Hosts ──────────────────────────────────────────────────────────────────────


@router.get(
    "/hosts",
    response_model=InfraHostList,
    summary="[Admin] List Docker hosts/endpoints",
)
def list_hosts(_: CodxUser = Depends(require_admin)) -> InfraHostList:
    """
    Return every Docker endpoint known to the API.

    By default this is the local daemon (``host-local``); extra endpoints can be
    declared through the ``CODX_JUNIOR_INFRA_HOSTS`` environment variable.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().hosts()
    except Exception as ex:
        _raise_http(ex)


@router.get(
    "/summary",
    response_model=InfraSummary,
    summary="[Admin] Host gauges and object counts",
)
def get_summary(
    host: Optional[str] = Query(None, description="Host id (see GET /api/infra/hosts)"),
    _: CodxUser = Depends(require_admin),
) -> InfraSummary:
    """
    Return host gauges (CPU, memory, disk) plus container/image/volume/network
    counts for the dashboard header.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().summary(host_id=host)
    except Exception as ex:
        _raise_http(ex)


# ── Containers: collection ─────────────────────────────────────────────────────


@router.get(
    "/containers",
    response_model=InfraContainerList,
    summary="[Admin] List containers",
)
def list_containers(
    host: Optional[str] = Query(None, description="Host id"),
    state: Optional[str] = Query(
        None, description="running | exited | paused | restarting | unhealthy | all"
    ),
    stack: Optional[str] = Query(None, description="Compose project name, or 'all'"),
    q: Optional[str] = Query(None, description="Filter on name, image, stack or service"),
    stats: bool = Query(True, description="Include live CPU/memory usage (slower)"),
    _: CodxUser = Depends(require_admin),
) -> InfraContainerList:
    """
    List containers of a host with optional filtering.

    Live usage is read with one ``/containers/{id}/stats`` call per *running*
    container, issued in parallel. Pass ``stats=false`` for a faster listing.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().containers(
            host_id=host,
            state=state,
            stack=stack,
            query=q,
            with_stats=stats,
        )
    except Exception as ex:
        _raise_http(ex)


@router.post(
    "/containers",
    response_model=InfraContainer,
    summary="[Admin] Create and run a container",
)
def create_container(
    payload: InfraCreateContainerRequest,
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraContainer:
    """
    Create a container and start it immediately.

    When ``stack`` is provided the container is labelled with the matching
    compose project/service labels so it shows up under that stack.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().create_container(payload, host_id=host)
    except Exception as ex:
        _raise_http(ex)


# ── Containers: single item ────────────────────────────────────────────────────


@router.get(
    "/containers/{container_id}/logs",
    response_model=InfraContainerLogs,
    summary="[Admin] Container log lines",
)
def get_container_logs(
    container_id: str,
    tail: int = Query(200, ge=1, le=2000, description="Number of lines"),
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraContainerLogs:
    """
    Return the most recent log lines of a container, parsed into
    ``{ts, level, msg}`` records (level is inferred from the message text).

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().logs(container_id, tail=tail, host_id=host)
    except Exception as ex:
        _raise_http(ex)


@router.get(
    "/containers/{container_id}/stats",
    response_model=InfraStats,
    summary="[Admin] Container CPU/memory stats",
)
def get_container_stats(
    container_id: str,
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraStats:
    """
    Return the current counters of a container plus the CPU/memory time series.

    The daemon only provides an instantaneous sample, so the series is an
    in-process ring buffer that fills up while the UI keeps polling.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().stats(container_id, host_id=host)
    except Exception as ex:
        _raise_http(ex)


@router.post(
    "/containers/{container_id}/actions",
    response_model=InfraContainer,
    summary="[Admin] Run a container lifecycle action",
)
def container_action(
    container_id: str,
    request: InfraActionRequest,
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraContainer:
    """
    Execute ``start``, ``stop``, ``restart``, ``pause``, ``unpause`` or ``kill``
    on a container and return its refreshed state.

    ``stop``/``restart`` use a 10 second grace period before killing.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().action(container_id, request, host_id=host)
    except Exception as ex:
        _raise_http(ex)


@router.get(
    "/containers/{container_id}",
    response_model=InfraContainer,
    summary="[Admin] Container detail",
)
def get_container(
    container_id: str,
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraContainer:
    """
    Return the full detail of a container: image, ports, env (secrets masked),
    mounts, networks, command, healthcheck, restart policy and labels.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().container(container_id, host_id=host)
    except Exception as ex:
        _raise_http(ex)


@router.delete(
    "/containers/{container_id}",
    response_model=InfraOk,
    summary="[Admin] Remove a container",
)
def remove_container(
    container_id: str,
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraOk:
    """
    Force-remove a container (it is stopped first when running).

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().remove_container(container_id, host_id=host)
    except Exception as ex:
        _raise_http(ex)


# ── Stacks, images, volumes, networks, events ─────────────────────────────────


@router.get(
    "/stacks",
    response_model=InfraStackList,
    summary="[Admin] Compose projects",
)
def list_stacks(
    request: Request,
    host: Optional[str] = Query(None, description="Host id"),
    refresh: bool = Query(
        False, description="Bypass the project file scan cache"
    ),
    _: CodxUser = Depends(require_admin),
) -> InfraStackList:
    """
    List compose projects: the ones running on the host AND the compose files
    discovered in the active project (plus its child projects).

    A discovered project that was never started is reported with
    ``status="stopped"``, ``source="project"`` and its ``declared_services``, so
    the UI can offer "Start" (``docker compose up -d``) for it.

    Requires the ``admin`` role.
    """
    try:
        manager = get_infra_manager()
        runtime = manager.stacks(host_id=host)
        _, roots = _project_scan_roots(request)
        if not roots:
            return runtime

        scan = discovery.scan_project_docker(roots, force=refresh)
        resolved_host = manager.host_config(host).id
        return InfraStackList(
            stacks=compose_stacks.merge_project_stacks(
                runtime.stacks, scan.compose, resolved_host
            )
        )
    except Exception as ex:
        _raise_http(ex)


@router.post(
    "/stacks/{name}/actions",
    response_model=None,
    summary="[Admin] Run a compose command on a stack",
)
def stack_action(
    request: Request,
    name: str,
    payload: InfraStackActionRequest,
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> Union[InfraStack, InfraOk]:
    """
    Run ONE ``docker compose`` command against a project and refresh it.

    | action    | equivalent                  | notes                                    |
    | :-------- | :-------------------------- | :--------------------------------------- |
    | `up`      | `docker compose up -d`      | labelled "Start": CREATES the containers |
    | `stop`    | `docker compose stop`       | containers are kept                      |
    | `restart` | `docker compose restart`    |                                          |
    | `build`   | `docker compose build`      | images only, idempotent                  |
    | `pull`    | `docker compose pull`       | images only, idempotent                  |
    | `down`    | `docker compose down`       | containers + networks removed            |

    The project is located through, in order: the compose file path sent in the
    body (validated against the active project scan — this is how a project
    that has no container yet is started), the labels of its containers, an
    in-process cache (so ``up`` still works right after ``down``) and finally
    ``docker compose ls``. Named volumes are never removed (no ``down -v``), so
    a stack brought down can be brought back up with its data intact.

    The call is synchronous and answers once the command settled, so ``build``
    and ``pull`` may take minutes (``CODX_JUNIOR_COMPOSE_TIMEOUT``, 600s).

    Returns the refreshed stack, or ``{"ok": true}`` when the project has no
    container left (``down``). Answers **404** when the project is unknown on
    that host, **503** when no compose CLI is installed and **504** when the
    command exceeds the timeout.

    Requires the ``admin`` role.
    """
    try:
        _, roots = _project_scan_roots(request)
        return compose_stacks.stack_action(
            get_infra_manager(),
            name,
            payload,
            host_id=host,
            project_roots=roots,
        )
    except Exception as ex:
        _raise_http(ex)


@router.get(
    "/stacks/{name}/logs",
    response_model=InfraStackLogs,
    summary="[Admin] Aggregated compose logs of a stack",
)
def get_stack_logs(
    name: str,
    tail: int = Query(200, ge=1, le=2000, description="Lines per service"),
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraStackLogs:
    """
    Return the logs of every service of a compose project as one chronological
    stream, each line prefixed with its service name (what ``docker compose
    logs`` prints).

    ``tail`` applies PER service, so the response holds at most
    ``tail × services`` lines. Answers **404** when the project has no container
    on that host.

    Requires the ``admin`` role.
    """
    try:
        return compose_stacks.stack_logs(
            get_infra_manager(), name, tail=tail, host_id=host
        )
    except Exception as ex:
        _raise_http(ex)


# ── Project Docker assets (compose files + Dockerfiles on disk) ───────────────


@router.get(
    "/project/docker",
    response_model=InfraProjectDocker,
    summary="[Admin] Docker assets scanned from the active project",
)
def get_project_docker(
    request: Request,
    host: Optional[str] = Query(None, description="Host id"),
    refresh: bool = Query(False, description="Bypass the scan cache"),
    _: CodxUser = Depends(require_admin),
) -> InfraProjectDocker:
    """
    Scan the active project (and its child/dependency projects) for Docker
    assets.

    The response carries:

    * ``compose`` — every discovered compose project, merged with the host
      runtime so a running one has its live services and status;
    * ``dockerfiles`` — every Dockerfile/Containerfile with its ``FROM``
      references, stages, build context and the compose service that builds it;
    * ``roots`` — the directories that were scanned.

    A request that is not scoped to a project answers with an empty payload and
    an explanatory ``message`` instead of failing, so the InfraView keeps
    working even before a project is opened.

    Requires the ``admin`` role.
    """
    try:
        manager = get_infra_manager()
        settings, roots = _project_scan_roots(request)
        if settings is None:
            return InfraProjectDocker(
                message="No active project: the request is not scoped by codx_path"
            )
        if not roots:
            return InfraProjectDocker(
                project=_project_info(settings),
                message="The active project has no readable checkout folder",
            )

        scan = discovery.scan_project_docker(roots, force=refresh)
        resolved_host = manager.host_config(host).id
        try:
            runtime = manager.stacks(host_id=host).stacks
        except (DockerUnavailable, DockerAPIError) as ex:
            # The files on disk are still useful when the daemon is down: list
            # them as stopped instead of failing the whole scan.
            logger.warning("Cannot merge the runtime stacks into the scan: %s", ex)
            runtime = []
        merged = compose_stacks.merge_project_stacks(
            runtime, scan.compose, resolved_host
        )
        return InfraProjectDocker(
            project=_project_info(settings),
            roots=[root.path for root in roots],
            compose=[stack for stack in merged if stack.source == "project"],
            dockerfiles=[_dockerfile_model(asset) for asset in scan.dockerfiles],
            scanned_at=scan.scanned_at,
            cached=scan.cached,
            message="" if (scan.compose or scan.dockerfiles)
            else "No compose file or Dockerfile found in the project",
        )
    except Exception as ex:
        _raise_http(ex)


@router.post(
    "/project/dockerfiles/build",
    response_model=InfraProjectDockerfileBuildResult,
    summary="[Admin] Build a Dockerfile discovered in the active project",
)
def build_project_dockerfile(
    request: Request,
    payload: InfraProjectDockerfileBuildRequest,
    _: CodxUser = Depends(require_admin),
) -> InfraProjectDockerfileBuildResult:
    """
    Run ``docker build`` for one Dockerfile discovered by the project scan.

    The Dockerfile must live inside the active project (or a child project);
    an arbitrary path is rejected. ``tag`` defaults to a name derived from the
    Dockerfile directory, ``context`` defaults to the context declared by a
    compose ``build:`` section (or the Dockerfile directory), and ``target`` /
    ``build_args`` map to ``--target`` / ``--build-arg``.

    The call is synchronous: it answers once the build settles (up to
    ``CODX_JUNIOR_DOCKER_BUILD_TIMEOUT``, 1800s) and returns the tail of the
    build log. Failure is **502** with the last output lines, timeout **504**,
    invalid input **400**, missing Docker CLI **503**.

    Requires the ``admin`` role.
    """
    try:
        _, roots = _project_scan_roots(request)
        return dockerfile_builder.build_dockerfile(
            get_infra_manager(), payload, roots
        )
    except Exception as ex:
        _raise_http(ex)


@router.get(
    "/images",
    response_model=InfraImageList,
    summary="[Admin] List images",
)
def list_images(
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraImageList:
    """
    List images with size, creation date, container usage count and a
    ``dangling`` flag (``<none>:<none>`` images).

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().images(host_id=host)
    except Exception as ex:
        _raise_http(ex)


@router.get(
    "/volumes",
    response_model=InfraVolumeList,
    summary="[Admin] List volumes",
)
def list_volumes(
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraVolumeList:
    """
    List volumes with size, mountpoint, the compose project inferred from the
    name, ``in_use`` and ``anonymous`` flags.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().volumes(host_id=host)
    except Exception as ex:
        _raise_http(ex)


@router.get(
    "/networks",
    response_model=InfraNetworkList,
    summary="[Admin] List networks",
)
def list_networks(
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraNetworkList:
    """
    List networks with driver, scope, subnet, ``internal`` flag and the names
    of the attached containers.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().networks(host_id=host)
    except Exception as ex:
        _raise_http(ex)


@router.get(
    "/events",
    response_model=InfraEventList,
    summary="[Admin] Recent Docker daemon events",
)
def list_events(
    host: Optional[str] = Query(None, description="Host id"),
    minutes: int = Query(60, ge=1, le=1440, description="Look-back window (minutes)"),
    _: CodxUser = Depends(require_admin),
) -> InfraEventList:
    """
    Return the daemon events of the last ``minutes`` (newest first, capped at
    100 entries): container start/stop/die, image pulls, volume/network
    creation, health status changes…

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().events(host_id=host, minutes=minutes)
    except Exception as ex:
        _raise_http(ex)


# ── Maintenance: single resource removal ──────────────────────────────────────


@router.delete(
    "/images/{image_id:path}",
    response_model=InfraOk,
    summary="[Admin] Remove an image",
)
def remove_image(
    image_id: str,
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraOk:
    """
    Remove a single image.

    ``image_id`` accepts either a ``sha256:…`` digest or a ``repo:tag``
    reference (the client percent-encodes it, so ``:`` and ``/`` are decoded
    here before being forwarded to the daemon).

    Returns ``{"ok": true}``. Answers **409** while a container - running or
    stopped - still references the image, which is exactly what the Docker CLI
    reports.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().remove_image(image_id, host_id=host)
    except Exception as ex:
        _raise_http(ex)


@router.delete(
    "/volumes/{name:path}",
    response_model=InfraOk,
    summary="[Admin] Remove a volume",
)
def remove_volume(
    name: str,
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraOk:
    """
    Remove a single volume by name.

    Returns ``{"ok": true}``. Answers **409** while a container (even a stopped
    one) still mounts the volume, so no data can be lost silently.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().remove_volume(name, host_id=host)
    except Exception as ex:
        _raise_http(ex)


@router.delete(
    "/networks/{network_id}",
    response_model=InfraOk,
    summary="[Admin] Remove a network",
)
def remove_network(
    network_id: str,
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraOk:
    """
    Remove a single network by id or name.

    Returns ``{"ok": true}``. Answers **403** for the predefined ``bridge``,
    ``host`` and ``none`` networks and **409** while endpoints are still
    attached.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().remove_network(network_id, host_id=host)
    except Exception as ex:
        _raise_http(ex)


# ── Maintenance: prune ────────────────────────────────────────────────────────


@router.post(
    "/maintenance/prune",
    response_model=InfraPruneResult,
    summary="[Admin] Prune Docker resources",
)
def prune_resources(
    payload: InfraPruneRequest,
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraPruneResult:
    """
    Prune one resource class and report what was reclaimed.

    ``target`` selects the resource class:

    | target        | what is removed                                                     |
    | :------------ | :------------------------------------------------------------------ |
    | `images`      | unused images (`dangling_only` keeps tagged ones)                    |
    | `volumes`     | unused volumes (`dangling_only` limits it to anonymous ones)         |
    | `networks`    | unused networks (predefined ones are never touched)                   |
    | `build_cache` | builder cache entries                                                 |
    | `system`      | stopped containers + unused networks + dangling images + build cache  |

    ``older_than_days`` restricts the prune to resources created before that
    window; the daemon supports it for `images` and `build_cache` only.
    `system` keeps named volumes on purpose, matching `docker system prune`.

    Returns ``{ok, host_id, target, removed, reclaimed_bytes}``.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().prune(payload, host_id=host)
    except Exception as ex:
        _raise_http(ex)

# Made with ❤️ by codx-junior