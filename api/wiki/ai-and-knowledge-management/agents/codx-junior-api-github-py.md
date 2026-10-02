# GitHub API Module

## Overview

This module provides a set of REST API endpoints for interacting with GitHub issues and Git repository information. It is part of the **Agents** category and covers functionality related to DevOps, Git issues, and base agent operations.

---

## Endpoints

### GitHub Issues

#### GET `/github/issues/help-wanted`

Retrieves GitHub issues labeled as "help wanted."

- **Query Parameters:**
  - `query` *(optional)*: A custom search query string. If provided, searches GitHub issues using that query.
  - If no query is provided, it returns issues from the `codx-junior` dependencies project by default.

- **Authentication:** Not required.

- **Behavior:**
  - If `query` parameter is present → calls `search_github_issues(query=query)`
  - If `query` parameter is absent → calls `search_codx_junior_dependencies_project_isssues()`

---

#### GET `/github/issues/read`

Downloads and returns detailed information about a specific GitHub issue.

- **Query Parameters:**
  - `issue_url` *(required)*: The URL of the GitHub issue to read.

- **Authentication:** Required (authenticated user via `get_authenticated_user`).

- **Behavior:** Calls `download_issue_info(issue_url)` to fetch issue details.

---

#### GET `/github/issues/ai/process`

Processes a GitHub issue using the AI-powered `GitIssuesAgent`.

- **Query Parameters:**
  - `issue_url` *(required)*: The URL of the GitHub issue to process.

- **Authentication:** Required (authenticated user via `get_authenticated_user`).

- **Behavior:** Instantiates `GitIssuesAgent` with the current session and runs it against the given issue URL. This is an **async** endpoint.

---

### Git Repository

#### GET `/github/repo/info`

Returns general repository information for the current project.

- **Authentication:** Not required.

- **Response Fields:**
  - `active_branch`: The currently active Git branch.
  - `git_root`: The root path of the Git repository.
  - `repo_path`: The absolute path of the project.

---

#### GET `/github/repo/branches`

Returns all available branches (local and remote) for the project.

- **Authentication:** Not required.

- **Behavior:** Calls `get_project_branches()` on the project's Git engine.

---

#### GET `/github/repo/branch/commits`

Returns all commits for a specific branch.

- **Query Parameters:**
  - `branch` *(required)*: The name of the branch to retrieve commits for.

- **Authentication:** Not required.

- **Behavior:** Calls `get_project_branch_commits(branch=branch)` on the project's Git engine.

---

#### GET `/github/repo/changes`

Returns file changes, diffs, and PR details between two branches or commits.

- **Query Parameters:**
  - `from_branch` *(required)*: The source branch or commit reference.
  - `to_branch` *(required)*: The target branch or commit reference.

- **Authentication:** Not required.

- **Behavior:** Calls `get_repo_changes(from_branch=from_branch, to_branch=to_branch)` on the project's Git engine.

---

## Dependencies

| Component | Description |
|---|---|
| `CODXJuniorSession` | Manages the active session for the project |
| `get_authenticated_user` | Security dependency for user authentication |
| `search_github_issues` | Searches GitHub issues by query |
| `download_issue_info` | Downloads details for a specific issue URL |
| `search_codx_junior_dependencies_project_isssues` | Returns issues from the codx-junior dependencies project |
| `GitIssuesAgent` | AI agent that processes GitHub issues |

---

## Authentication

Some endpoints require an authenticated user, resolved via the `get_authenticated_user` dependency. The following endpoints are protected:

- `/github/issues/read`
- `/github/issues/ai/process`

## Dependencies
**Imports from:** codx/junior/engine.py, codx/junior/security/user_management.py, codx/junior/misc/github.py, codx/junior/model/model.py, codx/junior/agents/git_issues_agent.py
**Imported by:** codx/junior/app.py