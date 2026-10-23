"""
Persistent registry of Docker hosts.

Why a file and not the environment?
-----------------------------------
`CODX_JUNIOR_INFRA_HOSTS` is fine for a static deployment, but the UI can now
register hosts (locally, over SSH, or through cloud provisioning), so the list
must survive a restart. The registry is a small JSON document written
atomically; the environment array is still honoured as the *seed* so existing
installations keep their extra endpoints.

Layout
------
```
$CODX_JUNIOR_INFRA_DATA_PATH/infra-hosts.json     # list of InfraHost records
```

Environment
-----------
CODX_JUNIOR_INFRA_DATA_PATH  Folder holding the registry (default /home/codx-junior/infra)
CODX_JUNIOR_INFRA_HOSTS      JSON array used to seed an empty registry
DOCKER_HOST / CODX_JUNIOR_DOCKER_SOCKET  Endpoint of the seeded local host

Example
-------
```json
[
  {
    "id": "host-local",
    "name": "codx-box",
    "kind": "local",
    "enabled": true,
    "is_local": true,
    "endpoint": "unix:///var/run/docker.sock"
  },
  {
    "id": "host-prod-01",
    "name": "prod-01",
    "kind": "ssh",
    "hostname": "10.0.0.21",
    "ssh_port": 22,
    "ssh_user": "root",
    "ssh_key_id": "key-a1b2c3d4",
    "endpoint": "ssh://root@10.0.0.21:22"
  }
]
```
"""

import json
import logging
import os
import re
import socket
import threading
from typing import Any, Dict, List, Optional

from codx.junior.infra.errors import InfraValidationError
from codx.junior.infra.models import InfraHost, InfraHostPayload

logger = logging.getLogger(__name__)

LOCAL_HOST_ID = "host-local"

DATA_PATH = os.environ.get("CODX_JUNIOR_INFRA_DATA_PATH", "/home/codx-junior/infra")
HOSTS_FILE = os.path.join(DATA_PATH, "infra-hosts.json")

LOCAL_SOCKET = os.environ.get("CODX_JUNIOR_DOCKER_SOCKET", "/var/run/docker.sock")

HOST_KINDS = ("local", "ssh")

HOST_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


# ── File helpers ───────────────────────────────────────────────────────────────


def _default_endpoint() -> str:
    """Endpoint of the local daemon (``DOCKER_HOST`` wins when set)."""
    return os.environ.get("DOCKER_HOST") or f"unix://{LOCAL_SOCKET}"


def _read_json(path: str, default: Any) -> Any:
    """Read a JSON document, returning ``default`` when it is missing/corrupt."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as ex:
        logger.error("Cannot read %s: %s", path, ex)
        return default


def _write_json(path: str, payload: Any) -> None:
    """Write a JSON document atomically (tmp file + ``os.replace``)."""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def slug_host_id(value: str) -> str:
    """
    Normalise a free-form name into a host id.

    Example:
        >>> slug_host_id("Prod 01 (Hetzner)")
        'prod-01-hetzner'
    """
    cleaned = re.sub(r"[^a-z0-9._-]+", "-", (value or "").strip().lower())
    return cleaned.strip("-")[:64] or "host"


def endpoint_for(kind: str, hostname: str, ssh_port: int, ssh_user: str) -> str:
    """Build the display endpoint of a host when the payload omits one."""
    if kind == "ssh":
        return f"ssh://{ssh_user}@{hostname}:{ssh_port}"
    return _default_endpoint()


def _local_host() -> InfraHost:
    """The always-present local daemon entry used to seed an empty registry."""
    return InfraHost(
        id=LOCAL_HOST_ID,
        name=socket.gethostname() or LOCAL_HOST_ID,
        kind="local",
        enabled=True,
        is_local=True,
        endpoint=_default_endpoint(),
        notes="Local Docker daemon",
    )


def _seed_hosts() -> List[InfraHost]:
    """
    Initial registry content.

    Honours the legacy ``CODX_JUNIOR_INFRA_HOSTS`` array (same shape as before)
    and always appends the local daemon so the UI has something to select.
    """
    hosts: List[InfraHost] = []
    raw = (os.environ.get("CODX_JUNIOR_INFRA_HOSTS") or "").strip()
    if raw:
        try:
            entries = json.loads(raw)
        except ValueError:
            logger.error("CODX_JUNIOR_INFRA_HOSTS is not valid JSON, ignoring it")
            entries = []
        for index, entry in enumerate(entries if isinstance(entries, list) else []):
            if not isinstance(entry, dict):
                logger.warning("Skipping invalid infra host entry #%d", index)
                continue
            endpoint = str(entry.get("endpoint") or _default_endpoint())
            host_id = str(entry.get("id") or f"host-{index}")
            hosts.append(
                InfraHost(
                    id=host_id,
                    name=str(entry.get("name") or host_id),
                    kind=str(entry.get("kind") or "local"),
                    enabled=bool(entry.get("enabled", True)),
                    is_local=bool(entry.get("is_local", not endpoint.startswith("ssh://"))),
                    endpoint=endpoint,
                )
            )

    if not any(host.id == LOCAL_HOST_ID for host in hosts):
        hosts.insert(0, _local_host())
    return hosts


# ── Store ─────────────────────────────────────────────────────────────────────


class InfraHostStore:
    """CRUD access to the persisted Docker host registry."""

    def __init__(self, path: str = HOSTS_FILE):
        self._path = path
        self._lock = threading.RLock()

    # -- reads -------------------------------------------------------------

    def list_hosts(self, enabled_only: bool = False) -> List[InfraHost]:
        """Return every registered host (optionally only the enabled ones)."""
        with self._lock:
            hosts = self._load()
        if enabled_only:
            hosts = [host for host in hosts if host.enabled]
        return hosts

    def get_host(self, host_id: str) -> InfraHost:
        """
        Return one host.

        Raises:
            KeyError: The host id is unknown.
        """
        target = (host_id or "").strip()
        for host in self.list_hosts():
            if host.id == target:
                return host
        raise KeyError(host_id)

    def hosts_using_key(self, key_id: str) -> List[str]:
        """Ids of the hosts that reference a managed key pair."""
        return [
            host.id
            for host in self.list_hosts()
            if key_id and host.ssh_key_id == key_id
        ]

    # -- writes ------------------------------------------------------------

    def create_host(self, payload: InfraHostPayload) -> InfraHost:
        """
        Register a new host.

        Raises:
            InfraValidationError: The definition is rejected, or the id exists.
        """
        record = self.build_record(payload)
        with self._lock:
            hosts = self._load()
            if any(host.id == record.id for host in hosts):
                raise InfraValidationError(f"Host '{record.id}' already exists")
            hosts.append(record)
            self._persist(hosts)
        logger.info("Infra host %s registered (%s)", record.id, record.endpoint)
        return record

    def update_host(self, host_id: str, payload: InfraHostPayload) -> InfraHost:
        """
        Update an existing host; omitted optional fields keep their value.

        Raises:
            KeyError: The host id is unknown.
            InfraValidationError: The resulting definition is invalid.
        """
        with self._lock:
            hosts = self._load()
            index = next(
                (position for position, host in enumerate(hosts) if host.id == host_id),
                None,
            )
            if index is None:
                raise KeyError(host_id)
            record = self.build_record(payload, current=hosts[index])
            record.id = hosts[index].id  # ids are immutable
            hosts[index] = record
            self._persist(hosts)
        logger.info("Infra host %s updated", host_id)
        return record

    def delete_host(self, host_id: str) -> None:
        """
        Forget a host. The remote machine keeps running untouched.

        Raises:
            KeyError: The host id is unknown.
        """
        with self._lock:
            hosts = self._load()
            remaining = [host for host in hosts if host.id != host_id]
            if len(remaining) == len(hosts):
                raise KeyError(host_id)
            self._persist(remaining)
        logger.info("Infra host %s removed", host_id)

    # -- validation --------------------------------------------------------

    @staticmethod
    def _pick(new: Any, current: Any, default: Any) -> Any:
        """Prefer the incoming value, then the stored one, then the default."""
        if new is not None:
            return new
        if current is not None:
            return current
        return default

    def build_record(
        self, payload: InfraHostPayload, current: Optional[InfraHost] = None
    ) -> InfraHost:
        """
        Validate a payload and turn it into a persistable :class:`InfraHost`.

        Passing ``current`` makes the call an *update*: every ``None`` field of
        the payload keeps the stored value.

        Raises:
            InfraValidationError: The definition is rejected.
        """
        pick = self._pick
        existing = current or InfraHost()

        kind = str(pick(payload.kind, existing.kind, "local")).strip().lower()
        if kind not in HOST_KINDS:
            raise InfraValidationError(
                f"Unsupported host kind '{kind}'. Allowed: {', '.join(HOST_KINDS)}"
            )

        name = str(pick(payload.name, existing.name, "")).strip()
        if not name:
            raise InfraValidationError("A host name is required")

        host_id = slug_host_id(str(pick(payload.id, existing.id, "") or name))
        if not HOST_ID_RE.match(host_id):
            raise InfraValidationError(f"Invalid host id '{host_id}'")

        hostname = str(pick(payload.hostname, existing.hostname, "")).strip()
        ssh_port = int(pick(payload.ssh_port, existing.ssh_port, 22) or 22)
        if not 1 <= ssh_port <= 65535:
            raise InfraValidationError("SSH port must be between 1 and 65535")

        ssh_user = str(pick(payload.ssh_user, existing.ssh_user, "root") or "root").strip()
        ssh_key_id = str(pick(payload.ssh_key_id, existing.ssh_key_id, "") or "").strip()
        ssh_key_file = str(
            pick(payload.ssh_key_file, existing.ssh_key_file, "") or ""
        ).strip()

        if kind == "ssh":
            if not hostname:
                raise InfraValidationError("An SSH host requires 'hostname'")
            if not ssh_key_id and not ssh_key_file:
                raise InfraValidationError(
                    "An SSH host requires 'ssh_key_id' or 'ssh_key_file'"
                )

        endpoint = str(pick(payload.endpoint, existing.endpoint, "") or "").strip()
        if not endpoint or (current is not None and endpoint.startswith("ssh://")
                            and not hostname):
            endpoint = endpoint_for(kind, hostname, ssh_port, ssh_user)

        return InfraHost(
            id=host_id,
            name=name,
            kind=kind,
            enabled=bool(pick(payload.enabled, existing.enabled, True)),
            is_local=kind == "local",
            notes=str(pick(payload.notes, existing.notes, "") or ""),
            hostname=hostname,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
            ssh_key_id=ssh_key_id,
            ssh_key_file=ssh_key_file,
            endpoint=endpoint,
            tls_verify=bool(pick(payload.tls_verify, existing.tls_verify, False)),
            tls_ca_file=str(pick(payload.tls_ca_file, existing.tls_ca_file, "") or ""),
            tls_cert_file=str(
                pick(payload.tls_cert_file, existing.tls_cert_file, "") or ""
            ),
            tls_key_file=str(pick(payload.tls_key_file, existing.tls_key_file, "") or ""),
            provider=pick(payload.provider, existing.provider, None),
            server_id=str(pick(payload.server_id, existing.server_id, "") or ""),
            region=str(pick(payload.region, existing.region, "") or ""),
        )

    # -- persistence -------------------------------------------------------

    def _load(self) -> List[InfraHost]:
        """Read the registry, seeding it on first use."""
        raw = _read_json(self._path, None)
        if not isinstance(raw, list) or not raw:
            hosts = _seed_hosts()
            self._persist(hosts)
            return hosts

        hosts: List[InfraHost] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            try:
                hosts.append(InfraHost(**entry))
            except Exception as ex:  # pragma: no cover - corrupt record
                logger.error("Skipping invalid host record: %s", ex)
        return hosts or _seed_hosts()

    def _persist(self, hosts: List[InfraHost]) -> None:
        """Write the registry back to disk."""
        _write_json(self._path, [host.model_dump() for host in hosts])


# ── Singleton ─────────────────────────────────────────────────────────────────

_host_store: Optional[InfraHostStore] = None
_host_store_lock = threading.Lock()


def get_host_store() -> InfraHostStore:
    """Return the process-wide :class:`InfraHostStore` (lazily created)."""
    global _host_store
    if _host_store is None:
        with _host_store_lock:
            if _host_store is None:
                _host_store = InfraHostStore()
    return _host_store

# Made with ❤️ by codx-junior