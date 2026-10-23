"""
Docker infrastructure access layer.

This package isolates everything that talks to the Docker daemon from the HTTP
layer, so the router stays a thin, admin-gated façade over a testable service.

Modules
-------
docker_client.py  – HTTP client for the Docker Engine API (unix socket / tcp).
models.py         – pydantic models mirroring the `/api/infra/*` contract.
manager.py        – mapping + orchestration (hosts, containers, stacks, …).

Environment
-----------
CODX_JUNIOR_DOCKER_SOCKET  Docker unix socket path (default /var/run/docker.sock)
DOCKER_HOST                Docker endpoint (unix://, tcp://, http://, https://)
CODX_JUNIOR_DOCKER_TIMEOUT Request timeout in seconds (default 10)
CODX_JUNIOR_INFRA_HOSTS    JSON array of host definitions; overrides the local one

Example
-------
```bash
# Talk to a remote daemon instead of the local socket
export CODX_JUNIOR_INFRA_HOSTS='[
  {"id": "host-remote", "name": "build-runner-01", "endpoint": "tcp://10.0.0.21:2376"}
]'
```

Diagram
-------
flowchart LR
    UI[client/src/api/modules/infra.js] -->|/api/infra/*| R[api/infra.py]
    R -->|require_admin| M[InfraManager]
    M --> C[DockerClient]
    C --> D[(Docker daemon)]
"""

from codx.junior.infra.docker_client import (
    DEFAULT_ENDPOINT,
    DockerAPIError,
    DockerClient,
    DockerUnavailable,
)
from codx.junior.infra.manager import InfraManager, get_infra_manager

__all__ = [
    "DEFAULT_ENDPOINT",
    "DockerAPIError",
    "DockerClient",
    "DockerUnavailable",
    "InfraManager",
    "get_infra_manager",
]

# Made with ❤️ by codx-junior