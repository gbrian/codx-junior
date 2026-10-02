import logging
from fastapi import APIRouter, Request, Depends

from codx.junior.engine import (
  CODXJuniorSession,
)

from codx.junior.security.user_management import get_authenticated_user

from codx.junior.misc.github import (
  search_github_issues,
  download_issue_info,
  search_codx_junior_dependencies_project_isssues
)

from codx.junior.model.model import CodxUser, CodxUserLogin

from codx.junior.agents.git_issues_agent import GitIssuesAgent

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get('/git/issues/help-wanted')
def get_github_issues_help_wanted(request: Request):
    query = request.query_params.get("query")
    if query:
      return search_github_issues(query=query)
    return search_codx_junior_dependencies_project_isssues() 

@router.get("/git/issues/read")
def read_github_issue(request: Request, user: CodxUser = Depends(get_authenticated_user)):  
    issue_url = request.query_params.get("issue_url")
    return download_issue_info(issue_url)

@router.get("/git/issues/ai/process")
async def process_github_issue(request: Request, user: CodxUser = Depends(get_authenticated_user)):  
    codx_junior_session = request.state.codx_junior_session
    issue_url = request.query_params.get("issue_url")
    return await GitIssuesAgent(session=codx_junior_session).run(issue_url=issue_url)

# Git Repository Endpoints
@router.get("/git/repo/info")
def get_repo_info(request: Request):
    """
    Get repository information including active branch and other git details.
    """
    codx_junior_session = request.state.codx_junior_session
    return {
        "active_branch": codx_junior_session.get_project_current_branch(),
        "git_root": codx_junior_session.get_git_engine().find_git_root_path(),
        "repo_path": codx_junior_session.settings.abs_project_path,
    }

@router.get("/git/repo/branches")
def get_repo_branches(request: Request):
    """
    Get all available branches (local and remote) for the project.
    """
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.get_git_engine().get_project_branches()

@router.get("/git/repo/branch/commits")
def get_repo_branch_commits(request: Request):
    """
    Get all commits for a specific branch.
    """
    codx_junior_session = request.state.codx_junior_session
    branch = request.query_params.get("branch")
    return codx_junior_session.get_git_engine().get_project_branch_commits(branch=branch)

@router.get("/git/repo/changes")
def get_repo_changes(request: Request):
    """
    Get file changes, diffs and PR details between two branches or commits.
    """
    codx_junior_session = request.state.codx_junior_session
    from_branch = request.query_params.get("from_branch")
    to_branch = request.query_params.get("to_branch")
    return codx_junior_session.get_git_engine().get_repo_changes(from_branch=from_branch, to_branch=to_branch)

@router.get("/git/files/content")
def get_file_content_from_branch(request: Request):
    """
    Get file content from a specific branch.
    """
    codx_junior_session = request.state.codx_junior_session
    file_path = request.query_params.get("path")
    branch = request.query_params.get("branch")
    
    if not file_path or not branch:
        return {"error": "Missing path or branch parameter"}
    
    content = codx_junior_session.get_git_engine().get_file_content_from_branch(
        file_path=file_path,
        branch=branch
    )
    
    return {
        "content": content,
        "path": file_path,
        "branch": branch
    }