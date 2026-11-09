"""
Merge conflict detection and resolution for codx-junior.

Extends :class:`codx.junior.engine.git_validator.GitValidatorEngine` with the
pieces the git view needs when a merge, rebase, cherry-pick or revert stops on
conflicts:

- :meth:`GitConflictEngine.get_conflicts`: detects the operation in progress and
  describes every unmerged path (status, conflict marker blocks, stage blobs,
  working tree content).
- :meth:`GitConflictEngine.resolve_conflict`: resolves one path manually by
  writing the merged content, taking *ours*/*theirs*, or staging the file the
  user edited outside the view.
- :meth:`GitConflictEngine.resolve_conflicts_with_ai`: asks the project LLM to
  merge the conflicting versions of one or more files.
- :meth:`GitConflictEngine.continue_operation` /
  :meth:`GitConflictEngine.abort_operation`: finish or discard the pending
  merge, rebase, cherry-pick or revert.

Nothing is ever committed or aborted implicitly: a conflicted merge/rebase is
left in progress (``keep_conflicts=True``) so the user can choose between
manual resolution, AI resolution and aborting the whole operation.

```mermaid
sequenceDiagram
    participant UI as GitView / conflict resolver
    participant API as git router
    participant Engine as GitConflictEngine
    participant Git as git CLI
    participant AI as LLM

    UI->>API: GET /api/git/repo/conflicts
    API->>Engine: get_conflicts()
    Engine->>Git: git ls-files -u -z / status / git-path MERGE_HEAD
    Engine-->>API: operation + conflicts + markers + content
    API-->>UI: 200 conflict state

    UI->>API: POST /api/git/repo/conflicts/resolve { path, content }
    API->>Engine: resolve_conflict()
    Engine->>Git: write file + git add -- path
    Engine-->>API: remaining conflicts

    UI->>API: POST /api/git/repo/conflicts/ai { paths }
    API->>Engine: resolve_conflicts_with_ai()
    Engine->>AI: base / ours / theirs / working tree
    AI-->>Engine: merged content
    Engine->>Git: write file + git add -- path
    Engine-->>API: applied resolutions

    UI->>API: POST /api/git/repo/conflicts/continue
    API->>Engine: continue_operation()
    Engine->>Git: git commit / git rebase --continue ...
    Engine-->>API: 200 operation result
```

Made with ❤️ by codx-junior
"""

import logging
import os
import re

from typing import Dict, List, Optional, Tuple

from codx.junior.engine.git_validator import GitValidatorEngine

logger = logging.getLogger(__name__)

# Porcelain conflict code -> human readable status and the labels used by the UI
CONFLICT_STATUS = {
    "DD": "both deleted",
    "AU": "added by us",
    "UD": "deleted by them",
    "UA": "added by them",
    "DU": "deleted by us",
    "AA": "both added",
    "UU": "both modified",
}

# Operation in progress -> title shown by the resolver
OPERATION_LABELS = {
    "merge": "Merge",
    "rebase": "Rebase",
    "cherry-pick": "Cherry-pick",
    "revert": "Revert",
}

# Repository files describing the operation in progress
MERGE_HEAD_FILE = "MERGE_HEAD"
MERGE_MSG_FILE = "MERGE_MSG"
SQUASH_MSG_FILE = "SQUASH_MSG"
CHERRY_PICK_HEAD_FILE = "CHERRY_PICK_HEAD"
REVERT_HEAD_FILE = "REVERT_HEAD"
REBASE_MERGE_DIR = "rebase-merge"
REBASE_APPLY_DIR = "rebase-apply"

# Conflict marker lines (diff3 style adds the ||||||| base section)
MARKER_START = "<<<<<<<"
MARKER_BASE = "|||||||"
MARKER_SEPARATOR = "======="
MARKER_END = ">>>>>>>"

# Maximum characters of a single working tree file returned to the UI. A
# conflict on a generated/minified file must not blow up the HTTP payload.
MAX_CONFLICT_FILE_CHARS = 1_000_000

# Per-section budget of the AI prompt (base / ours / theirs / working tree)
MAX_AI_SECTION_CHARS = 20_000

# The AI is asked to return only the merged file: anything looking like a
# conflict marker in the answer means the resolution is not usable.
CONFLICT_MARKER_PATTERN = re.compile(
    r"^(?:<{7}|={7}|>{7}|\|{7})(?: .*)?$", re.MULTILINE
)

# Fenced answer (```python ... ```) or an explicit <resolved_file> wrapper
CODE_FENCE_PATTERN = re.compile(r"^```[^\n]*\n(?P<body>.*?)\n?```$", re.DOTALL)
RESOLVED_FILE_PATTERN = re.compile(
    r"<resolved_file>\s*(?P<body>.*?)\s*</resolved_file>", re.DOTALL
)

# Parsing of a `git ls-files -u -z` record: "<mode> <sha> <stage>\t<path>"
LS_FILES_UNMERGED_PATTERN = re.compile(
    r"^(?P<mode>[0-9]+) (?P<sha>[0-9a-f]+) (?P<stage>[123])$"
)

# `Merge branch 'feature' into main` / `Merge remote-tracking branch 'origin/x'`
MERGE_MESSAGE_PATTERN = re.compile(
    r"Merge (?:remote-tracking )?branch ['\"](?P<branch>[^'\"]+)['\"]"
)


class GitConflictEngine(GitValidatorEngine):
    """
    Engine for conflict detection and resolution on top of the git router.

    Being a :class:`GitValidatorEngine`, it serves every other endpoint of the
    git router as well; :meth:`get_repo_info` is extended with the conflict
    state so the view detects a pending operation while loading the repository.
    """

    # -------------------------------------------------------------------------
    # Repository paths
    # -------------------------------------------------------------------------

    def _git_path(self, name: str, cwd: Optional[str] = None) -> str:
        """
        Resolve a path inside the git directory of the repository/worktree.

        ``git rev-parse --git-path`` is used instead of joining ``.git`` so the
        method works inside linked worktrees too (their git dir is not the
        repository's ``.git`` folder).

        Args:
            name: Path relative to the git directory, e.g. ``MERGE_HEAD``.
            cwd: Working directory. Defaults to the repository root.

        Returns:
            Absolute path, or an empty string when git cannot resolve it.
        """
        cwd = cwd or self._get_repo_root()
        result = self._run_git(["rev-parse", "--git-path", name], cwd=cwd)
        path = (result.get("output") or "").strip()
        if not path:
            return ""
        if not os.path.isabs(path):
            path = os.path.join(cwd, path)
        return os.path.normpath(path)

    def _read_git_file(self, name: str, cwd: Optional[str] = None) -> str:
        """
        Read a small file from the git directory (``MERGE_HEAD``, ``MERGE_MSG``).

        Args:
            name: File name relative to the git directory.
            cwd: Working directory. Defaults to the repository root.

        Returns:
            File content stripped, or an empty string when it does not exist.
        """
        path = self._git_path(name, cwd=cwd)
        try:
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    return handle.read().strip()
        except (IOError, OSError) as ex:
            logger.debug("Could not read git file %s: %s", path, ex)
        return ""

    def _git_dir_exists(self, name: str, cwd: Optional[str] = None) -> bool:
        """Return whether a file/folder exists inside the git directory."""
        path = self._git_path(name, cwd=cwd)
        return bool(path and os.path.exists(path))

    def _remove_git_file(self, name: str, cwd: Optional[str] = None) -> None:
        """
        Remove a small file from the git directory (a stale ``SQUASH_MSG``).

        ``git reset --merge`` cleans the index/worktree of an aborted squash
        merge but leaves ``SQUASH_MSG`` behind; a stale file would make the next
        load report an operation in progress.

        Args:
            name: File name relative to the git directory.
            cwd: Working directory. Defaults to the repository root.
        """
        path = self._git_path(name, cwd=cwd)
        try:
            if path and os.path.isfile(path):
                os.remove(path)
        except (IOError, OSError) as ex:
            logger.debug("Could not remove git file %s: %s", path, ex)

    def _has_staged_changes(self, cwd: Optional[str] = None) -> bool:
        """Return whether the index holds changes against HEAD."""
        result = self._run_git(
            ["diff", "--cached", "--name-only"], cwd=cwd
        )
        return bool(result["ok"] and (result.get("output") or "").strip())

    # -------------------------------------------------------------------------
    # Conflict detection
    # -------------------------------------------------------------------------

    def _unmerged_stages(self, cwd: Optional[str] = None) -> Dict[str, Dict[int, dict]]:
        """
        Read the unmerged index entries of the repository.

        ``git ls-files -u -z`` returns one NUL-separated record per stage:
        ``<mode> <sha> <stage>\\t<path>``. Stages are 1 (base), 2 (ours) and 3
        (theirs); a missing stage means that side deleted the file.

        Args:
            cwd: Working directory. Defaults to the repository root.

        Returns:
            Dict of ``path -> {stage: {mode, sha}}`` for every unmerged path.

        Example:
            >>> engine._unmerged_stages()["app.py"].keys()
            dict_keys([1, 2, 3])
        """
        result = self._run_git(
            ["ls-files", "-u", "-z"], cwd=cwd, strip_output=False
        )
        stages: Dict[str, Dict[int, dict]] = {}
        if not result["ok"]:
            return stages

        for record in (result.get("output") or "").split("\0"):
            if not record.strip():
                continue
            meta, separator, path = record.partition("\t")
            if not separator or not path:
                continue
            match = LS_FILES_UNMERGED_PATTERN.match(meta.strip())
            if not match:
                continue
            stage = int(match.group("stage"))
            stages.setdefault(path, {})[stage] = {
                "mode": match.group("mode"),
                "sha": match.group("sha"),
            }
        return stages

    def _conflict_paths(self, cwd: Optional[str] = None) -> List[str]:
        """
        Return the paths with unmerged index entries, sorted.

        Args:
            cwd: Working directory. Defaults to the repository root.

        Returns:
            Sorted repo-relative conflict paths.
        """
        return sorted(self._unmerged_stages(cwd=cwd).keys())

    def _conflict_status_codes(self) -> Dict[str, str]:
        """
        Map every unmerged path to its porcelain code (``UU``, ``AA``...).

        ``git status --porcelain`` reports both sides of an unmerged entry with
        the same code (``UU``, ``AA``, ``DU``...), which is exactly the code the
        conflict resolver displays.

        Returns:
            Dict of ``path -> code`` for the unmerged entries.
        """
        codes: Dict[str, str] = {}
        for line in self.get_working_tree_status()["files"]:
            parsed = self._parse_status_line(line)
            if not parsed:
                continue
            index_code, worktree_code, path = parsed
            code = f"{index_code}{worktree_code}"
            if code in CONFLICT_STATUS:
                codes[path] = code
        return codes

    def _parse_conflict_blocks(self, content: str) -> List[dict]:
        """
        Parse the conflict marker blocks of a file with merge markers.

        Supports both the two-way style (``<<<<<<<`` / ``=======`` /
        ``>>>>>>>``) and the diff3 style that adds a ``|||||||`` base section.

        Args:
            content: File content, with or without conflict markers.

        Returns:
            List of blocks, each with ``start_line``, labels and the text of the
            ``ours``, ``base`` and ``theirs`` sections.

        Example:
            >>> blocks = engine._parse_conflict_blocks(content)
            >>> blocks[0]["ours_label"]
            'HEAD'
        """
        lines = (content or "").splitlines(keepends=True)
        blocks: List[dict] = []
        index = 0

        while index < len(lines):
            line = lines[index]
            if not line.startswith(MARKER_START):
                index += 1
                continue

            block = {
                "start_line": index + 1,
                "end_line": index + 1,
                "ours_label": line[len(MARKER_START):].strip(),
                "base_label": "",
                "theirs_label": "",
                "ours": "",
                "base": "",
                "theirs": "",
            }
            section = "ours"
            sections: Dict[str, List[str]] = {
                "ours": [],
                "base": [],
                "theirs": [],
            }
            index += 1

            while index < len(lines):
                current = lines[index]
                if (
                    section == "ours"
                    and current.startswith(MARKER_BASE)
                ):
                    block["base_label"] = current[len(MARKER_BASE):].strip()
                    section = "base"
                    index += 1
                    continue
                if current.startswith(MARKER_SEPARATOR):
                    # Only a plain ======= line separates ours from theirs; a
                    # longer run of '=' is still a separator line.
                    section = "theirs"
                    index += 1
                    continue
                if current.startswith(MARKER_END):
                    block["theirs_label"] = current[len(MARKER_END):].strip()
                    block["end_line"] = index + 1
                    index += 1
                    break

                sections[section].append(current)
                index += 1

            block["ours"] = "".join(sections["ours"])
            block["base"] = "".join(sections["base"])
            block["theirs"] = "".join(sections["theirs"])
            blocks.append(block)

        return blocks

    def _marker_summary(self, content: str) -> dict:
        """
        Count the conflict markers of a file.

        Args:
            content: File content.

        Returns:
            Dict with 'count' (marker blocks), 'has_markers' and 'blocks'.
        """
        if not content:
            return {"count": 0, "has_markers": False, "blocks": []}
        blocks = self._parse_conflict_blocks(content)
        has_markers = bool(CONFLICT_MARKER_PATTERN.search(content))
        return {
            "count": len(blocks),
            "has_markers": has_markers,
            "blocks": blocks,
        }

    def _read_worktree_file(self, path: str) -> dict:
        """
        Read a file from the working tree, refusing paths outside the repo.

        Args:
            path: Repo-relative path.

        Returns:
            Dict with 'content', 'truncated', 'binary', 'exists' and 'error'.
        """
        repo_root = os.path.normpath(self._get_repo_root())
        relative = self._to_repo_path(path)
        if not relative:
            return {
                "content": "",
                "truncated": False,
                "binary": False,
                "exists": False,
                "error": "Invalid file path",
            }

        absolute = os.path.normpath(os.path.join(repo_root, relative))
        if not absolute.startswith(repo_root + os.sep):
            return {
                "content": "",
                "truncated": False,
                "binary": False,
                "exists": False,
                "error": "File path must belong to the repository",
            }
        if not os.path.isfile(absolute):
            return {
                "content": "",
                "truncated": False,
                "binary": False,
                "exists": False,
                "error": "",
            }

        try:
            with open(absolute, "rb") as handle:
                raw = handle.read(MAX_CONFLICT_FILE_CHARS + 1)
        except (IOError, OSError) as ex:
            return {
                "content": "",
                "truncated": False,
                "binary": False,
                "exists": False,
                "error": str(ex),
            }

        truncated = len(raw) > MAX_CONFLICT_FILE_CHARS
        if truncated:
            raw = raw[:MAX_CONFLICT_FILE_CHARS]

        binary = b"\0" in raw[:8192]
        if binary:
            return {
                "content": "",
                "truncated": truncated,
                "binary": True,
                "exists": True,
                "error": "",
            }

        return {
            "content": raw.decode("utf-8", errors="replace"),
            "truncated": truncated,
            "binary": False,
            "exists": True,
            "error": "",
        }

    def _stage_content(self, stage_info: Optional[dict]) -> dict:
        """
        Read the blob stored in a conflict stage.

        Args:
            stage_info: Entry from :meth:`_unmerged_stages` (or None).

        Returns:
            Dict with 'content', 'binary', 'exists' and 'truncated'.
        """
        if not stage_info:
            return {
                "content": "",
                "binary": False,
                "exists": False,
                "truncated": False,
            }

        result = self._run_git(
            ["cat-file", "blob", stage_info["sha"]], strip_output=False
        )
        if not result["ok"]:
            return {
                "content": "",
                "binary": False,
                "exists": True,
                "truncated": False,
            }

        content = result.get("output") or ""
        binary = "\0" in content[:8192]
        truncated = len(content) > MAX_CONFLICT_FILE_CHARS
        if truncated:
            content = content[:MAX_CONFLICT_FILE_CHARS]
        return {
            "content": "" if binary else content,
            "binary": binary,
            "exists": True,
            "truncated": truncated,
        }

    def _operation_state(self, cwd: Optional[str] = None) -> dict:
        """
        Detect the operation in progress (merge, rebase, cherry-pick, revert).

        A squash merge has no ``MERGE_HEAD``; when it stops on conflicts git
        leaves ``SQUASH_MSG`` behind, which is used to recognise the pending
        squash result.

        Args:
            cwd: Working directory. Defaults to the repository root.

        Returns:
            Dict with 'operation' (empty when idle), 'label', 'squash',
            'merge_head', 'merge_message', 'source_branch', 'rebase_branch',
            'rebase_onto' and 'current_branch'.
        """
        repo_path = cwd or self._get_repo_root()
        operation = ""
        details = {
            "operation": "",
            "label": "",
            "squash": False,
            "merge_head": "",
            "merge_message": "",
            "source_branch": "",
            "rebase_branch": "",
            "rebase_onto": "",
            "current_branch": self._current_branch(cwd=repo_path),
        }

        if self._git_dir_exists(REBASE_MERGE_DIR, cwd=repo_path) or self._git_dir_exists(
            REBASE_APPLY_DIR, cwd=repo_path
        ):
            operation = "rebase"
            head_name = self._read_git_file(
                f"{REBASE_MERGE_DIR}/head-name", cwd=repo_path
            ) or self._read_git_file(
                f"{REBASE_APPLY_DIR}/head-name", cwd=repo_path
            )
            onto = self._read_git_file(
                f"{REBASE_MERGE_DIR}/onto", cwd=repo_path
            ) or self._read_git_file(
                f"{REBASE_APPLY_DIR}/onto", cwd=repo_path
            )
            details["rebase_branch"] = head_name.replace("refs/heads/", "")
            details["rebase_onto"] = onto
            details["current_branch"] = details["rebase_branch"] or details["current_branch"]
        elif self._git_dir_exists(MERGE_HEAD_FILE, cwd=repo_path):
            operation = "merge"
            details["merge_head"] = self._read_git_file(
                MERGE_HEAD_FILE, cwd=repo_path
            )
            details["merge_message"] = self._read_git_file(
                MERGE_MSG_FILE, cwd=repo_path
            )
        elif self._git_dir_exists(CHERRY_PICK_HEAD_FILE, cwd=repo_path):
            operation = "cherry-pick"
        elif self._git_dir_exists(REVERT_HEAD_FILE, cwd=repo_path):
            operation = "revert"
        elif self._git_dir_exists(SQUASH_MSG_FILE, cwd=repo_path) and (
            self._conflict_paths(cwd=repo_path) or self._has_staged_changes(cwd=repo_path)
        ):
            operation = "merge"
            details["squash"] = True
            details["merge_message"] = self._read_git_file(
                SQUASH_MSG_FILE, cwd=repo_path
            )

        if details["merge_message"] and not details["source_branch"]:
            match = MERGE_MESSAGE_PATTERN.search(details["merge_message"])
            if match:
                details["source_branch"] = match.group("branch")

        details["operation"] = operation
        details["label"] = OPERATION_LABELS.get(operation, "")
        return details

    def _build_conflict_entry(
        self,
        path: str,
        code: str,
        stages: Dict[int, dict],
        include_content: bool,
        include_sides: bool,
    ) -> dict:
        """
        Build the payload of a single conflicted file.

        Args:
            path: Repo-relative path.
            code: Porcelain conflict code (``UU``, ``AA``...).
            stages: Stage entries of the path.
            include_content: Include the working tree content and markers.
            include_sides: Include the base/ours/theirs blob content.

        Returns:
            Conflict entry dict.
        """
        status_label = CONFLICT_STATUS.get(code, "conflicted")
        working = self._read_worktree_file(path)
        marker_summary = self._marker_summary(working["content"])

        entry = {
            "path": path,
            "code": code,
            "status": "conflict",
            "status_label": status_label,
            "binary": working["binary"],
            "exists": working["exists"],
            "truncated": working["truncated"],
            "marker_count": marker_summary["count"],
            "has_markers": marker_summary["has_markers"],
            "markers": marker_summary["blocks"],
            "ours_label": next(
                (
                    block["ours_label"]
                    for block in marker_summary["blocks"]
                    if block.get("ours_label")
                ),
                "",
            ),
            "theirs_label": next(
                (
                    block["theirs_label"]
                    for block in marker_summary["blocks"]
                    if block.get("theirs_label")
                ),
                "",
            ),
            "stages": {
                "base": bool(stages.get(1)),
                "ours": bool(stages.get(2)),
                "theirs": bool(stages.get(3)),
            },
        }

        if include_content:
            entry["content"] = working["content"]
            entry["error"] = working["error"]

        if include_sides:
            entry["sides"] = {
                "base": self._stage_content(stages.get(1)),
                "ours": self._stage_content(stages.get(2)),
                "theirs": self._stage_content(stages.get(3)),
            }

        return entry

    def _pending_stash(self) -> Optional[dict]:
        """
        Return the auto-stash created before the pending merge/rebase, if any.

        A conflict left in progress cannot restore its auto-stash (popping it on
        top of the unresolved operation would fail), so the stash is kept and
        reported here until the operation is continued or aborted.

        Returns:
            Dict with 'ref' and 'message', or None when there is no auto-stash.
        """
        result = self._run_git(["stash", "list", "--format=%gd|%s"])
        if not result["ok"]:
            return None
        for line in result["output"].split("\n"):
            ref, separator, message = line.partition("|")
            if not separator:
                continue
            # `git stash list` prefixes the message with "On <branch>: "
            if (
                "codx-junior: auto-stash before merging" in message
                or "codx-junior: auto-stash before rebasing" in message
            ):
                return {"ref": ref.strip(), "message": message.strip()}
        return None

    def _pop_pending_stash(self) -> dict:
        """
        Restore the auto-stash kept for the pending operation, when it exists.

        Returns:
            Dict with 'restored' (True when a stash was popped), 'ref', 'output'
            and 'error'.

        Example:
            >>> engine._pop_pending_stash()
            {'restored': True, 'ref': 'stash@{0}', 'output': '', 'error': ''}
        """
        stash = self._pending_stash()
        if not stash:
            return {"restored": False, "ref": "", "output": "", "error": ""}
        result = self._run_git(["stash", "pop", stash["ref"]])
        return {
            "restored": result["ok"],
            "ref": stash["ref"],
            "output": result["output"],
            "error": "" if result["ok"] else result["error"],
        }

    def get_conflicts(
        self,
        include_content: bool = True,
        paths: Optional[List[str]] = None,
        include_sides: bool = False,
    ) -> dict:
        """
        Return the conflict state of the repository.

        The state covers the operation in progress (merge, rebase, cherry-pick,
        revert or a stalled squash merge) and every unmerged path with its
        status, conflict marker blocks and, optionally, its content and the
        base/ours/theirs blobs.

        Args:
            include_content: Include the working tree content of each conflict.
            paths: Restrict the payload to these paths (all when omitted).
            include_sides: Include the base/ours/theirs blob content (used by
                the AI resolver; the UI does not need it).

        Returns:
            Dict with 'success', 'in_progress', 'has_conflicts', 'operation',
            'operation_label', 'squash', 'branch', 'merge_head', 'source_branch',
            'conflicts', 'conflict_count', 'unresolved_count', 'can_continue',
            'can_abort', 'stash_kept' and 'errors'. ``in_progress`` is True for
            a pending operation even when every file is already resolved, so
            the UI can distinguish it from unresolved conflicts.

        Example:
            >>> state = engine.get_conflicts()
            >>> state["operation"]
            'merge'
            >>> [item["path"] for item in state["conflicts"]]
            ['app.py']
        """
        repo_path = self._get_repo_root()
        stages = self._unmerged_stages(cwd=repo_path)
        codes = self._conflict_status_codes()
        wanted = {self._to_repo_path(path) for path in (paths or []) if path}
        conflict_paths = sorted(stages.keys())
        if wanted:
            conflict_paths = [path for path in conflict_paths if path in wanted]

        conflicts = [
            self._build_conflict_entry(
                path=path,
                code=codes.get(path) or self._infer_conflict_code(stages[path]),
                stages=stages[path],
                include_content=include_content,
                include_sides=include_sides,
            )
            for path in conflict_paths
        ]

        operation = self._operation_state(cwd=repo_path)
        in_progress = bool(operation["operation"] or conflicts)
        can_continue = bool(
            operation["operation"]
            and operation["operation"] in ("merge", "rebase", "cherry-pick", "revert")
            and not conflicts
            and not operation["squash"]
        )
        # A squash merge has no operation to continue: the resolved changes are
        # simply committed from the composer.
        can_commit = bool(operation["squash"] and not conflicts)
        stash = self._pending_stash()

        return {
            "success": True,
            "in_progress": in_progress,
            "operation": operation["operation"],
            "operation_label": operation["label"],
            "squash": operation["squash"],
            "branch": operation["current_branch"],
            "merge_head": operation["merge_head"],
            "merge_message": operation["merge_message"],
            "source_branch": operation["source_branch"],
            "rebase_branch": operation["rebase_branch"],
            "rebase_onto": operation["rebase_onto"],
            "conflicts": conflicts,
            "has_conflicts": bool(conflicts),
            "conflict_count": len(conflicts),
            "unresolved_count": len(conflicts),
            "can_continue": can_continue,
            "can_commit": can_commit,
            "can_abort": in_progress,
            "stash_kept": bool(stash),
            "stash_ref": stash["ref"] if stash else "",
            "stash_message": stash["message"] if stash else "",
            "errors": [],
        }

    def _infer_conflict_code(self, stages: Dict[int, dict]) -> str:
        """
        Infer the porcelain conflict code when ``git status`` no longer lists it.

        Args:
            stages: Stage entries of one path.

        Returns:
            Conflict code (``UU`` by default).
        """
        has_base = bool(stages.get(1))
        has_ours = bool(stages.get(2))
        has_theirs = bool(stages.get(3))
        if not has_base and has_ours and has_theirs:
            return "AA"
        if not has_base and has_ours:
            return "AU"
        if not has_base and has_theirs:
            return "UA"
        if has_ours and not has_theirs:
            return "UD"
        if has_theirs and not has_ours:
            return "DU"
        if not has_ours and not has_theirs:
            return "DD"
        return "UU"

    def get_repo_info(self) -> dict:
        """
        Extend the repository summary with the conflict state.

        The git view calls this endpoint on load, so a pending merge/rebase is
        detected immediately: ``in_conflict`` is True, ``conflicts`` lists the
        unmerged paths and ``conflict_state`` carries the full summary.

        Returns:
            Repository info dict plus 'in_conflict', 'operation_in_progress',
            'has_conflicts', 'conflicts' and 'conflict_state'.
        """
        info = super().get_repo_info()
        state = self.get_conflicts(include_content=False)
        info["in_conflict"] = bool(state["in_progress"])
        info["operation_in_progress"] = bool(state["in_progress"])
        info["has_conflicts"] = bool(state["conflicts"])
        info["conflicts"] = [entry["path"] for entry in state["conflicts"]]
        info["conflict_state"] = state
        return info

    def get_repo_status(self) -> dict:
        """
        Extend the working tree status with the conflict summary.

        Returns:
            Status dict plus 'in_conflict', 'operation_in_progress',
            'has_conflicts', 'conflicts' and 'conflict_state'.
        """
        status = super().get_repo_status()
        state = self.get_conflicts(include_content=False)
        status["in_conflict"] = bool(state["in_progress"])
        status["operation_in_progress"] = bool(state["in_progress"])
        status["has_conflicts"] = bool(state["conflicts"])
        status["conflicts"] = [entry["path"] for entry in state["conflicts"]]
        status["conflict_state"] = state
        return status

    # -------------------------------------------------------------------------
    # Resolution
    # -------------------------------------------------------------------------

    def _require_conflict(self, path: str) -> Tuple[str, Optional[dict]]:
        """
        Normalize a path and check it is currently unmerged.

        Args:
            path: File path (absolute or repo-relative).

        Returns:
            Tuple ``(resolved_path, error)``; error is None when the path is a
            current conflict.
        """
        resolved = self._to_repo_path(path)
        if not resolved:
            return "", self._git_operation_error("File path is required")
        if resolved not in self._unmerged_stages():
            return resolved, self._git_operation_error(
                f"'{resolved}' is not a conflicted file"
            )
        return resolved, None

    def _content_has_markers(self, content: str) -> bool:
        """Return whether *content* still holds git conflict markers."""
        return bool(CONFLICT_MARKER_PATTERN.search(content or ""))

    def _take_side(self, path: str, side: str) -> dict:
        """
        Check out one side of a conflict (``ours`` or ``theirs``).

        When the chosen side deleted the file there is no stage to check out:
        the file is removed from the working tree and the index instead.

        Args:
            path: Repo-relative conflict path.
            side: ``ours`` or ``theirs``.

        Returns:
            Result of the git command, or an error result.
        """
        stage = 2 if side == "ours" else 3
        stages = self._unmerged_stages().get(path, {})
        repo_path = self._get_repo_root()

        if not stages.get(stage):
            removal = self._run_git(
                ["rm", "-f", "--ignore-unmatch", "--", path], cwd=repo_path
            )
            return removal

        result = self._run_git(
            ["checkout", f"--{side}", "--", path], cwd=repo_path
        )
        if result["ok"]:
            return result
        # Older git versions spell the same operation through restore
        restore = self._run_git(
            ["restore", f"--{side}", "--worktree", "--", path], cwd=repo_path
        )
        return restore if restore["ok"] else result

    def resolve_conflict(
        self,
        path: str,
        content: Optional[str] = None,
        strategy: str = "manual",
        stage: bool = True,
        allow_markers: bool = False,
    ) -> dict:
        """
        Resolve one conflicted file.

        Strategies:

        * ``manual`` / ``content``: write *content* as the merged file. The
          content must not contain conflict markers unless *allow_markers* is
          set, so a half-finished resolution is never staged by mistake.
        * ``ours`` / ``theirs``: take that side of the conflict, including the
          deletion when that side deleted the file.
        * ``stage``: keep the file as it is on disk (edited outside the view)
          and mark it resolved. Markers are rejected.
        * ``delete``: remove the file and mark the deletion resolved.

        Args:
            path: Conflicted file path (absolute or repo-relative).
            content: Full merged content for the manual strategy.
            strategy: Resolution strategy.
            stage: Stage the file after resolving it (default True).
            allow_markers: Allow content that still contains conflict markers.

        Returns:
            Dict with 'success', 'action', 'path', 'strategy', 'resolved',
            'remaining', 'state' and 'errors'.

        Example:
            >>> engine.resolve_conflict("app.py", "print('merged')\\n")
            {'success': True, 'resolved': True, 'remaining': 0, ...}
            >>> engine.resolve_conflict("app.py", strategy="theirs")
        """
        resolved_path, error = self._require_conflict(path)
        if error:
            return error

        strategy = (strategy or "manual").strip().lower()
        repo_path = self._get_repo_root()
        steps: List[dict] = []
        errors: List[str] = []

        if strategy in ("manual", "content"):
            if content is None:
                return self._git_operation_error(
                    "The resolved content is required for the manual strategy",
                    path=resolved_path,
                    strategy=strategy,
                )
            if self._content_has_markers(content) and not allow_markers:
                return self._git_operation_error(
                    "The file still contains conflict markers: resolve them before saving",
                    path=resolved_path,
                    strategy=strategy,
                )
            write = self._write_repo_file(repo_path, resolved_path, content)
            steps.append({"name": "write", **write})
            if not write["ok"]:
                return self._git_operation_error(
                    write["error"] or "Could not write the resolved file",
                    path=resolved_path,
                    strategy=strategy,
                    steps=steps,
                )
        elif strategy in ("ours", "theirs"):
            take = self._take_side(resolved_path, strategy)
            steps.append({"name": strategy, **take})
            if not take["ok"]:
                errors.append(
                    take["error"] or f"Could not take the {strategy} version"
                )
        elif strategy == "stage":
            working = self._read_worktree_file(resolved_path)
            if working["binary"]:
                errors.append("Binary files must be resolved with ours/theirs")
            elif self._content_has_markers(working["content"]) and not allow_markers:
                errors.append(
                    "The file still contains conflict markers: resolve them before marking it resolved"
                )
        elif strategy == "delete":
            removal = self._run_git(
                ["rm", "-f", "--ignore-unmatch", "--", resolved_path],
                cwd=repo_path,
            )
            steps.append({"name": "delete", **removal})
            if not removal["ok"]:
                errors.append(removal["error"] or "Could not remove the file")
        else:
            return self._git_operation_error(
                f"Unknown resolution strategy '{strategy}'",
                path=resolved_path,
                strategy=strategy,
            )

        if not errors and stage and strategy != "delete":
            staged = self._run_git(
                ["add", "-A", "--", resolved_path], cwd=repo_path
            )
            steps.append({"name": "stage", **staged})
            if not staged["ok"]:
                errors.append(staged["error"] or "Could not stage the file")

        state = self.get_conflicts(include_content=False)
        remaining = state["unresolved_count"]
        result = {
            "success": not errors,
            "action": "resolve",
            "path": resolved_path,
            "strategy": strategy,
            "resolved": not errors and remaining == 0,
            "remaining": remaining,
            "state": state,
            "steps": steps,
            "errors": errors,
        }
        return result

    # -------------------------------------------------------------------------
    # AI resolution
    # -------------------------------------------------------------------------

    def _truncate_prompt_section(self, text: str, limit: int) -> str:
        """Truncate a prompt section, marking that it was cut."""
        text = text or ""
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "\n... (truncated)"

    def _conflict_prompt(self, entry: dict, instructions: str = "") -> str:
        """
        Build the AI prompt for one conflicted file.

        The model receives the base/ours/theirs versions and the working tree
        (with markers) and must answer with the complete merged file only.

        Args:
            entry: Conflict entry produced with ``include_sides=True``.
            instructions: Optional user guidance.

        Returns:
            Prompt string.
        """
        sides = entry.get("sides") or {}
        base = self._truncate_prompt_section(
            (sides.get("base") or {}).get("content", ""), MAX_AI_SECTION_CHARS
        )
        ours = self._truncate_prompt_section(
            (sides.get("ours") or {}).get("content", ""), MAX_AI_SECTION_CHARS
        )
        theirs = self._truncate_prompt_section(
            (sides.get("theirs") or {}).get("content", ""), MAX_AI_SECTION_CHARS
        )
        working = self._truncate_prompt_section(
            entry.get("content", ""), MAX_AI_SECTION_CHARS
        )
        labels = []
        if entry.get("ours_label"):
            labels.append(f"ours: {entry['ours_label']}")
        if entry.get("theirs_label"):
            labels.append(f"theirs: {entry['theirs_label']}")
        label_text = f"\nConflict sides: {', '.join(labels)}" if labels else ""
        hints = (
            f"\n<user_instructions>\n{instructions.strip()}\n</user_instructions>\n"
            if (instructions or "").strip()
            else ""
        )

        return f"""You resolve a git merge conflict in a software repository.

Return ONLY the complete resolved file content. Do not include explanations,
Markdown fences, comments about the conflict or any conflict marker
(<<<<<<<, |||||||, =======, >>>>>>>). Keep the surrounding code, imports,
formatting and line endings of the file. Combine both sides when both changes
are meaningful; never drop a change without a reason.

Conflict type: {entry.get('status_label')}
File: {entry.get('path')}{label_text}
{hints}
<base_version>
{base}
</base_version>

<ours_version>
{ours}
</ours_version>

<theirs_version>
{theirs}
</theirs_version>

<working_tree_with_markers>
{working}
</working_tree_with_markers>

Return the complete resolved file content now.
"""

    def _clean_ai_content(self, raw: str, original: str = "") -> str:
        """
        Extract the merged file from the model answer.

        Accepts a plain answer, a fenced block and an explicit
        ``<resolved_file>`` wrapper, then removes the trailing newline added by
        fencing while keeping the file's original trailing-newline style.

        Args:
            raw: Raw model answer.
            original: Working tree content (used to match trailing newlines).

        Returns:
            Resolved content, empty when the answer has no content.
        """
        text = str(raw or "").strip()
        if not text:
            return ""

        wrapped = RESOLVED_FILE_PATTERN.search(text)
        if wrapped:
            text = wrapped.group("body").strip("\n")

        fenced = CODE_FENCE_PATTERN.match(text)
        if fenced:
            text = fenced.group("body").strip("\n")

        text = text.strip("\r\n")
        if not text:
            return ""
        if original.endswith(("\n", "\r\n")) or not original:
            text += "\n"
        return text

    async def resolve_conflicts_with_ai(
        self,
        paths: Optional[List[str]] = None,
        instructions: str = "",
        apply: bool = True,
        continue_operation: bool = False,
    ) -> dict:
        """
        Resolve conflicts with the project LLM.

        Each conflicted file is sent with its base/ours/theirs versions and the
        working tree markers. The answer is validated (no conflict markers) and,
        when *apply* is true, written and staged. A failure on one file never
        discards the resolutions already applied to the others.

        Args:
            paths: Conflicts to resolve. Defaults to every conflicted file.
            instructions: Optional guidance for the merge decision.
            apply: Write and stage the answers (False returns suggestions only).
            continue_operation: Continue the merge/rebase once every conflict is
                resolved.

        Returns:
            Dict with 'success', 'applied', 'fallback', 'files' (one entry per
            path with 'content', 'applied' and 'error'), 'continued', 'state'
            and 'errors'.

        Example:
            >>> result = await engine.resolve_conflicts_with_ai()
            >>> result["applied"]
            True
        """
        result = {
            "success": False,
            "applied": False,
            "fallback": False,
            "files": [],
            "continued": False,
            "state": {},
            "errors": [],
        }

        state = self.get_conflicts(
            include_content=True, paths=paths, include_sides=True
        )
        conflicts = [entry for entry in state["conflicts"] if not entry["binary"]]
        skipped = [entry for entry in state["conflicts"] if entry["binary"]]
        for entry in skipped:
            result["files"].append(
                {
                    "path": entry["path"],
                    "applied": False,
                    "content": "",
                    "error": "Binary conflicts must be resolved with ours/theirs",
                }
            )

        if not conflicts:
            result["state"] = state
            result["errors"].append(
                "There are no text conflicts to resolve with AI"
                if skipped
                else "There are no conflicts in this repository"
            )
            return result

        get_ai = getattr(self.session, "get_ai", None)
        if not callable(get_ai):
            result["fallback"] = True
            result["errors"].append("AI is not available in this session")
            result["state"] = state
            return result

        try:
            ai = get_ai()
        except Exception as ex:
            logger.exception("Could not build the AI client: %s", ex)
            result["fallback"] = True
            result["errors"].append(str(ex) or "AI is not available")
            result["state"] = state
            return result

        for entry in conflicts:
            path = entry["path"]
            resolution = {
                "path": path,
                "applied": False,
                "content": "",
                "error": "",
            }
            prompt = self._conflict_prompt(entry, instructions=instructions)
            try:
                messages = await ai.a_chat(
                    prompt=prompt, headers={"tags": "git-conflicts"}
                )
                raw = str(getattr(messages[-1], "content", "") or "")
            except Exception as ex:
                logger.exception("Error resolving '%s' with AI: %s", path, ex)
                resolution["error"] = str(ex) or "AI resolution failed"
                result["files"].append(resolution)
                continue

            content = self._clean_ai_content(raw, original=entry.get("content", ""))
            if not content:
                resolution["error"] = "The AI returned an empty resolution"
                result["files"].append(resolution)
                continue
            if self._content_has_markers(content):
                resolution["error"] = (
                    "The AI answer still contains conflict markers; not applied"
                )
                result["files"].append(resolution)
                continue

            resolution["content"] = content
            if not apply:
                resolution["applied"] = False
                result["files"].append(resolution)
                continue

            applied = self.resolve_conflict(
                path, content=content, strategy="manual", stage=True
            )
            resolution["applied"] = bool(applied.get("success"))
            if not applied.get("success"):
                resolution["error"] = "; ".join(applied.get("errors") or [])
            result["files"].append(resolution)

        applied_count = sum(1 for entry in result["files"] if entry["applied"] or (
            not apply and entry["content"] and not entry["error"]
        ))
        result["applied"] = applied_count > 0 and all(
            entry.get("applied") or (not apply and entry.get("content"))
            for entry in result["files"]
        )
        for entry in result["files"]:
            if entry.get("error"):
                result["errors"].append(f"{entry['path']}: {entry['error']}")

        result["state"] = self.get_conflicts(include_content=False)
        if (
            continue_operation
            and apply
            and not result["state"]["conflicts"]
            and result["state"]["can_continue"]
        ):
            continued = self.continue_operation()
            result["continued"] = bool(continued.get("success"))
            result["state"] = continued.get("state") or self.get_conflicts(
                include_content=False
            )
            if not continued.get("success"):
                result["errors"].extend(continued.get("errors") or [])

        result["success"] = bool(applied_count and not result["errors"])
        return result

    # -------------------------------------------------------------------------
    # Continue / abort
    # -------------------------------------------------------------------------

    def continue_operation(self, message: Optional[str] = None) -> dict:
        """
        Finish the pending merge/rebase/cherry-pick/revert.

        Every conflict must be resolved (and staged) first. A rebase may stop
        again on the next commit: the refreshed conflict state is returned so
        the caller can offer the next resolution round. When the operation is
        finished, the auto-stash kept for it is restored.

        Args:
            message: Optional commit message for a merge or squash commit.

        Returns:
            Dict with 'success', 'action', 'operation', 'commit', 'conflicted',
            'state', 'output', 'stash_restored', 'stash_error' and 'errors'.

        Example:
            >>> engine.continue_operation()
            {'success': True, 'operation': 'merge', 'conflicted': False, ...}
        """
        repo_path = self._get_repo_root()
        state = self.get_conflicts(include_content=False)
        result = {
            "success": False,
            "action": "continue",
            "operation": state["operation"],
            "commit": "",
            "conflicted": bool(state["conflicts"]),
            "state": state,
            "output": "",
            "stash_restored": False,
            "stash_error": "",
            "errors": [],
        }

        if state["conflicts"]:
            result["errors"].append(
                f"Resolve the {state['unresolved_count']} remaining conflict(s) first"
            )
            return result
        if not state["operation"]:
            result["errors"].append("There is no operation in progress")
            return result

        command: List[str] = []
        if state["operation"] == "merge":
            if state["squash"]:
                message = (message or "").strip() or self._squash_commit_message(
                    state
                )
                command = ["commit", "-m", message]
            else:
                if state["merge_head"]:
                    command = ["commit", "--no-edit"]
                    if message:
                        command = ["commit", "-m", message.strip()]
                else:
                    result["errors"].append(
                        "No merge is in progress: the changes are staged, commit them from the composer"
                    )
                    return result
        elif state["operation"] == "rebase":
            command = ["-c", "core.editor=true", "rebase", "--continue"]
        elif state["operation"] == "cherry-pick":
            command = ["-c", "core.editor=true", "cherry-pick", "--continue"]
        elif state["operation"] == "revert":
            command = ["-c", "core.editor=true", "revert", "--continue"]

        if not command:
            result["errors"].append("Unsupported operation in progress")
            return result

        response = self._run_git(command, cwd=repo_path)
        result["output"] = response["output"]
        if not response["ok"]:
            error = response["error"] or response["output"] or "Could not continue"
            result["errors"].append(error)
        elif state.get("squash"):
            # The squashed changes are committed: the marker file is no longer
            # a pending operation.
            self._remove_git_file(SQUASH_MSG_FILE, cwd=repo_path)

        refreshed = self.get_conflicts(include_content=False)
        result["state"] = refreshed
        result["conflicted"] = bool(refreshed["conflicts"])
        head = self._run_git(["rev-parse", "HEAD"], cwd=repo_path)
        if head["ok"]:
            result["commit"] = head["output"]
        result["success"] = bool(response["ok"] and not result["conflicted"])

        # The local changes stashed before the operation could not be restored
        # while the conflict was pending: restore them now that it finished.
        if result["success"] and state.get("stash_kept"):
            stash = self._pop_pending_stash()
            result["stash_restored"] = stash["restored"]
            result["stash_error"] = stash["error"]
            result["state"] = self.get_conflicts(include_content=False)
        return result

    def _squash_commit_message(self, state: dict) -> str:
        """
        Build a commit message for a squash merge without an explicit one.

        Args:
            state: Conflict state (carries ``merge_message``).

        Returns:
            First non-empty line of the squash message, or a generic message.
        """
        message = (state.get("merge_message") or "").strip()
        if message:
            return message.split("\n")[0].strip()
        source = state.get("source_branch") or "branch"
        target = state.get("branch") or "HEAD"
        return f"Squash branch '{source}' into '{target}'"

    def abort_operation(self) -> dict:
        """
        Abort the pending merge/rebase/cherry-pick/revert.

        A stalled squash merge has no git operation to abort, so its unmerged
        entries are reset instead.

        Returns:
            Dict with 'success', 'action', 'operation', 'state', 'output',
            'stash_restored', 'stash_error' and 'errors'.

        Example:
            >>> engine.abort_operation()["success"]
            True
        """
        repo_path = self._get_repo_root()
        state = self.get_conflicts(include_content=False)
        operation = state["operation"]
        result = {
            "success": False,
            "action": "abort",
            "operation": operation,
            "state": state,
            "output": "",
            "stash_restored": False,
            "stash_error": "",
            "errors": [],
        }

        if not state["in_progress"]:
            result["errors"].append("There is no operation to abort")
            return result

        reset_squash = False
        if operation == "rebase":
            command = ["rebase", "--abort"]
        elif operation == "cherry-pick":
            command = ["cherry-pick", "--abort"]
        elif operation == "revert":
            command = ["revert", "--abort"]
        elif operation == "merge" and state["merge_head"]:
            command = ["merge", "--abort"]
        else:
            # Squash merge (or unmerged entries without an operation): reset
            # the index and the working tree to HEAD.
            command = ["reset", "--merge", "HEAD"]
            reset_squash = bool(state.get("squash"))

        response = self._run_git(command, cwd=repo_path)
        result["output"] = response["output"]
        if not response["ok"]:
            result["errors"].append(
                response["error"] or response["output"] or "Could not abort the operation"
            )
        elif reset_squash:
            # `git reset --merge` leaves SQUASH_MSG behind.
            self._remove_git_file(SQUASH_MSG_FILE, cwd=repo_path)

        refreshed = self.get_conflicts(include_content=False)
        result["state"] = refreshed
        result["success"] = bool(response["ok"] and not refreshed["in_progress"])

        # Restore the local changes stashed before the operation, mirroring the
        # success path: aborting must not make them disappear.
        if result["success"] and state.get("stash_kept"):
            stash = self._pop_pending_stash()
            result["stash_restored"] = stash["restored"]
            result["stash_error"] = stash["error"]
            result["state"] = self.get_conflicts(include_content=False)
        return result


# Made with ❤️ by codx-junior
