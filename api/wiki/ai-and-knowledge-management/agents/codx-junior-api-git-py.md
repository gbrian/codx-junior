# Git API Documentation

## Overview

This module provides a REST API for interacting with Git repositories and GitHub issues. It is part of the `codx-api` project and falls under the **Agents** category, covering DevOps, Git issues, and base agent functionality.

---

## Endpoints

### GitHub Issues

#### Get Help-Wanted Issues

**GET** `/git/issues/help-wanted`

Retrieves GitHub issues tagged as "help wanted". If a `query` parameter is provided, it searches GitHub issues using that query. Otherwise, it returns issues from the codx-junior dependencies projects.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | No | Custom search query for GitHub issues |

**Behavior:**
- If `query` is provided → calls `search_github_issues(query=query)`
- If `query` is absent → calls `search_codx_junior_dependencies_project_isssues()`

---

#### Read a GitHub Issue

**GET** `/git/issues/read`

Downloads and returns detailed information about a specific GitHub issue by its URL.

> **Authentication required.**

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_url` | string | Yes | The URL of the GitHub issue to read |

---

#### Process a GitHub Issue with AI

**GET** `/git/issues/ai/process`

Processes a GitHub issue using the `GitIssuesAgent`, which applies AI-based analysis to the specified issue.

> **Authentication required.**

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_url` | string | Yes | The URL of the GitHub issue to process |

This endpoint is asynchronous and delegates processing to `GitIssuesAgent.run(issue_url=issue_url)`.

---

### Git Repository

#### Get Repository Info

**GET** `/git/repo/info`

Returns general information about the current Git repository.

**Response Fields:**
| Field | Description |
|-------|-------------|
| `active_branch` | The currently active branch |
| `git_root` | The root path of the Git repository |
| `repo_path` | The absolute path of the project |

---

#### Get Repository Branches

**GET** `/git/repo/branches`

Returns all available branches (local and remote) for the current project.

---

#### Get Branch Commits

**GET** `/git/repo/branch/commits`

Returns all commits for a specified branch.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `branch` | string | Yes | The branch name to retrieve commits for |

---

#### Get Repository Changes

**GET** `/git/repo/changes`

Returns file changes, diffs, and pull request details between two branches or commits.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `from_branch` | string | Yes | The source branch or commit |
| `to_branch` | string | Yes | The target branch or commit |

---

### Git Files

#### Get File Content from Branch

**GET** `/git/files/content`

Returns the content of a specific file from a given branch.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | The file path within the repository |
| `branch` | string | Yes | The branch to retrieve the file from |

**Response Fields:**
| Field | Description |
|-------|-------------|
| `content` | The file content |
| `path` | The requested file path |
| `branch` | The branch from which the file was retrieved |

**Error Response:**
If either `path` or `branch` is missing, the endpoint returns:
```json
{ "error": "Missing path or branch parameter" }
```

---

## Authentication

Several endpoints require user authentication via the `get_authenticated_user` dependency:
- `/git/issues/read`
- `/git/issues/ai/process`

Unauthenticated requests to these endpoints will be rejected.

---

## Dependencies

This module relies on the following internal components:

- `CODXJuniorSession` — Core session engine managing project context
- `GitIssuesAgent` — AI agent for processing GitHub issues
- `get_authenticated_user` — Security dependency for user authentication
- `search_github_issues`, `download_issue_info`, `search_codx_junior_dependencies_project_isssues` — GitHub utility functions from `codx.junior.misc.github`