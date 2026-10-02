import logging
from fastapi import APIRouter, Request, Depends

from codx.junior.engine import CODXJuniorSession
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.model.model import CodxUser

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/projects/repo/branches")
def get_repo_branches(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    return codx_junior_session.get_repo_branches()

@router.get("/projects/repo/changes")
def get_repo_changes(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    from_branch = request.query_params.get("from_branch")
    to_branch = request.query_params.get("to_branch")
    return codx_junior_session.get_repo_changes(from_branch=from_branch, to_branch=to_branch)

@router.get("/projects/repo/commits")
def get_repo_commits(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    """Return a structured list of commits for a branch (default: HEAD)."""
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    branch = request.query_params.get("branch", None)
    limit = int(request.query_params.get("limit", 50))
    git_engine = codx_junior_session.get_git_engine()
    return git_engine.get_commit_list(branch=branch, limit=limit)

@router.get("/projects/repo/commit-changes")
def get_commit_changes(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    """Return diff and file changes between two commits."""
    codx_junior_session: CODXJuniorSession = request.state.codx_junior_session
    from_commit = request.query_params.get("from_commit")
    to_commit = request.query_params.get("to_commit")
    git_engine = codx_junior_session.get_git_engine()
    return git_engine.get_commit_changes(
        from_commit=from_commit,
        to_commit=to_commit
    )