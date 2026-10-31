"""
Console manager for codx-junior.

Centralizes everything related to running shell commands on the host: command
validation, working-directory resolution and project scoping, timeouts,
environment merging and output capture.

Consumers (API routers, engines, tools) must go through :class:`ConsoleManager`
instead of calling ``subprocess`` / ``exec_command`` directly, so the access
rules and the result shape stay consistent.

Access model
------------
* ``admin`` users have no restrictions: any command, any working directory, a
  project context is not even required.
* Any other authenticated user is confined to the real paths of the projects
  they have access to (the current project is always included).

```mermaid
flowchart TD
    A[ConsoleManager.execute] --> B{user?}
    B -- no --> C[ConsoleAuthError 401]
    B -- yes --> D{command empty?}
    D -- yes --> E[ConsoleValidationError 400]
    D -- no --> F{role == admin?}
    F -- yes --> G[cwd = requested or project or cwd]
    F -- no --> H{project session?}
    H -- no --> I[ConsoleValidationError 400]
    H -- yes --> J{cwd inside allowed_roots?}
    J -- no --> K[ConsoleAccessDeniedError 403]
    J -- yes --> L[cwd = resolved]
    G --> M[cwd exists?]
    L --> M
    M -- no --> N[ConsoleValidationError 400]
    M -- yes --> O[subprocess.run shell timeout]
    O --> P[stdout, stderr, exit_code, timed_out]
```

Made with ❤️ by codx-junior
"""

import logging
import os
import subprocess
from typing import TYPE_CHECKING, Dict, List, Optional

from codx.junior.model.model import CodxUser

if TYPE_CHECKING:
    from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 300


# ── Errors ─────────────────────────────────────────────────────────────────────


class ConsoleError(Exception):
    """
    Base exception for console operations.

    Carries the ``status_code`` the API layer should map the error to, so
    routers do not need to translate every failure case individually.
    """

    status_code = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ConsoleAuthError(ConsoleError):
    """Raised when the caller is not authenticated."""

    status_code = 401


class ConsoleValidationError(ConsoleError):
    """Raised when the request payload or target directory is invalid."""

    status_code = 400


class ConsoleAccessDeniedError(ConsoleError):
    """Raised when a non-admin targets a path outside their projects."""

    status_code = 403


class ConsoleExecutionError(ConsoleError):
    """Raised when the command cannot be started."""

    status_code = 500


class ConsoleManager:
    """
    Runs shell commands on behalf of a user, enforcing the access model.

    The project context is optional: admins may operate without one, while any
    other user requires a project to be scoped to.
    """

    def __init__(
        self,
        settings: Optional["CODXJuniorSettings"] = None,
        user: Optional[CodxUser] = None,
    ) -> None:
        """
        Initialize the manager.

        Args:
            settings: Settings of the project the commands run in (may be
                ``None`` for admins).
            user: Default user for the operations; can be overridden per call.
        """
        self.settings = settings
        self.user = user

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    @property
    def project_path(self) -> Optional[str]:
        """Return the absolute path of the project, or ``None`` without one."""
        return self.settings.abs_project_path if self.settings else None

    @staticmethod
    def is_admin(user: Optional[CodxUser]) -> bool:
        """
        Return True when the user has the ``admin`` role.

        Args:
            user: User to check (may be ``None``).

        Returns:
            True for unrestricted users.
        """
        return bool(user and user.role == "admin")

    def _require_user(self, user: Optional[CodxUser]) -> CodxUser:
        """
        Resolve the user for the operation.

        Args:
            user: Explicit user, or ``None`` to fall back to ``self.user``.

        Returns:
            The authenticated user.

        Raises:
            ConsoleAuthError: When no user is available.
        """
        user = user or self.user
        if not user:
            raise ConsoleAuthError("Authentication required")
        return user

    def _is_path_within(self, abs_path: str, root_path: str) -> bool:
        """
        Check that ``abs_path`` is ``root_path`` itself or a descendant of it.

        Separator-aware, so sibling roots sharing a prefix (``/app`` and
        ``/app-2``) are never confused.

        Args:
            abs_path: Absolute path to test.
            root_path: Absolute root to test against.

        Returns:
            True when the path belongs to the root tree.
        """
        if not abs_path or not root_path:
            return False
        abs_path = os.path.normpath(abs_path)
        root_path = os.path.normpath(root_path)
        return abs_path == root_path or abs_path.startswith(root_path + os.sep)

    def allowed_roots(self, user: Optional[CodxUser] = None) -> List[str]:
        """
        Return the real paths of every project the user may run commands in.

        The current project is always included so a user can always operate
        inside the project they are viewing (mirrors the file engine rules).

        Args:
            user: User to resolve the projects for (defaults to ``self.user``).

        Returns:
            Sorted list of absolute, real project paths.
        """
        from codx.junior.project.project_discover import find_all_user_projects

        user = user or self.user
        roots = set()
        if user:
            try:
                roots = {
                    os.path.realpath(project.abs_project_path)
                    for project in find_all_user_projects(user)
                }
            except Exception as ex:  # pragma: no cover - defensive
                logger.warning(
                    "Could not resolve projects for user '%s': %s",
                    getattr(user, "username", "?"),
                    ex,
                )

        if self.project_path:
            roots.add(os.path.realpath(self.project_path))

        return sorted(roots)

    def info(self, user: Optional[CodxUser] = None) -> dict:
        """
        Return the console context for a caller.

        Args:
            user: Caller (defaults to ``self.user``).

        Returns:
            Dict with 'username', 'role', 'unrestricted', 'project_path',
            'allowed_roots', 'default_timeout' and 'max_timeout'.

        Raises:
            ConsoleAuthError: When no user is available.
        """
        user = self._require_user(user)
        admin = self.is_admin(user)
        return {
            "username": user.username,
            "role": user.role,
            "unrestricted": admin,
            "project_path": self.project_path,
            "allowed_roots": None if admin else self.allowed_roots(user=user),
            "default_timeout": DEFAULT_TIMEOUT_SECONDS,
            "max_timeout": MAX_TIMEOUT_SECONDS,
        }

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    def clamp_timeout(self, timeout: Optional[int]) -> int:
        """
        Clamp the requested timeout into the allowed range.

        Args:
            timeout: Requested timeout in seconds (may be ``None``).

        Returns:
            Timeout between ``1`` and ``MAX_TIMEOUT_SECONDS`` seconds.
        """
        if not timeout:
            return DEFAULT_TIMEOUT_SECONDS
        return max(1, min(int(timeout), MAX_TIMEOUT_SECONDS))

    def resolve_cwd(
        self, cwd: Optional[str] = None, user: Optional[CodxUser] = None
    ) -> str:
        """
        Resolve the working directory the command will run in.

        Admins are unrestricted. Any other user is confined to the real paths of
        the projects they have access to.

        Args:
            cwd: Optional working directory (relative or absolute).
            user: Caller (defaults to ``self.user``).

        Returns:
            Absolute, real working directory path.

        Raises:
            ConsoleAuthError: When no user is available.
            ConsoleValidationError: When a non-admin has no project context.
            ConsoleAccessDeniedError: When a non-admin targets a path outside
                their projects.
        """
        user = self._require_user(user)

        if self.is_admin(user):
            target = cwd or self.project_path or os.getcwd()
            if not os.path.isabs(target):
                target = os.path.join(self.project_path or os.getcwd(), target)
            return os.path.realpath(target)

        # Non-admins are always tied to a project.
        if not self.project_path:
            raise ConsoleValidationError(
                "CODXJuniorSession not found in request state."
            )

        requested = cwd or self.project_path
        if not os.path.isabs(requested):
            requested = os.path.join(self.project_path, requested)
        resolved = os.path.realpath(requested)

        for root in self.allowed_roots(user=user):
            if self._is_path_within(resolved, root):
                return resolved

        logger.warning(
            "User '%s' attempted to run a command outside their projects: %s",
            user.username,
            resolved,
        )
        raise ConsoleAccessDeniedError(
            "Command execution is restricted to your projects. "
            "The admin role is required for unrestricted access."
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _build_env(self, env: Optional[Dict[str, str]]) -> Dict[str, str]:
        """
        Build the environment for the process.

        Args:
            env: Extra variables merged over the current process environment.

        Returns:
            Complete environment dictionary.
        """
        full_env = os.environ.copy()
        if env:
            full_env.update({str(key): str(value) for key, value in env.items()})
        return full_env

    def _run_process(
        self,
        command: str,
        cwd: str,
        env: Optional[Dict[str, str]],
        timeout: int,
    ) -> dict:
        """
        Run a shell command and capture its output.

        Args:
            command: Shell command line.
            cwd: Working directory (must exist).
            env: Extra environment variables.
            timeout: Maximum execution time in seconds.

        Returns:
            Dict with 'stdout', 'stderr', 'exit_code' and 'timed_out'.

        Raises:
            ConsoleExecutionError: When the process cannot be started.
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=self._build_env(env),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            return {
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "exit_code": result.returncode,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as ex:
            stdout = ex.stdout or ""
            stderr = ex.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": None,
                "timed_out": True,
            }
        except Exception as ex:  # pragma: no cover - defensive
            logger.exception("Error executing command: %s", ex)
            raise ConsoleExecutionError(f"Error executing command: {ex}") from ex

    def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        user: Optional[CodxUser] = None,
    ) -> dict:
        """
        Validate, scope and run a shell command.

        Args:
            command: Shell command line.
            cwd: Optional working directory (relative or absolute).
            env: Extra environment variables merged over the process env.
            timeout: Optional timeout in seconds (clamped).
            user: Caller (defaults to ``self.user``).

        Returns:
            Dict with 'command', 'cwd', 'user', 'unrestricted', 'timeout',
            'stdout', 'stderr', 'exit_code' and 'timed_out'.

        Raises:
            ConsoleAuthError: When no user is available.
            ConsoleValidationError: When the command is empty, there is no
                project context for a non-admin, or the directory is missing.
            ConsoleAccessDeniedError: When a non-admin targets a path outside
                their projects.
            ConsoleExecutionError: When the process cannot be started.
        """
        user = self._require_user(user)

        command = (command or "").strip()
        if not command:
            raise ConsoleValidationError("Field 'command' must not be empty.")

        resolved_cwd = self.resolve_cwd(cwd=cwd, user=user)
        if not os.path.isdir(resolved_cwd):
            raise ConsoleValidationError(
                f"Working directory not found: {resolved_cwd}"
            )

        timeout = self.clamp_timeout(timeout)
        admin = self.is_admin(user)

        logger.info(
            "User '%s' (admin=%s) running console command in '%s': %s",
            user.username,
            admin,
            resolved_cwd,
            command,
        )

        output = self._run_process(command, resolved_cwd, env, timeout)

        logger.info(
            "Console command finished (exit=%s, timed_out=%s) for user '%s'",
            output["exit_code"],
            output["timed_out"],
            user.username,
        )

        return {
            "command": command,
            "cwd": resolved_cwd,
            "user": user.username,
            "unrestricted": admin,
            "timeout": timeout,
            **output,
        }

# Made with ❤️ by codx-junior