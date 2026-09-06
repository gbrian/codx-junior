# Git Engine Documentation

## Overview

The Git Engine is a sub-engine for codx-junior that handles all git repository operations including branches, diffs, pull requests, and commit history management. It provides a comprehensive interface for querying and manipulating git repositories while supporting subprojects with independent git roots.

## Architecture

The GitEngine class operates as a specialized handler within the CODXJuniorSession framework:

```
GitEngine
├── Branch Operations
├── Diff & Changes
├── PR Review Details
├── Commit Management
├── File History
└── Repository State
```

## Core Concepts

### Branch Sanitization

Branch names are automatically cleaned to remove common git prefixes like `* ` (current branch indicator) or `+ worktree/` markers. This ensures consistent branch name handling across all operations.

### Git Root Resolution

The engine can determine the correct git root for any file, supporting subprojects with independent git repositories. It traverses the directory structure upward until it finds a `.git` directory, enabling operations on files in nested git repositories.

### File Modification Tracking

All file-related operations include ISO 8601 formatted modification timestamps, allowing for chronological tracking of changes across different branches and commits.

## Operations

### Repository Information

#### Get Repository Branches
Retrieves all local and remote branches for the project as a deduplicated, sorted list with sanitized names.

#### Get Project Branches
Returns both the branch list and a complete repository tree structure including commits and file changes.

#### Get Repository Tree
Builds a full repository tree with branches, commits, and associated file information. Each commit includes:
- Commit hash and author
- Commit date and message
- List of modified files with their modification timestamps

#### Get Current Branch
Returns the name of the currently checked-out branch.

### Commit Operations

#### Get Commit List
Retrieves a structured list of commits for a specified branch or HEAD. Supports configurable limits on the number of commits returned. Each commit includes:
- Full and short commit hashes
- Author name and email
- ISO 8601 formatted date
- Commit message and label

#### Get Branch Details
Extracts detailed commit information without checking out the branch. Returns commit metadata including:
- Commit hash and author
- Commit timestamp and message
- List of modified files with timestamps
- Parent branch information

#### Get Branch Commits
Returns a structured commit list for a specific branch with author and date information.

#### Get Project Parent Branch
Determines the parent branch of the current branch by analyzing the reflog. Returns an empty string if the parent cannot be determined.

### Change Detection

#### Get Repository Changes
Analyzes differences between two branches and returns:
- File change diffs and statistics
- Per-file commit history
- Last modification timestamps for each file
- PR review details
- Local uncommitted changes (when comparing against the current branch)
- Overall diff command and output

#### Get Commit Changes
Returns file changes and diffs between two commits (typically from newer to older). Includes:
- List of changed files
- File-level diffs
- File-level commit history
- Last modification timestamps
- PR review details

#### Get Project Changes
Returns the diff between the current working tree and a specified parent branch or a default reference.

#### Diff File
Compares a project file against provided content using git's diff functionality. Supports:
- Default behavior: comparing working tree against new content
- Branch-based comparison: comparing file content between two branches
- Diff statistics output

### PR and Review Details

#### Get PR Review Details
Generates comprehensive PR review information between two branches, including:
- File-level status (new, deleted, modified)
- Per-file diffs
- Commit lists for each file
- Last modification timestamps

#### Get PR Review Details by Commits
Similar to PR review details but for comparing two specific commits instead of branches.

### File Operations

#### Get File Content from Branch
Retrieves file content from a specific branch without checking it out. Returns:
- File content as a string
- Empty string if the file doesn't exist in the branch
- Handles both relative and absolute file paths

#### Get File Version at Depth
Navigates through file history to retrieve previous versions without needing commit IDs. The depth parameter allows easy access to historical versions:
- `depth=0`: Immediate previous version (1 commit back)
- `depth=1`: Version from 2 commits ago
- `depth=2`: Version from 3 commits ago

Returns comprehensive metadata including:
- File content
- Commit hash (full and short)
- Author information and email
- Commit date (ISO format)
- Commit message
- Error details if the file was not found at that commit

#### Reset Project File
Resets a file's staged changes, reverting it to the last committed state.

## Data Structures

### Commit Object
```
{
  "commit": "full_hash",
  "short_commit": "hash_8chars",
  "author": {"name": "...", "email": "..."},
  "date": "ISO_8601_date",
  "message": "commit message",
  "label": "hash_8chars - message_preview"
}
```

### File Change Object
```
{
  "file_name": "path/to/file",
  "status": "new|deleted|modified",
  "diff": "diff_output",
  "commits": ["commit_list"],
  "last_modification": "ISO_8601_datetime"
}
```

### Repository Changes Object
```
{
  "diff": "full_diff_output",
  "stat": "diff_statistics",
  "git_diff_cmd": "executed_command",
  "local_changes": {...},
  "repo_path": "git_root_path",
  "pr_details": [...],
  "commits": [],
  "branch_file_and_commits": {
    "file_path": {
      "commits": [...],
      "diff": "...",
      "last_modification": "ISO_8601_datetime"
    }
  },
  "compare_type": "branch|commit"
}
```

## Integration Points

The GitEngine integrates with:
- **CODXJuniorSession**: Parent session providing settings and logging
- **Project Discovery**: Finding parent project repositories
- **Utility Functions**: Command execution via `exec_command`
- **Knowledge Engine**: Building code change summaries from diffs

## Error Handling

The engine provides graceful error handling:
- Logs warnings for unparseable git output
- Returns empty strings or error descriptions for missing files
- Validates depth parameters against available commit history
- Handles both fatal git errors and graceful file-not-found scenarios

## Dependencies
**Imports from:** codx/junior/project/project_discover.py, codx/junior/utils/utils.py, codx/junior/engine/session.py
**Imported by:** codx/junior/engine/session.py