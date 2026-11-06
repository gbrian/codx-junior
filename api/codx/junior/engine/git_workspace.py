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

# Untracked files are reviewed from their content. Binary and very large files
# are skipped: they cannot be meaningfully reviewed and would flood the prompt.
MAX_UNTRACKED_FILE_BYTES = 512 * 1024

# Total patch budget for the synthetic untracked diffs of one review.
MAX_UNTRACKED_PATCH_CHARS = 2_000_000


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

    def _local_file_patch(self, path: str, base_ref: str) -> str:
        """
        Return the patch of one working tree file against *base_ref*.

        Tracked files are diffed with ``git diff <base_ref> -- <path>``: the
        comparison includes both the index and the working tree, so a file with
        staged changes only (or staged plus unstaged changes) is reported with
        its complete change set. Untracked files have no git diff against a
        ref, so they get the synthetic "new file" patch built by
        :meth:`get_file_diff`.

        Args:
            path: Repo-relative file path.
            base_ref: Ref the working tree is compared against.

        Returns:
            Unified patch (empty when the file has nothing to show).
        """
        if self._is_untracked(path):
            diff = self.get_file_diff(path=path, mode="worktree")
            return (diff.get("diff") or "").strip()

        result = self._run_git(
            ["diff", "--no-color", base_ref, "--", path], cwd=self._get_repo_root()
        )
        return (result["output"] or "").strip()

    def _untracked_patch(self, path: str) -> str:
        """
        Build a synthetic "new file" patch for an untracked file.

        Binary and oversized files return an empty patch: they still appear in
        the file list (the UI shows their status) but are not sent to the AI.
        Reading the file directly avoids spawning one git process per untracked
        file, which is what made reviewing a working tree with a generated
        folder (browser profiles, caches...) extremely slow.

        Args:
            path: Repo-relative path.

        Returns:
            Unified patch, or an empty string when the file cannot be reviewed.
        """
        repo_root = self._get_repo_root()
        absolute = os.path.join(repo_root, path)
        try:
            size = os.path.getsize(absolute)
            if size > MAX_UNTRACKED_FILE_BYTES:
                logger.info(
                    "Skipping untracked file %s in the local review: %s bytes",
                    path,
                    size,
                )
                return ""
            with open(absolute, "rb") as handle:
                raw = handle.read()
        except (OSError, IOError):
            return ""

        # NUL bytes mean binary content: a text diff would be meaningless
        if b"\0" in raw[:8000]:
            return ""

        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        hunk_size = len(lines)
        patch_lines = [
            f"diff --git a/{path} b/{path}",
            "new file mode 100644",
            "index 0000000..0000000",
            "--- /dev/null",
            f"+++ b/{path}",
            f"@@ -0,0 +1,{max(hunk_size, 0)} @@",
        ]
        patch_lines.extend(f"+{line}" for line in lines)
        if text and not text.endswith("\n"):
            patch_lines.append("\\ No newline at end of file")
        return "\n".join(patch_lines)

    def get_local_changes(
        self, base_ref: Optional[str] = None, paths: Optional[List[str]] = None
    ) -> dict:
        """
        Return the uncommitted changes of the project compared to a ref.

        This is the "local changes vs current branch" review payload: every
        staged, unstaged and untracked file is listed with its patch against
        *base_ref* (defaults to ``HEAD``, i.e. the checked out branch tip). It
        has the same shape as :meth:`get_repo_changes`, so the PR viewer can
        render it without a special case.

        Args:
            base_ref: Branch/ref the working tree is compared against. Defaults
                to ``HEAD``.
            paths: Optional file paths to restrict the result to.

        Returns:
            Dict with 'diff', 'stat', 'repo_path', 'pr_details', 'commits',
            'branch_file_and_commits', 'local_changes', 'compare_type'
            ('local'), 'base_ref' and 'base_branch'.

        Example:
            >>> result = engine.get_local_changes()
            >>> result["compare_type"]
            'local'
            >>> list(result["branch_file_and_commits"])
            ['app.py', 'new.json']
        """
        repo_root = self._get_repo_root()
        base_ref = (base_ref or "").strip() or "HEAD"
        if not self._ref_exists(base_ref):
            # A deleted/renamed branch must not hide the working tree changes
            logger.warning("Local review base ref %s not found: using HEAD", base_ref)
            base_ref = "HEAD"

        status = self.get_working_tree_status()
        changes = self.get_status_changes(status["files"])

        selected = set(self._clean_paths(paths)) if paths else None
        entries: Dict[str, dict] = {}
        order: List[str] = []

        def add_entry(entry: dict, staged: bool) -> None:
            path = self._to_repo_path(entry.get("path"))
            if not path:
                return
            if selected is not None and path not in selected:
                return
            current = entries.get(path)
            if current is None:
                current = {
                    "path": path,
                    "code": entry.get("code") or "M",
                    "status": entry.get("status") or "modified",
                    "staged": False,
                    "unstaged": False,
                }
                entries[path] = current
                order.append(path)
            if staged:
                current["staged"] = True
            else:
                current["unstaged"] = True

        for entry in changes["staged"]:
            add_entry(entry, staged=True)
        for entry in changes["unstaged"]:
            add_entry(entry, staged=False)

        # One diff for every tracked file, split per-file in memory. Spawning a
        # git process per changed file is what made the local review slow on
        # large working trees.
        tracked = self._run_git(
            ["diff", "--no-color", base_ref], cwd=repo_root
        )
        tracked_diff = tracked["output"] or ""
        tracked_patches = self._split_file_patches(tracked_diff)

        untracked_diffs: List[str] = []
        untracked_patch_chars = 0
        local_changes: Dict[str, dict] = {}
        branch_file_and_commits: Dict[str, dict] = {}
        pr_details: List[dict] = []

        for path in order:
            entry = entries[path]
            if entry["code"] == "?":
                # Untracked files are not part of `git diff`: build their
                # synthetic patch from the file content (bounded).
                remaining = MAX_UNTRACKED_PATCH_CHARS - untracked_patch_chars
                patch = self._untracked_patch(path) if remaining > 0 else ""
                if patch and len(patch) > remaining:
                    patch = patch[:remaining].rstrip() + "\n... (truncated)"
                if patch:
                    untracked_patch_chars += len(patch)
                    untracked_diffs.append(patch)
            else:
                patch = tracked_patches.get(path)
                if patch is None:
                    # Rare (quoted path / rename header): fall back to one diff
                    patch = self._local_file_patch(path, base_ref)

            last_modification = self._get_file_last_modification(path)
            local_changes[path] = {
                "diff": patch,
                "last_modification": last_modification,
                "code": entry["code"],
                "status": entry["status"],
                "staged": entry["staged"],
                "unstaged": entry["unstaged"],
            }
            branch_file_and_commits[path] = {
                "commits": [],
                "diff": patch,
                "last_modification": last_modification,
                "code": entry["code"],
                "status": entry["status"],
                "staged": entry["staged"],
                "unstaged": entry["unstaged"],
            }
            pr_details.append({
                "file_name": path,
                "status": (
                    "new" if entry["code"] in ("?", "A")
                    else "deleted" if entry["code"] == "D"
                    else "renamed" if entry["code"] == "R"
                    else "modified"
                ),
                "diff": patch,
                "commits": [],
                "last_modification": last_modification,
                "code": entry["code"],
            })

        # Whole-change patch: tracked changes against the base plus the
        # untracked files, which `git diff` never includes.
        diff_parts = [tracked_diff] if tracked_diff else []
        diff_parts += untracked_diffs
        combined_diff = "\n".join(part for part in diff_parts if part)

        stat_result = self._run_git(
            ["diff", "--shortstat", base_ref], cwd=repo_root
        )
        stat = stat_result["output"] if stat_result["ok"] else ""
        untracked_count = sum(1 for entry in entries.values() if entry["code"] == "?")
        if untracked_count:
            suffix = f"{untracked_count} untracked file(s)"
            stat = f"{stat}, {suffix}" if stat else suffix

        return {
            "diff": combined_diff,
            "stat": stat,
            "git_diff_cmd": f"git diff {base_ref}",
            "local_changes": local_changes,
            "repo_path": repo_root,
            "pr_details": pr_details,
            "commits": [],
            "branch_file_and_commits": branch_file_and_commits,
            "compare_type": "local",
            "base_ref": base_ref,
            "base_branch": base_ref,
            "from_branch": "local",
            "to_branch": base_ref,
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