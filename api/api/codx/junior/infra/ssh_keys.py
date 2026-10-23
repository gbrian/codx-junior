"""
Managed SSH key pairs (`/api/infra/ssh-keys/*`).

Why keys are host independent
-----------------------------
A key must exist **before** the machine it unlocks: cloud provisioning injects
the public half during the first boot, and the host entry is only registered
once the machine answers. Keys therefore live in their own collection and hosts
point at one through `InfraHost.ssh_key_id`.

Security
--------
The private key never leaves the codx-junior server: it is written with mode
`0600` inside the infra data folder and only its absolute path is reported to
the browser.

Layout
------
```
$CODX_JUNIOR_INFRA_DATA_PATH/infra-ssh-keys.json   # metadata (no private data)
$CODX_JUNIOR_INFRA_DATA_PATH/ssh-keys/key-<id>     # private key (0600)
$CODX_JUNIOR_INFRA_DATA_PATH/ssh-keys/key-<id>.pub # public key
```

Example
-------
```python
from codx.junior.infra.ssh_keys import get_ssh_key_store
from codx.junior.infra.models import InfraSshKeyGenerateRequest

store = get_ssh_key_store()
key = store.generate(InfraSshKeyGenerateRequest(name="prod-01", algorithm="ed25519"))
print(key.public_key)   # ssh-ed25519 AAAA… codx-junior:prod-01
print(key.fingerprint)  # SHA256:ab12…
```
"""

import logging
import os
import re
import shutil
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from codx.junior.infra.errors import InfraConflictError, InfraValidationError
from codx.junior.infra.host_store import DATA_PATH, get_host_store, _read_json, _write_json
from codx.junior.infra.models import (
    InfraSshKey,
    InfraSshKeyGenerateRequest,
)

logger = logging.getLogger(__name__)

KEYS_FILE = os.path.join(DATA_PATH, "infra-ssh-keys.json")
KEYS_FOLDER = os.path.join(DATA_PATH, "ssh-keys")

SSH_KEYGEN = "ssh-keygen"

ALGORITHMS = ("rsa", "ed25519")

DEFAULT_BITS = {"rsa": 4096, "ed25519": 256}

KEY_ID_RE = re.compile(r"^key-[0-9a-f]{8}$")


def _require_keygen() -> None:
    if shutil.which(SSH_KEYGEN) is None:
        raise InfraValidationError(
            "ssh-keygen is not installed on the codx-junior server"
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(public_key_file: str) -> str:
    """Read the OpenSSH fingerprint of a ``.pub`` file."""
    try:
        completed = subprocess.run(
            [SSH_KEYGEN, "-lf", public_key_file],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as ex:
        logger.error("Cannot read fingerprint of %s: %s", public_key_file, ex)
        return ""

    parts = (completed.stdout or "").split()
    return parts[1] if len(parts) > 1 else ""


def _derive_public_key(private_key_file: str) -> str:
    """
    Derive the public key line from a private key.

    Raises:
        InfraValidationError: The key is unreadable or passphrase protected.
    """
    try:
        completed = subprocess.run(
            [SSH_KEYGEN, "-y", "-f", private_key_file],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as ex:
        raise InfraValidationError(f"Cannot read the private key: {ex}") from ex

    if completed.returncode != 0:
        raise InfraValidationError(
            "Unreadable private key (passphrase-protected keys are not supported): "
            f"{(completed.stderr or '').strip()[:200]}"
        )
    return (completed.stdout or "").strip()


class SshKeyStore:
    """CRUD access to the managed SSH key pairs."""

    def __init__(self, path: str = KEYS_FILE, folder: str = KEYS_FOLDER):
        self._path = path
        self._folder = folder
        self._lock = threading.RLock()

    # -- reads -------------------------------------------------------------

    def list_keys(self) -> List[InfraSshKey]:
        """Return every managed key pair (public material only)."""
        with self._lock:
            records = self._load()
        return [self._hydrate(record) for record in records]

    def get_key(self, key_id: str) -> InfraSshKey:
        """
        Return one key pair.

        Raises:
            KeyError: The key id is unknown.
        """
        record = self._record(key_id)
        return self._hydrate(record)

    def public_key(self, key_id: str) -> str:
        """Return the OpenSSH public key line of a key pair."""
        record = self._record(key_id)
        public_key = record.get("public_key") or ""
        if public_key:
            return public_key

        public_file = record.get("public_key_file") or ""
        if public_file and os.path.isfile(public_file):
            with open(public_file, "r", encoding="utf-8") as handle:
                return handle.read().strip()
        return ""

    def private_key_file(self, key_id: str) -> str:
        """
        Return the absolute path of the private key (for `ssh -i`).

        Raises:
            KeyError: The key id is unknown.
            InfraValidationError: The private file is gone.
        """
        record = self._record(key_id)
        path = record.get("private_key_file") or ""
        if not path or not os.path.isfile(path):
            raise InfraValidationError(
                f"The private key of '{key_id}' is missing on this server"
            )
        return path

    # -- writes ------------------------------------------------------------

    def generate(self, request: InfraSshKeyGenerateRequest) -> InfraSshKey:
        """
        Generate a new key pair with ``ssh-keygen``.

        Args:
            request: Name, algorithm (`rsa`/`ed25519`), optional bits/comment.

        Returns:
            The stored :class:`InfraSshKey` (public key included).

        Raises:
            InfraValidationError: Invalid algorithm or generation failure.
        """
        _require_keygen()

        name = (request.name or "").strip()
        if not name:
            raise InfraValidationError("A key name is required")

        algorithm = (request.algorithm or "ed25519").strip().lower()
        if algorithm not in ALGORITHMS:
            raise InfraValidationError(
                f"Unsupported algorithm '{algorithm}'. Allowed: {', '.join(ALGORITHMS)}"
            )

        bits = int(request.bits or DEFAULT_BITS[algorithm])
        key_id = f"key-{uuid.uuid4().hex[:8]}"
        os.makedirs(self._folder, exist_ok=True)
        private_file = os.path.join(self._folder, key_id)
        comment = (request.comment or f"codx-junior:{name}").strip()

        args = [SSH_KEYGEN, "-q", "-t", algorithm, "-f", private_file, "-N", "", "-C", comment]
        if algorithm == "rsa":
            args += ["-b", str(bits)]

        try:
            completed = subprocess.run(
                args, capture_output=True, text=True, timeout=120, check=False
            )
        except (OSError, subprocess.SubprocessError) as ex:
            raise InfraValidationError(f"Cannot run ssh-keygen: {ex}") from ex

        if completed.returncode != 0:
            shutil.rmtree(private_file, ignore_errors=True)
            raise InfraValidationError(
                f"ssh-keygen failed: {(completed.stderr or '').strip()[:300]}"
            )

        os.chmod(private_file, 0o600)
        record = self._register(
            key_id=key_id,
            name=name,
            algorithm=algorithm,
            bits=bits,
            source="generated",
            private_file=private_file,
        )
        logger.info("SSH key %s generated (%s %s bits)", key_id, algorithm, bits)
        return self._hydrate(record)

    def import_key(
        self,
        name: str,
        private_key: bytes,
        public_key: Optional[bytes] = None,
    ) -> InfraSshKey:
        """
        Import an existing private key (and optionally its ``.pub`` companion).

        Args:
            name: Base name for the pair.
            private_key: Raw private key bytes (OpenSSH or PEM).
            public_key: Raw public key bytes; derived with ``ssh-keygen -y``
                when omitted.

        Returns:
            The stored :class:`InfraSshKey`.

        Raises:
            InfraValidationError: The material is missing, unreadable or
                passphrase protected.
        """
        _require_keygen()

        key_name = (name or "").strip()
        if not key_name:
            raise InfraValidationError("A key name is required")
        if not private_key:
            raise InfraValidationError("A private key file is required")

        key_id = f"key-{uuid.uuid4().hex[:8]}"
        os.makedirs(self._folder, exist_ok=True)
        private_file = os.path.join(self._folder, key_id)
        public_file = f"{private_file}.pub"

        with open(private_file, "wb") as handle:
            handle.write(private_key)
        os.chmod(private_file, 0o600)

        try:
            derived = _derive_public_key(private_file)
            if public_key:
                public_line = public_key.decode("utf-8", "replace").strip()
            else:
                public_line = derived
            if not public_line:
                raise InfraValidationError("The public key could not be determined")
            with open(public_file, "w", encoding="utf-8") as handle:
                handle.write(public_line + "\n")
        except Exception:
            for path in (private_file, public_file):
                if os.path.isfile(path):
                    os.remove(path)
            raise

        algorithm, bits = self._algorithm_from_line(public_line)
        record = self._register(
            key_id=key_id,
            name=key_name,
            algorithm=algorithm,
            bits=bits,
            source="uploaded",
            private_file=private_file,
            public_line=public_line,
        )
        logger.info("SSH key %s imported from upload", key_id)
        return self._hydrate(record)

    def delete(self, key_id: str) -> None:
        """
        Delete a key pair and its files.

        Raises:
            KeyError: The key id is unknown.
            InfraConflictError: A host still references the key.
        """
        hosts = get_host_store().hosts_using_key(key_id)
        if hosts:
            raise InfraConflictError(
                f"Key '{key_id}' is still used by: {', '.join(hosts)}"
            )

        with self._lock:
            records = self._load()
            target = next((item for item in records if item.get("id") == key_id), None)
            if target is None:
                raise KeyError(key_id)
            remaining = [item for item in records if item.get("id") != key_id]
            self._persist(remaining)

        for path in (target.get("private_key_file"), target.get("public_key_file")):
            if path and os.path.isfile(path):
                os.remove(path)
        logger.info("SSH key %s deleted", key_id)

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _algorithm_from_line(public_line: str) -> tuple:
        """Guess ``(algorithm, bits)`` from a public key line."""
        head = (public_line or "").split(" ")[0].lower()
        if "rsa" in head:
            return "rsa", DEFAULT_BITS["rsa"]
        return "ed25519", DEFAULT_BITS["ed25519"]

    def _register(
        self,
        key_id: str,
        name: str,
        algorithm: str,
        bits: int,
        source: str,
        private_file: str,
        public_line: str = "",
    ) -> Dict[str, Any]:
        """Persist the metadata of a freshly created/imported pair."""
        public_file = f"{private_file}.pub"
        if not public_line and os.path.isfile(public_file):
            with open(public_file, "r", encoding="utf-8") as handle:
                public_line = handle.read().strip()

        record = {
            "id": key_id,
            "name": name,
            "algorithm": algorithm,
            "bits": bits,
            "fingerprint": _fingerprint(public_file) if os.path.isfile(public_file) else "",
            "source": source,
            "public_key": public_line,
            "private_key_file": private_file,
            "public_key_file": public_file,
            "created_at": _now(),
        }

        with self._lock:
            records = [item for item in self._load() if item.get("id") != key_id]
            records.append(record)
            self._persist(records)
        return record

    def _hydrate(self, record: Dict[str, Any]) -> InfraSshKey:
        """Build the API model, resolving the hosts that use the key."""
        key_id = record.get("id") or ""
        hosts = get_host_store().hosts_using_key(key_id)
        return InfraSshKey(
            id=key_id,
            name=record.get("name") or "",
            algorithm=record.get("algorithm") or "ed25519",
            bits=int(record.get("bits") or DEFAULT_BITS["ed25519"]),
            fingerprint=record.get("fingerprint") or "",
            source=record.get("source") or "generated",
            public_key=record.get("public_key") or "",
            private_key_file=record.get("private_key_file") or "",
            public_key_file=record.get("public_key_file") or "",
            created_at=record.get("created_at") or "",
            hosts=hosts,
        )

    def _record(self, key_id: str) -> Dict[str, Any]:
        """Return the raw metadata record of a key (raises ``KeyError``)."""
        target = (key_id or "").strip()
        with self._lock:
            for record in self._load():
                if record.get("id") == target:
                    return record
        raise KeyError(key_id)

    def _load(self) -> List[Dict[str, Any]]:
        """Read the metadata document."""
        raw = _read_json(self._path, [])
        if not isinstance(raw, list):
            logger.error("%s does not contain a JSON array, ignoring it", self._path)
            return []
        return [item for item in raw if isinstance(item, dict) and item.get("id")]

    def _persist(self, records: List[Dict[str, Any]]) -> None:
        """Write the metadata document back."""
        _write_json(self._path, records)


# ── Singleton ─────────────────────────────────────────────────────────────────

_key_store: Optional[SshKeyStore] = None
_key_store_lock = threading.Lock()


def get_ssh_key_store() -> SshKeyStore:
    """Return the process-wide :class:`SshKeyStore` (lazily created)."""
    global _key_store
    if _key_store is None:
        with _key_store_lock:
            if _key_store is None:
                _key_store = SshKeyStore()
    return _key_store

# Made with ❤️ by codx-junior