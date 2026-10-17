"""
Pydantic models mirroring the `/api/infra/*` JSON contract.

The contract is defined (and documented) in `client/src/api/modules/infra.js`.
Every field carries a default on purpose: a daemon that omits an optional
attribute (older Docker versions, alternative runtimes, foreign endpoints)
must never break a response, and the UI renders zeros/empty lists fine.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# ── Shared building blocks ─────────────────────────────────────────────────────


class InfraPort(BaseModel):
    """A container port mapping."""

    host: Optional[int] = Field(default=None, description="Published host port")
    container: int = Field(default=0, description="Container-side port")
    proto: str = Field(default="tcp", description="tcp | udp")
    published: bool = Field(default=False, description="Published to the host")


class InfraMount(BaseModel):
    """A bind mount or named volume attached to a container."""

    type: str = Field(default="bind", description="bind | volume | tmpfs")
    source: str = Field(default="", description="Host path or volume name")
    destination: str = Field(default="", description="Container path")
    mode: str = Field(default="rw", description="rw | ro")


class InfraNetworkAttachment(BaseModel):
    """A network a container is connected to."""

    name: str = Field(default="")
    ip: str = Field(default="")


class InfraEnvVar(BaseModel):
    """A container environment variable (secret values are masked)."""

    k: str = Field(default="")
    v: str = Field(default="")


class InfraHealthcheck(BaseModel):
    """Healthcheck configuration of a container."""

    test: str = Field(default="")
    interval: str = Field(default="", description='e.g. "30s"')
    retries: int = Field(default=0)


# ── Host ───────────────────────────────────────────────────────────────────────


class InfraHost(BaseModel):
    """A Docker endpoint known to the API."""

    id: str = Field(default="host-local")
    name: str = Field(default="")
    endpoint: str = Field(default="", description="unix:///var/run/docker.sock, tcp://…")
    engine: str = Field(default="", description="Docker engine version")
    os: str = Field(default="", description="OS / arch string")
    cpu_cores: int = Field(default=0)
    cpu_pct: float = Field(default=0.0)
    mem_total: int = Field(default=0)
    mem_used: int = Field(default=0)
    disk_total: int = Field(default=0)
    disk_used: int = Field(default=0)
    is_local: bool = Field(default=False)


class InfraHostList(BaseModel):
    """Response of ``GET /api/infra/hosts``."""

    hosts: List[InfraHost] = Field(default_factory=list)


# ── Containers ─────────────────────────────────────────────────────────────────


class InfraContainer(BaseModel):
    """A container and its (live, when available) resource usage."""

    id: str = Field(default="")
    short: str = Field(default="")
    name: str = Field(default="")
    image: str = Field(default="")
    image_id: str = Field(default="")
    state: str = Field(default="unknown", description="running|exited|paused|…")
    health: Optional[str] = Field(default=None, description="healthy|unhealthy|starting")
    status_text: str = Field(default="", description='docker ps STATUS, e.g. "Up 3 days"')
    created: str = Field(default="")
    started_at: str = Field(default="")
    uptime_seconds: int = Field(default=0)
    host_id: str = Field(default="host-local")
    stack: str = Field(default="", description="Compose project name")
    service: str = Field(default="", description="Compose service name")
    ports: List[InfraPort] = Field(default_factory=list)
    cpu_pct: float = Field(default=0.0)
    mem_used: int = Field(default=0)
    mem_limit: int = Field(default=0)
    mem_pct: float = Field(default=0.0)
    net_rx: int = Field(default=0)
    net_tx: int = Field(default=0)
    block_read: int = Field(default=0)
    block_write: int = Field(default=0)
    restart_count: int = Field(default=0)
    restart_policy: str = Field(default="")
    labels: Dict[str, str] = Field(default_factory=dict)
    env: List[InfraEnvVar] = Field(default_factory=list)
    mounts: List[InfraMount] = Field(default_factory=list)
    networks: List[InfraNetworkAttachment] = Field(default_factory=list)
    cmd: List[str] = Field(default_factory=list)
    entrypoint: str = Field(default="")
    healthcheck: Optional[InfraHealthcheck] = Field(default=None)
    url: Optional[str] = Field(default=None, description="Exposed app URL")
    sysbox: bool = Field(default=False, description="Runs under the sysbox runtime")
    pids: int = Field(default=0)


class InfraContainerList(BaseModel):
    """Response of ``GET /api/infra/containers``."""

    total: int = Field(default=0)
    containers: List[InfraContainer] = Field(default_factory=list)


class InfraLogLine(BaseModel):
    """One parsed log line of a container."""

    ts: str = Field(default="", description="ISO 8601 timestamp")
    level: str = Field(default="INFO")
    msg: str = Field(default="")


class InfraContainerLogs(BaseModel):
    """Response of ``GET /api/infra/containers/{id}/logs``."""

    id: str = Field(default="")
    lines: List[InfraLogLine] = Field(default_factory=list)


class InfraStatsCurrent(BaseModel):
    """Instantaneous container counters."""

    cpu_pct: float = Field(default=0.0)
    mem_used: int = Field(default=0)
    mem_limit: int = Field(default=0)
    net_rx: int = Field(default=0)
    net_tx: int = Field(default=0)
    block_read: int = Field(default=0)
    block_write: int = Field(default=0)
    pids: int = Field(default=0)


class InfraStatsPoint(BaseModel):
    """A single point of the CPU/memory time series."""

    t: str = Field(default="", description="ISO 8601 timestamp")
    cpu: float = Field(default=0.0)
    mem: int = Field(default=0)


class InfraStats(BaseModel):
    """Response of ``GET /api/infra/containers/{id}/stats``."""

    current: InfraStatsCurrent = Field(default_factory=InfraStatsCurrent)
    series: List[InfraStatsPoint] = Field(default_factory=list)


# ── Host summary ───────────────────────────────────────────────────────────────


class InfraSummaryCounts(BaseModel):
    """Object counts shown as chips in the UI."""

    total: int = Field(default=0)
    running: int = Field(default=0)
    stopped: int = Field(default=0)
    paused: int = Field(default=0)
    restarting: int = Field(default=0)
    unhealthy: int = Field(default=0)
    images: int = Field(default=0)
    volumes: int = Field(default=0)
    networks: int = Field(default=0)


class InfraSummary(BaseModel):
    """Response of ``GET /api/infra/summary``."""

    host: InfraHost = Field(default_factory=InfraHost)
    engine: str = Field(default="")
    cpu_pct: float = Field(default=0.0)
    cpu_cores: int = Field(default=0)
    mem_used: int = Field(default=0)
    mem_total: int = Field(default=0)
    disk_used: int = Field(default=0)
    disk_total: int = Field(default=0)
    counts: InfraSummaryCounts = Field(default_factory=InfraSummaryCounts)


# ── Compose stacks ─────────────────────────────────────────────────────────────


class InfraStackService(BaseModel):
    """One compose service (a container) inside a stack."""

    service: str = Field(default="")
    name: str = Field(default="")
    state: str = Field(default="unknown")
    health: Optional[str] = Field(default=None)
    id: str = Field(default="")


class InfraStack(BaseModel):
    """A compose project."""

    name: str = Field(default="")
    host_id: str = Field(default="host-local")
    path: str = Field(default="", description="Compose file or working directory")
    status: str = Field(default="stopped", description="running|stopped|degraded")
    running: int = Field(default=0)
    total: int = Field(default=0)
    services: List[InfraStackService] = Field(default_factory=list)


class InfraStackList(BaseModel):
    """Response of ``GET /api/infra/stacks``."""

    stacks: List[InfraStack] = Field(default_factory=list)


# ── Images, volumes, networks, events ─────────────────────────────────────────


class InfraImage(BaseModel):
    """An image present on the host."""

    repo: str = Field(default="")
    tag: str = Field(default="")
    id: str = Field(default="")
    size: int = Field(default=0)
    created: str = Field(default="")
    containers: int = Field(default=0, description="Containers using this image")
    dangling: bool = Field(default=False)


class InfraImageList(BaseModel):
    """Response of ``GET /api/infra/images``."""

    images: List[InfraImage] = Field(default_factory=list)


class InfraVolume(BaseModel):
    """A volume present on the host."""

    name: str = Field(default="")
    driver: str = Field(default="")
    scope: str = Field(default="local")
    mountpoint: str = Field(default="")
    size: int = Field(default=0)
    stack: str = Field(default="", description="Compose project inferred from the name")
    in_use: bool = Field(default=False)
    anonymous: bool = Field(default=False)
    created: str = Field(default="")


class InfraVolumeList(BaseModel):
    """Response of ``GET /api/infra/volumes``."""

    volumes: List[InfraVolume] = Field(default_factory=list)


class InfraNetwork(BaseModel):
    """A network present on the host."""

    id: str = Field(default="")
    name: str = Field(default="")
    driver: str = Field(default="")
    scope: str = Field(default="local")
    subnet: str = Field(default="")
    internal: bool = Field(default=False)
    containers: List[str] = Field(default_factory=list)
    created: str = Field(default="")


class InfraNetworkList(BaseModel):
    """Response of ``GET /api/infra/networks``."""

    networks: List[InfraNetwork] = Field(default_factory=list)


class InfraEvent(BaseModel):
    """A Docker daemon event."""

    ts: str = Field(default="", description="ISO 8601 timestamp")
    type: str = Field(default="", description="container | image | volume | network | …")
    action: str = Field(default="")
    actor: str = Field(default="")


class InfraEventList(BaseModel):
    """Response of ``GET /api/infra/events``."""

    events: List[InfraEvent] = Field(default_factory=list)


# ── Requests ──────────────────────────────────────────────────────────────────


class InfraActionRequest(BaseModel):
    """Body of ``POST /api/infra/containers/{id}/actions``."""

    action: str = Field(description="start | stop | restart | pause | unpause | kill")


class InfraCreatePort(BaseModel):
    """Port mapping supplied when creating a container."""

    host: Optional[int] = Field(default=None, description="Host port (omit for none)")
    container: int = Field(default=0, description="Container port")
    proto: str = Field(default="tcp")


class InfraCreateEnvVar(BaseModel):
    """Environment variable supplied when creating a container."""

    k: str = Field(default="")
    v: str = Field(default="")


class InfraCreateContainerRequest(BaseModel):
    """Body of ``POST /api/infra/containers``."""

    name: str = Field(description="Container name (must be unique)")
    image: str = Field(description="Image reference, e.g. nginx:1.27-alpine")
    stack: Optional[str] = Field(
        default=None, description="Compose project name used to group the container"
    )
    cmd: Optional[str] = Field(default="", description="Command line (shell-quoted)")
    host_id: Optional[str] = Field(default=None, description="Target host id")
    ports: List[InfraCreatePort] = Field(default_factory=list)
    env: List[InfraCreateEnvVar] = Field(default_factory=list)


class InfraOk(BaseModel):
    """Generic ``{ok: true}`` response (container removal)."""

    ok: bool = Field(default=True)

# Made with ❤️ by codx-junior