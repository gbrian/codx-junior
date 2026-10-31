"""
Console API router.

Thin HTTP layer over :class:`~codx.junior.console_manager.ConsoleManager`, which
owns the access rules, the working-directory scoping and the execution itself.

Access model
------------
* Authenticated users may run commands **inside their projects**: the working
  directory is validated against the projects the user has access to, so a
  command can never traverse outside of them.
* Users with the ``admin`` role have **no restrictions**: they may run any
  command from any working directory (a project session is not even required).

Route layout
------------
GET  /api/console/info      – current project path + caller capabilities
POST /api/console/execute   – run a command and return stdout/stderr/exit code

```mermaid
flowchart TD
    A[POST /api/console/execute] --> B[ConsoleManager.execute]
    B --> C{ConsoleError?}
    C -- auth --> D[401]
    C -- validation --> E[400]
    C -- access denied --> F[403]
    C -- execution --> G[500]
    C -- no --> H[stdout, stderr, exit_code]
```
"""

import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from codx.junior.console_manager import ConsoleError, ConsoleManager
from codx.junior.engine import CODXJuniorSession
from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/console", tags=["console"])

# ── Request models ─────────────────────────────────────────────────────────────


class ConsoleCommand(BaseModel):
    """Payload for a console command execution."""

    command: str
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    timeout: Optional[int] = None


# ── Helpers ────────────────────────────────────────────────────────────────────


def _get_optional_session(request: Request) -> Optional[CODXJuniorSession]:
    """
    Return the active session attached to the request state, if any.

    Args:
        request: The incoming HTTP request.

    Returns:
        The ``CODXJuniorSession`` when a project context was resolved by the
        middleware, otherwise ``None``.
    """
    return getattr(request.state, "codx_junior_session", None)


def _get_manager(request: Request) -> ConsoleManager:
    """
    Build a ConsoleManager for the request project context.

    Args:
        request: The incoming HTTP request.

    Returns:
        A ``ConsoleManager`` bound to the request project (if any).
    """
    session = _get_optional_session(request)
    return ConsoleManager(settings=session.settings if session else None)


def _raise_http_error(ex: ConsoleError) -> None:
    """
    Translate a ConsoleError into an HTTPException.

    Args:
        ex: Error raised by the console manager.

    Raises:
        HTTPException: Always, with the status code carried by the error.
    """
    logger.warning("Console error (%s): %s", ex.status_code, ex.detail)
    raise HTTPException(status_code=ex.status_code, detail=ex.detail) from ex


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/info", summary="Console context for the current caller")
def console_info(
    request: Request,
    user: CodxUser = Depends(get_authenticated_user),
) -> dict:
    """
    Return the console context for the current caller.

    The client uses this to know whether the caller is unrestricted (admin) and
    which project roots are available.

    Returns:
        Dict with 'username', 'role', 'unrestricted', 'project_path',
        'allowed_roots', 'default_timeout' and 'max_timeout'.
    """
    try:
        return _get_manager(request).info(user=user)
    except ConsoleError as ex:
        _raise_http_error(ex)


@router.post("/execute", summary="Execute a shell command")
def console_execute(
    payload: ConsoleCommand,
    request: Request,
    user: CodxUser = Depends(get_authenticated_user),
) -> dict:
    """
    Execute a shell command on the host.

    Non-admin users can only run commands inside their projects (the working
    directory is validated). Admin users have no restrictions and may target
    any directory, with or without an active project session.

    Args:
        payload: Command, optional working directory, extra environment and
            timeout.
        request: Incoming HTTP request carrying the session in its state.
        user: The authenticated user performing the request.

    Returns:
        Dict with 'command', 'cwd', 'user', 'unrestricted', 'timeout', 'stdout',
        'stderr', 'exit_code' and 'timed_out'.

    Raises:
        HTTPException 400: When the command is empty, the session is missing for
            a non-admin, or the working directory does not exist.
        HTTPException 401: When the request is not authenticated.
        HTTPException 403: When a non-admin targets a path outside their
            projects.
        HTTPException 500: When the command cannot be started.
    """
    try:
        return _get_manager(request).execute(
            command=payload.command,
            cwd=payload.cwd,
            env=payload.env,
            timeout=payload.timeout,
            user=user,
        )
    except ConsoleError as ex:
        _raise_http_error(ex)

# Made with ❤️ by codx-junior