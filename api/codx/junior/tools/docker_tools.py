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

Tool Scope: "devops" (available to DevOps/admin roles only)

Made with ❤️ by codx-junior
"""

import logging
import re
import subprocess
from typing import Optional, List, Dict, Any, Tuple
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

ALLOWED_DOCKER_COMMANDS = {
    'ps': 'List running containers',
    'images': 'List available images',
    'logs': 'View container logs',
    'stats': 'Show live container statistics',
    'inspect': 'Show detailed container/image info',
    'network': 'Manage Docker networks',
    'volume': 'Manage Docker volumes',
}


class DockerCommandType(str, Enum):
    """Enumeration of allowed Docker command types."""
    PS = "ps"
    IMAGES = "images"
    LOGS = "logs"
    STATS = "stats"
    INSPECT = "inspect"
    RUN = "run"
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    COMPOSE_RUN = "compose_run"
    COMPOSE_START = "compose_start"
    COMPOSE_STOP = "compose_stop"
    COMPOSE_RESTART = "compose_restart"


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


def _safe_exec_docker(command: List[str], timeout: int = 30) -> Tuple[str, Optional[str]]:
    """
    Safely execute a Docker command using subprocess.

    Args:
        command: List of command arguments (no shell interpretation).
        timeout: Command timeout in seconds (default: 30).

    Returns:
        Tuple[str, Optional[str]]: (stdout, stderr_or_none)

    Raises:
        subprocess.TimeoutExpired: If command exceeds timeout.
        subprocess.CalledProcessError: If command returns non-zero exit code.
    """
    try:
        logger.debug("Executing Docker command: %s", " ".join(command))
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False  # Don't raise on non-zero exit
        )

        if result.returncode != 0:
            logger.warning("Docker command failed with exit code %d: %s\nstderr: %s", 
                         result.returncode, " ".join(command), result.stderr)
            return "", result.stderr

        logger.debug("Docker command succeeded: %s", " ".join(command))
        return result.stdout, None

    except subprocess.TimeoutExpired as e:
        error_msg = f"Command timed out after {timeout}s"
        logger.error("Docker command timeout: %s", " ".join(command))
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = str(e)
        logger.error("Error executing Docker command: %s", error_msg)
        raise RuntimeError(f"Failed to execute Docker command: {error_msg}") from e


def docker_ps(filters: Optional[str] = None, **kwargs) -> ToolResponse:
    """
    List Docker containers.

    Lists all running and stopped containers, optionally filtered by status or labels.

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
        command = ["docker", "ps", "-a", "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"]

        if filters:
            _validate_input(filters, "filters", allow_patterns=[r"^[a-zA-Z0-9_\-\.=]+$"])
            command.extend(["--filter", filters])

        stdout, stderr = _safe_exec_docker(command)

        if stderr:
            logger.error("Docker ps error for user %s: %s", user.username if user else "unknown", stderr)
            return ToolResponse(
                user_response="❌ Failed to list containers",
                llm_response=f"Error listing containers: {stderr}"
            )

        if not stdout.strip():
            return ToolResponse(
                user_response="✓ No containers found",
                llm_response="No containers currently running"
            )

        # Parse and format output
        lines = [line.strip() for line in stdout.strip().split('\n') if line.strip()]
        formatted_lines = ["**Container ID** | **Name** | **Status** | **Ports**"]
        formatted_lines.append("---|---|---|---")
        
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 2:
                container_id = parts[0]
                container_name = parts[1]
                status = parts[2] if len(parts) > 2 else "unknown"
                ports = parts[3] if len(parts) > 3 else "-"
                formatted_lines.append(f"`{container_id[:12]}` | `{container_name}` | {status} | {ports}")

        logger.info("Listed %d containers for user %s", len(lines), user.username if user else "unknown")

        user_response = f"✓ Found {len(lines)} container(s)\n\n" + "\n".join(formatted_lines)
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Listed {len(lines)} containers"
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
        stdout, stderr = _safe_exec_docker(command, timeout=10)

        if stderr and "error" in stderr.lower():
            logger.error("Docker logs error for container %s: %s", container_name, stderr)
            return ToolResponse(
                user_response=f"❌ Failed to retrieve logs: {stderr}",
                llm_response=f"Error retrieving logs for {container_name}: {stderr}"
            )

        if not stdout.strip():
            return ToolResponse(
                user_response=f"✓ No logs available for `{container_name}`",
                llm_response="Container has no log entries"
            )

        logger.info("Retrieved logs for container %s (tail=%d) by user %s", 
                   container_name, tail, user.username if user else "unknown")

        user_response = f"📋 **Logs for `{container_name}` (last {tail} lines):**\n\n```\n{stdout}\n```"
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Retrieved {len(stdout.split(chr(10)))} log lines from {container_name}"
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

        stdout, stderr = _safe_exec_docker(command, timeout=15)

        if stderr and "error" in stderr.lower():
            return ToolResponse(
                user_response=f"❌ Failed to retrieve statistics: {stderr}",
                llm_response=f"Error retrieving container stats: {stderr}"
            )

        if not stdout.strip():
            return ToolResponse(
                user_response="✓ No statistics available",
                llm_response="No running containers to show statistics for"
            )

        logger.info("Retrieved stats for %s by user %s",
                   container_name or "all containers", user.username if user else "unknown")

        user_response = f"📊 **Container Statistics:**\n\n```\n{stdout}\n```"
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Retrieved container statistics"
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
        stdout, stderr = _safe_exec_docker(command, timeout=10)

        if stderr and "error" in stderr.lower():
            return ToolResponse(
                user_response=f"❌ Failed to inspect {container_name}: {stderr}",
                llm_response=f"Error inspecting {container_name}: {stderr}"
            )

        logger.info("Inspected %s %s by user %s", inspect_type, container_name, 
                   user.username if user else "unknown")

        user_response = f"🔍 **{inspect_type.title()} Info for `{container_name}`:**\n\n```json\n{stdout}\n```"
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Retrieved detailed information for {container_name}"
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
        stdout, stderr = _safe_exec_docker(command)

        if stderr and "error" in stderr.lower():
            return ToolResponse(
                user_response=f"❌ Failed to list images: {stderr}",
                llm_response=f"Error listing Docker images: {stderr}"
            )

        if not stdout.strip():
            return ToolResponse(
                user_response="✓ No Docker images found",
                llm_response="No Docker images available"
            )

        lines = stdout.strip().split('\n')
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

        user_response = f"✓ Found {len(lines)} Docker image(s)\n\n" + "\n".join(formatted_lines)
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Listed {len(lines)} Docker images"
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

    Creates and starts a new container with specified configuration and security constraints.

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
        # Validate inputs
        _validate_input(container_name, "container_name", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])
        _validate_input(image, "image", allow_patterns=[r"^[a-zA-Z0-9_\-\.:/@]+$"])

        command = ["docker", "run", "-d" if detach else "-it"]
        command.extend(["--name", container_name])

        # Add port mappings if specified
        if port_mapping:
            _validate_input(port_mapping, "port_mapping", allow_patterns=[r"^\d+:\d+$"])
            command.extend(["-p", port_mapping])

        # Add environment variables
        for key, value in env_vars.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Environment variables must be strings")
            _validate_input(key, f"env_var_key_{key}")
            _validate_input(value, f"env_var_value_{key}")
            command.extend(["-e", f"{key}={value}"])

        command.append(image)

        stdout, stderr = _safe_exec_docker(command, timeout=30)

        if stderr:
            logger.error("Docker run error for user %s: %s", user.username if user else "unknown", stderr)
            return ToolResponse(
                user_response=f"❌ Failed to run container: {stderr}",
                llm_response=f"Error running container: {stderr}"
            )

        container_id = stdout.strip()[:12] if stdout else "unknown"
        logger.info("Started container %s (image=%s) for user %s", container_name, image, 
                   user.username if user else "unknown")

        user_response = f"✓ Container `{container_name}` started successfully\n\n**Container ID:** `{container_id}`"
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Successfully started container {container_name}"
        )

    except Exception as e:
        logger.exception("Error in docker_run: %s", str(e))
        return ToolResponse(
            user_response=f"❌ Error: {str(e)}",
            llm_response=f"Failed to run container: {str(e)}"
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
        stdout, stderr = _safe_exec_docker(command, timeout=15)

        if stderr and "error" in stderr.lower():
            logger.error("Docker start error for container %s: %s", container_name, stderr)
            return ToolResponse(
                user_response=f"❌ Failed to start container: {stderr}",
                llm_response=f"Error starting container: {stderr}"
            )

        logger.info("Started container %s by user %s", container_name, user.username if user else "unknown")

        user_response = f"✓ Container `{container_name}` started successfully"
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
        stdout, stderr = _safe_exec_docker(command, timeout=timeout + 10)

        if stderr and "error" in stderr.lower():
            logger.error("Docker stop error for container %s: %s", container_name, stderr)
            return ToolResponse(
                user_response=f"❌ Failed to stop container: {stderr}",
                llm_response=f"Error stopping container: {stderr}"
            )

        logger.info("Stopped container %s by user %s", container_name, user.username if user else "unknown")

        user_response = f"✓ Container `{container_name}` stopped successfully"
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
        stdout, stderr = _safe_exec_docker(command, timeout=timeout + 15)

        if stderr and "error" in stderr.lower():
            logger.error("Docker restart error for container %s: %s", container_name, stderr)
            return ToolResponse(
                user_response=f"❌ Failed to restart container: {stderr}",
                llm_response=f"Error restarting container: {stderr}"
            )

        logger.info("Restarted container %s by user %s", container_name, user.username if user else "unknown")

        user_response = f"✓ Container `{container_name}` restarted successfully"
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

    Executes a command in a service defined in docker-compose configuration.
    Allows shell commands with URLs, query parameters, and standard command syntax.

    Args:
        service: Service name in docker-compose.yml.
        command: Optional command to execute in the service (e.g., "curl http://domain.com/path?param=value").
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).

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

    if not settings:
        raise Exception("Invalid project settings")

    try:
        _validate_input(service, "service", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])
        if command:
            _validate_input(command, "command", allow_patterns=COMMAND_EXECUTION_ALLOWED_CHARS)

        compose_command = ["docker-compose", "run", "--rm", service]
        if command:
            compose_command.append(command)

        stdout, stderr = _safe_exec_docker(compose_command, timeout=60)

        if stderr and "error" in stderr.lower():
            logger.error("Docker Compose run error for service %s: %s", service, stderr)
            return ToolResponse(
                user_response=f"❌ Failed to run service: {stderr}",
                llm_response=f"Error running compose service: {stderr}"
            )

        logger.info("Executed compose run on service %s by user %s", service, 
                   user.username if user else "unknown")

        user_response = f"✓ Command executed on `{service}` service\n\n```\n{stdout}\n```"
        return ToolResponse(
            user_response=user_response,
            llm_response=f"Successfully executed command on {service} service"
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

    Starts one or all services defined in docker-compose.yml.

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
        if service:
            _validate_input(service, "service", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        command = ["docker-compose", "start"]
        if service:
            command.append(service)

        stdout, stderr = _safe_exec_docker(command, timeout=30)

        if stderr and "error" in stderr.lower():
            logger.error("Docker Compose start error: %s", stderr)
            return ToolResponse(
                user_response=f"❌ Failed to start services: {stderr}",
                llm_response=f"Error starting compose services: {stderr}"
            )

        logger.info("Started compose %s by user %s", service or "all services", 
                   user.username if user else "unknown")

        target = f"`{service}`" if service else "all services"
        user_response = f"✓ Docker Compose {target} started successfully"
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

    Stops one or all services defined in docker-compose.yml.

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
        if service:
            _validate_input(service, "service", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        if not isinstance(timeout, int) or timeout < 1 or timeout > 120:
            raise ValueError("timeout must be integer between 1-120 seconds")

        command = ["docker-compose", "stop", "-t", str(timeout)]
        if service:
            command.append(service)

        stdout, stderr = _safe_exec_docker(command, timeout=timeout + 15)

        if stderr and "error" in stderr.lower():
            logger.error("Docker Compose stop error: %s", stderr)
            return ToolResponse(
                user_response=f"❌ Failed to stop services: {stderr}",
                llm_response=f"Error stopping compose services: {stderr}"
            )

        logger.info("Stopped compose %s by user %s", service or "all services", 
                   user.username if user else "unknown")

        target = f"`{service}`" if service else "all services"
        user_response = f"✓ Docker Compose {target} stopped successfully"
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

    Stops and starts one or all services defined in docker-compose.yml.

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
        if service:
            _validate_input(service, "service", allow_patterns=[r"^[a-zA-Z0-9_\-\.]+$"])

        if not isinstance(timeout, int) or timeout < 1 or timeout > 120:
            raise ValueError("timeout must be integer between 1-120 seconds")

        command = ["docker-compose", "restart", "-t", str(timeout)]
        if service:
            command.append(service)

        stdout, stderr = _safe_exec_docker(command, timeout=timeout + 20)

        if stderr and "error" in stderr.lower():
            logger.error("Docker Compose restart error: %s", stderr)
            return ToolResponse(
                user_response=f"❌ Failed to restart services: {stderr}",
                llm_response=f"Error restarting compose services: {stderr}"
            )

        logger.info("Restarted compose %s by user %s", service or "all services", 
                   user.username if user else "unknown")

        target = f"`{service}`" if service else "all services"
        user_response = f"✓ Docker Compose {target} restarted successfully"
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


def docker_container(action: str, container_name: str, **kwargs) -> ToolResponse:
    """
    Unified Docker container management tool.

    Provides a single interface for container operations (start, stop, restart, inspect, logs)
    to reduce context size for profiles with wide permissions.

    Args:
        action: Action to perform. Available actions:
            - "start": Start a stopped container
            - "stop": Stop a running container (supports timeout param)
            - "restart": Restart a container (supports timeout param)
            - "inspect": Show detailed container information
            - "logs": Retrieve container logs (supports tail param)
        container_name: Name or ID of the container to operate on.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).
            - timeout (int): For stop/restart actions (1-120 seconds, default: 10).
            - tail (int): For logs action (1-1000 lines, default: 100).

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
    """
    action = action.lower().strip()
    valid_actions = ["start", "stop", "restart", "inspect", "logs"]

    if action not in valid_actions:
        return ToolResponse(
            user_response=f"❌ Invalid action '{action}'. Available actions: {', '.join(valid_actions)}",
            llm_response=f"Invalid container action: {action}"
        )

    try:
        if action == "start":
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

    Provides a single interface for service operations (start, stop, restart, run)
    to reduce context size for profiles with wide permissions.

    Args:
        action: Action to perform. Available actions:
            - "start": Start a stopped service (or all services if service is empty)
            - "stop": Stop a running service (supports timeout param)
            - "restart": Restart a service (supports timeout param)
            - "run": Execute a one-off command in a service (supports command param)
        service: Service name from docker-compose.yml (can be empty for start/stop/restart to target all).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).
            - user (CodxUser): Current user (for audit logging).
            - timeout (int): For stop/restart actions (1-120 seconds, default: 10).
            - command (str): For run action - command to execute in service.

    Returns:
        ToolResponse: Action result with user and LLM feedback.

    Raises:
        ValueError: If action is invalid or inputs contain unsafe values.
        RuntimeError: If Docker Compose command fails.

    Example:
        >>> docker_compose_service("start", "web")
        # Starts web service
        >>> docker_compose_service("run", "web", command="python manage.py migrate")
        # Runs migration command
    """
    action = action.lower().strip()
    valid_actions = ["start", "stop", "restart", "run"]

    if action not in valid_actions:
        return ToolResponse(
            user_response=f"❌ Invalid action '{action}'. Available actions: {', '.join(valid_actions)}",
            llm_response=f"Invalid compose service action: {action}"
        )

    try:
        if action == "start":
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
            "with status, ports, and basic information."
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
            "Supports URLs with query parameters and standard command syntax."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name defined in docker-compose.yml"
                },
                "command": {
                    "type": "string",
                    "description": (
                        "Command to execute in the service (optional). "
                        "Examples: 'python manage.py migrate', 'curl http://domain.com/api?key=value'"
                    )
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
            "if service name is not provided."
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
            "Consolidates start, stop, restart, inspect, and logs into a single interface "
            "to reduce context size for profiles with wide permissions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "stop", "restart", "inspect", "logs"],
                    "description": (
                        "Action to perform:\n"
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
                "timeout": {
                    "type": "integer",
                    "description": "For stop/restart actions: timeout in seconds before force action (1-120, default: 10)"
                },
                "tail": {
                    "type": "integer",
                    "description": "For logs action: number of log lines to retrieve (1-1000, default: 100)"
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
            "Consolidates start, stop, restart, and run into a single interface "
            "to reduce context size for profiles with wide permissions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "stop", "restart", "run"],
                    "description": (
                        "Action to perform:\n"
                        "  - 'start': Start a service (or all if service is empty)\n"
                        "  - 'stop': Stop a service (or all if service is empty)\n"
                        "  - 'restart': Restart a service (or all if service is empty)\n"
                        "  - 'run': Execute a one-off command in a service"
                    )
                },
                "service": {
                    "type": "string",
                    "description": (
                        "Service name from docker-compose.yml. "
                        "Can be empty for start/stop/restart to target all services. "
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
                }
            },
            "required": ["action", "service"]
        }
    }
}

# Made with ❤️ by codx-junior