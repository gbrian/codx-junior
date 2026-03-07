## GitHub Issues Agents

This document outlines the API endpoints for interacting with GitHub issues within the CODX Junior project.

### Help Wanted Issues

This endpoint allows you to search for "help wanted" issues on GitHub. You can either provide a specific query to narrow down your search or retrieve issues from the CODX Junior dependencies project.

```python /codx/junior/api/github.py
@router.get('/github/issues/help-wanted')
def get_github_issues_help_wanted(request: Request):
    query = request.query_params.get("query")
    if query:
      return search_github_issues(query=query)
    return search_codx_junior_dependencies_project_isssues()
```

### Read GitHub Issue

This endpoint retrieves detailed information about a specific GitHub issue. You need to provide the URL of the issue.

```python /codx/junior/api/github.py
@router.get("/github/issues/read")
def read_github_issue(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    issue_url = request.query_params.get("issue_url")
    return download_issue_info(issue_url)
```

### Process GitHub Issue with AI

This endpoint utilizes the `GitIssuesAgent` to process a GitHub issue using AI. It requires an authenticated user and the URL of the issue to be processed.

```python /codx/junior/api/github.py
@router.get("/github/issues/ai/process")
async def process_github_issue(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    codx_junior_session = request.state.codx_junior_session
    return await GitIssuesAgent(session=codx_junior_session).run(issue_url=issue_url)
```