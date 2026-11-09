"""
Git sub-engine for codx-junior.
Handles all git/branch/PR operations.

Made with ❤️ by codx-junior
"""

import base64
import codecs
import json
import logging
import os
import re
import shutil
import subprocess

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from codx.junior.project.project_discover import find_project_parents
from codx.junior.utils.utils import exec_command

if TYPE_CHECKING:
    from codx.junior.engine.session import CODXJuniorSession

logger = logging.getLogger(__name__)

DEFAULT_BRANCH_PREFIX = "codx-junior"
DEFAULT_COMMIT_MESSAGE = "feat: apply AI-generated code changes"
DEFAULT_REMOTE = "origin"

# Username sent with the project token: GitHub, GitLab, Bitbucket and Azure
# DevOps accept any non empty username as long as the token is the password
DEFAULT_TOKEN_USERNAME = "x-access-token"

# Git config key carrying the HTTP Basic credentials of a single command
TOKEN_ARG_PREFIX = "http.extraheader="

# Replacement used when a command carrying the token is logged or returned
TOKEN_VALUE_MASK = "********"

# Git errors meaning the remote rejected the (missing) credentials
AUTH_ERROR_PATTERNS = (
    "could not read username",
    "could not read password",
    "authentication failed",
    "invalid username or password",
    "permission denied (publickey)",
    "terminal prompts disabled",
    "support for password authentication was removed",
    "403 forbidden",
    "401 unauthorized",
    "repository not found",
)

# Actionable hint appended to authentication failures
AUTH_ERROR_HINT = (
    "The remote rejected the git credentials. Configure a project access token "
    "(PAT) in Project settings > Git > Access token, or use an SSH remote "
    "(git@host:owner/repo.git) with a mounted SSH key."
)

# Lock file git creates while the index is being written
INDEX_LOCK_FILE = "index.lock"

# Ignore file at the root of the checkout the view is working on
GITIGNORE_FILE = ".gitignore"

# Porcelain status code -> semantic status name
PORCELAIN_STATUS = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "T": "typechange",
    "U": "conflict",
    "?": "untracked",
}

# Arguments used everywhere the working tree status is read.
# ``--porcelain`` keeps the output stable across git versions (and locale
# independent) and ``--untracked-files=all`` expands untracked *directories*
# into the files they contain: without it git collapses them into a single
# ``?? folder/`` entry, which made the change lists (``changed_files``,
# ``staged``, ``unstaged``) return folder paths instead of files.
# A *nested* repository (submodule / embedded repository) is never expanded by
# git, it is reported as a single ``?? folder/`` entry and dropped by
# ``_filter_nested_repos``: those files belong to the nested repository.
STATUS_ARGS = ("status", "--porcelain", "--untracked-files=all")

# Start of one file patch inside a multi-file diff
DIFF_SPLIT_PATTERN = re.compile(r"(?m)^(?=diff --git )")

# `diff --git a/<old> b/<new>` header (git quotes paths with special chars)
DIFF_HEADER_PATH_PATTERN = re.compile(r'^diff --git "?a/(.+?)"? "?b/(.+?)"?$')

# Record separator used to delimit commits while reading `git log --name-only`
LOG_COMMIT_SEPARATOR = "\x01"


class GitEngine:
    """
    Handles git repository operations including branches, diffs and PRs.

    ```mermaid
    flowchart TD
        GE[GitEngine]
        GE --> get_git_identity
        GE --> _configured_identity
        GE --> _git_config_identity
        GE --> _identity_args
        GE --> get_git_access_token
        GE --> _token_args
        GE --> _mask_token_args
        GE --> get_git_token_info
        GE --> _auth_error_hint
        GE --> get_repo_branches
        GE --> get_repo_changes
        GE --> get_pr_review_details
        GE --> get_branch_details
        GE --> find_git_root_path
        GE --> get_commit_list
        GE --> get_commit_changes
        GE --> reset_project_file
        GE --> diff_file
        GE --> get_file_version_at_depth
        GE --> get_working_tree_status
        GE --> get_status_changes
        GE --> stage_changes
        GE --> build_branch_name
        GE --> create_pr_branch
        GE --> close_pr_branch
        GE --> abandon_pr_branch
        GE --> get_worktrees_path
        GE --> get_repo_info
        GE --> get_repo_status
        GE --> get_lock_info
        GE --> release_lock
        GE --> fetch_remote
        GE --> pull_remote
        GE --> push_remote
        GE --> create_branch
        GE --> checkout_branch
        GE --> delete_branch
        GE --> commit_changes
        GE --> merge_branches
    ```
    """

    def __init__(self, session: "CODXJuniorSession") -> None:
        """Initialize with a reference to the parent session."""
        self.session = session
        # Resolved git identity ({ name, email, source }), cached because it is
        # applied to every git command
        self._git_identity: Optional[Dict[str, str]] = None

    @property
    def settings(self):
        """Shortcut to session settings."""
        return self.session.settings

    def _sanitize_branch_name(self, branch: str) -> str:
        """
        Sanitize branch name by removing prefixes like '* ' or '+ worktree/'.
        Keeps the last part after splitting by space.
        
        Args:
            branch: Raw branch name that may contain prefixes.
            
        Returns:
            Cleaned branch name.
        """
        if not branch:
            return branch
        
        # Remove common git branch prefixes
        cleaned = branch.lstrip("* +").strip()
        
        # If there's still a space, take the last part (handles "worktree/branch" cases)
        if " " in cleaned:
            cleaned = cleaned.split()[-1]
        
        return cleaned

    @staticmethod
    def _unquote_git_path(value: str) -> str:
        """Decode the quoting git applies to paths with special characters."""
        value = (value or "").strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
            try:
                return codecs.escape_decode(value.encode("utf-8"))[0].decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                return value
        return value

    def _split_file_patches(self, diff: str) -> Dict[str, str]:
        """
        Split a multi-file diff into one patch per file.

        A single ``git diff`` plus this split is much faster than one ``git
        diff`` per file, which matters on large change sets (a branch with
        hundreds of files, a working tree with generated folders...).

        Args:
            diff: Output of ``git diff`` (possibly empty).

        Returns:
            Dict mapping the repo-relative new path to its patch.

        Example:
            >>> patches = engine._split_file_patches(diff)
            >>> patches["app.py"].startswith("diff --git")
            True
        """
        patches: Dict[str, str] = {}
        for chunk in DIFF_SPLIT_PATTERN.split(diff or ""):
            chunk = chunk.strip()
            if not chunk:
                continue
            header = chunk.split("\n", 1)[0]
            match = DIFF_HEADER_PATH_PATTERN.match(header)
            if not match:
                continue
            path = self._unquote_git_path(match.group(2))
            if path:
                patches[path] = chunk
        return patches

    def _commits_by_file(self, to_ref: str, from_ref: str) -> Dict[str, list]:
        """
        Return the commits in ``to_ref..from_ref`` grouped by changed file.

        One ``git log --name-only`` gives the full map, replacing one ``git
        log`` per changed file (the expensive part of a branch comparison).

        Args:
            to_ref: Base ref (exclusive).
            from_ref: Source ref (inclusive).

        Returns:
            Dict mapping file path to the list of commits that touched it.
        """
        pretty = (
            f'{LOG_COMMIT_SEPARATOR}{{ "commit": "%H", "author": "%an", '
            '"date": "%as", "message": "%f" }'
        )
        result = self._run_git([
            "log",
            f"--pretty=format:{pretty}",
            "--name-only",
            f"{to_ref}..{from_ref}",
        ])
        if not result["ok"]:
            logger.warning(
                "Could not read the commits between %s and %s: %s",
                to_ref,
                from_ref,
                result["error"],
            )
            return {}

        commits_by_file: Dict[str, list] = {}
        current = None
        for line in result["output"].splitlines():
            if line.startswith(LOG_COMMIT_SEPARATOR):
                try:
                    current = json.loads(line[len(LOG_COMMIT_SEPARATOR):])
                except Exception:
                    current = None
                continue
            path = line.strip()
            if not path or current is None:
                continue
            commits_by_file.setdefault(path, []).append(current)
        return commits_by_file

    def _get_repo_root(self) -> str:
        """
        Return the git root path for the project, falling back to the project path.

        Returns:
            Absolute path of the repository root.
        """
        return self.find_git_root_path() or self.settings.abs_project_path

    @staticmethod
    def _same_path(first: Optional[str], second: Optional[str]) -> bool:
        """
        Compare two filesystem paths as the same location.

        ``normpath`` alone misses bind mounts and symlinks (the same checkout can
        be reached through ``/home/user/projects/app`` and
        ``/home/user/app``), which made the main checkout look like a removable
        worktree. ``realpath`` resolves those aliases.

        Args:
            first: First path.
            second: Second path.

        Returns:
            True when both paths point to the same location.
        """
        if not first or not second:
            return False
        return os.path.normcase(os.path.realpath(first)) == os.path.normcase(
            os.path.realpath(second)
        )

    # -------------------------------------------------------------------------
    # Git identity (project settings -> global settings -> git config)
    # -------------------------------------------------------------------------

    def _configured_identity(self) -> Dict[str, str]:
        """
        Return the git identity stored in the project and global settings.

        The project values (`git_user_name` / `git_user_email`) win over the
        global ones (`git.username` / `git.email`), so a single project can
        commit with a different author than the rest of the installation.

        Returns:
            Dict with 'name', 'email' and 'source' ('project', 'global' or an
            empty string when nothing is configured).

        Example:
            >>> engine._configured_identity()
            {'name': 'Jane Doe', 'email': 'jane@acme.com', 'source': 'project'}
        """
        name = str(getattr(self.settings, "git_user_name", "") or "").strip()
        email = str(getattr(self.settings, "git_user_email", "") or "").strip()
        source = "project" if (name or email) else ""

        if name and email:
            return {"name": name, "email": email, "source": source}

        # Fall back to the global settings (installation wide identity)
        global_git = None
        try:
            from codx.junior.global_settings import get_global_settings

            global_git = getattr(get_global_settings(), "git", None)
        except Exception as ex:
            logger.warning("Could not read the global git settings: %s", ex)

        global_name = str(getattr(global_git, "username", "") or "").strip()
        global_email = str(getattr(global_git, "email", "") or "").strip()

        if not name and global_name:
            name = global_name
            source = source or "global"
        if not email and global_email:
            email = global_email
            source = source or "global"

        return {"name": name, "email": email, "source": source}

    def _git_config_identity(self) -> Dict[str, str]:
        """
        Read `user.name` and `user.email` from the repository git configuration.

        Used as the last fallback, so an identity already configured for the
        repository is never wiped by empty project settings. The git calls skip
        the identity override, otherwise resolving the identity would require
        the identity itself.

        Returns:
            Dict with 'name' and 'email' (empty strings when not configured).
        """
        name = self._run_git(
            ["config", "--get", "user.name"], apply_identity=False, apply_token=False
        )
        email = self._run_git(
            ["config", "--get", "user.email"], apply_identity=False, apply_token=False
        )
        return {
            "name": name["output"] if name["ok"] else "",
            "email": email["output"] if email["ok"] else "",
        }

    def get_git_identity(self, refresh: bool = False) -> dict:
        """
        Return the identity every repository operation is signed with.

        Resolution order:
            1. project settings (`git_user_name` / `git_user_email`)
            2. global settings (`git.username` / `git.email`)
            3. the git configuration (`user.name` / `user.email`)

        The result is cached: it is applied to every git command.

        Args:
            refresh: Re-read the settings instead of returning the cache.

        Returns:
            Dict with 'name', 'email' and 'source' ('project', 'global',
            'git-config' or '' when the identity is unknown).

        Example:
            >>> engine.get_git_identity()["email"]
            'jane@acme.com'
        """
        if self._git_identity and not refresh:
            return dict(self._git_identity)

        identity = self._configured_identity()
        if not identity["name"] or not identity["email"]:
            config_identity = self._git_config_identity()
            if not identity["name"]:
                identity["name"] = config_identity["name"]
            if not identity["email"]:
                identity["email"] = config_identity["email"]
            if not identity["source"] and (identity["name"] or identity["email"]):
                identity["source"] = "git-config"

        self._git_identity = identity
        return dict(identity)

    def _identity_args(self) -> List[str]:
        """
        Return the `-c` overrides that sign a git command with the identity.

        ``-c user.name=... -c user.email=...`` must be placed before the
        subcommand: every git command that records an author or a committer
        (commit, merge, rebase, cherry-pick, tag) then uses it, without changing
        the repository or the global git configuration.

        Returns:
            Git argument list, empty when no identity is configured.

        Example:
            >>> engine._identity_args()
            ['-c', 'user.name=Jane Doe', '-c', 'user.email=jane@acme.com']
        """
        identity = self.get_git_identity()
        args: List[str] = []
        if identity["name"]:
            args += ["-c", f"user.name={identity['name']}"]
        if identity["email"]:
            args += ["-c", f"user.email={identity['email']}"]
        return args

    # -------------------------------------------------------------------------
    # Git access token (PAT, managed in the project settings)
    # -------------------------------------------------------------------------

    def get_git_access_token(self) -> str:
        """
        Return the project git access token (PAT) used to authenticate remotes.

        The value comes from the project settings (`git_access_token`), the
        global git settings or the environment, and may reference an environment
        variable (`${GITHUB_TOKEN}`), so the secret can live outside the project
        file. An unresolved reference (unset variable) is ignored instead of
        being sent to the remote.

        Returns:
            Token string, empty when no usable token is configured.

        Example:
            >>> engine.get_git_access_token()
            'ghp_1234567890abcdef'
        """
        getter = getattr(self.settings, "get_git_access_token", None)
        if callable(getter):
            return str(getter() or "").strip()

        # Settings object without the helper (older project files)
        raw = str(getattr(self.settings, "git_access_token", "") or "").strip()
        if not raw:
            return ""
        expanded = os.path.expandvars(raw).strip()
        if expanded.startswith("${") and expanded.endswith("}"):
            return ""
        return expanded

    def _token_args(self) -> List[str]:
        """
        Return the `-c` override that authenticates a command with the token.

        The PAT is sent as an HTTP Basic credential
        (`x-access-token:<token>`) for the current command only: nothing is
        written to the repository config, to the global git config or to a
        credential store, so the token never persists on disk. The HTTP header
        is only used by the HTTP transport, which makes it a no-op for SSH and
        local remotes.

        Returns:
            Git argument list, empty when no token is configured.

        Example:
            >>> engine._token_args()
            ['-c', 'http.extraheader=Authorization: Basic eC1hY2Nlc3MtdG9rZW46Z2hw']
        """
        token = self.get_git_access_token()
        if not token:
            return []

        credentials = f"{DEFAULT_TOKEN_USERNAME}:{token}".encode("utf-8")
        encoded = base64.b64encode(credentials).decode("ascii")
        return ["-c", f"{TOKEN_ARG_PREFIX}Authorization: Basic {encoded}"]

    def _mask_token_args(self, command_str: str, token_args: List[str]) -> str:
        """
        Replace the credentials of a git command string with a mask.

        Commands are logged and returned in the 'command' result field, so the
        base64 credential must never be shown as is.

        Args:
            command_str: Full command string.
            token_args: Arguments returned by ``_token_args``.

        Returns:
            Command string where `http.extraheader=Authorization: Basic ...`
            is replaced by `http.extraheader=********`.

        Example:
            >>> engine._mask_token_args(
            ...     "git -c http.extraheader=Authorization: Basic abc push",
            ...     ["-c", "http.extraheader=Authorization: Basic abc"])
            'git -c http.extraheader=******** push'
        """
        masked = command_str
        for arg in token_args:
            masked = masked.replace(arg, f"{TOKEN_ARG_PREFIX}{TOKEN_VALUE_MASK}")
        return masked

    def get_git_token_info(self) -> dict:
        """
        Return whether remote operations are authenticated with a token.

        The token itself is never returned (it is a secret): the UI only learns
        whether one is configured.

        Returns:
            Dict with 'configured' and 'source' ('project' or '').

        Example:
            >>> engine.get_git_token_info()
            {'configured': True, 'source': 'project'}
        """
        configured = bool(self.get_git_access_token())
        return {"configured": configured, "source": "project" if configured else ""}

    def _auth_error_hint(self, error_text: str) -> str:
        """
        Return an actionable hint when git failed because of missing credentials.

        A headless API cannot answer the interactive username prompt, so a push
        to a private HTTPS remote fails with
        ``fatal: could not read Username for 'https://host': No such device``.
        Returning the raw message leaves the user without a way forward, so the
        hint explains how to configure the project access token.

        Args:
            error_text: Stderr of the failed git command.

        Returns:
            Hint message, or an empty string when the failure is not about
            authentication.

        Example:
            >>> engine._auth_error_hint("fatal: could not read Username for ...")
            'The remote rejected the git credentials. Configure a project ...'
        """
        text = (error_text or "").lower()
        if not text:
            return ""
        if any(pattern in text for pattern in AUTH_ERROR_PATTERNS):
            return AUTH_ERROR_HINT
        return ""

    def _run_git(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        strip_output: bool = True,
        apply_identity: bool = True,
        apply_token: bool = True,
    ) -> dict:
        """
        Run a git command without a shell and return a structured result.

        Uses ``subprocess.run`` with an argument list so branch names and file
        paths never need shell quoting, and stdout/stderr stay separated (unlike
        ``exec_command``, which merges stderr into stdout).

        The project git identity (see ``get_git_identity``) is passed as
        ``-c user.name`` / ``-c user.email``, so every commit, merge or rebase
        performed by the engine is signed with the project author. The project
        access token (see ``get_git_access_token``) is passed as an HTTP Basic
        header, so push/pull/fetch work on private remotes without storing any
        credential.

        Args:
            args: Git arguments, e.g. ``["checkout", "-b", "feature/x"]``.
            cwd: Working directory. Defaults to the repository root.
            strip_output: Strip leading/trailing whitespace from stdout. Set it
                to False for commands whose leading spaces carry meaning, such
                as ``git status --porcelain``.
            apply_identity: Inject the git identity overrides (disable it while
                resolving the identity itself).
            apply_token: Authenticate the command with the project token (the
                credential is masked in the returned 'command' and in the logs).

        Returns:
            Dict with 'ok', 'command', 'output', 'error' and 'returncode'.
        """
        cwd = cwd or self._get_repo_root()
        identity_args = self._identity_args() if apply_identity else []
        token_args = self._token_args() if apply_token else []
        command = ["git"] + identity_args + token_args + list(args)
        # The token is a secret: it must never reach the logs
        command_str = self._mask_token_args(" ".join(command), token_args)
        logger.info("git command: %s (cwd=%s)", command_str, cwd)
        try:
            completed = subprocess.run(
                command, cwd=cwd, text=True, capture_output=True
            )
        except Exception as ex:
            logger.error("Error running '%s': %s", command_str, ex)
            return {
                "ok": False,
                "command": command_str,
                "output": "",
                "error": str(ex),
                "returncode": -1,
            }

        raw_output = completed.stdout or ""
        output = raw_output.strip() if strip_output else raw_output
        error = (completed.stderr or "").strip()
        ok = completed.returncode == 0
        if not ok:
            logger.warning("git command failed: %s. %s", command_str, error)
        return {
            "ok": ok,
            "command": command_str,
            "output": output,
            "error": error,
            "returncode": completed.returncode,
        }

    def _ref_exists(self, ref: str, cwd: Optional[str] = None) -> bool:
        """
        Check whether a git ref (branch, remote branch or commit) exists.

        Args:
            ref: Full ref name, e.g. ``refs/heads/main`` or ``origin/main``.
            cwd: Working directory. Defaults to the repository root.

        Returns:
            True when the ref can be resolved.
        """
        result = self._run_git(["rev-parse", "--verify", "--quiet", ref], cwd=cwd)
        return bool(result["ok"] and result["output"])

    def _resolve_base_ref(self, base_branch: Optional[str], cwd: str) -> Optional[str]:
        """
        Resolve the ref a new PR branch should be created from.

        Local branches are preferred (PRs are reviewed locally) and the remote
        tracking branch is used as a fallback.

        Args:
            base_branch: Base branch name, may be empty.
            cwd: Working directory (repository root).

        Returns:
            Resolvable ref name, or None when the base branch is unknown.
        """
        if not base_branch:
            return None

        base_branch = self._sanitize_branch_name(base_branch)
        for candidate in (
            f"refs/heads/{base_branch}",
            f"refs/remotes/origin/{base_branch}",
        ):
            if self._ref_exists(candidate, cwd=cwd):
                return candidate

        logger.warning("Base branch not found: %s", base_branch)
        return None

    def _get_remote_url(self, remote: str = DEFAULT_REMOTE) -> str:
        """
        Return the configured URL for a remote.

        Args:
            remote: Remote name.

        Returns:
            Remote URL, or an empty string when the remote is not configured.
        """
        result = self._run_git(["config", "--get", f"remote.{remote}.url"])
        return result["output"] if result["ok"] else ""

    def _get_ahead_behind(
        self, branch: str, remote: str = DEFAULT_REMOTE
    ) -> Tuple[int, int]:
        """
        Return how many commits the local branch is ahead/behind its remote.

        Args:
            branch: Local branch name.
            remote: Remote name.

        Returns:
            Tuple of ``(ahead, behind)``; ``(0, 0)`` when there is no upstream.
        """
        if not branch:
            return 0, 0

        upstream = f"{remote}/{branch}"
        if not self._ref_exists(f"refs/remotes/{upstream}"):
            return 0, 0

        result = self._run_git(
            ["rev-list", "--left-right", "--count", f"{upstream}...{branch}"]
        )
        if not result["ok"] or not result["output"]:
            return 0, 0

        try:
            behind, ahead = result["output"].split()
        except ValueError:
            return 0, 0
        return int(ahead), int(behind)

    def _ensure_local_branch(
        self, branch: str, remote: str = DEFAULT_REMOTE
    ) -> dict:
        """
        Make sure a branch exists locally, creating it from the remote if needed.

        Args:
            branch: Branch name.
            remote: Remote name.

        Returns:
            Dict with 'ok', 'created' and 'error'.
        """
        if self._ref_exists(f"refs/heads/{branch}"):
            return {"ok": True, "created": False, "error": ""}

        if self._ref_exists(f"refs/remotes/{remote}/{branch}"):
            result = self._run_git(
                ["checkout", "-b", branch, f"{remote}/{branch}"]
            )
            return {
                "ok": result["ok"],
                "created": result["ok"],
                "error": result["error"],
            }

        return {
            "ok": False,
            "created": False,
            "error": f"Branch '{branch}' does not exist",
        }

    def _git_operation_result(self, command_result: dict, **extra) -> dict:
        """
        Convert a ``_run_git`` result into an operation result dict.

        Failures caused by a stale index lock are flagged with 'locked' and
        'lock_path' so the caller can offer to release the lock. Failures caused
        by rejected credentials are flagged with 'auth_error' and get an
        actionable hint appended, so the UI never shows a bare
        ``could not read Username``.

        Args:
            command_result: Dict returned by ``_run_git``.
            extra: Additional fields merged into the result.

        Returns:
            Dict with 'success', 'command', 'output' and 'errors'.
        """
        ok = bool(command_result.get("ok"))
        error = command_result.get("error") or ""
        result = {
            "success": ok,
            "command": command_result.get("command", ""),
            "output": command_result.get("output", ""),
            "errors": [] if ok else [error or "git command failed"],
            **extra,
        }
        if not ok:
            result.update(self._lock_error_info(error))
            auth_hint = self._auth_error_hint(error)
            if auth_hint:
                result["auth_error"] = True
                result["errors"].append(auth_hint)
        return result

    def _git_operation_error(self, message: str, **extra) -> dict:
        """
        Build a failed operation result dict.

        Args:
            message: Human readable error message.
            extra: Additional fields merged into the result.

        Returns:
            Dict with 'success' set to False and the message in 'errors'.
        """
        return {"success": False, "errors": [message], **extra}

    def _lock_error_info(self, error_text: str) -> dict:
        """
        Detect a stale index lock in a failed git command output.

        Git refuses to write the index while ``.git/index.lock`` exists and
        reports ``Unable to create '.../index.lock': File exists``. Such a
        failure is returned with 'locked' and 'lock_path' so the UI can offer to
        release the lock instead of showing an opaque git error.

        Args:
            error_text: Stderr of the failed git command.

        Returns:
            Dict with 'locked' and 'lock_path' when the command failed because
            of the index lock, an empty dict otherwise.
        """
        text = (error_text or "").lower()
        lock_blocked = "index.lock" in text and (
            "file exists" in text or "unable to create" in text
        )
        if not lock_blocked:
            return {}
        info = self.get_lock_info()
        return {"locked": True, "lock_path": info.get("path", "")}

    def _get_file_last_modification(self, file_path: str) -> Optional[str]:
        """
        Return the last modification datetime of a file as an ISO 8601 string.
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.settings.abs_project_path, file_path)
        try:
            if not os.path.isfile(file_path):
                return None
            mtime = os.path.getmtime(file_path)
        except (OSError, IOError):
            # The file may be removed between the status read and the stat
            # (working trees with generated folders change while being read).
            return None
        return datetime.fromtimestamp(mtime).isoformat()

    def _get_git_root_for_file(self, file_path: str) -> str:
        """
        Determine the Git root for a given file, allowing for subprojects.

        Args:
            file_path: The path to the file.

        Returns:
            The absolute Git root path.
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.settings.abs_project_path, file_path)
            
        current_path = os.path.dirname(file_path)
        
        while current_path != os.path.dirname(current_path):
            if os.path.exists(os.path.join(current_path, '.git')):
                return current_path
            current_path = os.path.dirname(current_path)
            
        return self.find_git_root_path()

    def _write_repo_file(self, repo_path: str, file_path: str, content: str) -> dict:
        """
        Write a file inside a repository (or worktree), creating parent folders.

        Paths escaping the repository root are rejected.

        Args:
            repo_path: Absolute repository (or worktree) root.
            file_path: Relative (to the repo) or absolute file path.
            content: Full file content to write.

        Returns:
            Dict with 'ok', 'file_path' (repo-relative) and 'error'.
        """
        repo_root = os.path.normpath(repo_path)
        resolved = file_path
        if not os.path.isabs(resolved):
            resolved = os.path.join(repo_root, resolved)
        resolved = os.path.normpath(resolved)

        if not resolved.startswith(repo_root + os.sep):
            return {
                "ok": False,
                "file_path": file_path,
                "error": f"File path must belong to {repo_path}",
            }

        try:
            dir_name = os.path.dirname(resolved)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(resolved, "w", encoding="utf-8") as f:
                f.write(content if content is not None else "")
        except (IOError, OSError) as ex:
            logger.error("Error writing file %s: %s", resolved, ex)
            return {"ok": False, "file_path": file_path, "error": str(ex)}

        return {
            "ok": True,
            "file_path": os.path.relpath(resolved, repo_root),
            "error": "",
        }

    def diff_file(self, path: str, content: str, from_branch: str = None, to_branch: str = None) -> dict:
        """
        Diff a project file against provided content using git diff --no-index.
        Optionally compare against specific branches.

        Args:
            path: File path.
            content: New content to diff against.
            from_branch: Optional source branch for comparison (git diff --no-index ignores this for file diffs).
            to_branch: Optional target branch for comparison (git diff --no-index ignores this for file diffs).

        Returns:
            Dict with 'diff', 'stats', 'last_modification', and 'size'.
        
        Note:
            For branch-based diffs, use git commands like:
            `git diff from_branch to_branch -- path` instead of `git diff --no-index`.
            This implementation uses --no-index for comparing working tree against provided content.
        """
        path = self._get_git_root_for_file(file_path=path)

        # For comparing against branches, we would use different git commands
        # Currently using --no-index for comparing working file against new content
        if from_branch and to_branch:
            # Compare file between two branches
            cmd = ["git", "diff", f"{from_branch}..{to_branch}", "--", path]
            result = subprocess.run(cmd, text=True, capture_output=True, cwd=self.settings.abs_project_path)
            diff_out = result.stdout
            
            git_stats_cmd = ["git", "diff", f"{from_branch}..{to_branch}", "--shortstat", "--", path]
            stats_result = subprocess.run(git_stats_cmd, text=True, capture_output=True, cwd=self.settings.abs_project_path)
            diff_stats_out = stats_result.stdout
        else:
            # Default behavior: compare provided content against current file
            cmd = ["git", "diff", "--no-index", path, "-"]
            result = subprocess.run(cmd, input=content, text=True, capture_output=True)
            diff_out = result.stdout

            git_command = f"""
            cat << EOF | git --no-pager diff --shortstat --no-index -- - {path}
            {content}
            EOF
            """
            diff_stats_out = os.popen(git_command).read()

        return {
            "diff": diff_out.strip(),
            "stats": diff_stats_out.strip(),
        }

    def get_repo_branches(self) -> list:
        """
        Return all git branches (local and remote) ordered by latest activity.

        The list is sorted by the committer date of the branch tip, newest
        first, so the branch with the most recent changes is always at the top
        of the git view. The ref name is used as a stable tie-breaker.

        Remote symbolic refs (``origin/HEAD``) are skipped: they are aliases of
        another branch and would appear twice in the list.

        Returns:
            Sanitized branch names, newest commit first.

        Example:
            >>> engine.get_repo_branches()
            ['feature/login', 'main', 'origin/main']
        """
        # ``for-each-ref`` resolves every branch (local + remote) in one call and
        # exposes the commit date used for sorting. Tab separators keep names
        # with slashes readable.
        result = self._run_git(
            [
                "for-each-ref",
                "--sort=-committerdate",
                "--format=%(committerdate:unix)%09%(refname:short)",
                "refs/heads",
                "refs/remotes",
            ]
        )

        entries: List[tuple] = []
        if result["ok"]:
            for line in result["output"].splitlines():
                timestamp, separator, raw_name = line.partition("\t")
                if not separator or not raw_name.strip():
                    continue
                name = self._sanitize_branch_name(raw_name)
                # Symbolic remote refs are aliases: origin/HEAD -> origin/main
                if not name or name.endswith("/HEAD"):
                    continue
                try:
                    date = int(timestamp)
                except (TypeError, ValueError):
                    date = 0
                entries.append((date, name))

        if not entries:
            # Very old git versions (or a repository without refs): keep the
            # previous behaviour as a fallback instead of returning nothing.
            def get_branches(cmd: str) -> list:
                stdout, _ = exec_command(cmd, cwd=self.settings.abs_project_path)
                branches = [s.strip() for s in stdout.split("\n") if s.strip()]
                return [self._sanitize_branch_name(b) for b in branches]

            branches = list(
                set(get_branches("git branch") + get_branches("git branch -r"))
            )
            branches.sort()
            return branches

        # Newest first; refname keeps equal dates deterministic.
        entries.sort(key=lambda item: (-item[0], item[1]))

        branches: List[str] = []
        seen = set()
        for _date, name in entries:
            if name in seen:
                continue
            seen.add(name)
            branches.append(name)
        return branches

    def get_project_branches(self) -> dict:
        """
        Return branches, the checked out branch and the full repo tree.

        ``active_branch`` lets the review panel pre-select the branch the local
        changes belong to instead of the first (latest) branch of the list.

        Returns:
            Dict with 'branches', 'active_branch', 'default_branch' and
            'repo_tree'.
        """
        return {
            "branches": self.get_repo_branches(),
            "active_branch": self._sanitize_branch_name(
                self.get_project_current_branch()
            ),
            "default_branch": self.get_default_branch(),
            "repo_tree": self.get_repo_tree(),
        }

    def get_project_branch_commits(self, branch: str) -> dict:
        """
        Return commits for a given branch.
        """
        branch = self._sanitize_branch_name(branch)
        commits, _ = exec_command(
            f"git log {branch}", cwd=self.settings.abs_project_path
        )
        return {"commits": commits}

    def _git_toplevel(self, cwd: Optional[str] = None) -> str:
        """
        Return the working tree root git reports for *cwd*.

        The identity and token overrides are disabled: this helper is used while
        resolving the repository root, and resolving the identity itself needs
        the repository root (which would recurse).

        Args:
            cwd: Directory inside the repository. Defaults to the project path.

        Returns:
            Absolute, normalized top-level path, or an empty string when *cwd*
            is not inside a git working tree.
        """
        cwd = cwd or self.settings.abs_project_path
        if not cwd:
            return ""
        result = self._run_git(
            ["rev-parse", "--show-toplevel"],
            cwd=cwd,
            apply_identity=False,
            apply_token=False,
        )
        if not result["ok"] or not result["output"]:
            return ""
        return os.path.normpath(result["output"])

    def find_git_root_path(self) -> str:
        """
        Find the root path of the git repository by checking parents.

        A project can be a subdirectory of the repository (``api/``,
        ``client/``...) whose parent project is not registered or is registered
        behind a different mount alias. In that case the project path is not the
        repository root: ask git for the real top-level, so worktree detection
        and every repository write run from the root instead of the subfolder.
        """
        if self.settings.is_git_root:
            return self.settings.abs_project_path
        for parent in find_project_parents(project=self.settings):
            if parent.is_git_root:
                return parent.abs_project_path
        return self._git_toplevel(self.settings.abs_project_path)

    def get_commit_list(self, branch: str = None, limit: int = 50) -> list:
        """
        Return a structured list of commits for a branch or HEAD.

        Args:
            branch: Branch name. Defaults to current HEAD.
            limit:  Maximum number of commits to return.

        Returns:
            List of commit dicts with hash, author, date, message.
        """
        if branch:
            branch = self._sanitize_branch_name(branch)
        
        ref = branch or "HEAD"
        pretty = "%H|%an|%ae|%ad|%s"
        cmd = f"git log --pretty=format:{pretty} --date=iso -n {limit} {ref}"
        stdout, _ = exec_command(cmd, cwd=self.settings.abs_project_path)

        commits = []
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                commit_hash, author_name, author_email, date, message = line.split("|", 4)
                commits.append({
                    "commit": commit_hash,
                    "short_commit": commit_hash[:8],
                    "author": {"name": author_name, "email": author_email},
                    "date": date.strip(),
                    "message": message.strip(),
                    "label": f"{commit_hash[:8]} - {message.strip()[:60]}"
                })
            except ValueError:
                logger.warning("Could not parse commit line: %s", line)
        return commits

    def get_commit_changes(self, from_commit: str, to_commit: str) -> dict:
        """
        Return file changes and diffs between two commits.

        Args:
            from_commit: Source commit hash (newer).
            to_commit:   Target commit hash (older / base).

        Returns:
            Dict matching the shape of get_repo_changes output.
        """
        diff_name_cmd = f"git diff --name-only {to_commit}...{from_commit}"
        branch_files_raw, _ = exec_command(diff_name_cmd, cwd=self.settings.abs_project_path)
        branch_files = [f for f in branch_files_raw.strip().split("\n") if f]

        def get_file_diff(file_path: str) -> str:
            cmd = f"git diff {to_commit}...{from_commit} -- {file_path}"
            out, _ = exec_command(cmd, cwd=self.settings.abs_project_path)
            return out.strip()

        def get_file_commits(file_path: str) -> list:
            pretty = '{ "commit": "%H", "author": "%an", "date": "%as", "message": "%f" }'
            cmd = f"git log --pretty=format:'{pretty}' {to_commit}..{from_commit} -- {file_path}"
            out, _ = exec_command(cmd, cwd=self.settings.abs_project_path)
            results = []
            for line in out.strip().split("\n"):
                try:
                    results.append(json.loads(line))
                except Exception:
                    pass
            return results

        branch_file_and_commits = {
            file_path: {
                "commits": get_file_commits(file_path),
                "diff": get_file_diff(file_path),
                "last_modification": self._get_file_last_modification(file_path),
            }
            for file_path in branch_files
        }

        git_diff_cmd = f"git diff {to_commit} {from_commit}"
        git_diff_out, _ = exec_command(git_diff_cmd, cwd=self.settings.abs_project_path)
        git_diff_stat_out, _ = exec_command(
            f"git diff --shortstat {to_commit} {from_commit}",
            cwd=self.settings.abs_project_path
        )

        pr_details = self.get_pr_review_details_by_commits(from_commit, to_commit)

        return {
            "diff": git_diff_out,
            "stat": git_diff_stat_out,
            "git_diff_cmd": git_diff_cmd,
            "local_changes": {},
            "repo_path": self.find_git_root_path(),
            "pr_details": pr_details,
            "commits": [],
            "branch_file_and_commits": branch_file_and_commits,
            "compare_type": "commit",
            "from_commit": from_commit,
            "to_commit": to_commit,
        }

    def get_pr_review_details_by_commits(self, from_commit: str, to_commit: str) -> list:
        """
        Return PR review details between two commits.

        Args:
            from_commit: Source commit hash.
            to_commit:   Target / base commit hash.

        Returns:
            List of change dicts per file.
        """
        diff_command = f"git diff --name-status {to_commit}..{from_commit}"
        stdout, _ = exec_command(diff_command, cwd=self.settings.abs_project_path)

        STATUS_MAP = {"A": "new", "D": "deleted"}
        changes = []

        for line in stdout.strip().split("\n"):
            # Guard: skip empty lines or lines without a tab separator
            if not line or "\t" not in line:
                continue
            parts = line.split("\t", 1)
            if len(parts) < 2:
                continue
            status, file_path = parts
            file_path = file_path.strip()
            if not file_path:
                continue

            file_status = STATUS_MAP.get(status.strip(), "modified")

            file_diff, _ = exec_command(
                f"git diff {to_commit}..{from_commit} -- {file_path}",
                cwd=self.settings.abs_project_path
            )
            file_commits_raw, _ = exec_command(
                f"git log --oneline {to_commit}..{from_commit} -- {file_path}",
                cwd=self.settings.abs_project_path
            )
            changes.append({
                "file_name": file_path,
                "status": file_status,
                "diff": file_diff,
                "commits": [c for c in file_commits_raw.strip().split("\n") if c],
                "last_modification": self._get_file_last_modification(file_path),
            })

        return changes

    def get_repo_changes(self, from_branch: str, to_branch: str) -> dict:
        """
        Return file changes, diffs and PR details between two branches.

        The ``local`` sentinel compares the uncommitted working tree against
        the other side of the comparison, which is how the git view reviews
        local changes against the current branch:

        - ``to_branch="local"`` compares the working tree against *from_branch*.
        - ``from_branch="local"`` compares the working tree against *to_branch*.

        Each file entry includes a 'last_modification' datetime (ISO 8601).
        """
        # Sanitize branch names
        from_branch = self._sanitize_branch_name(from_branch)
        to_branch = self._sanitize_branch_name(to_branch)

        # Local changes are compared against the other side of the pair. This is
        # the branch the working tree is based on, defaulting to the checked out
        # one when the caller did not name it.
        local_sentinel = "local"
        from_local = (from_branch or "").lower() == local_sentinel
        to_local = (to_branch or "").lower() == local_sentinel
        if from_local or to_local:
            base_branch = to_branch if from_local else from_branch
            if not base_branch or base_branch.lower() == local_sentinel:
                base_branch = (
                    self._sanitize_branch_name(self.get_project_current_branch())
                    or "HEAD"
                )
            result = self.get_local_changes(base_ref=base_branch)
            result.update({
                "from_branch": from_branch,
                "to_branch": to_branch,
                "base_branch": base_branch,
            })
            return result

        # Get list of changed files (and their status) in one command
        git_branch_file_changed = f"git diff --name-status {to_branch}...{from_branch}"
        branch_files_output, _ = exec_command(
            git_branch_file_changed, cwd=self.settings.abs_project_path
        )
        status_by_file: Dict[str, str] = {}
        for line in branch_files_output.split("\n"):
            if not line.strip() or "\t" not in line:
                continue
            parts = line.split("\t")
            code = (parts[0] or "").strip()[:1]
            path = (parts[-1] or "").strip()
            if not path:
                continue
            status_by_file[path] = (
                "new" if code == "A"
                else "deleted" if code == "D"
                else "renamed" if code == "R"
                else "copied" if code == "C"
                else "typechange" if code == "T"
                else "modified"
            )
        branch_files = list(status_by_file)

        # One diff and one log for the whole comparison: spawning git per file
        # made a 700-file comparison take minutes.
        git_diff_cmd = f"git diff --no-color {to_branch}...{from_branch}"
        git_diff_cmd_out, _ = exec_command(
            git_diff_cmd, cwd=self.settings.abs_project_path
        )
        patches = self._split_file_patches(git_diff_cmd_out)
        commits_by_file = self._commits_by_file(
            to_ref=to_branch, from_ref=from_branch
        )

        # Build per-file metadata
        branch_file_and_commits = {}
        for file_path in branch_files:
            if not file_path:
                continue
            patch = patches.get(file_path)
            if patch is None:
                # Fallback for quoted paths the split could not map
                patch, _ = exec_command(
                    f"git diff {to_branch}...{from_branch} -- {file_path}",
                    cwd=self.settings.abs_project_path,
                )
                patch = (patch or "").strip()
            branch_file_and_commits[file_path] = {
                "commits": commits_by_file.get(file_path, []),
                "diff": patch or "",
                "last_modification": self._get_file_last_modification(file_path),
            }

        # Get overall diff stats (from the same command run above)
        git_diff_cmd_stat_out, _ = exec_command(
            f"git diff --shortstat {to_branch}...{from_branch}",
            cwd=self.settings.abs_project_path,
        )

        # Reuse the per-file data already loaded instead of running one diff
        # and one log per file again.
        pr_details = [
            {
                "file_name": file_path,
                "status": status_by_file.get(file_path, "modified"),
                "diff": entry["diff"],
                "commits": entry["commits"],
                "last_modification": entry["last_modification"],
            }
            for file_path, entry in branch_file_and_commits.items()
        ]

        return {
            "diff": git_diff_cmd_out,
            "stat": git_diff_cmd_stat_out,
            "git_diff_cmd": git_diff_cmd,
            "local_changes": {},
            "repo_path": self.find_git_root_path(),
            "pr_details": pr_details,
            "commits": [],
            "branch_file_and_commits": branch_file_and_commits,
            "compare_type": "branch",
            "from_branch": from_branch,
            "to_branch": to_branch,
        }

    def get_branch_commits(self, from_branch: str, repo_path: str) -> list:
        """
        Return structured commit list for a branch.
        """
        from_branch = self._sanitize_branch_name(from_branch)
        git_log_command = (
            f"git log --pretty=format:%H|%an|%ae|%ad|%s {from_branch}"
        )
        stdout, _ = exec_command(git_log_command, cwd=repo_path)

        log_entries = stdout.strip().split("\n")
        log_list = []
        for entry in log_entries:
            if not entry.strip():
                continue
            commit_hash, author_name, author_email, date, message = entry.split("|", 4)
            log_list.append(
                {
                    "commit": commit_hash,
                    "author": {"name": author_name, "email": author_email},
                    "date": date,
                    "message": message.strip(),
                }
            )
        return log_list

    def get_repo_tree(self) -> list:
        """
        Build a full repo tree with branches and commits.
        """
        branches = self.get_repo_branches()
        repo_tree = []

        for branch in branches:
            branch_details = self.get_branch_details(branch_name=branch)
            branch_info = {
                "branch_name": branch,
                "author": "",
                "date": "",
                "commits": [],
            }
            for commit in branch_details["commits"]:
                branch_info["commits"].append(
                    {
                        "commit_id": commit["commit_hash"],
                        "author": commit["author"],
                        "date": commit["date"],
                        "comment": commit["message"],
                        "files": commit["files"],
                    }
                )
            repo_tree.append(branch_info)

        return repo_tree

    def get_branch_details(self, branch_name: str) -> dict:
        """
        Extract commit details from a branch without checking it out.
        """
        branch_name = self._sanitize_branch_name(branch_name)
        log_command = f"git log -g --format=%H|%an|%cI|%s {branch_name}"
        stdout, _ = exec_command(log_command, cwd=self.settings.abs_project_path)

        log_lines = stdout.split("\n")
        commits = []

        for entry in log_lines:
            if not entry.strip():
                continue
            try:
                commit_hash, author, date, message = entry.split("|", 3)
            except ValueError:
                continue

            file_changes_command = (
                f"git show --name-only --pretty=format:{commit_hash}"
            )
            stdout_files, _ = exec_command(
                file_changes_command, cwd=self.settings.abs_project_path
            )
            file_changes = stdout_files.strip().split("\n")

            enriched_files = []
            for f in file_changes[1:]:
                if not f:
                    continue
                enriched_files.append(
                    {
                        "file_path": f,
                        "last_modification": self._get_file_last_modification(f),
                    }
                )

            commits.append(
                {
                    "entry_line": entry,
                    "commit_hash": commit_hash,
                    "author": author,
                    "date": date,
                    "message": message,
                    "files": enriched_files,
                }
            )

        return {
            "commits": commits,
            "parent_branch": commits[-1]["commit_hash"] if commits else None,
        }

    def get_project_current_branch(self) -> str:
        """Return the current git branch name."""
        stdout, _ = exec_command(
            "git branch --show-current", cwd=self._get_repo_root()
        )
        return stdout.strip()

    def get_project_parent_branch(self) -> str:
        """Determine the parent branch of the current branch via reflog."""
        current_branch = self.get_project_current_branch()
        stdout, _ = exec_command(
            f"git reflog {current_branch}",
            cwd=self.settings.abs_project_path,
        )
        self.session.log_info(
            "get_project_parent_branch reflog: %s cwd: %s",
            stdout,
            self.settings.abs_project_path,
        )

        creation_lines = [l for l in stdout.split("\n") if "Created from" in l]
        if not creation_lines:
            return ""

        creation_line = creation_lines[0]

        if "refs/remotes/" in creation_line:
            ref_branch = creation_line.split(" ")[-1].replace("refs/remotes/", "")
            return self._sanitize_branch_name(ref_branch)

        ref_branch = creation_line.split(" (")[1].split(",")[0]
        return self._sanitize_branch_name(ref_branch)

    def get_project_changes(self, parent_branch: str = None) -> dict:
        """Return diff between current working tree and a parent branch."""
        if not parent_branch:
            parent_branch = "HEAD@{1}"
            self.session.log_info(
                "get_project_changes parent_branch %s", parent_branch
            )

        diff_out, _ = exec_command(
            f"git diff {parent_branch}", cwd=self.settings.abs_project_path
        )
        diff_stat_out, _ = exec_command(
            f"git diff --shortstat {parent_branch}",
            cwd=self.settings.abs_project_path,
        )
        return {"diff": diff_out, "stats": diff_stat_out}

    def build_code_changes_summary(self, force: bool = False) -> object:
        """Build a code changes summary from git diff."""
        project_branches = self.get_project_branches()
        diff = project_branches.get("git_diff", "")
        return self.session.get_knowledge().build_code_changes_summary(
            diff=diff, force=force
        )

    def get_pr_review_details(self, from_branch: str, to_branch: str) -> list:
        """
        Return PR review details (file changes, diffs, commits) between two branches.
        Each file entry includes a 'last_modification' datetime (ISO 8601).
        """
        # Sanitize branch names
        from_branch = self._sanitize_branch_name(from_branch)
        to_branch = self._sanitize_branch_name(to_branch)
        
        exec_command(
            f"git fetch origin {to_branch}:{to_branch}",
            cwd=self.settings.abs_project_path,
        )
        exec_command(
            f"git fetch origin {from_branch}:{from_branch}",
            cwd=self.settings.abs_project_path,
        )

        diff_command = f"git diff --name-status {to_branch}..{from_branch}"
        stdout, _ = exec_command(diff_command, cwd=self.settings.abs_project_path)

        STATUS_MAP = {"A": "new", "D": "deleted"}
        changes = []

        for line in stdout.strip().split("\n"):
            # Guard: skip empty or tab-less lines to avoid unpack errors
            if not line or "\t" not in line:
                continue
            parts = line.split("\t", 1)
            if len(parts) < 2:
                continue
            status, file_path = parts
            file_path = file_path.strip()
            if not file_path:
                continue

            file_status = STATUS_MAP.get(status.strip(), "modified")

            file_diff_command = f"git diff {to_branch}..{from_branch} -- {file_path}"
            file_diff, _ = exec_command(
                file_diff_command, cwd=self.settings.abs_project_path
            )

            file_commits_command = (
                f"git log --oneline {to_branch}..{from_branch} -- {file_path}"
            )
            file_commits_stdout, _ = exec_command(
                file_commits_command, cwd=self.settings.abs_project_path
            )
            file_commits = [c for c in file_commits_stdout.strip().split("\n") if c]

            changes.append(
                {
                    "file_name": file_path,
                    "status": file_status,
                    "diff": file_diff,
                    "commits": file_commits,
                    "last_modification": self._get_file_last_modification(file_path),
                }
            )

        return changes

    def _clean_status_path(self, path: str) -> str:
        """
        Return the target path of a porcelain status entry.

        Rename entries keep only the destination path and quoted paths (paths
        with spaces or special characters) are unquoted.

        Args:
            path: Raw path read from ``git status --porcelain``.

        Returns:
            Cleaned, repo-relative file path.
        """
        path = (path or "").strip()
        if " -> " in path:
            path = path.split(" -> ")[-1].strip()
        return path.strip('"')

    def _parse_status_line(self, line: str) -> Optional[Tuple[str, str, str]]:
        """
        Split a porcelain v1 status line into its parts.

        The format is ``XY <path>``: X is the staged (index) status and Y the
        unstaged (worktree) status. The leading space of a line may have been
        trimmed when reading the command output, so the separator position is
        used to detect the shifted format.

        Args:
            line: One line of ``git status --porcelain`` output.

        Returns:
            Tuple of ``(index_code, worktree_code, path)``, or None when the
            line has no usable entry.
        """
        if not line or not line.strip():
            return None

        if len(line) >= 3 and line[2] == " ":
            index_code, worktree_code, path = line[0], line[1], line[3:]
        elif len(line) >= 2:
            # Leading space was trimmed: only the worktree status is left
            index_code, worktree_code, path = " ", line[0], line[2:]
        else:
            return None

        path = self._clean_status_path(path)
        if not path:
            return None
        return index_code, worktree_code, path

    def _status_entry(self, code: str, path: str) -> dict:
        """
        Build a staged/unstaged status entry.

        Args:
            code: Porcelain status code (``M``, ``A``, ``D``, ``?``...).
            path: Repo-relative file path.

        Returns:
            Dict with 'path', 'code' and 'status'.
        """
        return {
            "path": path,
            "code": code,
            "status": PORCELAIN_STATUS.get(code, "modified"),
        }

    def _is_nested_repo(self, path: str, cwd: Optional[str] = None) -> bool:
        """
        Return whether *path* is a folder holding its own git repository.

        A nested repository (an embedded repository, or a submodule that is not
        registered yet) carries its own ``.git``: a folder for a regular
        checkout, a file for a submodule or a worktree.

        Args:
            path: Repo-relative folder path.
            cwd: Working directory. Defaults to the repository root.

        Returns:
            True when the folder contains a ``.git`` entry.

        Example:
            >>> engine._is_nested_repo("plugins/simpleopd.ai/")
            True
        """
        cwd = cwd or self._get_repo_root()
        return os.path.exists(os.path.join(cwd, (path or "").strip(), ".git"))

    def _is_untracked_nested_repo(
        self, line: str, cwd: Optional[str] = None
    ) -> bool:
        """
        Return whether a porcelain status line is an untracked nested repository.

        ``--untracked-files=all`` expands every regular untracked folder into
        its files: only a *nested repository* is still reported as a single
        directory entry (``?? folder/``), because git never descends into it.

        Args:
            line: One line of ``git status --porcelain`` output.
            cwd: Working directory. Defaults to the repository root.

        Returns:
            True when the line is an untracked directory holding its own ``.git``.

        Example:
            >>> engine._is_untracked_nested_repo("?? plugins/simpleopd.ai/")
            True
        """
        parsed = self._parse_status_line(line)
        if not parsed:
            return False

        index_code, worktree_code, path = parsed
        if index_code != "?" or worktree_code != "?" or not path.endswith("/"):
            return False
        return self._is_nested_repo(path, cwd=cwd)

    def _filter_nested_repos(
        self, lines: List[str], cwd: Optional[str] = None
    ) -> List[str]:
        """
        Drop the status entries of the nested repositories (submodules).

        The files of a nested repository belong to that repository, not to this
        one: neither the folder nor the files it contains are reported as
        changes, so they are never listed in the UI nor staged by the engine
        (staging the folder would add it as an opaque gitlink).

        Changes to an already tracked submodule (its `` M submodule`` gitlink
        entry) are real changes of this repository and are kept.

        Args:
            lines: Porcelain status lines.
            cwd: Working directory. Defaults to the repository root.

        Returns:
            Porcelain status lines without the untracked nested repositories.

        Example:
            >>> engine._filter_nested_repos(["?? plugins/simpleopd.ai/", " M app.py"])
            [' M app.py']
        """
        filtered: List[str] = []
        for line in lines:
            if self._is_untracked_nested_repo(line, cwd=cwd):
                parsed = self._parse_status_line(line)
                logger.info(
                    "Ignoring nested repository '%s': its files belong to a "
                    "submodule",
                    parsed[2] if parsed else line,
                )
                continue
            filtered.append(line)
        return filtered

    def _status_paths(self, cwd: Optional[str] = None) -> List[str]:
        """
        Return the file paths currently reported by ``git status --porcelain``.

        Untracked directories are expanded into the files they contain (see
        ``STATUS_ARGS``), so a change list never contains folder paths.

        Untracked nested repositories (submodules / embedded repositories) are
        skipped: their files belong to the nested repository and must never be
        staged by this one. Ignored files (``!`` entries) are skipped too: they
        cannot be staged.

        Args:
            cwd: Working directory. Defaults to the repository root.

        Returns:
            De-duplicated, repo-relative file paths.

        Example:
            >>> engine._status_paths()
            ['app.py', 'new.json']
        """
        result = self._run_git(STATUS_ARGS, cwd=cwd, strip_output=False)
        paths: List[str] = []

        for line in result["output"].split("\n"):
            parsed = self._parse_status_line(line)
            if not parsed:
                continue
            index_code, worktree_code, path = parsed
            if index_code == "!" or worktree_code == "!":
                continue
            # Nested repositories are never staged: their files are not ours
            if self._is_untracked_nested_repo(line, cwd=cwd):
                continue
            if path not in paths:
                paths.append(path)

        return paths

    def get_status_changes(self, files: Optional[List[str]] = None) -> dict:
        """
        Split the working tree status into staged and unstaged file lists.

        Args:
            files: Porcelain status lines. Read from git when omitted.

        Returns:
            Dict with 'staged' and 'unstaged' lists of
            ``{path, code, status}`` entries.

        Example:
            >>> engine.get_status_changes()
            {'staged': [{'path': 'app.py', 'code': 'M', 'status': 'modified'}],
             'unstaged': [{'path': 'new.json', 'code': '?', 'status': 'untracked'}]}
        """
        if files is None:
            files = self.get_working_tree_status()["files"]

        staged: List[dict] = []
        unstaged: List[dict] = []

        for line in files:
            parsed = self._parse_status_line(line)
            if not parsed:
                continue

            index_code, worktree_code, path = parsed

            # '!' entries are ignored files: never shown as changes
            if index_code == "!" or worktree_code == "!":
                continue

            if index_code == "?" and worktree_code == "?":
                unstaged.append(self._status_entry("?", path))
                continue

            if index_code != " ":
                staged.append(self._status_entry(index_code, path))
            if worktree_code not in (" ", "?"):
                unstaged.append(self._status_entry(worktree_code, path))

        return {"staged": staged, "unstaged": unstaged}

    def get_working_tree_status(self) -> dict:
        """
        Return the working tree status of the repository.

        Untracked directories are expanded into the files they contain
        (``--untracked-files=all``), so ``files`` lists individual files and
        never folder paths. Untracked nested repositories (submodules and
        embedded repositories) are dropped by ``_filter_nested_repos``: git
        never descends into them and their files belong to the nested
        repository, so neither the folder nor its files are reported.

        Returns:
            Dict with 'ok', 'dirty', 'files' (porcelain lines, one per file)
            and 'error'.

        Example:
            >>> engine.get_working_tree_status()
            {'ok': True, 'dirty': True, 'files': [' M codx/junior/app.py'], 'error': ''}
        """
        # Leading spaces are part of the porcelain format (index vs worktree)
        result = self._run_git(STATUS_ARGS, strip_output=False)
        raw_files = [line for line in result["output"].split("\n") if line.strip()]
        files = self._filter_nested_repos(raw_files)
        return {
            "ok": result["ok"],
            "dirty": bool(files),
            "files": files,
            "error": result["error"],
        }

    def stage_changes(
        self, files: Optional[List[str]] = None, cwd: Optional[str] = None
    ) -> dict:
        """
        Stage working tree changes without aborting on individual failures.

        A single ``git add`` for every path fails as a whole as soon as one of
        them cannot be staged (removed from disk, unknown pathspec...), leaving
        the remaining changes unstaged. Each path is therefore staged on its
        own, so a failure only affects that path and every failure is collected
        in 'errors'.

        Args:
            files: Paths to stage. Defaults to every change in the worktree.
            cwd: Working directory. Defaults to the repository root.

        Returns:
            Dict with 'ok' (True when no path failed), 'staged' (paths staged
            successfully), 'errors' (one message per failed path), 'output',
            'locked' and 'lock_path' (set when staging failed because of a stale
            index lock).

        Example:
            >>> engine.stage_changes(["app.py", "gone.json"])
            {'ok': False, 'staged': ['app.py'],
             'errors': ["gone.json: pathspec 'gone.json' did not match..."],
             'output': '', 'locked': False, 'lock_path': ''}
        """
        cwd = cwd or self._get_repo_root()
        if files is None:
            files = self._status_paths(cwd=cwd)

        staged: List[str] = []
        errors: List[str] = []
        outputs: List[str] = []
        locked = False
        lock_path = ""

        for path in files:
            result = self._run_git(["add", "-A", "--", path], cwd=cwd)
            if result["ok"]:
                staged.append(path)
                if result["output"]:
                    outputs.append(result["output"])
                continue

            error = result["error"] or result["output"] or "could not be staged"
            logger.warning("Could not stage %s: %s", path, error)
            errors.append(f"{path}: {error}")

            lock = self._lock_error_info(error)
            if lock.get("locked"):
                locked = True
                lock_path = lock.get("lock_path", "")

        return {
            "ok": not errors,
            "staged": staged,
            "errors": errors,
            "output": "\n".join(outputs),
            "locked": locked,
            "lock_path": lock_path,
        }

    def build_branch_name(self, name: Optional[str] = None, prefix: Optional[str] = None) -> str:
        """
        Build a safe branch name from free text.

        Args:
            name: Optional descriptive text (chat name, task title...).
            prefix: Branch prefix. Defaults to the project's `git_pr_branch_prefix`
                setting, or 'codx-junior'.

        Returns:
            Branch name such as 'codx-junior/fix-login-timeout' or
            'codx-junior/chat-20240101-120000' when no name is provided.

        Example:
            >>> engine.build_branch_name("Fix: login timeout!")
            'codx-junior/fix-login-timeout'
        """
        if prefix is None:
            prefix = getattr(self.settings, "git_pr_branch_prefix", None) or DEFAULT_BRANCH_PREFIX

        slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
        slug = slug[:40].strip("-")
        if not slug:
            slug = f"chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        prefix = (prefix or "").strip("/")
        return f"{prefix}/{slug}" if prefix else slug

    def get_worktrees_path(self) -> str:
        """
        Return the folder where PR worktrees are created.

        The base path is read from the project settings
        (`git_worktrees_path` / `get_worktrees_path()`, which already resolves
        relative values against the project path). `~` is expanded and the
        result normalized, so every worktree path is built from the same base.

        Returns:
            Absolute, normalized worktrees base path.
        """
        getter = getattr(self.settings, "get_worktrees_path", None)
        base_path = getter() if callable(getter) else ""
        if not base_path:
            # Settings object without the getter: use the raw setting
            base_path = getattr(self.settings, "git_worktrees_path", "") or ""
        base_path = str(base_path).strip()

        if base_path:
            base_path = os.path.expanduser(base_path)
            if not os.path.isabs(base_path):
                base_path = os.path.join(self.settings.abs_project_path, base_path)
            return os.path.normpath(base_path)

        repo_path = self._get_repo_root().rstrip("/")
        return os.path.join(
            os.path.dirname(repo_path), f"{os.path.basename(repo_path)}-worktrees"
        )

    def _worktree_changes(self, worktree_path: str) -> dict:
        """
        Return the working tree changes of one worktree.

        The status is read inside the worktree itself (``git status`` with the
        worktree as cwd), so it reports the files changed in that checkout and
        never the files of the main repository.

        Args:
            worktree_path: Absolute worktree path.

        Returns:
            Dict with 'ok', 'dirty', 'files', 'staged', 'unstaged',
            'file_count' and 'errors'.

        Example:
            >>> engine._worktree_changes("/repo-worktrees/feature")["file_count"]
            2
        """
        if not worktree_path or not os.path.isdir(worktree_path):
            return {
                "ok": False,
                "dirty": False,
                "files": [],
                "staged": [],
                "unstaged": [],
                "file_count": 0,
                "errors": [f"Worktree path does not exist: {worktree_path}"],
            }

        result = self._run_git(STATUS_ARGS, cwd=worktree_path, strip_output=False)
        raw_files = [line for line in result["output"].split("\n") if line.strip()]
        files = self._filter_nested_repos(raw_files, cwd=worktree_path)
        changes = self.get_status_changes(files)
        return {
            "ok": result["ok"],
            "dirty": bool(files),
            "files": files,
            "staged": changes["staged"],
            "unstaged": changes["unstaged"],
            "file_count": len(files),
            "errors": [] if result["ok"] else [result["error"]],
        }

    def list_worktrees(self, include_changes: bool = True) -> list:
        """
        Return the repository's registered worktrees.

        Args:
            include_changes: Read the working tree status of every worktree and
                include it under 'changes'. Disable it when only the path /
                branch mapping is needed (the git view needs the changes).

        Returns:
            List of dicts with 'path', 'branch', 'head', 'bare', 'detached' and,
            when *include_changes* is true, 'changes' (staged / unstaged file
            lists, dirty flag and file count).
        """
        result = self._run_git(["worktree", "list", "--porcelain"])
        # Resolve once: the same checkout can be reached through a symlink or a
        # bind mount, and path aliases must not turn the main checkout into a
        # "removable worktree".
        repo_root = self._get_repo_root()
        worktrees = []
        current: Dict[str, str] = {}

        def flush_worktree() -> None:
            if not current:
                return
            entry = dict(current)
            path = entry.get("path", "")
            # `worktree.useRelativePaths` makes porcelain report paths relative
            # to the main checkout: normalize them so path matching (and the
            # removal command) always uses absolute paths.
            if path and not os.path.isabs(path):
                path = os.path.normpath(os.path.join(repo_root, path))
                entry["path"] = path
            entry["name"] = os.path.basename(os.path.normpath(path)) if path else ""
            entry["branch"] = self._sanitize_branch_name(entry.get("branch", ""))
            entry["head"] = entry.get("head", "")
            entry["bare"] = entry.get("bare") == "bare"
            entry["detached"] = entry.get("detached") == "detached"
            entry["is_main"] = self._same_path(path, repo_root)
            if include_changes:
                entry["changes"] = self._worktree_changes(path)
            worktrees.append(entry)

        for line in result["output"].split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("worktree "):
                flush_worktree()
                current = {"path": line[len("worktree "):].strip()}
            elif line.startswith("HEAD ") and current is not None:
                current["head"] = line[len("HEAD "):].strip()
            elif line.startswith("branch ") and current is not None:
                branch = line[len("branch "):].strip()
                current["branch"] = branch.replace("refs/heads/", "")
            elif line == "bare" and current is not None:
                current["bare"] = "bare"
            elif line == "detached" and current is not None:
                current["detached"] = "detached"

        flush_worktree()
        return worktrees

    def get_worktree_merge_status(
        self, source_branch: str, target_branch: Optional[str] = None
    ) -> dict:
        """
        Summarize what a worktree branch would bring into the target branch.

        The Repository view shows, next to every worktree, whether its branch
        has files pending to merge into the branch currently checked out. The
        comparison is the same three-dot diff used by the Review tab
        (``target...source``), so it lists only the changes introduced by the
        worktree branch since it diverged from the target.

        Args:
            source_branch: Branch checked out in the worktree.
            target_branch: Branch to merge into. Defaults to the checked out
                branch of the repository.

        Returns:
            Dict with 'applicable', 'source_branch', 'target_branch',
            'has_changes', 'file_count', 'files' (bounded), 'commit_count',
            'stat' and 'errors'.
        """
        source = self._sanitize_branch_name(source_branch)
        target = self._sanitize_branch_name(target_branch) or self._sanitize_branch_name(
            self.get_project_current_branch()
        )
        result = {
            "applicable": False,
            "source_branch": source,
            "target_branch": target,
            "has_changes": False,
            "file_count": 0,
            "files": [],
            "commit_count": 0,
            "stat": "",
            "errors": [],
        }
        if not source or not target or source == target:
            return result
        if not self._ref_exists(f"refs/heads/{source}"):
            return result

        result["applicable"] = True
        repo_path = self._get_repo_root()
        diff = self._run_git(
            ["diff", "--name-only", f"{target}...{source}"], cwd=repo_path
        )
        if not diff["ok"]:
            # A missing target (or no common ancestor) must not break the
            # repository load: report it as an unavailable comparison.
            result["errors"].append(diff["error"] or "Could not compare branches")
            return result

        files = [
            line.strip()
            for line in diff["output"].split("\n")
            if line.strip()
        ]
        result["file_count"] = len(files)
        result["files"] = files[:50]

        commits = self._run_git(
            ["rev-list", "--count", f"{target}..{source}"], cwd=repo_path
        )
        if commits["ok"] and commits["output"].strip().isdigit():
            result["commit_count"] = int(commits["output"].strip())

        stat = self._run_git(
            ["diff", "--shortstat", f"{target}...{source}"], cwd=repo_path
        )
        if stat["ok"]:
            result["stat"] = stat["output"]
        result["has_changes"] = bool(result["file_count"] or result["commit_count"])
        return result

    def get_worktree_path_for_branch(self, branch_name: str) -> str:
        """
        Return the worktree path already registered for a branch, if any.

        Args:
            branch_name: Branch name to look for.

        Returns:
            Absolute worktree path, or an empty string when none exists.
        """
        branch_name = self._sanitize_branch_name(branch_name)
        # Only the path/branch mapping is needed here: skip the status scan.
        for worktree in self.list_worktrees(include_changes=False):
            if worktree.get("branch") == branch_name:
                return worktree.get("path", "")
        return ""

    def _force_remove_worktree_path(
        self, path: str, cwd: Optional[str] = None
    ) -> dict:
        """
        Remove a registered worktree checkout, including locked/dirty ones.

        ``git worktree remove --force`` is the safe path and the only one used
        while it succeeds. Some real-world checkouts still fail: a stale
        ``locked`` admin entry, a registration whose directory was already
        deleted, or a filesystem/git mismatch. In those cases the checkout is
        deleted and the registration pruned, so the UI action actually completes
        instead of leaving a worktree that can never be removed. Callers must
        resolve *path* against the registered worktrees (never an arbitrary
        directory) and reject the main/current checkout before calling this.

        Args:
            path: Absolute worktree path.
            cwd: Repository directory. Defaults to the repository root.

        Returns:
            Dict with 'ok', 'removed', 'output' and 'error'.
        """
        result = {
            "ok": False,
            "removed": False,
            "path": path,
            "output": "",
            "error": "",
        }
        remove = self._run_git(
            ["worktree", "remove", "--force", path], cwd=cwd
        )
        if not remove["ok"] and os.path.lexists(path):
            # A locked worktree refuses `remove` even with --force. Unlock and
            # retry once; unlocking an unlocked worktree logs a harmless error,
            # so it only runs after a failed removal.
            self._run_git(["worktree", "unlock", path], cwd=cwd)
            remove = self._run_git(
                ["worktree", "remove", "--force", path], cwd=cwd
            )
        result["output"] = remove["output"]
        if remove["ok"]:
            result["ok"] = True
            result["removed"] = True
            return result

        # Stale administrative entries must not hide a checkout that is already
        # gone (folder deleted outside git).
        self._run_git(["worktree", "prune"], cwd=cwd)
        still_registered = any(
            self._same_path(worktree.get("path", ""), path)
            for worktree in self.list_worktrees(include_changes=False)
        )
        if not still_registered and not os.path.lexists(path):
            result["ok"] = True
            result["removed"] = True
            result["output"] = result["output"] or "worktree pruned"
            return result

        # Last resort: delete the checkout and prune its registration. The
        # caller already validated that this is a registered, non-main,
        # non-active worktree and the user confirmed the data loss.
        try:
            if os.path.islink(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except OSError as ex:
            result["error"] = remove["error"] or str(ex)
            return result

        self._run_git(["worktree", "prune"], cwd=cwd)
        still_registered = any(
            self._same_path(worktree.get("path", ""), path)
            for worktree in self.list_worktrees(include_changes=False)
        )
        if still_registered:
            result["error"] = (
                remove["error"]
                or "The checkout was deleted but git still lists the worktree"
            )
            return result

        result["ok"] = True
        result["removed"] = True
        result["output"] = result["output"] or "checkout deleted and pruned"
        return result

    def remove_worktree(
        self, branch: Optional[str] = None, path: Optional[str] = None
    ) -> dict:
        """
        Remove a registered worktree, keeping its branch.

        The target is always resolved against the registered worktrees, so the
        endpoint can never delete an arbitrary directory. The main checkout and
        the checkout in use (the active project) are rejected. A stale ``path``
        falls back to the ``branch`` lookup, and a checkout whose folder was
        deleted outside git is pruned instead of being reported as a failure.

        Args:
            branch: Branch whose worktree should be removed.
            path: Exact worktree path. Takes precedence over *branch* and is
                required for detached worktrees.

        Returns:
            Dict with 'success', 'action', 'branch', 'path', 'removed',
            'output' and 'errors'.

        Example:
            >>> engine.remove_worktree(branch="codx-junior/fix-login")
            {'success': True, 'removed': True, ...}
        """
        branch = self._sanitize_branch_name(branch or "")
        result = {
            "success": False,
            "action": "worktree-remove",
            "branch": branch,
            "path": "",
            "removed": False,
            "output": "",
            "errors": [],
        }

        wanted_path = os.path.normpath(path) if path else ""
        worktrees = self.list_worktrees(include_changes=False)
        target = None
        if wanted_path:
            for worktree in worktrees:
                if self._same_path(worktree.get("path", ""), wanted_path):
                    target = worktree
                    break
        # The caller may send a stale path (the checkout was moved or recreated
        # after the view loaded). Fall back to the branch instead of failing
        # even though the worktree is still registered.
        if not target and branch:
            for worktree in worktrees:
                if worktree.get("branch") == branch:
                    target = worktree
                    break

        if not target:
            target_name = path or branch
            result["errors"].append(
                f"No worktree registered for '{target_name}'"
            )
            return result

        target_path = target.get("path", "")
        result["path"] = target_path
        result["branch"] = target.get("branch") or branch

        repo_root = self._get_repo_root()
        if target.get("is_main") or self._same_path(target_path, repo_root):
            result["errors"].append(
                "The main checkout cannot be removed as a worktree"
            )
            return result

        # Removing the checkout currently in use would delete the open project
        protected = [
            repo_root,
            str(getattr(self.settings, "abs_project_path", "") or ""),
        ]
        if any(self._same_path(target_path, candidate) for candidate in protected):
            result["errors"].append(
                f"Cannot remove the checkout in use: {target_path}"
            )
            return result

        remove = self._force_remove_worktree_path(target_path, cwd=repo_root)
        result["output"] = remove["output"]
        if not remove["ok"]:
            result["errors"].append(
                f"Could not remove worktree '{target_path}': "
                f"{remove['error'] or remove['output']}"
            )
            return result

        result["removed"] = True
        result["success"] = True
        return result

    # -------------------------------------------------------------------------
    # .gitignore editor
    # -------------------------------------------------------------------------

    def get_gitignore_root(self) -> str:
        """
        Return the checkout root whose ``.gitignore`` the git view edits.

        ``--show-toplevel`` resolves the checkout the project actually belongs
        to: a linked worktree gets its own ``.gitignore`` instead of the main
        checkout's, and a subproject uses the repository root (the only place
        git applies a root ignore file from).

        Returns:
            Absolute checkout root.
        """
        return (
            self._git_toplevel(self.settings.abs_project_path)
            or self._get_repo_root()
        )

    def get_gitignore_path(self) -> str:
        """Return the absolute path of the checkout's ``.gitignore``."""
        return os.path.join(self.get_gitignore_root(), GITIGNORE_FILE)

    def get_gitignore(self) -> dict:
        """
        Return the checkout's ``.gitignore`` content for the editor.

        The file is optional: when it does not exist the editor starts with an
        empty document and saves it on demand.

        Returns:
            Dict with 'success', 'path', 'root', 'exists', 'content' and
            'errors'.
        """
        path = self.get_gitignore_path()
        result = {
            "success": False,
            "path": path,
            "root": self.get_gitignore_root(),
            "exists": False,
            "content": "",
            "errors": [],
        }
        if not os.path.isfile(path):
            result["success"] = True
            return result

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                result["content"] = handle.read()
        except OSError as ex:
            logger.error("Could not read %s: %s", path, ex)
            result["errors"].append(f"Could not read {path}: {ex}")
            return result

        result["exists"] = True
        result["success"] = True
        return result

    def save_gitignore(self, content: str) -> dict:
        """
        Write the checkout's ``.gitignore``.

        Line endings are normalized and a trailing newline is added, so the file
        stays diff friendly. Nothing is staged or committed: it becomes a normal
        working tree change the user can review.

        Args:
            content: New ``.gitignore`` content.

        Returns:
            Dict with 'success', 'path', 'root', 'exists', 'content' and
            'errors'.
        """
        path = self.get_gitignore_path()
        normalized = str(content or "").replace("\r\n", "\n").replace("\r", "\n")
        if normalized and not normalized.endswith("\n"):
            normalized += "\n"
        result = {
            "success": False,
            "path": path,
            "root": self.get_gitignore_root(),
            "exists": os.path.isfile(path),
            "content": normalized,
            "errors": [],
        }
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(normalized)
        except OSError as ex:
            logger.error("Could not write %s: %s", path, ex)
            result["errors"].append(f"Could not write {path}: {ex}")
            return result

        result["exists"] = True
        result["success"] = True
        return result

    def _gitignore_relative_path(self, raw_path: str, root: str) -> str:
        """
        Resolve a file/folder path to a pattern path relative to *root*.

        Absolute paths outside the checkout and ``..`` escapes are rejected:
        the ignore file must never reference files outside the repository.

        Args:
            raw_path: Repo/project-relative or absolute path.
            root: Checkout root containing the ``.gitignore``.

        Returns:
            Normalized relative path, or an empty string when it is not usable.
        """
        path = str(raw_path or "").strip().strip('"\'')
        if not path or "\n" in path:
            return ""
        path = path.replace("\\", "/")
        if os.path.isabs(path):
            try:
                path = os.path.relpath(os.path.realpath(path), os.path.realpath(root))
            except (OSError, ValueError):
                return ""
        relative = os.path.normpath(path).replace("\\", "/")
        while relative.startswith("./"):
            relative = relative[2:]
        if not relative or relative == "." or relative.startswith(".."):
            return ""
        return relative

    @staticmethod
    def _gitignore_pattern(relative_path: str, is_dir: bool) -> str:
        """
        Build an anchored gitignore pattern for one path.

        The leading ``/`` anchors the pattern at the repository root, so
        ``/config/`` ignores the root folder without hiding every ``config``
        folder in the tree. Glob characters in the literal path are escaped.

        Args:
            relative_path: Path relative to the checkout root.
            is_dir: Whether the entry is a folder.

        Returns:
            Gitignore pattern, e.g. ``/logs/``.
        """
        escaped = re.sub(r"([\\*?\[\]])", r"\\\1", relative_path)
        return f"/{escaped}" + ("/" if is_dir else "")

    def add_to_gitignore(self, entries: List[dict]) -> dict:
        """
        Append ignore patterns for files/folders to the checkout's `.gitignore`.

        Existing patterns are never duplicated and the rest of the document is
        preserved (comments, blank lines, negations). Every entry is resolved
        against the checkout root and writes are atomic enough for this small
        text file.

        Args:
            entries: ``[{'path': 'build', 'is_dir': True}, ...]``. ``is_dir`` is
                inferred from the filesystem when omitted.

        Returns:
            Dict with 'success', 'path', 'root', 'exists', 'content', 'added',
            'skipped' and 'errors'.

        Example:
            >>> engine.add_to_gitignore([{'path': 'node_modules', 'is_dir': True}])
            {'success': True, 'added': ['/node_modules/'], ...}
        """
        root = self.get_gitignore_root()
        path = os.path.join(root, GITIGNORE_FILE)
        current = self.get_gitignore()
        content = current.get("content") or ""
        lines = content.splitlines()

        result = {
            "success": False,
            "path": path,
            "root": root,
            "exists": bool(current.get("exists")),
            "content": content,
            "added": [],
            "skipped": [],
            "errors": list(current.get("errors") or []),
        }
        if not current.get("success"):
            return result

        existing = {
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        }

        for entry in entries or []:
            if isinstance(entry, str):
                raw_path = entry
                is_dir = False
            else:
                raw_path = (entry or {}).get("path") or ""
                is_dir = bool((entry or {}).get("is_dir"))
            relative = self._gitignore_relative_path(raw_path, root)
            if not relative:
                result["errors"].append(f"Invalid path for .gitignore: {raw_path}")
                continue
            if not is_dir:
                is_dir = os.path.isdir(os.path.join(root, relative))
            pattern = self._gitignore_pattern(relative, is_dir)
            if pattern in existing:
                result["skipped"].append(pattern)
                continue
            lines.append(pattern)
            existing.add(pattern)
            result["added"].append(pattern)

        if not result["added"]:
            result["success"] = not result["errors"]
            return result

        new_content = "\n".join(lines).rstrip() + "\n"
        saved = self.save_gitignore(new_content)
        result["content"] = saved.get("content") or new_content
        result["exists"] = saved.get("exists", False)
        result["success"] = bool(saved.get("success"))
        result["errors"].extend(saved.get("errors") or [])
        return result

    def _create_branch_worktree(
        self,
        repo_path: str,
        branch_name: str,
        base_ref: str,
        branch_exists: bool,
        worktree_path: Optional[str] = None,
    ) -> dict:
        """
        Create (or reuse) a worktree holding the given branch.

        Args:
            repo_path: Absolute repository root.
            branch_name: Branch to check out in the worktree.
            base_ref: Ref used to create the branch when it does not exist yet.
            branch_exists: Whether the branch already exists locally.
            worktree_path: Optional target path. Relative paths are resolved
                against the worktrees base path (never against the repository).
                Defaults to `<worktrees path>/<branch slug>`.

        Returns:
            Dict with 'ok', 'path', 'output' and 'error'.
        """
        repo_root = os.path.normpath(repo_path)

        existing_path = self.get_worktree_path_for_branch(branch_name)
        if existing_path and os.path.isdir(existing_path):
            return {
                "ok": True,
                "path": existing_path,
                "output": f"reusing worktree {existing_path}",
                "error": "",
            }

        if existing_path:
            # Stale registration: the folder was removed outside git and would
            # block the path, prune the administration data
            logger.warning(
                "Stale worktree registration for '%s': %s", branch_name, existing_path
            )
            self._run_git(["worktree", "prune"], cwd=repo_root)

        target_path = worktree_path or os.path.join(
            self.get_worktrees_path(),
            re.sub(r"[^a-zA-Z0-9_.-]+", "-", branch_name).strip("-"),
        )
        if not os.path.isabs(target_path):
            # Resolve against the worktrees base: resolving against the
            # repository would create the worktree inside the working tree
            target_path = os.path.join(self.get_worktrees_path(), target_path)
        target_path = os.path.normpath(target_path)

        if target_path == repo_root or target_path.startswith(repo_root + os.sep):
            return {
                "ok": False,
                "path": target_path,
                "output": "",
                "error": (
                    f"Worktree path '{target_path}' must be outside the "
                    f"repository '{repo_root}'; check the project's "
                    "git_worktrees_path setting"
                ),
            }

        try:
            os.makedirs(target_path, exist_ok=True)
        except OSError as ex:
            return {
                "ok": False,
                "path": target_path,
                "output": "",
                "error": f"Could not create worktree folder {target_path}: {ex}",
            }

        if branch_exists:
            args = ["worktree", "add", target_path, branch_name]
        else:
            args = ["worktree", "add", "-b", branch_name, target_path, base_ref]

        result = self._run_git(args, cwd=repo_root)
        return {
            "ok": result["ok"],
            "path": target_path,
            "output": result["output"],
            "error": result["error"],
        }

    def _current_branch(self, cwd: Optional[str] = None) -> str:
        """
        Return the branch currently checked out in *cwd* (empty when detached).

        Args:
            cwd: Working directory. Defaults to the repository root.

        Returns:
            Current branch name, or an empty string for a detached HEAD.
        """
        result = self._run_git(["branch", "--show-current"], cwd=cwd)
        return result["output"] if result["ok"] else ""

    def get_default_branch(self) -> str:
        """
        Return the repository's default (integration) branch.

        Resolution order: ``main``, ``master``, ``develop``, the remote HEAD,
        and finally the first local branch found.

        Returns:
            Default branch name, or an empty string when it cannot be resolved.
        """
        repo_path = self._get_repo_root()
        for candidate in ("main", "master", "develop"):
            if self._ref_exists(f"refs/heads/{candidate}", cwd=repo_path):
                return candidate

        remote_head = self._run_git(
            ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=repo_path
        )
        if remote_head["ok"] and remote_head["output"]:
            return self._sanitize_branch_name(remote_head["output"].split("/")[-1])

        refs = self._run_git(
            ["for-each-ref", "--format=%(refname:short)", "refs/heads"],
            cwd=repo_path,
        )
        branches = [b.strip() for b in refs["output"].split("\n") if b.strip()]
        return branches[0] if branches else ""

    def _remove_worktree(self, branch_name: str, cwd: Optional[str] = None) -> dict:
        """
        Remove the worktree registered for *branch_name*, when it exists.

        Args:
            branch_name: Branch whose worktree should be removed.
            cwd: Working directory. Defaults to the repository root.

        Returns:
            Dict with 'ok', 'removed' (True when a worktree was deleted),
            'path', 'output' and 'error'.
        """
        worktree_path = self.get_worktree_path_for_branch(branch_name)
        if not worktree_path:
            return {
                "ok": True,
                "removed": False,
                "path": "",
                "output": "no worktree registered",
                "error": "",
            }

        # The main checkout is not a removable worktree: never try (git would
        # fail with "is a main working tree"), just report nothing to remove.
        if self._same_path(worktree_path, self._get_repo_root()):
            return {
                "ok": True,
                "removed": False,
                "path": worktree_path,
                "output": "main checkout is not removed",
                "error": "",
            }

        result = self._force_remove_worktree_path(worktree_path, cwd=cwd)

        return {
            "ok": result["ok"],
            "removed": result["removed"],
            "path": worktree_path,
            "output": result["output"],
            "error": result["error"],
        }

    def _delete_branch(
        self, branch_name: str, cwd: Optional[str] = None, force: bool = True
    ) -> dict:
        """
        Delete a local branch.

        Args:
            branch_name: Branch to delete.
            cwd: Working directory. Defaults to the repository root.
            force: Use ``-D`` (delete without merge check) when True.

        Returns:
            Dict with 'ok', 'deleted' (True when a branch was deleted),
            'output' and 'error'.
        """
        if not self._ref_exists(f"refs/heads/{branch_name}", cwd=cwd):
            return {
                "ok": True,
                "deleted": False,
                "output": "branch not found",
                "error": "",
            }

        result = self._run_git(
            ["branch", "-D" if force else "-d", branch_name], cwd=cwd
        )
        return {
            "ok": result["ok"],
            "deleted": result["ok"],
            "output": result["output"],
            "error": result["error"],
        }

    def _commit_all(
        self, cwd: str, message: str, allow_empty: bool = True
    ) -> dict:
        """
        Stage every change and commit it.

        Staging never aborts on a single failing path: the paths that could be
        staged are committed and the failures are returned in 'staging_errors'.

        Args:
            cwd: Working directory (repository root or worktree path).
            message: Commit message.
            allow_empty: Allow commits without content changes.

        Returns:
            Result dict of the commit command, extended with 'staged' (paths
            staged) and 'staging_errors' (staging failures).
        """
        staging = self.stage_changes(cwd=cwd)

        if not staging["ok"] and not staging["staged"]:
            # Nothing could be staged: report why instead of committing
            return {
                "ok": False,
                "command": "git add",
                "output": staging["output"],
                "error": "; ".join(staging["errors"]),
                "returncode": -1,
                "staged": [],
                "staging_errors": staging["errors"],
                "locked": staging.get("locked", False),
                "lock_path": staging.get("lock_path", ""),
            }

        args = ["commit", "-m", message]
        if allow_empty:
            args.append("--allow-empty")
        commit = self._run_git(args, cwd=cwd)

        return {
            **commit,
            "staged": staging["staged"],
            "staging_errors": staging["errors"],
        }

    def create_pr_branch(
        self,
        branch_name: Optional[str] = None,
        files_content: Optional[Dict[str, str]] = None,
        base_branch: Optional[str] = None,
        commit_message: Optional[str] = None,
        use_worktree: bool = False,
        worktree_path: Optional[str] = None,
        allow_empty: bool = True,
    ) -> dict:
        """
        Create a local PR branch from the current branch with the chat changes.

        PRs are reviewed locally by codx-junior, so nothing is pushed to the
        remote: the workflow ends once the branch and its commit exist locally.

        Workflow:
            1. Resolve the base branch: `base_branch` or the **current** branch.
            2. Create the branch from that base, either:
               - as a git worktree (`use_worktree=True`): the main checkout and
                 its uncommitted changes stay untouched, or
               - in the project working tree (`use_worktree=False`): the repo is
                 switched to the new branch.
            3. Write `files_content` (optional) and commit every change.

        Args:
            branch_name: Target PR branch (e.g. 'codx-junior/fix-login').
                Generated automatically when omitted.
            files_content: Optional map of repo-relative file path -> full content.
                Omit it to commit the changes already present on disk.
            base_branch: Base branch. Defaults to the current branch.
            commit_message: Commit message. Defaults to a generic message.
            use_worktree: Create the branch as a worktree (default: False).
            worktree_path: Custom worktree folder (absolute, or relative to the
                worktrees base path). Defaults to
                `<worktrees path>/<branch slug>`.
            allow_empty: Allow commits with no content changes.

        Returns:
            Dict with 'success', 'branch', 'base_branch', 'base_ref',
            'original_branch', 'commit', 'files_written', 'worktree',
            'worktree_path', 'branch_checked_out', 'steps', 'errors' and
            'repo_path'.

        Example:
            Create a local PR branch from the current branch, in a worktree:
            >>> engine.create_pr_branch(
            ...     branch_name="codx-junior/fix-login",
            ...     commit_message="fix: login timeout",
            ...     use_worktree=True,
            ... )
            {'success': True, 'branch': 'codx-junior/fix-login', ...}
        """
        repo_path = self._get_repo_root()
        original_branch = (self.get_project_current_branch() or "").strip()

        base_branch = (
            self._sanitize_branch_name(base_branch) if base_branch else original_branch
        )
        branch_name = (
            self._sanitize_branch_name(branch_name) if branch_name else ""
        ) or self.build_branch_name()

        result = {
            "success": False,
            "branch": branch_name,
            "base_branch": base_branch,
            "base_ref": None,
            "original_branch": original_branch,
            "commit": "",
            "files_written": [],
            "worktree": False,
            "worktree_path": "",
            "branch_checked_out": False,
            "steps": [],
            "errors": [],
            "repo_path": repo_path,
        }

        if not branch_name:
            result["errors"].append("branch_name is required")
            return result

        if base_branch and branch_name == base_branch:
            result["errors"].append(
                f"Branch name '{branch_name}' must differ from the base branch"
            )
            return result

        if files_content is not None and not isinstance(files_content, dict):
            result["errors"].append("files_content must be a dictionary")
            return result

        status = self.get_working_tree_status()
        result["steps"].append({
            "name": "status",
            "ok": status["ok"],
            "output": f"{len(status['files'])} changed file(s)",
            "error": status["error"],
        })
        if not status["ok"]:
            result["errors"].append(f"Could not read git status: {status['error']}")
            return result

        commit_message = commit_message or DEFAULT_COMMIT_MESSAGE

        base_ref = self._resolve_base_ref(base_branch, repo_path) or "HEAD"
        result["base_ref"] = base_ref

        branch_exists = self._ref_exists(
            f"refs/heads/{branch_name}", cwd=repo_path
        )

        if use_worktree:
            worktree_result = self._create_branch_worktree(
                repo_path=repo_path,
                branch_name=branch_name,
                base_ref=base_ref,
                branch_exists=branch_exists,
                worktree_path=worktree_path,
            )
            result["steps"].append({"name": "worktree", **worktree_result})
            if not worktree_result["ok"]:
                result["errors"].append(
                    f"Could not create worktree for '{branch_name}': "
                    f"{worktree_result['error']}"
                )
                return result

            result["worktree"] = True
            result["worktree_path"] = worktree_result["path"]
            work_path = worktree_result["path"]
        else:
            checkout = self._run_git(
                ["checkout", branch_name]
                if branch_exists
                else ["checkout", "-b", branch_name, base_ref]
            )
            result["steps"].append({"name": "checkout", **checkout})
            if not checkout["ok"]:
                result["errors"].append(
                    f"Could not checkout branch '{branch_name}': {checkout['error']}"
                )
                return result

            work_path = repo_path
            result["branch_checked_out"] = True

        for file_path, content in (files_content or {}).items():
            write_result = self._write_repo_file(
                repo_path=work_path,
                file_path=file_path,
                content=content,
            )
            result["steps"].append({"name": "write", **write_result})
            if write_result["ok"]:
                result["files_written"].append(write_result["file_path"])
            else:
                result["errors"].append(
                    f"Could not write '{file_path}': {write_result['error']}"
                )

        if result["errors"]:
            return result

        commit = self._commit_all(
            cwd=work_path, message=commit_message, allow_empty=allow_empty
        )
        result["steps"].append({"name": "commit", **commit})
        if not commit["ok"]:
            result["errors"].append(
                f"Could not commit changes: {commit['error'] or commit['output']}"
            )
            return result

        head = self._run_git(["rev-parse", "HEAD"], cwd=work_path)
        if head["ok"]:
            result["commit"] = head["output"]

        result["success"] = not result["errors"]
        return result

    def close_pr_branch(
        self,
        branch_name: str,
        base_branch: Optional[str] = None,
        commit_message: Optional[str] = None,
        delete_branch: bool = False,
    ) -> dict:
        """
        Close a local PR by merging its branch into the base branch.

        Workflow:
            1. Resolve the base branch (`base_branch`, the branch currently
               checked out, or the repository default branch).
            2. Stash local changes so the checkout never fails.
            3. Check out the base branch and ``git merge --no-ff <branch>``.
               Conflicts abort the merge and are reported.
            4. Remove the branch worktree, when one exists.
            5. Optionally delete the merged branch.
            6. Restore the stashed local changes.

        Nothing is pushed: PRs are reviewed and merged locally by codx-junior.

        Args:
            branch_name: PR branch to merge.
            base_branch: Branch to merge into. Defaults to the current branch,
                or the repository default branch when the PR branch is the one
                checked out.
            commit_message: Merge commit message. Defaults to
                ``"Merge branch '<branch>' into '<base>'"``.
            delete_branch: Delete the PR branch after merging (default: False).

        Returns:
            Dict with 'success', 'action', 'branch', 'base_branch',
            'original_branch', 'commit', 'worktree_removed', 'branch_deleted',
            'steps', 'errors' and 'repo_path'.

        Example:
            >>> engine.close_pr_branch(branch_name="codx-junior/fix-login")
            {'success': True, 'branch': 'codx-junior/fix-login', ...}
        """
        repo_path = self._get_repo_root()
        branch_name = self._sanitize_branch_name(branch_name)

        result = {
            "success": False,
            "action": "merge",
            "branch": branch_name,
            "base_branch": (
                self._sanitize_branch_name(base_branch) if base_branch else ""
            ),
            "original_branch": "",
            "commit": "",
            "worktree_removed": False,
            "branch_deleted": False,
            "steps": [],
            "errors": [],
            "repo_path": repo_path,
        }

        if not branch_name:
            result["errors"].append("branch_name is required")
            return result

        original_branch = self._current_branch(repo_path)
        result["original_branch"] = original_branch
        current_branch = (
            self._sanitize_branch_name(original_branch) if original_branch else ""
        )

        if not self._ref_exists(f"refs/heads/{branch_name}", cwd=repo_path):
            result["errors"].append(f"Branch '{branch_name}' not found")
            return result

        base = result["base_branch"] or (
            current_branch
            if current_branch and current_branch != branch_name
            else self.get_default_branch()
        )
        result["base_branch"] = base

        if not base:
            result["errors"].append(
                "Could not determine the base branch to merge into"
            )
            return result
        if base == branch_name:
            result["errors"].append(
                f"Branch '{branch_name}' cannot be merged into itself"
            )
            return result

        status = self.get_working_tree_status()
        result["steps"].append({
            "name": "status",
            "ok": status["ok"],
            "output": f"{len(status['files'])} changed file(s)",
            "error": status["error"],
        })
        if not status["ok"]:
            result["errors"].append(f"Could not read git status: {status['error']}")
            return result

        message = commit_message or f"Merge branch '{branch_name}' into '{base}'"
        stashed = False
        try:
            # Keep local work safe: checkout would fail on a dirty tree
            if status["dirty"]:
                stash = self._run_git([
                    "stash", "push", "-u",
                    "-m", f"codx-junior: auto-stash before closing {branch_name}",
                ], cwd=repo_path)
                result["steps"].append({"name": "stash", **stash})
                if not stash["ok"]:
                    result["errors"].append(
                        f"Could not stash local changes: {stash['error']}"
                    )
                    return result
                stashed = True

            if current_branch != base:
                checkout = self._run_git(["checkout", base], cwd=repo_path)
                result["steps"].append({"name": "checkout", **checkout})
                if not checkout["ok"]:
                    result["errors"].append(
                        f"Could not checkout base branch '{base}': "
                        f"{checkout['error']}"
                    )
                    return result

            merge = self._run_git(
                ["merge", "--no-ff", branch_name, "-m", message], cwd=repo_path
            )
            result["steps"].append({"name": "merge", **merge})
            if not merge["ok"]:
                self._run_git(["merge", "--abort"], cwd=repo_path)
                result["errors"].append(
                    f"Could not merge '{branch_name}' into '{base}': "
                    f"{merge['error'] or merge['output']}"
                )
                return result

            head = self._run_git(["rev-parse", "HEAD"], cwd=repo_path)
            if head["ok"]:
                result["commit"] = head["output"]

            worktree = self._remove_worktree(branch_name, cwd=repo_path)
            result["steps"].append({"name": "worktree-remove", **worktree})
            result["worktree_removed"] = worktree["removed"]
            if not worktree["ok"]:
                result["errors"].append(
                    f"Could not remove worktree '{worktree['path']}': "
                    f"{worktree['error']}"
                )
                return result

            if delete_branch:
                deleted = self._delete_branch(branch_name, cwd=repo_path)
                result["steps"].append({"name": "branch-delete", **deleted})
                result["branch_deleted"] = deleted["deleted"]
                if not deleted["ok"]:
                    result["errors"].append(
                        f"Could not delete branch '{branch_name}': "
                        f"{deleted['error']}"
                    )

            return result
        finally:
            if stashed:
                pop = self._run_git(["stash", "pop"], cwd=repo_path)
                result["steps"].append({"name": "stash-pop", **pop})
                if not pop["ok"]:
                    result["errors"].append(
                        "Could not restore stashed local changes. "
                        "Run 'git stash pop' manually."
                    )
            result["success"] = not result["errors"]

    def abandon_pr_branch(
        self,
        branch_name: str,
        base_branch: Optional[str] = None,
        delete_branch: bool = True,
    ) -> dict:
        """
        Abandon a local PR: remove its worktree and drop the branch.

        The PR changes are discarded: the branch (and its commits) is deleted,
        so the base branch never receives them. When the repository is checked
        out on the PR branch, the base branch is checked out first (local
        changes are never forced away — a failed checkout is reported).

        Args:
            branch_name: PR branch to abandon.
            base_branch: Branch to return to when the PR branch is checked out.
                Defaults to the repository default branch.
            delete_branch: Delete the (unmerged) branch (default: True).

        Returns:
            Dict with 'success', 'action', 'branch', 'base_branch',
            'restored_branch', 'worktree_removed', 'branch_deleted',
            'steps', 'errors' and 'repo_path'.

        Example:
            >>> engine.abandon_pr_branch(branch_name="codx-junior/fix-login")
            {'success': True, 'branch': 'codx-junior/fix-login', ...}
        """
        repo_path = self._get_repo_root()
        branch_name = self._sanitize_branch_name(branch_name)

        result = {
            "success": False,
            "action": "discard",
            "branch": branch_name,
            "base_branch": (
                self._sanitize_branch_name(base_branch) if base_branch else ""
            ),
            "restored_branch": "",
            "worktree_removed": False,
            "branch_deleted": False,
            "steps": [],
            "errors": [],
            "repo_path": repo_path,
        }

        if not branch_name:
            result["errors"].append("branch_name is required")
            return result

        # 1. Remove the worktree (if the branch lives in one)
        worktree = self._remove_worktree(branch_name, cwd=repo_path)
        result["steps"].append({"name": "worktree-remove", **worktree})
        result["worktree_removed"] = worktree["removed"]
        if not worktree["ok"]:
            result["errors"].append(
                f"Could not remove worktree '{worktree['path']}': "
                f"{worktree['error']}"
            )
            return result

        # 2. Leave the PR branch before deleting it
        current_branch = self._current_branch(repo_path)
        if current_branch == branch_name:
            base = result["base_branch"] or self.get_default_branch()
            result["base_branch"] = base
            if not base or base == branch_name:
                result["errors"].append(
                    f"Cannot abandon '{branch_name}' while it is checked out: "
                    "provide a base_branch to return to"
                )
                return result

            checkout = self._run_git(["checkout", base], cwd=repo_path)
            result["steps"].append({"name": "checkout", **checkout})
            if not checkout["ok"]:
                result["errors"].append(
                    f"Could not checkout '{base}': {checkout['error']}"
                )
                return result
            result["restored_branch"] = base

        # 3. Drop the branch
        if delete_branch:
            deleted = self._delete_branch(branch_name, cwd=repo_path)
            result["steps"].append({"name": "branch-delete", **deleted})
            result["branch_deleted"] = deleted["deleted"]
            if not deleted["ok"]:
                result["errors"].append(
                    f"Could not delete branch '{branch_name}': {deleted['error']}"
                )
                return result

        result["success"] = not result["errors"]
        return result

    # -------------------------------------------------------------------------
    # Repository lock (stale .git/index.lock)
    # -------------------------------------------------------------------------

    def _git_dir(self) -> str:
        """
        Return the absolute path of the repository git directory.

        Returns:
            Absolute git directory path (``<repo>/.git`` on fallback).
        """
        result = self._run_git(["rev-parse", "--git-dir"])
        git_dir = result["output"] if result["ok"] else ""
        if not git_dir:
            return os.path.join(self._get_repo_root(), ".git")
        if not os.path.isabs(git_dir):
            git_dir = os.path.join(self._get_repo_root(), git_dir)
        return os.path.normpath(git_dir)

    def get_lock_info(self) -> dict:
        """
        Return whether the repository is locked by a stale index lock.

        Git creates ``.git/index.lock`` while it writes the index and removes it
        afterwards. When a git process is interrupted the file is left behind
        and every later write fails with
        ``Unable to create '.../index.lock': File exists``.

        Returns:
            Dict with 'locked', 'path' (empty when not locked), 'git_dir',
            'repository' and 'age_seconds' (0 when not locked).

        Example:
            >>> engine.get_lock_info()
            {'locked': True, 'path': '/repo/.git/index.lock',
             'git_dir': '/repo/.git', 'repository': '/repo', 'age_seconds': 120}
        """
        git_dir = self._git_dir()
        lock_path = os.path.join(git_dir, INDEX_LOCK_FILE)
        locked = os.path.exists(lock_path)
        info = {
            "locked": locked,
            "path": lock_path if locked else "",
            "git_dir": git_dir,
            "repository": self._get_repo_root(),
            "age_seconds": 0,
        }
        if locked:
            try:
                info["age_seconds"] = max(
                    0,
                    int(datetime.now().timestamp() - os.path.getmtime(lock_path)),
                )
            except OSError:
                pass
        return info

    def release_lock(self) -> dict:
        """
        Remove the stale ``.git/index.lock`` file.

        Only safe when no git process is actually running: removing the lock of
        a live process can corrupt the index, so the UI asks the user first.

        Returns:
            Dict with 'success', 'released' (True when a file was removed),
            'path', 'output', 'errors' and 'lock' (the refreshed lock info).

        Example:
            >>> engine.release_lock()
            {'success': True, 'released': True,
             'path': '/repo/.git/index.lock', ...}
        """
        info = self.get_lock_info()
        lock_path = info.get("path", "")
        if not info.get("locked"):
            return {
                "success": True,
                "released": False,
                "path": "",
                "output": "No lock to release",
                "errors": [],
                "lock": info,
            }

        try:
            os.remove(lock_path)
        except OSError as ex:
            return {
                "success": False,
                "released": False,
                "path": lock_path,
                "output": "",
                "errors": [f"Could not remove {lock_path}: {ex}"],
                "lock": self.get_lock_info(),
            }

        logger.warning("Released stale git lock: %s", lock_path)
        return {
            "success": True,
            "released": True,
            "path": lock_path,
            "output": f"Removed {lock_path}",
            "errors": [],
            "lock": self.get_lock_info(),
        }

    # -------------------------------------------------------------------------
    # Repository management (fetch/pull/push, branches, commit, merge)
    # -------------------------------------------------------------------------

    def get_repo_info(self) -> dict:
        """
        Return a summary of the repository state used by the git view header.

        Returns:
            Dict with repo path, project path, active/default branch, remote
            url, ahead/behind counters, working tree state (including the
            staged and unstaged file lists), lock state, worktrees, the git
            identity commits are signed with, the token state (never the token
            itself) and the last commit. Every worktree also carries
            ``merge_status``: the files its branch would bring into the current
            branch. 'changed_files' lists one entry per changed file: untracked
            directories are expanded and untracked nested repositories
            (submodules) are ignored, so it never contains folder paths nor
            files belonging to a submodule.

        Example:
            >>> engine.get_repo_info()["active_branch"]
            'main'
        """
        current_branch = self._sanitize_branch_name(
            self.get_project_current_branch()
        )
        status = self.get_working_tree_status()
        changes = self.get_status_changes(status["files"])
        remote_url = self._get_remote_url()
        ahead, behind = self._get_ahead_behind(current_branch)
        commits = self.get_commit_list(limit=1)
        lock = self.get_lock_info()
        identity = self.get_git_identity()

        # Worktree change lists. The main worktree reuses the status already
        # read above instead of running `git status` on the same folder twice
        # (a large working tree makes that duplicate scan expensive).
        main_changes = {
            "ok": status["ok"],
            "dirty": status["dirty"],
            "files": status["files"],
            "staged": changes["staged"],
            "unstaged": changes["unstaged"],
            "file_count": len(status["files"]),
            "errors": [] if status["ok"] else [status["error"]],
        }
        worktrees = self.list_worktrees(include_changes=False)
        for worktree in worktrees:
            worktree["changes"] = (
                main_changes
                if worktree.get("is_main")
                else self._worktree_changes(worktree["path"])
            )
            # Repository view hint: does this worktree branch have files
            # pending to merge into the branch currently checked out?
            worktree["merge_status"] = self.get_worktree_merge_status(
                worktree.get("branch", ""), current_branch
            )

        return {
            "repo_path": self._get_repo_root(),
            "project_path": self.settings.abs_project_path,
            "active_branch": current_branch,
            "default_branch": self.get_default_branch(),
            "remote_url": remote_url,
            "has_remote": bool(remote_url),
            "ahead": ahead,
            "behind": behind,
            "dirty": status["dirty"],
            "changed_files": status["files"],
            "staged": changes["staged"],
            "unstaged": changes["unstaged"],
            "locked": lock["locked"],
            "lock_path": lock["path"],
            "worktrees": worktrees,
            "git_identity": identity,
            "git_token": self.get_git_token_info(),
            "last_commit": commits[0] if commits else None,
        }

    def get_repo_status(self) -> dict:
        """
        Return the working tree status.

        Returns:
            Dict with 'success', 'dirty', 'files', 'staged', 'unstaged' and
            'errors'.

        Example:
            >>> engine.get_repo_status()["staged"]
            [{'path': 'app.py', 'code': 'M', 'status': 'modified'}]
        """
        status = self.get_working_tree_status()
        changes = self.get_status_changes(status["files"])
        return {
            "success": status["ok"],
            "dirty": status["dirty"],
            "files": status["files"],
            "staged": changes["staged"],
            "unstaged": changes["unstaged"],
            "errors": [] if status["ok"] else [status["error"]],
        }

    def fetch_remote(
        self, remote: str = DEFAULT_REMOTE, prune: bool = True
    ) -> dict:
        """
        Fetch refs (and prune deleted ones) from a remote.

        The project access token (when configured) authenticates the request, so
        private HTTPS remotes work without a credential helper.

        Args:
            remote: Remote name.
            prune: Remove remote-tracking refs that no longer exist.

        Returns:
            Operation result dict.
        """
        if not self._get_remote_url(remote):
            return self._git_operation_error(f"No remote '{remote}' configured")

        args: List[str] = ["fetch", remote]
        if prune:
            args.append("--prune")
        return self._git_operation_result(self._run_git(args))

    def pull_remote(
        self, remote: str = DEFAULT_REMOTE, branch: Optional[str] = None
    ) -> dict:
        """
        Pull the current (or given) branch from a remote.

        The project access token (when configured) authenticates the request.

        Args:
            remote: Remote name.
            branch: Branch to pull. Defaults to the checked out branch.

        Returns:
            Operation result dict.

        Example:
            >>> engine.pull_remote()
            {'success': True, 'branch': 'main', ...}
        """
        if not self._get_remote_url(remote):
            return self._git_operation_error(f"No remote '{remote}' configured")

        branch = self._sanitize_branch_name(branch) or (
            self.get_project_current_branch()
        )
        if not branch:
            return self._git_operation_error("Cannot pull while HEAD is detached")

        result = self._run_git(
            ["pull", "--no-rebase", "--no-edit", remote, branch]
        )
        return self._git_operation_result(result, branch=branch)

    def push_remote(
        self,
        remote: str = DEFAULT_REMOTE,
        branch: Optional[str] = None,
        set_upstream: bool = True,
    ) -> dict:
        """
        Push the current (or given) branch to a remote.

        The project access token (when configured) authenticates the request.
        Without it a headless API cannot answer git's interactive username
        prompt, so the failure is reported with an actionable hint instead of a
        bare ``could not read Username``.

        Args:
            remote: Remote name.
            branch: Branch to push. Defaults to the checked out branch.
            set_upstream: Set the upstream tracking reference (``-u``).

        Returns:
            Operation result dict ('auth_error' is set when the remote rejected
            the credentials).

        Example:
            >>> engine.push_remote()
            {'success': True, 'branch': 'main', ...}
        """
        if not self._get_remote_url(remote):
            return self._git_operation_error(f"No remote '{remote}' configured")

        branch = self._sanitize_branch_name(branch) or (
            self.get_project_current_branch()
        )
        if not branch:
            return self._git_operation_error("Cannot push while HEAD is detached")

        args: List[str] = ["push"]
        if set_upstream:
            args.append("--set-upstream")
        args += [remote, branch]

        return self._git_operation_result(self._run_git(args), branch=branch)

    def create_branch(
        self,
        branch: str,
        from_branch: Optional[str] = None,
        checkout: bool = False,
    ) -> dict:
        """
        Create a branch from another branch (or HEAD).

        Args:
            branch: New branch name.
            from_branch: Base branch. Defaults to the checked out branch.
            checkout: Switch to the new branch after creating it.

        Returns:
            Operation result dict with 'branch' and 'base_ref'.

        Example:
            >>> engine.create_branch("feature/login", from_branch="main")
            {'success': True, 'branch': 'feature/login', ...}
        """
        branch = self._sanitize_branch_name(branch)
        if not branch:
            return self._git_operation_error("Branch name is required")

        check = self._run_git(["check-ref-format", "--branch", branch])
        if not check["ok"]:
            return self._git_operation_error(
                f"Invalid branch name '{branch}': {check['error']}", branch=branch
            )

        if self._ref_exists(f"refs/heads/{branch}"):
            return self._git_operation_error(
                f"Branch '{branch}' already exists", branch=branch
            )

        base_ref = self._resolve_base_ref(from_branch, self._get_repo_root()) or "HEAD"
        result = self._run_git(["branch", branch, base_ref])
        response = self._git_operation_result(
            result, branch=branch, base_ref=base_ref
        )
        if not response["success"]:
            return response

        if checkout:
            switch = self._run_git(["checkout", branch])
            response["steps"] = [self._git_operation_result(switch)]
            if not switch["ok"]:
                response.update(
                    success=False,
                    errors=[f"Branch created but checkout failed: {switch['error']}"],
                )

        return response

    def checkout_branch(self, branch: str) -> dict:
        """
        Check out a local branch, tracking the remote branch when needed.

        Args:
            branch: Branch name.

        Returns:
            Operation result dict with 'branch'.
        """
        branch = self._sanitize_branch_name(branch)
        if not branch:
            return self._git_operation_error("Branch name is required")

        if self._ref_exists(f"refs/heads/{branch}"):
            result = self._run_git(["checkout", branch])
            return self._git_operation_result(result, branch=branch)

        if self._ref_exists(f"refs/remotes/{DEFAULT_REMOTE}/{branch}"):
            result = self._run_git(
                ["checkout", "-b", branch, f"{DEFAULT_REMOTE}/{branch}"]
            )
            return self._git_operation_result(
                result, branch=branch, created_from_remote=True
            )

        return self._git_operation_error(
            f"Branch '{branch}' not found", branch=branch
        )

    def delete_branch(self, branch: str, force: bool = True) -> dict:
        """
        Delete a local branch, removing its worktree first when it has one.

        Args:
            branch: Branch name.
            force: Delete even when the branch is not merged (``-D``).

        Returns:
            Operation result dict with 'branch', 'deleted' and
            'worktree_removed'.
        """
        branch = self._sanitize_branch_name(branch)
        if not branch:
            return self._git_operation_error("Branch name is required")

        repo_path = self._get_repo_root()
        current_branch = self._sanitize_branch_name(
            self.get_project_current_branch()
        )
        if branch == current_branch:
            return self._git_operation_error(
                f"Cannot delete '{branch}' while it is checked out", branch=branch
            )

        worktree = self._remove_worktree(branch, cwd=repo_path)
        if not worktree["ok"]:
            return self._git_operation_error(
                f"Could not remove worktree '{worktree['path']}': "
                f"{worktree['error']}",
                branch=branch,
            )

        deleted = self._delete_branch(branch, cwd=repo_path, force=force)
        if not deleted["ok"]:
            return self._git_operation_error(
                f"Could not delete branch '{branch}': {deleted['error']}",
                branch=branch,
            )

        return {
            "success": True,
            "branch": branch,
            "deleted": deleted["deleted"],
            "worktree_removed": worktree["removed"],
            "output": deleted["output"],
            "errors": [],
        }

    def commit_changes(
        self,
        message: str,
        stage_all: bool = True,
        allow_empty: bool = False,
    ) -> dict:
        """
        Commit the working tree changes.

        Staging is done path by path: a path that cannot be staged is reported
        in 'staging_errors' and never blocks the commit of the remaining
        changes. Untracked nested repositories (submodules) are not staged.

        Args:
            message: Commit message.
            stage_all: Stage every change before committing (``git add -A``).
            allow_empty: Allow commits with no content changes.

        Returns:
            Operation result dict with 'commit' (full hash), 'short_commit'
            and 'staging_errors'.

        Example:
            >>> engine.commit_changes("feat: add git management")
            {'success': True, 'commit': 'a1b2c3...', ...}
        """
        message = (message or "").strip()
        if not message:
            return self._git_operation_error("Commit message is required")

        repo_path = self._get_repo_root()
        if stage_all:
            result = self._commit_all(
                cwd=repo_path, message=message, allow_empty=allow_empty
            )
        else:
            args: List[str] = ["commit", "-m", message]
            if allow_empty:
                args.append("--allow-empty")
            result = self._run_git(args, cwd=repo_path)

        response = self._git_operation_result(
            result,
            message=message,
            stage_all=stage_all,
            staging_errors=result.get("staging_errors", []),
        )
        if not response["success"]:
            error = (result["error"] or result["output"] or "").strip()
            response["errors"] = [error or "Could not commit changes"]
            return response

        head = self._run_git(["rev-parse", "HEAD"], cwd=repo_path)
        if head["ok"]:
            response["commit"] = head["output"]
            response["short_commit"] = head["output"][:8]

        return response

    def merge_branches(
        self,
        from_branch: str,
        to_branch: Optional[str] = None,
        message: Optional[str] = None,
        delete_branch: bool = False,
        no_commit: bool = False,
        squash: bool = False,
        delete_worktree: bool = False,
        commit: Optional[bool] = None,
        keep_conflicts: bool = False,
    ) -> dict:
        """
        Merge a branch into another one, with optional squash / no-commit modes.

        Workflow:
            1. Resolve the target branch: ``to_branch``, the checked out branch,
               or the repository default branch.
            2. Stash local changes so the checkout never fails.
            3. Check out the target branch and merge the source branch.
            4. Restore the stashed changes.

        Merge modes:

        * default: ``git merge --no-ff`` records a merge commit.
        * ``squash=True``: ``git merge --squash`` collapses every source commit
          into a single commit on the target branch.
        * ``no_commit=True``: stop before committing and leave the merge result
          staged, so it can be reviewed and committed later. A regular merge in
          this mode keeps ``MERGE_HEAD`` (the eventual commit has two parents);
          a squash merge does not record any merge information.

        ``squash`` and ``no_commit`` combine: the squashed changes stay staged
        and no commit is created.

        Conflicting merges are aborted (or reset, for a squash merge, which has
        no merge state) and the conflicting paths are reported in
        ``conflicts``. With ``keep_conflicts=True`` the merge is left in
        progress instead, so the conflict resolver can finish it manually or
        with AI; the result then carries ``conflicted=True`` and the pending
        ``conflict_state``. Nothing is pushed.

        Args:
            from_branch: Branch to merge (source).
            to_branch: Branch to merge into (target).
            message: Commit message. Defaults to
                ``"Merge branch '<source>' into '<target>'"`` (or the squash
                equivalent). It is only used when a commit is created.
            delete_branch: Delete the source branch after merging. Its worktree
                is removed first when it has one.
            no_commit: Leave the merge result staged instead of committing it.
            squash: Collapse the source branch commits into a single commit.
            delete_worktree: Remove the source branch worktree after merging,
                keeping the branch. Uncommitted changes in that worktree are
                discarded (the UI warns about them first).
            commit: Compatibility alias for ``no_commit``: ``commit=False``
                merges without committing.
            keep_conflicts: Leave the merge stopped on conflicts instead of
                aborting it, so the user can resolve them and continue.

        Returns:
            Operation result dict with 'from_branch', 'to_branch', 'commit',
            'committed', 'squashed', 'no_commit', 'up_to_date', 'conflicts',
            'conflicted', 'conflict_state', 'branch_deleted',
            'worktree_removed' and 'steps'.

        Example:
            >>> engine.merge_branches("codx-junior/fix-login", "main")
            {'success': True, 'from_branch': 'codx-junior/fix-login', ...}
            >>> engine.merge_branches("codx-junior/fix-login", "main", squash=True)
            {'success': True, 'squashed': True, 'committed': True, ...}
            >>> engine.merge_branches("feature", "main", no_commit=True)
            {'success': True, 'no_commit': True, 'committed': False, ...}
        """
        # `commit=False` is the positive spelling of `no_commit=True`
        if commit is False:
            no_commit = True

        source = self._sanitize_branch_name(from_branch)
        if not source:
            return self._git_operation_error("Source branch is required")

        repo_path = self._get_repo_root()
        if not self._ref_exists(f"refs/heads/{source}"):
            return self._git_operation_error(
                f"Branch '{source}' not found", branch=source
            )

        current_branch = self._sanitize_branch_name(
            self.get_project_current_branch()
        )
        target = self._sanitize_branch_name(to_branch) or (
            current_branch
            if current_branch and current_branch != source
            else self.get_default_branch()
        )
        if not target:
            return self._git_operation_error(
                "Could not determine the target branch to merge into"
            )
        if target == source:
            return self._git_operation_error(
                f"Branch '{source}' cannot be merged into itself",
                from_branch=source,
                to_branch=target,
            )

        result = {
            "success": False,
            "from_branch": source,
            "to_branch": target,
            "original_branch": current_branch,
            "commit": "",
            "committed": False,
            "squashed": bool(squash),
            "no_commit": bool(no_commit),
            "up_to_date": False,
            "conflicts": [],
            "conflicted": False,
            "conflict_state": {},
            "stash_kept": False,
            "branch_deleted": False,
            "worktree_removed": False,
            "worktree_path": "",
            "steps": [],
            "errors": [],
        }

        status = self.get_working_tree_status()
        result["steps"].append(
            {
                "name": "status",
                "ok": status["ok"],
                "output": f"{len(status['files'])} changed file(s)",
            }
        )
        if not status["ok"]:
            result["errors"].append(f"Could not read git status: {status['error']}")
            return result

        local_branch = self._ensure_local_branch(target)
        result["steps"].append({"name": "ensure-target", **local_branch})
        if not local_branch["ok"]:
            result["errors"].append(local_branch["error"])
            return result

        message = message or (
            f"Squash branch '{source}' into '{target}'"
            if squash
            else f"Merge branch '{source}' into '{target}'"
        )
        stashed = False
        # A conflict left in progress keeps the auto-stash: popping it on top
        # of the unresolved merge would fail and could hide local changes.
        keep_stash = False
        try:
            if status["dirty"]:
                stash = self._run_git(
                    [
                        "stash",
                        "push",
                        "-u",
                        "-m",
                        f"codx-junior: auto-stash before merging {source}",
                    ],
                    cwd=repo_path,
                )
                result["steps"].append({"name": "stash", **stash})
                if not stash["ok"]:
                    result["errors"].append(
                        f"Could not stash local changes: {stash['error']}"
                    )
                    return result
                stashed = True

            if current_branch != target:
                checkout = self._run_git(["checkout", target], cwd=repo_path)
                result["steps"].append({"name": "checkout", **checkout})
                if not checkout["ok"]:
                    result["errors"].append(
                        f"Could not checkout '{target}': {checkout['error']}"
                    )
                    return result

            head_before = self._run_git(["rev-parse", "HEAD"], cwd=repo_path)

            # Build the merge command for the selected mode. `--squash` already
            # implies "do not commit": adding `--no-commit` is unnecessary (and
            # rejected by some git versions).
            merge_args: List[str] = ["merge"]
            if squash:
                merge_args.append("--squash")
            else:
                merge_args.append("--no-ff")
                if no_commit:
                    merge_args.append("--no-commit")
                merge_args.extend(["-m", message])
            merge_args.append(source)

            merge = self._run_git(merge_args, cwd=repo_path)
            result["steps"].append({"name": "merge", **merge})
            if not merge["ok"]:
                conflicts = self._run_git(
                    ["diff", "--name-only", "--diff-filter=U"], cwd=repo_path
                )
                result["conflicts"] = [
                    f.strip() for f in conflicts["output"].split("\n") if f.strip()
                ]
                result["errors"].append(
                    f"Could not merge '{source}' into '{target}': "
                    f"{merge['error'] or merge['output']}"
                )
                if keep_conflicts and result["conflicts"]:
                    # Leave MERGE_HEAD / SQUASH_MSG in place: the conflict
                    # resolver stages the resolutions and continues (or aborts)
                    # the merge. The auto-stash stays untouched for the same
                    # reason and is reported so the user can restore it later.
                    result["conflicted"] = True
                    keep_stash = stashed
                    result["stash_kept"] = stashed
                    get_conflicts = getattr(self, "get_conflicts", None)
                    if callable(get_conflicts):
                        result["conflict_state"] = get_conflicts(
                            include_content=False
                        )
                    return result

                # A squash merge never writes MERGE_HEAD, so `merge --abort`
                # cannot clean it up: reset the index/worktree instead.
                if self._ref_exists("MERGE_HEAD", cwd=repo_path):
                    self._run_git(["merge", "--abort"], cwd=repo_path)
                else:
                    self._run_git(["reset", "--merge", "HEAD"], cwd=repo_path)
                return result

            staged = self._run_git(
                ["diff", "--cached", "--name-only"], cwd=repo_path
            )
            has_staged_changes = bool(staged["ok"] and staged["output"].strip())

            # A squash merge stages the changes but never commits them: create
            # the single squashed commit unless the caller asked for no commit.
            if squash and not no_commit and has_staged_changes:
                squashed_commit = self._run_git(
                    ["commit", "-m", message], cwd=repo_path
                )
                result["steps"].append({"name": "commit", **squashed_commit})
                if not squashed_commit["ok"]:
                    result["errors"].append(
                        "Could not commit the squashed changes: "
                        f"{squashed_commit['error'] or squashed_commit['output']}"
                    )
                    return result

            head_after = self._run_git(["rev-parse", "HEAD"], cwd=repo_path)
            if head_after["ok"]:
                result["committed"] = bool(
                    head_before["ok"]
                    and head_before["output"] != head_after["output"]
                )
            if result["committed"]:
                result["commit"] = head_after["output"]
            # No commit and nothing staged means the source was already merged
            result["up_to_date"] = (
                not result["committed"] and not has_staged_changes
            )

            # Removing the worktree is also required before deleting the branch:
            # git refuses to delete a branch checked out in a worktree.
            if delete_worktree or delete_branch:
                worktree = self._remove_worktree(source, cwd=repo_path)
                result["steps"].append({"name": "worktree-remove", **worktree})
                result["worktree_removed"] = worktree["removed"]
                result["worktree_path"] = worktree.get("path", "")
                if not worktree["ok"]:
                    result["errors"].append(
                        f"Could not remove worktree '{worktree['path']}': "
                        f"{worktree['error']}"
                    )
                    return result

            if delete_branch:
                deleted = self._delete_branch(source, cwd=repo_path)
                result["steps"].append({"name": "branch-delete", **deleted})
                result["branch_deleted"] = deleted["deleted"]
                if not deleted["ok"]:
                    result["errors"].append(
                        f"Could not delete branch '{source}': {deleted['error']}"
                    )

            return result
        finally:
            if stashed and not keep_stash:
                pop = self._run_git(["stash", "pop"], cwd=repo_path)
                result["steps"].append({"name": "stash-pop", **pop})
                if not pop["ok"]:
                    result["errors"].append(
                        "Could not restore stashed local changes. "
                        "Run 'git stash pop' manually."
                    )
            elif keep_stash:
                result["steps"].append(
                    {
                        "name": "stash-kept",
                        "ok": True,
                        "output": "local changes kept in the stash until the "
                        "merge is continued or aborted",
                    }
                )
            result["success"] = not result["errors"]

    def reset_project_file(self, file_path: str) -> None:
        """Reset file's last change."""
        # Determine the correct Git root path for this file
        git_root_path = self._get_git_root_for_file(file_path)

        cmd = f"git reset {file_path}"
        exec_command(cmd, cwd=git_root_path)
        logger.info("Reset file: %s", file_path)

    def get_file_content_from_branch(self, file_path: str, branch: str) -> str:
        """
        Get file content from a specific branch without checking it out.
        
        Args:
            file_path: Relative path to the file in the repository.
            branch: Branch name to fetch content from.
            
        Returns:
            File content as string. Empty string if file doesn't exist in branch.
            
        Raises:
            Exception: If git command fails.
        """
        branch = self._sanitize_branch_name(branch)
        git_root_path = self._get_git_root_for_file(file_path)
        
        # Normalize file path to be relative to git root
        if file_path.startswith(git_root_path):
            git_file_path = file_path[len(git_root_path):].lstrip('/')
        else:
            git_file_path = file_path
        
        cmd = f'git show "{branch}:{git_file_path}"'
        
        stdout, stderr = exec_command(cmd, cwd=git_root_path)
        
        # Check for errors in both stdout and stderr
        error_indicators = ["fatal", "does not exist", "exists on disk, but not in"]
        combined_output = f"{stdout} {stderr}".lower()
        
        if any(indicator in combined_output for indicator in error_indicators):
            logger.warning(f"File {file_path} not found in branch {branch}")
            return ""
        
        return stdout

    def get_file_version_at_depth(self, file_path: str, depth: int = 0) -> dict:
        """
        Retrieve a previous version of a file from git history.

        Navigate through file history by depth level without needing commit IDs.
        Depth represents how many commits back to look:
        - depth=0: Get the immediate previous version (1 commit back)
        - depth=1: Get version from 2 commits ago
        - depth=2: Get version from 3 commits ago
        - etc.

        Args:
            file_path: Relative or absolute path to the file.
            depth: How many commits back to go (0 = previous version, 1 = two commits back, etc).
                   Default is 0 (immediate previous version).

        Returns:
            Dict containing:
                - "content": File content at that version (empty string if not found)
                - "commit": Full commit hash
                - "short_commit": Short commit hash (8 chars)
                - "author": Author name
                - "email": Author email
                - "date": Commit date (ISO format)
                - "message": Commit message
                - "depth": The depth requested
                - "error": Error message if any (None if successful)

        Raises:
            ValueError: If file_path is empty or depth is negative.
        """
        if not file_path:
            raise ValueError("file_path cannot be empty")
        if depth < 0:
            raise ValueError("depth cannot be negative")

        # Resolve git root and file path
        git_root = self._get_git_root_for_file(file_path)
        if not os.path.isabs(file_path):
            abs_file_path = os.path.join(self.settings.abs_project_path, file_path)
        else:
            abs_file_path = file_path

        # Normalize file path relative to git root
        if abs_file_path.startswith(git_root):
            git_file_path = os.path.relpath(abs_file_path, git_root)
        else:
            git_file_path = file_path

        try:
            # Get commit list for this file
            pretty = "%H|%an|%ae|%ad|%s"
            cmd = f"git log --pretty=format:{pretty} --date=iso -- {git_file_path}"
            stdout, stderr = exec_command(cmd, cwd=git_root)

            if stderr and "fatal" in stderr.lower():
                logger.warning("Failed to get git log for %s: %s", file_path, stderr)
                return {
                    "content": "",
                    "commit": "",
                    "short_commit": "",
                    "author": "",
                    "email": "",
                    "date": "",
                    "message": "",
                    "depth": depth,
                    "error": f"Failed to retrieve git history: {stderr}",
                }

            commits = []
            for line in stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    commit_hash, author, email, date, message = line.split("|", 4)
                    commits.append({
                        "commit": commit_hash,
                        "short_commit": commit_hash[:8],
                        "author": author,
                        "email": email,
                        "date": date.strip(),
                        "message": message.strip(),
                    })
                except ValueError:
                    logger.warning("Could not parse commit line: %s", line)
                    continue

            # Check if depth is valid
            if depth >= len(commits):
                logger.warning(
                    "Depth %d exceeds available commits (%d) for file %s",
                    depth,
                    len(commits),
                    file_path
                )
                return {
                    "content": "",
                    "commit": "",
                    "short_commit": "",
                    "author": "",
                    "email": "",
                    "date": "",
                    "message": "",
                    "depth": depth,
                    "error": f"Depth {depth} exceeds available commits ({len(commits)})",
                }

            # Get the commit at the requested depth
            target_commit = commits[depth]

            # Get file content at that commit
            cmd = f'git show "{target_commit["commit"]}:{git_file_path}"'
            file_content, stderr = exec_command(cmd, cwd=git_root)

            # Check for errors
            if stderr and ("fatal" in stderr.lower() or "does not exist" in stderr.lower()):
                logger.warning(
                    "File %s does not exist at commit %s: %s",
                    file_path,
                    target_commit["short_commit"],
                    stderr
                )
                return {
                    "content": "",
                    "commit": target_commit["commit"],
                    "short_commit": target_commit["short_commit"],
                    "author": target_commit["author"],
                    "email": target_commit["email"],
                    "date": target_commit["date"],
                    "message": target_commit["message"],
                    "depth": depth,
                    "error": f"File did not exist at this commit",
                }

            logger.info(
                "Retrieved file version at depth %d: %s (%s)",
                depth,
                file_path,
                target_commit["short_commit"]
            )

            return {
                "content": file_content,
                "commit": target_commit["commit"],
                "short_commit": target_commit["short_commit"],
                "author": target_commit["author"],
                "email": target_commit["email"],
                "date": target_commit["date"],
                "message": target_commit["message"],
                "depth": depth,
                "error": None,
            }

        except Exception as e:
            error_msg = f"Error retrieving file version: {str(e)}"
            logger.error(error_msg)
            return {
                "content": "",
                "commit": "",
                "short_commit": "",
                "author": "",
                "email": "",
                "date": "",
                "message": "",
                "depth": depth,
                "error": error_msg,
            }

# Made with ❤️ by codx-junior