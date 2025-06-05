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

@router.get('/github/issues/help-wanted')
def get_github_issues_help_wanted(request: Request):
    query = request.query_params.get("query")
    if query:
      return search_github_issues(query=query)
    return search_codx_junior_dependencies_project_isssues() 

@router.get("/github/issues/read")
def read_github_issue(request: Request, user: CodxUser = Depends(get_authenticated_user)):  
    issue_url = request.query_params.get("issue_url")
    return download_issue_info(issue_url)

@router.get("/github/issues/ai/process")
async def process_github_issue(request: Request, user: CodxUser = Depends(get_authenticated_user)):  
    codx_junior_session = request.state.codx_junior_session
    return await GitIssuesAgent(session=codx_junior_session).run(issue_url=issue_url)
