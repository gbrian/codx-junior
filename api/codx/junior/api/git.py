"""
Git repository API.

Exposes the repository management endpoints consumed by the git view:

- Read: repository info, branches, commits, working tree status,
  two-branch comparison (PR review) and single file diff/history.
- Write: fetch, pull, push, create/checkout/delete branch, stage/unstage/
  discard files, commit and merge.

All operations are delegated to
:class:`codx.junior.engine.git_workspace.GitWorkspaceEngine` (a
:class:`codx.junior.engine.git_engine.GitEngine` with file level operations).
Routes are mounted under ``/api`` by the dynamic router loader
(``codx.junior.api.discover_routers``), so the final paths look like
``/api/git/repo/branches``.

```mermaid
sequenceDiagram
    participant UI as GitView
    participant API as git router
    participant Engine as GitWorkspaceEngine
    participant Git as git CLI

    UI->>API: POST /api/git/repo/stage { paths }
    API->>Engine: stage_files(paths)
    Engine->>Git: git add -A -- <paths>
    Git-->>Engine: ok
    Engine-->>API: { success, paths }
    API-->>UI: 200 result | 400 { detail }
```

Made with ❤️ by codx-junior
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from codx.junior.engine.git_workspace import GitWorkspaceEngine
from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter()


# -----------------------------------------------------------------------------
# Request models
# -----------------------------------------------------------------------------


class CreateBranchRequest(BaseModel):
    """Payload to create a branch."""

    branch: str
    from_branch: Optional[str] = None
    checkout: bool = False


class CheckoutBranchRequest(BaseModel):
    """Payload to check out a branch."""

    branch: str


class CommitRequest(BaseModel):
    """Payload to commit the working tree changes."""

    message: str
    stage_all: bool = True
    allow_empty: bool = False


class MergeRequest(BaseModel):
    """Payload to merge one branch into another."""

    from_branch: str
    to_branch: Optional[str] = None
    message: Optional[str] = None
    delete_branch: bool = False


class FilePathsRequest(BaseModel):
    """Payload for bulk operations over a set of working tree files."""

    paths: List[str]
    include_staged: bool = True


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _git_engine(request: Request) -> GitWorkspaceEngine:
    """
    Build a GitWorkspaceEngine for the active project session.

    Args:
        request: Incoming HTTP request holding the session in its state.

    Returns:
        Engine bound to the request session.

    Raises:
        HTTPException: 400 when the request has no project session.
    """
    session = getattr(request.state, "codx_junior_session", None)
    if not session:
        raise HTTPException(
            status_code=400,
            detail="CODXJuniorSession not found in request state.",
        )
    return GitWorkspaceEngine(session=session)


def _ensure_success(result: dict) -> dict:
    """
    Raise a 400 HTTP error when a git operation failed.

    Args:
        result: Operation result dict with 'success' and 'errors'.

    Returns:
        The same result when the operation succeeded.

    Raises:
        HTTPException: 400 with the git error messages joined.
    """
    if not result.get("success"):
        errors = [e for e in (result.get("errors") or []) if e]
        detail = "; ".join(str(e) for e in errors) or "Git operation failed"
        raise HTTPException(status_code=400, detail=detail)
    return result


# -----------------------------------------------------------------------------
# Read endpoints
# -----------------------------------------------------------------------------


@router.get("/git/repo/info")
def api_git_repo_info(
    request: Request, user: CodxUser = Depends(get_authenticated_user)
):
    """
    Return a summary of the repository state.

    Includes the active/default branch, remote URL, ahead/behind counters,
    working tree state (staged and unstaged file lists) and the last commit.
    """
    return _git_engine(request).get_repo_info()


@router.get("/git/repo/status")
def api_git_repo_status(
    request: Request, user: CodxUser = Depends(get_authenticated_user)
):
    """Return the working tree status (dirty flag, staged and unstaged files)."""
    return _git_engine(request).get_repo_status()


@router.get("/git/repo/branches")
def api_git_repo_branches(
    request: Request, user: CodxUser = Depends(get_authenticated_user)
):
    """Return the branch list plus the repo tree (branches with commits)."""
    return _git_engine(request).get_project_branches()


@router.get("/git/repo/branch/commits")
def api_git_repo_branch_commits(
    request: Request,
    branch: Optional[str] = Query(None, description="Branch name, defaults to HEAD"),
    limit: int = Query(50, ge=1, le=500),
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Return the commit history of a branch.

    Args:
        branch: Branch name. Defaults to the current HEAD.
        limit: Maximum number of commits returned.
    """
    commits = _git_engine(request).get_commit_list(branch=branch, limit=limit)
    return {"branch": branch or "HEAD", "commits": commits}


@router.get("/git/repo/commits")
def api_git_repo_commits(
    request: Request,
    branch: Optional[str] = Query(None, description="Branch name, defaults to HEAD"),
    limit: int = Query(50, ge=1, le=500),
    user: CodxUser = Depends(get_authenticated_user),
):
    """Alias of ``/git/repo/branch/commits`` returning a flat commit list."""
    return _git_engine(request).get_commit_list(branch=branch, limit=limit)


@router.get("/git/repo/changes")
def api_git_repo_changes(
    request: Request,
    from_branch: str = Query(..., description="Source branch (PR branch)"),
    to_branch: str = Query(..., description="Target branch (base)"),
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Compare two branches and return the PR review payload.

    Args:
        from_branch: Source branch.
        to_branch: Target/base branch.
    """
    return _git_engine(request).get_repo_changes(
        from_branch=from_branch, to_branch=to_branch
    )


@router.get("/git/repo/file/diff")
def api_git_repo_file_diff(
    request: Request,
    path: str = Query(..., description="File path (relative or absolute)"),
    staged: bool = Query(False, description="Diff the staged (index) changes"),
    commit: Optional[str] = Query(None, description="Commit hash to diff"),
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Return the diff of a single file.

    Sources, in precedence order: the given ``commit``, the staged changes
    (``staged=true``) or the working tree. Untracked files get a synthetic
    "new file" diff.
    """
    result = _git_engine(request).get_file_diff(
        path=path, staged=staged, commit=commit
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error") or "Could not read the file diff",
        )
    return result


@router.get("/git/repo/file/history")
def api_git_repo_file_history(
    request: Request,
    path: str = Query(..., description="File path (relative or absolute)"),
    limit: int = Query(25, ge=1, le=200),
    user: CodxUser = Depends(get_authenticated_user),
):
    """Return the commit history of a single file."""
    commits = _git_engine(request).get_file_history(path=path, limit=limit)
    return {"path": path, "commits": commits}


# -----------------------------------------------------------------------------
# Working tree operations (stage / unstage / discard)
# -----------------------------------------------------------------------------


@router.post("/git/repo/stage")
def api_git_repo_stage(
    request: Request,
    payload: FilePathsRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """Stage the given files (untracked files and deletions included)."""
    return _ensure_success(_git_engine(request).stage_files(payload.paths))


@router.post("/git/repo/unstage")
def api_git_repo_unstage(
    request: Request,
    payload: FilePathsRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """Remove the given files from the index, keeping their changes."""
    return _ensure_success(_git_engine(request).unstage_files(payload.paths))


@router.post("/git/repo/discard")
def api_git_repo_discard(
    request: Request,
    payload: FilePathsRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Roll the given files back to HEAD.

    Untracked and newly added files are removed from the working tree, so the
    operation is destructive: the UI must confirm it with the user first.
    """
    return _ensure_success(
        _git_engine(request).discard_files(
            payload.paths, include_staged=payload.include_staged
        )
    )


# -----------------------------------------------------------------------------
# Remote operations
# -----------------------------------------------------------------------------


@router.post("/git/repo/fetch")
def api_git_repo_fetch(
    request: Request,
    remote: str = Query("origin"),
    prune: bool = Query(True),
    user: CodxUser = Depends(get_authenticated_user),
):
    """Fetch (and prune) remote refs."""
    return _ensure_success(
        _git_engine(request).fetch_remote(remote=remote, prune=prune)
    )


@router.post("/git/repo/pull")
def api_git_repo_pull(
    request: Request,
    remote: str = Query("origin"),
    branch: Optional[str] = Query(None),
    user: CodxUser = Depends(get_authenticated_user),
):
    """Pull the current (or given) branch from a remote."""
    return _ensure_success(
        _git_engine(request).pull_remote(remote=remote, branch=branch)
    )


@router.post("/git/repo/push")
def api_git_repo_push(
    request: Request,
    remote: str = Query("origin"),
    branch: Optional[str] = Query(None),
    set_upstream: bool = Query(True),
    user: CodxUser = Depends(get_authenticated_user),
):
    """Push the current (or given) branch to a remote."""
    return _ensure_success(
        _git_engine(request).push_remote(
            remote=remote, branch=branch, set_upstream=set_upstream
        )
    )


# -----------------------------------------------------------------------------
# Branch operations
# -----------------------------------------------------------------------------


@router.post("/git/repo/branch")
def api_git_repo_create_branch(
    request: Request,
    payload: CreateBranchRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """Create a branch from another branch (or HEAD)."""
    return _ensure_success(
        _git_engine(request).create_branch(
            branch=payload.branch,
            from_branch=payload.from_branch,
            checkout=payload.checkout,
        )
    )


@router.delete("/git/repo/branch")
def api_git_repo_delete_branch(
    request: Request,
    branch: str = Query(..., description="Branch to delete"),
    force: bool = Query(True, description="Delete even if not merged"),
    user: CodxUser = Depends(get_authenticated_user),
):
    """Delete a local branch (removing its worktree first when present)."""
    return _ensure_success(
        _git_engine(request).delete_branch(branch=branch, force=force)
    )


@router.post("/git/repo/branch/checkout")
def api_git_repo_checkout_branch(
    request: Request,
    payload: CheckoutBranchRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """Check out a branch, tracking the remote branch when needed."""
    return _ensure_success(
        _git_engine(request).checkout_branch(branch=payload.branch)
    )


# -----------------------------------------------------------------------------
# Commit and merge
# -----------------------------------------------------------------------------


@router.post("/git/repo/commit")
def api_git_repo_commit(
    request: Request,
    payload: CommitRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Commit the working tree changes.

    ``stage_all=True`` stages every change first; with ``stage_all=False`` only
    the changes already in the index are committed.
    """
    return _ensure_success(
        _git_engine(request).commit_changes(
            message=payload.message,
            stage_all=payload.stage_all,
            allow_empty=payload.allow_empty,
        )
    )


@router.post("/git/repo/merge")
def api_git_repo_merge(
    request: Request,
    payload: MergeRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """Merge a branch into another one, aborting on conflicts."""
    return _ensure_success(
        _git_engine(request).merge_branches(
            from_branch=payload.from_branch,
            to_branch=payload.to_branch,
            message=payload.message,
            delete_branch=payload.delete_branch,
        )
    )


# Made with ❤️ by codx-junior