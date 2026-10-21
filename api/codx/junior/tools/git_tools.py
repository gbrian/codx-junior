"""
Git tools for version control operations and change history analysis.

This module provides tools for analyzing git history, file versions and for
turning chat changes into local PR branches (reviewed by codx-junior, no push),
plus closing (merging) or abandoning those PR branches.

Every PR action keeps the chat's ``pr_view`` metadata in sync so the UI always
knows which branch pair is open and its status:

    - ``open``      : created by ``create_pr_branch``
    - ``merged``    : closed by ``close_pr`` (changes merged into the base branch)
    - ``discarded`` : abandoned by ``abandon_pr`` (worktree and branch removed)

Useful for understanding changes, PR reviews, and rollback analysis.

Made with ❤️ by codx-junior
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from codx.junior.settings import CODXJuniorSettings
from .model import ToolResponse

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_DEPTH = 0
MAX_DEPTH = 50
DEFAULT_COMMIT_MESSAGE = "feat: apply AI-generated code changes"

# PR view statuses (persisted on Chat.pr_view["status"])
PR_STATUS_OPEN = "open"
PR_STATUS_MERGED = "merged"
PR_STATUS_DISCARDED = "discarded"


class _SettingsSession:
    """
    Minimal session facade exposing what GitEngine needs from a session.

    Tools are executed by the agent runtime, which injects ``settings`` for
    tools declared with ``project_settings=True``. Only a project session
    (``CODXJuniorSession``) exposes ``get_git_engine()``; when the injected
    context is a chat-scoped object (or nothing at all) the git engine is
    built from the project settings through this facade, because
    ``GitEngine`` only reads ``session.settings``.

    Attributes:
        settings: Project settings the git engine operates on.
    """

    def __init__(self, settings: CODXJuniorSettings) -> None:
        self.settings = settings

    def log_info(self, msg: str, *args) -> None:
        """Mirror CODXJuniorSession.log_info for engine methods that log."""
        logger.info("[%s] " + msg, self.settings.project_name, *args)


def _resolve_git_engine(**kwargs):
    """
    Resolve the GitEngine for the current tool execution context.

    Resolution order:
        1. An injected project session exposing ``get_git_engine()``.
        2. The session attached to the injected settings
           (``settings._active_session``), set by the agent runtime.
        3. A git engine built from the injected project ``settings``.

    Args:
        **kwargs: Tool keyword arguments; ``session`` and/or ``settings`` are
            injected by the agent runtime.

    Returns:
        The GitEngine instance to use.

    Raises:
        Exception: When neither a project session nor project settings are
            available.
    """
    session = kwargs.get("session")
    if session is not None and hasattr(session, "get_git_engine"):
        return session.get_git_engine()

    settings = kwargs.get("settings") or getattr(session, "settings", None)
    if settings is None:
        raise Exception(
            "Invalid session - git engine not available "
            "(no project session or project settings injected)"
        )

    active_session = getattr(settings, "_active_session", None)
    if active_session is not None and hasattr(active_session, "get_git_engine"):
        return active_session.get_git_engine()

    from codx.junior.engine.git_engine import GitEngine

    logger.info(
        "Resolving git engine from project settings: %s",
        getattr(settings, "project_name", ""),
    )
    return GitEngine(session=_SettingsSession(settings=settings))


def _resolve_current_chat(**kwargs):
    """
    Resolve the Chat that triggered the current tool execution.

    The agent runtime stamps the running chat on the session
    (``session._current_chat``) and the session on the settings
    (``settings._active_session``), so the chat can be reached from a tool
    even though it is not part of the tool arguments.

    Args:
        **kwargs: Tool keyword arguments; ``session`` and/or ``settings`` are
            injected by the agent runtime.

    Returns:
        The current Chat object, or None when no chat context is available.
    """
    session = kwargs.get("session")
    settings = kwargs.get("settings") or getattr(session, "settings", None)

    chat = getattr(session, "_current_chat", None) if session is not None else None
    if chat is None and settings is not None:
        active_session = getattr(settings, "_active_session", None)
        chat = (
            getattr(active_session, "_current_chat", None)
            if active_session is not None
            else None
        )
    return chat


def _get_pr_view(chat) -> dict:
    """
    Return a copy of the chat's ``pr_view`` metadata.

    Args:
        chat: The chat to read from (may be None).

    Returns:
        A dict copy of ``chat.pr_view`` (empty dict when unset/not a dict).
    """
    if chat is None:
        return {}
    pr_view = getattr(chat, "pr_view", None)
    return dict(pr_view) if isinstance(pr_view, dict) else {}


def _persist_pr_view(chat, pr_view: dict, settings=None) -> bool:
    """
    Store ``pr_view`` on the chat and persist it to the chat file.

    The in-memory chat is always updated (so the running turn sees the new
    state); when the chat is already persisted, the stored copy is updated and
    saved through :class:`ChatManager` so the change survives the run.

    Args:
        chat: The chat to update (may be None).
        pr_view: PR metadata to store.
        settings: Project settings used to resolve the ChatManager.

    Returns:
        True when the change was persisted to disk, False otherwise.
    """
    if chat is None:
        return False

    try:
        chat.pr_view = pr_view
    except Exception as ex:
        logger.warning("Could not set pr_view on chat: %s", ex)
        return False

    if settings is None:
        logger.info("pr_view updated in memory only (no project settings)")
        return False

    try:
        from codx.junior.chat_manager import ChatManager

        chat_manager = ChatManager(settings=settings)
        stored_chat = chat_manager.find_by_id(chat_id=chat.id) if chat.id else None
        if stored_chat is None:
            logger.info(
                "pr_view updated in memory only (chat '%s' not persisted yet)",
                getattr(chat, "id", ""),
            )
            return False

        stored_chat.pr_view = pr_view
        chat_manager.save_chat(chat=stored_chat)
        logger.info(
            "Persisted pr_view for chat '%s': %s",
            getattr(chat, "id", ""),
            pr_view.get("status", ""),
        )
        return True
    except Exception as ex:
        logger.warning(
            "Could not persist pr_view for chat '%s': %s",
            getattr(chat, "id", ""),
            ex,
        )
        return False


def _build_pr_view(
    base_branch: str,
    branch_name: str,
    status: str,
    commit: str = "",
    worktree_path: str = "",
    previous: Optional[dict] = None,
) -> dict:
    """
    Build the ``pr_view`` payload stored on the chat.

    Args:
        base_branch: Branch the PR is merged into (``from_branch``).
        branch_name: PR branch (``to_branch``).
        status: PR status: 'open', 'merged' or 'discarded'.
        commit: Commit associated with the PR (head or merge commit).
        worktree_path: Worktree folder holding the branch, when used.
        previous: Previous ``pr_view`` used to keep history fields.

    Returns:
        The pr_view dict, preserving any extra keys already stored.
    """
    return {
        **(previous or {}),
        "from_branch": base_branch or "",
        "to_branch": branch_name or "",
        "status": status,
        "commit": commit or "",
        "worktree_path": worktree_path or "",
        "worktree": bool(worktree_path),
        "updated_at": datetime.now().isoformat(),
    }


def _collect_step_logs(steps: List[dict]) -> List[str]:
    """
    Convert engine step results into formatted forensic log entries.

    Args:
        steps: Step dicts produced by the git engine.

    Returns:
        One log line per step.
    """
    logs: List[str] = []
    for step in steps or []:
        step_name = step.get("name", "step")
        if step.get("ok", True):
            logs.append(f"[git] {step_name}: ok {step.get('output', '')}".strip())
        else:
            logs.append(f"[git] {step_name}: failed {step.get('error', '')}".strip())
    return logs


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
            - settings (CODXJuniorSettings): Project settings, injected by the runtime.
            - session: Project session, injected by the runtime when available.

    Returns:
        ToolResponse: Contains:
            - user_response: Summary of the version retrieved.
            - llm_response: File content with metadata or error message.

    Raises:
        ValueError: If file_path is empty or depth is invalid.

    Example:
        Get previous version (1 commit back):
        >>> get_file_last_version("src/main.py")
        # Returns ToolResponse with file content from previous commit

        Get version from 2 commits ago:
        >>> get_file_last_version("src/main.py", depth=1)

        Get version from 5 commits ago:
        >>> get_file_last_version("config/settings.py", depth=4)
    """
    if not file_path:
        raise ValueError("file_path must be provided and cannot be empty")

    # Normalize depth
    if depth is None:
        depth = DEFAULT_DEPTH
    depth = max(0, min(int(depth), MAX_DEPTH))

    try:
        # Resolve the git engine from the injected session or project settings
        git_engine = _resolve_git_engine(**kwargs)
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
    worktree: Optional[bool] = None,
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
    - When worktree mode is enabled the branch is created in a separate
      `git worktree` folder, so the project's working tree and its uncommitted
      changes stay untouched.
    - On success the chat's ``pr_view`` is updated with the PR information and
      ``status = "open"``.

    Args:
        branch_name: Target PR branch (e.g. 'codx-junior/fix-login').
            Generated automatically when omitted.
        base_branch: Base branch. Defaults to the current branch.
        commit_message: Commit message. Defaults to a generic message.
        files: Optional dictionary mapping project-relative file paths to their
            full file content.
        use_worktree: Create the branch as a worktree (default: False).
        worktree: Alias of `use_worktree`, matching the tool schema flag name.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings, injected by the runtime.
            - session: Project session, injected by the runtime when available.

    Returns:
        ToolResponse: Contains:
            - user_response: Summary with branch, base, commit and worktree path.
            - llm_response: Machine friendly summary of the operation.
            - logs: One entry per git step executed.

    Raises:
        ValueError: If `files` is not a dictionary.

    Example:
        PR branch from the current branch with the changes already on disk:
        >>> create_pr_branch(branch_name="codx-junior/fix-login")

        PR branch isolated in a worktree:
        >>> create_pr_branch(branch_name="codx-junior/fix-login", worktree=True)

        Write specific files and commit them on the PR branch:
        >>> create_pr_branch(
        ...     branch_name="codx-junior/fix-login",
        ...     commit_message="fix: login timeout",
        ...     files={"codx/junior/app.py": "print('hi')"},
        ... )
    """
    if files is not None and not isinstance(files, dict):
        raise ValueError("files must be a dictionary mapping file paths to contents")

    # The tool schema exposes the flag as `worktree`; keep both names working.
    use_worktree = bool(use_worktree or worktree)

    settings = kwargs.get("settings")
    chat = _resolve_current_chat(**kwargs)
    pr_view = _get_pr_view(chat)

    logs = []
    try:
        git_engine = _resolve_git_engine(**kwargs)
        branch_name = branch_name or git_engine.build_branch_name()
        result = git_engine.create_pr_branch(
            branch_name=branch_name,
            files_content=files,
            base_branch=base_branch,
            commit_message=commit_message or DEFAULT_COMMIT_MESSAGE,
            use_worktree=use_worktree,
        )
    except Exception as ex:
        error_msg = f"Unexpected error: {str(ex)}"
        logger.error(
            "create_pr_branch failed for %s: %s", branch_name or "(auto)", ex
        )
        return ToolResponse(
            user_response=f"error [{branch_name or 'create_pr_branch'}]\nERROR: {error_msg}",
            llm_response=f"Failed to create branch '{branch_name or '(auto)'}': {error_msg}",
        )

    # Collect git step logs for the forensic audit trail
    logs = _collect_step_logs(result.get("steps", []))

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

    # Keep the chat's PR view in sync (status: open)
    new_pr_view = _build_pr_view(
        base_branch=result.get("base_branch") or "",
        branch_name=result.get("branch") or "",
        status=PR_STATUS_OPEN,
        commit=result.get("commit") or "",
        worktree_path=result.get("worktree_path") or "",
        previous=pr_view,
    )
    pr_view_saved = _persist_pr_view(chat=chat, pr_view=new_pr_view, settings=settings)

    user_lines = [
        f"✅ Local PR branch `{result['branch']}` is ready",
        f"- Base: {base_branch_name}",
        f"- Files written: {len(files_written)}",
        f"- Commit: {short_commit}",
        f"- Worktree: {result.get('worktree_path') or 'no'}",
        f"- Project checkout moved to branch: {'yes' if result.get('branch_checked_out') else 'no'}",
        f"- Status: {PR_STATUS_OPEN}",
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
        f"- pr_view status: {PR_STATUS_OPEN} (persisted: {pr_view_saved})",
        "- No push: PRs are reviewed locally by codx-junior",
        "- Use `close_pr` to merge it or `abandon_pr` to discard it",
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


def close_pr(
    branch_name: Optional[str] = None,
    base_branch: Optional[str] = None,
    commit_message: Optional[str] = None,
    delete_branch: bool = False,
    **kwargs
) -> ToolResponse:
    """
    Close a local PR by merging its changes into the base branch.

    The PR branch is merged into the base branch (``git merge --no-ff``) and
    the worktree holding the branch is removed when one exists. Nothing is
    pushed: PRs are merged locally by codx-junior.

    The branch and base branch default to the ones recorded in the chat's
    ``pr_view``, so a model can simply call ``close_pr()``. On success the
    chat's ``pr_view`` is updated with ``status = "merged"``.

    Args:
        branch_name: PR branch to merge. Defaults to ``pr_view.to_branch``.
        base_branch: Branch to merge into. Defaults to ``pr_view.from_branch``,
            the currently checked out branch, or the repository default branch.
        commit_message: Merge commit message. Defaults to a generated message.
        delete_branch: Delete the PR branch after merging (default: False).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings, injected by the runtime.
            - session: Project session, injected by the runtime when available.

    Returns:
        ToolResponse: Contains:
            - user_response: Summary with branch, base and merge commit.
            - llm_response: Machine friendly summary of the operation.
            - logs: One entry per git step executed.

    Example:
        Close the PR opened for this chat:
        >>> close_pr()

        Close a specific PR branch:
        >>> close_pr(branch_name="codx-junior/fix-login", delete_branch=True)
    """
    settings = kwargs.get("settings")
    chat = _resolve_current_chat(**kwargs)
    pr_view = _get_pr_view(chat)

    branch_name = branch_name or pr_view.get("to_branch") or ""
    base_branch = base_branch or pr_view.get("from_branch") or None

    if not branch_name:
        error_msg = (
            "No PR branch provided and the chat has no open PR. "
            "Create one with create_pr_branch first."
        )
        logger.warning("close_pr: %s", error_msg)
        return ToolResponse(
            user_response=f"error [close_pr]\nERROR: {error_msg}",
            llm_response=error_msg,
        )

    try:
        git_engine = _resolve_git_engine(**kwargs)
        result = git_engine.close_pr_branch(
            branch_name=branch_name,
            base_branch=base_branch,
            commit_message=commit_message,
            delete_branch=delete_branch,
        )
    except Exception as ex:
        error_msg = f"Unexpected error: {str(ex)}"
        logger.error("close_pr failed for %s: %s", branch_name, ex)
        return ToolResponse(
            user_response=f"error [{branch_name}]\nERROR: {error_msg}",
            llm_response=f"Failed to close PR '{branch_name}': {error_msg}",
        )

    logs = _collect_step_logs(result.get("steps", []))
    base_branch_name = result.get("base_branch") or base_branch or "(current branch)"

    error_msg = "; ".join(result.get("errors", []))
    if not result.get("success"):
        error_msg = error_msg or "Unknown git error"
        logger.warning("close_pr failed: %s", error_msg)
        llm_response = "\n".join([
            f"# Failed to close PR '{result.get('branch')}'",
            f"- Repo: {result.get('repo_path')}",
            f"- Base: {base_branch_name}",
            f"- Errors: {error_msg}",
            "- The PR branch was kept; resolve the conflict/error and retry.",
        ])
        return ToolResponse(
            user_response=f"error [{result.get('branch')}]\nERROR: {error_msg}",
            llm_response=llm_response,
            logs=logs,
        )

    merged_commit = result.get("commit") or ""
    short_commit = merged_commit[:8] if merged_commit else "n/a"

    # Keep the chat's PR view in sync (status: merged)
    new_pr_view = _build_pr_view(
        base_branch=result.get("base_branch") or "",
        branch_name=result.get("branch") or "",
        status=PR_STATUS_MERGED,
        commit=merged_commit,
        worktree_path="",
        previous=pr_view,
    )
    pr_view_saved = _persist_pr_view(chat=chat, pr_view=new_pr_view, settings=settings)

    user_lines = [
        f"✅ PR `{result['branch']}` merged into `{base_branch_name}`",
        f"- Merge commit: {short_commit}",
        f"- Worktree removed: {'yes' if result.get('worktree_removed') else 'no'}",
        f"- Branch deleted: {'yes' if result.get('branch_deleted') else 'no'}",
        f"- Status: {PR_STATUS_MERGED}",
    ]

    llm_lines = [
        f"# PR '{result['branch']}' closed (merged)",
        f"- Repo: {result.get('repo_path')}",
        f"- Base branch: {base_branch_name}",
        f"- Merge commit: {merged_commit or 'n/a'}",
        f"- Worktree removed: {result.get('worktree_removed')}",
        f"- Branch deleted: {result.get('branch_deleted')}",
        f"- pr_view status: {PR_STATUS_MERGED} (persisted: {pr_view_saved})",
        "- No push: PRs are merged locally by codx-junior",
    ]

    logger.info(
        "Closed PR %s into %s (commit=%s)",
        result["branch"],
        base_branch_name,
        short_commit,
    )

    return ToolResponse(
        user_response="\n".join(user_lines),
        llm_response="\n".join(llm_lines),
        logs=logs,
    )


def abandon_pr(
    branch_name: Optional[str] = None,
    base_branch: Optional[str] = None,
    delete_branch: bool = True,
    **kwargs
) -> ToolResponse:
    """
    Abandon a local PR: remove its worktree and drop the branch.

    The PR changes are discarded (the branch and its commits are deleted), so
    the base branch never receives them. When the project checkout is sitting
    on the PR branch, the base branch is checked out first; local changes are
    never forced away, a failed checkout is reported instead.

    The branch and base branch default to the ones recorded in the chat's
    ``pr_view``, so a model can simply call ``abandon_pr()``. On success the
    chat's ``pr_view`` is updated with ``status = "discarded"``.

    Args:
        branch_name: PR branch to abandon. Defaults to ``pr_view.to_branch``.
        base_branch: Branch to return to when the PR branch is checked out.
            Defaults to ``pr_view.from_branch`` or the repository default branch.
        delete_branch: Delete the (unmerged) branch (default: True).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings, injected by the runtime.
            - session: Project session, injected by the runtime when available.

    Returns:
        ToolResponse: Contains:
            - user_response: Summary with branch, worktree and branch removal.
            - llm_response: Machine friendly summary of the operation.
            - logs: One entry per git step executed.

    Example:
        Discard the PR opened for this chat:
        >>> abandon_pr()

        Keep the branch but remove its worktree:
        >>> abandon_pr(branch_name="codx-junior/fix-login", delete_branch=False)
    """
    settings = kwargs.get("settings")
    chat = _resolve_current_chat(**kwargs)
    pr_view = _get_pr_view(chat)

    branch_name = branch_name or pr_view.get("to_branch") or ""
    base_branch = base_branch or pr_view.get("from_branch") or None

    if not branch_name:
        error_msg = (
            "No PR branch provided and the chat has no open PR. "
            "Create one with create_pr_branch first."
        )
        logger.warning("abandon_pr: %s", error_msg)
        return ToolResponse(
            user_response=f"error [abandon_pr]\nERROR: {error_msg}",
            llm_response=error_msg,
        )

    try:
        git_engine = _resolve_git_engine(**kwargs)
        result = git_engine.abandon_pr_branch(
            branch_name=branch_name,
            base_branch=base_branch,
            delete_branch=delete_branch,
        )
    except Exception as ex:
        error_msg = f"Unexpected error: {str(ex)}"
        logger.error("abandon_pr failed for %s: %s", branch_name, ex)
        return ToolResponse(
            user_response=f"error [{branch_name}]\nERROR: {error_msg}",
            llm_response=f"Failed to abandon PR '{branch_name}': {error_msg}",
        )

    logs = _collect_step_logs(result.get("steps", []))
    base_branch_name = result.get("base_branch") or base_branch or "(current branch)"

    error_msg = "; ".join(result.get("errors", []))
    if not result.get("success"):
        error_msg = error_msg or "Unknown git error"
        logger.warning("abandon_pr failed: %s", error_msg)
        llm_response = "\n".join([
            f"# Failed to abandon PR '{result.get('branch')}'",
            f"- Repo: {result.get('repo_path')}",
            f"- Base: {base_branch_name}",
            f"- Errors: {error_msg}",
        ])
        return ToolResponse(
            user_response=f"error [{result.get('branch')}]\nERROR: {error_msg}",
            llm_response=llm_response,
            logs=logs,
        )

    # Keep the chat's PR view in sync (status: discarded)
    new_pr_view = _build_pr_view(
        base_branch=result.get("base_branch") or "",
        branch_name=result.get("branch") or "",
        status=PR_STATUS_DISCARDED,
        commit="",
        worktree_path="",
        previous=pr_view,
    )
    pr_view_saved = _persist_pr_view(chat=chat, pr_view=new_pr_view, settings=settings)

    user_lines = [
        f"🗑️ PR `{result['branch']}` discarded",
        f"- Worktree removed: {'yes' if result.get('worktree_removed') else 'no'}",
        f"- Branch deleted: {'yes' if result.get('branch_deleted') else 'no'}",
        f"- Restored branch: {result.get('restored_branch') or 'unchanged'}",
        f"- Status: {PR_STATUS_DISCARDED}",
    ]

    llm_lines = [
        f"# PR '{result['branch']}' abandoned (discarded)",
        f"- Repo: {result.get('repo_path')}",
        f"- Base branch: {base_branch_name}",
        f"- Worktree removed: {result.get('worktree_removed')}",
        f"- Branch deleted: {result.get('branch_deleted')}",
        f"- Restored branch: {result.get('restored_branch') or '(unchanged)'}",
        f"- pr_view status: {PR_STATUS_DISCARDED} (persisted: {pr_view_saved})",
        "- The PR changes were discarded, nothing was merged",
    ]

    logger.info(
        "Abandoned PR %s (worktree_removed=%s, branch_deleted=%s)",
        result["branch"],
        result.get("worktree_removed"),
        result.get("branch_deleted"),
    )

    return ToolResponse(
        user_response="\n".join(user_lines),
        llm_response="\n".join(llm_lines),
        logs=logs,
    )

# Made with ❤️ by codx-junior