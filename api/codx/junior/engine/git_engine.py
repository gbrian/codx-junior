"""
Git sub-engine for codx-junior.
Handles all git/branch/PR operations.

Made with ❤️ by codx-junior
"""

import json
import logging
import os
import subprocess

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from codx.junior.project.project_discover import find_project_parents
from codx.junior.utils.utils import exec_command

if TYPE_CHECKING:
    from codx.junior.engine.session import CODXJuniorSession

logger = logging.getLogger(__name__)


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
        path = self._get_git_root_for_file(file_path
        =path)

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
        stdout, _ = exec_command("git branch --show-current", cwd=self.settings.abs_project_path)
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