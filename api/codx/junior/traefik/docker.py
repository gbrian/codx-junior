"""
Docker container discovery for the Traefik rule editor.

We deliberately use the Docker CLI instead of the full ``codx.junior.infra``
manager: the editor only needs names, ports, networks and compose labels for
*running* containers, and the CLI is already a hard dependency of the workspace
engine.

The result is cached for a few seconds because the rule editor may load it
while the user opens several target pickers.
"""

import json
import logging
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 5.0
DOCKER_TIMEOUT_SECONDS = 10

_cache: Dict[str, Any] = {"at": 0.0, "data": None}
_lock = threading.Lock()


def _run(args: List[str], timeout: int = DOCKER_TIMEOUT_SECONDS) -> Tuple[str, Optional[str]]:
    """Run a docker CLI command and return ``(stdout, error)``."""
    try:
        result = subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return "", "Docker CLI is not available"
    except subprocess.TimeoutExpired:
        return "", f"Docker command timed out after {timeout}s"
    except Exception as ex:  # pragma: no cover - defensive
        return "", str(ex)

    if result.returncode != 0:
        return "", (result.stderr or result.stdout or "docker command failed").strip()
    return result.stdout or "", None


def _extract_ports(container: Dict[str, Any]) -> List[int]:
    """Return the container's internal TCP ports (deduplicated, sorted)."""
    ports = set()
    sections = [
        (container.get("Config") or {}).get("ExposedPorts"),
        (container.get("NetworkSettings") or {}).get("Ports"),
        (container.get("HostConfig") or {}).get("PortBindings"),
    ]
    for section in sections:
        for key in (section or {}):
            port, _, proto = str(key).partition("/")
            if proto and proto != "tcp":
                continue
            if port.isdigit():
                ports.add(int(port))
    return sorted(ports)


def _extract_networks(container: Dict[str, Any]) -> Tuple[List[str], Dict[str, List[str]]]:
    networks = ((container.get("NetworkSettings") or {}).get("Networks") or {})
    names = list(networks.keys())
    aliases = {
        name: list((info or {}).get("Aliases") or [])
        for name, info in networks.items()
    }
    return names, aliases


def _is_traefik(container: Dict[str, Any]) -> bool:
    name = (container.get("Name") or "").lstrip("/").lower()
    image = ((container.get("Config") or {}).get("Image") or "").lower()
    return "traefik" in name or "traefik" in image


def _shape_container(container: Dict[str, Any], traefik_networks: List[str]) -> Dict[str, Any]:
    labels = (container.get("Config") or {}).get("Labels") or {}
    name = (container.get("Name") or "").lstrip("/")
    networks, aliases = _extract_networks(container)
    ports = _extract_ports(container)
    state = ((container.get("State") or {}).get("Status") or "").lower()

    reachable: Optional[bool]
    if traefik_networks:
        reachable = bool(set(networks) & set(traefik_networks))
    else:
        reachable = None

    return {
        "id": container.get("Id") or "",
        "name": name,
        "image": (container.get("Config") or {}).get("Image") or "",
        "state": state,
        "running": state == "running",
        "ports": ports,
        "networks": networks,
        "network_aliases": aliases,
        "compose_project": labels.get("com.docker.compose.project", ""),
        "compose_service": labels.get("com.docker.compose.service", ""),
        "traefik_enable": str(labels.get("traefik.enable", "")).lower() == "true",
        "reachable": reachable,
    }


def _query_containers() -> Dict[str, Any]:
    ids_stdout, error = _run(["ps", "-q"])
    if error:
        return {"containers": [], "traefik_networks": [], "error": error}

    ids = [line.strip() for line in ids_stdout.splitlines() if line.strip()]
    if not ids:
        return {"containers": [], "traefik_networks": [], "error": None}

    inspect_stdout, error = _run(["inspect", *ids])
    if error:
        return {"containers": [], "traefik_networks": [], "error": error}

    try:
        containers = json.loads(inspect_stdout)
    except json.JSONDecodeError as ex:
        logger.warning("Cannot parse docker inspect output: %s", ex)
        return {"containers": [], "traefik_networks": [], "error": "Invalid Docker inspect output"}

    traefik_networks: List[str] = []
    for container in containers:
        if _is_traefik(container):
            networks, _ = _extract_networks(container)
            traefik_networks.extend(networks)
    traefik_networks = sorted(set(traefik_networks))

    shaped = [
        _shape_container(container, traefik_networks)
        for container in containers
        if not _is_traefik(container)
    ]
    shaped.sort(key=lambda item: (not item["running"], item["name"].lower()))
    return {
        "containers": shaped,
        "traefik_networks": traefik_networks,
        "error": None,
    }


def list_running_containers(force: bool = False) -> Dict[str, Any]:
    """
    Return running Docker containers with ports / networks / compose labels.

    The result is cached for ``CACHE_TTL_SECONDS``.  Docker failures never
    raise: they are returned as ``{"containers": [], "error": "..."}`` so the
    settings UI can still use URL and workspace targets.
    """
    global _cache

    with _lock:
        if not force and _cache["data"] is not None and time.time() - _cache["at"] < CACHE_TTL_SECONDS:
            return _cache["data"]

    data = _query_containers()
    with _lock:
        _cache = {"at": time.time(), "data": data}
    return data
