Git sub-engine for codx-junior.

# Overview
Handles all git/branch/PR operations.

Made with ❤️ by codx-junior

## API Documentation

### GitEngine Class

The `GitEngine` class handles all git repository operations including branches, diffs and PRs.
It is initialized with a reference to the parent session and provides several methods for interacting with the Git repository.

#### `__init__(session: CODXJuniorSession)`:

Initialize with a reference to the parent session.

#### Properties

*   `settings`: Shortcut to session settings.
*   `_sanitize_branch_name(branch: str) -> str`: Sanitize branch name by removing prefixes like '* ' or '+ worktree//'.
*   `_get_file_last_modification(file_path: str) -> Optional[str]`: Return the last modification datetime of a file as an ISO 8601 string.
*   `_get_git_root_for_file(file_path: str) -> str`: Determine the Git root for a given file, allowing for subprojects.

### Methods

#### `diff_file(path: str, content: str, from_branch: str = None, to_branch: str = None)`
Diff a project file against provided content using git diff --no-index.
 
*   `[diff]`: Diff output
*   `[stats]`: Stats output
*   `[last_modification]`: Last modification datetime (ISO 8601)
*   `[size]`: File size

#### `get_repo_branches() -> list`
Return all Git branches (local and remote) for the project.
Sanitizes branch names by removing prefixes.
 
#### `get_project_branches() -> dict`

Return branches and full repo tree.

#### `get_project_branch_commits(branch: str) -> dict`
Return commits for a given branch.
 
*   `[commits]`: List of commit dictionaries
*   `[tree]`: Fullrepo trees

### Utilities

The class provides several utility methods:

-   `_sanitize_branch_name(branch: str) -> str`
    Sanitize branch name by removing prefixes like '* ' or '+ worktree//'.

### API Reference
#### `build_code_changes_summary(force: bool = False)`
 
Build a code changes summary from git diff.
 
*   `[force]`: Force flag for updating code changes

-   **Parenting**:
    This class is part of the Codx-Junior Junior framework and utilizes the CODXJuniorSession to access its settings.

#### `get_pr_review_details(from_branch: str, to_branch: str)`
 
Return PR review details (file changes, diffs, commits) between two branches.
Each file entry includes a 'last_modification' datetime (ISO 8601).

*   `[from_branch]`: Source branch
*   `[to_branch]`: Target branch

#### `get_commit_list(branch: str = None, limit: int = 50)`
 
Return structured list of commits for a branch or HEAD.
 

-   **Branch Options**:
    The 'limit' parameter determines the number of commits fetched. 
    When no branch is specified ('branch'), it defaults to HEAD.

#### `get_commit_changes(from_commit: str, to_commit: str)`
 
Return file changes and diffs between two commits.
 
-   **Commit Options**:

*   `[from_commit]`: Source commit hash (newer)
*   `[to_commit]`: Target commit hash (older / base)

### Notes

## Dependencies
**Imports from:** codx/junior/project/project_discover.py, codx/junior/utils/utils.py, codx/junior/engine/session.py
**Imported by:** codx/junior/engine/session.py