"""
Git sub-engine for codx-junior.
Handles all git/branch/PR operations.

Made with ❤️ by codx-junior
"""

import json
import logging
import os
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
    ```
    """

    def __init__(self, session: "CODXJuniorSession") -> None:
        """Initialize with a reference to the parent session."""
        self.session = session

    @property
    def settings(self):
        """Shortcut to session settings."""
        return self.session.settings

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

    def get_repo_branches(self) -> list:
        """
        Return all git branches (local and remote) for the project.
        """
        def get_branches(cmd: str) -> list:
            stdout, _ = exec_command(cmd, cwd=self.settings.abs_project_path)
            return [s.strip() for s in stdout.split("\n") if s.strip()]

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
        is_current_branch = from_branch.startswith("* ")
        if from_branch and is_current_branch:
            from_branch = from_branch[2:]
        if to_branch.startswith("* "):
            to_branch = to_branch[2:]

        git_branch_file_changed = f"git diff --name-only {to_branch}...{from_branch}"
        branch_files, _ = exec_command(
            git_branch_file_changed, cwd=self.settings.abs_project_path
        )
        branch_files = branch_files.strip().split("\n")

        def get_git_file_diff(file_path: str) -> str:
            cmd = f"git diff {to_branch}...{from_branch} -- {file_path}"
            git_cmd_out, _ = exec_command(cmd, cwd=self.settings.abs_project_path)
            logger.info(
                "get_git_file_diff: %s: %s\n%s\n%s",
                file_path,
                git_cmd_out,
                self.settings.abs_project_path,
                cmd,
            )
            return git_cmd_out.strip()

        def get_git_file_commits(file_path: str) -> list:
            pretty = '{ "commit": "%H", "author": "%an", "date": "%as", "message": "%f" }'
            cmd = f"git log --pretty=format:'{pretty}' {from_branch} -- {file_path}"
            git_cmd_out, _ = exec_command(cmd, cwd=self.settings.abs_project_path)
            return [json.loads(line) for line in git_cmd_out.strip().split("\n")]

        git_commits = []
        try:
            git_commits = get_git_file_commits(branch_files[-1] if branch_files else "")
        except Exception as ex:
            logger.error("Error reading branch commits: %s", ex)

        branch_file_and_commits = {
            file_path: {
                "commits": git_commits,
                "diff": get_git_file_diff(file_path),
                "last_modification": self._get_file_last_modification(file_path),
            }
            for file_path in branch_files
        }

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

        local_changes: dict = {}

        if is_current_branch:
            git_local, _ = exec_command(
                "git status -s", cwd=self.settings.abs_project_path
            )
            local_files = [f.strip().split(" ")[-1] for f in git_local.split("\n")]
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
        stdout, _ = exec_command("git branch --show-current")
        return stdout

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
            return ref_branch

        ref_branch = creation_line.split(" (")[1].split(",")[0]
        return ref_branch

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
        cmd = f"git reset {file_path}"
        exec_command(cmd, cwd=self.settings.abs_project_path)
        logger.info("Reset file: %s", file_path)