"""
Docker asset discovery for the active codx-junior project.

Why scan the filesystem?
------------------------
The Docker Engine only knows what is *running* (or was created) on the host:
a compose project that was never started has no container, therefore no
``com.docker.compose.*`` label, therefore it does not exist for
``GET /api/infra/stacks``. The user, however, thinks in terms of the project
checkout: "this repository has a compose file, let me start it". InfraView
therefore also scans the active project folder (plus its nested and declared
child projects) for:

* compose files — ``compose.yaml``, ``docker-compose.yml`` (and their
  ``.override`` / variant siblings), grouped per directory so a command gets
  every file of the project, exactly like ``docker compose`` would;
* Dockerfiles — ``Dockerfile``, ``Dockerfile.*``, ``*.Dockerfile`` and the
  ``Containerfile`` equivalents, including their ``FROM`` / stage metadata and
  the build context declared by a compose ``build:`` section.

Safety / performance
--------------------
* The scan is rooted: a scan root is an absolute project path. Every path used
  by an action is re-validated against those roots, so a request cannot point
  the CLI at an arbitrary file on the codx-junior host.
* Symlinks are not followed, heavy dependency folders (``node_modules``,
  virtualenvs, caches) are pruned, and both the visited-directory count and the
  number of matches are capped.
* Results are cached per root set for ``CODX_JUNIOR_DOCKER_SCAN_TTL`` seconds
  (20 by default) because InfraView polls; ``force=True`` bypasses the cache
  when the user explicitly asks for a fresh scan.

Example
-------
```python
roots = [ScanRoot("/srv/app", "app"), ScanRoot("/srv/app/libs/api", "api")]
result = scan_project_docker(roots)
for project in result.compose:
    print(project.name, project.files)
for dockerfile in result.dockerfiles:
    print(dockerfile.path, dockerfile.base_images)
```
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

try:  # PyYAML is already a transitive dependency of the wiki/plugin code.
    import yaml
except ImportError:  # pragma: no cover - only on a broken installation
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

DEFAULT_SCAN_TTL = float(os.environ.get("CODX_JUNIOR_DOCKER_SCAN_TTL", "20"))
MAX_SCAN_DEPTH = int(os.environ.get("CODX_JUNIOR_DOCKER_SCAN_DEPTH", "12"))
MAX_VISITED_DIRS = int(os.environ.get("CODX_JUNIOR_DOCKER_SCAN_DIRS", "20000"))
MAX_COMPOSE_PROJECTS = int(os.environ.get("CODX_JUNIOR_DOCKER_SCAN_COMPOSE", "300"))
MAX_DOCKERFILES = int(os.environ.get("CODX_JUNIOR_DOCKER_SCAN_DOCKERFILES", "500"))
MAX_COMPOSE_BYTES = 4 * 1024 * 1024

# Directories that never contain first-party Docker assets and can be huge.
SKIP_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".codx",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "bower_components",
    "site-packages",
    "dist-packages",
    "__pycache__",
    ".next",
    ".nuxt",
    ".turbo",
    ".parcel-cache",
    "htmlcov",
}

BASE_COMPOSE_NAMES = (
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
)

_COMPOSE_FILE_RE = re.compile(
    r"^(?:docker-compose|compose)(?:\.[A-Za-z0-9_.-]+)?\.ya?ml$", re.I
)
_COMPOSE_OVERRIDE_RE = re.compile(r"^(?:docker-compose|compose)\.override\.ya?ml$", re.I)
_DOCKERFILE_RE = re.compile(
    r"(?:^dockerfile(?:\..+)?$)"
    r"|(?:^.+\.dockerfile$)"
    r"|(?:^containerfile(?:\..+)?$)"
    r"|(?:^.+\.containerfile$)",
    re.I,
)
_FROM_RE = re.compile(
    r"^FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?\s*$", re.I
)
_VAR_RE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}|([A-Za-z_][A-Za-z0-9_]*))")
_PROJECT_NAME_INVALID_RE = re.compile(r"[^a-z0-9_-]+")


# ── Data ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ScanRoot:
    """A directory to scan and the codx-junior project that owns it."""

    path: str
    project: str = ""


@dataclass
class ComposeProject:
    """A compose project discovered from files on disk."""

    name: str
    path: str
    directory: str
    files: List[str] = field(default_factory=list)
    declared_services: List[str] = field(default_factory=list)
    project: str = ""
    project_root: str = ""
    relative_path: str = ""
    error: str = ""


@dataclass
class DockerfileAsset:
    """A Dockerfile discovered from files on disk."""

    name: str
    path: str
    directory: str
    relative_path: str
    context: str
    project: str = ""
    project_root: str = ""
    base_images: List[str] = field(default_factory=list)
    stages: List[str] = field(default_factory=list)
    stage_count: int = 0
    has_dockerignore: bool = False
    compose_project: str = ""
    compose_service: str = ""


@dataclass
class ScanResult:
    """Everything found under a set of roots."""

    compose: List[ComposeProject] = field(default_factory=list)
    dockerfiles: List[DockerfileAsset] = field(default_factory=list)
    scanned_at: str = ""
    cached: bool = False


# (root-set key) → (monotonic timestamp, result)
_scan_cache: Dict[Tuple[Tuple[str, str], ...], Tuple[float, ScanResult]] = {}
_scan_lock = threading.Lock()


# ── Path helpers ──────────────────────────────────────────────────────────────


def _abs(path: str) -> str:
    """Absolute, normalised path (no symlink resolution)."""
    return os.path.normpath(os.path.abspath(os.path.expanduser(path or "")))


def _real(path: str) -> str:
    """Absolute path with symlinks resolved."""
    return os.path.realpath(_abs(path))


def normalize_scan_roots(roots: Sequence[ScanRoot]) -> List[ScanRoot]:
    """
    Clean, deduplicate and order scan roots (parents before children).

    A root that does not exist (anymore) is dropped; an empty project label
    falls back to the directory name. Sorting by path length makes the
    ``visited_dirs`` guard skip a nested root that the parent scan already
    walked, while keeping the nested root available for project labelling.

    Args:
        roots: Candidate scan roots.

    Returns:
        The usable roots, shallowest first.
    """
    cleaned: List[ScanRoot] = []
    seen = set()
    for root in roots or []:
        path = _abs(getattr(root, "path", "") or "")
        if not path or not os.path.isdir(path):
            continue
        real_path = _real(path)
        if real_path in seen:
            continue
        seen.add(real_path)
        project = (getattr(root, "project", "") or "").strip() or os.path.basename(real_path)
        cleaned.append(ScanRoot(path=real_path, project=project))
    cleaned.sort(key=lambda item: (len(item.path), item.path))
    return cleaned


def is_path_within_roots(path: str, roots: Sequence[ScanRoot]) -> bool:
    """
    Return True when ``path`` is inside one of the (normalised) roots.

    Uses ``os.path.commonpath`` on real paths, so a shared string prefix
    (``/srv/app2`` vs ``/srv/app``) is not mistaken for containment.

    Example:
        >>> is_path_within_roots("/srv/app/docker-compose.yml", [ScanRoot("/srv/app")])
        True
        >>> is_path_within_roots("/srv/other/docker-compose.yml", [ScanRoot("/srv/app")])
        False
    """
    if not path:
        return False
    real_path = _real(path)
    for root in normalize_scan_roots(roots):
        try:
            if os.path.commonpath([real_path, root.path]) == root.path:
                return True
        except ValueError:
            continue
    return False


def _owner_root(path: str, roots: Sequence[ScanRoot]) -> Optional[ScanRoot]:
    """Return the most specific scan root containing ``path``."""
    real_path = _real(path)
    best: Optional[ScanRoot] = None
    for root in roots:
        try:
            if os.path.commonpath([real_path, root.path]) != root.path:
                continue
        except ValueError:
            continue
        if best is None or len(root.path) > len(best.path):
            best = root
    return best


def _relative_to(path: str, root: ScanRoot) -> str:
    """Path relative to the owning root, with forward slashes."""
    try:
        relative = os.path.relpath(_real(path), root.path)
    except ValueError:
        return path
    if relative == ".":
        return os.path.basename(path)
    return relative.replace(os.sep, "/")


# ── Compose helpers ───────────────────────────────────────────────────────────


def _is_compose_filename(filename: str) -> bool:
    """Return True for ``compose.yaml`` / ``docker-compose.yml`` (any case)."""
    return bool(_COMPOSE_FILE_RE.match(filename or ""))


def _is_dockerfile_filename(filename: str) -> bool:
    """Return True for Dockerfile/Containerfile names and their variants."""
    return bool(_DOCKERFILE_RE.match(filename or ""))


def _read_env_file(directory: str) -> Dict[str, str]:
    """
    Parse the ``.env`` of a compose directory (best effort).

    Docker Compose reads ``KEY=VALUE`` lines (optionally prefixed with
    ``export``, optionally quoted) from the project directory. Only the values
    needed for the project name are used here, so a malformed line is skipped
    instead of failing the scan.

    Args:
        directory: Compose file directory.

    Returns:
        The parsed variables (empty when there is no readable ``.env``).
    """
    values: Dict[str, str] = {}
    path = os.path.join(directory, ".env")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                key, _, value = line.partition("=")
                key = key.strip()
                if not key:
                    continue
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                    value = value[1:-1]
                values[key] = value
    except OSError:
        return {}
    return values


def _interpolate(value: str, env: Dict[str, str]) -> str:
    """
    Resolve the ``$VAR`` / ``${VAR}`` / ``${VAR:-default}`` forms in a name.

    Compose performs full interpolation before using ``name:``. Only the common
    forms are implemented (enough to resolve ``${COMPOSE_PROJECT_NAME}``); an
    unknown variable is left untouched so the caller can detect it.

    Example:
        >>> _interpolate("${PREFIX:-app}-web", {"PREFIX": "shop"})
        'shop-web'
    """

    def replace(match: re.Match) -> str:
        name = match.group(1) or match.group(3)
        default = match.group(2)
        if name in env:
            return env[name]
        if name in os.environ:
            return os.environ[name]
        return default if default is not None else match.group(0)

    return _VAR_RE.sub(replace, value or "")


def normalize_project_name(value: str) -> str:
    """
    Normalise a compose project name the way Docker does.

    Docker accepts lowercase letters, digits, dashes and underscores, and the
    name must start with a letter or digit.

    Example:
        >>> normalize_project_name("My Project (dev)")
        'myprojectdev'
        >>> normalize_project_name("")
        ''
    """
    name = (value or "").strip().lower()
    name = _PROJECT_NAME_INVALID_RE.sub("", name)
    name = re.sub(r"^[^a-z0-9]+", "", name)
    return name[:63]


def _load_yaml(path: str) -> Tuple[Optional[dict], str]:
    """
    Load a compose file safely.

    Returns:
        ``(document, error)``; both are empty/None when the file cannot be read
        or is not valid YAML. A scan must never fail because one file is broken.
    """
    if yaml is None:
        return None, "PyYAML is not installed: compose files cannot be parsed"
    try:
        if os.path.getsize(path) > MAX_COMPOSE_BYTES:
            return None, "compose file is too large to parse"
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            document = yaml.safe_load(handle)
    except OSError as ex:
        return None, f"cannot read compose file: {ex}"
    except yaml.YAMLError as ex:  # type: ignore[union-attr]
        return None, f"invalid YAML: {ex}"
    return (document if isinstance(document, dict) else None), ""


def _merged_services(files: Sequence[str]) -> Tuple[Dict[str, object], str]:
    """
    Merge the ``services:`` maps of several compose files.

    Compose merges files left to right; the same override semantics is applied
    here (a later service definition replaces the earlier one) because only the
    service names are needed by the UI.

    Args:
        files: Compose files, base first.

    Returns:
        ``(services, error)`` with the first parse error encountered.
    """
    services: Dict[str, object] = {}
    error = ""
    for path in files:
        document, parse_error = _load_yaml(path)
        if parse_error and not error:
            error = parse_error
        if not document:
            continue
        declared = document.get("services")
        if isinstance(declared, dict):
            services.update(declared)
    return services, error


def _compose_project_name(
    directory: str, files: Sequence[str], env: Dict[str, str]
) -> str:
    """
    Resolve the compose project name from the project's own configuration.

    The order is ``COMPOSE_PROJECT_NAME`` in the directory's ``.env`` →
    top-level ``name:`` → directory name. (The process-wide
    ``COMPOSE_PROJECT_NAME`` is deliberately ignored: codx-junior itself may
    run under compose with such a variable, and it must not rename every
    discovered project.) The resolved name is passed to the CLI as ``-p``, so
    it is authoritative for actions too.

    This is what the running containers carry in their labels, so it is what
    makes a discovered stack line up with a running one.
    """
    env_name = env.get("COMPOSE_PROJECT_NAME")
    if env_name:
        normalized = normalize_project_name(_interpolate(env_name, env))
        if normalized:
            return normalized

    for path in files:
        document, _ = _load_yaml(path)
        if not document:
            continue
        declared = document.get("name")
        if isinstance(declared, str) and declared.strip():
            normalized = normalize_project_name(_interpolate(declared.strip(), env))
            if normalized:
                return normalized

    return normalize_project_name(os.path.basename(directory)) or "compose"


def _compose_files_for_dir(directory: str, filenames: Optional[Sequence[str]] = None) -> List[str]:
    """
    Return the compose files of a directory in ``docker compose`` order.

    A base file (``compose.yaml`` / ``docker-compose.yml``) comes first, then
    its ``.override`` sibling, then any variants (``docker-compose.prod.yml``).
    They are grouped as ONE project because that is the natural unit of a
    directory and because compose itself merges the base + override pair.

    Args:
        directory: Directory to inspect.
        filenames: Optional pre-read directory entries.

    Returns:
        Absolute compose file paths (empty when the directory has none).
    """
    if filenames is None:
        try:
            filenames = os.listdir(directory)
        except OSError:
            return []

    names = [
        name
        for name in filenames
        if _is_compose_filename(name) and os.path.isfile(os.path.join(directory, name))
    ]
    if not names:
        return []

    def rank(name: str) -> Tuple[int, int, str]:
        lower = name.lower()
        if lower in BASE_COMPOSE_NAMES:
            return (0, BASE_COMPOSE_NAMES.index(lower), lower)
        if _COMPOSE_OVERRIDE_RE.match(name):
            return (1, 0, lower)
        return (2, 0, lower)

    names.sort(key=rank)
    return [os.path.join(directory, name) for name in names]


def _build_compose_project(
    directory: str, files: Sequence[str], owner: ScanRoot
) -> ComposeProject:
    """Build the :class:`ComposeProject` record for one directory."""
    env = _read_env_file(directory)
    services, error = _merged_services(files)
    primary = files[0] if files else ""
    return ComposeProject(
        name=_compose_project_name(directory, files, env),
        path=primary,
        directory=directory,
        files=list(files),
        declared_services=list(services.keys()),
        project=owner.project,
        project_root=owner.path,
        relative_path=_relative_to(primary, owner) if primary else "",
        error=error,
    )


def _compose_build_refs(
    directory: str, project_name: str, files: Sequence[str]
) -> Dict[str, Tuple[str, str, str]]:
    """
    Map Dockerfile paths to the compose service that builds them.

    Both compose build syntaxes are handled::

        build: ./app
        build:
          context: ./app
          dockerfile: Dockerfile.dev

    Each file is read independently: a shallow service merge would let an
    override file that only sets ``environment:`` hide the ``build:`` section
    declared by the base file.

    Returns:
        ``{realpath(dockerfile): (compose_project, service, context)}``.
    """
    refs: Dict[str, Tuple[str, str, str]] = {}
    for path in files:
        document, _ = _load_yaml(path)
        if not document:
            continue
        services = document.get("services")
        if not isinstance(services, dict):
            continue
        for service_name, service in services.items():
            if not isinstance(service, dict):
                continue
            build = service.get("build")
            if not build:
                continue

            context = "."
            dockerfile = "Dockerfile"
            if isinstance(build, str):
                context = build
            elif isinstance(build, dict):
                context = build.get("context") or "."
                dockerfile = build.get("dockerfile") or "Dockerfile"
            else:
                continue

            if str(context).startswith(
                ("http://", "https://", "git://", "ssh://", "git@")
            ):
                continue
            context_path = _abs(os.path.join(directory, str(context)))
            if os.path.isabs(str(dockerfile)):
                dockerfile_path = _abs(str(dockerfile))
            else:
                dockerfile_path = _abs(os.path.join(context_path, str(dockerfile)))
            refs[_real(dockerfile_path)] = (
                project_name,
                str(service_name),
                context_path,
            )
    return refs


# ── Dockerfile helpers ────────────────────────────────────────────────────────


def _parse_dockerfile(path: str) -> Tuple[List[str], List[str]]:
    """
    Read the ``FROM`` instructions of a Dockerfile.

    Line continuations (``FROM \\``) and comments are handled; the parser stops
    after :data:`MAX_DOCKERFILE_LINES` lines so a generated 50k-line file cannot
    stall a scan.

    Args:
        path: Dockerfile path.

    Returns:
        ``(base_images, stages)`` — the image reference of every ``FROM`` and the
        names declared with ``AS``.
    """
    base_images: List[str] = []
    stages: List[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()[:5000]
    except OSError:
        return [], []

    buffer = ""
    for raw_line in lines:
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if not buffer and (not stripped or stripped.startswith("#")):
            continue
        if line.rstrip().endswith("\\"):
            buffer += line.rstrip()[:-1] + " "
            continue
        statement = (buffer + line).strip()
        buffer = ""
        match = _FROM_RE.match(statement)
        if not match:
            continue
        image, stage = match.group(1), match.group(2)
        if image:
            base_images.append(image)
        if stage:
            stages.append(stage)
    return base_images, stages


# ── Scan ──────────────────────────────────────────────────────────────────────


def _scan_key(roots: Sequence[ScanRoot]) -> Tuple[Tuple[str, str], ...]:
    """Stable cache key for a normalised root set."""
    return tuple((root.path, root.project) for root in roots)


def _now_iso() -> str:
    """Current UTC time in ISO 8601 (seconds precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def scan_project_docker(
    roots: Sequence[ScanRoot], force: bool = False
) -> ScanResult:
    """
    Scan the given roots for compose files and Dockerfiles.

    Args:
        roots: Project roots (see :class:`ScanRoot`).
        force: Bypass the TTL cache when True.

    Returns:
        A :class:`ScanResult`; a failed directory is skipped, never raised.
    """
    normalized = normalize_scan_roots(roots)
    if not normalized:
        return ScanResult(scanned_at=_now_iso())

    key = _scan_key(normalized)
    now = time.monotonic()
    with _scan_lock:
        cached = _scan_cache.get(key)
        if cached and not force and (now - cached[0]) < DEFAULT_SCAN_TTL:
            result = cached[1]
            return ScanResult(
                compose=list(result.compose),
                dockerfiles=list(result.dockerfiles),
                scanned_at=result.scanned_at,
                cached=True,
            )

        result = _scan_uncached(normalized)
        if len(_scan_cache) > 16:
            _scan_cache.clear()
        _scan_cache[key] = (now, result)
        return ScanResult(
            compose=list(result.compose),
            dockerfiles=list(result.dockerfiles),
            scanned_at=result.scanned_at,
            cached=False,
        )


def _scan_uncached(roots: Sequence[ScanRoot]) -> ScanResult:
    """Walk the roots and collect compose projects and Dockerfiles."""
    compose: List[ComposeProject] = []
    dockerfiles: List[DockerfileAsset] = []
    build_refs: Dict[str, Tuple[str, str, str]] = {}
    visited_dirs = set()
    seen_files = set()
    visited = 0

    for scan_root in roots:
        if _real(scan_root.path) in visited_dirs:
            continue
        for dirpath, dirnames, filenames in os.walk(
            scan_root.path, topdown=True, followlinks=False
        ):
            dir_real = _real(dirpath)
            if dir_real in visited_dirs:
                # A parent root already walked this subtree.
                dirnames[:] = []
                continue
            visited_dirs.add(dir_real)
            visited += 1
            if visited > MAX_VISITED_DIRS:
                logger.warning(
                    "Docker scan stopped after %d directories under %s",
                    visited,
                    scan_root.project,
                )
                break

            depth = 0
            if dirpath != scan_root.path:
                relative = os.path.relpath(dirpath, scan_root.path)
                depth = relative.count(os.sep) + 1
            if depth >= MAX_SCAN_DEPTH:
                dirnames[:] = []
            else:
                dirnames[:] = sorted(
                    name
                    for name in dirnames
                    if name.lower() not in SKIP_DIRECTORIES
                )

            # A directory can belong to a nested child project: label it with
            # the most specific root, not with the project of the parent root.
            owner = _owner_root(dirpath, roots) or scan_root

            compose_files = _compose_files_for_dir(dirpath, filenames)
            if compose_files and len(compose) < MAX_COMPOSE_PROJECTS:
                project = _build_compose_project(dirpath, compose_files, owner)
                compose.append(project)
                build_refs.update(
                    _compose_build_refs(dirpath, project.name, compose_files)
                )
            elif compose_files:
                logger.warning("Docker scan compose list is capped at %d", MAX_COMPOSE_PROJECTS)

            for filename in filenames:
                if not _is_dockerfile_filename(filename):
                    continue
                path = os.path.join(dirpath, filename)
                real_path = _real(path)
                if real_path in seen_files or not os.path.isfile(path):
                    continue
                if len(dockerfiles) >= MAX_DOCKERFILES:
                    logger.warning(
                        "Docker scan Dockerfile list is capped at %d", MAX_DOCKERFILES
                    )
                    break
                seen_files.add(real_path)
                base_images, stages = _parse_dockerfile(path)
                dockerfiles.append(
                    DockerfileAsset(
                        name=filename,
                        path=path,
                        directory=dirpath,
                        relative_path=_relative_to(path, owner),
                        context=dirpath,
                        project=owner.project,
                        project_root=owner.path,
                        base_images=base_images,
                        stages=stages,
                        stage_count=len(base_images),
                        has_dockerignore=os.path.isfile(
                            os.path.join(dirpath, ".dockerignore")
                        ),
                    )
                )

    # Compose may live in a parent directory and reference a Dockerfile in a
    # child one: apply the build: metadata after the whole walk.
    for dockerfile in dockerfiles:
        reference = build_refs.get(_real(dockerfile.path))
        if not reference:
            continue
        project_name, service, context = reference
        dockerfile.compose_project = project_name
        dockerfile.compose_service = service
        if os.path.isdir(context):
            dockerfile.context = context
            dockerfile.has_dockerignore = os.path.isfile(
                os.path.join(context, ".dockerignore")
            )

    compose.sort(key=lambda item: (item.name, item.directory))
    dockerfiles.sort(key=lambda item: item.relative_path)
    return ScanResult(
        compose=compose, dockerfiles=dockerfiles, scanned_at=_now_iso()
    )


def invalidate_scan_cache() -> None:
    """Drop every cached scan (used by tests and by a forced refresh)."""
    with _scan_lock:
        _scan_cache.clear()


# ── Action target validation ──────────────────────────────────────────────────


def resolve_compose_target(
    path: str, roots: Sequence[ScanRoot]
) -> Optional[ComposeProject]:
    """
    Validate a compose path supplied by an action request.

    The path must be an existing compose file inside one of the project roots.
    The returned project carries the same file grouping a scan would produce,
    so ``docker compose -f … -f …`` receives the base and its override.

    Args:
        path: Compose file path from the request.
        roots: Allowed project roots.

    Returns:
        The resolved project, or ``None`` when the path is not a project compose
        file (the caller answers 404/400).
    """
    normalized = normalize_scan_roots(roots)
    if not path or not normalized:
        return None

    target = _abs(path)
    if not os.path.isfile(target) or not _is_compose_filename(os.path.basename(target)):
        return None
    owner = _owner_root(target, normalized)
    if not owner:
        return None

    directory = os.path.dirname(target)
    files = _compose_files_for_dir(directory)
    if _real(target) not in {_real(item) for item in files}:
        return None
    return _build_compose_project(directory, files, owner)


def resolve_dockerfile_target(
    path: str, roots: Sequence[ScanRoot]
) -> Optional[DockerfileAsset]:
    """
    Validate a Dockerfile path and return its scanned record.

    The Dockerfile must be part of the current project scan (which also gives
    it the correct build context when a compose ``build:`` section references
    it). A forced rescan is used so a just-created file is honoured.

    Args:
        path: Dockerfile path from the request.
        roots: Allowed project roots.

    Returns:
        The asset, or ``None`` when it is not a Dockerfile inside the roots.
    """
    normalized = normalize_scan_roots(roots)
    if not path or not normalized:
        return None
    target = _abs(path)
    if not os.path.isfile(target) or not _is_dockerfile_filename(
        os.path.basename(target)
    ):
        return None
    if not is_path_within_roots(target, normalized):
        return None

    result = scan_project_docker(normalized, force=True)
    target_real = _real(target)
    for asset in result.dockerfiles:
        if _real(asset.path) == target_real:
            return asset
    return None

# Made with ❤️ by codx-junior
