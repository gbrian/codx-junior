"""
Dockerfile builds for the active codx-junior project.

Why shell out?
--------------
The Engine API can build images (``POST /build`` with a tar context), but that
means streaming an archive of the project to the daemon. The Docker CLI already
implements the context rules (``.dockerignore``, symlinks, BuildKit), shows a
usable progress log and behaves exactly like the command the user would type.
The router therefore runs ``docker build`` synchronously and returns the tail of
its output, like the compose stack actions do.

Security
--------
* The Dockerfile MUST be one discovered by the active project scan (see
  :mod:`codx.junior.infra.discovery`); an arbitrary path is rejected.
* A build context override must stay inside the project roots and exist.
* The tag / target / build-arg names are validated before reaching the CLI.
  Arguments are passed as a list (never a shell string), so nothing is
  interpolated by a shell.

Example
-------
```bash
curl -X POST -b "auth=…" -H 'Content-Type: application/json' \
     -d '{"path":"/srv/app/docker/Dockerfile","tag":"app:dev","target":"runtime"}' \
     "https://codx.local/api/infra/project/dockerfiles/build"
```
"""

import logging
import os
import re
import shlex
import shutil
import subprocess
from typing import Dict, List, Optional, Sequence

from codx.junior.infra import discovery
from codx.junior.infra.docker_client import DockerAPIError, DockerUnavailable
from codx.junior.infra.models import (
    InfraProjectDockerfileBuildRequest,
    InfraProjectDockerfileBuildResult,
)

logger = logging.getLogger(__name__)

BUILD_TIMEOUT = float(os.environ.get("CODX_JUNIOR_DOCKER_BUILD_TIMEOUT", "1800"))
MAX_OUTPUT_LINES = 200

_TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@-]*$")
_TARGET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_BUILD_ARG_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_UNSAFE_TAG_RE = re.compile(r"(\.\.|//|[\s$`])")


def build_env(manager: object, host_id: str) -> Dict[str, str]:
    """
    Environment for a ``docker build`` against the selected host.

    Mirrors :func:`codx.junior.infra.compose._compose_env`: a bare socket path is
    normalised to a ``unix://`` URI so ``DOCKER_HOST`` selects the very daemon
    the rest of the API talks to.

    Args:
        manager: :class:`~codx.junior.infra.manager.InfraManager`.
        host_id: Target host id.

    Returns:
        A copy of the process environment with ``DOCKER_HOST`` set.
    """
    endpoint = manager.host_config(host_id).endpoint
    if not endpoint.startswith(("unix://", "tcp://", "http://", "https://", "ssh://")):
        endpoint = "unix://" + endpoint
    env = dict(os.environ)
    env["DOCKER_HOST"] = endpoint
    return env


def _sanitize_tag_part(value: str) -> str:
    """Turn a folder/Dockerfile name into a valid image repository component."""
    part = re.sub(r"[^a-z0-9_.-]+", "-", (value or "").lower())
    part = re.sub(r"^[^a-z0-9]+|[-_.]+$", "", part)
    return part[:80] or "image"


def default_image_tag(asset: discovery.DockerfileAsset) -> str:
    """
    Derive a readable default image tag for a discovered Dockerfile.

    ``/srv/app/docker/Dockerfile`` → ``docker:latest``; a variant such as
    ``Dockerfile.worker`` becomes ``docker-worker:latest`` so two Dockerfiles in
    the same directory do not overwrite each other.

    Args:
        asset: Discovered Dockerfile.

    Returns:
        A valid ``repo:tag`` reference.
    """
    folder = _sanitize_tag_part(os.path.basename(asset.directory))
    name = (asset.name or "Dockerfile").strip()
    lower = name.lower()
    variant = ""
    if lower.startswith("dockerfile."):
        variant = name[len("Dockerfile."):]
    elif lower.startswith("containerfile."):
        variant = name[len("Containerfile."):]
    elif lower.endswith(".dockerfile"):
        variant = name[: -len(".dockerfile")]
    elif lower.endswith(".containerfile"):
        variant = name[: -len(".containerfile")]

    variant = _sanitize_tag_part(variant) if variant else ""
    repository = f"{folder}-{variant}" if variant and variant != "image" else folder
    return f"{repository}:latest"


def _validate_tag(tag: str) -> str:
    """
    Validate an image tag before it is handed to the CLI.

    Raises:
        ValueError: The tag is empty or contains shell/registry separators that
            never make sense in ``docker build -t``.
    """
    cleaned = (tag or "").strip()
    if not cleaned:
        raise ValueError("An image tag is required")
    if _UNSAFE_TAG_RE.search(cleaned) or not _TAG_RE.match(cleaned):
        raise ValueError(
            "Invalid image tag: use a repository name and optional :tag "
            "(letters, digits, '.', '_', '-', '/', ':')"
        )
    return cleaned


def _validate_target(target: Optional[str]) -> str:
    """Validate a multi-stage build target name (empty when not requested)."""
    value = (target or "").strip()
    if not value:
        return ""
    if not _TARGET_RE.match(value):
        raise ValueError("Invalid build target: only letters, digits, '.', '_' and '-'")
    return value


def _validate_build_args(values: Dict[str, str]) -> List[str]:
    """
    Validate ``--build-arg`` entries and render them as ``KEY=VALUE`` strings.

    Raises:
        ValueError: A key is not a valid build-arg name.
    """
    rendered: List[str] = []
    for key, value in (values or {}).items():
        name = str(key or "").strip()
        if not _BUILD_ARG_RE.match(name):
            raise ValueError(f"Invalid build argument name: '{key}'")
        rendered.append(f"{name}={'' if value is None else str(value)}")
    return rendered


def _output_tail(text: str) -> List[str]:
    """Return the last lines of a build log (keeps responses bounded)."""
    lines = [line.rstrip() for line in (text or "").splitlines() if line.strip()]
    return lines[-MAX_OUTPUT_LINES:]


def build_dockerfile(
    manager: object,
    request: InfraProjectDockerfileBuildRequest,
    project_roots: Sequence[discovery.ScanRoot],
) -> InfraProjectDockerfileBuildResult:
    """
    Build one discovered Dockerfile and return the tail of the CLI output.

    Args:
        manager: :class:`~codx.junior.infra.manager.InfraManager`.
        request: Dockerfile path, optional tag/context/target/build args and host.
        project_roots: Roots of the active project scan (validation boundary).

    Returns:
        :class:`InfraProjectDockerfileBuildResult` with the image tag and output.

    Raises:
        ValueError: The path is not in the project scan, the context is outside
            the roots, or a tag/target/build-arg is invalid.
        DockerUnavailable: The Docker CLI is not installed / cannot be started.
        DockerAPIError: 500/502 when the build fails, 504 on timeout.
    """
    if not project_roots:
        raise ValueError(
            "No active project: open a project before building a Dockerfile"
        )

    asset = discovery.resolve_dockerfile_target(request.path, project_roots)
    if not asset:
        raise ValueError(
            "The Dockerfile is not part of the active project scan "
            "(it must live inside the project or one of its child projects)"
        )

    tag = _validate_tag(request.tag or default_image_tag(asset))
    target = _validate_target(request.target)

    context = (request.context or "").strip() or asset.context or asset.directory
    if not os.path.isdir(context):
        raise ValueError(f"Build context is not a directory: {context}")
    if not discovery.is_path_within_roots(context, project_roots):
        raise ValueError("The build context must stay inside the active project")

    docker_cli = shutil.which("docker")
    if not docker_cli:
        raise DockerUnavailable(
            "The docker CLI is not available on the codx-junior host: "
            "cannot run 'docker build'"
        )

    resolved_host = manager.host_config(request.host_id).id
    command = [docker_cli, "build", "--file", asset.path, "--tag", tag]
    if target:
        command += ["--target", target]
    for build_arg in _validate_build_args(request.build_args):
        command += ["--build-arg", build_arg]
    command.append(context)

    logger.info(
        "Docker build on %s: %s",
        resolved_host,
        " ".join(shlex.quote(part) for part in command),
    )

    try:
        result = subprocess.run(
            command,
            cwd=context,
            env=build_env(manager, resolved_host),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=BUILD_TIMEOUT,
        )
    except subprocess.TimeoutExpired as ex:
        raise DockerAPIError(
            504,
            f"'docker build' did not finish within {int(BUILD_TIMEOUT)} seconds",
            "docker build",
        ) from ex
    except OSError as ex:
        raise DockerUnavailable(f"Cannot run docker build: {ex}") from ex

    output = _output_tail(result.stdout or "")
    if result.returncode != 0:
        message = "\n".join(output[-8:]) or f"exit code {result.returncode}"
        raise DockerAPIError(500, message[:1600], "docker build")

    logger.info("Docker image %s built from %s", tag, asset.path)
    return InfraProjectDockerfileBuildResult(
        ok=True,
        image=tag,
        tag=tag,
        dockerfile=asset.path,
        context=context,
        output=output[-40:],
    )

# Made with ❤️ by codx-junior
