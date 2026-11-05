"""
Compose (stack) orchestration for the `/api/infra/*` endpoints.

Why a separate module
---------------------
``manager.py`` speaks the Docker **Engine API** only, and the Engine API has no
compose equivalent: a project is a *file on disk*, the daemon just sees
containers carrying ``com.docker.compose.*`` labels. Running ``up``, ``stop``,
``restart``, ``build``, ``pull`` or ``down`` therefore means shelling out to the
compose CLI, which fails in completely different ways (plugin missing, non-zero
exit code, minutes long runs). Keeping that here leaves :class:`InfraManager` a
pure Engine-API client and gives the compose behaviour a single home.

Every command exports ``DOCKER_HOST`` pointing at the very endpoint the rest of
the API talks to (``InfraHostConfig.endpoint``), so a stack that lives on a
remote host is operated on that host and not on the codx-junior one.

Locating a project
------------------
A compose command needs the compose file(s). The labels of the project's
containers are the source of truth, an in-process cache keeps the answer alive
after ``down`` removed every container, and ``docker compose ls --all`` is the
final fallback (e.g. after a codx-junior restart). When none of them knows the
project the request is answered with **404** — that is a "this stack does not
exist on this host" answer, not a daemon failure.

Diagram
-------
flowchart LR
    R[POST /stacks/:name/actions] --> S[stack_action]
    S --> L{locate project}
    L -->|container labels| C[(cache)]
    L -->|compose ls| CLI
    S -->|DOCKER_HOST=host endpoint| CLI[docker compose CLI]
    CLI --> D[(Docker daemon)]
"""

import json
import logging
import os
import shlex
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple, Union

from codx.junior.infra.docker_client import DockerAPIError, DockerUnavailable
from codx.junior.infra.models import (
    InfraContainer,
    InfraLogLine,
    InfraOk,
    InfraStack,
    InfraStackActionRequest,
    InfraStackLogs,
)

logger = logging.getLogger(__name__)

COMPOSE_PROJECT_LABEL = "com.docker.compose.project"
COMPOSE_SERVICE_LABEL = "com.docker.compose.service"
COMPOSE_WORKDIR_LABEL = "com.docker.compose.project.working_dir"
COMPOSE_CONFIG_LABEL = "com.docker.compose.project.config_files"

# Compose sub-commands accepted by ``POST /api/infra/stacks/{name}/actions``.
#
# ``up`` is what the UI labels "Start": it is the only command that CREATES the
# missing containers, which is why a project brought ``down`` is revived with
# ``up`` and never with ``start``/``create``. ``down`` removes the containers and
# the networks but KEEPS the named volumes (`-v` is deliberately not sent).
COMPOSE_ACTIONS = ("up", "stop", "restart", "build", "pull", "down")

# Arguments appended after ``docker compose [-p NAME] [-f FILE] …``.
COMPOSE_ACTION_ARGS: Dict[str, List[str]] = {
    "up": ["up", "-d"],
    "stop": ["stop"],
    "restart": ["restart"],
    "build": ["build"],
    "pull": ["pull"],
    "down": ["down"],
}

# Building or pulling images legitimately takes minutes, so the default is
# generous on purpose: a slow registry must not be reported as a failure.
COMPOSE_TIMEOUT = float(os.environ.get("CODX_JUNIOR_COMPOSE_TIMEOUT", "600"))

# ``docker compose ls`` and the CLI probe only inspect local files.
COMPOSE_LIST_TIMEOUT = 30

LOGS_POOL_SIZE = 8

# The compose CLI is resolved once per process: ``docker compose`` (plugin)
# first, the legacy standalone ``docker-compose`` binary as a fallback.
_compose_cli: Optional[List[str]] = None
_compose_cli_lock = threading.Lock()

# (host id, compose project) → (working dir, compose files). Remembering where a
# project lives keeps ``up`` possible right after ``down`` removed every
# container of that project.
_locations: Dict[Tuple[str, str], Tuple[str, List[str]]] = {}
_locations_lock = threading.Lock()


# ── CLI resolution ────────────────────────────────────────────────────────────


def _split_config_files(value: Any) -> List[str]:
    """
    Split the ``com.docker.compose.project.config_files`` label.

    Compose stores the list as a comma separated string when more than one file
    was passed with ``-f`` (``docker-compose.yml,override.yml``).

    Example:
        >>> _split_config_files("/srv/app/docker-compose.yml")
        ['/srv/app/docker-compose.yml']
        >>> _split_config_files("")
        []
    """
    return [chunk.strip() for chunk in str(value or "").split(",") if chunk.strip()]


def compose_cli() -> List[str]:
    """
    Return the compose CLI prefix (``["docker", "compose"]`` or the legacy one).

    The probe runs ``<cli> version`` once and the result is cached, so repeated
    stack commands do not pay for it.

    Returns:
        The command prefix to prepend to the compose arguments.

    Raises:
        DockerUnavailable: No compose CLI is installed or it cannot be started.
    """
    global _compose_cli
    if _compose_cli is not None:
        return list(_compose_cli)

    with _compose_cli_lock:
        if _compose_cli is not None:
            return list(_compose_cli)

        for candidate in (["docker", "compose"], ["docker-compose"]):
            if not shutil.which(candidate[0]):
                continue
            try:
                probe = subprocess.run(
                    candidate + ["version"],
                    capture_output=True,
                    text=True,
                    timeout=COMPOSE_LIST_TIMEOUT,
                )
            except (OSError, subprocess.SubprocessError) as ex:
                logger.debug("Compose probe failed for %s: %s", candidate, ex)
                continue
            if probe.returncode == 0:
                _compose_cli = candidate
                logger.info("Using compose CLI: %s", " ".join(candidate))
                return list(candidate)

    raise DockerUnavailable(
        "docker compose is not available on the codx-junior host "
        "(install the compose plugin or the docker-compose binary)"
    )


def _compose_env(manager: Any, host_id: str) -> Dict[str, str]:
    """
    Environment for a compose invocation, pointed at ``host_id``'s daemon.

    A bare socket path (``/var/run/docker.sock``) is normalised to a
    ``unix://`` URI, which is what the CLI expects in ``DOCKER_HOST``.
    """
    endpoint = manager.host_config(host_id).endpoint
    if not endpoint.startswith(("unix://", "tcp://", "http://", "https://")):
        endpoint = "unix://" + endpoint

    env = dict(os.environ)
    env["DOCKER_HOST"] = endpoint
    # No TTY here: plain output and no spinner escape codes in the logs.
    env.setdefault("COMPOSE_ANSI", "never")
    env.setdefault("COMPOSE_PROGRESS", "plain")
    return env


# ── Project location ──────────────────────────────────────────────────────────


def _remember(host_id: str, project: str, workdir: str, files: List[str]) -> None:
    """Cache where a compose project lives (working dir + compose files)."""
    if not project or (not workdir and not files):
        return
    with _locations_lock:
        _locations[(host_id, project)] = (workdir, list(files))


def _project_containers(manager: Any, project: str, host_id: str) -> List[InfraContainer]:
    """Every container of the host that belongs to ``project``."""
    containers = manager.containers(host_id, with_stats=False).containers
    return [item for item in containers if item.stack == project]


def _location_from_containers(
    manager: Any, project: str, host_id: str
) -> Optional[Tuple[str, List[str]]]:
    """Read the compose location from the labels of the project's containers."""
    for container in _project_containers(manager, project, host_id):
        workdir = container.labels.get(COMPOSE_WORKDIR_LABEL) or ""
        files = _split_config_files(container.labels.get(COMPOSE_CONFIG_LABEL))
        if workdir or files:
            return workdir, files
    return None


def _compose_ls(manager: Any, host_id: str) -> List[Dict[str, Any]]:
    """
    ``docker compose ls --all --format json``, or ``[]`` when unavailable.

    Used only to locate a project that currently has no container: an older CLI
    without ``--format json`` or a broken environment must degrade to "unknown
    project", never to a 500.
    """
    command = compose_cli() + ["ls", "--all", "--format", "json"]
    try:
        result = subprocess.run(
            command,
            env=_compose_env(manager, host_id),
            capture_output=True,
            text=True,
            timeout=COMPOSE_LIST_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as ex:
        logger.debug("'docker compose ls' failed: %s", ex)
        return []

    if result.returncode != 0:
        logger.debug("'docker compose ls' exit %s: %s", result.returncode, result.stderr)
        return []

    try:
        entries = json.loads(result.stdout or "[]")
    except ValueError:
        logger.debug("'docker compose ls' returned non-JSON output")
        return []
    return entries if isinstance(entries, list) else []


def _location_from_cli(
    manager: Any, project: str, host_id: str
) -> Optional[Tuple[str, List[str]]]:
    """Locate a project through ``docker compose ls`` (containers already gone)."""
    for entry in _compose_ls(manager, host_id):
        if str((entry or {}).get("Name") or "") != project:
            continue
        workdir = str((entry or {}).get("WorkingDir") or "")
        files = _split_config_files((entry or {}).get("ConfigFiles"))
        if not workdir and files:
            workdir = os.path.dirname(files[0])
        if workdir or files:
            return workdir, files
    return None


def _project_location(
    manager: Any, project: str, host_id: str
) -> Optional[Tuple[str, List[str]]]:
    """
    Resolve the working directory and compose file(s) of a project.

    Order: container labels (authoritative) → in-process cache → compose CLI.

    Returns:
        ``(working_dir, config_files)`` or ``None`` when the project is unknown
        on that host (the caller answers 404).
    """
    found = _location_from_containers(manager, project, host_id)
    if found:
        _remember(host_id, project, found[0], found[1])
        return found

    with _locations_lock:
        cached = _locations.get((host_id, project))
    if cached:
        return cached[0], list(cached[1])

    found = _location_from_cli(manager, project, host_id)
    if found:
        _remember(host_id, project, found[0], found[1])
    return found


# ── Command execution ─────────────────────────────────────────────────────────


def _compose_args(
    project: str, workdir: str, files: List[str], action: str
) -> List[str]:
    """
    Build the arguments that follow the ``docker compose`` prefix.

    ``-p`` pins the project name (a folder can be renamed) and
    ``--project-directory`` preserves the relative paths written inside the
    compose file, so the command behaves exactly like the one that started the
    stack.

    Example:
        >>> _compose_args("app", "/srv/app", ["/srv/app/docker-compose.yml"], "up")
        ['-p', 'app', '--project-directory', '/srv/app', '-f', '/srv/app/docker-compose.yml', 'up', '-d']
    """
    args = ["-p", project]
    if workdir:
        args += ["--project-directory", workdir]
    for config_file in files:
        args += ["-f", config_file]
    return args + COMPOSE_ACTION_ARGS[action]


def _run_compose(
    manager: Any, host_id: str, project: str, action: str, workdir: str, files: List[str]
) -> str:
    """
    Run one compose command against a project and return its stdout.

    Raises:
        DockerAPIError: 504 on timeout, 500/502 when compose reports an error.
        DockerUnavailable: The CLI is missing or cannot be started.
    """
    command = compose_cli() + _compose_args(project, workdir, files, action)
    logger.info(
        "Compose '%s' on %s: %s (cwd=%s)",
        action,
        project,
        " ".join(shlex.quote(part) for part in command),
        workdir or "-",
    )

    try:
        result = subprocess.run(
            command,
            cwd=workdir or None,
            env=_compose_env(manager, host_id),
            capture_output=True,
            text=True,
            timeout=COMPOSE_TIMEOUT,
        )
    except subprocess.TimeoutExpired as ex:
        raise DockerAPIError(
            504,
            f"'docker compose {action}' did not finish within "
            f"{int(COMPOSE_TIMEOUT)} seconds",
            "compose",
        ) from ex
    except OSError as ex:
        raise DockerUnavailable(f"Cannot run docker compose: {ex}") from ex

    if result.returncode != 0:
        output = [
            line.strip()
            for line in (result.stderr or result.stdout or "").splitlines()
            if line.strip()
        ]
        message = "\n".join(output[-5:]) or f"exit code {result.returncode}"
        raise DockerAPIError(500, message[:800], "compose")

    return result.stdout or ""


# ── Public API ────────────────────────────────────────────────────────────────


def find_stack(manager: Any, project: str, host_id: str) -> Optional[InfraStack]:
    """Return ONE stack from the host snapshot, or ``None`` when it is gone."""
    return next(
        (item for item in manager.stacks(host_id).stacks if item.name == project),
        None,
    )


def stack_action(
    manager: Any,
    name: str,
    request: InfraStackActionRequest,
    host_id: Optional[str] = None,
) -> Union[InfraStack, InfraOk]:
    """
    Run ONE ``docker compose`` command against a project.

    The call is synchronous and answers once the command settled, so ``build``
    and ``pull`` may take minutes (``CODX_JUNIOR_COMPOSE_TIMEOUT``, 600s).

    Args:
        manager: The :class:`InfraManager` (engine client + host registry).
        name: Compose project name.
        request: ``action`` + optional ``host_id``.
        host_id: Target host (``request.host_id`` wins when set).

    Returns:
        The refreshed :class:`InfraStack`, or ``InfraOk`` when the project has
        no container left (``down``).

    Raises:
        ValueError: The action is unknown or the name is empty.
        DockerAPIError: 404 when the project is unknown on that host, 500/502
            when compose failed, 504 when it timed out.
        DockerUnavailable: No compose CLI is installed (503).
    """
    project = (name or "").strip()
    if not project:
        raise ValueError("A compose project name is required")

    action = (request.action or "").strip().lower()
    if action not in COMPOSE_ACTIONS:
        raise ValueError(
            f"Unsupported compose action '{request.action}'. "
            f"Allowed: {', '.join(COMPOSE_ACTIONS)}"
        )

    resolved_host = manager.host_config(request.host_id or host_id).id
    location = _project_location(manager, project, resolved_host)
    if not location:
        raise DockerAPIError(
            404,
            f"Compose project '{project}' was not found on host "
            f"'{resolved_host}': no container carries its compose labels and "
            f"'docker compose ls' does not list it",
            "compose",
        )

    workdir, files = location
    _run_compose(manager, resolved_host, project, action, workdir, files)
    logger.info("Compose project %s: '%s' completed on %s", project, action, resolved_host)

    # ``down`` leaves no container behind, so there is no stack to report.
    return find_stack(manager, project, resolved_host) or InfraOk(ok=True)


def _safe_logs(
    manager: Any, container: InfraContainer, tail: int, host_id: str
) -> List[InfraLogLine]:
    """Read one service tail; a single failure must not empty the overlay."""
    try:
        return manager.logs(container.id, tail=tail, host_id=host_id).lines
    except (DockerUnavailable, DockerAPIError) as ex:
        logger.debug("Cannot read logs for %s: %s", container.id, ex)
        return []


def stack_logs(
    manager: Any, name: str, tail: int = 200, host_id: Optional[str] = None
) -> InfraStackLogs:
    """
    Return the aggregated logs of every service of a compose project.

    Each line is prefixed with its service name (what ``docker compose logs``
    prints) and the merged result is sorted by timestamp, so the UI can render
    one chronological stream. ``tail`` applies PER service.

    Args:
        manager: The :class:`InfraManager`.
        name: Compose project name.
        tail: Lines requested from each service (clamped to 1..2000).
        host_id: Target host.

    Raises:
        ValueError: The project name is empty.
        DockerAPIError: 404 when the project has no container on that host.
    """
    project = (name or "").strip()
    if not project:
        raise ValueError("A compose project name is required")

    tail = max(1, min(int(tail or 200), 2000))
    resolved_host = manager.host_config(host_id).id
    containers = _project_containers(manager, project, resolved_host)
    if not containers:
        raise DockerAPIError(
            404,
            f"Compose project '{project}' has no container on host "
            f"'{resolved_host}'",
            "compose",
        )

    # Keep the location fresh: this is the cheapest place to learn it from the
    # labels, and it is what makes a later ``up`` possible right after ``down``.
    _project_location(manager, project, resolved_host)

    with ThreadPoolExecutor(max_workers=LOGS_POOL_SIZE) as pool:
        payloads = list(
            pool.map(lambda item: _safe_logs(manager, item, tail, resolved_host), containers)
        )

    lines: List[InfraLogLine] = []
    for container, container_lines in zip(containers, payloads):
        prefix = container.service or container.name
        for line in container_lines:
            lines.append(
                InfraLogLine(
                    ts=line.ts,
                    level=line.level,
                    msg=f"{prefix} | {line.msg}",
                )
            )

    lines.sort(key=lambda item: item.ts)
    return InfraStackLogs(name=project, lines=lines)

# Made with ❤️ by codx-junior