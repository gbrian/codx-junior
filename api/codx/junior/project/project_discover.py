import os
import logging
import subprocess
from datetime import datetime, timedelta
from threading import Thread
from typing import Dict, Generator, List, Optional

from codx.junior.profiling.profiler import profile_function
from codx.junior.security.user_management import UserSecurityManager
from codx.junior.settings import CODXJuniorSettings, CODXJuniorProject
from codx.junior.model.model import CodxUser
from codx.junior.global_settings import read_global_settings

logger = logging.getLogger(__name__)

_ALL_PROJECTS: Optional[Dict[str, CODXJuniorSettings]] = None
_ALL_PROJECTS_PROC: Optional[Thread] = None


def get_projects_root_path() -> str:
    """
    Return the root path under which all projects are stored.

    Reads from global settings first, then falls back to the
    ``CODX_JUNIOR_PROJECTS_PATH`` environment variable, and finally
    defaults to ``~/projects``.

    Returns:
        Absolute path string for the projects root directory.
    """
    global_settings = read_global_settings()
    return (
        global_settings.projects_root_path
        or os.environ.get("CODX_JUNIOR_PROJECTS_PATH")
        or f"{os.environ['HOME']}/projects"
    )


def is_path_child_of(child_path: str, parent_path: str) -> bool:
    """
    Return True only when ``child_path`` is a genuine subdirectory of ``parent_path``.

    Uses ``os.path.commonpath`` to avoid false positives caused by shared string
    prefixes (e.g. ``/home/foo-projects/bar`` vs ``/home/foo``).

    Args:
        child_path:  Absolute path that may be a child.
        parent_path: Absolute path of the candidate parent directory.

    Returns:
        True if child_path is strictly inside parent_path, False otherwise.

    Examples:
        >>> is_path_child_of('/home/projects/foo/sub', '/home/projects/foo')
        True
        >>> is_path_child_of('/home/projects/foobar', '/home/projects/foo')
        False
        >>> is_path_child_of('/home/projects/foo', '/home/projects/foo')
        False
    """
    # Normalise both paths to remove any trailing slashes / double separators
    child_path = os.path.normpath(child_path)
    parent_path = os.path.normpath(parent_path)

    if child_path == parent_path:
        return False

    try:
        common = os.path.commonpath([child_path, parent_path])
    except ValueError:
        # commonpath raises ValueError on mixed absolute/relative on Windows
        return False

    return common == parent_path


def find_all_projects(force: bool = False) -> Dict[str, CODXJuniorSettings]:
    """
    Return a mapping of project_id → CODXJuniorSettings for all discovered projects.

    Discovery runs in a background thread on the first call (or when ``force``
    is True).  Subsequent calls return the cached result immediately unless
    a refresh is forced.

    Args:
        force: When True, trigger a fresh discovery scan even if results are cached.

    Returns:
        Dictionary mapping project_id to CODXJuniorSettings.
    """
    global _ALL_PROJECTS_PROC
    global _ALL_PROJECTS

    if not _ALL_PROJECTS_PROC or force:
        _ALL_PROJECTS_PROC = Thread(target=_update_all_projects)
        _ALL_PROJECTS_PROC.start()

    if not _ALL_PROJECTS and _ALL_PROJECTS_PROC:
        logger.info("Waiting for _ALL_PROJECTS_PROC to finish discovery.")
        _ALL_PROJECTS_PROC.join(timeout=60)

    return _ALL_PROJECTS


def find_project_from_file_path(file_path: str) -> Optional[CODXJuniorSettings]:
    """
    Given an absolute file path, return the most-specific project that contains it.

    When multiple projects match (nested projects), the one with the longest
    ``abs_project_path`` (i.e. the deepest / most specific) is returned.

    Args:
        file_path: Absolute path to a file.

    Returns:
        The matching CODXJuniorSettings, or None if no project matches.
    """
    all_projects = find_all_projects().values()
    matches = [
        p for p in all_projects
        if is_path_child_of(file_path, p.abs_project_path)
        or is_path_child_of(file_path, p.codx_path)
    ]
    if matches:
        logger.info(
            "Find projects for file %s: %s",
            file_path,
            [m.project_name for m in matches],
        )
        return sorted(matches, key=lambda p: len(p.abs_project_path))[-1]
    return None


def find_project_by_id(project_id: str) -> Optional[CODXJuniorSettings]:
    """
    Look up a project by its unique identifier.

    Args:
        project_id: The project UUID string.

    Returns:
        Matching CODXJuniorSettings, or None if not found.
    """
    all_projects = find_all_projects().values()
    matches = [p for p in all_projects if p.project_id == project_id]
    return matches[0] if matches else None


def find_project_by_project_path(project_path: str) -> Optional[CODXJuniorSettings]:
    """
    Look up a project by its absolute filesystem path.

    Args:
        project_path: Absolute path to the project root.

    Returns:
        Matching CODXJuniorSettings, or None if not found.
    """
    all_projects = find_all_projects().values()
    matches = [p for p in all_projects if p.abs_project_path == project_path]
    return matches[0] if matches else None


def find_project_by_name(project_name: str) -> Optional[CODXJuniorSettings]:
    """
    Look up a project by its display name.

    Args:
        project_name: Human-readable project name.

    Returns:
        Matching CODXJuniorSettings, or None if not found.
    """
    all_projects = find_all_projects().values()
    matches = [p for p in all_projects if p.project_name == project_name]
    project = matches[0] if matches else None
    if not project:
        logger.warning("find_project_by_name '%s' not found", project_name)
    return project


def find_all_user_projects(user: CodxUser) -> Generator[CODXJuniorProject, None, None]:
    """
    Yield all projects accessible to the given user.

    For each project, the permission walk climbs parent projects until an
    authorised ancestor is found.  If no ancestor grants access, the project
    is skipped.

    Args:
        user: The authenticated user whose permissions are checked.

    Yields:
        CODXJuniorProject instances enriched with permission information.
    """
    user_security_manager = UserSecurityManager()
    all_projects = list(find_all_projects().values())

    def find_parent(project_path: str) -> Optional[CODXJuniorSettings]:
        """Return the most-specific parent project for the given path."""
        all_parents = [
            p for p in all_projects
            if is_path_child_of(project_path, p.abs_project_path)
        ]
        all_parents.sort(key=lambda p: len(p.abs_project_path))
        return all_parents[-1] if all_parents else None

    for settings in all_projects:
        current_settings: Optional[CODXJuniorSettings] = settings
        while current_settings:
            permissions = user_security_manager.get_user_project_access(
                user=user, settings=current_settings
            )
            if permissions:
                yield CODXJuniorProject(**{
                    **settings.__dict__,
                    "permissions": permissions,
                })
                current_settings = None
            else:
                current_settings = find_parent(current_settings.abs_project_path)


def get_project_dependencies(settings: CODXJuniorSettings) -> List[CODXJuniorSettings]:
    """
    Return all projects that the given project depends on.

    This includes:
    - Child/sub-projects declared in ``settings.get_sub_projects()``.
    - Explicitly linked dependency projects from ``settings.get_project_dependencies()``.

    Unresolvable project names are silently omitted (``find_project_by_name``
    returns None and the list comprehension filters those out).

    Args:
        settings: The project whose dependencies should be resolved.

    Returns:
        List of resolved CODXJuniorSettings for all dependency projects.
    """
    project_child_projects: List[Optional[CODXJuniorSettings]] = [
        find_project_by_name(project.project_name)
        for project in settings.get_sub_projects()
    ]
    project_dependencies: List[Optional[CODXJuniorSettings]] = [
        find_project_by_name(project_name)
        for project_name in settings.get_project_dependencies()
    ]

    # Filter out any None values from projects that could not be resolved
    resolved = [p for p in project_child_projects + project_dependencies if p is not None]

    logger.info(
        "get_project_dependencies for '%s': resolved %d dependencies.",
        settings.project_name,
        len(resolved),
    )
    return resolved


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

@profile_function
def _update_all_projects() -> None:
    """
    Background worker that scans the filesystem for all ``.codx/project.json``
    files and populates the global ``_ALL_PROJECTS`` cache.

    Diagram:
    flowchart TD
        A[_update_all_projects] --> B[find / -name .codx]
        B --> C[Filter paths with project.json]
        C --> D{R/W permissions?}
        D -- No --> E[Skip path]
        D -- Yes --> F[Parse CODXJuniorSettings]
        F --> G{Valid project?}
        G -- Yes --> H[Register in all_projects dict]
        G -- No  --> I[Log and skip]
        H --> J[_ALL_PROJECTS = all_projects]
    """
    global _ALL_PROJECTS_PROC
    global _ALL_PROJECTS

    all_projects: Dict[str, CODXJuniorSettings] = {}
    projects_root_path = get_projects_root_path()
    user_security_manager = UserSecurityManager()

    result = subprocess.run(
        ["find", "/", "-name", ".codx"],
        cwd="/",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    all_codx_paths = result.stdout.decode("utf-8").split("\n")
    paths = [p for p in all_codx_paths if os.path.isfile(f"{p}/project.json")]

    logger.info("[find_all_projects] projects root path: %s", projects_root_path)
    logger.info("[find_all_projects] found %d project files", len(paths))

    def is_valid_project(candidate: CODXJuniorSettings) -> bool:
        """
        Return True when the candidate project should be added to the registry.

        Duplicates that live outside the configured root are rejected in favour
        of the canonical copy inside the root.
        """
        if not candidate or not candidate.project_name:
            return False
        existing_project = all_projects.get(candidate.project_id)
        if existing_project:
            if not is_path_child_of(candidate.abs_project_path, projects_root_path):
                # Prefer projects inside the configured root on duplicates
                return False
        return True

    for codx_path in paths:
        try:
            project_file_path = f"{codx_path}/project.json"
            # Verify that the process has read/write access before loading
            if not (
                os.access(project_file_path, os.R_OK)
                and os.access(project_file_path, os.W_OK)
            ):
                logger.warning(
                    "Skipping %s due to insufficient permissions.", project_file_path
                )
                continue

            settings = CODXJuniorProject(
                **CODXJuniorSettings.from_project_file(project_file_path).__dict__
            )
            if is_valid_project(settings):
                project_users = user_security_manager.get_users_with_project_access(
                    project_id=settings.project_id
                )
                settings.users = project_users
                all_projects[settings.project_id] = settings
            else:
                logger.error(
                    "Invalid or duplicate project at: %s", settings.abs_project_path
                )
        except Exception as exc:
            logger.exception("Error loading project %s: %s", codx_path, exc)

    _ALL_PROJECTS = all_projects
    _ALL_PROJECTS_PROC = None


def find_project_parents(
    project: CODXJuniorSettings,
    user: Optional[CodxUser] = None,
) -> List[CODXJuniorSettings]:
    """
    Return all ancestor projects for the given project, ordered from root to leaf.

    When a ``user`` is provided only projects accessible to that user are
    considered as potential ancestors.

    Args:
        project: The project whose ancestors should be found.
        user:    Optional user for permission-filtered ancestor discovery.

    Returns:
        List of ancestor CODXJuniorSettings sorted by path length (shallowest first).
    """
    all_candidates = (
        list(find_all_user_projects(user))
        if user
        else list(find_all_projects().values())
    )
    project_path = project.abs_project_path
    all_parents = [
        p for p in all_candidates
        if is_path_child_of(project_path, p.abs_project_path)
    ]
    return sorted(all_parents, key=lambda p: len(p.abs_project_path))


def find_active_projects() -> List[CODXJuniorSettings]:
    """
    Return all projects that have been accessed within the last 30 minutes.

    Returns:
        List of recently active CODXJuniorSettings instances.
    """
    last_access = datetime.now() - timedelta(minutes=30)
    return [
        p for p in find_all_projects().values()
        if getattr(p, "last_access_time", None)
        and p.last_access_time >= str(last_access)
    ]

# Made with ❤️ by codx-junior