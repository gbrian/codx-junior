# GitEngine Documentation

## Overview

The `GitEngine` class is a sub-engine for codx-junior that handles all git repository operations including branches, diffs, pull requests, and file versioning. It provides a comprehensive interface for interacting with git repositories while supporting subprojects and complex branch comparisons.

## Architecture

```
GitEngine
├── Repository Operations
│   ├── get_repo_branches()
│   ├── get_repo_changes()
│   └── get_repo_tree()
├── Branch Operations
│   ├── get_project_branches()
│   ├── get_project_branch_commits()
│   ├── get_branch_details()
│   └── get_project_current_branch()
├── Commit Operations
│   ├── get_commit_list()
│   ├── get_commit_changes()
│   └── get_project_branch_commits()
├── File Operations
│   ├── diff_file()
│   ├── reset_project_file()
│   ├── get_file_content_from_branch()
│   └── get_file_version_at_depth()
└── PR Operations
    ├── get_pr_review_details()
    └── get_pr_review_details_by_commits()
```

## Core Concepts

### Branch Name Sanitization

The engine automatically sanitizes branch names by removing common git prefixes such as `* ` (current branch indicator) and `+ worktree/` prefixes. This is handled transparently across all methods through the `_sanitize_branch_name()` method.

### File Path Resolution

The engine intelligently resolves file paths across subprojects by:
- Converting relative paths to absolute paths using the project root
- Locating the correct Git root for a given file via `_get_git_root_for_file()`
- Supporting nested git repositories

### Last Modification Tracking

All file operations return `last_modification` timestamps in ISO 8601 format, obtained from the file system rather than git history.

## Methods Reference

### Repository Information

#### `get_repo_branches() → list`
Returns all git branches (local and remote) for the project with sanitized names sorted alphabetically.

#### `get_project_branches() → dict`
Returns both branches and the full repository tree structure:
```python
{
    "branches": [...],
    "repo_tree": [...]
}
```

#### `get_repo_tree() → list`
Builds a comprehensive repository tree containing all branches with their commits and associated files.

#### `find_git_root_path() → str`
Locates the root directory of the git repository by checking parent directories or returning the project path if it's already a git root.

### Branch Operations

#### `get_branch_details(branch_name: str) → dict`
Extracts detailed commit information from a branch without checking it out:
```python
{
    "commits": [
        {
            "commit_hash": "...",
            "author": "...",
            "date": "...",
            "message": "...",
            "files": [...]
        }
    ],
    "parent_branch": "..."
}
```

#### `get_project_current_branch() → str`
Returns the name of the currently checked-out branch.

#### `get_project_parent_branch() → str`
Determines the parent branch of the current branch by analyzing git reflog. Returns an empty string if parent cannot be determined.

#### `get_project_branch_commits(branch: str) → dict`
Returns git log output for a given branch.

#### `get_branch_commits(from_branch: str, repo_path: str) → list`
Returns a structured list of commits for a branch with parsed author, date, and message information.

### Commit Operations

#### `get_commit_list(branch: str = None, limit: int = 50) → list`
Retrieves a structured list of commits with rich metadata:
```python
[
    {
        "commit": "full_hash",
        "short_commit": "8_char_hash",
        "author": {"name": "...", "email": "..."},
        "date": "ISO_8601",
        "message": "...",
        "label": "hash - message_preview"
    }
]
```

#### `get_commit_changes(from_commit: str, to_commit: str) → dict`
Returns comprehensive file changes and diffs between two commits:
```python
{
    "diff": "...",
    "stat": "...",
    "git_diff_cmd": "...",
    "pr_details": [...],
    "branch_file_and_commits": {...},
    "from_commit": "...",
    "to_commit": "..."
}
```

### File Operations

#### `diff_file(path: str, content: str, from_branch: str = None, to_branch: str = None) → dict`
Compares a file against provided content or between two branches:
- Default behavior uses `git diff --no-index` to compare working tree against new content
- When both `from_branch` and `to_branch` are provided, compares the file between those branches

Returns:
```python
{
    "diff": "...",
    "stats": "..."
}
```

#### `reset_project_file(file_path: str) → None`
Resets a file's last change by executing `git reset` on the specified file.

#### `get_file_content_from_branch(file_path: str, branch: str) → str`
Retrieves file content from a specific branch without checking it out. Returns empty string if the file doesn't exist in that branch.

#### `get_file_version_at_depth(file_path: str, depth: int = 0) → dict`
Retrieves a previous version of a file from git history by navigating through commits:

**Depth Levels:**
- `depth=0`: Immediate previous version (1 commit back)
- `depth=1`: Version from 2 commits ago
- `depth=2`: Version from 3 commits ago

Returns:
```python
{
    "content": "...",
    "commit": "...",
    "short_commit": "...",
    "author": "...",
    "email": "...",
    "date": "ISO_8601",
    "message": "...",
    "depth": depth_requested,
    "error": None  # or error message
}
```

### Branch Comparison

#### `get_repo_changes(from_branch: str, to_branch: str) → dict`
Returns comprehensive file changes, diffs, and PR details between two branches:
```python
{
    "diff": "...",
    "stat": "...",
    "git_diff_cmd": "...",
    "local_changes": {...},
    "repo_path": "...",
    "pr_details": [...],
    "branch_file_and_commits": {...},
    "compare_type": "branch"
}
```

Each file entry includes:
- `commits`: List of commits that modified the file
- `diff`: Full diff output
- `last_modification`: ISO 8601 timestamp

#### `get_project_changes(parent_branch: str = None) → dict`
Returns diff between current working tree and a parent branch. Defaults to `HEAD@{1}` if no parent branch specified.

### Pull Request Operations

#### `get_pr_review_details(from_branch: str, to_branch: str) → list`
Returns PR review details with file changes, diffs, and commits between two branches:
```python
[
    {
        "file_name": "...",
        "status": "new|deleted|modified",
        "diff": "...",
        "commits": [...],
        "last_modification": "ISO_8601"
    }
]
```

#### `get_pr_review_details_by_commits(from_commit: str, to_commit: str) → list`
Similar to PR review details but operates between specific commits instead of branches.

## Special Features

### Code Changes Summary

#### `build_code_changes_summary(force: bool = False) → object`
Builds a summarized view of code changes from git diff using the session's knowledge system.

### Local Changes Handling

When comparing branches, the engine automatically detects and includes local uncommitted changes in the diff if the target branch is the current branch.

## Error Handling

- **Missing files**: Methods return empty strings or empty lists with error messages in return dictionaries
- **Invalid depths**: `get_file_version_at_depth()` validates depth and returns error information
- **Git command failures**: Errors are logged and gracefully handled with appropriate return values
- **Path resolution**: Automatically handles both absolute and relative paths

## Integration Points

The `GitEngine` requires:
- A `CODXJuniorSession` instance for initialization
- Access to `session.settings` for project paths and configuration
- Access to `session.log_info()` for logging important operations
- Access to `session.get_knowledge()` for code summary building

## Dependencies
**Imports from:** codx/junior/project/project_discover.py, codx/junior/utils/utils.py, codx/junior/engine/session.py
**Imported by:** codx/junior/engine/session.py