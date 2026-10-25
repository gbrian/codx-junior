"""
Working tree (file level) git operations for codx-junior.

Extends :class:`codx.junior.engine.git_engine.GitEngine` with the operations the
repository view needs on individual files:

- stage / unstage file lists
- discard (rollback) file changes, removing untracked and new files
- single file diffs (worktree, index or a given commit)
- single file commit history

```mermaid
flowchart TD
    GWE[GitWorkspaceEngine]
    GWE --> stage_files
    GWE --> unstage_files
    GWE --> discard_files
    GWE --> get_file_diff
    GWE --> get_file_history
    GWE --> _to_repo_path
    GWE --> _clean_paths
    GWE --> _status_codes
    GWE --> _is_untracked
    GWE --> _count_diff_lines
    GWE --> _split_patch
```

Made with ❤️ by codx-junior
"""

import logging
import os
import re

from typing import Dict, List, Optional, Tuple

from codx.junior.engine.git_engine import GitEngine

logger = logging.getLogger(__name__)

# First line of a unified patch: anything before it is command metadata
PATCH_START_PATTERN = re.compile(r"^(diff --git |--- )", re.MULTILINE)


class GitWorkspaceEngine(GitEngine):
    """
    File level working tree operations on top of :class:`GitEngine`.

    Every method accepts paths relative to the repository root or absolute
    paths, so callers can forward whatever the UI already has (file names from
    the status list, absolute project paths...).
    """

    def _to_repo_path(self, path: Optional[str]) -> str:
        """
        Normalize a file path so it is relative to the repository root.

        Args:
            path: Absolute path, project-relative path or repo-relative path.

        Returns:
            Repo-relative path with forward slashes, or an empty string when no
            usable path was given.

        Example:
            >>> engine._to_repo_path("/repo/app/main.py")
            'app/main.py'
        """
        if not path:
            return ""

        value = str(path).strip()
        if not value:
            return ""

        value = value.replace("\\", "/")
        if os.path.isabs(value):
            repo_root = os.path.normpath(self._get_repo_root())
            try:
                value = os.path.relpath(os.path.normpath(value), repo_root)
            except ValueError:
                # Different drive (windows): keep the original value
                return ""
            value = value.replace("\\", "/")

        while value.startswith("./"):
            value = value[2:]

        return value

    def _clean_paths(self, paths) -> List[str]:
        """
        Normalize and de-duplicate a path list.

        Args:
            paths: Single path or list of paths.

        Returns:
            Unique repo-relative paths, preserving the given order.

        Example:
            >>> engine._clean_paths(["./app.py", "app.py", ""])
            ['app.py']
        """
        if isinstance(paths, str):
            paths = [paths]

        cleaned: List[str] = []
        for path in paths or []:
            value = self._to_repo_path(path)
            if value and value not in cleaned:
                cleaned.append(value)
        return cleaned

    def _status_codes(self) -> Dict[str, Tuple[str, str]]:
        """
        Map every working tree path to its porcelain (index, worktree) codes.

        Returns:
            Dict of ``path -> (index_code, worktree_code)``.

        Example:
            >>> engine._status_codes().get("app.py")
            (' ', 'M')
        """
        codes: Dict[str, Tuple[str, str]] = {}
        for line in self.get_working_tree_status()["files"]:
            parsed = self._parse_status_line(line)
            if not parsed:
                continue
            index_code, worktree_code, path = parsed
            codes[path] = (index_code, worktree_code)
        return codes

    def _is_untracked(self, path: str) -> bool:
        """
        Return whether a file is unknown to git.

        Args:
            path: Repo-relative file path.

        Returns:
            True when the file has no entry in the index.
        """
        result = self._run_git(["ls-files", "--error-unmatch", "--", path])
        return not result["ok"]

    def _count_diff_lines(self, diff: str) -> dict:
        """
        Count the added and removed lines of a unified diff.

        Args:
            diff: Unified diff text.

        Returns:
            Dict with 'additions' and 'deletions'.

        Example:
            >>> engine._count_diff_lines("+added\n-removed\n")
            {'additions': 1, 'deletions': 1}
        """
        additions = 0
        deletions = 0
        for line in (diff or "").split("\n"):
            # File headers (---/+++) are not content changes
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                additions += 1
            elif line.startswith("-"):
                deletions += 1
        return {"additions": additions, "deletions": deletions}

    def _split_patch(self, diff: str) -> Tuple[str, str]:
        """
        Split command output into its metadata header and the unified patch.

        ``git show`` prints the commit metadata (hash, author, date, message)
        before the patch, and diff renderers expect the patch to start at
        ``diff --git``/``---``. Separating both keeps the renderer from drawing
        the metadata as diff content.

        Args:
            diff: Raw output of a diff/show command.

        Returns:
            Tuple of ``(header, patch)``.

        Example:
            >>> engine._split_patch("commit abc\\n\\ndiff --git a/x b/x")
            ('commit abc', 'diff --git a/x b/x')
        """
        text = diff or ""
        match = PATCH_START_PATTERN.search(text)
        if not match:
            # No patch at all: everything is header (e.g. an empty result)
            return text.strip(), ""

        index = match.start()
        return text[:index].strip(), text[index:]

    def stage_files(self, paths) -> dict:
        """
        Stage files, including deletions and untracked files.

        Each path is staged on its own: when one of them cannot be staged
        (removed from disk, unknown pathspec...) the remaining ones are still
        staged and the failure is returned in 'errors'.

        Args:
            paths: Single path or list of paths.

        Returns:
            Operation result dict with 'action', 'paths' (requested),
            'staged' (paths staged successfully), 'errors' (one message per
            failed path) and 'locked'/'lock_path' (set when the repository is
            locked by a stale ``.git/index.lock``).

        Example:
            >>> engine.stage_files(["app.py", "config/settings.json"])["success"]
            True
            >>> engine.stage_files(["gone.json"])["errors"]
            ["gone.json: pathspec 'gone.json' did not match any files"]
        """
        cleaned = self._clean_paths(paths)
        if not cleaned:
            return self._git_operation_error("No file paths provided")

        staging = self.stage_changes(files=cleaned)
        return {
            "success": staging["ok"],
            "action": "stage",
            "paths": cleaned,
            "staged": staging["staged"],
            "command": "",
            "output": staging["output"],
            "errors": staging["errors"],
            "locked": staging.get("locked", False),
            "lock_path": staging.get("lock_path", ""),
        }

    def unstage_files(self, paths) -> dict:
        """
        Remove files from the index, keeping their worktree changes.

        Args:
            paths: Single path or list of paths.

        Returns:
            Operation result dict with 'action' and 'paths'.

        Note:
            A repository without commits has no HEAD to restore the index from,
            so the entries are dropped from the index instead.
        """
        cleaned = self._clean_paths(paths)
        if not cleaned:
            return self._git_operation_error("No file paths provided")

        result = self._run_git(["restore", "--staged", "--"] + cleaned)
        if not result["ok"]:
            fallback = self._run_git(
                ["rm", "--cached", "-r", "-q", "--force", "--"] + cleaned
            )
            if not fallback["ok"]:
                return self._git_operation_error(
                    result["error"] or fallback["error"] or "Could not unstage files",
                    action="unstage",
                    paths=cleaned,
                )
            result = fallback

        return self._git_operation_result(result, action="unstage", paths=cleaned)

    def discard_files(self, paths, include_staged: bool = True) -> dict:
        """
        Roll files back to their last committed state.

        Tracked files are restored from HEAD; untracked and newly added files
        are removed from the working tree. When *include_staged* is True the
        index entries are dropped too, so the files come back completely clean.

        Args:
            paths: Single path or list of paths.
            include_staged: Unstage the files before restoring them.

        Returns:
            Dict with 'success', 'action', 'paths', 'discarded', 'steps' and
            'errors'.

        Example:
            >>> engine.discard_files(["app.py", "new.json"])["success"]
            True
        """
        cleaned = self._clean_paths(paths)
        if not cleaned:
            return self._git_operation_error("No file paths provided")

        repo_root = self._get_repo_root()
        codes = self._status_codes()

        tracked: List[str] = []
        added: List[str] = []
        untracked: List[str] = []

        for path in cleaned:
            index_code, worktree_code = codes.get(path, (" ", " "))
            if index_code == "?" and worktree_code == "?":
                untracked.append(path)
            elif index_code == "A":
                # Staged new file: not part of HEAD, it must be deleted
                added.append(path)
            else:
                tracked.append(path)

        steps: List[dict] = []
        errors: List[str] = []

        if include_staged and (tracked or added):
            unstage = self.unstage_files(tracked + added)
            steps.append({
                "name": "unstage",
                "ok": unstage["success"],
                "output": unstage.get("output", ""),
            })
            if not unstage["success"]:
                errors += unstage.get("errors") or []

        removable = untracked + added
        if removable:
            clean = self._run_git(["clean", "-f", "-d", "--"] + removable, cwd=repo_root)
            steps.append({
                "name": "clean",
                "ok": clean["ok"],
                "output": clean["output"],
            })
            if not clean["ok"]:
                errors.append(clean["error"] or "Could not remove untracked files")

        if tracked:
            restore = self._run_git(
                ["restore", "--worktree", "--source=HEAD", "--"] + tracked,
                cwd=repo_root,
            )
            if not restore["ok"]:
                # Older git versions: plain checkout restores the worktree too
                restore = self._run_git(["checkout", "--"] + tracked, cwd=repo_root)
            steps.append({
                "name": "restore",
                "ok": restore["ok"],
                "output": restore["output"],
            })
            if not restore["ok"]:
                errors.append(restore["error"] or "Could not restore files")

        return {
            "success": not errors,
            "action": "discard",
            "paths": cleaned,
            "discarded": tracked + removable,
            "command": "",
            "output": "",
            "steps": steps,
            "errors": errors,
        }

    def get_file_diff(
        self,
        path: str,
        staged: bool = False,
        commit: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> dict:
        """
        Return the diff of a single file.

        Sources, in precedence order:
            1. ``commit`` (or ``mode="commit"``): the commit's changes for the
               file (``git show``), metadata returned in 'header'.
            2. ``staged`` (or ``mode="staged"``): index against HEAD
               (``git diff --cached``).
            3. working tree against the index (``git diff``).

        Untracked files have no git diff, so a synthetic "new file" diff is
        generated from their content. A file with nothing to show is **not** an
        error: the result carries an empty 'diff' and the UI renders its empty
        state.

        Args:
            path: File path (absolute or repo-relative).
            staged: Diff the staged (index) changes instead of the worktree.
            commit: Commit hash to diff instead of the worktree.
            mode: Explicit source ('worktree', 'staged' or 'commit'); overrides
                the ``staged``/``commit`` flags.

        Returns:
            Dict with 'success', 'path', 'file_name', 'language', 'mode',
            'commit', 'header', 'diff', 'additions', 'deletions' and 'error'.

        Example:
            >>> engine.get_file_diff("app.py")["mode"]
            'unstaged'
            >>> engine.get_file_diff("app.py", mode="staged")["diff"][:11]
            'diff --git '
        """
        rel_path = self._to_repo_path(path)
        if not rel_path:
            return {
                "success": False,
                "path": "",
                "file_name": "",
                "language": "",
                "mode": "",
                "commit": "",
                "header": "",
                "diff": "",
                "additions": 0,
                "deletions": 0,
                "error": "path is required",
            }

        mode = mode or ("commit" if commit else "staged" if staged else "unstaged")
        repo_root = self._get_repo_root()

        if mode == "commit":
            if not commit:
                return {
                    "success": False,
                    "path": rel_path,
                    "file_name": os.path.basename(rel_path),
                    "language": "",
                    "mode": mode,
                    "commit": "",
                    "header": "",
                    "diff": "",
                    "additions": 0,
                    "deletions": 0,
                    "error": "commit is required for the commit mode",
                }
            args = ["show", "--no-color", "--format=medium", commit, "--", rel_path]
        elif mode == "staged":
            args = ["diff", "--cached", "--no-color", "--", rel_path]
        else:
            mode = "unstaged"
            args = ["diff", "--no-color", "--", rel_path]

        result = self._run_git(args, cwd=repo_root)
        diff = result["output"]

        if mode == "commit" and not result["ok"] and not diff.strip():
            return {
                "success": False,
                "path": rel_path,
                "file_name": os.path.basename(rel_path),
                "language": "",
                "mode": mode,
                "commit": commit or "",
                "header": "",
                "diff": "",
                "additions": 0,
                "deletions": 0,
                "error": result["error"] or "Could not read the commit diff",
            }

        if mode == "unstaged" and not diff.strip() and self._is_untracked(rel_path):
            # Untracked file: diff it against /dev/null (exit code 1 is expected)
            synthetic = self._run_git(
                ["diff", "--no-color", "--no-index", "--", os.devnull, rel_path],
                cwd=repo_root,
            )
            diff = synthetic["output"]

        header, patch = self._split_patch(diff)
        counts = self._count_diff_lines(patch)

        return {
            "success": True,
            "path": rel_path,
            "file_name": os.path.basename(rel_path),
            "language": os.path.splitext(rel_path)[1].lstrip("."),
            "mode": mode,
            "commit": commit or "",
            "header": header,
            "diff": patch,
            "additions": counts["additions"],
            "deletions": counts["deletions"],
            "error": "",
        }

    def get_file_history(self, path: str, limit: int = 25) -> list:
        """
        Return the commit history of a single file.

        Args:
            path: File path (absolute or repo-relative).
            limit: Maximum number of commits returned.

        Returns:
            List of commit dicts with 'commit', 'short_commit', 'author',
            'email', 'date' and 'message'.

        Example:
            >>> engine.get_file_history("app.py", limit=5)[0]["short_commit"]
            'a1b2c3d4'
        """
        rel_path = self._to_repo_path(path)
        if not rel_path:
            return []

        pretty = "%H|%an|%ae|%ad|%s"
        result = self._run_git([
            "log",
            f"--pretty=format:{pretty}",
            "--date=iso",
            "-n", str(max(1, int(limit or 25))),
            "--follow",
            "--", rel_path,
        ])
        if not result["ok"]:
            logger.warning("Could not read history for %s: %s", rel_path, result["error"])
            return []

        commits = []
        for line in result["output"].split("\n"):
            if not line.strip():
                continue
            try:
                commit_hash, author, email, date, message = line.split("|", 4)
            except ValueError:
                logger.warning("Could not parse file commit line: %s", line)
                continue
            commits.append({
                "commit": commit_hash,
                "short_commit": commit_hash[:8],
                "author": author,
                "email": email,
                "date": date.strip(),
                "message": message.strip(),
            })
        return commits

# Made with ❤️ by codx-junior