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
    """
    A Docker endpoint known to the API.

    The first block is the persisted configuration (written by
    `POST/PUT /api/infra/hosts`), the second one holds read-only gauges filled
    by `GET /api/infra/hosts` / `GET /api/infra/summary`.
    """

    # ── Identity ────────────────────────────────────────────────────────────
    id: str = Field(default="host-local", description='Stable key, e.g. "host-local"')
    name: str = Field(default="", description="Human readable host name")
    kind: str = Field(default="local", description="local | ssh")
    enabled: bool = Field(default=True, description="Listed/queried by the UI")
    is_local: bool = Field(default=False)
    notes: str = Field(default="", description="Free-form operator notes")

    # ── SSH connection (kind == 'ssh') ──────────────────────────────────────
    hostname: str = Field(default="", description="Hostname or IP of the remote machine")
    ssh_port: int = Field(default=22)
    ssh_user: str = Field(default="root")
    ssh_key_id: str = Field(default="", description="Managed key pair (preferred)")
    ssh_key_file: str = Field(default="", description="Key file already on this server")

    # ── Docker endpoint + TLS ───────────────────────────────────────────────
    endpoint: str = Field(
        default="",
        description="unix:///var/run/docker.sock, ssh://user@host:22 or tcp://host:2376",
    )
    tls_verify: bool = Field(default=False)
    tls_ca_file: str = Field(default="")
    tls_cert_file: str = Field(default="")
    tls_key_file: str = Field(default="")

    # ── Cloud metadata (filled for provisioned hosts) ───────────────────────
    provider: Optional[str] = Field(default=None, description="aws | azure | hetzner")
    server_id: str = Field(default="", description="Provider instance id")
    region: str = Field(default="")

    # ── Read-only engine gauges ─────────────────────────────────────────────
    engine: str = Field(default="", description="Docker engine version")
    os: str = Field(default="", description="OS / arch string")
    cpu_cores: int = Field(default=0)
    cpu_pct: float = Field(default=0.0)
    mem_total: int = Field(default=0)
    mem_used: int = Field(default=0)
    disk_total: int = Field(default=0)
    disk_used: int = Field(default=0)


class InfraHostList(BaseModel):
    """Response of ``GET /api/infra/hosts``."""

    hosts: List[InfraHost] = Field(default_factory=list)


class InfraHostPayload(BaseModel):
    """Body accepted by ``POST/PUT /api/infra/hosts`` and ``POST /api/infra/hosts/test``.

    Every optional field left to ``None`` keeps the stored value on update and
    falls back to the sensible default on create.
    """

    id: Optional[str] = Field(default=None, description="Stable id (derived from the name)")
    name: str = Field(description="Human readable host name")
    kind: str = Field(default="local", description="local | ssh")
    enabled: bool = Field(default=True)
    hostname: Optional[str] = Field(default=None, description="Hostname or IP (kind = ssh)")
    ssh_port: Optional[int] = Field(default=None, ge=1, le=65535)
    ssh_user: Optional[str] = Field(default=None, description='Login user (default "root")')
    ssh_key_id: Optional[str] = Field(default=None, description="Managed key pair id")
    ssh_key_file: Optional[str] = Field(
        default=None, description="Key file already present on the codx-junior server"
    )
    endpoint: Optional[str] = Field(
        default=None, description="Derived from kind/hostname when omitted"
    )
    tls_verify: Optional[bool] = Field(default=None)
    tls_ca_file: Optional[str] = Field(default=None)
    tls_cert_file: Optional[str] = Field(default=None)
    tls_key_file: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    # Cloud metadata is written by the provisioning engine only.
    provider: Optional[str] = Field(default=None)
    server_id: Optional[str] = Field(default=None)
    region: Optional[str] = Field(default=None)


class InfraHostTestResult(BaseModel):
    """Response of ``POST /api/infra/hosts/test``."""

    ok: bool = Field(default=False)
    message: str = Field(default="")
    engine: str = Field(default="")
    os: str = Field(default="")


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
    """Generic ``{ok: true}`` response (container/image/volume/network removal)."""

    ok: bool = Field(default=True)


# ── Maintenance ───────────────────────────────────────────────────────────────


class InfraPruneRequest(BaseModel):
    """Body of ``POST /api/infra/maintenance/prune``."""

    target: str = Field(
        default="images",
        description="images | volumes | networks | build_cache | system",
    )
    older_than_days: Optional[int] = Field(
        default=None,
        ge=0,
        description=(
            "Only prune resources older than N days. Honoured by 'images' and "
            "'build_cache'; the daemon has no age filter for volumes/networks."
        ),
    )
    dangling_only: bool = Field(
        default=False,
        description=(
            "images: keep tagged images (dangling=true). "
            "volumes: only anonymous volumes (docker's default behaviour)."
        ),
    )
    host_id: Optional[str] = Field(default=None, description="Target host id")


class InfraPruneResult(BaseModel):
    """Response of ``POST /api/infra/maintenance/prune``."""

    ok: bool = Field(default=True)
    host_id: str = Field(default="host-local")
    target: str = Field(default="images")
    removed: int = Field(default=0, description="Number of resources removed")
    reclaimed_bytes: int = Field(default=0, description="Disk space reclaimed")


# ── SSH keys ──────────────────────────────────────────────────────────────────


class InfraSshKey(BaseModel):
    """
    A managed key pair.

    The private material never leaves the codx-junior server: only the public
    key line and the absolute paths are reported.
    """

    id: str = Field(default="", description='Stable key id ("key-…")')
    name: str = Field(default="", description="Human readable name")
    algorithm: str = Field(default="ed25519", description="rsa | ed25519")
    bits: int = Field(default=256, description="256 for ed25519, 4096 for rsa")
    fingerprint: str = Field(default="", description='OpenSSH fingerprint ("SHA256:…")')
    source: str = Field(default="generated", description="generated | uploaded")
    public_key: str = Field(default="", description="OpenSSH public key line")
    private_key_file: str = Field(default="", description="Absolute path on this server")
    public_key_file: str = Field(default="", description="Absolute path of the .pub file")
    created_at: str = Field(default="", description="ISO 8601")
    hosts: List[str] = Field(default_factory=list, description="Host ids using this key")


class InfraSshKeyList(BaseModel):
    """Response of ``GET /api/infra/ssh-keys``."""

    keys: List[InfraSshKey] = Field(default_factory=list)


class InfraSshKeyGenerateRequest(BaseModel):
    """Body of ``POST /api/infra/ssh-keys/generate``."""

    name: str = Field(description="Base name for the key files")
    algorithm: str = Field(default="ed25519", description="rsa | ed25519")
    bits: Optional[int] = Field(
        default=None, description="4096 for rsa, ignored for ed25519"
    )
    comment: str = Field(default="", description="Trailing comment of the public key")


# ── Cloud providers ───────────────────────────────────────────────────────────


class CloudCredentialField(BaseModel):
    """Describes ONE credential input (the wizard renders itself from this)."""

    key: str = Field(description="Payload key inside `credentials`")
    label: str = Field(default="")
    type: str = Field(default="text", description="text | password | textarea")
    required: bool = Field(default=True)
    secret: bool = Field(default=False, description="Masked by default")
    placeholder: str = Field(default="")
    help: str = Field(default="", description="Where to find the value / required scope")


class CloudOption(BaseModel):
    """One selectable value of a cloud catalog (region, size, image)."""

    value: str = Field(default="")
    label: str = Field(default="")
    note: Optional[str] = Field(default=None)


class CloudProvider(BaseModel):
    """A provisioning provider and everything the wizard needs to render it."""

    id: str = Field(default="", description="aws | azure | hetzner")
    name: str = Field(default="")
    icon: str = Field(default="fa-cloud", description='Font Awesome solid class')
    summary: str = Field(default="")
    credentials: List[CloudCredentialField] = Field(default_factory=list)
    regions: List[CloudOption] = Field(default_factory=list)
    sizes: List[CloudOption] = Field(default_factory=list)
    images: List[CloudOption] = Field(default_factory=list)
    default_region: str = Field(default="")
    default_size: str = Field(default="")
    default_image: str = Field(default="")
    ssh_user: str = Field(default="root", description='Login user of the image ("ubuntu")')
    uploads_key: bool = Field(
        default=True, description="The public key is registered at the provider"
    )


class CloudProviderList(BaseModel):
    """Response of ``GET /api/infra/cloud/providers``."""

    providers: List[CloudProvider] = Field(default_factory=list)


class CloudValidateRequest(BaseModel):
    """Body of ``POST /api/infra/cloud/validate`` (credentials are transient)."""

    provider: str = Field(description="aws | azure | hetzner")
    credentials: Dict[str, str] = Field(default_factory=dict)
    region: Optional[str] = Field(default=None)


class CloudValidateResult(BaseModel):
    """Response of ``POST /api/infra/cloud/validate``."""

    ok: bool = Field(default=False)
    account: Optional[str] = Field(default=None)
    message: str = Field(default="")


class CloudServerRequest(BaseModel):
    """Body of ``POST /api/infra/cloud/servers`` (asynchronous job)."""

    provider: str = Field(description="aws | azure | hetzner")
    credentials: Dict[str, str] = Field(
        default_factory=dict, description="TRANSIENT — never persisted"
    )
    region: str = Field(default="")
    name: str = Field(description="Hostname / instance name")
    size: str = Field(default="", description="Instance type / SKU / server type")
    image: str = Field(default="", description="Image id, alias or URN")
    ssh_key_id: str = Field(description="Key pair whose public half is injected")
    ssh_user: Optional[str] = Field(default=None, description="Login user")
    install_docker: bool = Field(default=True, description="Install Docker Engine")
    open_ports: List[int] = Field(default_factory=list, description="Extra firewall ports")
    tags: Dict[str, str] = Field(default_factory=dict)


class CloudServerJobLog(BaseModel):
    """One line of the provisioning journal."""

    ts: str = Field(default="")
    level: str = Field(default="info")
    msg: str = Field(default="")


class CloudServerJob(BaseModel):
    """Response of ``POST|GET /api/infra/cloud/servers[/{id}]``."""

    id: str = Field(default="")
    provider: str = Field(default="")
    status: str = Field(
        default="queued",
        description=(
            "queued | creating | booting | installing_docker | registering | "
            "ready | error"
        ),
    )
    progress: int = Field(default=0, ge=0, le=100)
    message: str = Field(default="", description="Human readable current step")
    ip: str = Field(default="")
    hostname: str = Field(default="")
    host_id: str = Field(default="", description="InfraHost registered at the end")
    host: Optional[InfraHost] = Field(default=None, description="The host document")
    logs: List[CloudServerJobLog] = Field(default_factory=list)


class CloudCredentialsBody(BaseModel):
    """Optional body of ``DELETE /api/infra/cloud/servers/{id}``.

    Provisioning credentials are never stored, so a server created by a
    previous process can only be destroyed when they are supplied again.
    """

    credentials: Dict[str, str] = Field(default_factory=dict)
    region: Optional[str] = Field(default=None)

# Made with ❤️ by codx-junior