"""
Query layer for the project atlas.

The public surface is deliberately small and deterministic:

* ``map``    — orient: domains, entry points, key files, reading order;
* ``locate`` — find: ranked ``path:line`` evidence for a symbol, string, route,
  doc or file pattern (this replaces grep/glob/semantic search);
* ``trace``  — follow imports/calls/routes from a symbol;
* ``impact`` — reverse dependencies, tests and docs before a change;
* ``health`` — coverage, freshness and index warnings.

Ranking is local and explainable. It encodes the heuristics a developer applies
to a grep result: definitions beat references, source beats tests/docs for an
implementation question, central files beat leaves, exact names beat fuzzy
text, and generated/vendor paths are penalised.
"""

from __future__ import annotations

import fnmatch
import logging
import math
import os
import re
import time
from collections import deque
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .indexer import AtlasIndexer
from .models import AtlasHealth, AtlasPacket, Evidence
from .related import child_paths
from .store import AtlasStore

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "me", "my", "of", "on",
    "or", "our", "please", "show", "tell", "that", "the", "their", "this",
    "to", "was", "we", "what", "when", "where", "which", "who", "why",
    "will", "with", "would", "you", "your", "find", "locate", "code",
    "file", "files", "project", "please", "def", "class", "function",
    "const", "let", "var", "return", "import", "from",
}

KIND_FILTERS = {
    "symbol": {"symbol"},
    "function": {"symbol"},
    "class": {"symbol"},
    "method": {"symbol"},
    "route": {"route"},
    "endpoint": {"route"},
    "doc": {"doc"},
    "docs": {"doc"},
    "file": {"file"},
    "test": {"file"},
    "config": {"file"},
}

ENTRY_POINT_NAMES = {
    "main.py", "app.py", "server.py", "__init__.py", "router.py",
    "index.ts", "index.tsx", "index.js", "main.ts", "main.tsx", "main.js",
    "app.ts", "app.tsx", "app.js", "App.vue", "router.ts", "router.js",
    "run_api.sh", "entrypoint.sh", "Dockerfile", "package.json", "pyproject.toml",
}

PENALIZED_PATH_PARTS = {
    "vendor", "dist", "build", "node_modules", "coverage", ".next", ".nuxt",
    "generated", "gen", "third_party", "third-party",
}
PENALIZED_SUFFIXES = (
    ".min.js", ".min.css", ".map", ".lock", "package-lock.json",
    "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock",
)


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_./-]*|\d+", (text or "").lower())
    result: List[str] = []
    for word in words:
        word = word.strip("./-")
        if not word or word in STOPWORDS:
            continue
        if word not in result:
            result.append(word)
    return result


def _is_glob(query: str) -> bool:
    return any(char in query for char in "*?[")


def _is_identifier(query: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.\-]*", query or ""))


def _fts_query(tokens: Sequence[str]) -> str:
    # Quote each token: code identifiers contain characters FTS treats as
    # syntax. OR keeps recall high; ranking decides relevance.
    return " OR ".join(f'"{token}"' for token in tokens if token)


def _normalise_path(path: str) -> str:
    return os.path.normpath(path).replace(os.sep, "/")


class ProjectAtlas:
    """Atlas facade bound to one project's settings."""

    def __init__(self, settings: Any):
        self.settings = settings
        self.root = os.path.abspath(getattr(settings, "abs_project_path", "") or ".")
        codx_path = getattr(settings, "codx_path", None) or os.path.join(self.root, ".codx")
        self.codx_path = os.path.abspath(codx_path)
        self.db_path = os.path.join(self.codx_path, "atlas", "atlas.db")
        self.indexer = AtlasIndexer(
            root=self.root,
            db_path=self.db_path,
            project_name=getattr(settings, "project_name", "") or os.path.basename(self.root),
            max_files=int(getattr(settings, "project_atlas_max_files", 5000) or 5000),
            ttl_seconds=int(getattr(settings, "project_atlas_ttl_seconds", 5) or 5),
            # Child projects have their own atlas; index only this project.
            exclude_paths=child_paths(settings, self.root),
        )
        self._store: Optional[AtlasStore] = None
        self._file_cache: Dict[str, List[str]] = {}
        self._in_degree_cache: Dict[str, int] = {}
        self._degrees_loaded = False
        self._error: Optional[str] = None

    # ── lifecycle ───────────────────────────────────────────────────────────

    def __enter__(self) -> "ProjectAtlas":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        if self._store is not None:
            try:
                self._store.close()
            finally:
                self._store = None

    def ensure(self, force: bool = False) -> AtlasStore:
        if self._store is None:
            self._degrees_loaded = False
            self._in_degree_cache.clear()
            try:
                self._store = self.indexer.ensure(force=force)
                self._load_degrees(self._store)
                self._error = None
            except Exception as ex:
                self._error = str(ex)
                logger.exception("Atlas: cannot open index for %s", self.root)
                raise
        return self._store

    def rebuild(self) -> AtlasHealth:
        if self._store is not None:
            self._store.close()
            self._store = None
        self.ensure(force=True)
        return self.health()

    # ── map ─────────────────────────────────────────────────────────────────

    def map(self, query: str = "", path: str = "", limit: int = 12) -> AtlasPacket:
        store = self.ensure()
        stats = store.stats()
        domains = store.domain_counts()
        if query:
            focus = self.locate(query=query, path=path, limit=min(max(limit, 3), 10))
            domain_hits = [
                domain for domain in domains
                if query.lower() in str(domain.get("domain", "")).lower()
            ]
            if domain_hits:
                domains = domain_hits + [d for d in domains if d not in domain_hits]
        else:
            focus = None

        central = store.top_central_files(limit=max(limit, 20))
        if path:
            prefix = _normalise_path(path).strip("/")
            domains = [
                domain for domain in domains
                if str(domain.get("domain") or "").startswith(prefix.split("/")[0])
            ]
            central = [
                row for row in central
                if str(row.get("path") or "").startswith(prefix + "/")
                or str(row.get("path") or "") == prefix
            ]
        central_by_domain: Dict[str, List[Dict[str, Any]]] = {}
        for row in central:
            domain = self._domain_of(str(row.get("path", "")))
            central_by_domain.setdefault(domain, []).append(row)

        evidence: List[Evidence] = []
        domains_lines: List[str] = []
        for domain in domains[:limit]:
            name = str(domain.get("domain") or "root")
            files = int(domain.get("files") or 0)
            key_files = central_by_domain.get(name, [])[:3]
            if not key_files:
                key_files = [
                    {"path": row["path"], "degree": 0}
                    for row in store.conn.execute(
                        "SELECT path FROM files WHERE domain = ? "
                        "AND role = 'source' ORDER BY path LIMIT 3",
                        (name,),
                    )
                ]
            key_paths = ", ".join(f"`{row['path']}`" for row in key_files) or "—"
            domains_lines.append(f"| `{name}` | {files} | {key_paths} |")
            if len(evidence) < limit:
                for row in key_files[:1]:
                    evidence.append(Evidence(
                        path=row["path"],
                        start_line=1,
                        end_line=1,
                        kind="file",
                        name=os.path.basename(row["path"]),
                        why=f"key file in domain `{name}`",
                        score=float(row.get("degree") or 0),
                    ))

        entry_points = self._entry_points(store)
        if focus and focus.evidence:
            evidence = focus.evidence[: max(3, limit // 2)] + evidence
            # De-duplicate while preserving order.
            seen: Set[str] = set()
            evidence = [
                item for item in evidence
                if not (item.location in seen or seen.add(item.location))
            ]

        reading_order: List[str] = []
        for row in entry_points[:8]:
            if row["path"] not in reading_order:
                reading_order.append(row["path"])
        for item in evidence:
            if item.path not in reading_order:
                reading_order.append(item.path)
        for row in central:
            if row["path"] not in reading_order:
                reading_order.append(row["path"])
        reading_order = reading_order[:limit]

        generation = self._generation(store)
        lines = [
            f"> atlas map: {stats['files']} files, {stats['symbols']} symbols, "
            f"{stats['domains']} domains | {generation.get('commit', 'no-git')}"
            f"{' +dirty' if generation.get('dirty') else ''}",
            "",
            "| Domain | Files | Key files |",
            "| --- | ---: | --- |",
        ]
        lines.extend(domains_lines)
        if entry_points:
            lines.extend(["", "### Entry points"])
            for row in entry_points[:8]:
                lines.append(f"- `{row['path']}` — imported by {row['degree']} file(s)")
        if reading_order:
            lines.extend(["", "### Reading order"])
            for index, location in enumerate(reading_order, 1):
                lines.append(f"{index}. `{location}`")
        if focus and focus.evidence:
            lines.extend(["", "### Query focus"])
            lines.extend(f"- `{item.location}` — {item.why}" for item in focus.evidence[:5])

        return AtlasPacket(
            query=query or "*",
            intent="map",
            answer=(
                f"Project map for `{getattr(self.settings, 'project_name', '') or self.root}`: "
                f"{stats['domains']} domains, {stats['files']} indexed files."
            ),
            evidence=evidence[:limit],
            reading_order=reading_order,
            confidence=0.9 if stats["files"] else 0.2,
            generation=generation,
            gaps=[] if stats["files"] else ["The atlas indexed no files."],
            next_probes=[
                "project_locate('<feature or symbol>')",
                "project_health()",
            ],
            body="\n".join(lines),
        )

    # ── locate ──────────────────────────────────────────────────────────────

    def locate(
        self,
        query: str,
        path: str = "",
        include: str = "",
        regex: bool = False,
        case_sensitive: bool = False,
        limit: int = 8,
        include_tests: bool = True,
        kind: str = "",
    ) -> AtlasPacket:
        query = (query or "").strip()
        if not query:
            return AtlasPacket(
                query="",
                intent="locate",
                answer="Empty query.",
                gaps=["Pass a symbol, string, route, doc title or file pattern."],
            )

        store = self.ensure()
        tokens = _tokenize(query)
        candidates: Dict[str, Dict[str, Any]] = {}
        query_lower = query.lower()
        kind_set = KIND_FILTERS.get((kind or "").lower())
        query_path = _normalise_path(path) if path else ""

        def allowed(candidate: Dict[str, Any]) -> bool:
            if query_path and not _normalise_path(candidate["path"]).startswith(query_path):
                return False
            if include and not (
                fnmatch.fnmatch(candidate["path"], include)
                or fnmatch.fnmatch(os.path.basename(candidate["path"]), include)
            ):
                return False
            if not include_tests and candidate.get("role") == "test":
                return False
            if kind_set:
                if candidate.get("kind") not in kind_set:
                    return False
                kind_name = (kind or "").lower()
                if kind_name == "test" and candidate.get("role") != "test":
                    return False
                if kind_name == "config" and candidate.get("role") != "config":
                    return False
            return True

        def add(candidate: Dict[str, Any]) -> None:
            if not allowed(candidate):
                return
            key = (
                candidate["path"],
                candidate.get("kind"),
                int(candidate.get("start_line") or 1),
            )
            existing = candidates.get(key)
            if existing is None or candidate.get("base_score", 0) > existing.get("base_score", 0):
                candidates[key] = candidate

        # 1) Symbol / route / doc names and paths.
        for node in store.search_nodes(tokens, limit=300):
            add(self._candidate_from_node(store, node, base_score=2.0))

        # 2) File paths.
        for row in store.search_files(tokens, limit=200):
            add(self._candidate_from_file(row, base_score=1.0))

        # 3) Full-text body. bm25 rank is ascending (best first).
        for index, row in enumerate(store.search_fts(_fts_query(tokens), limit=200)):
            file_row = store.file(row["path"]) or {"path": row["path"], "role": "source"}
            candidate = self._candidate_from_file(file_row, base_score=max(0.5, 5.0 - index * 0.15))
            candidate["fts_snippet"] = row.get("snippet") or ""
            add(candidate)
            # A symbol whose name is in the query is a stronger landmark than
            # a body match in the same file.
            for node in store.nodes_for_path(row["path"], kinds=("symbol", "route", "doc")):
                if node.get("kind") == "doc" and file_row.get("role") == "doc":
                    add(self._candidate_from_node(store, node, base_score=3.5))
                elif any(token in str(node.get("name", "")).lower() for token in tokens):
                    add(self._candidate_from_node(store, node, base_score=4.0))

        # 4) Explicit file globs.
        if _is_glob(query):
            for file_path in store.file_paths():
                if fnmatch.fnmatch(file_path, query) or fnmatch.fnmatch(
                    os.path.basename(file_path), query
                ):
                    add(self._candidate_from_file(
                        store.file(file_path) or {"path": file_path, "role": "source"},
                        base_score=8.0,
                    ))

        # 5) Exact phrase / regex content search. FTS tokenisation is the wrong
        # tool for an error message or a regex; scan the candidate set first and
        # only fall back to the whole project when nothing was found.
        needs_scan = regex or (
            " " in query and len(query) >= 4
        ) or ("_" in query and len(tokens) == 1 and not candidates)
        if needs_scan:
            scan_paths = [item["path"] for item in candidates.values()]
            if not scan_paths:
                scan_paths = [row["path"] for row in store.files()]
            for file_path in scan_paths[: 800 if regex else 250]:
                match = self._scan_file(
                    file_path,
                    query,
                    regex=regex,
                    case_sensitive=case_sensitive,
                )
                if not match:
                    continue
                line, snippet = match
                candidate = self._candidate_from_file(
                    store.file(file_path) or {"path": file_path, "role": "source"},
                    base_score=6.0 if regex else 7.0,
                )
                candidate["match_line"] = line
                candidate["match_snippet"] = snippet
                add(candidate)

        if not candidates:
            return AtlasPacket(
                query=query,
                intent="locate",
                answer=f"No indexed match for `{query}`.",
                gaps=[
                    "The atlas found no symbol, path, route, document or content match.",
                    "Try a shorter identifier, a file extension filter, or `project_map()` first.",
                ],
                next_probes=[f"project_health()", f"project_map(query='{query[:40]}')"],
                confidence=0.1,
                generation=self._generation(store),
            )

        ranked = sorted(
            candidates.values(),
            key=lambda candidate: self._score(store, candidate, tokens, query, regex),
            reverse=True,
        )
        top = ranked[: max(1, min(int(limit or 8), 20))]
        evidence = [self._evidence(store, candidate, query, regex) for candidate in top]
        stale = any(item.stale for item in evidence)
        confidence = self._confidence(top, query, stale)
        reading_order = []
        for item in evidence:
            if item.path not in reading_order:
                reading_order.append(item.location)
        top_item = evidence[0]
        answer = (
            f"Best match: `{top_item.location}` — {top_item.kind}"
            f"{' `' + top_item.name + '`' if top_item.name and top_item.name not in top_item.path else ''}."
        )
        gaps: List[str] = []
        if confidence < 0.55:
            gaps.append("Low confidence: verify the top evidence before editing.")
        if not any(item.kind in ("symbol", "route") for item in evidence):
            gaps.append("No symbol matched; results are file/content locations.")
        if include_tests and not any(item.meta.get("role") == "test" for item in evidence):
            gaps.append("No test file matched; use `project_impact` before changing code.")

        next_probes = []
        if top_item.meta.get("node_key"):
            next_probes.append(f"project_trace('{top_item.name or query}')")
        next_probes.append(f"project_impact(['{top_item.path}'])")
        if confidence < 0.55:
            next_probes.append(f"project_locate('{query}', regex=True)")

        return AtlasPacket(
            query=query,
            intent="locate",
            answer=answer,
            evidence=evidence,
            reading_order=reading_order,
            gaps=gaps,
            next_probes=next_probes[:3],
            confidence=confidence,
            generation=self._generation(store),
            stale=stale,
        )

    # ── trace ───────────────────────────────────────────────────────────────

    def trace(self, symbol: str, direction: str = "out", depth: int = 2) -> AtlasPacket:
        store = self.ensure()
        located = self.locate(symbol, limit=3, kind="symbol")
        if not located.evidence:
            located = self.locate(symbol, limit=3)
        if not located.evidence:
            return AtlasPacket(
                query=symbol,
                intent="trace",
                answer=f"No indexed symbol/path for `{symbol}`.",
                gaps=["Use `project_map()` for orientation, then `project_locate()`."],
                confidence=0.1,
                generation=self._generation(store),
            )
        start = located.evidence[0]
        node_key = start.meta.get("node_key") or f"file:{start.path}"
        start_node = store.node_by_key(node_key)
        if not start_node:
            return AtlasPacket(
                query=symbol,
                intent="trace",
                answer=f"`{symbol}` matched `{start.location}` but its graph node is missing.",
                evidence=[start],
                gaps=["The index is inconsistent; run `project_health()` or reindex."],
                confidence=0.2,
                generation=self._generation(store),
                stale=True,
            )

        direction = (direction or "out").lower()
        edge_kinds = {
            "out": ("calls", "imports", "handles", "contains"),
            "in": ("calls", "imports", "tests", "documents"),
            "both": ("calls", "imports", "handles", "tests", "documents"),
        }.get(direction, ("calls", "imports", "handles"))

        visited: Dict[int, int] = {int(start_node["id"]): 0}
        queue: deque = deque([(start_node, 0)])
        reached: List[Tuple[Dict[str, Any], int, str]] = []
        while queue:
            node, node_depth = queue.popleft()
            if node_depth >= max(1, min(int(depth or 2), 4)):
                continue
            if direction in ("out", "both"):
                edges = store.edges_from(int(node["id"]), kinds=edge_kinds)
            else:
                edges = store.edges_to(int(node["id"]), kinds=edge_kinds)
            for edge in edges:
                other = store.node(int(edge["other_id"]))
                if not other or int(other["id"]) in visited:
                    continue
                visited[int(other["id"])] = node_depth + 1
                reached.append((other, node_depth + 1, str(edge["kind"])))
                queue.append((other, node_depth + 1))
                if len(reached) >= 40:
                    break
            if len(reached) >= 40:
                break

        evidence: List[Evidence] = [start]
        for node, node_depth, edge_kind in reached[:20]:
            evidence.append(Evidence(
                path=node["path"],
                start_line=int(node.get("start_line") or 1),
                end_line=int(node.get("end_line") or 1),
                kind=str(node.get("kind") or "node"),
                name=str(node.get("name") or ""),
                why=f"{edge_kind} edge, depth {node_depth}",
                score=float(max(1, 10 - node_depth * 2)),
                meta={"node_key": node["key"], "role": self._role_of(store, node["path"])},
            ))
        answer = (
            f"Trace from `{start.location}` (`{start.kind}` `{start.name}`): "
            f"{len(evidence) - 1} related node(s) via {direction} edges."
        )
        return AtlasPacket(
            query=symbol,
            intent="trace",
            answer=answer,
            evidence=evidence,
            reading_order=self._unique_locations(evidence),
            gaps=[] if len(evidence) > 1 else ["No graph edges found; the symbol may be a leaf."],
            next_probes=[f"project_impact(['{start.path}'])"],
            confidence=0.8 if len(evidence) > 1 else 0.55,
            generation=self._generation(store),
        )

    # ── impact ──────────────────────────────────────────────────────────────

    def impact(self, paths: Sequence[str], depth: int = 2) -> AtlasPacket:
        store = self.ensure()
        if isinstance(paths, str):
            paths = [paths]
        requested = [str(path).strip() for path in (paths or []) if str(path).strip()]
        if not requested:
            return AtlasPacket(
                query="",
                intent="impact",
                answer="No paths provided.",
                gaps=["Pass one or more project-relative files."],
            )
        evidence: List[Evidence] = []
        seen: Set[str] = set()
        missing: List[str] = []
        dependents: Dict[str, int] = {}
        for path in requested:
            rel = _normalise_path(path).lstrip("./")
            if not os.path.isfile(os.path.join(self.root, rel)):
                missing.append(rel)
                continue
            file_node = store.node_by_key(f"file:{rel}")
            if not file_node:
                missing.append(rel)
                continue
            visited = {int(file_node["id"])}
            queue = deque([(file_node, 0)])
            count = 0
            while queue:
                node, node_depth = queue.popleft()
                if node_depth >= max(1, min(int(depth or 2), 4)):
                    continue
                for edge in store.edges_to(int(node["id"]), kinds=("imports", "calls", "tests", "documents")):
                    other = store.node(int(edge["other_id"]))
                    if not other or int(other["id"]) in visited:
                        continue
                    visited.add(int(other["id"]))
                    queue.append((other, node_depth + 1))
                    count += 1
                    location = f"{other['path']}:{int(other.get('start_line') or 1)}"
                    if location in seen:
                        continue
                    seen.add(location)
                    evidence.append(Evidence(
                        path=other["path"],
                        start_line=int(other.get("start_line") or 1),
                        end_line=int(other.get("end_line") or 1),
                        kind=str(other.get("kind") or "file"),
                        name=str(other.get("name") or ""),
                        why=f"{edge['kind']} dependency, depth {node_depth + 1}",
                        score=float(max(1, 10 - node_depth * 2)),
                        meta={"node_key": other["key"], "role": self._role_of(store, other["path"])},
                    ))
                    if len(evidence) >= 40:
                        break
            dependents[rel] = count
        evidence.sort(key=lambda item: item.score, reverse=True)
        tests = [item for item in evidence if item.meta.get("role") == "test"]
        docs = [item for item in evidence if item.kind == "doc"]
        top_dependents = max(dependents.values()) if dependents else 0
        risk = "high" if top_dependents >= 10 else "medium" if top_dependents >= 3 else "low"
        answer = (
            f"Impact of {', '.join(f'`{path}`' for path in requested)}: "
            f"{len(evidence)} dependent node(s), {len(tests)} test(s), "
            f"{len(docs)} doc page(s), risk **{risk}**."
        )
        gaps = []
        if missing:
            gaps.append("Not indexed: " + ", ".join(f"`{path}`" for path in missing))
        if not tests:
            gaps.append("No test edge found; verify with the project test command.")
        return AtlasPacket(
            query=", ".join(requested),
            intent="impact",
            answer=answer,
            evidence=evidence[:20],
            reading_order=self._unique_locations(evidence[:20]),
            gaps=gaps,
            next_probes=[
                "project_locate('<changed symbol>')",
                "project_trace('<changed symbol>')",
            ],
            confidence=0.85 if evidence else 0.4,
            generation=self._generation(store),
        )

    # ── health ──────────────────────────────────────────────────────────────

    def health(self) -> AtlasHealth:
        try:
            store = self.ensure()
        except Exception as ex:
            return AtlasHealth(
                project=getattr(self.settings, "project_name", ""),
                root=self.root,
                db_path=self.db_path,
                warnings=[f"Index unavailable: {ex}"],
            )
        stats = store.stats()
        meta = store.all_meta()
        warnings = list(meta.get("warnings") or [])
        if meta.get("truncated"):
            warnings.append("File cap reached; some files are not indexed.")
        if self._git_head() and meta.get("commit") and self._git_head() != meta.get("commit"):
            warnings.append("Working tree HEAD moved after the last build; refresh required.")
        return AtlasHealth(
            project=str(meta.get("project") or getattr(self.settings, "project_name", "")),
            root=self.root,
            db_path=self.db_path,
            built_at=float(meta.get("built_at") or 0),
            commit=str(meta.get("commit") or ""),
            dirty=bool(meta.get("dirty")),
            index_version=int(meta.get("index_version") or 0),
            files=stats["files"],
            symbols=stats["symbols"],
            routes=stats["routes"],
            docs=stats["docs"],
            tests=stats["tests"],
            edges=stats["edges"],
            domains=stats["domains"],
            db_bytes=os.path.getsize(self.db_path) if os.path.isfile(self.db_path) else 0,
            duration_seconds=float(meta.get("duration_seconds") or 0),
            truncated=bool(meta.get("truncated")),
            warnings=warnings,
        )

    # ── candidate helpers ───────────────────────────────────────────────────

    def _candidate_from_node(
        self, store: AtlasStore, node: Dict[str, Any], base_score: float = 0.0
    ) -> Dict[str, Any]:
        file_row = store.file(node["path"]) or {}
        return {
            "path": node["path"],
            "kind": str(node.get("kind") or "symbol"),
            "name": str(node.get("name") or ""),
            "qualname": str(node.get("qualname") or ""),
            "start_line": int(node.get("start_line") or 1),
            "end_line": int(node.get("end_line") or 1),
            "node_key": node.get("key"),
            "role": file_row.get("role") or "source",
            "base_score": base_score,
            "mtime": float(file_row.get("mtime") or 0),
        }

    def _candidate_from_file(self, row: Dict[str, Any], base_score: float = 0.0) -> Dict[str, Any]:
        path = str(row.get("path") or "")
        role = row.get("role") or "source"
        return {
            "path": path,
            "kind": "doc" if role == "doc" else "file",
            "name": "" if role == "doc" else os.path.basename(path),
            "qualname": "",
            "start_line": 1,
            "end_line": 1,
            "node_key": f"file:{path}",
            "role": row.get("role") or "source",
            "base_score": base_score,
            "mtime": float(row.get("mtime") or 0),
        }

    def _score(
        self,
        store: AtlasStore,
        candidate: Dict[str, Any],
        tokens: Sequence[str],
        query: str,
        regex: bool = False,
    ) -> float:
        path = str(candidate.get("path") or "").lower()
        name = str(candidate.get("name") or "").lower()
        basename = os.path.basename(path)
        query_lower = query.lower()
        score = float(candidate.get("base_score") or 0.0)

        if name and name == query_lower:
            score += 14
        elif query_lower and query_lower in name:
            score += 8
        if query_lower and query_lower in path:
            score += 5
        for token in tokens:
            if token in name:
                score += 4
            if token in basename:
                score += 3
            if token in path:
                score += 2

        kind = candidate.get("kind")
        if kind == "symbol":
            score += 3
        elif kind == "route":
            score += 4
        elif kind == "doc":
            score += 1
        elif kind == "file":
            score -= 1

        role = candidate.get("role")
        if role == "source":
            score += 2
        elif role == "test":
            score -= 1
        elif role == "doc":
            score -= 0.5
        elif role == "config":
            score -= 1

        if candidate.get("match_line"):
            score += 6 if regex else 7
        if candidate.get("fts_snippet"):
            score += 2

        # Centrality: a file imported by many others is a better landmark.
        degree = self._in_degree_cache.get(path, 0)
        if degree:
            score += min(4.0, math.log2(1 + degree))

        # Recency is a tiny prior, never a reason to prefer a file.
        mtime = float(candidate.get("mtime") or 0)
        if mtime and time.time() - mtime < 14 * 86400:
            score += 0.5

        if any(part in path.split("/") for part in PENALIZED_PATH_PARTS):
            score -= 10
        if any(path.endswith(suffix) for suffix in PENALIZED_SUFFIXES):
            score -= 12
        if candidate.get("role") == "test" and not query_lower.startswith("test"):
            score -= 1
        return score

    def _evidence(
        self,
        store: AtlasStore,
        candidate: Dict[str, Any],
        query: str,
        regex: bool = False,
    ) -> Evidence:
        path = candidate["path"]
        start = int(candidate.get("start_line") or 1)
        end = int(candidate.get("end_line") or start)
        name = str(candidate.get("name") or "")
        stale = False
        snippet = ""
        if candidate.get("match_line"):
            start = int(candidate["match_line"])
            end = start
            snippet = str(candidate.get("match_snippet") or "")
        elif candidate.get("kind") in ("symbol", "doc"):
            lines = self._read_lines(path)
            if lines:
                if start > len(lines):
                    stale = True
                else:
                    window = "\n".join(lines[max(0, start - 1): min(len(lines), end)])
                    is_vue_component = (
                        path.lower().endswith(".vue")
                        and name == os.path.splitext(os.path.basename(path))[0]
                    )
                    if (
                        name
                        and name not in window
                        and not path.lower().endswith(".md")
                        and not is_vue_component
                    ):
                        relocated = self._relocate_symbol(path, name)
                        if relocated:
                            start = relocated
                            end = relocated
                            stale = True
                        else:
                            stale = True
            snippet = self._snippet(path, start, end)
        elif candidate.get("kind") == "route":
            lines = self._read_lines(path)
            if lines and start > len(lines):
                stale = True
            snippet = self._snippet(path, start, end)
        else:
            if not candidate.get("match_line"):
                match = self._scan_file(path, query, regex=regex)
                if match:
                    start, snippet = match
                    end = start
            if not snippet:
                snippet = self._snippet(path, start, min(end, start + 2))
        role = candidate.get("role") or "source"
        why_parts = []
        if name and name.lower() == query.lower():
            why_parts.append("exact name")
        if candidate.get("match_line"):
            why_parts.append("content match")
        if candidate.get("fts_snippet"):
            why_parts.append("text match")
        if role == "test":
            why_parts.append("test")
        elif role == "doc":
            why_parts.append("documentation")
        degree = self._in_degree_cache.get(path.lower(), 0)
        if degree:
            why_parts.append(f"imported by {degree}")
        if stale:
            why_parts.append("line drift detected")
        return Evidence(
            path=path,
            start_line=start,
            end_line=max(start, end),
            kind=str(candidate.get("kind") or "file"),
            name=name,
            why=", ".join(why_parts) or "atlas match",
            score=self._score(store, candidate, _tokenize(query), query, regex),
            snippet=snippet,
            stale=stale,
            meta={
                "node_key": candidate.get("node_key"),
                "role": role,
                "query": query,
            },
        )

    def _scan_file(
        self,
        path: str,
        query: str,
        regex: bool = False,
        case_sensitive: bool = False,
    ) -> Optional[Tuple[int, str]]:
        lines = self._read_lines(path)
        if not lines:
            return None
        flags = 0 if case_sensitive else re.IGNORECASE
        if regex:
            try:
                matcher = re.compile(query, flags)
            except re.error:
                return None
        else:
            matcher = None
            needle = query if case_sensitive else query.lower()
        for index, line in enumerate(lines, 1):
            matched = (
                matcher.search(line) is not None
                if matcher is not None
                else (needle in (line if case_sensitive else line.lower()))
            )
            if matched:
                context_start = max(0, index - 2)
                context_end = min(len(lines), index + 1)
                snippet = "\n".join(
                    f"{line_no + 1}: {lines[line_no][:180]}"
                    for line_no in range(context_start, context_end)
                )
                return index, snippet
        return None

    def _relocate_symbol(self, path: str, name: str) -> Optional[int]:
        if not name:
            return None
        lines = self._read_lines(path)
        patterns = (
            rf"\bdef\s+{re.escape(name)}\b",
            rf"\bclass\s+{re.escape(name)}\b",
            rf"\bfunction\s+{re.escape(name)}\b",
            rf"\b(?:const|let|var)\s+{re.escape(name)}\b",
        )
        for pattern in patterns:
            matcher = re.compile(pattern)
            for index, line in enumerate(lines, 1):
                if matcher.search(line):
                    return index
        return None

    def _snippet(self, path: str, start: int, end: int) -> str:
        lines = self._read_lines(path)
        if not lines:
            return ""
        start = max(1, start)
        end = min(len(lines), max(start, end))
        end = min(end, start + 4)
        return "\n".join(
            f"{line_no}: {lines[line_no - 1][:180]}"
            for line_no in range(start, end + 1)
        )

    def _read_lines(self, path: str) -> List[str]:
        if path in self._file_cache:
            return self._file_cache[path]
        abs_path = os.path.join(self.root, path)
        try:
            if os.path.getsize(abs_path) > 512 * 1024:
                self._file_cache[path] = []
                return []
            with open(abs_path, "r", encoding="utf-8", errors="replace") as handle:
                lines = handle.read().splitlines()
        except OSError:
            lines = []
        self._file_cache[path] = lines
        return lines

    # ── other helpers ───────────────────────────────────────────────────────

    def _load_degrees(self, store: AtlasStore) -> None:
        """Cache reverse-dependency counts once per query (one SQL pass)."""
        if self._degrees_loaded:
            return
        try:
            for row in store.conn.execute(
                "SELECT dst.path AS path, COUNT(*) AS degree "
                "FROM edges e JOIN nodes dst ON dst.id = e.dst "
                "WHERE e.kind IN ('imports', 'calls', 'documents', 'tests') "
                "GROUP BY dst.path"
            ):
                self._in_degree_cache[str(row["path"]).lower()] = int(row["degree"])
        except Exception:
            logger.debug("Atlas: cannot load degree cache", exc_info=True)
        self._degrees_loaded = True

    def _confidence(self, ranked: Sequence[Dict[str, Any]], query: str, stale: bool) -> float:
        if not ranked:
            return 0.1
        top = self._score(None, ranked[0], _tokenize(query), query)  # type: ignore[arg-type]
        second = self._score(None, ranked[1], _tokenize(query), query) if len(ranked) > 1 else 0.0  # type: ignore[arg-type]
        margin = max(0.0, top - second)
        base = 0.45 + min(0.35, top / 45.0) + min(0.12, margin / 30.0)
        if str(ranked[0].get("name", "")).lower() == query.lower():
            base += 0.08
        if stale:
            base -= 0.15
        return round(max(0.05, min(0.96, base)), 2)

    def _generation(self, store: AtlasStore) -> Dict[str, Any]:
        meta = store.all_meta()
        return {
            "commit": str(meta.get("commit") or "")[:12],
            "dirty": bool(meta.get("dirty")),
            "built_at": int(float(meta.get("built_at") or 0)),
            "files": int(meta.get("file_count") or 0),
            "index_version": int(meta.get("index_version") or 0),
        }

    def _entry_points(self, store: AtlasStore) -> List[Dict[str, Any]]:
        priority = {
            "app.py": 100, "main.py": 95, "main.ts": 90, "main.tsx": 90,
            "main.js": 90, "server.py": 85, "run_api.sh": 80,
            "index.ts": 70, "index.tsx": 70, "index.js": 70,
            "__init__.py": 10, "router.py": 60, "App.vue": 65,
        }
        rows = []
        for row in store.conn.execute(
            "SELECT path FROM files WHERE role = 'source' ORDER BY path"
        ):
            path = row["path"]
            name = os.path.basename(path)
            if name in ENTRY_POINT_NAMES:
                rows.append({
                    "path": path,
                    "degree": store.in_degree(path),
                    "priority": priority.get(name, 20),
                })
        rows.sort(
            key=lambda item: (item["priority"], item["degree"]),
            reverse=True,
        )
        unique = []
        seen_names = set()
        for row in rows:
            name = os.path.basename(row["path"])
            if name in seen_names:
                continue
            seen_names.add(name)
            unique.append(row)
        return unique

    @staticmethod
    def _unique_locations(evidence: Iterable[Evidence]) -> List[str]:
        result = []
        for item in evidence:
            if item.path not in result:
                result.append(item.location)
        return result

    @staticmethod
    def _domain_of(path: str) -> str:
        parts = path.replace(os.sep, "/").split("/")
        if len(parts) == 1:
            return "root"
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "codx":
            return "api"
        return parts[0]

    def _role_of(self, store: AtlasStore, path: str) -> str:
        row = store.file(path)
        return str((row or {}).get("role") or "source")

    def _git_head(self) -> str:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "-C", self.root, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""


def atlas_db_path(settings: Any) -> str:
    """Return the SQLite path for a project without opening the index."""
    root = os.path.abspath(getattr(settings, "abs_project_path", "") or ".")
    codx_path = getattr(settings, "codx_path", None) or os.path.join(root, ".codx")
    return os.path.join(os.path.abspath(codx_path), "atlas", "atlas.db")


def atlas_ready(settings: Any) -> bool:
    """Return True only when a completed build exists (meta.built_at is set)."""
    if settings is None or not bool(getattr(settings, "project_atlas_enabled", False)):
        return False
    db_path = atlas_db_path(settings)
    if not os.path.isfile(db_path):
        return False
    try:
        import sqlite3

        connection = sqlite3.connect(db_path, timeout=1)
        try:
            row = connection.execute(
                "SELECT value FROM meta WHERE key = 'built_at'"
            ).fetchone()
        finally:
            connection.close()
        return bool(row and row[0])
    except Exception:
        return False
