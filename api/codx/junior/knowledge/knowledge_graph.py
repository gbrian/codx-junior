import os
import ast
import re
import json
import logging
import time
from typing import Dict, List, Optional

from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)


class DependencyGraph:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.project_path = settings.abs_project_path
        self.graph_file = os.path.join(settings.codx_path, "dependency_graph.json")
        self._graph: Dict = {}

    def build(self, file_paths: List[str]) -> Dict:
        files: Dict[str, Dict] = {}

        for fp in file_paths:
            rel = self._rel(fp)
            imports, external = self._extract_imports(fp)
            files[rel] = {
                "imports": imports,
                "imported_by": [],
                "external_deps": external,
            }

        # Build reverse index
        for rel, entry in files.items():
            for imp in entry["imports"]:
                if imp in files:
                    if rel not in files[imp]["imported_by"]:
                        files[imp]["imported_by"].append(rel)

        self._graph = {
            "version": 1,
            "updated_at": int(time.time()),
            "files": files,
        }
        return self._graph

    def get_file_deps(self, file_path: str) -> Dict:
        rel = self._rel(file_path)
        files = self._graph.get("files", {})
        entry = files.get(rel, {})
        return {
            "imports": entry.get("imports", []),
            "imported_by": entry.get("imported_by", []),
            "external_deps": entry.get("external_deps", []),
        }

    def get_affected_files(self, file_path: str, depth: int = 2) -> List[str]:
        rel = self._rel(file_path)
        files = self._graph.get("files", {})
        visited = set()
        queue = [rel]
        result = []
        current_depth = 0
        while queue and current_depth < depth:
            next_queue = []
            for f in queue:
                for importer in files.get(f, {}).get("imported_by", []):
                    if importer not in visited:
                        visited.add(importer)
                        result.append(importer)
                        next_queue.append(importer)
            queue = next_queue
            current_depth += 1
        return result

    def save(self) -> None:
        try:
            tmp = self.graph_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._graph, fh, indent=2)
            os.replace(tmp, self.graph_file)
            logger.info("Dependency graph saved to %s", self.graph_file)
        except Exception as ex:
            logger.error("Error saving dependency graph: %s", ex)

    def load(self) -> bool:
        if not os.path.isfile(self.graph_file):
            return False
        try:
            with open(self.graph_file, "r", encoding="utf-8") as fh:
                self._graph = json.load(fh)
            return True
        except Exception as ex:
            logger.error("Error loading dependency graph: %s", ex)
            return False

    # ── helpers ───────────────────────────────────────────────────────────────

    def _rel(self, file_path: str) -> str:
        if file_path.startswith(self.project_path):
            rel = file_path[len(self.project_path):]
            return rel.lstrip("/")
        return file_path

    def _extract_imports(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".py":
                return self._extract_py_imports(file_path)
            elif ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
                return self._extract_js_imports(file_path)
            else:
                return self._extract_regex_imports(file_path)
        except Exception as ex:
            logger.debug("Error extracting imports from %s: %s", file_path, ex)
            return [], []

    def _extract_py_imports(self, file_path: str):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return [], []

        internal = []
        external = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resolved = self._resolve_py_module(alias.name)
                    if resolved:
                        if resolved not in internal:
                            internal.append(resolved)
                    else:
                        top = alias.name.split(".")[0]
                        if top not in external:
                            external.append(top)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.level and node.level > 0:
                        resolved = self._resolve_relative_py(file_path, node.module, node.level)
                        if resolved and resolved not in internal:
                            internal.append(resolved)
                    else:
                        resolved = self._resolve_py_module(node.module)
                        if resolved:
                            if resolved not in internal:
                                internal.append(resolved)
                        else:
                            top = node.module.split(".")[0]
                            if top not in external:
                                external.append(top)
                elif node.level and node.level > 0:
                    resolved = self._resolve_relative_py(file_path, "", node.level)
                    if resolved and resolved not in internal:
                        internal.append(resolved)

        return internal, external

    def _resolve_py_module(self, module_name: str) -> Optional[str]:
        parts = module_name.replace(".", "/")
        candidates = [
            f"{parts}.py",
            f"{parts}/__init__.py",
        ]
        for c in candidates:
            if os.path.isfile(os.path.join(self.project_path, c)):
                return c
        return None

    def _resolve_relative_py(self, file_path: str, module: str, level: int) -> Optional[str]:
        base = os.path.dirname(file_path)
        for _ in range(level - 1):
            base = os.path.dirname(base)
        if module:
            parts = module.replace(".", "/")
            candidates = [
                os.path.join(base, f"{parts}.py"),
                os.path.join(base, parts, "__init__.py"),
            ]
        else:
            candidates = [os.path.join(base, "__init__.py")]
        for c in candidates:
            if os.path.isfile(c):
                return self._rel(c)
        return None

    def _extract_js_imports(self, file_path: str):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()

        pattern = r"""(?:import\s+.*?\s+from\s+|require\s*\(\s*)['"]([^'"]+)['"]"""
        matches = re.findall(pattern, source)
        internal = []
        external = []

        file_dir = os.path.dirname(file_path)
        for match in matches:
            if match.startswith("."):
                resolved = self._resolve_js_path(file_dir, match)
                if resolved and resolved not in internal:
                    internal.append(resolved)
            else:
                top = match.split("/")[0]
                if top not in external:
                    external.append(top)

        return internal, external

    def _resolve_js_path(self, base_dir: str, rel_import: str) -> Optional[str]:
        candidates_suffixes = ["", ".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"]
        for suffix in candidates_suffixes:
            candidate = os.path.normpath(os.path.join(base_dir, rel_import + suffix))
            if os.path.isfile(candidate):
                return self._rel(candidate)
        return None

    def _extract_regex_imports(self, file_path: str):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        pattern = r"""(?:import|require|include|use)\s+['"]([^'"]+)['"]"""
        matches = re.findall(pattern, source)
        external = [m for m in matches if not m.startswith(".")]
        return [], external
