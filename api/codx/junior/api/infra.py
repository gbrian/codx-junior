"""
Docker infrastructure router (`/api/infra/*`).

Every route is **admin-only**: listing containers is harmless, but start/stop/
kill and container creation are privileged operations. The JSON contract is the
one consumed by `client/src/api/modules/infra.js` (its `INFRA_ENDPOINTS` array
is the machine-readable version of the table below).

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
GET    /api/infra/stacks                     – compose projects
GET    /api/infra/images                     – images
GET    /api/infra/volumes                    – volumes
GET    /api/infra/networks                   – networks
GET    /api/infra/events                     – recent daemon events

Example
-------
```bash
# List running containers with live usage
curl -b "auth=…" "https://codx.local/api/infra/containers?host=host-local&state=running"

# Restart a container
curl -X POST -b "auth=…" -H 'Content-Type: application/json' \
     -d '{"action":"restart"}' \
     "https://codx.local/api/infra/containers/codx-junior/actions"
```

Diagram
-------
flowchart LR
    A[Admin UI] -->|cookie auth| B{Router}
    B -->|require_admin| C[InfraManager]
    C --> D[DockerClient]
    D --> E[(Docker daemon)]
"""

import logging
from typing import Any, Dict, NoReturn, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from codx.junior.api import require_admin
from codx.junior.infra import (
    DockerAPIError,
    DockerUnavailable,
    get_infra_manager,
)
from codx.junior.infra.models import (
    InfraActionRequest,
    InfraContainer,
    InfraContainerList,
    InfraContainerLogs,
    InfraCreateContainerRequest,
    InfraEventList,
    InfraHostList,
    InfraImageList,
    InfraNetworkList,
    InfraOk,
    InfraStackList,
    InfraStats,
    InfraSummary,
    InfraVolumeList,
)
from codx.junior.model.model import CodxUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/infra", tags=["infra"])


# ── Helpers ────────────────────────────────────────────────────────────────────


def _raise_http(ex: Exception) -> NoReturn:
    """
    Translate infrastructure exceptions into HTTP errors.

    Mapping:
      * ``DockerUnavailable`` → 503 (daemon/socket not reachable)
      * ``DockerAPIError`` 404 → 404 (no such container)
      * other ``DockerAPIError`` → 502 (daemon rejected the operation)
      * ``KeyError`` → 404 (unknown host id)
      * ``ValueError`` → 400 (invalid request)
      * anything else → 500
    """
    if isinstance(ex, DockerUnavailable):
        raise HTTPException(status_code=503, detail=str(ex)) from ex

    if isinstance(ex, DockerAPIError):
        if ex.status_code == 404:
            raise HTTPException(status_code=404, detail=ex.message) from ex
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
    host: Optional[str] = Query(None, description="Host id"),
    _: CodxUser = Depends(require_admin),
) -> InfraStackList:
    """
    Group containers by their ``com.docker.compose.project`` label and report
    ``running``/``stopped``/``degraded`` status per stack.

    Requires the ``admin`` role.
    """
    try:
        return get_infra_manager().stacks(host_id=host)
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

# Made with ❤️ by codx-junior
