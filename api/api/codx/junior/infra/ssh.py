"""
SSH helpers: connectivity probe, remote command execution and Docker socket
tunnelling.

Two problems are solved here
----------------------------
1. **Bootstrap** – a freshly provisioned machine only exposes SSH. We wait for
   the port, optionally install Docker and report the output.
2. **Management** – `DockerClient` speaks HTTP over a unix socket or TCP. For
   an SSH host we therefore open a *unix socket tunnel* with the system `ssh`
   client (``ssh -N -L /tmp/xxx.sock:/var/run/docker.sock``) and hand that
   socket to the existing client, so every `/api/infra/*` endpoint works
   unchanged on remote hosts.

Notes
-----
* The system `ssh` binary is required (it is already assumed by codx-junior for
  `ssh-keygen`). Passphrase-protected keys are not supported: the tunnel and
  the bootstrap run in batch mode.
* Tunnels are cached per connection tuple and kept open until the process ends
  (`atexit` → :func:`close_tunnels`). A dead tunnel (`ssh` exited) is detected
  and recreated on the next access.

Example
-------
```python
from codx.junior.infra.ssh import wait_for_port, install_docker, docker_socket_endpoint

wait_for_port("10.0.0.21", 22, timeout=300)
install_docker("10.0.0.21", user="root", key_file="/home/codx-junior/infra/ssh-keys/key-a1b2")
endpoint = docker_socket_endpoint("host-prod-01", hostname="10.0.0.21",
                                  user="root", key_file="/home/codx-junior/infra/ssh-keys/key-a1b2")
# endpoint -> 'unix:///tmp/codx-ssh-xxxx/docker.sock'
```
"""

import atexit
import logging
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from typing import Dict, List, Optional, Tuple

from codx.junior.infra.errors import SshError

logger = logging.getLogger(__name__)

DEFAULT_SSH_TIMEOUT = float(os.environ.get("CODX_JUNIOR_SSH_TIMEOUT", "30"))
TUNNEL_START_TIMEOUT = float(os.environ.get("CODX_JUNIOR_SSH_TUNNEL_TIMEOUT", "20"))
REMOTE_DOCKER_SOCKET = os.environ.get(
    "CODX_JUNIOR_DOCKER_SOCKET", "/var/run/docker.sock"
)

SSH_BIN = "ssh"

# Non-interactive defaults: never prompt, never pollute known_hosts.
SSH_OPTIONS: List[str] = [
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
    "-o", f"ConnectTimeout={int(DEFAULT_SSH_TIMEOUT)}",
]

INSTALL_DOCKER_COMMAND = (
    "set -e; "
    "if ! command -v docker >/dev/null 2>&1; then "
    "  curl -fsSL https://get.docker.com | sh; "
    "fi; "
    "systemctl enable --now docker"
)


# ── Primitives ────────────────────────────────────────────────────────────────


def ssh_available() -> bool:
    """Return True when the system `ssh` binary can be found."""
    return shutil.which(SSH_BIN) is not None


def _require_ssh() -> None:
    if not ssh_available():
        raise SshError("The 'ssh' binary is not installed on the codx-junior server")


def _ssh_target(hostname: str, user: Optional[str]) -> str:
    """Build the ``user@host`` target, defaulting to ``root``."""
    return f"{user or 'root'}@{hostname}"


def run_ssh(
    hostname: str,
    user: str = "root",
    port: int = 22,
    key_file: Optional[str] = None,
    command: str = "true",
    timeout: float = 120.0,
) -> Tuple[int, str]:
    """
    Run a command on a remote machine.

    Args:
        hostname: Target host or IP.
        user: Login user.
        port: SSH port.
        key_file: Private key file (skipped when empty).
        command: Shell command, run by the remote login shell.
        timeout: Seconds before the call is aborted.

    Returns:
        ``(returncode, stdout + stderr)``. A non-zero code is *returned*, not
        raised, so callers can decide what is fatal.

    Raises:
        SshError: The `ssh` binary is missing or the call timed out.
    """
    _require_ssh()
    if not hostname:
        raise SshError("A hostname is required to run an SSH command")

    args: List[str] = [SSH_BIN, *SSH_OPTIONS, "-p", str(port or 22)]
    if key_file:
        if not os.path.isfile(key_file):
            raise SshError(f"SSH key file not found: {key_file}")
        args += ["-i", key_file]
    args += [_ssh_target(hostname, user), command]

    try:
        completed = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as ex:
        raise SshError(f"SSH command timed out after {timeout:g}s: {command}") from ex
    except OSError as ex:
        raise SshError(f"Cannot run ssh: {ex}") from ex

    output = f"{completed.stdout or ''}{completed.stderr or ''}".strip()
    return completed.returncode, output


def wait_for_port(
    hostname: str,
    port: int = 22,
    timeout: float = 240.0,
    interval: float = 3.0,
) -> bool:
    """
    Poll a TCP port until it accepts connections.

    Used to wait for a freshly created instance to finish booting (sshd is the
    first thing that answers).

    Args:
        hostname: Target host or IP.
        port: Port to probe.
        timeout: Give up after this many seconds.
        interval: Delay between attempts.

    Returns:
        True when the port opened, False on timeout.
    """
    deadline = time.time() + max(1.0, timeout)
    while time.time() < deadline:
        try:
            with socket.create_connection((hostname, port), timeout=5):
                return True
        except OSError:
            time.sleep(interval)
    return False


def install_docker(
    hostname: str,
    user: str = "root",
    port: int = 22,
    key_file: Optional[str] = None,
    timeout: float = 900.0,
) -> str:
    """
    Install Docker Engine (and enable the service) on a remote machine.

    Uses the official convenience script, guarded by a ``command -v docker``
    check so re-running it is a no-op.

    Args:
        hostname: Target host or IP.
        user: Login user (needs sudo/root).
        port: SSH port.
        key_file: Private key file.
        timeout: Seconds allowed for the installation.

    Returns:
        The command output (useful for the provisioning journal).

    Raises:
        SshError: The installation failed or timed out.
    """
    code, output = run_ssh(
        hostname,
        user=user,
        port=port,
        key_file=key_file,
        command=INSTALL_DOCKER_COMMAND,
        timeout=timeout,
    )
    if code != 0:
        raise SshError(f"Docker installation failed (exit {code}): {output[-800:]}")
    return output


def docker_ready(
    hostname: str,
    user: str = "root",
    port: int = 22,
    key_file: Optional[str] = None,
    timeout: float = 60.0,
) -> bool:
    """Return True when ``docker info`` succeeds on the remote machine."""
    try:
        code, _ = run_ssh(
            hostname,
            user=user,
            port=port,
            key_file=key_file,
            command="docker info --format '{{.ServerVersion}}'",
            timeout=timeout,
        )
    except SshError as ex:
        logger.debug("docker_ready failed: %s", ex)
        return False
    return code == 0


# ── Docker socket tunnel ──────────────────────────────────────────────────────

TunnelKey = Tuple[str, int, str, str]


class SshTunnel:
    """A ``ssh -N -L <unix socket>:<remote socket>`` forwarder."""

    def __init__(
        self,
        hostname: str,
        port: int = 22,
        user: str = "root",
        key_file: Optional[str] = None,
        remote_socket: str = REMOTE_DOCKER_SOCKET,
    ):
        self.hostname = hostname
        self.port = port or 22
        self.user = user or "root"
        self.key_file = key_file or ""
        self.remote_socket = remote_socket or REMOTE_DOCKER_SOCKET
        self.socket_path = ""
        self._folder = ""
        self._process: Optional[subprocess.Popen] = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> str:
        """
        Open the tunnel and wait for the local socket to appear.

        Returns:
            The local unix socket path.

        Raises:
            SshError: The `ssh` binary is missing or the forward failed.
        """
        _require_ssh()
        self._folder = tempfile.mkdtemp(prefix="codx-ssh-")
        self.socket_path = os.path.join(self._folder, "docker.sock")

        args: List[str] = [
            SSH_BIN, *SSH_OPTIONS,
            "-o", "ExitOnForwardFailure=yes",
            "-N", "-L", f"{self.socket_path}:{self.remote_socket}",
            "-p", str(self.port),
        ]
        if self.key_file:
            args += ["-i", self.key_file]
        args.append(_ssh_target(self.hostname, self.user))

        try:
            self._process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as ex:
            self.close()
            raise SshError(f"Cannot start the SSH tunnel: {ex}") from ex

        deadline = time.time() + TUNNEL_START_TIMEOUT
        while time.time() < deadline:
            if os.path.exists(self.socket_path):
                logger.info(
                    "SSH tunnel to %s opened at %s", self.hostname, self.socket_path
                )
                return self.socket_path
            if self._process.poll() is not None:
                message = ""
                if self._process.stderr:
                    message = (self._process.stderr.read() or "").strip()
                self.close()
                raise SshError(
                    f"SSH tunnel to {self.hostname} closed immediately: {message[:400]}"
                )
            time.sleep(0.2)

        self.close()
        raise SshError(f"SSH tunnel to {self.hostname} did not open in time")

    def alive(self) -> bool:
        """Return True when the forwarder is still running with its socket."""
        return (
            self._process is not None
            and self._process.poll() is None
            and os.path.exists(self.socket_path)
        )

    def close(self) -> None:
        """Terminate the forwarder and remove the temporary socket folder."""
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception as ex:  # pragma: no cover - best effort
                logger.debug("Error stopping SSH tunnel: %s", ex)
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

        if self._folder and os.path.isdir(self._folder):
            shutil.rmtree(self._folder, ignore_errors=True)
        self.socket_path = ""
        self._folder = ""


_tunnels: Dict[TunnelKey, SshTunnel] = {}
_tunnels_lock = threading.Lock()


def docker_socket_endpoint(
    host_id: str,
    hostname: str,
    port: int = 22,
    user: str = "root",
    key_file: Optional[str] = None,
    remote_socket: str = REMOTE_DOCKER_SOCKET,
) -> str:
    """
    Return a Docker endpoint backed by an SSH tunnel to the remote daemon.

    The tunnel is cached per ``(hostname, port, user, key)`` and reused until
    the process exits or the forwarder dies.

    Args:
        host_id: Host id (used for logging only).
        hostname: Remote machine.
        port: SSH port.
        user: SSH login user.
        key_file: Private key file.
        remote_socket: Docker socket path on the remote machine.

    Returns:
        ``unix:///tmp/codx-ssh-xxxx/docker.sock``

    Raises:
        SshError: The tunnel could not be established.
    """
    target = (hostname or "").strip()
    if not target:
        raise SshError(f"Host {host_id} has no hostname to open an SSH tunnel")

    key: TunnelKey = (target, int(port or 22), user or "root", key_file or "")
    with _tunnels_lock:
        tunnel = _tunnels.get(key)
        if tunnel is not None and tunnel.alive():
            return "unix://" + tunnel.socket_path
        if tunnel is not None:
            logger.info("SSH tunnel to %s died, reconnecting", target)
            tunnel.close()
        tunnel = SshTunnel(
            hostname=target,
            port=port,
            user=user,
            key_file=key_file,
            remote_socket=remote_socket,
        )
        socket_path = tunnel.start()
        _tunnels[key] = tunnel
        return "unix://" + socket_path


def forget_tunnels(hostname: str) -> None:
    """Close every tunnel opened to ``hostname`` (host updated/removed)."""
    with _tunnels_lock:
        keys = [key for key in _tunnels if key[0] == hostname]
        for key in keys:
            _tunnels.pop(key).close()


def close_tunnels() -> None:
    """Close every open tunnel (registered with ``atexit``)."""
    with _tunnels_lock:
        for tunnel in _tunnels.values():
            tunnel.close()
        _tunnels.clear()


atexit.register(close_tunnels)

# Made with ❤️ by codx-junior