"""
Git tools for version control operations and change history analysis.

This module provides tools for analyzing git history, file versions and for
turning chat changes into local PR branches (reviewed by codx-junior, no push).
Useful for understanding changes, PR reviews, and rollback analysis.

Made with ❤️ by codx-junior
"""

import logging
from typing import Dict, Optional

from codx.junior.engine import CODXJuniorSession
from .model import ToolResponse

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_DEPTH = 0
MAX_DEPTH = 50
DEFAULT_COMMIT_MESSAGE = "feat: apply AI-generated code changes"


def get_file_last_version(
    file_path: str,
    depth: Optional[int] = None,
    **kwargs
) -> ToolResponse:
    """
    Retrieve a previous version of a file from git history.

    Navigate through file history by depth level without needing commit IDs.
    Each depth level represents how many commits back to look:
    - depth=0 (or None): Get the immediate previous version (1 commit back)
    - depth=1: Get version from 2 commits ago
    - depth=2: Get version from 3 commits ago
    - etc.

    Useful for:
    - Understanding what changed between versions
    - PR reviews and change analysis
    - Forensic debugging and rollback analysis
    - Comparing current code against previous implementations

    Args:
        file_path: Relative or absolute path to the file to retrieve.
        depth: How many commits back to navigate (default: 0 = previous version).
               Must be >= 0. If exceeds available history, returns error.
        **kwargs: Additional arguments including:
            - session (CODXJuniorSession): Session with git engine (required).

    Returns:
        ToolResponse: Contains:
            - user_response: Summary of the version retrieved.
            - llm_response: File content with metadata or error message.

    Raises:
        ValueError: If file_path is empty or depth is invalid.
        Exception: If session or git engine is not available.

    Example:
        Get previous version (1 commit back):
        >>> get_file_last_version("src/main.py")
        # Returns ToolResponse with file content from previous commit

        Get version from 2 commits ago:
        >>> get_file_last_version("src/main.py", depth=1)

        Get version from 5 commits ago:
        >>> get_file_last_version("config/settings.py", depth=4)
    """
    session: CODXJuniorSession = kwargs.get("session", None)
    if not session:
        raise Exception("Invalid session - git engine not available")

    if not file_path:
        raise ValueError("file_path must be provided and cannot be empty")

    # Normalize depth
    if depth is None:
        depth = DEFAULT_DEPTH
    depth = max(0, min(int(depth), MAX_DEPTH))

    try:
        # Get git engine and retrieve file version
        git_engine = session.get_git_engine()
        result = git_engine.get_file_version_at_depth(file_path=file_path, depth=depth)

        # Check for errors
        if result.get("error"):
            error_msg = result["error"]
            logger.warning("Error retrieving file version: %s", error_msg)
            return ToolResponse(
                user_response=f"error [{file_path}]\nERROR: {error_msg}",
                llm_response=f"Failed to retrieve file version: {error_msg}",
            )

        # Build file content response
        if not result.get("content"):
            error_msg = "File content is empty or file did not exist at this version"
            logger.warning("Empty content for %s at depth %d", file_path, depth)
            return ToolResponse(
                user_response=f"warning [{file_path}]\n{error_msg}",
                llm_response=f"Retrieved empty file: {file_path} at depth {depth}",
            )

        # Format the file content in a code block
        extension = file_path.split(".")[-1] if "." in file_path else "txt"
        content_block = f"```{extension} {file_path}\n{result['content']}\n```"

        # Build metadata section
        metadata = [
            f"# File Version History: {file_path}",
            f"## Retrieved Version (Depth: {depth})",
            f"- Commit: `{result['short_commit']}` ({result['commit']})",
            f"- Author: {result['author']} <{result['email']}>",
            f"- Date: {result['date']}",
            f"- Message: {result['message']}",
            "",
            "## File Content",
            content_block,
        ]

        llm_response = "\n".join(metadata)

        # Build user summary
        user_response = (
            f"Retrieved version of `{file_path}` | "
            f"Depth: {depth} | "
            f"Commit: {result['short_commit']} | "
            f"Author: {result['author']}"
        )

        logger.info(
            "Retrieved file version: %s (depth=%d, commit=%s)",
            file_path,
            depth,
            result["short_commit"]
        )

        return ToolResponse(user_response=user_response, llm_response=llm_response)

    except ValueError as e:
        error_msg = str(e)
        logger.error("Validation error: %s", error_msg)
        return ToolResponse(
            user_response=f"error [{file_path}]\nERROR: {error_msg}",
            llm_response=f"Failed to retrieve file version: {error_msg}",
        )

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return ToolResponse(
            user_response=f"error [{file_path}]\nERROR: {error_msg}",
            llm_response=f"Failed to retrieve file version: {error_msg}",
        )


def create_pr_branch(
    branch_name: Optional[str] = None,
    base_branch: Optional[str] = None,
    commit_message: Optional[str] = None,
    files: Optional[Dict[str, str]] = None,
    use_worktree: bool = False,
    **kwargs
) -> ToolResponse:
    """
    Create a local PR branch from the current branch with the chat changes.

    PRs are handled locally by codx-junior (reviewed inside the project), so
    nothing is pushed to the remote: the workflow ends when the branch and its
    commit exist on disk.

    - The branch is created from the **current** branch unless `base_branch` is
      given.
    - When `files` is provided those contents are written before committing.
      When omitted, the changes already present on disk are committed.
    - When `use_worktree` is enabled the branch is created in a separate
      `git worktree` folder, so the project's working tree and its uncommitted
      changes stay untouched.

    Args:
        branch_name: Target PR branch (e.g. 'codx-junior/fix-login').
            Generated automatically when omitted.
        base_branch: Base branch. Defaults to the current branch.
        commit_message: Commit message. Defaults to a generic message.
        files: Optional dictionary mapping project-relative file paths to their
            full file content.
        use_worktree: Create the branch as a worktree (default: False).
        **kwargs: Additional arguments including:
            - session (CODXJuniorSession): Session with git engine (required).

    Returns:
        ToolResponse: Contains:
            - user_response: Summary with branch, base, commit and worktree path.
            - llm_response: Machine friendly summary of the operation.
            - logs: One entry per git step executed.

    Raises:
        ValueError: If `files` is not a dictionary.
        Exception: If session or git engine is not available.

    Example:
        PR branch from the current branch with the changes already on disk:
        >>> create_pr_branch(branch_name="codx-junior/fix-login")

        PR branch isolated in a worktree:
        >>> create_pr_branch(branch_name="codx-junior/fix-login", use_worktree=True)

        Write specific files and commit them on the PR branch:
        >>> create_pr_branch(
        ...     branch_name="codx-junior/fix-login",
        ...     commit_message="fix: login timeout",
        ...     files={"codx/junior/app.py": "print('hi')"},
        ... )
    """
    session: CODXJuniorSession = kwargs.get("session", None)
    if not session:
        raise Exception("Invalid session - git engine not available")

    if files is not None and not isinstance(files, dict):
        raise ValueError("files must be a dictionary mapping file paths to contents")

    git_engine = session.get_git_engine()
    branch_name = branch_name or git_engine.build_branch_name()

    logs = []
    try:
        result = git_engine.create_pr_branch(
            branch_name=branch_name,
            files_content=files,
            base_branch=base_branch,
            commit_message=commit_message or DEFAULT_COMMIT_MESSAGE,
            use_worktree=use_worktree,
        )
    except Exception as ex:
        error_msg = f"Unexpected error: {str(ex)}"
        logger.error("create_pr_branch failed for %s: %s", branch_name, ex)
        return ToolResponse(
            user_response=f"error [{branch_name}]\nERROR: {error_msg}",
            llm_response=f"Failed to create branch '{branch_name}': {error_msg}",
        )

    # Collect git step logs for the forensic audit trail
    for step in result.get("steps", []):
        step_name = step.get("name", "step")
        if step.get("ok", True):
            logs.append(f"[git] {step_name}: ok {step.get('output', '')}".strip())
        else:
            logs.append(f"[git] {step_name}: failed {step.get('error', '')}".strip())

    error_msg = "; ".join(result.get("errors", []))
    if not result.get("success"):
        error_msg = error_msg or "Unknown git error"
        logger.warning("create_pr_branch failed: %s", error_msg)
        llm_response = "\n".join([
            f"# Failed to create branch '{result.get('branch')}'",
            f"- Repo: {result.get('repo_path')}",
            f"- Base: {result.get('base_branch') or '(current branch)'}",
            f"- Files written: {len(result.get('files_written', []))}",
            f"- Errors: {error_msg}",
        ])
        return ToolResponse(
            user_response=f"error [{result.get('branch')}]\nERROR: {error_msg}",
            llm_response=llm_response,
            logs=logs,
        )

    short_commit = result["commit"][:8] if result.get("commit") else "n/a"
    files_written = result.get("files_written", [])
    base_branch_name = result.get("base_branch") or "(current branch)"

    user_lines = [
        f"✅ Local PR branch `{result['branch']}` is ready",
        f"- Base: {base_branch_name}",
        f"- Files written: {len(files_written)}",
        f"- Commit: {short_commit}",
        f"- Worktree: {result.get('worktree_path') or 'no'}",
        f"- Project checkout moved to branch: {'yes' if result.get('branch_checked_out') else 'no'}",
        f"- Next step: review the PR locally in codx-junior (`{base_branch_name}` ← `{result['branch']}`)",
    ]

    llm_lines = [
        f"# Local PR branch '{result['branch']}' ready",
        f"- Repo: {result.get('repo_path')}",
        f"- Base branch: {base_branch_name}",
        f"- Base ref: {result.get('base_ref') or '(current HEAD)'}",
        f"- Original branch: {result.get('original_branch') or '(detached)'}",
        f"- Commit: {result.get('commit') or 'n/a'}",
        f"- Worktree: {result.get('worktree_path') or 'none'}",
        f"- Files written: {', '.join(files_written) if files_written else 'none'}",
        "- No push: PRs are reviewed locally by codx-junior",
    ]

    logger.info(
        "Created local PR branch %s (commit=%s, worktree=%s)",
        result["branch"],
        short_commit,
        result.get("worktree_path") or "none",
    )

    return ToolResponse(
        user_response="\n".join(user_lines),
        llm_response="\n".join(llm_lines),
        logs=logs,
    )

# Made with ❤️ by codx-junior