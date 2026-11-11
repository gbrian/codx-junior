"""
SQLite storage for the project atlas.

One database per project: ``<project .codx>/atlas/atlas.db``. It contains the
file inventory, symbol/route/doc nodes, graph edges and an FTS5 index over file
paths and bodies. SQLite is deliberate: the graph is small (thousands of files,
tens of thousands of symbols), queries are local and sub-100ms, and no service
has to be running for the atlas to work.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA temp_store=MEMORY;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    lang TEXT,
    role TEXT,
    domain TEXT,
    size INTEGER,
    mtime REAL,
    sha1 TEXT,
    summary TEXT,
    indexed_at REAL
);

CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    qualname TEXT,
    start_line INTEGER DEFAULT 1,
    end_line INTEGER DEFAULT 1,
    parent_id INTEGER,
    lang TEXT,
    meta TEXT
);

CREATE INDEX IF NOT EXISTS nodes_path_idx ON nodes(path);
CREATE INDEX IF NOT EXISTS nodes_name_idx ON nodes(name);
CREATE INDEX IF NOT EXISTS nodes_kind_idx ON nodes(kind);

CREATE TABLE IF NOT EXISTS edges (
    src INTEGER NOT NULL,
    dst INTEGER NOT NULL,
    kind TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    line INTEGER DEFAULT 0,
    PRIMARY KEY (src, dst, kind, line)
);

CREATE INDEX IF NOT EXISTS edges_src_idx ON edges(src);
CREATE INDEX IF NOT EXISTS edges_dst_idx ON edges(dst);
CREATE INDEX IF NOT EXISTS edges_kind_idx ON edges(kind);

CREATE VIRTUAL TABLE IF NOT EXISTS atlas_fts USING fts5(
    path UNINDEXED,
    name,
    body,
    tokenize = 'unicode61'
);
"""


class AtlasStore:
    """Thin, transaction-oriented wrapper around the atlas SQLite database."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._node_id_cache: Dict[str, int] = {}

    # ── lifecycle ───────────────────────────────────────────────────────────

    def begin_bulk(self) -> None:
        """Trade durability for build speed; the index is always rebuildable."""
        self.conn.execute("PRAGMA synchronous=OFF")

    def end_bulk(self) -> None:
        self.conn.commit()
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:  # pragma: no cover - best effort
            pass

    def __enter__(self) -> "AtlasStore":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # ── meta ────────────────────────────────────────────────────────────────

    def get_meta(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except (TypeError, ValueError):
            return row["value"]

    def set_meta(self, key: str, value: Any) -> None:
        encoded = json.dumps(value) if not isinstance(value, str) else value
        self.conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, encoded),
        )

    def all_meta(self) -> Dict[str, Any]:
        return {
            row["key"]: self._decode_meta(row["value"])
            for row in self.conn.execute("SELECT key, value FROM meta")
        }

    @staticmethod
    def _decode_meta(value: Any) -> Any:
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    # ── inventory ───────────────────────────────────────────────────────────

    def reset_schema(self) -> None:
        """Drop and recreate the atlas tables (used when the index version moves)."""
        with self.conn:
            for table in ("atlas_fts", "edges", "nodes", "files", "meta"):
                self.conn.execute(f"DROP TABLE IF EXISTS {table}")
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._node_id_cache.clear()

    def clear(self) -> None:
        with self.conn:
            for table in ("edges", "nodes", "files", "meta", "atlas_fts"):
                self.conn.execute(f"DELETE FROM {table}")
            self.conn.execute("DELETE FROM sqlite_sequence WHERE name = 'nodes'")
        self._node_id_cache.clear()

    def upsert_file(self, record: Dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO files(path, lang, role, domain, size, mtime, sha1, summary, indexed_at)
            VALUES(:path, :lang, :role, :domain, :size, :mtime, :sha1, :summary, :indexed_at)
            ON CONFLICT(path) DO UPDATE SET
                lang = excluded.lang,
                role = excluded.role,
                domain = excluded.domain,
                size = excluded.size,
                mtime = excluded.mtime,
                sha1 = excluded.sha1,
                summary = excluded.summary,
                indexed_at = excluded.indexed_at
            """,
            record,
        )

    def delete_file(self, path: str) -> None:
        ids = [
            row["id"]
            for row in self.conn.execute(
                "SELECT id FROM nodes WHERE path = ?", (path,)
            )
        ]
        self._delete_node_ids(ids)
        self.conn.execute("DELETE FROM nodes WHERE path = ?", (path,))
        self.conn.execute("DELETE FROM files WHERE path = ?", (path,))
        self.conn.execute("DELETE FROM atlas_fts WHERE path = ?", (path,))
        self._node_id_cache.clear()

    def file_paths(self) -> List[str]:
        return [
            row["path"]
            for row in self.conn.execute("SELECT path FROM files ORDER BY path")
        ]

    def files(self) -> List[Dict[str, Any]]:
        return [
            dict(row)
            for row in self.conn.execute("SELECT * FROM files ORDER BY path")
        ]

    def file(self, path: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM files WHERE path = ?", (path,)
        ).fetchone()
        return dict(row) if row else None

    # ── nodes ───────────────────────────────────────────────────────────────

    def upsert_file_node(
        self, path: str, name: str, end_line: int, lang: str = ""
    ) -> int:
        key = f"file:{path}"
        row = self.conn.execute(
            "SELECT id FROM nodes WHERE key = ?", (key,)
        ).fetchone()
        if row:
            self.conn.execute(
                "UPDATE nodes SET name = ?, end_line = ?, lang = ? WHERE id = ?",
                (name, max(1, int(end_line or 1)), lang, row["id"]),
            )
            return int(row["id"])
        cursor = self.conn.execute(
            """
            INSERT INTO nodes(key, kind, path, name, qualname, start_line, end_line, lang)
            VALUES(?, 'file', ?, ?, ?, 1, ?, ?)
            """,
            (key, path, name, name, max(1, int(end_line or 1)), lang),
        )
        return int(cursor.lastrowid)

    def replace_symbols(
        self,
        path: str,
        nodes: Sequence[Dict[str, Any]],
        edges: Sequence[Dict[str, Any]],
        body: str,
        fts_name: str,
        fresh: bool = False,
    ) -> None:
        """Replace every non-file node of ``path`` and its outgoing edges.

        ``fresh`` is used by a full build, where the tables were just cleared:
        it skips the per-file deletes (an FTS delete by path is a table scan and
        makes a full build quadratic).
        """
        if not fresh:
            ids = [
                row["id"]
                for row in self.conn.execute(
                    "SELECT id FROM nodes WHERE path = ? AND kind != 'file'",
                    (path,),
                )
            ]
            self._delete_node_ids(ids)
            self.conn.execute(
                "DELETE FROM nodes WHERE path = ? AND kind != 'file'", (path,)
            )

        key_to_id: Dict[str, int] = {}
        file_row = self.conn.execute(
            "SELECT id FROM nodes WHERE key = ?", (f"file:{path}",)
        ).fetchone()
        if file_row:
            key_to_id[f"file:{path}"] = int(file_row["id"])

        # Parents before children so parent_id resolves in one pass.
        ordered = sorted(
            nodes,
            key=lambda node: (
                int(node.get("start_line") or 1),
                -int(node.get("end_line") or 1),
            ),
        )
        for node in ordered:
            key = node["key"]
            parent_id = key_to_id.get(node.get("parent_key") or "")
            cursor = self.conn.execute(
                """
                INSERT OR REPLACE INTO nodes(
                    key, kind, path, name, qualname, start_line, end_line,
                    parent_id, lang, meta
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    node.get("kind") or "symbol",
                    path,
                    node.get("name") or "",
                    node.get("qualname") or "",
                    int(node.get("start_line") or 1),
                    int(node.get("end_line") or 1),
                    parent_id,
                    node.get("lang") or "",
                    json.dumps(node.get("meta") or {}),
                ),
            )
            key_to_id[key] = int(cursor.lastrowid)

        for edge in edges:
            src = key_to_id.get(edge.get("src_key") or "")
            if src is None:
                src = self._resolve_key(edge.get("src_key") or "")
            dst = key_to_id.get(edge.get("dst_key") or "")
            if dst is None:
                dst = self._resolve_key(edge.get("dst_key") or "")
            if not src or not dst or src == dst:
                continue
            self.conn.execute(
                "INSERT OR IGNORE INTO edges(src, dst, kind, confidence, line) "
                "VALUES(?, ?, ?, ?, ?)",
                (
                    src,
                    dst,
                    edge.get("kind") or "related",
                    float(edge.get("confidence") or 1.0),
                    int(edge.get("line") or 0),
                ),
            )

        if not fresh:
            self.conn.execute("DELETE FROM atlas_fts WHERE path = ?", (path,))
        self.conn.execute(
            "INSERT INTO atlas_fts(path, name, body) VALUES(?, ?, ?)",
            (path, fts_name or path, body or ""),
        )
        self._node_id_cache.clear()

    def add_edges(self, edges: Iterable[Dict[str, Any]]) -> int:
        """Insert edges by node key after all nodes exist (calls, tests, docs)."""
        inserted = 0
        for edge in edges:
            src = self._resolve_key(edge.get("src_key") or "")
            dst = self._resolve_key(edge.get("dst_key") or "")
            if not src or not dst or src == dst:
                continue
            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO edges(src, dst, kind, confidence, line) "
                "VALUES(?, ?, ?, ?, ?)",
                (
                    src,
                    dst,
                    edge.get("kind") or "related",
                    float(edge.get("confidence") or 1.0),
                    int(edge.get("line") or 0),
                ),
            )
            inserted += cursor.rowcount if cursor.rowcount > 0 else 0
        return inserted

    def _resolve_key(self, key: str) -> Optional[int]:
        if not key:
            return None
        cached = self._node_id_cache.get(key)
        if cached:
            return cached
        row = self.conn.execute(
            "SELECT id FROM nodes WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            return None
        self._node_id_cache[key] = int(row["id"])
        return int(row["id"])

    def node_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM nodes WHERE key = ?", (key,)
        ).fetchone()
        return dict(row) if row else None

    def node(self, node_id: int) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        return dict(row) if row else None

    def _delete_node_ids(self, ids: Sequence[int]) -> None:
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        self.conn.execute(
            f"DELETE FROM edges WHERE src IN ({placeholders}) OR dst IN ({placeholders})",
            tuple(ids) + tuple(ids),
        )

    # ── search ──────────────────────────────────────────────────────────────

    def search_nodes(
        self,
        tokens: Sequence[str],
        limit: int = 250,
    ) -> List[Dict[str, Any]]:
        if not tokens:
            return []
        clauses = []
        params: List[Any] = []
        for token in tokens:
            clauses.append("(lower(name) LIKE ? OR lower(path) LIKE ?)")
            like = f"%{token.lower()}%"
            params.extend([like, like])
        sql = (
            "SELECT * FROM nodes WHERE kind != 'file' AND ("
            + " OR ".join(clauses)
            + ") ORDER BY start_line LIMIT ?"
        )
        params.append(int(limit))
        return [dict(row) for row in self.conn.execute(sql, params)]

    def search_files(self, tokens: Sequence[str], limit: int = 150) -> List[Dict[str, Any]]:
        if not tokens:
            return []
        clauses = []
        params: List[Any] = []
        for token in tokens:
            clauses.append("lower(path) LIKE ?")
            params.append(f"%{token.lower()}%")
        sql = (
            "SELECT * FROM files WHERE (" + " OR ".join(clauses) + ") "
            "ORDER BY path LIMIT ?"
        )
        params.append(int(limit))
        return [dict(row) for row in self.conn.execute(sql, params)]

    def search_fts(self, match_query: str, limit: int = 150) -> List[Dict[str, Any]]:
        if not match_query:
            return []
        try:
            rows = self.conn.execute(
                """
                SELECT path, name, bm25(atlas_fts) AS rank,
                       snippet(atlas_fts, 2, '', '', ' … ', 12) AS snippet
                FROM atlas_fts
                WHERE atlas_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (match_query, int(limit)),
            )
            return [dict(row) for row in rows]
        except sqlite3.OperationalError as ex:
            logger.debug("Atlas FTS query failed (%s): %s", match_query, ex)
            return []

    def nodes_for_path(self, path: str, kinds: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
        params: List[Any] = [path]
        sql = "SELECT * FROM nodes WHERE path = ?"
        if kinds:
            sql += " AND kind IN (" + ",".join("?" for _ in kinds) + ")"
            params.extend(kinds)
        sql += " ORDER BY start_line"
        return [dict(row) for row in self.conn.execute(sql, params)]

    def edges_from(self, node_id: int, kinds: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
        return self._edges(node_id, "src", kinds)

    def edges_to(self, node_id: int, kinds: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
        return self._edges(node_id, "dst", kinds)

    def _edges(self, node_id: int, side: str, kinds: Optional[Sequence[str]]) -> List[Dict[str, Any]]:
        join_col = "dst" if side == "src" else "src"
        sql = (
            "SELECT e.src, e.dst, e.kind, e.confidence, e.line, "
            "n.id AS other_id, n.kind AS other_kind, n.path AS other_path, "
            "n.name AS other_name, n.start_line AS other_start_line, "
            "n.end_line AS other_end_line "
            "FROM edges e JOIN nodes n ON n.id = e."
            + join_col
            + " WHERE e."
            + side
            + " = ?"
        )
        params: List[Any] = [node_id]
        if kinds:
            sql += " AND e.kind IN (" + ",".join("?" for _ in kinds) + ")"
            params.extend(kinds)
        sql += " ORDER BY e.kind, n.path, n.start_line LIMIT 200"
        return [dict(row) for row in self.conn.execute(sql, params)]

    def in_degree(self, path: str) -> int:
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM edges e
            JOIN nodes src ON src.id = e.src
            JOIN nodes dst ON dst.id = e.dst
            WHERE dst.path = ? AND e.kind IN ('imports', 'calls', 'documents', 'tests')
            """,
            (path,),
        ).fetchone()
        return int(row["total"] if row else 0)

    def top_central_files(self, limit: int = 12, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        params: List[Any] = []
        domain_clause = ""
        if domain:
            domain_clause = "AND dst.path LIKE ?"
            params.append(f"{domain}%")
        sql = (
            "SELECT dst.path AS path, COUNT(*) AS degree "
            "FROM edges e "
            "JOIN nodes dst ON dst.id = e.dst "
            "JOIN files f ON f.path = dst.path "
            "WHERE e.kind IN ('imports', 'calls', 'documents', 'tests') "
            "AND f.role = 'source' "
            "AND dst.path NOT LIKE '%/public/%' "
            "AND dst.path NOT LIKE '%node_modules%' "
            "AND dst.path NOT LIKE '%.min.%' "
            + domain_clause
            + " GROUP BY dst.path ORDER BY degree DESC LIMIT ?"
        )
        params.append(int(limit))
        return [dict(row) for row in self.conn.execute(sql, params)]

    def domain_counts(self) -> List[Dict[str, Any]]:
        return [
            dict(row)
            for row in self.conn.execute(
                "SELECT domain, COUNT(*) AS files FROM files "
                "GROUP BY domain ORDER BY files DESC"
            )
        ]

    def stats(self) -> Dict[str, Any]:
        def count(sql: str) -> int:
            row = self.conn.execute(sql).fetchone()
            return int(row[0] if row else 0)

        return {
            "files": count("SELECT COUNT(*) FROM files"),
            "symbols": count("SELECT COUNT(*) FROM nodes WHERE kind = 'symbol'"),
            "routes": count("SELECT COUNT(*) FROM nodes WHERE kind = 'route'"),
            "docs": count("SELECT COUNT(*) FROM nodes WHERE kind = 'doc'"),
            "tests": count("SELECT COUNT(*) FROM files WHERE role = 'test'"),
            "edges": count("SELECT COUNT(*) FROM edges"),
            "domains": count("SELECT COUNT(DISTINCT domain) FROM files"),
        }
