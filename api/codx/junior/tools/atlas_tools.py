"""
Model-facing atlas tools.

These are the only discovery tools the model needs: ``project_map`` to orient,
``project_locate`` to find anything (symbol, string, route, doc or file
pattern), ``project_trace`` to follow a flow, ``project_impact`` before a change
and ``project_health`` when the index looks wrong.

When the project atlas is enforced (``project_atlas_force``), the agent runtime
removes ``project_grep``/``project_glob``/``project_search`` from the request,
so the model cannot fall back to raw scanning. A bounded in-tool fallback keeps
the capability available if the index itself cannot be opened.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .model import ToolResponse

logger = logging.getLogger(__name__)


def _settings(kwargs: Dict[str, Any]) -> Any:
    settings = kwargs.get("settings")
    if settings is None:
        raise Exception("Invalid project settings")
    return settings


def _atlas(settings: Any):
    from codx.junior.atlas import ProjectAtlas

    return ProjectAtlas(settings)


def _project_root(settings: Any) -> str:
    return os.path.abspath(getattr(settings, "abs_project_path", "") or ".")


# ── related projects (children + declared dependencies) ─────────────────────


def _related_rows(settings: Any) -> List[Dict[str, Any]]:
    """Projects searched together with this one (children + dependencies)."""
    try:
        from codx.junior.atlas.related import related_projects

        return related_projects(settings)
    except Exception:
        logger.debug("Atlas: related projects unavailable", exc_info=True)
        return []


def _related_section(rows: Sequence[Dict[str, Any]]) -> str:
    """Describe the project structure so the model knows where it can search."""
    if not rows:
        return ""
    lines = [
        "### Related projects",
        "",
        "| Project | Relation | Root | Atlas |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['name']}` | {row['kind']} | `{row['root']}` | "
            f"{'indexed' if row.get('indexed') else 'not built yet'} |"
        )
    lines.extend([
        "",
        "Use `project_locate(query, project='<name>')` to search one of them, or "
        "`project_locate(query, project='all')` to search this project and every "
        "related project in one call. Paths reported for another project are "
        "relative to that project's root: read them with "
        "`project_read_file('<root>/<path>')`.",
    ])
    return "\n".join(lines)


def _related_targets(settings: Any, project: str) -> Tuple[List[Dict[str, Any]], str]:
    """Resolve the ``project`` tool argument to atlas targets (or an error)."""
    from codx.junior.atlas.related import find_related_project

    wanted = (project or "").strip()
    rows = _related_rows(settings)
    if wanted.lower() in {"all", "*", "any", "every"}:
        return rows, ""
    row = find_related_project(settings, wanted)
    if row is None:
        names = ", ".join(f"`{item['name']}`" for item in rows) or "none configured"
        return [], (
            f"No related project named `{wanted}`. Available: {names}. "
            "Call `project_map()` to see the project structure."
        )
    return [row], ""


def _locate_related_projects(
    settings: Any, query: str, project: str, **locate_args
) -> ToolResponse:
    """Locate in the atlas of other projects (children and dependencies)."""
    from codx.junior.atlas import ProjectAtlas, atlas_ready

    rows, error = _related_targets(settings, project)
    if error:
        return ToolResponse(user_response=error, llm_response=f"> {error}")

    current = {
        "name": (
            getattr(settings, "project_name", "")
            or os.path.basename(_project_root(settings))
        ),
        "root": _project_root(settings),
        "kind": "current",
        "settings": settings,
        "indexed": atlas_ready(settings),
    }
    everywhere = project.strip().lower() in {"all", "*", "any", "every"}
    targets = ([current] if everywhere else []) + rows
    if not targets:
        targets = [current]

    lines = [f"> atlas locate `{query}` across {len(targets)} project(s)", ""]
    evidence_count = 0
    for target in targets:
        label = f"## `{target['name']}` ({target['kind']})"
        root = target["root"]
        if not target.get("indexed"):
            _schedule_warmup(target["settings"])
            lines.extend([
                label,
                "",
                f"> no atlas yet for `{root}`; a build was scheduled. "
                "Retry this call in a few seconds.",
                "",
            ])
            continue
        try:
            with ProjectAtlas(target["settings"]) as atlas:
                packet = atlas.locate(query=query, **locate_args)
        except Exception as ex:
            logger.exception("project_locate failed for %s", target["name"])
            lines.extend([label, "", f"> atlas error: {ex}", ""])
            continue
        evidence_count += len(packet.evidence)
        lines.extend([label, ""])
        if target["settings"] is not settings:
            lines.extend([
                f"- root: `{root}`",
                "- paths below are relative to that root; read them with "
                f"`project_read_file('{root}/<path>')`",
                "",
            ])
        lines.extend([packet.to_markdown(), ""])

    if not evidence_count:
        lines.append(
            "> No evidence in any project. Call `project_map()` to see the "
            "structure, or retry with a shorter identifier."
        )
    return ToolResponse(
        user_response=_one_line(
            f"atlas: {evidence_count} locator(s) across {len(targets)} project(s) "
            f"for `{query}`"
        ),
        llm_response="\n".join(lines).strip(),
    )


def _one_line(text: str, limit: int = 240) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ── fast bootstrap (no full index yet) ─────────────────────────────────────


def _schedule_warmup(settings: Any) -> None:
    try:
        from codx.junior.atlas.curator import schedule_atlas_refresh

        schedule_atlas_refresh(settings, delay=0.2)
    except Exception:
        pass


def _fallback_map(settings: Any, limit: int = 12) -> str:
    """Cheap filesystem map used while the real index builds in background."""
    root = _project_root(settings)
    counts: Dict[str, int] = {}
    entry_points: List[str] = []
    scanned = 0
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [
            directory for directory in dirs
            if directory not in {
                ".git", ".codx", "node_modules", ".venv", "venv", "__pycache__",
                "dist", "build", "coverage", ".worktrees",
            }
            and not directory.startswith(".")
        ]
        for file_name in files:
            if scanned >= 1500:
                break
            rel_dir = os.path.relpath(current_root, root)
            domain = rel_dir.split(os.sep)[0] if rel_dir != "." else "root"
            counts[domain] = counts.get(domain, 0) + 1
            if file_name in {
                "main.py", "app.py", "server.py", "__init__.py", "index.ts",
                "main.ts", "App.vue", "run_api.sh", "Dockerfile", "package.json",
            }:
                entry_points.append(
                    os.path.relpath(os.path.join(current_root, file_name), root)
                    .replace(os.sep, "/")
                )
            scanned += 1
        if scanned >= 1500:
            break
    lines = [
        "> atlas warming up: bounded filesystem map (full index builds in background)",
        "",
        "| Domain | Files (sampled) |",
        "| --- | ---: |",
    ]
    for domain, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]:
        lines.append(f"| `{domain}` | {count} |")
    if entry_points:
        lines.extend(["", "### Entry points"])
        lines.extend(f"- `{path}`" for path in entry_points[:8])
    lines.extend([
        "",
        "> Call `project_locate(...)` for a concrete locator; it will use the "
        "atlas as soon as the build completes.",
    ])
    return "\n".join(lines)


# ── tool functions ──────────────────────────────────────────────────────────


def project_map(query: str = "", path: str = "", limit: int = 12, **kwargs) -> ToolResponse:
    """
    Orient in the project: domains, entry points, key files and reading order.

    Use this as the FIRST call for any non-trivial task. It is cheap, local and
    returns a map instead of a pile of search hits. Pass ``query`` when the task
    already names a feature or symbol (for example ``"wallet"`` or ``"auth"``)
    to focus the map on the matching files.
    """
    settings = _settings(kwargs)
    from codx.junior.atlas import atlas_ready

    related = _related_section(_related_rows(settings))

    if not atlas_ready(settings):
        _schedule_warmup(settings)
        llm_response = _fallback_map(settings, limit=limit)
        if related:
            llm_response = f"{llm_response}\n\n{related}"
        return ToolResponse(
            user_response="Atlas warming up; returning a filesystem map.",
            llm_response=llm_response,
        )
    try:
        with _atlas(settings) as atlas:
            packet = atlas.map(query=query, path=path, limit=limit)
        llm_response = packet.to_markdown()
        if related:
            llm_response = f"{llm_response}\n\n{related}"
        return ToolResponse(
            user_response=_one_line(packet.answer),
            llm_response=llm_response,
        )
    except Exception as ex:
        logger.exception("project_map failed")
        return ToolResponse(
            user_response=f"Atlas map unavailable: {ex}",
            llm_response=(
                f"> atlas map unavailable: {ex}\n\n"
                "The project atlas could not be built. Do not fall back to a "
                "repo-wide text search; call `project_health()` for details."
            ),
        )


def project_locate(
    query: str,
    path: str = "",
    include: str = "",
    regex: bool = False,
    case_sensitive: bool = False,
    limit: int = 8,
    include_tests: bool = True,
    kind: str = "",
    project: str = "",
    **kwargs,
) -> ToolResponse:
    """
    Find the exact resources for a question and return ranked ``path:line``
    locators with snippets and a reason.

    Use this instead of grep/glob/semantic search:

    * symbol or feature: ``project_locate("check_user_wallet")``
    * exact string/error: ``project_locate("spending limits exceeded")``
    * regex: ``project_locate(r"TODO:\\s*wallet", regex=True)``
    * file pattern: ``project_locate("**/*wallet*.py")``
    * route: ``project_locate("POST /chat")``
    * documentation: ``project_locate("wallet", kind="doc")``
    * another project: ``project_locate("AtlasIndexer", project="codx-api")``
    * this project and every related one: ``project_locate("router", project="all")``

    Results are ranked (definitions before references, source before tests,
    central files before leaves) and capped, so the model reads a few files
    instead of scanning the repository.
    """
    settings = _settings(kwargs)
    if not (query or "").strip():
        raise ValueError("query must be provided and cannot be empty")

    # Another project: children and declared dependencies have their own atlas.
    if (project or "").strip().lower() not in {"", "self", "current", "this"}:
        return _locate_related_projects(
            settings,
            query=query,
            project=project,
            path=path,
            include=include,
            regex=regex,
            case_sensitive=case_sensitive,
            limit=max(3, min(int(limit or 8), 8)),
            include_tests=include_tests,
            kind=kind,
        )

    from codx.junior.atlas import atlas_ready

    if not atlas_ready(settings):
        _schedule_warmup(settings)
        fallback = _fallback_locate(settings, query, path=path, regex=regex, limit=limit)
        if fallback:
            markdown = (
                "> atlas warming up: bounded fallback search "
                "(full index builds in background)\n\n"
                "### Evidence\n"
                + "\n".join(f"- `{location}` — {why}" for location, why in fallback)
            )
        else:
            markdown = (
                "> atlas warming up: no bounded match yet. The full index is "
                "building in the background; retry this call in a few seconds."
            )
        return ToolResponse(
            user_response=f"Atlas warming up; {len(fallback)} fallback locator(s).",
            llm_response=markdown,
        )
    try:
        with _atlas(settings) as atlas:
            packet = atlas.locate(
                query=query,
                path=path,
                include=include,
                regex=regex,
                case_sensitive=case_sensitive,
                limit=limit,
                include_tests=include_tests,
                kind=kind,
            )
        if not packet.evidence:
            fallback = _fallback_locate(settings, query, path=path, regex=regex, limit=limit)
            if fallback:
                markdown = (
                    f"> atlas fallback: {len(fallback)} locator(s) | index unavailable or empty\n\n"
                    "### Evidence\n"
                    + "\n".join(
                        f"- `{location}` — {why}" for location, why in fallback
                    )
                )
                return ToolResponse(
                    user_response=f"Found {len(fallback)} locator(s) in fallback mode.",
                    llm_response=markdown,
                )
        return ToolResponse(
            user_response=_one_line(packet.answer),
            llm_response=packet.to_markdown(),
        )
    except Exception as ex:
        logger.exception("project_locate failed")
        fallback = _fallback_locate(settings, query, path=path, regex=regex, limit=limit)
        if fallback:
            markdown = (
                f"> atlas unavailable ({ex}); bounded fallback search\n\n"
                "### Evidence\n"
                + "\n".join(f"- `{location}` — {why}" for location, why in fallback)
            )
            return ToolResponse(
                user_response=f"Found {len(fallback)} locator(s) in fallback mode.",
                llm_response=markdown,
            )
        return ToolResponse(
            user_response=f"Atlas locate failed: {ex}",
            llm_response=(
                f"> atlas locate failed: {ex}\n\n"
                "Call `project_health()` and report the error instead of scanning "
                "the whole repository."
            ),
        )


def project_trace(symbol: str, direction: str = "out", depth: int = 2, **kwargs) -> ToolResponse:
    """
    Follow imports, calls, routes and handlers from a symbol or file.

    Use it to answer "how does this request reach the database?", "who calls
    this function?", or "which handler owns this route?". ``direction`` is
    ``out`` (what this uses), ``in`` (who uses this) or ``both``.
    """
    settings = _settings(kwargs)
    from codx.junior.atlas import atlas_ready

    if not atlas_ready(settings):
        _schedule_warmup(settings)
        return ToolResponse(
            user_response="Atlas warming up; trace needs the graph index.",
            llm_response=(
                "> atlas warming up: the graph index is building in the background. "
                "Use `project_locate(...)` for an immediate locator and retry "
                "`project_trace(...)` in a few seconds."
            ),
        )
    try:
        with _atlas(settings) as atlas:
            packet = atlas.trace(symbol=symbol, direction=direction, depth=depth)
        return ToolResponse(
            user_response=_one_line(packet.answer),
            llm_response=packet.to_markdown(),
        )
    except Exception as ex:
        logger.exception("project_trace failed")
        return ToolResponse(
            user_response=f"Atlas trace failed: {ex}",
            llm_response=f"> atlas trace failed: {ex}\n\nCall `project_health()`.",
        )


def project_impact(paths: Any, depth: int = 2, **kwargs) -> ToolResponse:
    """
    List what depends on one or more files before changing them.

    Returns reverse imports/calls, tests and documentation pages, plus a risk
    level. Use it before editing a shared module, a model or an API route.
    """
    settings = _settings(kwargs)
    if isinstance(paths, str):
        paths = [paths]
    from codx.junior.atlas import atlas_ready

    if not atlas_ready(settings):
        _schedule_warmup(settings)
        return ToolResponse(
            user_response="Atlas warming up; impact needs the graph index.",
            llm_response=(
                "> atlas warming up: the graph index is building in the background. "
                "Read the files directly for now and retry `project_impact([...])` "
                "in a few seconds."
            ),
        )
    try:
        with _atlas(settings) as atlas:
            packet = atlas.impact(paths=paths or [], depth=depth)
        return ToolResponse(
            user_response=_one_line(packet.answer),
            llm_response=packet.to_markdown(),
        )
    except Exception as ex:
        logger.exception("project_impact failed")
        return ToolResponse(
            user_response=f"Atlas impact failed: {ex}",
            llm_response=f"> atlas impact failed: {ex}\n\nCall `project_health()`.",
        )


def project_health(**kwargs) -> ToolResponse:
    """
    Report atlas coverage, freshness and warnings.

    Call it when ``project_locate`` returns nothing, when a locator looks
    stale, or before trusting a large architectural answer.
    """
    settings = _settings(kwargs)
    from codx.junior.atlas import atlas_ready

    if not atlas_ready(settings):
        _schedule_warmup(settings)
        return ToolResponse(
            user_response="Atlas is not built yet; warming up.",
            llm_response=(
                "> atlas is not built yet. A background build was scheduled; "
                "retry `project_health()` in a few seconds."
            ),
        )
    try:
        with _atlas(settings) as atlas:
            health = atlas.health()
        return ToolResponse(
            user_response=(
                f"Atlas: {health.files} files, {health.symbols} symbols, "
                f"{health.edges} edges, commit {health.commit or 'no-git'}"
            ),
            llm_response=health.to_markdown(),
        )
    except Exception as ex:
        logger.exception("project_health failed")
        return ToolResponse(
            user_response=f"Atlas health failed: {ex}",
            llm_response=f"> atlas health failed: {ex}",
        )


# ── bounded fallback (never a repo-wide unbounded scan) ─────────────────────


def _fallback_locate(
    settings: Any,
    query: str,
    path: str = "",
    regex: bool = False,
    limit: int = 8,
) -> List[Tuple[str, str]]:
    """
    Tiny literal/regex scan used only when the atlas cannot answer.

    It is bounded to 800 files and 1 MB per file, and returns locators rather
    than matching lines, so the model still gets a reading list.
    """
    root = _project_root(settings)
    base = os.path.normpath(os.path.join(root, path)) if path else root
    if not base.startswith(root):
        return []
    matcher = None
    if regex:
        try:
            matcher = re.compile(query, re.IGNORECASE)
        except re.error:
            return []
    needle = query.lower()
    results: List[Tuple[str, str]] = []
    scanned = 0
    for current_root, dirs, files in os.walk(base):
        dirs[:] = [
            directory for directory in dirs
            if directory not in {
                ".git", ".codx", "node_modules", ".venv", "venv", "__pycache__",
                "dist", "build", "coverage", ".worktrees",
            }
        ]
        for file_name in files:
            if scanned >= 800 or len(results) >= limit:
                return results
            ext = os.path.splitext(file_name)[1].lower()
            if ext not in {
                ".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".md", ".json",
                ".yaml", ".yml", ".toml", ".sh",
            }:
                continue
            abs_path = os.path.join(current_root, file_name)
            try:
                if os.path.getsize(abs_path) > 1024 * 1024:
                    continue
                with open(abs_path, "r", encoding="utf-8", errors="replace") as handle:
                    for line_no, line in enumerate(handle, 1):
                        matched = (
                            matcher.search(line) is not None
                            if matcher is not None
                            else needle in line.lower()
                        )
                        if matched:
                            rel = os.path.relpath(abs_path, root).replace(os.sep, "/")
                            results.append((
                                f"{rel}:{line_no}",
                                "fallback content match",
                            ))
                            break
            except OSError:
                continue
            scanned += 1
    return results


# ── tool schemas ────────────────────────────────────────────────────────────

PROJECT_MAP_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "project_map",
        "description": (
            "PROJECT ATLAS — call this FIRST for any non-trivial task. Returns a "
            "map of the project: domains, entry points, key files and a reading "
            "order. Use it to orient instead of scanning folders or grepping. "
            "Pass query='<feature/symbol>' to focus the map; pass path='api/' to "
            "restrict it. The atlas is local, verified against the working tree "
            "and usually faster than one grep call. The map also lists the "
            "related projects (child and dependency projects) that can be "
            "searched with project_locate(..., project='<name>'|'all')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Optional feature, domain or symbol to focus the map on.",
                },
                "path": {
                    "type": "string",
                    "description": "Optional project-relative folder to map.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum domains/key files to return (3-30).",
                    "default": 12,
                    "minimum": 3,
                    "maximum": 30,
                },
            },
        },
    },
}

PROJECT_LOCATE_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "project_locate",
        "description": (
            "PROJECT ATLAS — the only discovery search you need. Finds symbols, "
            "strings, error messages, routes, docs and file patterns and returns "
            "ranked `path:line` locators with snippets and reasons. Use it instead "
            "of grep/glob/semantic search: it ranks definitions before references, "
            "source before tests, central files before leaves, and it verifies "
            "the lines against the current files. Examples: "
            "project_locate('check_user_wallet'); project_locate('POST /chat'); "
            "project_locate('spending limits exceeded'); "
            "project_locate('**/*wallet*.py')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Symbol, feature, exact string, error message, route, doc "
                        "title or glob pattern."
                    ),
                },
                "path": {
                    "type": "string",
                    "description": "Optional project-relative folder to search.",
                },
                "include": {
                    "type": "string",
                    "description": "Optional glob filter, e.g. '*.py' or 'api/**/*.ts'.",
                },
                "regex": {
                    "type": "boolean",
                    "description": "Treat query as a regular expression. Defaults to false.",
                    "default": False,
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Match case for content scans. Defaults to false.",
                    "default": False,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum locators to return (1-20).",
                    "default": 8,
                    "minimum": 1,
                    "maximum": 20,
                },
                "include_tests": {
                    "type": "boolean",
                    "description": "Include test files. Defaults to true.",
                    "default": True,
                },
                "kind": {
                    "type": "string",
                    "enum": [
                        "symbol", "function", "class", "method", "route",
                        "endpoint", "doc", "file", "test", "config", "",
                    ],
                    "description": "Optional result kind filter.",
                    "default": "",
                },
                "project": {
                    "type": "string",
                    "description": (
                        "Search another project instead of (or in addition to) this "
                        "one. Use a project name listed by project_map ('child' or "
                        "'dependency' projects) or 'all' to search this project and "
                        "every related project. Paths from another project are "
                        "relative to its root. Defaults to this project only."
                    ),
                    "default": "",
                },
            },
            "required": ["query"],
        },
    },
}

PROJECT_TRACE_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "project_trace",
        "description": (
            "PROJECT ATLAS — follow imports, calls, routes and handlers from a "
            "symbol or file. Answers 'how does this request reach the database?', "
            "'who calls this function?' and 'which handler owns this route?'. "
            "Use direction='out' (what it uses), 'in' (who uses it) or 'both'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol name, route or file path to start from.",
                },
                "direction": {
                    "type": "string",
                    "enum": ["out", "in", "both"],
                    "description": "Edge direction. Defaults to 'out'.",
                    "default": "out",
                },
                "depth": {
                    "type": "integer",
                    "description": "Maximum graph depth (1-4).",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 4,
                },
            },
            "required": ["symbol"],
        },
    },
}

PROJECT_IMPACT_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "project_impact",
        "description": (
            "PROJECT ATLAS — list what depends on one or more files before you "
            "change them: reverse imports/calls, tests to run, documentation to "
            "update and a risk level. Call it before editing a shared module, a "
            "model, a route or a public helper."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": ["string", "array"],
                    "description": "One file path or a list of project-relative file paths.",
                },
                "depth": {
                    "type": "integer",
                    "description": "Maximum reverse-dependency depth (1-4).",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 4,
                },
            },
            "required": ["paths"],
        },
    },
}

PROJECT_HEALTH_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "project_health",
        "description": (
            "PROJECT ATLAS — report index coverage, freshness, commit and "
            "warnings. Call it when project_locate returns nothing, when a "
            "locator looks stale, or before trusting a large architectural answer."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}
