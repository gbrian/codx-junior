"""
Admin-only interactive container shells (``docker exec``) for the web UI.

Why a PTY + the Docker CLI instead of the Engine API?
-----------------------------------------------------
The Engine API exposes ``POST /containers/{id}/exec`` + ``POST /exec/{id}/start``,
but ``/start`` upgrades the HTTP connection and is **bidirectional**. ``httpx``
(the client used by :mod:`codx.junior.infra.docker_client`) cannot half-close and
then keep writing to a hijacked socket, so driving an interactive terminal over
it would mean hand-writing a raw HTTP upgrade on the Unix socket.

The ``docker exec -it`` CLI already speaks that protocol and is present in the
codx-junior image (the compose stack actions already shell out to the CLI too).
This module therefore allocates a local PTY, runs the CLI attached to it, and
pumps bytes between the PTY and the WebSocket. The daemon-side rules (container
must be running, TTY allocation, user permissions) are still enforced by Docker
itself; this module adds the codx-junior rules:

  * **admins only** — issuing a shell ticket re-checks the role, and the
    WebSocket only accepts a ticket (never a raw JWT);
  * **running containers only**;
  * **allow-listed shells only** (no arbitrary command execution through the
    ``shell`` field);
  * **single-use, short-lived tickets** so a WebSocket URL never carries the
    long-lived JWT (URLs end up in proxy logs).

Lifecycle
---------
``POST /api/infra/containers/{id}/shell`` issues a ticket (admin). The browser
then opens ``WS /api/infra/containers/{id}/shell?ticket=…``. The router validates
the ticket, starts a :class:`ContainerShellSession`, and relays JSON frames:

    client → server   {"type": "input",  "data": "<base64>"}
                      {"type": "resize", "cols": 120, "rows": 32}
                      {"type": "close"}
                      {"type": "ping"}
    server → client   {"type": "ready",  "container_id": "…", "shell": "/bin/sh"}
                      {"type": "output", "data": "<base64>"}
                      {"type": "exit",   "code": 0}
                      {"type": "error",  "message": "…"}
                      {"type": "pong"}

Base64 is used for terminal payloads because a PTY is a byte stream: it may
contain partial UTF-8 sequences, and JSON strings cannot carry arbitrary bytes.

Diagram
-------
flowchart LR
    B[Browser xterm.js] -->|ticket| A[POST issue]
    A -->|require_admin| S[ShellTicketStore]
    B -->|WS + ticket| W[WS router]
    W -->|consume| S
    W --> P[ContainerShellSession]
    P --> T[(PTY master)]
    T --> D[docker exec -it]
    D --> C[(container)]

Environment
-----------
CODX_JUNIOR_CONTAINER_SHELL_ENABLED  ``0``/``false`` disables the feature (503)
CODX_JUNIOR_DOCKER_BIN               Docker CLI path (default: ``docker`` in PATH)
CODX_JUNIOR_SHELL_TICKET_TTL         Ticket lifetime in seconds (default 60)
CODX_JUNIOR_SHELL_MAX_SESSIONS       Concurrent shell cap (default 20)
"""

from __future__ import annotations

import atexit
import errno
import fcntl
import logging
import os
import pty
import queue
import secrets
import shutil
import signal
import struct
import subprocess
import termios
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from codx.junior.infra.docker_client import (
    DEFAULT_ENDPOINT,
    DockerAPIError,
    DockerUnavailable,
)

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_SHELL = "/bin/sh"

#: Shells an admin may request. The value is passed as a single argv element, so
#: a value such as ``sh -c whoami`` can never be interpreted as extra arguments.
ALLOWED_SHELLS: Tuple[str, ...] = (
    "/bin/sh",
    "/bin/bash",
    "/bin/ash",
    "/bin/zsh",
    "/bin/dash",
    "sh",
    "bash",
    "ash",
    "zsh",
    "dash",
)

DEFAULT_TICKET_TTL = 60
DEFAULT_MAX_SESSIONS = 20
MAX_INPUT_BYTES = 64 * 1024
MIN_COLS, MAX_COLS = 20, 500
MIN_ROWS, MAX_ROWS = 5, 200

READ_CHUNK = 64 * 1024
EVENT_QUEUE_SIZE = 256
CLOSE_GRACE_SECONDS = 3.0


def _env_flag(name: str, default: bool = True) -> bool:
    """Read a boolean environment flag (``0``/``false``/``no`` disable it)."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def feature_enabled() -> bool:
    """Return whether the container shell feature is enabled."""
    return _env_flag("CODX_JUNIOR_CONTAINER_SHELL_ENABLED", True)


def docker_binary() -> str:
    """Resolve the Docker CLI, raising a user-facing error when it is missing."""
    configured = (os.environ.get("CODX_JUNIOR_DOCKER_BIN") or "").strip()
    if configured:
        if os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        raise ShellUnavailableError(
            f"CODX_JUNIOR_DOCKER_BIN points to an executable that does not exist: {configured}"
        )
    found = shutil.which("docker")
    if not found:
        raise ShellUnavailableError(
            "The Docker CLI ('docker') was not found in PATH. Container shells "
            "need the CLI because interactive exec streams are bidirectional."
        )
    return found


# ── Errors ────────────────────────────────────────────────────────────────────


class ShellError(Exception):
    """Base error for container shell operations."""

    status_code = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ShellValidationError(ShellError):
    """Bad container, shell, size or not-running state (HTTP 400/409)."""

    status_code = 400


class ShellConflictError(ShellValidationError):
    """The container exists but cannot be attached to (HTTP 409)."""

    status_code = 409


class ShellAccessDeniedError(ShellError):
    """The caller is not an admin (HTTP 403)."""

    status_code = 403


class ShellUnavailableError(ShellError):
    """Docker CLI/socket/feature is unavailable (HTTP 503)."""

    status_code = 503


class ShellLimitError(ShellError):
    """Too many concurrent shell sessions (HTTP 429)."""

    status_code = 429


# ── Validation helpers ────────────────────────────────────────────────────────


def normalize_shell(shell: Optional[str]) -> str:
    """
    Validate and return the requested shell.

    Args:
        shell: Requested shell (``None``/empty uses :data:`DEFAULT_SHELL`).

    Returns:
        One of :data:`ALLOWED_SHELLS`.

    Raises:
        ShellValidationError: The shell is not allow-listed.
    """
    value = (shell or DEFAULT_SHELL).strip()
    if value not in ALLOWED_SHELLS:
        raise ShellValidationError(
            "Unsupported shell. Choose one of: " + ", ".join(ALLOWED_SHELLS)
        )
    return value


def clamp_size(cols: int, rows: int) -> Tuple[int, int]:
    """Clamp terminal dimensions to safe bounds."""
    try:
        cols = int(cols)
        rows = int(rows)
    except (TypeError, ValueError):
        cols, rows = 120, 32
    return (
        max(MIN_COLS, min(cols, MAX_COLS)),
        max(MIN_ROWS, min(rows, MAX_ROWS)),
    )


def _cli_endpoint(endpoint: str) -> Tuple[str, Dict[str, str]]:
    """
    Translate a daemon endpoint into what ``docker -H`` accepts.

    Args:
        endpoint: ``unix://``, bare socket path, ``tcp://``, ``http://`` or
            ``ssh://`` endpoint.

    Returns:
        ``(endpoint_for_cli, extra_env)``. HTTPS endpoints keep their transport
        implicit (``tcp://``) and enable TLS verification; certificate paths
        belong to the Docker CLI's own environment (``DOCKER_CERT_PATH``).

    Raises:
        ShellValidationError: The endpoint scheme is unsupported.
    """
    raw = (endpoint or "").strip()
    if not raw:
        raise ShellValidationError("The Docker host has no endpoint configured.")
    if raw.startswith("https://"):
        return "tcp://" + raw[len("https://"):], {"DOCKER_TLS_VERIFY": "1"}
    if raw.startswith("http://"):
        return "tcp://" + raw[len("http://"):], {}
    if raw.startswith(("unix://", "tcp://", "ssh://")):
        return raw, {}
    if raw.startswith("/"):
        return raw, {}
    raise ShellValidationError(f"Unsupported Docker endpoint scheme: {raw}")


def build_exec_command(
    container_id: str,
    shell: str,
    endpoint: str = DEFAULT_ENDPOINT,
    docker_bin: Optional[str] = None,
    is_local: bool = True,
) -> Tuple[List[str], Dict[str, str]]:
    """
    Build the ``docker exec`` argv and environment for an interactive shell.

    Args:
        container_id: Container name or id (passed as its own argv element).
        shell: Allow-listed shell path.
        endpoint: Docker endpoint of the host that owns the container.
        docker_bin: Docker CLI path (defaults to :func:`docker_binary`).
        is_local: Whether the endpoint is the local daemon.

    Returns:
        ``(argv, env)`` ready for ``subprocess.Popen``.

    Raises:
        ShellValidationError: Empty container id, invalid shell or endpoint.
        ShellUnavailableError: The Docker CLI cannot be resolved.
    """
    container_id = (container_id or "").strip()
    if not container_id:
        raise ShellValidationError("A container id or name is required.")
    shell = normalize_shell(shell)
    binary = docker_bin or docker_binary()

    argv: List[str] = [binary]
    endpoint_arg, extra_env = _cli_endpoint(endpoint)
    # Omit -H for the default local socket so the CLI uses its own context and
    # the common case stays identical to running `docker exec` by hand.
    if not (is_local and endpoint_arg == DEFAULT_ENDPOINT):
        argv += ["-H", endpoint_arg]

    argv += [
        "exec",
        "-i",                    # keep stdin open
        "-t",                    # allocate a TTY inside the container
        "-e", "TERM=xterm-256color",
        "-e", "COLORTERM=truecolor",
        container_id,
        shell,
    ]

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    env.update(extra_env)
    return argv, env


# ── Ticket store ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ShellTicket:
    """Everything a WebSocket needs, captured when the admin asked for it."""

    value: str
    username: str
    role: str
    container_id: str
    host_id: str
    shell: str
    created_at: float
    expires_at: float

    @property
    def expired(self) -> bool:
        """True once the ticket lifetime elapsed."""
        return time.monotonic() >= self.expires_at


class ShellTicketStore:
    """
    In-memory, single-use tickets that bootstrap a shell WebSocket.

    A ticket is bound to the admin who requested it, the container, the host and
    the shell. It is removed on the first successful :meth:`consume`, so a leaked
    URL cannot be replayed. Tickets are intentionally *not* persisted: a restart
    of the API invalidates every pending shell, which is the safe default.
    """

    def __init__(self, ttl: Optional[int] = None, max_tickets: int = 1000) -> None:
        self.ttl = max(5, int(ttl or DEFAULT_TICKET_TTL))
        self.max_tickets = max(1, int(max_tickets))
        self._tickets: Dict[str, ShellTicket] = {}
        self._lock = threading.Lock()

    def issue(
        self,
        user,
        container_id: str,
        host_id: str,
        shell: str,
    ) -> ShellTicket:
        """
        Create a ticket for an admin.

        Args:
            user: Authenticated user object (``username``/``role`` attributes).
            container_id: Container the shell will attach to.
            host_id: Docker host id.
            shell: Validated shell path.

        Returns:
            The newly created :class:`ShellTicket`.

        Raises:
            ShellAccessDeniedError: The user is not an admin.
            ShellValidationError: Missing container/host.
        """
        if not user or getattr(user, "role", None) != "admin":
            raise ShellAccessDeniedError("Container shells are restricted to admins.")
        container_id = (container_id or "").strip()
        host_id = (host_id or "").strip()
        if not container_id:
            raise ShellValidationError("A container id or name is required.")
        if not host_id:
            raise ShellValidationError("A Docker host id is required.")
        shell = normalize_shell(shell)

        now = time.monotonic()
        value = secrets.token_urlsafe(32)
        ticket = ShellTicket(
            value=value,
            username=getattr(user, "username", "") or "",
            role="admin",
            container_id=container_id,
            host_id=host_id,
            shell=shell,
            created_at=now,
            expires_at=now + self.ttl,
        )

        with self._lock:
            self._purge_locked(now)
            if len(self._tickets) >= self.max_tickets:
                # Drop the oldest to keep a misbehaving client from growing the
                # map without bound.
                oldest = min(self._tickets.values(), key=lambda item: item.created_at)
                self._tickets.pop(oldest.value, None)
            self._tickets[value] = ticket
        return ticket

    def consume(self, value: str) -> Optional[ShellTicket]:
        """
        Atomically validate and remove a ticket.

        Args:
            value: Ticket value from the WebSocket query string.

        Returns:
            The ticket when it existed, had not expired and still belongs to an
            admin; ``None`` otherwise.
        """
        if not value:
            return None
        now = time.monotonic()
        with self._lock:
            self._purge_locked(now)
            ticket = self._tickets.pop(value, None)
        if not ticket or ticket.expired or ticket.role != "admin":
            return None
        return ticket

    def _purge_locked(self, now: float) -> None:
        """Remove expired tickets (caller holds the lock)."""
        expired = [key for key, ticket in self._tickets.items() if ticket.expires_at <= now]
        for key in expired:
            self._tickets.pop(key, None)


#: Process-wide ticket store shared by the ticket and WebSocket routes.
shell_tickets = ShellTicketStore()


# ── Running-container check ───────────────────────────────────────────────────


def ensure_running(manager, container_id: str, host_id: str) -> str:
    """
    Verify the container exists and is running before a ticket is issued.

    Args:
        manager: ``InfraManager`` used to resolve the Docker client.
        container_id: Container id or name.
        host_id: Docker host id.

    Returns:
        The canonical container id.

    Raises:
        ShellConflictError: The container is stopped, paused, restarting or dead.
        ShellValidationError: The container does not exist.
        ShellUnavailableError: The daemon cannot be reached.
    """
    from urllib.parse import quote

    client = manager.client(host_id)
    try:
        detail = client.get_json(f"/containers/{quote(container_id, safe='')}/json")
    except DockerAPIError as ex:
        if ex.status_code == 404:
            raise ShellValidationError(f"Container not found: {container_id}") from ex
        raise
    except DockerUnavailable as ex:
        raise ShellUnavailableError(str(ex)) from ex

    state = detail.get("State") or {}
    running = bool(state.get("Running"))
    paused = bool(state.get("Paused"))
    status = str(state.get("Status") or ("paused" if paused else "stopped"))
    if not running:
        raise ShellConflictError(
            f"Container '{container_id}' is not running (state: {status}). "
            "Start it before opening a shell."
        )
    if paused:
        raise ShellConflictError(
            f"Container '{container_id}' is paused. Unpause it before opening a shell."
        )
    return str(detail.get("Id") or container_id)


# ── PTY-backed shell session ──────────────────────────────────────────────────


class ContainerShellSession:
    """
    One interactive shell, backed by a local PTY and a child process.

    The object is deliberately synchronous: the WebSocket router reads
    :attr:`events` from a worker thread and writes through :meth:`write` /
    :meth:`resize`. All methods are safe to call from different threads, and
    :meth:`close` may be called more than once.

    Events pushed to :attr:`events` are ``("output", bytes)`` and
    ``("exit", int | None)``. A ``("error", str)`` event is emitted when the child
    cannot be started or the PTY fails unexpectedly.
    """

    def __init__(
        self,
        argv: List[str],
        env: Optional[Dict[str, str]] = None,
        cols: int = 120,
        rows: int = 32,
        cwd: Optional[str] = None,
        on_start: Optional[Callable[["ContainerShellSession"], None]] = None,
    ) -> None:
        self.argv = list(argv)
        self.env = env
        self.cwd = cwd
        self.cols, self.rows = clamp_size(cols, rows)
        self._on_start = on_start
        self.events: "queue.Queue[Tuple[str, object]]" = queue.Queue(
            maxsize=EVENT_QUEUE_SIZE
        )
        self.process: Optional[subprocess.Popen] = None
        self._master_fd: Optional[int] = None
        self._reader: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._fd_lock = threading.Lock()
        self._closed = False
        self.started_at: Optional[float] = None
        self.ended_at: Optional[float] = None
        self.exit_code: Optional[int] = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> "ContainerShellSession":
        """
        Allocate the PTY and spawn the child.

        Returns:
            ``self`` so the session can be started inline.

        Raises:
            ShellUnavailableError: The PTY or child process could not be created.
        """
        if self.process is not None:
            return self
        try:
            master_fd, slave_fd = pty.openpty()
        except OSError as ex:
            raise ShellUnavailableError(f"Cannot allocate a PTY: {ex}") from ex

        try:
            self._set_winsize(master_fd, self.cols, self.rows)
            self.process = subprocess.Popen(
                self.argv,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=self.env,
                cwd=self.cwd,
                start_new_session=True,
                close_fds=True,
            )
        except Exception as ex:
            self._close_fd(master_fd)
            self._close_fd(slave_fd)
            raise ShellUnavailableError(f"Cannot start the shell process: {ex}") from ex
        finally:
            # The child owns the slave side; the parent only reads/writes the
            # master. Keeping the slave open would prevent EOF on exit.
            if self.process is not None:
                self._close_fd(slave_fd)

        self._master_fd = master_fd
        self.started_at = time.time()
        if self._on_start:
            try:
                self._on_start(self)
            except Exception:  # pragma: no cover - defensive callback
                logger.exception("Container shell on_start callback failed")

        self._reader = threading.Thread(
            target=self._read_loop,
            name=f"container-shell-{self.process.pid}",
            daemon=True,
        )
        self._reader.start()
        return self

    def _read_loop(self) -> None:
        """Pump PTY bytes into :attr:`events` until EOF, then report the exit."""
        fd = self._master_fd
        if fd is None:
            return
        try:
            while True:
                try:
                    chunk = os.read(fd, READ_CHUNK)
                except OSError as ex:
                    if ex.errno in (errno.EIO, errno.EBADF):
                        break
                    if not self._closed:
                        self._emit("error", f"PTY read failed: {ex}")
                    break
                if not chunk:
                    break
                self._emit("output", chunk)
        finally:
            code = self._wait_for_exit()
            self.ended_at = time.time()
            self.exit_code = code
            self._emit("exit", code)
            self._release_fd()

    def _wait_for_exit(self) -> Optional[int]:
        """Wait for the child to settle, escalating to SIGKILL if necessary."""
        process = self.process
        if process is None:
            return None
        try:
            return process.wait(timeout=CLOSE_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            self._signal(signal.SIGKILL)
            try:
                return process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive
                return None

    def _signal(self, sig: int) -> None:
        """Signal the child's process group (it was started in a new session)."""
        process = self.process
        if process is None or process.poll() is not None:
            return
        try:
            os.killpg(os.getpgid(process.pid), sig)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                process.send_signal(sig)
            except Exception:  # pragma: no cover - best effort
                pass

    # -- io ----------------------------------------------------------------

    def write(self, data: bytes) -> bool:
        """
        Write client bytes to the PTY.

        Args:
            data: Raw bytes (already decoded from the WebSocket frame).

        Returns:
            True when the bytes were handed to the PTY.
        """
        if not data:
            return True
        fd = self._master_fd
        if fd is None or self._closed:
            return False
        try:
            os.write(fd, data)
            return True
        except OSError as ex:
            logger.debug("Container shell write failed: %s", ex)
            return False

    def resize(self, cols: int, rows: int) -> bool:
        """
        Apply a new terminal size (Docker CLI forwards SIGWINCH to the exec).

        Args:
            cols: Columns (clamped).
            rows: Rows (clamped).

        Returns:
            True when the ioctl succeeded.
        """
        fd = self._master_fd
        if fd is None or self._closed:
            return False
        self.cols, self.rows = clamp_size(cols, rows)
        try:
            self._set_winsize(fd, self.cols, self.rows)
            return True
        except OSError as ex:
            logger.debug("Container shell resize failed: %s", ex)
            return False

    @staticmethod
    def _set_winsize(fd: int, cols: int, rows: int) -> None:
        """Set the kernel window size for a PTY file descriptor."""
        packed = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, packed)

    def _emit(self, kind: str, payload: object) -> None:
        """Push an event, blocking if the consumer is behind (backpressure)."""
        try:
            self.events.put((kind, payload))
        except Exception:  # pragma: no cover - queue is unbounded in practice
            pass

    # -- close -------------------------------------------------------------

    def close(self) -> None:
        """Terminate the child and release the PTY. Safe to call repeatedly."""
        with self._lock:
            if self._closed:
                return
            self._closed = True

        self._signal(signal.SIGHUP)
        self._signal(signal.SIGTERM)

        process = self.process
        if process is not None and process.poll() is None:
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self._signal(signal.SIGKILL)
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:  # pragma: no cover - defensive
                    pass

        # Closing the master makes the reader's os.read fail, which unblocks
        # the thread even if the child did not exit cleanly.
        self._release_fd()
        logger.info(
            "Container shell closed (pid=%s, exit=%s, duration=%.1fs)",
            getattr(process, "pid", None),
            self.exit_code,
            (self.ended_at or time.time()) - (self.started_at or time.time()),
        )

    def _release_fd(self) -> None:
        """Close the master fd exactly once (the reader and close() may race)."""
        with self._fd_lock:
            fd = self._master_fd
            self._master_fd = None
        if fd is not None:
            self._close_fd(fd)

    @staticmethod
    def _close_fd(fd: Optional[int]) -> None:
        """Close a file descriptor, ignoring already-closed errors."""
        if fd is None:
            return
        try:
            os.close(fd)
        except OSError:
            pass

    @property
    def alive(self) -> bool:
        """True while the child process is running."""
        return self.process is not None and self.process.poll() is None

    @property
    def pid(self) -> Optional[int]:
        """Child pid (useful for logs/tests)."""
        return getattr(self.process, "pid", None)


def create_container_shell(
    manager,
    container_id: str,
    host_id: str,
    shell: str,
    cols: int = 120,
    rows: int = 32,
    username: str = "",
) -> ContainerShellSession:
    """
    Resolve the host, build the CLI argv and start a PTY-backed session.

    Args:
        manager: ``InfraManager`` (resolves the endpoint of ``host_id``).
        container_id: Container name or id.
        host_id: Docker host id.
        shell: Allow-listed shell.
        cols/rows: Initial terminal size.
        username: Admin opening the shell (for the audit log).

    Returns:
        A started :class:`ContainerShellSession`.

    Raises:
        ShellError: Any validation/unavailability failure.
    """
    if not feature_enabled():
        raise ShellUnavailableError(
            "Container shells are disabled by CODX_JUNIOR_CONTAINER_SHELL_ENABLED."
        )
    canonical_id = ensure_running(manager, container_id, host_id)
    host = manager.host_config(host_id)
    argv, env = build_exec_command(
        canonical_id,
        shell,
        endpoint=host.endpoint,
        is_local=host.is_local,
    )
    logger.info(
        "Opening container shell: user=%s host=%s container=%s shell=%s",
        username or "-",
        host_id,
        canonical_id[:12],
        shell,
    )
    return ContainerShellSession(argv=argv, env=env, cols=cols, rows=rows).start()


# ── Session registry / limits ─────────────────────────────────────────────────


class ShellSessionRegistry:
    """Tracks live sessions so the process can enforce a concurrency cap."""

    def __init__(self, limit: Optional[int] = None) -> None:
        self.limit = max(1, int(limit or os.environ.get(
            "CODX_JUNIOR_SHELL_MAX_SESSIONS", DEFAULT_MAX_SESSIONS
        )))
        self._sessions: Dict[str, ContainerShellSession] = {}
        self._lock = threading.Lock()

    def add(self, key: str, session: ContainerShellSession) -> None:
        """
        Register a started session.

        Raises:
            ShellLimitError: The concurrency cap was reached.
        """
        with self._lock:
            if len(self._sessions) >= self.limit:
                raise ShellLimitError(
                    f"Too many open container shells ({self.limit}). Close one and retry."
                )
            self._sessions[key] = session

    def remove(self, key: str) -> None:
        """Forget a session (does not close it)."""
        with self._lock:
            self._sessions.pop(key, None)

    def close_all(self) -> None:
        """Close every tracked session (used on shutdown/tests)."""
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            try:
                session.close()
            except Exception:  # pragma: no cover - best effort
                logger.exception("Error closing container shell session")

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)


shell_sessions = ShellSessionRegistry()

# Make sure an API shutdown does not leave `docker exec` children behind.
atexit.register(shell_sessions.close_all)


# ── Message helpers used by the router ────────────────────────────────────────


def decode_input(message: dict) -> bytes:
    """
    Decode the base64 ``data`` field of an ``input`` frame.

    Args:
        message: Parsed JSON frame.

    Returns:
        Raw bytes (possibly empty).

    Raises:
        ShellValidationError: Missing/invalid base64 or oversized payload.
    """
    import base64
    import binascii

    raw = message.get("data")
    if raw is None:
        return b""
    if not isinstance(raw, str):
        raise ShellValidationError("'data' must be a base64 string.")
    if len(raw) > MAX_INPUT_BYTES * 2:
        raise ShellValidationError("Input frame is too large.")
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as ex:
        raise ShellValidationError("'data' is not valid base64.") from ex
    if len(data) > MAX_INPUT_BYTES:
        raise ShellValidationError("Input frame is too large.")
    return data


def encode_output(data: bytes) -> str:
    """Encode PTY bytes for a JSON ``output`` frame."""
    import base64

    return base64.b64encode(data).decode("ascii")


# Made with ❤️ by codx-junior
