"""
Project-scoped filesystem checks for harness execution.

A harness is an external process with its own filesystem view. The host must
never ask it to work outside the project that owns the task, and a harness
event must never be allowed to attach a task from another project.

This module is deliberately small and dependency free: it is the single place
where the "is this path inside the project?" question is answered. It uses
``realpath`` so a symlink cannot escape the project root.

OS-level isolation remains a deployment concern: run the harness with only the
project workspace mounted (the DSH service already does this). These checks are
the application-level guard and the contract the plugin validates before it
starts a session.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional


class HarnessSandboxError(ValueError):
    """A harness path is outside the project workspace."""


def project_root(settings: Any) -> str:
    """
    Resolve the physical root of the project that owns *settings*.

    Priority mirrors :class:`DshConfig`: explicit project path, then the parent
    of ``codx_path``. The returned path is absolute and symlink-resolved.
    """
    root = (
        getattr(settings, "abs_project_path", None)
        or getattr(settings, "project_path", None)
        or (
            os.path.dirname(getattr(settings, "codx_path", "") or "")
            if getattr(settings, "codx_path", None)
            else None
        )
        or os.getcwd()
    )
    return os.path.realpath(str(root))


def is_path_within(path: Optional[str], root: Optional[str]) -> bool:
    """
    Return True when *path* resolves inside *root*.

    Empty paths are treated as "not provided"; callers that allow an omitted
    cwd should check that separately. The comparison is case-normalized for
    platforms with case-insensitive paths.
    """
    if not path or not root:
        return False
    try:
        target = os.path.realpath(str(path))
        base = os.path.realpath(str(root))
        return os.path.commonpath(
            [os.path.normcase(target), os.path.normcase(base)]
        ) == os.path.normcase(base)
    except (OSError, ValueError):
        return False


def ensure_within_project(
    path: Optional[str],
    root: str,
    *,
    field: str = "path",
    must_exist: bool = False,
) -> str:
    """
    Validate and return *path* resolved inside *root*.

    Args:
        path: Candidate path. ``None`` or an empty string resolves to *root*.
        root: Project root.
        field: Field name used in the error message.
        must_exist: When True the resolved path must be an existing directory.

    Raises:
        HarnessSandboxError: The path escapes the project, or does not exist
            when ``must_exist`` is set.
    """
    base = os.path.realpath(str(root))
    target = os.path.realpath(str(path or base))
    if not is_path_within(target, base):
        raise HarnessSandboxError(
            f"{field} '{target}' is outside the project workspace '{base}'"
        )
    if must_exist and not os.path.isdir(target):
        raise HarnessSandboxError(f"{field} '{target}' is not an existing directory")
    return target


def ensure_project_cwd(path: Optional[str], settings: Any) -> str:
    """Validate a task cwd against the project that owns *settings*."""
    return ensure_within_project(
        path,
        project_root(settings),
        field="cwd",
        must_exist=True,
    )


def workspace_roots(settings: Any) -> List[str]:
    """Return the physical workspace roots a harness may be granted."""
    root = project_root(settings)
    return [root]
