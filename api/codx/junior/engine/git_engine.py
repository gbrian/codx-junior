"""
Git sub-engine for codx-junior.
Handles all git/branch/PR operations.

Made with ❤️ by codx-junior
"""

import json
import logging
import os
import re
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


class GitEngine:
    """
    Handles git repository operations including branches, diffs and PRs.

    ```mermaid
    flowchart TD
        GE[GitEngine]
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
        GE --> build_branch_name
        GE --> create_pr_branch
        GE --> close_pr_branch
        GE --> abandon_pr_branch
        GE --> get_worktrees_path
        GE --> get_repo_info
        GE --> get_repo_status
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

    def _get_repo_root(self) -> str:
        """
        Return the git root path for the project, falling back to the project path.

        Returns:
            Absolute path of the repository root.
        """
        return self.find_git_root_path() or self.settings.abs_project_path

    def _run_git(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        strip_output: bool = True,
    ) -> dict:
        """
        Run a git command without a shell and return a structured result.

        Uses ``subprocess.run`` with an argument list so branch names and file
        paths never need shell quoting, and stdout/stderr stay separated (unlike
        ``exec_command``, which merges stderr into stdout).

        Args:
            args: Git arguments, e.g. ``["checkout", "-b", "feature/x"]``.
            cwd: Working directory. Defaults to the repository root.
            strip_output: Strip leading/trailing whitespace from stdout. Set it
                to False for commands whose leading spaces carry meaning, such
                as ``git status --porcelain``.

        Returns:
            Dict with 'ok', 'command', 'output', 'error' and 'returncode'.
        """
        cwd = cwd or self._get_repo_root()
        command = ["git"] + list(args)
        command_str = " ".join(command)
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

        Args:
            command_result: Dict returned by ``_run_git``.
            extra: Additional fields merged into the result.

        Returns:
            Dict with 'success', 'command', 'output' and 'errors'.
        """
        ok = bool(command_result.get("ok"))
        error = command_result.get("error") or ""
        return {
            "success": ok,
            "command": command_result.get("command", ""),
            "output": command_result.get("output", ""),
            "errors": [] if ok else [error or "git command failed"],
            **extra,
        }

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

    def _get_file_last_modification(self, file_path: str) -> Optional[str]:
        """
        Return the last modification datetime of a file as an ISO 8601 string.
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.settings.abs_project_path, file_path)
        if not os.path.isfile(file_path):
            return None
        mtime = os.path.getmtime(file_path)
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
        Return all git branches (local and remote) for the project.
        Sanitizes branch names by removing prefixes.
        """
        def get_branches(cmd: str) -> list:
            stdout, _ = exec_command(cmd, cwd=self.settings.abs_project_path)
            branches = [s.strip() for s in stdout.split("\n") if s.strip()]
            return [self._sanitize_branch_name(b) for b in branches]

        branches = list(set(get_branches("git branch") + get_branches("git branch -r")))
        branches.sort()
        return branches

    def get_project_branches(self) -> dict:
        """
        Return branches and full repo tree.
        """
        return {
            "branches": self.get_repo_branches(),
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

    def find_git_root_path(self) -> str:
        """
        Find the root path of the git repository by checking parents.
        """
        if self.settings.is_git_root:
            return self.settings.abs_project_path
        for parent in find_project_parents(project=self.settings):
            if parent.is_git_root:
                return parent.abs_project_path
        return ""

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
        Each file entry includes a 'last_modification' datetime (ISO 8601).
        """
        # Sanitize branch names
        from_branch = self._sanitize_branch_name(from_branch)
        to_branch = self._sanitize_branch_name(to_branch)
        
        is_current_branch = from_branch != to_branch  # Simplified check after sanitization

        # Get list of changed files
        git_branch_file_changed = f"git diff --name-only {to_branch}...{from_branch}"
        branch_files_output, _ = exec_command(
            git_branch_file_changed, cwd=self.settings.abs_project_path
        )
        branch_files = [f.strip() for f in branch_files_output.strip().split("\n") if f.strip()]

        def get_git_file_diff(file_path: str) -> str:
            """Get diff for a specific file between branches."""
            cmd = f"git diff {to_branch}...{from_branch} -- {file_path}"
            git_cmd_out, _ = exec_command(cmd, cwd=self.settings.abs_project_path)
            return git_cmd_out.strip()

        def get_git_file_commits(file_path: str) -> list:
            """Get commits that touched a specific file between branches."""
            pretty = '{ "commit": "%H", "author": "%an", "date": "%as", "message": "%f" }'
            cmd = f"git log --pretty=format:'{pretty}' {to_branch}..{from_branch} -- {file_path}"
            git_cmd_out, _ = exec_command(cmd, cwd=self.settings.abs_project_path)
            
            results = []
            for line in git_cmd_out.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    results.append(json.loads(line))
                except Exception as ex:
                    logger.warning("Could not parse commit line for %s: %s", file_path, ex)
            return results

        # Build per-file metadata
        branch_file_and_commits = {}
        for file_path in branch_files:
            if not file_path:
                continue
            
            branch_file_and_commits[file_path] = {
                "commits": get_git_file_commits(file_path),
                "diff": get_git_file_diff(file_path),
                "last_modification": self._get_file_last_modification(file_path),
            }

        # Get overall diff stats
        git_diff_cmd = (
            f"git diff {to_branch} {from_branch}"
            if from_branch != "local"
            else f"git diff {to_branch}"
        )

        git_diff_cmd_out, _ = exec_command(
            git_diff_cmd, cwd=self.settings.abs_project_path
        )
        git_diff_cmd_stat_out, _ = exec_command(
            git_diff_cmd.replace("git diff", "git diff --shortstat"),
            cwd=self.settings.abs_project_path,
        )

        # Handle local changes if comparing against current branch
        local_changes: dict = {}
        if is_current_branch:
            git_local, _ = exec_command(
                "git status -s", cwd=self.settings.abs_project_path
            )
            local_files = [f.strip().split(" ")[-1] for f in git_local.split("\n") if f.strip()]
            
            for file in local_files:
                full_path = os.path.join(self.settings.abs_project_path, file)
                if os.path.isfile(full_path):
                    git_diff_local_out, _ = exec_command(
                        f"git diff {to_branch} {file}",
                        cwd=self.settings.abs_project_path,
                    )
                    local_changes[file] = {
                        "diff": git_diff_local_out or (
                            f"diff --git a/ b/{file}\nnew file mode"
                        ),
                        "last_modification": self._get_file_last_modification(file),
                    }

            # Merge local changes into branch changes
            for local_file, local_file_info in local_changes.items():
                if local_file in branch_file_and_commits:
                    branch_file_and_commits[local_file]["diff"] = local_file_info["diff"]
                    branch_file_and_commits[local_file]["last_modification"] = (
                        local_file_info["last_modification"]
                    )
                else:
                    branch_file_and_commits[local_file] = local_file_info

        pr_details = self.get_pr_review_details(from_branch, to_branch)

        return {
            "diff": git_diff_cmd_out,
            "stat": git_diff_cmd_stat_out,
            "git_diff_cmd": git_diff_cmd,
            "local_changes": local_changes,
            "repo_path": self.find_git_root_path(),
            "pr_details": pr_details,
            "commits": [],
            "branch_file_and_commits": branch_file_and_commits,
            "compare_type": "branch",
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

        Returns:
            Dict with 'ok', 'dirty', 'files' (porcelain lines) and 'error'.

        Example:
            >>> engine.get_working_tree_status()
            {'ok': True, 'dirty': True, 'files': [' M codx/junior/app.py'], 'error': ''}
        """
        # Leading spaces are part of the porcelain format (index vs worktree)
        result = self._run_git(["status", "--porcelain"], strip_output=False)
        files = [line for line in result["output"].split("\n") if line.strip()]
        return {
            "ok": result["ok"],
            "dirty": bool(files),
            "files": files,
            "error": result["error"],
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

    def list_worktrees(self) -> list:
        """
        Return the repository's registered worktrees.

        Returns:
            List of dicts with 'path' and 'branch' keys.
        """
        result = self._run_git(["worktree", "list", "--porcelain"])
        worktrees = []
        current: Dict[str, str] = {}

        for line in result["output"].split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                current = {"path": line[len("worktree "):].strip()}
            elif line.startswith("branch ") and current is not None:
                branch = line[len("branch "):].strip()
                current["branch"] = self._sanitize_branch_name(
                    branch.replace("refs/heads/", "")
                )

        if current:
            worktrees.append(current)
        return worktrees

    def get_worktree_path_for_branch(self, branch_name: str) -> str:
        """
        Return the worktree path already registered for a branch, if any.

        Args:
            branch_name: Branch name to look for.

        Returns:
            Absolute worktree path, or an empty string when none exists.
        """
        branch_name = self._sanitize_branch_name(branch_name)
        for worktree in self.list_worktrees():
            if worktree.get("branch") == branch_name:
                return worktree.get("path", "")
        return ""

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

        result = self._run_git(["worktree", "remove", "--force", worktree_path], cwd=cwd)
        if not result["ok"]:
            # Stale administrative entries block future worktree operations
            self._run_git(["worktree", "prune"], cwd=cwd)

        return {
            "ok": result["ok"],
            "removed": result["ok"],
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

        Args:
            cwd: Working directory (repository root or worktree path).
            message: Commit message.
            allow_empty: Allow commits without content changes.

        Returns:
            Result dict of the commit command.
        """
        add = self._run_git(["add", "-A"], cwd=cwd)
        if not add["ok"]:
            return add

        args = ["commit", "-m", message]
        if allow_empty:
            args.append("--allow-empty")
        return self._run_git(args, cwd=cwd)

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
    # Repository management (fetch/pull/push, branches, commit, merge)
    # -------------------------------------------------------------------------

    def get_repo_info(self) -> dict:
        """
        Return a summary of the repository state used by the git view header.

        Returns:
            Dict with repo path, project path, active/default branch, remote
            url, ahead/behind counters, working tree state (including the
            staged and unstaged file lists), worktrees and the last commit.

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
            "worktrees": self.list_worktrees(),
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

        Args:
            remote: Remote name.
            branch: Branch to push. Defaults to the checked out branch.
            set_upstream: Set the upstream tracking reference (``-u``).

        Returns:
            Operation result dict.

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

        Args:
            message: Commit message.
            stage_all: Stage every change before committing (``git add -A``).
            allow_empty: Allow commits with no content changes.

        Returns:
            Operation result dict with 'commit' (full hash) and 'short_commit'.

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
            result, message=message, stage_all=stage_all
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
    ) -> dict:
        """
        Merge a branch into another one (PR close workflow).

        Workflow:
            1. Resolve the target branch: ``to_branch``, the checked out branch,
               or the repository default branch.
            2. Stash local changes so the checkout never fails.
            3. Check out the target branch and ``git merge --no-ff <source>``;
               conflicting merges are aborted and the conflicts reported.
            4. Restore the stashed changes.

        Args:
            from_branch: Branch to merge (source).
            to_branch: Branch to merge into (target).
            message: Merge commit message. Defaults to
                ``"Merge branch '<source>' into '<target>'"``.
            delete_branch: Delete the source branch after merging.

        Returns:
            Operation result dict with 'from_branch', 'to_branch', 'commit',
            'conflicts', 'branch_deleted' and 'steps'.

        Example:
            >>> engine.merge_branches("codx-junior/fix-login", "main")
            {'success': True, 'from_branch': 'codx-junior/fix-login', ...}
        """
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
            "conflicts": [],
            "branch_deleted": False,
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

        message = message or f"Merge branch '{source}' into '{target}'"
        stashed = False
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

            merge = self._run_git(
                ["merge", "--no-ff", source, "-m", message], cwd=repo_path
            )
            result["steps"].append({"name": "merge", **merge})
            if not merge["ok"]:
                conflicts = self._run_git(
                    ["diff", "--name-only", "--diff-filter=U"], cwd=repo_path
                )
                result["conflicts"] = [
                    f.strip() for f in conflicts["output"].split("\n") if f.strip()
                ]
                self._run_git(["merge", "--abort"], cwd=repo_path)
                result["errors"].append(
                    f"Could not merge '{source}' into '{target}': "
                    f"{merge['error'] or merge['output']}"
                )
                return result

            head = self._run_git(["rev-parse", "HEAD"], cwd=repo_path)
            if head["ok"]:
                result["commit"] = head["output"]

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
            if stashed:
                pop = self._run_git(["stash", "pop"], cwd=repo_path)
                result["steps"].append({"name": "stash-pop", **pop})
                if not pop["ok"]:
                    result["errors"].append(
                        "Could not restore stashed local changes. "
                        "Run 'git stash pop' manually."
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