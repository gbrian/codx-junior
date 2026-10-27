"""
Docker tools for DevOps support in codx-junior.

This module provides safe Docker commands for managing containers, images, and
services within the codx-junior workspace. All operations are restricted to
project-related containers and include comprehensive security safeguards to
prevent system compromise.

Security Features:
    - Command whitelist validation
    - Input sanitization and validation
    - No shell metacharacters allowed in Docker parameters
    - Audit logging for all operations
    - Rate limiting considerations

Execution model:
    - Every command runs with ``cwd`` set to the project directory
      (``settings.abs_project_path``) so ``docker-compose`` resolves the
      project's own compose file instead of the process working directory.
    - The exit code is always inspected: a non-zero exit is reported as a
      failure with the daemon's own output, never as a success.

Tool Scope: "devops" (available to DevOps/admin roles only)

Made with ❤️ by codx-junior
"""

import logging
import os
import re
import shlex
import subprocess
from typing import Optional, List, Dict, Any, NamedTuple
from enum import Enum

from codx.junior.settings import CODXJuniorSettings
from codx.junior.model.model import CodxUser
from .model import ToolResponse, ToolSettings

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DOCKER_UNSAFE_PATTERNS = [
    r'[;&|`$\(\)\{\}\[\]<>\\]',  # Shell metacharacters
    r'--privileged',               # Privilege escalation
    r'--user root',                # Root access
    r'--cap-add',                  # Capability additions
    r'--device',                   # Direct device access
    r'--security-opt',             # Security options
]

# Patterns allowed for command execution (curl, wget, etc with URL parameters)
COMMAND_EXECUTION_ALLOWED_CHARS = [
    r'^[a-zA-Z0-9_\-\.\s/=?&:@%#\[\]]+$'  # Allows URLs, query params, anchors
]

# Compose file names checked, in order, inside the project directory.
COMPOSE_FILE_NAMES = [
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
]

# Optional override so a host with only the compose v2 plugin can run
# ``docker compose`` instead of the legacy ``docker-compose`` binary.
COMPOSE_CMD_ENV = "CODX_JUNIOR_COMPOSE_CMD"

ALLOWED_DOCKER_COMMANDS = {
    'ps': 'List running containers',
    'images': 'List available images',
    'logs': 'View container logs',
    'stats': 'Show live container statistics',
    'inspect': 'Show detailed container/image info',
    'network': 'Manage Docker networks',
    'volume': 'Manage Docker volumes',
}


class DockerCommandResult(NamedTuple):
    """Outcome of a Docker subprocess execution."""

    stdout: str
    stderr: str
    returncode: int

    @property
    def ok(self) -> bool:
        """Return True when the command exited with status 0."""
        return self.returncode == 0


class DockerCommandType(str, Enum):
    """Enumeration of allowed Docker command types."""
    PS = "ps"
    IMAGES = "images"
    LOGS = "logs"
    STATS = "stats"
    INSPECT = "inspect"
    RUN = "run"
    CREATE = "create"
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    COMPOSE_RUN = "compose_run"
    COMPOSE_START = "compose_start"
    COMPOSE_STOP = "compose_stop"
    COMPOSE_RESTART = "compose_restart"
    COMPOSE_BUILD = "compose_build"
    COMPOSE_UP = "compose_up"


def _validate_input(value: str, field_name: str = "input", allow_patterns: Optional[List[str]] = None) -> bool:
    """
    Validate input to prevent command injection.

    Args:
        value: The value to validate.
        field_name: Name of the field being validated (for logging).
        allow_patterns: Optional list of regex patterns that are allowed.

    Returns:
        bool: True if valid, False otherwise.

    Raises:
        ValueError: If input contains unsafe patterns.
    """
    if not isinstance(value, str):
        logger.warning("Invalid input type for %s: expected str, got %s", field_name, type(value).__name__)
        raise ValueError(f"{field_name} must be a string")

    if not value or len(value) > 500:
        logger.warning("Invalid input length for %s: length=%d", field_name, len(value) if value else 0)
        raise ValueError(f"{field_name} must be 1-500 characters")

    # Check for unsafe patterns only in Docker-specific contexts
    for pattern in DOCKER_UNSAFE_PATTERNS:
        if re.search(pattern, value):
            logger.warning("Unsafe pattern detected in %s: pattern=%s, value=%s", field_name, pattern, value)
            raise ValueError(f"{field_name} contains unsafe characters")

    # Validate against allowed patterns if specified
    if allow_patterns:
        if not any(re.match(p, value) for p in allow_patterns):
            logger.warning("Input %s does not match allowed patterns: value=%s", field_name, value)
            raise ValueError(f"{field_name} does not match allowed format")

    return True


def _project_cwd(settings: Optional[CODXJuniorSettings]) -> Optional[str]:
    """
    Resolve the directory a Docker/Compose command must run from.

    Compose resolves its configuration file from the current working directory,
    so every command needs the project directory as ``cwd``. ``abs_project_path``
    is preferred because it is always absolute.

    Args:
        settings: Project settings (may be ``None``).

    Returns:
        The project directory, or ``None`` when it cannot be resolved.
    """
    if not settings:
        return None
    for attr in ("abs_project_path", "project_path"):
        value = getattr(settings, attr, None)
        if value:
            return value
    return None


def _find_compose_file(project_dir: Optional[str]) -> Optional[str]:
    """Return the compose file path inside ``project_dir`` (or ``None``)."""
    if not project_dir:
        return None
    for name in COMPOSE_FILE_NAMES:
        candidate = os.path.join(project_dir, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def _compose_context(
    settings: Optional[CODXJuniorSettings], tool_name: str
) -> "tuple[Optional[str], Optional[str], Optional[str]]":
    """
    Resolve the project directory and compose file for a compose command.

    Args:
        settings: Project settings.
        tool_name: Calling tool name (used in error messages).

    Returns:
        Tuple ``(project_dir, compose_file, error)``. ``error`` is ``None`` on
        success, otherwise a human-readable message explaining the failure.
    """
    project_dir = _project_cwd(settings)
    if not project_dir or not os.path.isdir(project_dir):
        return project_dir, None, (
            f"{tool_name}: no valid project directory (got {project_dir!r}). "
            "The Docker command must run from the project root."
        )
    compose_file = _find_compose_file(project_dir)
    if not compose_file:
        return project_dir, None, (
            f"{tool_name}: no compose file found in {project_dir}. "
            f"Expected one of: {', '.join(COMPOSE_FILE_NAMES)}."
        )
    return project_dir, compose_file, None


def _compose_base() -> List[str]:
    """Return the base command for compose invocations."""
    override = os.environ.get(COMPOSE_CMD_ENV)
    if override:
        return shlex.split(override)
    return ["docker-compose"]


def _safe_exec_docker(command: List[str], timeout: int = 30, cwd: Optional[str] = None) -> DockerCommandResult:
    """
    Safely execute a Docker command using subprocess.

    Args:
        command: List of command arguments (no shell interpretation).
        timeout: Command timeout in seconds (default: 30).
        cwd: Working directory for the command. Compose needs the project root.

    Returns:
        DockerCommandResult: Captured stdout, stderr and exit code. Inspect
        ``result.ok`` (returncode == 0) to distinguish success from failure.

    Raises:
        RuntimeError: If the command times out or cannot be executed.
    """
    try:
        logger.debug("Executing Docker command: %s (cwd=%s)", " ".join(command), cwd)
        result = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False  # Don't raise on non-zero exit
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        if result.returncode != 0:
            logger.warning(
                "Docker command failed with exit code %d: %s\nstderr: %s",
                result.returncode, " ".join(command), stderr
            )
        else:
            logger.debug("Docker command succeeded: %s", " ".join(command))
        return DockerCommandResult(stdout=stdout, stderr=stderr, returncode=result.returncode)

    except subprocess.TimeoutExpired as e:
        logger.error("Docker command timeout: %s", " ".join(command))
        raise RuntimeError(f"Command timed out after {timeout}s") from e
    except FileNotFoundError as e:
        binary = command[0] if command else "docker"
        logger.error("Docker command not found: %s", binary)
        raise RuntimeError(f"Docker command not found: {binary}") from e
    except Exception as e:
        error_msg = str(e)
        logger.error("Error executing Docker command: %s", error_msg)
        raise RuntimeError(f"Failed to execute Docker command: {error_msg}") from e


def _format_command_feedback(operation: str, output: str, empty_text: str = "_(no output)_") -> str:
    """
    Build user-facing feedback that always shows the executed Docker operation
    together with its output, so the chat never displays an empty result.

    Args:
        operation: Human-readable description of the Docker command executed
                   (e.g. "docker-compose run --rm api").
        output: Captured command output (stdout). May be empty.
        empty_text: Placeholder shown when there is no output.

    Returns:
        str: Markdown block using the format::

            > Running: `<operation>`
            Output:

            <output or empty_text>
    """
    output = (output or "").strip()
    if not output:
        output = empty_text
    return f"> Running: `{operation}`\nOutput:\n\n{output}"


def _command_failure(operation: str, result: DockerCommandResult) -> str:
    """
    Build a failure block showing the command, both streams and exit code.

    Args:
        operation: Human-readable command string that was executed.
        result: The failed command result.

    Returns:
        str: Markdown block with the command, exit code and any captured output.
    """
    parts = [f"> Running: `{operation}`", f"Exit code: {result.returncode}"]
    if result.stderr.strip():
        parts.append(f"stderr:\n{result.stderr.strip()}")
    if result.stdout.strip():
        parts.append(f"stdout:\n{result.stdout.strip()}")
    return "\n\n".join(parts)


def _create_or_run_container(
    mode: str,
    image: str,
    container_name: str,
    detach: bool,
    port_mapping: Optional[str],
    env_vars: Optional[Dict[str, str]],
    settings: CODXJuniorSettings,
    user: Optional[CodxUser],
) -> ToolResponse:
    """
    Shared implementation for ``docker run`` and ``docker create``.

    Args:
        mode: Either ``"run"`` or ``"create"``.
        image: Docker image name/ID.
        container_name: Name for the container.
        detach: Run in background (only meaningful for ``run``).
        port_mapping: Optional ``host:container`` port mapping.
        env_vars: Optional environment variables.
        settings: Project settings.
        user: Current user (audit logging).

    Returns:
        ToolResponse: Container creation/start result.
    """
    _validate_input(container_name, "container_name", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])
    _validate_input(image, "image", allow_patterns=[r"^[a-zA-Z0-9_\-\.:/@]+$"])
    project_dir = _project_cwd(settings)

    command = ["docker", mode]
    if mode == "run":
        command.append("-d" if detach else "-it")
    command.extend(["--name", container_name])

    if port_mapping:
        _validate_input(port_mapping, "port_mapping", allow_patterns=[r"^\d+:\d+$"])
        command.extend(["-p", port_mapping])

    for key, value in (env_vars or {}).items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("Environment variables must be strings")
        _validate_input(key, f"env_var_key_{key}")
        _validate_input(value, f"env_var_value_{key}")
        command.extend(["-e", f"{key}={value}"])

    command.append(image)
    operation = " ".join(command)

    result = _safe_exec_docker(command, timeout=120, cwd=project_dir)

    if not result.ok:
        logger.error(
            "Docker %s failed for user %s: %s",
            mode, user.username if user else "unknown", result.stderr
        )
        return ToolResponse(
            user_response=f"❌ Failed to {mode} container `{container_name}`\n\n"
                          f"{_command_failure(operation, result)}",
            llm_response=(
                f"`{operation}` failed with exit code {result.returncode}.\n"
                f"stderr: {result.stderr.strip()}\nstdout: {result.stdout.strip()}"
            )
        )

    container_id = "unknown"
    if result.stdout.strip():
        container_id = result.stdout.strip().splitlines()[0][:12]

    verb = "created" if mode == "create" else "started"
    logger.info(
        "Docker %s container %s (image=%s) for user %s",
        mode, container_name, image, user.username if user else "unknown"
    )

    return ToolResponse(
        user_response=_format_command_feedback(
            operation,
            f"Container `{container_name}` {verb} successfully (ID: `{container_id}`)"
        ),
        llm_response=(
            f"Successfully {verb} container {container_name} from image {image} "
            f"(ID: {container_id})."
        )
    )


def docker_ps(filters: Optional[str] = None, **kwargs) -> ToolResponse:
    """
    List Docker containers.

    Lists all running and stopped containers, optionally filtered by status or labels.
    Includes the image, status/health, ports and the compose project/service labels
    so a compose stack can be verified without follow-up ``inspect`` calls.

    Args:
        filters: Optional Docker filter (e.g., "status=running", "label=project=myapp").
                 Must not contain unsafe characters.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Container listing with detailed information.

    Raises:
        ValueError: If filters contain unsafe input.
        RuntimeError: If Docker command fails.

    Example:
        >>> docker_ps(filters="status=running")
        # Lists all running containers
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        ps_format = "\t".join([
            "{{.ID}}",
            "{{.Names}}",
            "{{.Image}}",
            "{{.Status}}",
            "{{.Ports}}",
            '{{.Label "com.docker.compose.project"}}',
            '{{.Label "com.docker.compose.service"}}',
        ])
        command = ["docker", "ps", "-a", "--format", ps_format]

        if filters:
            _validate_input(filters, "filters", allow_patterns=[r"^[a-zA-Z0-9_\-\.=]+$"])
            command.extend(["--filter", filters])

        operation = " ".join(command)
        result = _safe_exec_docker(command, cwd=_project_cwd(settings))

        if not result.ok:
            logger.error("Docker ps error for user %s: %s", user.username if user else "unknown", result.stderr)
            return ToolResponse(
                user_response=f"❌ Failed to list containers\n\n{_command_failure(operation, result)}",
                llm_response=f"Error listing containers (exit {result.returncode}): {result.stderr.strip()}"
            )

        if not result.stdout.strip():
            return ToolResponse(
                user_response="✓ No containers found",
                llm_response="No containers currently running"
            )

        # Parse and format output
        lines = [line for line in result.stdout.strip().split('\n') if line.strip()]
        formatted_lines = [
            "**Container ID** | **Name** | **Image** | **Status** | **Ports** | "
            "**Compose Project** | **Compose Service**"
        ]
        formatted_lines.append("---|---|---|---|---|---|---")
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 3:
                container_id = parts[0]
                container_name = parts[1]
                image = parts[2] if len(parts) > 2 else "-"
                status = parts[3] if len(parts) > 3 else "unknown"
                ports = parts[4] if len(parts) > 4 and parts[4] else "-"
                project = parts[5] if len(parts) > 5 and parts[5] else "-"
                service = parts[6] if len(parts) > 6 and parts[6] else "-"
                formatted_lines.append(
                    f"`{container_id[:12]}` | `{container_name}` | `{image}` | {status} | "
                    f"{ports} | {project} | {service}"
                )

        logger.info("Listed %d containers for user %s", len(lines), user.username if user else "unknown")

        user_response = _format_command_feedback(operation, "\n".join(formatted_lines))
        # llm_response is the ONLY content the model receives (user_response is
        # shown in the chat but not sent to the model). Include the real data and
        # echo the exact command so filtered listings are not mislabeled.
        llm_response = (
            f"Found {len(lines)} container(s). Command: `{operation}`\n"
            f"Raw output (ID\tName\tImage\tStatus\tPorts\tProject\tService):\n"
            f"{result.stdout.strip()}"
        )
        return ToolResponse(
            user_response=user_response,
            llm_response=llm_response
        )

    except Exception as e:
        logger.exception("Error in docker_ps: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to list containers: {str(e)}"
        )


def docker_logs(container_name: str, tail: int = 100, **kwargs) -> ToolResponse:
    """
    Retrieve Docker container logs.

    Fetches the last N lines of logs from a container.

    Args:
        container_name: Name or ID of the container.
        tail: Number of log lines to retrieve (1-1000, default: 100).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Container logs formatted for display.

    Raises:
        ValueError: If container_name or tail contain invalid input.
        RuntimeError: If Docker command fails.

    Example:
        >>> docker_logs("myapp_container", tail=50)
        # Shows last 50 lines of container logs
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        # Validate inputs
        _validate_input(container_name, "container_name", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        if not isinstance(tail, int) or tail < 1 or tail > 1000:
            raise ValueError("tail must be integer between 1-1000")

        command = ["docker", "logs", "--tail", str(tail), container_name]
        operation = " ".join(command)
        result = _safe_exec_docker(command, timeout=10, cwd=_project_cwd(settings))

        if not result.ok:
            logger.error("Docker logs error for container %s: %s", container_name, result.stderr)
            return ToolResponse(
                user_response=f"❌ Failed to retrieve logs\n\n{_command_failure(operation, result)}",
                llm_response=(
                    f"Error retrieving logs for {container_name} "
                    f"(exit {result.returncode}): {result.stderr.strip()}"
                )
            )

        # docker logs sends the container's stderr stream to our stderr, so a
        # successful command may still carry content there. Include both.
        output = (result.stdout or "") + (result.stderr or "")
        if not output.strip():
            return ToolResponse(
                user_response=f"✓ No logs available for `{container_name}`",
                llm_response="Container has no log entries"
            )

        logger.info("Retrieved logs for container %s (tail=%d) by user %s",
                   container_name, tail, user.username if user else "unknown")

        user_response = _format_command_feedback(operation, output)
        # Provide the actual log content to the model (not just a summary).
        llm_response = (
            f"Logs for container '{container_name}' (last {tail} lines):\n{output}"
        )
        return ToolResponse(
            user_response=user_response,
            llm_response=llm_response
        )

    except Exception as e:
        logger.exception("Error in docker_logs: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to retrieve logs: {str(e)}"
        )


def docker_stats(container_name: Optional[str] = None, **kwargs) -> ToolResponse:
    """
    Show Docker container resource statistics.

    Displays CPU, memory, network I/O, and block I/O statistics for one or all containers.
    Useful for performance monitoring and debugging.

    Args:
        container_name: Optional specific container name. If not provided, shows all containers.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Container statistics formatted for display.

    Raises:
        ValueError: If container_name contains invalid input.
        RuntimeError: If Docker command fails.

    Example:
        >>> docker_stats()
        # Shows stats for all containers
        >>> docker_stats("myapp_container")
        # Shows stats for specific container
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        if container_name:
            _validate_input(container_name, "container_name", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])
            command = ["docker", "stats", "--no-stream", container_name]
        else:
            command = ["docker", "stats", "--no-stream"]

        operation = " ".join(command)
        result = _safe_exec_docker(command, timeout=15, cwd=_project_cwd(settings))

        if not result.ok:
            return ToolResponse(
                user_response=f"❌ Failed to retrieve statistics\n\n{_command_failure(operation, result)}",
                llm_response=f"Error retrieving container stats (exit {result.returncode}): {result.stderr.strip()}"
            )

        if not result.stdout.strip():
            return ToolResponse(
                user_response="✓ No statistics available",
                llm_response="No running containers to show statistics for"
            )

        logger.info("Retrieved stats for %s by user %s",
                   container_name or "all containers", user.username if user else "unknown")

        user_response = _format_command_feedback(operation, result.stdout)
        # Provide the actual statistics to the model (not just a summary).
        llm_response = (
            f"Container statistics for {container_name or 'all containers'}:\n{result.stdout}"
        )
        return ToolResponse(
            user_response=user_response,
            llm_response=llm_response
        )

    except Exception as e:
        logger.exception("Error in docker_stats: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to retrieve statistics: {str(e)}"
        )


def docker_inspect(container_name: str, inspect_type: str = "container", **kwargs) -> ToolResponse:
    """
    Show detailed information about a Docker container or image.

    Provides comprehensive details including configuration, networking, volumes,
    and environment variables.

    Args:
        container_name: Name or ID of the container/image.
        inspect_type: Type to inspect - "container" or "image" (default: "container").
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Detailed information in JSON format.

    Raises:
        ValueError: If inputs contain invalid values.
        RuntimeError: If Docker command fails.

    Example:
        >>> docker_inspect("myapp_container")
        # Shows detailed container info
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        _validate_input(container_name, "container_name", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        if inspect_type not in ["container", "image"]:
            raise ValueError("inspect_type must be 'container' or 'image'")

        command = ["docker", "inspect", container_name]
        operation = " ".join(command)
        result = _safe_exec_docker(command, timeout=10, cwd=_project_cwd(settings))

        if not result.ok:
            return ToolResponse(
                user_response=f"❌ Failed to inspect {container_name}\n\n{_command_failure(operation, result)}",
                llm_response=f"Error inspecting {container_name}: {result.stderr.strip()}"
            )

        logger.info("Inspected %s %s by user %s", inspect_type, container_name,
                   user.username if user else "unknown")

        user_response = _format_command_feedback(operation, result.stdout)
        # Provide the actual inspect JSON to the model (not just a summary).
        llm_response = (
            f"Inspect output for {inspect_type} '{container_name}':\n{result.stdout}"
        )
        return ToolResponse(
            user_response=user_response,
            llm_response=llm_response
        )

    except Exception as e:
        logger.exception("Error in docker_inspect: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to inspect container: {str(e)}"
        )


def docker_images(**kwargs) -> ToolResponse:
    """
    List available Docker images.

    Shows all locally available Docker images with repository, tag, ID, size,
    and creation date. Useful for managing project dependencies.

    Args:
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Image listing with detailed information.

    Example:
        >>> docker_images()
        # Lists all available Docker images
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        command = ["docker", "images", "--format", "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedAt}}"]
        operation = " ".join(command)
        result = _safe_exec_docker(command, cwd=_project_cwd(settings))

        if not result.ok:
            return ToolResponse(
                user_response=f"❌ Failed to list images\n\n{_command_failure(operation, result)}",
                llm_response=f"Error listing Docker images (exit {result.returncode}): {result.stderr.strip()}"
            )

        if not result.stdout.strip():
            return ToolResponse(
                user_response="✓ No Docker images found",
                llm_response="No Docker images available"
            )

        lines = result.stdout.strip().split('\n')
        formatted_lines = ["**Repository** | **Tag** | **ID** | **Size** | **Created**"]
        formatted_lines.append("---|---|---|---|---")

        for line in lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 5:
                    formatted_lines.append(
                        f"`{parts[0]}` | `{parts[1]}` | `{parts[2][:12]}` | {parts[3]} | {parts[4]}"
                    )

        logger.info("Listed Docker images for user %s: %d images", user.username if user else "unknown", len(lines))

        user_response = _format_command_feedback(operation, "\n".join(formatted_lines))
        # Provide the actual image list to the model (not just a summary).
        llm_response = (
            f"Found {len(lines)} Docker image(s). Raw `docker images` output "
            f"(Repository\tTag\tID\tSize\tCreatedAt):\n{result.stdout.strip()}"
        )
        return ToolResponse(
            user_response=user_response,
            llm_response=llm_response
        )

    except Exception as e:
        logger.exception("Error in docker_images: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to list images: {str(e)}"
        )


def docker_run(image: str, container_name: str, **kwargs) -> ToolResponse:
    """
    Run a Docker container from an image.

    Creates and starts a new container with specified configuration and security
    constraints. ``docker run`` pulls the image automatically when it is not cached
    locally, so it can also be used to obtain an image.

    Args:
        image: Docker image name/ID to run.
        container_name: Name for the new container.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).
            - detach (bool): Run in background (default: True).
            - port_mapping (str): Port mapping (e.g., "8080:80").
            - env_vars (dict): Environment variables.

    Returns:
        ToolResponse: Container creation confirmation with container ID.

    Raises:
        ValueError: If inputs contain invalid values or unsafe patterns.
        RuntimeError: If Docker command fails.

    Example:
        >>> docker_run("nginx:latest", "myapp_web_1", port_mapping="8080:80")
        # Runs nginx container
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")
    detach = kwargs.get("detach", True)
    port_mapping = kwargs.get("port_mapping")
    env_vars = kwargs.get("env_vars", {})

    if not settings:
        raise Exception("Invalid project settings")

    try:
        return _create_or_run_container(
            "run", image, container_name, detach, port_mapping, env_vars, settings, user
        )
    except Exception as e:
        logger.exception("Error in docker_run: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to run container: {str(e)}"
        )


def docker_create(image: str, container_name: str, **kwargs) -> ToolResponse:
    """
    Create a Docker container from an image without starting it.

    Wraps ``docker create`` with the same validation constraints as
    :func:`docker_run`. Use it when a container must be created first and
    started later with :func:`docker_start`.

    Args:
        image: Docker image name/ID to create the container from.
        container_name: Name for the new container.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).
            - port_mapping (str): Port mapping (e.g., "8080:80").
            - env_vars (dict): Environment variables.

    Returns:
        ToolResponse: Container creation confirmation with container ID.

    Rapresents:
        ValueError: If inputs contain invalid values or unsafe patterns.
        RuntimeError: If Docker command fails.

    Example:
        >>> docker_create("nginx:latest", "myapp_web_1", port_mapping="8080:80")
        # Creates nginx container (not started)
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")
    port_mapping = kwargs.get("port_mapping")
    env_vars = kwargs.get("env_vars", {})

    if not settings:
        raise Exception("Invalid project settings")

    try:
        return _create_or_run_container(
            "create", image, container_name, False, port_mapping, env_vars, settings, user
        )
    except Exception as e:
        logger.exception("Error in docker_create: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to create container: {str(e)}"
        )


def docker_start(container_name: str, **kwargs) -> ToolResponse:
    """
    Start a stopped Docker container.

    Starts a previously stopped container by name.

    Args:
        container_name: Name of the container to start.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Confirmation of container start.

    Raises:
        ValueError: If container_name contains invalid input.
        RuntimeError: If Docker command fails.

    Example:
        >>> docker_start("myapp_container")
        # Starts the container
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        _validate_input(container_name, "container_name", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        command = ["docker", "start", container_name]
        operation = " ".join(command)
        result = _safe_exec_docker(command, timeout=15, cwd=_project_cwd(settings))

        if not result.ok:
            logger.error("Docker start error for container %s: %s", container_name, result.stderr)
            return ToolResponse(
                user_response=f"❌ Failed to start container\n\n{_command_failure(operation, result)}",
                llm_response=f"Error starting container {container_name}: {result.stderr.strip()}"
            )

        logger.info("Started container %s by user %s", container_name, user.username if user else "unknown")

        user_response = _format_command_feedback(operation, result.stdout)
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Successfully started container {container_name}"
        )

    except Exception as e:
        logger.exception("Error in docker_start: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to start container: {str(e)}"
        )


def docker_stop(container_name: str, timeout: int = 10, **kwargs) -> ToolResponse:
    """
    Stop a running Docker container.

    Gracefully stops a container with optional timeout.

    Args:
        container_name: Name of the container to stop.
        timeout: Timeout in seconds before force kill (default: 10).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Confirmation of container stop.

    Raises:
        ValueError: If container_name contains invalid input.
        RuntimeError: If Docker command fails.

    Example:
        >>> docker_stop("myapp_container", timeout=5)
        # Stops the container with 5 second timeout
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        _validate_input(container_name, "container_name", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        if not isinstance(timeout, int) or timeout < 1 or timeout > 120:
            raise ValueError("timeout must be integer between 1-120 seconds")

        command = ["docker", "stop", "-t", str(timeout), container_name]
        operation = " ".join(command)
        result = _safe_exec_docker(command, timeout=timeout + 10, cwd=_project_cwd(settings))

        if not result.ok:
            logger.error("Docker stop error for container %s: %s", container_name, result.stderr)
            return ToolResponse(
                user_response=f"❌ Failed to stop container\n\n{_command_failure(operation, result)}",
                llm_response=f"Error stopping container {container_name}: {result.stderr.strip()}"
            )

        logger.info("Stopped container %s by user %s", container_name, user.username if user else "unknown")

        user_response = _format_command_feedback(operation, result.stdout)
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Successfully stopped container {container_name}"
        )

    except Exception as e:
        logger.exception("Error in docker_stop: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to stop container: {str(e)}"
        )


def docker_restart(container_name: str, timeout: int = 10, **kwargs) -> ToolResponse:
    """
    Restart a Docker container.

    Stops and starts a container in one operation.

    Args:
        container_name: Name of the container to restart.
        timeout: Timeout in seconds for stopping before restart (default: 10).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Confirmation of container restart.

    Raises:
        ValueError: If container_name contains invalid input.
        RuntimeError: If Docker command fails.

    Example:
        >>> docker_restart("myapp_container")
        # Restarts the container
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        _validate_input(container_name, "container_name", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        if not isinstance(timeout, int) or timeout < 1 or timeout > 120:
            raise ValueError("timeout must be integer between 1-120 seconds")

        command = ["docker", "restart", "-t", str(timeout), container_name]
        operation = " ".join(command)
        result = _safe_exec_docker(command, timeout=timeout + 15, cwd=_project_cwd(settings))

        if not result.ok:
            logger.error("Docker restart error for container %s: %s", container_name, result.stderr)
            return ToolResponse(
                user_response=f"❌ Failed to restart container\n\n{_command_failure(operation, result)}",
                llm_response=f"Error restarting container {container_name}: {result.stderr.strip()}"
            )

        logger.info("Restarted container %s by user %s", container_name, user.username if user else "unknown")

        user_response = _format_command_feedback(operation, result.stdout)
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Successfully restarted container {container_name}"
        )

    except Exception as e:
        logger.exception("Error in docker_restart: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to restart container: {str(e)}"
        )


def docker_compose_run(service: str, command: Optional[str] = None, **kwargs) -> ToolResponse:
    """
    Run a one-off command in a docker-compose service.

    Executes a command in a service defined in the project's compose file. The
    command string is split into arguments (no shell interpretation) and the
    command runs from the project directory, using the project's compose file.

    Args:
        service: Service name in the compose file.
        command: Optional command to execute in the service (e.g. "curl http://domain.com/path?param=value").
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).
            - no_deps (bool): Do not start linked services (default: False).

    Returns:
        ToolResponse: Command execution result.

    Raises:
        ValueError: If inputs contain invalid values.
        RuntimeError: If Docker Compose command fails.

    Example:
        >>> docker_compose_run("web", "python manage.py migrate")
        # Runs migration in web service
        >>> docker_compose_run("web", "curl http://domain.com/api?key=12345")
        # Executes curl with URL parameters
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")
    no_deps = kwargs.get("no_deps", False)

    if not settings:
        raise Exception("Invalid project settings")

    try:
        project_dir, compose_file, error = _compose_context(settings, "docker_compose_run")
        if error:
            return ToolResponse(user_response=f"❌ {error}", llm_response=error)

        _validate_input(service, "service", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])
        if command:
            _validate_input(command, "command", allow_patterns=COMMAND_EXECUTION_ALLOWED_CHARS)

        compose_command = _compose_base() + ["-f", compose_file, "run", "--rm"]
        if no_deps:
            compose_command.append("--no-deps")
        compose_command.append(service)
        if command:
            compose_command.extend(shlex.split(command))

        operation = " ".join(compose_command)
        result = _safe_exec_docker(compose_command, timeout=60, cwd=project_dir)

        if not result.ok:
            logger.error("Docker Compose run error for service %s: %s", service, result.stderr)
            return ToolResponse(
                user_response=f"❌ Failed to run service `{service}`\n\n{_command_failure(operation, result)}",
                llm_response=f"Error running compose service {service}: {result.stderr.strip()}"
            )

        logger.info("Executed compose run on service %s by user %s", service,
                   user.username if user else "unknown")

        # Always show the executed command and its output (placeholder when empty),
        # so the user never sees an empty result.
        user_response = _format_command_feedback(operation, result.stdout)
        # Provide the command output to the model (not just a status summary).
        llm_response = (
            f"Command executed on '{service}' service"
            + (f" (command: {command})" if command else "")
            + f". Output:\n{result.stdout}"
        )
        return ToolResponse(
            user_response=user_response,
            llm_response=llm_response
        )

    except Exception as e:
        logger.exception("Error in docker_compose_run: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to run compose service: {str(e)}"
        )


def docker_compose_start(service: Optional[str] = None, **kwargs) -> ToolResponse:
    """
    Start docker-compose services.

    Starts one or all services defined in the project's compose file. Note that
    ``docker-compose start`` only starts containers that already exist; use
    :func:`docker_compose_up` for a first creation/build.

    Args:
        service: Optional specific service name. If not provided, starts all services.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Confirmation of services started.

    Raises:
        ValueError: If service name contains invalid input.
        RuntimeError: If Docker Compose command fails.

    Example:
        >>> docker_compose_start("web")
        # Starts web service
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        project_dir, compose_file, error = _compose_context(settings, "docker_compose_start")
        if error:
            return ToolResponse(user_response=f"❌ {error}", llm_response=error)

        if service:
            _validate_input(service, "service", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        command = _compose_base() + ["-f", compose_file, "start"]
        if service:
            command.append(service)

        operation = " ".join(command)
        result = _safe_exec_docker(command, timeout=30, cwd=project_dir)

        if not result.ok:
            logger.error("Docker Compose start error: %s", result.stderr)
            return ToolResponse(
                user_response=f"❌ Failed to start services\n\n{_command_failure(operation, result)}",
                llm_response=f"Error starting compose services: {result.stderr.strip()}"
            )

        logger.info("Started compose %s by user %s", service or "all services",
                   user.username if user else "unknown")

        target = f"`{service}`" if service else "all services"
        user_response = _format_command_feedback(operation, result.stdout)
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Successfully started compose {target}"
        )

    except Exception as e:
        logger.exception("Error in docker_compose_start: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to start compose services: {str(e)}"
        )


def docker_compose_stop(service: Optional[str] = None, timeout: int = 10, **kwargs) -> ToolResponse:
    """
    Stop docker-compose services.

    Stops one or all services defined in the project's compose file.

    Args:
        service: Optional specific service name. If not provided, stops all services.
        timeout: Timeout in seconds before force stop (default: 10).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Confirmation of services stopped.

    Raises:
        ValueError: If inputs contain invalid values.
        RuntimeError: If Docker Compose command fails.

    Example:
        >>> docker_compose_stop("web", timeout=5)
        # Stops web service with 5 second timeout
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        project_dir, compose_file, error = _compose_context(settings, "docker_compose_stop")
        if error:
            return ToolResponse(user_response=f"❌ {error}", llm_response=error)

        if service:
            _validate_input(service, "service", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        if not isinstance(timeout, int) or timeout < 1 or timeout > 120:
            raise ValueError("timeout must be integer between 1-120 seconds")

        command = _compose_base() + ["-f", compose_file, "stop", "-t", str(timeout)]
        if service:
            command.append(service)

        operation = " ".join(command)
        result = _safe_exec_docker(command, timeout=timeout + 15, cwd=project_dir)

        if not result.ok:
            logger.error("Docker Compose stop error: %s", result.stderr)
            return ToolResponse(
                user_response=f"❌ Failed to stop services\n\n{_command_failure(operation, result)}",
                llm_response=f"Error stopping compose services: {result.stderr.strip()}"
            )

        logger.info("Stopped compose %s by user %s", service or "all services",
                   user.username if user else "unknown")

        target = f"`{service}`" if service else "all services"
        user_response = _format_command_feedback(operation, result.stdout)
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Successfully stopped compose {target}"
        )

    except Exception as e:
        logger.exception("Error in docker_compose_stop: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to stop compose services: {str(e)}"
        )


def docker_compose_restart(service: Optional[str] = None, timeout: int = 10, **kwargs) -> ToolResponse:
    """
    Restart docker-compose services.

    Stops and starts one or all services defined in the project's compose file.

    Args:
        service: Optional specific service name. If not provided, restarts all services.
        timeout: Timeout in seconds for stopping before restart (default: 10).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Confirmation of services restarted.

    Raises:
        ValueError: If inputs contain invalid values.
        RuntimeError: If Docker Compose command fails.

    Example:
        >>> docker_compose_restart("web")
        # Restarts web service
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        project_dir, compose_file, error = _compose_context(settings, "docker_compose_restart")
        if error:
            return ToolResponse(user_response=f"❌ {error}", llm_response=error)

        if service:
            _validate_input(service, "service", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        if not isinstance(timeout, int) or timeout < 1 or timeout > 120:
            raise ValueError("timeout must be integer between 1-120 seconds")

        command = _compose_base() + ["-f", compose_file, "restart", "-t", str(timeout)]
        if service:
            command.append(service)

        operation = " ".join(command)
        result = _safe_exec_docker(command, timeout=timeout + 20, cwd=project_dir)

        if not result.ok:
            logger.error("Docker Compose restart error: %s", result.stderr)
            return ToolResponse(
                user_response=f"❌ Failed to restart services\n\n{_command_failure(operation, result)}",
                llm_response=f"Error restarting compose services: {result.stderr.strip()}"
            )

        logger.info("Restarted compose %s by user %s", service or "all services",
                   user.username if user else "unknown")

        target = f"`{service}`" if service else "all services"
        user_response = _format_command_feedback(operation, result.stdout)
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Successfully restarted compose {target}"
        )

    except Exception as e:
        logger.exception("Error in docker_compose_restart: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to restart compose services: {str(e)}"
        )


def docker_compose_build(service: Optional[str] = None, **kwargs) -> ToolResponse:
    """
    Build docker-compose service images.

    Runs ``docker-compose build`` in the project directory, so a freshly created
    project gets its images built (something ``docker-compose start`` can never
    do). Base images are pulled automatically when missing.

    Args:
        service: Optional specific service name. If not provided, builds all services.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Build result with command output.

    Raises:
        ValueError: If service name contains invalid input.
        RuntimeError: If Docker Compose command fails.

    Example:
        >>> docker_compose_build()
        # Builds every service image
        >>> docker_compose_build("web")
        # Builds the web service image
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        project_dir, compose_file, error = _compose_context(settings, "docker_compose_build")
        if error:
            return ToolResponse(user_response=f"❌ {error}", llm_response=error)

        if service:
            _validate_input(service, "service", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        command = _compose_base() + ["-f", compose_file, "build"]
        if service:
            command.append(service)

        operation = " ".join(command)
        result = _safe_exec_docker(command, timeout=900, cwd=project_dir)

        if not result.ok:
            logger.error("Docker Compose build error: %s", result.stderr)
            return ToolResponse(
                user_response=f"❌ Build failed\n\n{_command_failure(operation, result)}",
                llm_response=(
                    f"`{operation}` failed with exit code {result.returncode}.\n"
                    f"stderr:\n{result.stderr.strip()}\nstdout:\n{result.stdout.strip()}"
                )
            )

        logger.info("Built compose %s by user %s", service or "all services",
                   user.username if user else "unknown")

        target = f"`{service}`" if service else "all services"
        return ToolResponse(
            user_response=_format_command_feedback(operation, result.stdout),
            llm_response=f"Successfully built compose {target}.\nOutput:\n{result.stdout}"
        )

    except Exception as e:
        logger.exception("Error in docker_compose_build: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to build compose services: {str(e)}"
        )


def docker_compose_up(
    service: Optional[str] = None,
    build: bool = True,
    detach: bool = True,
    remove_orphans: bool = True,
    **kwargs,
) -> ToolResponse:
    """
    Create and start docker-compose services.

    Runs ``docker-compose up`` in the project directory and, by default, rebuilds
    images first (``--build``) and runs detached (``-d``). This is the intended
    entry point for launching a freshly created project, since it both builds and
    creates the containers.

    Args:
        service: Optional specific service name. If not provided, starts all services.
        build: Rebuild images before starting (default: True).
        detach: Run containers in the background (default: True).
        remove_orphans: Remove containers for services no longer defined
                        (default: True).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

    Returns:
        ToolResponse: Up result with command output.

    Raises:
        ValueError: If service name contains invalid input.
        RuntimeError: If Docker Compose command fails.

    Example:
        >>> docker_compose_up()
        # Builds and starts every service in the background
        >>> docker_compose_up("web", build=False)
        # Starts the web service using the existing image
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    user: CodxUser = kwargs.get("user")

    if not settings:
        raise Exception("Invalid project settings")

    try:
        project_dir, compose_file, error = _compose_context(settings, "docker_compose_up")
        if error:
            return ToolResponse(user_response=f"❌ {error}", llm_response=error)

        if service:
            _validate_input(service, "service", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        command = _compose_base() + ["-f", compose_file, "up"]
        if detach:
            command.append("-d")
        if build:
            command.append("--build")
        if remove_orphans:
            command.append("--remove-orphans")
        if service:
            command.append(service)

        operation = " ".join(command)
        result = _safe_exec_docker(command, timeout=900, cwd=project_dir)

        if not result.ok:
            logger.error("Docker Compose up error: %s", result.stderr)
            return ToolResponse(
                user_response=f"❌ Failed to bring services up\n\n{_command_failure(operation, result)}",
                llm_response=(
                    f"`{operation}` failed with exit code {result.returncode}.\n"
                    f"stderr:\n{result.stderr.strip()}\nstdout:\n{result.stdout.strip()}"
                )
            )

        logger.info("Compose up %s by user %s", service or "all services",
                   user.username if user else "unknown")

        target = f"`{service}`" if service else "all services"
        return ToolResponse(
            user_response=_format_command_feedback(operation, result.stdout),
            llm_response=f"Successfully started compose {target}.\nOutput:\n{result.stdout}"
        )

    except Exception as e:
        logger.exception("Error in docker_compose_up: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to start compose services: {str(e)}"
        )


def docker_container(action: str, container_name: str, **kwargs) -> ToolResponse:
    """
    Unified Docker container management tool.

    Provides a single interface for container operations (create, run, start,
    stop, restart, inspect, logs) to reduce context size for profiles with wide
    permissions.

    Args:
        action: Action to perform. Available actions:
            - "create": Create a container from an image without starting it
            - "run": Create and start a container from an image
            - "start": Start a stopped container
            - "stop": Stop a running container (supports timeout param)
            - "restart": Restart a container (supports timeout param)
            - "inspect": Show detailed container information
            - "logs": Retrieve container logs (supports tail param)
        container_name: Name or ID of the container to operate on.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).
            - image (str): Required for create/run - image name/ID to use.
            - timeout (int): For stop/restart actions (1-120 seconds, default: 10).
            - tail (int): For logs action (1-1000 lines, default: 100).
            - port_mapping (str): For create/run - port mapping (e.g. "8080:80").
            - env_vars (dict): For create/run - environment variables.
            - detach (bool): For run - run in background (default: True).

    Returns:
        ToolResponse: Action result with user and LLM feedback.

    Raises:
        ValueError: If action is invalid or container_name contains unsafe input.
        RuntimeError: If Docker command fails.

    Example:
        >>> docker_container("start", "myapp_container")
        # Starts the container
        >>> docker_container("logs", "myapp_container", tail=50)
        # Shows last 50 lines of logs
        >>> docker_container("run", "mallorca-island", image="myapp:latest", port_mapping="8080:80")
        # Creates and starts the container from an image
    """
    action = action.lower().strip()
    valid_actions = ["create", "run", "start", "stop", "restart", "inspect", "logs"]

    if action not in valid_actions:
        return ToolResponse(
            user_response=f"❌ Invalid action '{action}'. Available actions: {', '.join(valid_actions)}",
            llm_response=f"Invalid container action: {action}"
        )

    try:
        if action in ("create", "run"):
            image = kwargs.pop("image", None)
            if not image:
                return ToolResponse(
                    user_response=f"❌ Action '{action}' requires an 'image' argument",
                    llm_response=f"Missing image for container action: {action}"
                )
            if action == "create":
                return docker_create(image, container_name, **kwargs)
            return docker_run(image, container_name, **kwargs)
        elif action == "start":
            return docker_start(container_name, **kwargs)
        elif action == "stop":
            timeout = kwargs.pop("timeout", 10)
            return docker_stop(container_name, timeout=timeout, **kwargs)
        elif action == "restart":
            timeout = kwargs.pop("timeout", 10)
            return docker_restart(container_name, timeout=timeout, **kwargs)
        elif action == "inspect":
            return docker_inspect(container_name, **kwargs)
        elif action == "logs":
            tail = kwargs.pop("tail", 100)
            return docker_logs(container_name, tail=tail, **kwargs)

    except Exception as e:
        logger.exception("Error in docker_container action '%s': %s", action, str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to execute container action: {str(e)}"
        )


def docker_compose_service(action: str, service: str, **kwargs) -> ToolResponse:
    """
    Unified Docker Compose service management tool.

    Provides a single interface for service operations (build, up, start, stop,
    restart, run) to reduce context size for profiles with wide permissions.
    Every action runs from the project directory against the project's compose
    file; actions never report success unless the compose command exited with 0.

    Args:
        action: Action to perform. Available actions:
            - "build": Build service images (all services if service is empty)
            - "up": Build (optional) and start services (all if service is empty)
            - "start": Start a stopped service (or all services if service is empty)
            - "stop": Stop a running service (supports timeout param)
            - "restart": Restart a service (supports timeout param)
            - "run": Execute a one-off command in a service (supports command param)
        service: Service name from the compose file (can be empty for
                 build/up/start/stop/restart to target all).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).
            - timeout (int): For stop/restart actions (1-120 seconds, default: 10).
            - command (str): For run action - command to execute in service.
            - no_deps (bool): For run action - do not start linked services.
            - build (bool): For up action - rebuild images (default: True).
            - detach (bool): For up action - run in background (default: True).
            - remove_orphans (bool): For up action - remove orphans (default: True).

    Returns:
        ToolResponse: Action result with user and LLM feedback.

    Raises:
        ValueError: If action is invalid or inputs contain unsafe values.
        RuntimeError: If Docker Compose command fails.

    Example:
        >>> docker_compose_service("up", "game")
        # Builds and starts the game service (creating its container)
        >>> docker_compose_service("build", "")
        # Builds every service image
        >>> docker_compose_service("run", "web", command="python manage.py migrate")
        # Runs migration command
    """
    action = action.lower().strip()
    valid_actions = ["build", "up", "start", "stop", "restart", "run"]

    if action not in valid_actions:
        return ToolResponse(
            user_response=f"❌ Invalid action '{action}'. Available actions: {', '.join(valid_actions)}",
            llm_response=f"Invalid compose service action: {action}"
        )

    try:
        service = service or ""
        if action == "build":
            service_name = service if service.strip() else None
            return docker_compose_build(service_name, **kwargs)
        elif action == "up":
            service_name = service if service.strip() else None
            build = kwargs.pop("build", True)
            detach = kwargs.pop("detach", True)
            remove_orphans = kwargs.pop("remove_orphans", True)
            return docker_compose_up(
                service_name,
                build=build,
                detach=detach,
                remove_orphans=remove_orphans,
                **kwargs,
            )
        elif action == "start":
            service_name = service if service.strip() else None
            return docker_compose_start(service_name, **kwargs)
        elif action == "stop":
            timeout = kwargs.pop("timeout", 10)
            service_name = service if service.strip() else None
            return docker_compose_stop(service_name, timeout=timeout, **kwargs)
        elif action == "restart":
            timeout = kwargs.pop("timeout", 10)
            service_name = service if service.strip() else None
            return docker_compose_restart(service_name, timeout=timeout, **kwargs)
        elif action == "run":
            command = kwargs.pop("command", None)
            return docker_compose_run(service, command=command, **kwargs)

    except Exception as e:
        logger.exception("Error in docker_compose_service action '%s': %s", action, str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to execute compose service action: {str(e)}"
        )


# Tool JSON definitions

DOCKER_PS_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_ps",
        "description": (
            "List Docker containers. Shows running and stopped containers "
            "with image, status/health, ports and compose project/service labels."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filters": {
                    "type": "string",
                    "description": (
                        "Optional Docker filter expression (e.g., 'status=running', 'label=env=prod'). "
                        "No shell metacharacters allowed."
                    )
                }
            },
            "required": []
        }
    }
}

DOCKER_LOGS_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_logs",
        "description": (
            "Retrieve and display logs from a Docker container. Useful for debugging, monitoring, "
            "and understanding container behavior."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "container_name": {
                    "type": "string",
                    "description": "Name or ID of the container"
                },
                "tail": {
                    "type": "integer",
                    "description": "Number of log lines to retrieve (1-1000, default: 100)"
                }
            },
            "required": ["container_name"]
        }
    }
}

DOCKER_STATS_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_stats",
        "description": (
            "Show real-time resource statistics (CPU, memory, I/O) for Docker containers. "
            "Useful for performance monitoring and identifying resource constraints."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "container_name": {
                    "type": "string",
                    "description": (
                        "Optional specific container name. If omitted, shows stats for all containers."
                    )
                }
            },
            "required": []
        }
    }
}

DOCKER_INSPECT_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_inspect",
        "description": (
            "Show detailed configuration and metadata for a Docker container or image. "
            "Includes networking, volumes, environment, and other detailed information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "container_name": {
                    "type": "string",
                    "description": "Name or ID of the container or image"
                },
                "inspect_type": {
                    "type": "string",
                    "enum": ["container", "image"],
                    "description": "Type of object to inspect (default: 'container')"
                }
            },
            "required": ["container_name"]
        }
    }
}

DOCKER_IMAGES_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_images",
        "description": (
            "List all available Docker images with repository, tag, size, and creation date. "
            "Useful for managing project dependencies and image versions."
        ),
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}

DOCKER_RUN_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_run",
        "description": (
            "Run a new Docker container from an image with security constraints. "
            "Pulls the image automatically when it is not cached. "
            "Prevents privilege escalation through input validation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "image": {
                    "type": "string",
                    "description": "Docker image name or ID to run"
                },
                "container_name": {
                    "type": "string",
                    "description": "Name for the new container"
                },
                "detach": {
                    "type": "boolean",
                    "description": "Run in background (default: true)"
                },
                "port_mapping": {
                    "type": "string",
                    "description": "Port mapping (e.g., '8080:80')"
                },
                "env_vars": {
                    "type": "object",
                    "description": "Environment variables as key-value pairs"
                }
            },
            "required": ["image", "container_name"]
        }
    }
}

DOCKER_START_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_start",
        "description": (
            "Start a stopped Docker container."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "container_name": {
                    "type": "string",
                    "description": "Name of the container to start"
                }
            },
            "required": ["container_name"]
        }
    }
}

DOCKER_STOP_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_stop",
        "description": (
            "Stop a running Docker container gracefully."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "container_name": {
                    "type": "string",
                    "description": "Name of the container to stop"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds before force stop (1-120, default: 10)"
                }
            },
            "required": ["container_name"]
        }
    }
}

DOCKER_RESTART_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_restart",
        "description": (
            "Restart a Docker container. Combines stop and start in one operation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "container_name": {
                    "type": "string",
                    "description": "Name of the container to restart"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds for stopping before restart (1-120, default: 10)"
                }
            },
            "required": ["container_name"]
        }
    }
}

DOCKER_COMPOSE_RUN_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_compose_run",
        "description": (
            "Run a one-off command in a docker-compose service. "
            "Useful for executing tasks like migrations, utilities, or API calls via curl. "
            "Supports URLs with query parameters and standard command syntax. "
            "Runs from the project directory against the project's compose file."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name defined in the project's compose file"
                },
                "command": {
                    "type": "string",
                    "description": (
                        "Command to execute in the service (optional). "
                        "Examples: 'python manage.py migrate', 'curl http://domain.com/api?key=value'"
                    )
                },
                "no_deps": {
                    "type": "boolean",
                    "description": "Do not start linked services (default: false)"
                }
            },
            "required": ["service"]
        }
    }
}

DOCKER_COMPOSE_START_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_compose_start",
        "description": (
            "Start docker-compose services. Starts one specific service or all services "
            "if service name is not provided. Note: 'start' only starts existing "
            "containers; use 'up' to create/build them."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Optional service name. If omitted, starts all services."
                }
            },
            "required": []
        }
    }
}

DOCKER_COMPOSE_STOP_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_compose_stop",
        "description": (
            "Stop docker-compose services. Stops one specific service or all services "
            "if service name is not provided."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Optional service name. If omitted, stops all services."
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds before force stop (1-120, default: 10)"
                }
            },
            "required": []
        }
    }
}

DOCKER_COMPOSE_RESTART_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_compose_restart",
        "description": (
            "Restart docker-compose services. Restarts one specific service or all services "
            "if service name is not provided."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Optional service name. If omitted, restarts all services."
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds for stopping before restart (1-120, default: 10)"
                }
            },
            "required": []
        }
    }
}

DOCKER_CONTAINER_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_container",
        "description": (
            "Unified Docker container management tool for common operations. "
            "Consolidates create, run, start, stop, restart, inspect and logs into a single "
            "interface to reduce context size for profiles with wide permissions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "run", "start", "stop", "restart", "inspect", "logs"],
                    "description": (
                        "Action to perform:\n"
                        "  - 'create': Create a container from an image (not started)\n"
                        "  - 'run': Create and start a container from an image\n"
                        "  - 'start': Start a stopped container\n"
                        "  - 'stop': Stop a running container\n"
                        "  - 'restart': Restart a container\n"
                        "  - 'inspect': Show detailed container information\n"
                        "  - 'logs': Retrieve container logs"
                    )
                },
                "container_name": {
                    "type": "string",
                    "description": "Name or ID of the container to operate on"
                },
                "image": {
                    "type": "string",
                    "description": "For create/run actions: image name or ID to use (required for create/run)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "For stop/restart actions: timeout in seconds before force action (1-120, default: 10)"
                },
                "tail": {
                    "type": "integer",
                    "description": "For logs action: number of log lines to retrieve (1-1000, default: 100)"
                },
                "port_mapping": {
                    "type": "string",
                    "description": "For create/run actions: port mapping (e.g., '8080:80')"
                },
                "env_vars": {
                    "type": "object",
                    "description": "For create/run actions: environment variables as key-value pairs"
                },
                "detach": {
                    "type": "boolean",
                    "description": "For run action: run in background (default: true)"
                }
            },
            "required": ["action", "container_name"]
        }
    }
}

DOCKER_COMPOSE_SERVICE_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "docker_compose_service",
        "description": (
            "Unified Docker Compose service management tool for common operations. "
            "Consolidates build, up, start, stop, restart and run into a single interface "
            "to reduce context size for profiles with wide permissions. "
            "Runs from the project directory against the project's compose file and only "
            "reports success when the compose command exits with 0."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["build", "up", "start", "stop", "restart", "run"],
                    "description": (
                        "Action to perform:\n"
                        "  - 'build': Build service images (all if service is empty)\n"
                        "  - 'up': Build and start services (all if service is empty)\n"
                        "  - 'start': Start a stopped service (or all if service is empty)\n"
                        "  - 'stop': Stop a service (or all if service is empty)\n"
                        "  - 'restart': Restart a service (or all if service is empty)\n"
                        "  - 'run': Execute a one-off command in a service"
                    )
                },
                "service": {
                    "type": "string",
                    "description": (
                        "Service name from the project's compose file. "
                        "Can be empty for build/up/start/stop/restart to target all services. "
                        "Required for run action."
                    )
                },
                "timeout": {
                    "type": "integer",
                    "description": "For stop/restart actions: timeout in seconds before force action (1-120, default: 10)"
                },
                "command": {
                    "type": "string",
                    "description": "For run action: command to execute in the service (optional)"
                },
                "no_deps": {
                    "type": "boolean",
                    "description": "For run action: do not start linked services (default: false)"
                },
                "build": {
                    "type": "boolean",
                    "description": "For up action: rebuild images before starting (default: true)"
                },
                "detach": {
                    "type": "boolean",
                    "description": "For up action: run in background (default: true)"
                },
                "remove_orphans": {
                    "type": "boolean",
                    "description": "For up action: remove orphan containers (default: true)"
                }
            },
            "required": ["action", "service"]
        }
    }
}

# Made with ❤️ by codx-junior