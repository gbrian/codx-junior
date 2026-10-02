### Git Sub-Engine Documentation

#### Overview

The Git sub-engine is a module within Codx Junior that handles various Git operations, including repository browsing, branching, and pull requests.

### Usage

To use this engine, create an instance of the `GitEngine` class, passing in your `CODXJuniorSession`.

```markdown
from codx.junior.engine.git_engine import GitEngine

# Replace with your session object
session = CODXJuniorSession()

# Initialize the GitEngine
git_engine = GitEngine(session)
```

### Methods

#### 1. diff_file(file_path, content, from_branch=None, to_branch=None)

Diff a file against provided content.

```markdown
def diff_file(self, path: str, content: str, from_branch: str = None, to_branch: str = None) -> dict:
    """
    Diff a file against provided content.

    Args:
        path (str): File path.
        content (str): New content to diff against.
        from_branch (str, optional): Optional source branch for comparison. Defaults to None.
        to_branch (str, optional): Optional target branch for comparison. Defaults to None.

    Returns:
        Dict with 'diff', 'stats', 'last_modification', and 'size'.
    """
```

#### 2. get_repo_branches()

Return all Git branches (local and remote) for the project.

```markdown
def get_repo_branches(self) -> list:
    """
    Return all Git branches (local and remote) for the project.
    Sanitizes branch names by removing prefixes.

    Returns:
        List of sanitized branch names.
    """
```

#### 3. get_project_branches()

Return branches and full repo tree.

```markdown
def get_project_branches(self) -> dict:
    """
    Return branches and full repo tree.

    Returns:
        Dict with 'branches' and 'repo_tree'.
    """
```

#### 4. build_code_changes_summary(force=False)

Build a code changes summary from Git diff.

```markdown
def build_code_changes_summary(self, force: bool = False) -> object:
    """
    Build a code changes summary from Git diff.

    Args:
        force (bool, optional): Force rebuild if necessary. Defaults to False.

    Returns:
        Object containing the summarized code changes.
    """
```

Refer to [GitEngine class documentation](https://codx-junior.readthedocs.io/en/latest/_modules/codx_junior/engine/git_engine.html) for method details and usage examples.

### Troubleshooting

Check your Git repository setup and permissions to ensure successful execution of these methods.

## Dependencies
**Imports from:** codx/junior/project/project_discover.py, codx/junior/utils/utils.py, codx/junior/engine/session.py
**Imported by:** codx/junior/engine/session.py