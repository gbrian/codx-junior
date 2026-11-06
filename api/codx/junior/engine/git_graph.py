"""
Commit graph and repository inspection engine for codx-junior.

Extends :class:`codx.junior.engine.git_workspace.GitWorkspaceEngine` with the
operations the repository graph view needs:

- :meth:`GitGraphEngine.get_repo_graph`: commits (newest first) with their
  parents and refs, ready to be laid out as a VSCode *Git Graph* style graph.
- :meth:`GitGraphEngine.get_commit_detail`: changed files and patches of a
  single commit, read with a single ``git diff``.
- :meth:`GitGraphEngine.list_remotes`: configured remotes.
- :meth:`GitGraphEngine.rebase_branch`: rebase a branch onto another one (the
  graph's "rebase current branch onto this branch" action).

```mermaid
flowchart TD
    GGE[GitGraphEngine]
    GGE --> get_repo_graph
    GGE --> get_commit_detail
    GGE --> list_remotes
    GGE --> rebase_branch
    GGE --> _graph_refs
    GGE --> _split_patches
    GGE --> _resolve_onto_ref

    get_repo_graph --> _graph_refs
    _graph_refs --> for_each_ref
    get_repo_graph --> git_log
    get_commit_detail --> git_diff
    get_commit_detail --> _split_patches
    rebase_branch --> _resolve_onto_ref
    rebase_branch --> git_rebase
```

Being a :class:`GitWorkspaceEngine`, it also serves every other endpoint of the
git router (branches, working tree, commits, merge, PR lifecycle).

Made with ❤️ by codx-junior
"""

import logging
import re

from typing import Dict, List, Optional

from codx.junior.engine.git_workspace import GitWorkspaceEngine

logger = logging.getLogger(__name__)

# First line of a per-file patch: used to split a full patch into its files
PATCH_SPLIT_PATTERN = re.compile(r"(?m)^(?=diff --git )")

# ``diff --git a/<old> b/<new>`` header of a single file patch
DIFF_HEADER_PATTERN = re.compile(
    r"^diff --git a/(?P<old>.+) b/(?P<new>.+)$", re.MULTILINE
)

# One commit per line: hash, parents, author name, author email, date, subject
COMMIT_FORMAT = "%H|%P|%an|%ae|%ad|%s"

# One ref per line: ref name, target object, peeled object (annotated tags)
REF_FORMAT = "%(refname)|%(objectname)|%(*objectname)"

DEFAULT_GRAPH_LIMIT = 150
MAX_GRAPH_LIMIT = 1000

# Remote used when a branch name is resolved to its remote-tracking ref
DEFAULT_REMOTE = "origin"


class GitGraphEngine(GitWorkspaceEngine):
    """
    Engine for the repository graph: commits, refs, commit details and the
    branch synchronisation (rebase) used by the graph view.

    ```mermaid
    sequenceDiagram
        participant UI as GitGraph.vue
        participant API as git router
        participant Engine as GitGraphEngine
        participant Git as git CLI

        UI->>API: GET /api/git/repo/graph?limit=150
        API->>Engine: get_repo_graph(limit=150)
        Engine->>Git: git for-each-ref refs/heads refs/tags refs/remotes
        Engine->>Git: git log --date-order -n 150 (--branches --tags --remotes)
        Engine-->>API: { commits, branches, default_branch, active_branch }
        API-->>UI: 200 graph payload

        UI->>API: GET /api/git/repo/commit/detail?commit=<sha>
        API->>Engine: get_commit_detail(commit)
        Engine->>Git: git show -s --format=...
        Engine->>Git: git diff <first-parent> <commit>
        Engine-->>API: { commit, stat, files: [{ path, diff, ... }] }
        API-->>UI: 200 commit detail

        UI->>API: POST /api/git/repo/rebase { onto_branch, branch }
        API->>Engine: rebase_branch(onto_branch, branch)
        Engine->>Git: git rebase <onto_ref>
        Engine-->>API: { success, onto_branch, branch, conflicts }
        API-->>UI: 200 result | 400 { detail }
    ```
    """

    # -------------------------------------------------------------------------
    # Remotes
    # -------------------------------------------------------------------------

    def list_remotes(self) -> List[dict]:
        """
        Return the configured git remotes.

        ``git remote -v`` prints one line per (remote, url, kind) tuple, so the
        lines are grouped by remote name into a single entry.

        Returns:
            List of dicts with 'name', 'url', 'fetch_url' and 'push_url'.

        Example:
            >>> engine.list_remotes()
            [{'name': 'origin', 'url': 'git@github.com:acme/app.git',
              'fetch_url': 'git@github.com:acme/app.git',
              'push_url': 'git@github.com:acme/app.git'}]
        """
        result = self._run_git(["remote", "-v"])
        if not result["ok"]:
            return []

        remotes: List[dict] = []
        by_name: Dict[str, dict] = {}

        for line in result["output"].split("\n"):
            parts = line.split()
            if len(parts) < 2:
                continue

            name, url = parts[0], parts[1]
            kind = parts[2] if len(parts) > 2 else "(fetch)"

            entry = by_name.get(name)
            if entry is None:
                entry = {"name": name, "url": url, "fetch_url": "", "push_url": ""}
                by_name[name] = entry
                remotes.append(entry)

            if "push" in kind:
                entry["push_url"] = url
            else:
                entry["fetch_url"] = url
                entry["url"] = url

        return remotes

    # -------------------------------------------------------------------------
    # Commit graph
    # -------------------------------------------------------------------------

    def _graph_refs(self, include_remote: bool = True) -> List[dict]:
        """
        Return every branch and tag with the commit it points to.

        Annotated tags store the commit in the peeled object reference, so
        ``%(*objectname)`` is preferred over ``%(objectname)``. Symbolic refs
        such as ``refs/remotes/origin/HEAD`` are skipped.

        Args:
            include_remote: Include remote-tracking branches.

        Returns:
            List of dicts with 'name', 'type' ('local' | 'remote' | 'tag') and
            'commit'.

        Example:
            >>> engine._graph_refs()
            [{'name': 'main', 'type': 'local', 'commit': 'a1b2c3...'},
             {'name': 'origin/main', 'type': 'remote', 'commit': 'a1b2c3...'}]
        """
        namespaces = ["refs/heads", "refs/tags"]
        if include_remote:
            namespaces.append("refs/remotes")

        result = self._run_git(
            ["for-each-ref", f"--format={REF_FORMAT}"] + namespaces
        )
        if not result["ok"]:
            logger.warning("Could not list refs: %s", result["error"])
            return []

        refs: List[dict] = []
        for line in result["output"].split("\n"):
            if not line.strip() or "|" not in line:
                continue

            refname, object_hash, peeled_hash = (line.split("|") + ["", ""])[:3]
            refname = refname.strip()
            commit = (peeled_hash or object_hash or "").strip()

            if not refname or not commit or refname.endswith("/HEAD"):
                continue

            if refname.startswith("refs/heads/"):
                ref_type, name = "local", refname[len("refs/heads/"):]
            elif refname.startswith("refs/remotes/"):
                ref_type, name = "remote", refname[len("refs/remotes/"):]
            elif refname.startswith("refs/tags/"):
                ref_type, name = "tag", refname[len("refs/tags/"):]
            else:
                continue

            refs.append({"name": name, "type": ref_type, "commit": commit})

        return refs

    def get_repo_graph(
        self,
        branch: Optional[str] = None,
        limit: int = DEFAULT_GRAPH_LIMIT,
        include_remote: bool = True,
    ) -> dict:
        """
        Return the commit graph of the repository.

        Commits are returned newest first (``--date-order``) and carry their
        parents and the refs pointing to them, so the client only has to assign
        lanes. Refs are resolved once for the whole repository, not per commit.

        Args:
            branch: Restrict the graph to a single branch (default: all refs).
            limit: Maximum number of commits returned.
            include_remote: Include remote-tracking branches and commits.

        Returns:
            Dict with 'success', 'repo_path', 'branch', 'default_branch',
            'active_branch', 'include_remote', 'limit', 'branches', 'commits'
            and 'error'. Each commit has 'hash', 'short', 'parents', 'author',
            'date', 'subject', 'refs' and 'is_merge'.

        Example:
            >>> graph = engine.get_repo_graph(limit=2)
            >>> graph["commits"][0]["parents"]
            ['3b5a11ec...']
        """
        repo_path = self._get_repo_root()
        branch = self._sanitize_branch_name(branch) if branch else ""

        try:
            limit = int(limit or DEFAULT_GRAPH_LIMIT)
        except (TypeError, ValueError):
            limit = DEFAULT_GRAPH_LIMIT
        limit = max(1, min(limit, MAX_GRAPH_LIMIT))

        refs = self._graph_refs(include_remote=include_remote)
        refs_by_commit: Dict[str, List[dict]] = {}
        for ref in refs:
            refs_by_commit.setdefault(ref["commit"], []).append(
                {"name": ref["name"], "type": ref["type"]}
            )

        if branch:
            revisions = [branch]
        else:
            revisions = ["--branches", "--tags"]
            if include_remote:
                revisions.append("--remotes")

        args = [
            "log",
            "--date-order",
            "--no-color",
            "--date=iso-strict",
            f"--pretty=format:{COMMIT_FORMAT}",
            "-n",
            str(limit),
        ] + revisions

        result = self._run_git(args, cwd=repo_path)
        commits: List[dict] = []

        for line in result["output"].split("\n"):
            if not line.strip():
                continue

            parts = line.split("|", 5)
            if len(parts) < 6:
                logger.warning("Could not parse graph commit line: %s", line)
                continue

            commit_hash, parents, author_name, author_email, date, subject = parts
            parent_hashes = [parent for parent in parents.split() if parent]

            commits.append({
                "hash": commit_hash,
                "short": commit_hash[:8],
                "parents": parent_hashes,
                "author": {"name": author_name, "email": author_email},
                "date": date,
                "subject": subject,
                "refs": refs_by_commit.get(commit_hash, []),
                "is_merge": len(parent_hashes) > 1,
            })

        return {
            "success": result["ok"],
            "repo_path": repo_path,
            "branch": branch,
            "default_branch": self.get_default_branch(),
            "active_branch": self._sanitize_branch_name(
                self.get_project_current_branch()
            ),
            "include_remote": bool(include_remote),
            "limit": limit,
            "branches": refs,
            "commits": commits,
            "error": "" if result["ok"] else result["error"],
        }

    # -------------------------------------------------------------------------
    # Commit detail
    # -------------------------------------------------------------------------

    def _split_patches(self, patch: str) -> List[dict]:
        """
        Split a full patch into its per-file entries.

        A single ``git diff`` produces every file patch at once, so splitting it
        avoids running one git command per changed file. The status is derived
        from the extended headers (``new file mode``, ``rename from``...).

        Args:
            patch: Output of a diff/show command.

        Returns:
            List of dicts with 'path', 'status', 'additions', 'deletions' and
            'diff'.

        Example:
            >>> engine._split_patches("diff --git a/x.py b/x.py\\n+print(1)")
            [{'path': 'x.py', 'status': 'modified', 'additions': 1,
              'deletions': 0, 'diff': '...'}]
        """
        files: List[dict] = []

        for chunk in PATCH_SPLIT_PATTERN.split(patch or ""):
            if not chunk.strip():
                continue

            match = DIFF_HEADER_PATTERN.search(chunk)
            if not match:
                continue

            old_path = match.group("old").strip()
            new_path = match.group("new").strip()
            path = new_path if new_path and new_path != "/dev/null" else old_path
            if not path or path == "/dev/null":
                continue

            if "new file mode" in chunk:
                status = "added"
            elif "deleted file mode" in chunk:
                status = "deleted"
            elif "rename from" in chunk:
                status = "renamed"
            elif "copy from" in chunk:
                status = "copied"
            else:
                status = "modified"

            counts = self._count_diff_lines(chunk)
            files.append({
                "path": path,
                "status": status,
                "additions": counts["additions"],
                "deletions": counts["deletions"],
                "diff": chunk.rstrip(),
            })

        return files

    def get_commit_detail(self, commit: str, path: Optional[str] = None) -> dict:
        """
        Return the files changed by a commit, with their patches.

        The patch is read with a single ``git diff <first-parent> <commit>``:
        ``git show`` prints nothing for merge commits, and one command per file
        is too slow for large commits. Root commits (no parent) use
        ``git show --format=``, which diffs against the empty tree.

        Args:
            commit: Commit hash (or any revision expression).
            path: Optional file path; only that file is returned.

        Returns:
            Dict with 'success', 'commit' (hash, parents, author, date,
            subject), 'stat', 'total_additions', 'total_deletions', 'files' and
            'error'.

        Example:
            >>> detail = engine.get_commit_detail("a2d3b55")
            >>> detail["files"][0]["path"]
            'aspnetcore/toc.yml'
        """
        commit = (commit or "").strip()
        empty = {
            "success": False,
            "commit": {},
            "stat": "",
            "total_additions": 0,
            "total_deletions": 0,
            "files": [],
            "error": "",
        }

        if not commit:
            return {**empty, "error": "commit is required"}

        repo_root = self._get_repo_root()
        meta = self._run_git([
            "show",
            "-s",
            "--no-color",
            "--date=iso-strict",
            f"--format={COMMIT_FORMAT}",
            commit,
        ], cwd=repo_root)

        if not meta["ok"] or not meta["output"].strip():
            return {
                **empty,
                "error": meta["error"] or f"Commit '{commit}' not found",
            }

        fields = meta["output"].split("|", 5)
        if len(fields) < 6:
            return {**empty, "error": f"Could not parse commit '{commit}'"}

        commit_hash, parents, author_name, author_email, date, subject = fields
        parent_hashes = [parent for parent in parents.split() if parent]

        if parent_hashes:
            args = ["diff", "--no-color", parent_hashes[0], commit_hash]
        else:
            args = ["show", "--format=", "--no-color", commit_hash]

        rel_path = self._to_repo_path(path)
        if rel_path:
            args += ["--", rel_path]

        patch_result = self._run_git(args, cwd=repo_root)
        files = self._split_patches(patch_result["output"])

        additions = sum(file["additions"] for file in files)
        deletions = sum(file["deletions"] for file in files)

        return {
            "success": True,
            "commit": {
                "hash": commit_hash,
                "short": commit_hash[:8],
                "parents": parent_hashes,
                "author": {"name": author_name, "email": author_email},
                "date": date,
                "subject": subject,
                "is_merge": len(parent_hashes) > 1,
            },
            "stat": (
                f"{len(files)} file(s) changed, "
                f"{additions} insertions(+), {deletions} deletions(-)"
            ),
            "total_additions": additions,
            "total_deletions": deletions,
            "files": files,
            "error": "",
        }

    # -------------------------------------------------------------------------
    # Branch synchronisation (rebase)
    # -------------------------------------------------------------------------

    def _resolve_onto_ref(self, onto_branch: str) -> str:
        """
        Resolve the ref a branch is rebased onto.

        Local branches are preferred, with the remote-tracking ref as a
        fallback, so a branch can be rebased onto a ref that only exists on the
        remote (e.g. ``origin/main``).

        Args:
            onto_branch: Branch name, without any remote prefix.

        Returns:
            Resolvable ref name (``main`` or ``origin/main``), or an empty
            string when the branch is unknown.

        Example:
            >>> engine._resolve_onto_ref("main")
            'main'
        """
        if not onto_branch:
            return ""

        if self._ref_exists(f"refs/heads/{onto_branch}"):
            return onto_branch
        if self._ref_exists(f"refs/remotes/{DEFAULT_REMOTE}/{onto_branch}"):
            return f"{DEFAULT_REMOTE}/{onto_branch}"
        return ""

    def rebase_branch(
        self,
        onto_branch: str,
        branch: Optional[str] = None,
        keep_conflicts: bool = False,
    ) -> dict:
        """
        Rebase a branch onto another one (graph "rebase onto this branch").

        Workflow:
            1. Resolve the target branch (`branch` or the checked out one) and
               the ref to rebase onto (`onto_branch`, local or remote-tracking).
            2. Stash local changes so the checkout never fails.
            3. Check out the target branch and ``git rebase <onto_ref>``;
               conflicting rebases are aborted and the conflicts reported,
               unless ``keep_conflicts`` is true: the rebase is then left in
               progress for the conflict resolver.
            4. Restore the stashed changes.

        The rebase rewrites history: existing commits of the target branch get
        new hashes. Nothing is pushed.

        Args:
            onto_branch: Branch (or remote branch) to rebase onto.
            branch: Branch to rebase. Defaults to the checked out branch.
            keep_conflicts: Leave the rebase stopped on conflicts instead of
                aborting it, so the user can resolve them and continue.

        Returns:
            Dict with 'success', 'action', 'branch', 'onto_branch', 'onto_ref',
            'original_branch', 'previous_head', 'commit', 'up_to_date',
            'conflicts', 'conflicted', 'conflict_state', 'steps', 'errors' and
            'repo_path'.

        Example:
            >>> engine.rebase_branch(onto_branch="main")
            {'success': True, 'branch': 'codx-junior/fix-login',
             'onto_branch': 'main', ...}
        """
        repo_path = self._get_repo_root()
        onto = self._sanitize_branch_name(onto_branch) if onto_branch else ""

        original_branch = self._sanitize_branch_name(
            self.get_project_current_branch()
        )
        target = self._sanitize_branch_name(branch) if branch else original_branch

        result = {
            "success": False,
            "action": "rebase",
            "branch": target,
            "onto_branch": onto,
            "onto_ref": "",
            "original_branch": original_branch,
            "previous_head": "",
            "commit": "",
            "up_to_date": False,
            "conflicts": [],
            "conflicted": False,
            "conflict_state": {},
            "stash_kept": False,
            "steps": [],
            "errors": [],
            "repo_path": repo_path,
        }

        if not onto:
            result["errors"].append("onto_branch is required")
            return result

        if not target:
            result["errors"].append(
                "Cannot rebase while HEAD is detached: provide a branch"
            )
            return result

        if target == onto:
            result["errors"].append(
                f"Branch '{onto}' cannot be rebased onto itself"
            )
            return result

        if not self._ref_exists(f"refs/heads/{target}", cwd=repo_path):
            result["errors"].append(f"Branch '{target}' not found")
            return result

        onto_ref = self._resolve_onto_ref(onto)
        result["onto_ref"] = onto_ref
        if not onto_ref:
            result["errors"].append(f"Branch '{onto}' not found")
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

        head = self._run_git(["rev-parse", "HEAD"], cwd=repo_path)
        previous_head = head["output"] if head["ok"] else ""
        result["previous_head"] = previous_head

        stashed = False
        # A rebase left in progress keeps the auto-stash: popping it on top of
        # the unresolved rebase would fail.
        keep_stash = False
        try:
            # Keep local work safe: both checkout and rebase need a clean tree
            if status["dirty"]:
                stash = self._run_git([
                    "stash", "push", "-u",
                    "-m", f"codx-junior: auto-stash before rebasing {target}",
                ], cwd=repo_path)
                result["steps"].append({"name": "stash", **stash})
                if not stash["ok"]:
                    result["errors"].append(
                        f"Could not stash local changes: {stash['error']}"
                    )
                    return result
                stashed = True

            if original_branch != target:
                checkout = self._run_git(["checkout", target], cwd=repo_path)
                result["steps"].append({"name": "checkout", **checkout})
                if not checkout["ok"]:
                    result["errors"].append(
                        f"Could not checkout '{target}': {checkout['error']}"
                    )
                    return result

            rebase = self._run_git(["rebase", onto_ref], cwd=repo_path)
            result["steps"].append({"name": "rebase", **rebase})
            if not rebase["ok"]:
                conflicts = self._run_git(
                    ["diff", "--name-only", "--diff-filter=U"], cwd=repo_path
                )
                result["conflicts"] = [
                    f.strip() for f in conflicts["output"].split("\n") if f.strip()
                ]
                result["errors"].append(
                    f"Could not rebase '{target}' onto '{onto}': "
                    f"{rebase['error'] or rebase['output']}"
                )
                if keep_conflicts and result["conflicts"]:
                    # Leave the rebase in progress so the conflict resolver can
                    # stage the resolutions and run `git rebase --continue`.
                    result["conflicted"] = True
                    keep_stash = stashed
                    result["stash_kept"] = stashed
                    get_conflicts = getattr(self, "get_conflicts", None)
                    if callable(get_conflicts):
                        result["conflict_state"] = get_conflicts(
                            include_content=False
                        )
                    return result

                # Never leave the repository in the middle of a rebase
                self._run_git(["rebase", "--abort"], cwd=repo_path)
                return result

            new_head = self._run_git(["rev-parse", "HEAD"], cwd=repo_path)
            if new_head["ok"]:
                result["commit"] = new_head["output"]
            result["up_to_date"] = bool(
                previous_head and result["commit"] == previous_head
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
                        "rebase is continued or aborted",
                    }
                )
            result["success"] = not result["errors"]

# Made with ❤️ by codx-junior