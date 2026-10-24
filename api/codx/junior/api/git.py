"""
Git repository API.

Exposes the repository management endpoints consumed by the git view:

- Read: repository info, branches, commits, the commit graph, remotes,
  worktrees, working tree status, two-branch comparison (PR review), commit
  details and single file diff/history/content.
- Write: fetch, pull, push, create/checkout/delete branch, stage/unstage/
  discard files, commit, merge, rebase and the local PR lifecycle (create,
  close, abandon).

All operations are delegated to
:class:`codx.junior.engine.git_graph.GitGraphEngine` (a
:class:`codx.junior.engine.git_workspace.GitWorkspaceEngine` with the graph read
operations, itself a :class:`codx.junior.engine.git_engine.GitEngine` with file
level operations). Routes are mounted under ``/api`` by the dynamic router
loader (``codx.junior.api.discover_routers``), so the final paths look like
``/api/git/repo/branches``.

Staging is the only write operation that never fails as a whole: each path is
staged on its own, so a failing path is reported in ``errors`` while the
remaining ones are already in the index.

```mermaid
sequenceDiagram
    participant UI as GitView
    participant API as git router
    participant Engine as GitGraphEngine
    participant Git as git CLI

    UI->>API: POST /api/git/repo/stage { paths }
    API->>Engine: stage_files(paths)
    loop each path
        Engine->>Git: git add -A -- <path>
        Git-->>Engine: ok | pathspec error
    end
    Engine-->>API: { success, staged, errors }
    API-->>UI: 200 result (failed paths listed in errors)

    UI->>API: GET /api/git/repo/graph?limit=150
    API->>Engine: get_repo_graph(limit=150)
    Engine->>Git: git log --date-order + git for-each-ref
    Engine-->>API: { commits, branches, default_branch }
    API-->>UI: 200 graph payload

    UI->>API: POST /api/git/repo/commit { message }
    API->>Engine: commit_changes(message)
    Engine->>Git: git commit -m <message>
    Git-->>Engine: ok | error
    Engine-->>API: { success, commit }
    API-->>UI: 200 result | 400 { detail }
```

Made with ❤️ by codx-junior
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from codx.junior.engine.git_graph import GitGraphEngine
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


class RebaseRequest(BaseModel):
    """Payload to rebase a branch onto another one."""

    onto_branch: str
    branch: Optional[str] = None


class FilePathsRequest(BaseModel):
    """Payload for bulk operations over a set of working tree files."""

    paths: List[str]
    include_staged: bool = True


class CreatePRRequest(BaseModel):
    """Payload to create a local PR branch."""

    branch: Optional[str] = None
    branch_name: Optional[str] = None
    base_branch: Optional[str] = None
    commit_message: Optional[str] = None
    files_content: Optional[Dict[str, str]] = None
    use_worktree: bool = False
    worktree_path: Optional[str] = None
    allow_empty: bool = True


class ClosePRRequest(BaseModel):
    """Payload to close a local PR (merge its branch into the base)."""

    branch: str
    base_branch: Optional[str] = None
    commit_message: Optional[str] = None
    delete_branch: bool = False


class AbandonPRRequest(BaseModel):
    """Payload to abandon a local PR (drop the branch and its commits)."""

    branch: str
    base_branch: Optional[str] = None
    delete_branch: bool = True


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _git_engine(request: Request) -> GitGraphEngine:
    """
    Build a GitGraphEngine for the active project session.

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
    return GitGraphEngine(session=session)


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


@router.get("/git/repo/graph")
def api_git_repo_graph(
    request: Request,
    branch: Optional[str] = Query(None, description="Restrict to a branch"),
    limit: int = Query(150, ge=1, le=1000, description="Maximum commits"),
    include_remote: bool = Query(True, description="Include remote branches"),
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Return the commit graph of the repository (VSCode *Git Graph* style).

    Commits are returned newest first with their parents and the refs pointing
    to them, so the client only assigns lanes and draws the edges.

    Args:
        branch: Restrict the graph to a single branch. Defaults to all refs.
        limit: Maximum number of commits returned.
        include_remote: Include remote-tracking branches and their commits.

    Returns:
        Dict with 'default_branch', 'active_branch', 'branches' (refs with the
        commit they point to) and 'commits'.

    Example:
        GET /api/git/repo/graph?limit=150&include_remote=1

        200 OK
        {
          "default_branch": "main",
          "active_branch": "feature/login",
          "branches": [
            {"name": "main", "type": "local", "commit": "a2d3b55c"},
            {"name": "origin/main", "type": "remote", "commit": "a2d3b55c"}
          ],
          "commits": [{
            "hash": "a2d3b55c...",
            "parents": ["3b5a11ec..."],
            "subject": "fix: login timeout",
            "author": {"name": "Jane", "email": "jane@acme.com"},
            "date": "2024-05-01T10:00:00+02:00",
            "refs": [{"name": "main", "type": "local"}],
            "is_merge": false
          }]
        }
    """
    return _git_engine(request).get_repo_graph(
        branch=branch, limit=limit, include_remote=include_remote
    )


@router.get("/git/repo/remotes")
def api_git_repo_remotes(
    request: Request, user: CodxUser = Depends(get_authenticated_user)
):
    """Return the configured remotes with their fetch and push URLs."""
    return {"remotes": _git_engine(request).list_remotes()}


@router.get("/git/repo/worktrees")
def api_git_repo_worktrees(
    request: Request, user: CodxUser = Depends(get_authenticated_user)
):
    """Return the repository's registered worktrees (path and branch)."""
    return {"worktrees": _git_engine(request).list_worktrees()}


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


@router.get("/git/repo/commit/changes")
def api_git_repo_commit_changes(
    request: Request,
    from_commit: str = Query(..., description="Source commit hash (newer)"),
    to_commit: str = Query(..., description="Target commit hash (older / base)"),
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Compare two commits and return the PR review payload.

    Args:
        from_commit: Source commit hash (newer).
        to_commit: Target commit hash (older / base).
    """
    return _git_engine(request).get_commit_changes(
        from_commit=from_commit, to_commit=to_commit
    )


@router.get("/git/repo/commit/detail")
def api_git_repo_commit_detail(
    request: Request,
    commit: str = Query(..., description="Commit hash"),
    path: Optional[str] = Query(
        None, description="Optional file path to restrict the diff"
    ),
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Return the files changed by a commit together with their patches.

    Used by the graph's commit panel: one request returns the whole commit, so
    the UI never needs one round trip per changed file.

    Args:
        commit: Commit hash.
        path: Optional file path (relative or absolute) to diff only that file.
    """
    result = _git_engine(request).get_commit_detail(commit=commit, path=path)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error") or "Could not read the commit",
        )
    return result


@router.get("/git/repo/file/diff")
def api_git_repo_file_diff(
    request: Request,
    path: str = Query(..., description="File path (relative or absolute)"),
    staged: bool = Query(False, description="Diff the staged (index) changes"),
    commit: Optional[str] = Query(None, description="Commit hash to diff"),
    mode: Optional[str] = Query(
        None, description="Diff source: worktree, staged or commit"
    ),
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Return the diff of a single file.

    Sources, in precedence order: `mode`, the given ``commit``, the staged
    changes (``staged=true``) or the working tree. Untracked files get a
    synthetic "new file" diff.
    """
    if mode and mode not in ("worktree", "staged", "commit"):
        raise HTTPException(
            status_code=400,
            detail="mode must be 'worktree', 'staged' or 'commit'",
        )

    result = _git_engine(request).get_file_diff(
        path=path, staged=staged, commit=commit, mode=mode
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


@router.get("/git/files/content")
def api_git_file_content(
    request: Request,
    path: str = Query(..., description="File path (relative or absolute)"),
    branch: Optional[str] = Query(None, description="Branch, defaults to the current one"),
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Return a file's content as it is stored in a branch, without checking it out.

    Args:
        path: File path (relative or absolute).
        branch: Branch name. Defaults to the checked out branch.

    Returns:
        Dict with 'path', 'branch' and 'content' (empty when the file does not
        exist in that branch).

    Example:
        GET /api/git/files/content?path=app.py&branch=main

        200 OK
        {"path": "app.py", "branch": "main", "content": "print(1)\\n"}
    """
    engine = _git_engine(request)
    branch = branch or engine.get_project_current_branch()
    if not branch:
        raise HTTPException(
            status_code=400,
            detail="branch is required while HEAD is detached",
        )

    content = engine.get_file_content_from_branch(file_path=path, branch=branch)
    return {"path": path, "branch": branch, "content": content}


# -----------------------------------------------------------------------------
# Working tree operations (stage / unstage / discard)
# -----------------------------------------------------------------------------


@router.post("/git/repo/stage")
def api_git_repo_stage(
    request: Request,
    payload: FilePathsRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Stage the given files (untracked files and deletions included).

    Staging never fails as a whole: each path is staged on its own, so the
    paths that could be staged are already in the index when the response is
    returned. A failing path (removed from disk, unknown pathspec, ignored...)
    only affects itself and is listed in ``errors``; the request still answers
    **200** so the caller can refresh the status and show the failed paths.

    Args:
        payload: ``paths`` to stage (``include_staged`` is ignored here).

    Returns:
        Staging result with 'success' (False when at least one path failed),
        'paths' (requested), 'staged' (paths staged successfully) and 'errors'
        (one message per failed path).

    Example:
        POST /api/git/repo/stage {"paths": ["app.py", "gone.json"]}

        200 OK
        {
          "success": false,
          "paths": ["app.py", "gone.json"],
          "staged": ["app.py"],
          "errors": ["gone.json: pathspec 'gone.json' did not match any files"]
        }
    """
    result = _git_engine(request).stage_files(payload.paths)
    return {
        **result,
        "staged": result.get("staged", []),
        "errors": [e for e in (result.get("errors") or []) if e],
    }


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

    Staging failures are returned in ``staging_errors`` without blocking the
    commit of the changes that could be staged.
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


@router.post("/git/repo/rebase")
def api_git_repo_rebase(
    request: Request,
    payload: RebaseRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Rebase a branch onto another one (graph "rebase current onto this branch").

    The rebase rewrites the history of the rebased branch: its commits get new
    hashes. Conflicting rebases are aborted and the conflicting files are
    returned in ``conflicts`` (through the 400 detail) so nothing is left in the
    middle of a rebase.

    Args:
        payload: ``onto_branch`` (branch to rebase onto) and ``branch``
            (branch to rebase, defaults to the checked out one).

    Example:
        POST /api/git/repo/rebase {"onto_branch": "main", "branch": "fix-login"}

        200 OK
        {
          "success": true,
          "action": "rebase",
          "branch": "fix-login",
          "onto_branch": "main",
          "onto_ref": "main",
          "commit": "b7c1d9e0...",
          "up_to_date": false,
          "conflicts": []
        }
    """
    return _ensure_success(
        _git_engine(request).rebase_branch(
            onto_branch=payload.onto_branch,
            branch=payload.branch,
        )
    )


# -----------------------------------------------------------------------------
# Local PR lifecycle
# -----------------------------------------------------------------------------


@router.post("/git/repo/pr")
def api_git_repo_create_pr(
    request: Request,
    payload: CreatePRRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Create a local PR branch and commit the chat changes on it.

    PRs are reviewed locally by codx-junior: nothing is pushed to the remote.

    Args:
        payload: Branch name (``branch`` or ``branch_name``), optional base
            branch, commit message, file contents, and whether the branch is
            created as a worktree.
    """
    return _ensure_success(
        _git_engine(request).create_pr_branch(
            branch_name=payload.branch_name or payload.branch,
            files_content=payload.files_content,
            base_branch=payload.base_branch,
            commit_message=payload.commit_message,
            use_worktree=payload.use_worktree,
            worktree_path=payload.worktree_path,
            allow_empty=payload.allow_empty,
        )
    )


@router.post("/git/repo/pr/close")
def api_git_repo_close_pr(
    request: Request,
    payload: ClosePRRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """Close a local PR by merging its branch into the base branch."""
    return _ensure_success(
        _git_engine(request).close_pr_branch(
            branch_name=payload.branch,
            base_branch=payload.base_branch,
            commit_message=payload.commit_message,
            delete_branch=payload.delete_branch,
        )
    )


@router.post("/git/repo/pr/abandon")
def api_git_repo_abandon_pr(
    request: Request,
    payload: AbandonPRRequest,
    user: CodxUser = Depends(get_authenticated_user),
):
    """Abandon a local PR: remove its worktree and drop the branch."""
    return _ensure_success(
        _git_engine(request).abandon_pr_branch(
            branch_name=payload.branch,
            base_branch=payload.base_branch,
            delete_branch=payload.delete_branch,
        )
    )


# Made with ❤️ by codx-junior