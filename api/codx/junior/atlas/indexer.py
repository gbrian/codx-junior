"""
Incremental codebase indexer for the project atlas.

The indexer is intentionally conservative and dependency-free:

* files come from ``git ls-files`` (so ``.gitignore`` is honored) with an
  ``os.walk`` fallback;
* Python uses ``ast`` for real line ranges, classes, functions and routes;
* JS/TS/Vue use focused regexes (definitions, imports and routes);
* Markdown uses frontmatter plus headings, so docs can be cited and linked back
  to source files.

The first build is synchronous and fast (a few seconds for a normal project).
Later calls compare the git HEAD and the working-tree status and reindex only
the changed files. A full rebuild happens when the HEAD moved or more than
``max_incremental_files`` changed at once.
"""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import logging
import os
import re
import subprocess
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .constants import (
    ATLAS_INDEX_VERSION,
    DEFAULT_MAX_FILES,
    DEFAULT_TTL_SECONDS,
)
from .store import AtlasStore

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_BODY_CHARS = 120_000
MAX_INCREMENTAL_FILES = 40
MAX_CALL_EDGES = 20_000

CODE_EXT = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue",
    ".sql", ".sh", ".bash",
}
DOC_EXT = {".md", ".mdx", ".rst"}
CONFIG_EXT = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}
INDEXED_EXT = CODE_EXT | DOC_EXT | CONFIG_EXT

IGNORED_PARTS = {
    ".git", ".codx", "node_modules", ".venv", "venv", "__pycache__",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".worktrees", "vendor",
}
IGNORED_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "uv.lock", "bun.lockb", "composer.lock", "Cargo.lock",
}
IGNORED_SUFFIXES = (
    ".min.js", ".min.css", ".map", ".lock", ".pyc", ".pyo",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf",
    ".zip", ".gz", ".tar", ".whl", ".so", ".dylib", ".dll",
)

PY_ROUTE_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "route"}

_PY_CLASS_RE = re.compile(r"^(\s*)class\s+([A-Za-z_]\w*)\b")
_PY_DEF_RE = re.compile(r"^(\s*)(?:async\s+)?def\s+([A-Za-z_]\w*)\b")
_JS_FUNCTION_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"
)
_JS_CLASS_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)"
)
_JS_CONST_FN_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
    r"(?:async\s*)?(?:\([^)]*\)\s*=>|function\b|\()"
)
_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+.*?\s+from\s+|require\s*\(\s*)['"]([^'"]+)['"]"""
)
_JS_ROUTE_RE = re.compile(
    r"""(?:router|app|api)\.(get|post|put|delete|patch)\(\s*['"`]([^'"`]+)"""
)
_MD_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _run_git(root: str, *args: str, timeout: int = 30) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "-C", root, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as ex:
        logger.debug("git %s failed in %s: %s", args, root, ex)
        return None
    if result.returncode != 0:
        return None
    return result.stdout


class AtlasIndexer:
    """Build and refresh the atlas database for one project root."""

    def __init__(
        self,
        root: str,
        db_path: str,
        project_name: str = "",
        max_files: int = DEFAULT_MAX_FILES,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        exclude_paths: Sequence[str] = (),
    ):
        self.root = os.path.abspath(root)
        self.db_path = db_path
        self.project_name = project_name or os.path.basename(self.root)
        self.max_files = max(100, int(max_files or DEFAULT_MAX_FILES))
        # Child projects own their atlas: do not index their files here.
        self.exclude_paths = tuple(
            str(path).replace(os.sep, "/").strip("/")
            for path in (exclude_paths or ())
            if str(path).strip("/")
        )
        self.ttl_seconds = max(0, int(ttl_seconds or 0))
        self._calls_seen = 0
        self._pending_calls: List[Dict[str, Any]] = []
        self._pending_edges: List[Dict[str, Any]] = []
        self._symbol_names: Dict[str, List[Dict[str, str]]] = {}
        self.truncated = False
        self.warnings: List[str] = []
        self._git_top_level: Optional[str] = None
        self._wiki_source_map: Optional[Dict[str, str]] = None

    # ── public entry point ──────────────────────────────────────────────────

    def ensure(self, force: bool = False) -> AtlasStore:
        """Open the store and make sure it reflects the current working tree."""
        started = time.time()
        store = AtlasStore(self.db_path)
        try:
            paths = store.file_paths()
            index_version = int(store.get_meta("index_version") or 0)
            if paths and index_version != ATLAS_INDEX_VERSION:
                logger.info(
                    "Atlas: index version %s -> %s, rebuilding",
                    index_version,
                    ATLAS_INDEX_VERSION,
                )
                store.reset_schema()
                paths = []
            if force or not paths:
                self._build_full(store, started)
                return store

            checked_at = float(store.get_meta("checked_at") or 0)
            if not force and time.time() - checked_at < self.ttl_seconds:
                return store
            store.set_meta("checked_at", time.time())
            store.conn.commit()

            head = self._git_head()
            indexed_head = str(store.get_meta("commit") or "")
            if head and indexed_head and head != indexed_head:
                logger.info("Atlas: HEAD changed, rebuilding %s", self.root)
                self._build_full(store, started)
                return store

            changed = self._git_changes()
            current = self._list_files()
            if changed is None:
                # No git: compare mtimes with the stored inventory.
                changed = self._mtime_changes(store, current)
            if changed and len(changed) > MAX_INCREMENTAL_FILES:
                logger.info(
                    "Atlas: %d changed files, rebuilding instead of patching",
                    len(changed),
                )
                self._build_full(store, started)
                return store
            if changed:
                self._apply_incremental(store, changed, current)
                self._finish_build(store, started)
            else:
                self._prune_missing(store, current)
                store.set_meta("dirty", False)
                store.set_meta("changed_files", 0)
                store.conn.commit()
            return store
        except Exception:
            store.close()
            raise

    def build(self, force: bool = True) -> AtlasStore:
        """Public alias used by the rebuild endpoint."""
        return self.ensure(force=force)

    # ── full build ──────────────────────────────────────────────────────────

    def _build_full(self, store: AtlasStore, started: float) -> None:
        self.truncated = False
        self.warnings = []
        self._pending_calls = []
        self._pending_edges = []
        self._symbol_names = {}
        self._calls_seen = 0

        paths = self._list_files()
        store.begin_bulk()
        store.clear()
        # Phase 1: create every file node first, so import/doc/test edges can
        # resolve regardless of indexing order.
        for rel_path in paths:
            store.upsert_file_node(
                rel_path,
                os.path.basename(rel_path),
                1,
                self._language(rel_path),
            )
        # Phase 2: parse contents. A single transaction keeps the build fast:
        # committing per file costs a WAL fsync per file.
        for rel_path in paths:
            try:
                self._index_file(store, rel_path, fresh=True)
            except Exception as ex:  # pragma: no cover - one bad file must not kill the index
                logger.warning("Atlas: cannot index %s: %s", rel_path, ex)
                self.warnings.append(f"{rel_path}: {ex}")
        store.conn.commit()
        self._resolve_pending(store)
        store.end_bulk()
        self._finish_build(store, started)

    def _apply_incremental(
        self,
        store: AtlasStore,
        changed: Sequence[str],
        current: Sequence[str],
    ) -> None:
        self._pending_calls = []
        self._pending_edges = []
        self._symbol_names = {}
        self._calls_seen = 0
        for rel_path in changed:
            rel_path = os.path.normpath(rel_path)
            if rel_path not in current:
                store.delete_file(rel_path)
                continue
            store.upsert_file_node(
                rel_path,
                os.path.basename(rel_path),
                1,
                self._language(rel_path),
            )
            try:
                self._index_file(store, rel_path, fresh=False)
            except Exception as ex:  # pragma: no cover
                logger.exception("Atlas: cannot update %s: %s", rel_path, ex)
                self.warnings.append(f"{rel_path}: {ex}")
        store.conn.commit()
        self._resolve_pending(store)
        self._prune_missing(store, current)
        store.set_meta("dirty", bool(self._git_changes()))
        store.set_meta("changed_files", len(changed))

    def _finish_build(self, store: AtlasStore, started: float) -> None:
        stats = store.stats()
        duration = time.time() - started
        store.set_meta("index_version", ATLAS_INDEX_VERSION)
        store.set_meta("built_at", time.time())
        store.set_meta("checked_at", time.time())
        store.set_meta("duration_seconds", round(duration, 3))
        store.set_meta("commit", self._git_head() or "")
        store.set_meta("dirty", bool(self._git_changes()))
        store.set_meta("file_count", stats["files"])
        store.set_meta("truncated", self.truncated)
        store.set_meta("warnings", self.warnings[-20:])
        store.set_meta("project", self.project_name)
        store.conn.commit()

    # ── file discovery ──────────────────────────────────────────────────────

    def _list_files(self) -> List[str]:
        paths: List[str] = []
        tracked = _run_git(self.root, "ls-files", "-z")
        if tracked is not None:
            paths = [self._relative_to_root(item) for item in tracked.split("\0") if item]
            others = _run_git(self.root, "ls-files", "--others", "--exclude-standard", "-z")
            if others:
                paths.extend(
                    self._relative_to_root(item) for item in others.split("\0") if item
                )
        if not paths:
            paths = self._walk_files()

        candidates = []
        for raw in paths:
            rel_path = os.path.normpath(raw or "")
            if not rel_path or rel_path.startswith("..") or not self._is_candidate(rel_path):
                continue
            candidates.append(rel_path)

        candidates = sorted(
            set(candidates),
            key=lambda path: (self._role_priority(path), path),
        )
        if len(candidates) > self.max_files:
            self.truncated = True
            candidates = candidates[: self.max_files]
        return candidates

    def _relative_to_root(self, raw_path: str) -> str:
        """Normalize a git path to a path relative to this project root."""
        candidate = raw_path
        if not os.path.isabs(candidate):
            direct = os.path.join(self.root, candidate)
            if os.path.exists(direct):
                return os.path.relpath(direct, self.root)
            if self._git_top_level is None:
                self._git_top_level = (
                    _run_git(self.root, "rev-parse", "--show-toplevel") or ""
                ).strip()
            if self._git_top_level:
                candidate = os.path.join(self._git_top_level, candidate)
        return os.path.relpath(candidate, self.root)

    def _walk_files(self) -> List[str]:
        found = []
        for current_root, dirs, files in os.walk(self.root):
            dirs[:] = [
                directory for directory in dirs
                if directory not in IGNORED_PARTS
                and not directory.startswith(".")
            ]
            for file_name in files:
                abs_path = os.path.join(current_root, file_name)
                found.append(os.path.relpath(abs_path, self.root))
        return found

    def _is_candidate(self, rel_path: str) -> bool:
        if self.exclude_paths:
            posix_path = rel_path.replace(os.sep, "/")
            if any(
                posix_path == prefix or posix_path.startswith(f"{prefix}/")
                for prefix in self.exclude_paths
            ):
                return False
        parts = rel_path.split(os.sep)
        if any(part in IGNORED_PARTS for part in parts):
            return False
        name = parts[-1]
        if name in IGNORED_NAMES or name.startswith("."):
            return False
        lower = name.lower()
        if lower.endswith(IGNORED_SUFFIXES):
            return False
        ext = os.path.splitext(lower)[1]
        if ext not in INDEXED_EXT:
            return False
        try:
            abs_path = os.path.join(self.root, rel_path)
            if os.path.getsize(abs_path) > MAX_FILE_BYTES:
                return False
        except OSError:
            return False
        return True

    def _role_priority(self, rel_path: str) -> int:
        role = self._role(rel_path)
        return {"source": 0, "test": 1, "doc": 2, "config": 3}.get(role, 4)

    # ── one file ────────────────────────────────────────────────────────────

    def _index_file(self, store: AtlasStore, rel_path: str, fresh: bool = False) -> None:
        abs_path = os.path.join(self.root, rel_path)
        text = self._read_text(abs_path)
        if text is None:
            store.delete_file(rel_path)
            return
        lines = text.splitlines()
        language = self._language(rel_path)
        role = self._role(rel_path)
        tree = None
        if language == "python":
            try:
                tree = ast.parse(text, filename=rel_path)
            except SyntaxError:
                tree = None
        summary = self._summary(rel_path, text, language, tree)
        stat = os.stat(abs_path)
        record = {
            "path": rel_path,
            "lang": language,
            "role": role,
            "domain": self._domain(rel_path),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "sha1": hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest(),
            "summary": summary,
            "indexed_at": time.time(),
        }
        store.upsert_file(record)
        store.upsert_file_node(rel_path, os.path.basename(rel_path), len(lines), language)

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        if language == "python":
            nodes, edges = self._parse_python(rel_path, text, lines, tree)
        elif language in ("javascript", "typescript", "vue"):
            nodes, edges = self._parse_javascript(rel_path, text, lines, language)
        elif language == "markdown":
            nodes, edges = self._parse_markdown(rel_path, text, lines)

        # Every symbol is contained by its file node.
        for node in nodes:
            if node.get("kind") in ("symbol", "route", "doc"):
                edges.append({
                    "src_key": f"file:{rel_path}",
                    "dst_key": node["key"],
                    "kind": "contains",
                    "confidence": 1.0,
                    "line": node.get("start_line") or 1,
                })

        fts_name = " ".join(
            [rel_path, summary]
            + [node.get("name", "") for node in nodes if node.get("name")]
        )
        body = text[:MAX_BODY_CHARS]
        store.replace_symbols(
            rel_path, nodes, edges, body, fts_name, fresh=fresh
        )

        # Deferred cross-file edges.
        self._pending_edges.extend(self._deferred_edges(rel_path, role, edges))
        for node in nodes:
            if node.get("kind") == "symbol":
                self._symbol_names.setdefault(node["name"], []).append({
                    "key": node["key"],
                    "path": rel_path,
                })
        if language == "python":
            self._collect_python_calls(rel_path, text, tree)

    # ── Python ──────────────────────────────────────────────────────────────

    def _parse_python(
        self,
        rel_path: str,
        text: str,
        lines: Sequence[str],
        tree: Optional[ast.AST] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        if tree is None:
            try:
                tree = ast.parse(text, filename=rel_path)
            except SyntaxError:
                return nodes, edges

        def visit(node: ast.AST, parents: List[Tuple[str, str]]) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    kind = "class" if isinstance(child, ast.ClassDef) else "function"
                    qualname = ".".join([name for _, name in parents] + [child.name])
                    key = f"symbol:{rel_path}:{qualname}"
                    start = int(getattr(child, "lineno", 1) or 1)
                    end = int(getattr(child, "end_lineno", start) or start)
                    parent_key = parents[-1][0] if parents else ""
                    nodes.append({
                        "key": key,
                        "kind": "symbol",
                        "name": child.name,
                        "qualname": qualname,
                        "start_line": start,
                        "end_line": end,
                        "parent_key": parent_key,
                        "lang": "python",
                        "meta": {
                            "python_kind": kind,
                            "decorators": [
                                self._safe_unparse(decorator)
                                for decorator in getattr(child, "decorator_list", [])
                            ],
                        },
                    })
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        route = self._python_route(child, rel_path, start)
                        if route:
                            route_key = f"route:{rel_path}:{route['name']}:{start}"
                            nodes.append({
                                "key": route_key,
                                "kind": "route",
                                "name": route["name"],
                                "qualname": route["name"],
                                "start_line": start,
                                "end_line": start,
                                "parent_key": "",
                                "lang": "python",
                                "meta": {"framework": "python"},
                            })
                            edges.append({
                                "src_key": route_key,
                                "dst_key": key,
                                "kind": "handles",
                                "confidence": 1.0,
                                "line": start,
                            })
                    visit(child, parents + [(key, child.name)])
                else:
                    visit(child, parents)

        visit(tree, [])

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = self._resolve_py_module(alias.name)
                    if target:
                        edges.append(self._import_edge(rel_path, target, getattr(node, "lineno", 0)))
            elif isinstance(node, ast.ImportFrom):
                target = self._resolve_py_from(rel_path, node)
                if target:
                    edges.append(self._import_edge(rel_path, target, getattr(node, "lineno", 0)))
        return nodes, edges

    def _collect_python_calls(
        self, rel_path: str, text: str, tree: Optional[ast.AST] = None
    ) -> None:
        if self._calls_seen >= MAX_CALL_EDGES:
            return
        if tree is None:
            try:
                tree = ast.parse(text, filename=rel_path)
            except SyntaxError:
                return

        def direct_calls(node: ast.AST, caller_qualname: str) -> None:
            """Collect calls in one function body, not in nested functions."""
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if isinstance(child, ast.Call):
                    name = self._call_name(child.func)
                    if name:
                        self._pending_calls.append({
                            "path": rel_path,
                            "caller_qualname": caller_qualname,
                            "name": name,
                            "line": int(getattr(child, "lineno", 0) or 0),
                        })
                        self._calls_seen += 1
                        if self._calls_seen >= MAX_CALL_EDGES:
                            return
                direct_calls(child, caller_qualname)

        def visit(node: ast.AST, parents: List[str]) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qualname = ".".join(parents + [child.name])
                    direct_calls(child, qualname)
                    visit(child, parents + [child.name])
                elif isinstance(child, ast.ClassDef):
                    visit(child, parents + [child.name])
                else:
                    visit(child, parents)

        visit(tree, [])

    @staticmethod
    def _call_name(func: ast.AST) -> str:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return ""

    def _python_route(self, node: ast.AST, rel_path: str, line: int) -> Optional[Dict[str, str]]:
        for decorator in getattr(node, "decorator_list", []):
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            name = self._safe_unparse(target)
            method = name.rsplit(".", 1)[-1].lower()
            if method not in PY_ROUTE_METHODS:
                continue
            route_path = ""
            if isinstance(decorator, ast.Call) and decorator.args:
                first = decorator.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    route_path = first.value
            if not route_path:
                continue
            http_method = "ROUTE" if method == "route" else method.upper()
            return {"name": f"{http_method} {route_path}"}
        return None

    def _resolve_py_module(self, module: str) -> Optional[str]:
        parts = module.replace(".", "/")
        for candidate in (f"{parts}.py", f"{parts}/__init__.py"):
            if os.path.isfile(os.path.join(self.root, candidate)):
                return candidate
        return None

    def _resolve_py_from(self, rel_path: str, node: ast.ImportFrom) -> Optional[str]:
        if not node.module and not node.level:
            return None
        if node.level:
            base = os.path.dirname(rel_path)
            for _ in range(max(0, int(node.level) - 1)):
                base = os.path.dirname(base)
            module = (node.module or "").replace(".", "/")
            candidate = os.path.normpath(os.path.join(base, module)) if module else base
            for path in (f"{candidate}.py", os.path.join(candidate, "__init__.py")):
                rel = os.path.relpath(os.path.join(self.root, path), self.root)
                if os.path.isfile(os.path.join(self.root, rel)):
                    return rel
            return None
        return self._resolve_py_module(node.module or "")

    @staticmethod
    def _safe_unparse(node: ast.AST) -> str:
        try:
            return ast.unparse(node)
        except Exception:  # pragma: no cover - old Python
            return type(node).__name__

    # ── JavaScript / TypeScript / Vue ───────────────────────────────────────

    def _parse_javascript(
        self,
        rel_path: str,
        text: str,
        lines: Sequence[str],
        language: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        offset = 0
        script = text
        if language == "vue":
            match = re.search(r"<script[^>]*>(.*?)</script>", text, re.DOTALL | re.IGNORECASE)
            if match:
                script = match.group(1)
                offset = text[: match.start(1)].count("\n")
            else:
                script = ""
        for index, line in enumerate(script.splitlines(), 1):
            if line.lstrip().startswith(("//", "*", "/*")):
                continue
            match = (
                _JS_CLASS_RE.match(line)
                or _JS_FUNCTION_RE.match(line)
                or _JS_CONST_FN_RE.match(line)
            )
            if not match:
                continue
            name = match.group(1)
            start = index + offset
            key = f"symbol:{rel_path}:{name}"
            if any(node["key"] == key for node in nodes):
                continue
            nodes.append({
                "key": key,
                "kind": "symbol",
                "name": name,
                "qualname": name,
                "start_line": start,
                "end_line": start,
                "parent_key": "",
                "lang": language,
                "meta": {"javascript_kind": "class" if _JS_CLASS_RE.match(line) else "function"},
            })
        for match in _JS_ROUTE_RE.finditer(script):
            method = match.group(1).upper()
            route_path = match.group(2)
            line = script[: match.start()].count("\n") + 1 + offset
            name = f"{method} {route_path}"
            nodes.append({
                "key": f"route:{rel_path}:{name}:{line}",
                "kind": "route",
                "name": name,
                "qualname": name,
                "start_line": line,
                "end_line": line,
                "parent_key": "",
                "lang": language,
                "meta": {"framework": "javascript"},
            })
        for match in _JS_IMPORT_RE.finditer(script):
            target = self._resolve_js_import(rel_path, match.group(1))
            if target:
                line = script[: match.start()].count("\n") + 1 + offset
                edges.append(self._import_edge(rel_path, target, line))
        if language == "vue":
            # The component itself is a useful landmark.
            component = os.path.splitext(os.path.basename(rel_path))[0]
            key = f"symbol:{rel_path}:{component}"
            if not any(node["key"] == key for node in nodes):
                nodes.append({
                    "key": key,
                    "kind": "symbol",
                    "name": component,
                    "qualname": component,
                    "start_line": 1,
                    "end_line": max(1, len(lines)),
                    "parent_key": "",
                    "lang": "vue",
                    "meta": {"javascript_kind": "component"},
                })
        return nodes, edges

    def _resolve_js_import(self, rel_path: str, specifier: str) -> Optional[str]:
        if not specifier.startswith("."):
            if specifier.startswith("@/"):
                specifier = "./" + specifier[2:]
            elif specifier.startswith("~/"):
                specifier = "./" + specifier[2:]
            else:
                return None
        base = os.path.normpath(os.path.join(os.path.dirname(rel_path), specifier))
        candidates = [
            base,
            f"{base}.ts",
            f"{base}.tsx",
            f"{base}.js",
            f"{base}.jsx",
            f"{base}.vue",
            f"{base}.mjs",
            f"{base}.cjs",
            os.path.join(base, "index.ts"),
            os.path.join(base, "index.tsx"),
            os.path.join(base, "index.js"),
            os.path.join(base, "index.vue"),
        ]
        for candidate in candidates:
            if candidate.startswith(".."):
                continue
            if os.path.isfile(os.path.join(self.root, candidate)):
                return candidate
        return None

    # ── Markdown ────────────────────────────────────────────────────────────

    def _parse_markdown(
        self, rel_path: str, text: str, lines: Sequence[str]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        frontmatter = self._frontmatter(text)
        title = str(frontmatter.get("title") or "").strip()
        if not title:
            for line in lines[:40]:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        title = title or os.path.splitext(os.path.basename(rel_path))[0]
        page_key = f"doc:{rel_path}:page"
        nodes.append({
            "key": page_key,
            "kind": "doc",
            "name": title,
            "qualname": title,
            "start_line": 1,
            "end_line": max(1, len(lines)),
            "parent_key": "",
            "lang": "markdown",
            "meta": {
                "description": frontmatter.get("description") or "",
                "tags": frontmatter.get("tags") or [],
            },
        })
        headings = []
        for index, line in enumerate(lines, 1):
            match = _MD_HEADING_RE.match(line)
            if match:
                headings.append((index, match.group(2).strip()))
        for position, (line, heading) in enumerate(headings):
            end = headings[position + 1][0] - 1 if position + 1 < len(headings) else len(lines)
            nodes.append({
                "key": f"doc:{rel_path}:{heading}:{line}",
                "kind": "doc",
                "name": heading,
                "qualname": heading,
                "start_line": line,
                "end_line": max(line, end),
                "parent_key": page_key,
                "lang": "markdown",
                "meta": {"heading": True},
            })
        sources = frontmatter.get("source") or frontmatter.get("sources") or frontmatter.get("file")
        if not sources:
            sources = self._wiki_sources().get(rel_path)
        if isinstance(sources, str):
            sources = [sources]
        for source in sources if isinstance(sources, list) else []:
            target = self._resolve_doc_source(rel_path, str(source))
            if target:
                edges.append({
                    "src_key": page_key,
                    "dst_key": f"file:{target}",
                    "kind": "documents",
                    "confidence": 1.0,
                    "line": 1,
                })
        return nodes, edges

    def _wiki_sources(self) -> Dict[str, str]:
        """Map generated wiki pages to source files (legacy wiki_settings)."""
        if self._wiki_source_map is not None:
            return self._wiki_source_map
        self._wiki_source_map = {}
        codx_path = os.path.dirname(os.path.dirname(self.db_path))
        settings_path = os.path.join(codx_path, "wiki_settings.json")
        if not os.path.isfile(settings_path):
            return self._wiki_source_map
        try:
            with open(settings_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return self._wiki_source_map

        def visit(categories):
            for category in categories or []:
                for entry in category.get("files") or []:
                    source = str(entry.get("path") or "").lstrip("/")
                    wiki_file = str(entry.get("wiki_file") or "")
                    if not source or not wiki_file:
                        continue
                    try:
                        rel_wiki = os.path.relpath(wiki_file, self.root).replace(os.sep, "/")
                    except ValueError:
                        continue
                    if rel_wiki.startswith(".."):
                        continue
                    if os.path.isfile(os.path.join(self.root, rel_wiki)) and os.path.isfile(
                        os.path.join(self.root, source)
                    ):
                        self._wiki_source_map[rel_wiki] = source
                visit(category.get("children") or [])

        visit(data.get("categories") or [])
        return self._wiki_source_map

    def _resolve_doc_source(self, rel_path: str, source: str) -> Optional[str]:
        source = source.strip().strip("`'\"")
        if not source:
            return None
        candidates = [
            os.path.normpath(source),
            os.path.normpath(os.path.join(os.path.dirname(rel_path), source)),
        ]
        for candidate in candidates:
            if candidate.startswith(".."):
                continue
            if os.path.isfile(os.path.join(self.root, candidate)):
                return candidate
        return None

    @staticmethod
    def _frontmatter(text: str) -> Dict[str, Any]:
        match = _FRONTMATTER_RE.match(text)
        if not match:
            return {}
        data: Dict[str, Any] = {}
        for raw_line in match.group(1).splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip().strip("'\"")
            if value.startswith("[") and value.endswith("]"):
                value = [
                    item.strip().strip("'\"")
                    for item in value[1:-1].split(",")
                    if item.strip()
                ]
            data[key] = value
        return data

    # ── shared helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _import_edge(rel_path: str, target: str, line: int) -> Dict[str, Any]:
        return {
            "src_key": f"file:{rel_path}",
            "dst_key": f"file:{target}",
            "kind": "imports",
            "confidence": 1.0,
            "line": int(line or 0),
        }

    def _deferred_edges(
        self, rel_path: str, role: str, edges: Sequence[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        deferred = []
        if role == "test":
            for edge in edges:
                if edge.get("kind") == "imports":
                    deferred.append({
                        "src_key": f"file:{rel_path}",
                        "dst_key": edge["dst_key"],
                        "kind": "tests",
                        "confidence": 0.8,
                        "line": edge.get("line") or 0,
                    })
        return deferred

    def _resolve_pending(self, store: AtlasStore) -> None:
        by_name: Dict[str, List[Dict[str, str]]] = {}
        for row in store.conn.execute(
            "SELECT key, name, path FROM nodes WHERE kind = 'symbol'"
        ):
            by_name.setdefault(row["name"], []).append({
                "key": row["key"],
                "path": row["path"],
            })
        edges: List[Dict[str, Any]] = []
        for call in self._pending_calls:
            candidates = by_name.get(call["name"]) or []
            if len(candidates) == 1:
                target = candidates[0]
            else:
                same_file = [item for item in candidates if item["path"] == call["path"]]
                if len(same_file) != 1:
                    continue
                target = same_file[0]
            edges.append({
                "src_key": f"symbol:{call['path']}:{call['caller_qualname']}"
                if call.get("caller_qualname")
                else f"file:{call['path']}",
                "dst_key": target["key"],
                "kind": "calls",
                "confidence": 0.7,
                "line": call.get("line") or 0,
            })
        edges.extend(self._pending_edges)
        if edges:
            store.add_edges(edges)
        self._pending_calls = []
        self._pending_edges = []

    def _mtime_changes(self, store: AtlasStore, current: Sequence[str]) -> List[str]:
        known = {row["path"]: row for row in store.files()}
        changed = []
        for rel_path in current:
            record = known.get(rel_path)
            try:
                mtime = os.path.getmtime(os.path.join(self.root, rel_path))
            except OSError:
                continue
            if not record or float(record.get("mtime") or 0) < mtime:
                changed.append(rel_path)
        changed.extend(path for path in known if path not in current)
        return changed

    def _git_head(self) -> str:
        output = _run_git(self.root, "rev-parse", "HEAD")
        return (output or "").strip()

    def _git_changes(self) -> Optional[List[str]]:
        output = _run_git(self.root, "status", "--porcelain")
        if output is None:
            return None
        changed: Set[str] = set()
        for line in output.splitlines():
            if len(line) < 4:
                continue
            status = line[:2]
            payload = line[3:].strip()
            if " -> " in payload:
                old, new = payload.split(" -> ", 1)
                changed.add(self._relative_to_root(old.strip().strip('"')))
                changed.add(self._relative_to_root(new.strip().strip('"')))
            elif payload:
                changed.add(self._relative_to_root(payload.strip('"')))
        return sorted(
            path for path in changed
            if path and self._is_candidate(path)
        )

    def _prune_missing(self, store: AtlasStore, current: Sequence[str]) -> None:
        current_set = set(current)
        for path in store.file_paths():
            if path not in current_set:
                store.delete_file(path)

    def _read_text(self, abs_path: str) -> Optional[str]:
        try:
            if os.path.getsize(abs_path) > MAX_FILE_BYTES:
                return None
            with open(abs_path, "rb") as handle:
                raw = handle.read()
        except OSError:
            return None
        if b"\x00" in raw:
            return None
        return raw.decode("utf-8", "replace")

    @staticmethod
    def _language(rel_path: str) -> str:
        ext = os.path.splitext(rel_path)[1].lower()
        return {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".mjs": "javascript",
            ".cjs": "javascript",
            ".vue": "vue",
            ".md": "markdown",
            ".mdx": "markdown",
            ".rst": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".sh": "shell",
            ".bash": "shell",
            ".sql": "sql",
        }.get(ext, ext.lstrip(".") or "text")

    @staticmethod
    def _role(rel_path: str) -> str:
        parts = [part.lower() for part in rel_path.split(os.sep)]
        name = parts[-1]
        if (
            any(part in {"test", "tests", "__tests__", "spec", "e2e"} for part in parts[:-1])
            or name.startswith("test_")
            or ".test." in name
            or ".spec." in name
        ):
            return "test"
        ext = os.path.splitext(name)[1]
        if ext in DOC_EXT or name.startswith("readme"):
            return "doc"
        if ext in CONFIG_EXT or name in {
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            "Makefile", "Procfile",
        }:
            return "config"
        return "source"

    @staticmethod
    def _domain(rel_path: str) -> str:
        parts = rel_path.split(os.sep)
        if len(parts) == 1:
            return "root"
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "codx":
            return "api"
        return parts[0]

    def _summary(
        self, rel_path: str, text: str, language: str, tree: Optional[ast.AST] = None
    ) -> str:
        if language == "markdown":
            frontmatter = self._frontmatter(text)
            summary = str(frontmatter.get("description") or "").strip()
            if summary:
                return summary[:300]
            for line in text.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith(("#", "---", "```")):
                    return stripped[:300]
            return ""
        if language == "python":
            docstring = ast.get_docstring(tree) if tree is not None else None
            if docstring:
                return " ".join(docstring.split())[:300]
        for line in text.splitlines()[:40]:
            stripped = line.strip()
            if stripped.startswith(("//", "#", "/*", "*")):
                return stripped.lstrip("/*# ").strip()[:300]
        return ""


def index_project(
    root: str,
    db_path: str,
    project_name: str = "",
    force: bool = False,
    max_files: int = DEFAULT_MAX_FILES,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    exclude_paths: Sequence[str] = (),
) -> AtlasStore:
    """Convenience entry point used by tests and non-settings callers."""
    return AtlasIndexer(
        root=root,
        db_path=db_path,
        project_name=project_name,
        max_files=max_files,
        ttl_seconds=ttl_seconds,
        exclude_paths=exclude_paths,
    ).ensure(force=force)
