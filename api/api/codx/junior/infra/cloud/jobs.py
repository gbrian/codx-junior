"""
Asynchronous provisioning pipeline (`POST /api/infra/cloud/servers`).

State machine
-------------
```
queued → creating → booting → installing_docker → registering → ready
                     ↘ error (any step)
```

Steps
-----
1. **creating** – resolve the SSH key pair, call `provider.create_server()`.
2. **booting** – wait for TCP/22 (sshd is the first thing that answers).
3. **installing_docker** – `curl -fsSL https://get.docker.com | sh`.
4. **registering** – persist an SSH `InfraHost` and probe the daemon.
5. **ready** – the host is usable by every other `/api/infra/*` endpoint.

Credentials live in memory only (never persisted/logged), as required by the
`CloudServerRequest` contract. `DELETE` therefore needs them again once the
process restarted.

Example
-------
```python
from codx.junior.infra.cloud.jobs import get_cloud_job_manager

job = get_cloud_job_manager().start(request)
while job.status not in ("ready", "error"):
    time.sleep(2)
    job = get_cloud_job_manager().get(job.id)
    print(job.progress, job.message)
```
"""

import logging
import threading
import traceback
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from codx.junior.infra.cloud import get_provider
from codx.junior.infra.errors import InfraValidationError
from codx.junior.infra.host_store import InfraHostStore, get_host_store
from codx.junior.infra.models import (
    CloudServerJob,
    CloudServerJobLog,
    CloudServerRequest,
    InfraHostPayload,
)
from codx.junior.infra.ssh import (
    docker_ready,
    install_docker,
    wait_for_port,
)
from codx.junior.infra.ssh_keys import SshKeyStore, get_ssh_key_store

logger = logging.getLogger(__name__)

BOOT_TIMEOUT = float(300)
KEY_TIMEOUT = 30

FINAL_STATUSES = ("ready", "error")


def _now() -> str:
    """ISO 8601 UTC timestamp used by the journal."""
    return datetime.now(timezone.utc).isoformat()


class CloudJobManager:
    """In-memory registry of provisioning jobs."""

    def __init__(
        self,
        hosts: Optional[InfraHostStore] = None,
        keys: Optional[SshKeyStore] = None,
    ):
        self._hosts = hosts or get_host_store()
        self._keys = keys or get_ssh_key_store()
        self._jobs: Dict[str, CloudServerJob] = {}
        self._credentials: Dict[str, Dict[str, str]] = {}
        self._server_ids: Dict[str, str] = {}
        self._lock = threading.RLock()

    # -- public API --------------------------------------------------------

    def start(self, request: CloudServerRequest) -> CloudServerJob:
        """
        Queue a provisioning job and return it immediately.

        Raises:
            CloudProviderError: The provider is unknown (404).
            InfraValidationError: Required fields are missing (422).
        """
        provider = get_provider(request.provider)
        if not (request.name or "").strip():
            raise InfraValidationError("A server name is required")
        if not (request.ssh_key_id or "").strip():
            raise InfraValidationError("'ssh_key_id' is required")
        self._keys.get_key(request.ssh_key_id)  # raises KeyError → 404

        job = CloudServerJob(
            id=f"cjob-{uuid.uuid4().hex[:8]}",
            provider=provider.id,
            status="queued",
            progress=0,
            message="Queued",
            hostname=request.name,
            logs=[CloudServerJobLog(ts=_now(), level="info", msg="Job queued")],
        )
        with self._lock:
            self._jobs[job.id] = job
            self._credentials[job.id] = dict(request.credentials or {})

        thread = threading.Thread(
            target=self._run, args=(job.id, request), name=f"cloud-{job.id}", daemon=True
        )
        thread.start()
        logger.info("Cloud job %s started for provider %s", job.id, provider.id)
        return self.get(job.id)

    def get(self, job_id: str) -> CloudServerJob:
        """
        Return a snapshot of a job.

        Raises:
            KeyError: The job id is unknown.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            snapshot = job.model_copy(deep=True)
            snapshot.host = None
            if job.host_id:
                try:
                    snapshot.host = self._hosts.get_host(job.host_id)
                except KeyError:
                    snapshot.host = None
            return snapshot

    def list_jobs(self) -> List[CloudServerJob]:
        """Return every job known to this process (newest first)."""
        with self._lock:
            job_ids = list(self._jobs)
        jobs = [self.get(job_id) for job_id in job_ids]
        return sorted(jobs, key=lambda job: job.id, reverse=True)

    def destroy(
        self, job_id: str, credentials: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Destroy the cloud server of a job and forget its host entry.

        Args:
            job_id: Provisioning job id.
            credentials: Provider credentials. Required when the job was created
                by a previous process (nothing is persisted).

        Raises:
            KeyError: The job id is unknown.
            CloudProviderError: Credentials are missing (422) or the provider
                refused the deletion.
        """
        job = self.get(job_id)
        with self._lock:
            stored = dict(self._credentials.get(job_id) or {})
            server_id = self._server_ids.get(job_id) or ""
        merged = {**stored, **(credentials or {})}

        if not server_id and job.host_id:
            try:
                server_id = self._hosts.get_host(job.host_id).server_id
            except KeyError:
                server_id = ""

        provider = get_provider(job.provider)
        if server_id:
            if not merged:
                raise provider_error(provider.name)
            provider.destroy_server(server_id, merged)

        if job.host_id:
            try:
                self._hosts.delete_host(job.host_id)
            except KeyError:
                pass

        with self._lock:
            self._jobs.pop(job_id, None)
            self._credentials.pop(job_id, None)
            self._server_ids.pop(job_id, None)
        logger.info("Cloud job %s destroyed (server %s)", job_id, server_id)

    # -- pipeline ----------------------------------------------------------

    def _run(self, job_id: str, request: CloudServerRequest) -> None:
        """Thread target: drive the job through the provisioning steps."""
        provider = get_provider(request.provider)
        log = lambda level, msg: self._log(job_id, level, msg)  # noqa: E731
        server_id = ""

        try:
            key = self._keys.get_key(request.ssh_key_id)
            public_key = key.public_key or self._keys.public_key(request.ssh_key_id)
            if not public_key:
                raise InfraValidationError(
                    f"Key '{request.ssh_key_id}' has no public key line"
                )

            self._update(
                job_id,
                status="creating",
                progress=10,
                message="Creating the server…",
            )
            provisioned = provider.create_server(request, public_key, log)
            server_id = provisioned.server_id
            with self._lock:
                self._server_ids[job_id] = server_id

            self._update(
                job_id,
                status="booting",
                progress=35,
                message=f"Waiting for SSH on {provisioned.ip}…",
                ip=provisioned.ip,
            )
            if not wait_for_port(provisioned.ip, 22, timeout=BOOT_TIMEOUT):
                raise InfraValidationError(
                    f"{provisioned.ip} did not accept SSH connections in time"
                )
            self._log(job_id, "info", f"SSH is up on {provisioned.ip}")

            ssh_user = (request.ssh_user or provider.ssh_user or "root").strip()
            key_file = self._keys.private_key_file(request.ssh_key_id)

            if request.install_docker:
                self._update(
                    job_id,
                    status="installing_docker",
                    progress=60,
                    message="Installing Docker Engine…",
                )
                output = install_docker(
                    provisioned.ip, user=ssh_user, key_file=key_file
                )
                self._log(job_id, "info", output[-400:] or "Docker installed")
            else:
                self._log(job_id, "info", "Docker installation skipped")
                if not docker_ready(
                    provisioned.ip, user=ssh_user, key_file=key_file, timeout=KEY_TIMEOUT
                ):
                    self._log(
                        job_id,
                        "warn",
                        "The daemon did not answer; the host was registered anyway",
                    )

            self._update(
                job_id,
                status="registering",
                progress=85,
                message="Registering the host…",
            )
            payload = InfraHostPayload(
                name=request.name,
                kind="ssh",
                enabled=True,
                hostname=provisioned.ip,
                ssh_port=22,
                ssh_user=ssh_user,
                ssh_key_id=request.ssh_key_id,
                endpoint=f"ssh://{ssh_user}@{provisioned.ip}:22",
                provider=provider.id,
                server_id=server_id,
                region=self._region_of(provider, request),
                notes=(
                    f"Provisioned by codx-junior "
                    f"({provider.id} {request.size or provider.default_size} "
                    f"{request.image or provider.default_image})"
                ),
            )
            try:
                host = self._hosts.create_host(payload)
            except InfraValidationError as ex:
                if "already exists" not in str(ex):
                    raise
                host = self._hosts.update_host(
                    payload.id or "", payload
                ) if payload.id else self._hosts.list_hosts()[-1]

            self._update(
                job_id,
                status="ready",
                progress=100,
                message=f"Host '{host.id}' is ready",
                host_id=host.id,
            )
            self._log(job_id, "info", "Provisioning finished")

        except Exception as ex:  # noqa: BLE001 - reported to the UI
            logger.error("Cloud job %s failed: %s", job_id, ex)
            logger.debug(traceback.format_exc())
            self._log(job_id, "error", str(ex))
            self._update(
                job_id,
                status="error",
                progress=100,
                message=str(ex) or "Provisioning failed",
            )
            # Best effort: do not leave a half-built paid instance behind.
            if server_id:
                try:
                    provider.destroy_server(
                        server_id, self._credentials.get(job_id) or {}
                    )
                    self._log(job_id, "info", "The failed instance was destroyed")
                except Exception as cleanup_ex:  # pragma: no cover
                    self._log(
                        job_id,
                        "warn",
                        f"Could not destroy the failed instance: {cleanup_ex}",
                    )

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _region_of(provider, request: CloudServerRequest) -> str:
        """Effective region, used as host metadata."""
        return (request.region or provider.default_region or "").strip()

    def _update(self, job_id: str, **changes) -> None:
        """Apply changes to a job and stamp the journal."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in changes.items():
                setattr(job, key, value)
            if "message" in changes:
                job.logs.append(
                    CloudServerJobLog(ts=_now(), level="info", msg=str(changes["message"]))
                )

    def _log(self, job_id: str, level: str, message: str) -> None:
        """Append one journal line (bounded to the last 200 entries)."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.logs.append(CloudServerJobLog(ts=_now(), level=level, msg=str(message)))
            del job.logs[:-200]


def provider_error(provider_name: str):
    """Build the `422` raised when destroy credentials are missing."""
    from codx.junior.infra.cloud.base import CloudProviderError

    return CloudProviderError(
        f"Credentials for {provider_name} are required to destroy this server: "
        "they are never stored, so a server provisioned by a previous process "
        "can only be destroyed with them supplied again.",
        422,
    )


# ── Singleton ─────────────────────────────────────────────────────────────────

_job_manager: Optional[CloudJobManager] = None
_job_manager_lock = threading.Lock()


def get_cloud_job_manager() -> CloudJobManager:
    """Return the process-wide :class:`CloudJobManager` (lazily created)."""
    global _job_manager
    if _job_manager is None:
        with _job_manager_lock:
            if _job_manager is None:
                _job_manager = CloudJobManager()
    return _job_manager

# Made with ❤️ by codx-junior