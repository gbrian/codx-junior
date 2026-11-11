"""
Search tools for the ``.codx`` control plane.

The project tree has two namespaces and they must never be confused:

* **codebase** — the source files, searched by the ``project_*`` tools
  (``project_structure``, ``project_glob``, ``project_grep``,
  ``project_search``, ``project_read_file``). ``.codx`` is always excluded from
  those tools.
* **control plane** — the ``.codx`` folder. It stores task cards and boards,
  AI profiles, browser/desktop sessions, views, teams, workspaces, chat turns,
  orchestration state, project metadata and logs. It can be hundreds of
  megabytes (task histories, chat turns, databases), so a source-code search
  that wanders into it is both slow and wrong.

This module is the single LLM-facing entry point for the second namespace:
:func:`search_codx`. It:

* searches only the selected modules (``modules=[]`` lists the inventory),
* parses JSON/JSONL files structurally, so a hit reports the JSON field
  (``name``, ``description``, ``messages[3].content``), not an escaped blob,
* skips databases, downloads, locks, binary files, text files larger than
  8 MB and sensitive files (``.env``, keys, credentials),
* bounds the work with file/byte/result caps and reports when it truncates.

The tool is read-only. It never writes to ``.codx``.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from .model import ToolResponse

logger = logging.getLogger(__name__)

# ── Modules ──────────────────────────────────────────────────────────────────
# ``paths`` are folders relative to the .codx root; ``files`` are individual
# files. ``default`` modules are searched when the caller does not select any.
MODULES: Dict[str, Dict[str, Any]] = {
    "profiles": {
        "label": "AI profiles (persona, content, tools, tags)",
        "paths": ("profiles",),
        "default": True,
    },
    "tasks": {
        "label": "Task cards, boards, columns and task histories",
        "paths": ("tasks",),
        "default": True,
    },
    "browser_sessions": {
        "label": "Browser and desktop sessions (metadata and activity)",
        "paths": ("browser_sessions",),
        "default": True,
    },
    "views": {
        "label": "Desktop/board view layouts",
        "paths": ("views",),
        "default": True,
    },
    "teams": {
        "label": "Human + AI team rosters",
        "paths": ("teams",),
        "default": True,
    },
    "workspaces": {
        "label": "Workspace definitions (infra/dev containers)",
        "paths": ("workspaces",),
        "default": True,
    },
    "chat_turns": {
        "label": "Durable chat-turn records (recovery/processing state)",
        "paths": ("chat_turns",),
        "default": True,
    },
    "boards": {
        "label": "Board manager state and the task index",
        "paths": ("board_manager", "tasks/boards"),
        "files": ("tasks/index.json",),
        "default": True,
    },
    "orchestration": {
        "label": "Durable orchestration worker/run state",
        "paths": ("orchestration",),
        "default": True,
    },
    "project": {
        "label": "Project metadata (project.json, wiki settings, dependency map)",
        "files": (
            "project.json",
            "project_summary.md",
            "wiki_settings.json",
            "dependency_graph.json",
            "domain_map.json",
        ),
        "default": True,
    },
    "logs": {
        "label": "Application/agent logs",
        "paths": ("logs",),
        "default": False,
    },
}

DEFAULT_MODULES: Tuple[str, ...] = tuple(
    name for name, spec in MODULES.items() if spec.get("default")
)

# Modules that are NOT text searchable. They are rejected with an explanation
# instead of silently scanning a database or a binary download folder.
UNSUPPORTED_MODULES: Dict[str, str] = {
    "db": "the vector/SQLite databases (never text-search these)",
    "computer_library": "the computer image library (binaries)",
    "computer_downloads": "computer session downloads (binaries)",
    "browser_downloads": "browser.session downloads (binaries)",
}

MODULE_ALIASES: Dict[str, Tuple[str, ...]] = {
    "profile": ("profiles",),
    "agent": ("profiles",),
    "agents": ("profiles",),
    "task": ("tasks",),
    "kanban": ("tasks",),
    "browser": ("browser_sessions",),
    "browsers": ("browser_sessions",),
    "session": ("browser_sessions",),
    "sessions": ("browser_sessions",),
    "computer": ("browser_sessions",),
    "computers": ("browser_sessions",),
    "computer_session": ("browser_sessions",),
    "computer_sessions": ("browser_sessions",),
    "view": ("views",),
    "layout": ("views",),
    "layouts": ("views",),
    "team": ("teams",),
    "workspace": ("workspaces",),
    "infra": ("workspaces",),
    "chat": ("chat_turns",),
    "chats": ("chat_turns",),
    "chat_turn": ("chat_turns",),
    "board": ("boards",),
    "board_manager": ("boards",),
    "run": ("orchestration",),
    "runs": ("orchestration",),
    "worker": ("orchestration",),
    "workers": ("orchestration",),
    "settings": ("project",),
    "meta": ("project",),
    "metadata": ("project",),
    "log": ("logs",),
}

# ── Safety / performance limits ─────────────────────────────────────────────
# A .codx can be hundreds of megabytes. Every dimension is bounded; the tool
# reports when it had to stop, so the model can narrow the query instead of
# silently getting a partial answer.
MAX_CODX_FILE_BYTES = 8 * 1024 * 1024
MAX_CODX_FILES = 3000
MAX_CODX_TOTAL_BYTES = 300 * 1024 * 1024
MAX_CODX_RESULTS = 100
DEFAULT_CODX_RESULTS = 30
MAX_CODX_JSON_NODES = 100_000
MAX_CODX_MATCHES_PER_FILE = 3
MAX_CODX_COLLECTED_MATCHES = 600

# Folders under a module that are never text: databases, caches, binaries.
EXCLUDED_DIRS = frozenset({
    "db", "__pycache__", "node_modules", ".git", ".cache",
    "computer_library", "computer_downloads", "browser_downloads",
    "attachments", "uploads",
})

EXCLUDED_SUFFIXES = frozenset({
    ".lock", ".tmp", ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe",
    ".bin", ".db", ".sqlite", ".sqlite3", ".zip", ".tar", ".gz", ".tgz",
    ".7z", ".rar", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
    ".pdf", ".mp3", ".mp4", ".webm", ".mov", ".woff", ".woff2", ".ttf",
})

# Files that may contain credentials. They are never searched or inventoried.
SENSITIVE_FILE_PREFIXES = (
    ".env", "id_rsa", "id_ed25519", "credentials", "secrets", "secret.",
)
SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".kdbx")

# JSON/JSONL file types parsed structurally. ``.jsonl`` is line-based on
# purpose: every line is a JSON object and line numbers are useful.
JSON_SUFFIXES = frozenset({".json", ".profile", ".session", ".view", ".workspace"})
TEXT_SUFFIXES = frozenset({
    ".md", ".txt", ".py", ".js", ".ts", ".vue", ".yaml", ".yml", ".toml",
    ".ini", ".conf", ".log", ".jsonl", ".sh", ".css", ".html",
})

# JSON keys that are never searched: identity/credentials noise, not content.
_SKIP_JSON_KEYS = frozenset({
    "user", "users", "token", "tokens", "api_key", "api_settings",
    "password", "passwords", "secret", "secrets", "env", "environment",
    "authorization", "headers", "cookies",
})

_README = (
    "`.codx` is the control plane (tasks, profiles, sessions, chats, boards), "
    "not the codebase. Use the project_* tools for source code."
)


# ── Data types ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CodxFile:
    """One searchable file under a .codx module."""

    path: str
    rel_path: str
    display_path: str
    size: int
    mtime: float


@dataclass(frozen=True)
class CodxMatch:
    """One search hit with enough context for the model to decide."""

    module: str
    path: str
    field: str
    snippet: str
    score: int
    mtime: float


class _Matcher:
    """Literal or regex matcher with a snippet extractor."""

    def __init__(self, query: str, mode: str) -> None:
        self.query = query
        self.mode = mode
        self.regex: Optional[re.Pattern[str]] = None
        if mode == "regex":
            self.regex = re.compile(query, re.IGNORECASE)
        else:
            self._needle = query.lower()

    def matches(self, text: str) -> bool:
        if not text:
            return False
        if self.regex is not None:
            return self.regex.search(text) is not None
        return self._needle in text.lower()

    def snippet(self, text: str, max_chars: int = 320) -> str:
        """Return a one-line excerpt centered on the match."""
        if not text:
            return ""
        start = 0
        length = len(self.query)
        if self.regex is not None:
            match = self.regex.search(text)
            if match:
                start = match.start()
                length = max(1, match.end() - match.start())
        else:
            found = text.lower().find(self._needle)
            if found >= 0:
                start = found

        left = max(0, start - 120)
        right = min(len(text), start + length + 180)
        fragment = re.sub(r"\s+", " ", text[left:right]).strip()
        prefix = "…" if left > 0 else ""
        suffix = "…" if right < len(text) else ""
        return f"{prefix}{fragment}{suffix}"[:max_chars]


# ── Module resolution ───────────────────────────────────────────────────────
def _resolve_modules(
    modules: Optional[Iterable[str] | str],
) -> Tuple[List[str], List[str]]:
    """
    Normalize the ``modules`` argument into known module names.

    Accepts a string (comma/space separated), a list, aliases such as
    ``browser``/``computer_sessions`` or ``all``/``*``. Unknown modules are
    reported as warnings; unsupported modules (``db``, downloads) are rejected
    with an explanation instead of scanning them.
    """
    warnings: List[str] = []
    if modules is None or modules == [] or modules == "":
        return list(DEFAULT_MODULES), warnings

    values = modules if isinstance(modules, (list, tuple, set)) else [modules]
    names: List[str] = []

    for value in values:
        for token in re.split(r"[,;\s]+", str(value)):
            key = token.strip().lower().replace("-", "_")
            if not key:
                continue
            if key in ("all", "*"):
                expanded: Tuple[str, ...] = DEFAULT_MODULES
            elif key in MODULES:
                expanded = (key,)
            elif key in MODULE_ALIASES:
                expanded = MODULE_ALIASES[key]
            elif key in UNSUPPORTED_MODULES:
                warnings.append(
                    f"Module '{key}' is not text-searchable: "
                    f"{UNSUPPORTED_MODULES[key]}."
                )
                continue
            else:
                warnings.append(
                    f"Unknown module '{key}'. Valid modules: "
                    f"{', '.join(MODULES)}."
                )
                continue

            for name in expanded:
                if name not in names:
                    names.append(name)

    if not names:
        warnings.append("No valid module selected; searching all safe modules.")
        names = list(DEFAULT_MODULES)
    return names, warnings


def _codx_root(settings: Any) -> str:
    """Return the absolute ``.codx`` root for *settings*."""
    raw = getattr(settings, "codx_path", None) or ""
    if not raw:
        raw = os.path.join(getattr(settings, "abs_project_path", "") or "", ".codx")
    if not os.path.isabs(raw):
        raw = os.path.join(
            getattr(settings, "abs_project_path", "") or "", raw
        )
    return os.path.abspath(raw)


def _display_path(codx_root: str, abs_path: str) -> str:
    """Return ``.codx/<relative>`` with forward slashes."""
    rel = os.path.relpath(abs_path, codx_root)
    return ".codx/" + rel.replace(os.sep, "/")


def _human_size(size: int) -> str:
    """Return a compact human-readable size."""
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _is_searchable_file(name: str) -> bool:
    """Return False for locks, binaries, credentials and hidden files."""
    lowered = name.lower()
    if lowered.startswith("."):
        # .env* and other dotfiles may contain secrets; the control plane's
        # own hidden files are locks/temporary state, not content.
        return False
    if lowered.startswith(SENSITIVE_FILE_PREFIXES):
        return False
    if lowered.endswith(SENSITIVE_SUFFIXES):
        return False
    suffix = os.path.splitext(lowered)[1]
    if suffix in EXCLUDED_SUFFIXES:
        return False
    if suffix in JSON_SUFFIXES or suffix in TEXT_SUFFIXES:
        return True
    # Unknown text-ish files (e.g. ``*.session`` without a suffix mapping):
    # skip obvious binaries by suffix, keep the rest available for text scan.
    return True


def _iter_module_files(
    codx_root: str,
    module: str,
) -> Iterator[CodxFile]:
    """
    Yield the searchable files of one module.

    Walks only the module's folders (never the whole ``.codx``), prunes
    database/cache/binary folders and skips sensitive files. File stats are
    included so callers can bound the scan and sort by recency.
    """
    spec = MODULES.get(module)
    if not spec:
        return

    seen: set[str] = set()

    def _yield_file(abs_path: str) -> Optional[CodxFile]:
        if abs_path in seen or not os.path.isfile(abs_path):
            return None
        seen.add(abs_path)
        if not _is_searchable_file(os.path.basename(abs_path)):
            return None
        try:
            stat = os.stat(abs_path)
        except OSError:
            return None
        if stat.st_size == 0:
            return None
        return CodxFile(
            path=abs_path,
            rel_path=os.path.relpath(abs_path, codx_root),
            display_path=_display_path(codx_root, abs_path),
            size=stat.st_size,
            mtime=stat.st_mtime,
        )

    for relative in spec.get("paths", ()):
        root = os.path.join(codx_root, relative)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(
                name for name in dirnames
                if name not in EXCLUDED_DIRS and not name.startswith(".")
            )
            for name in sorted(filenames):
                item = _yield_file(os.path.join(dirpath, name))
                if item is not None:
                    yield item

    for relative in spec.get("files", ()):
        item = _yield_file(os.path.join(codx_root, relative))
        if item is not None:
            yield item


# ── JSON traversal ──────────────────────────────────────────────────────────
def _walk_json_strings(
    value: Any,
    path: str = "",
    depth: int = 0,
    budget: Optional[List[int]] = None,
) -> Iterator[Tuple[str, str]]:
    """
    Yield ``(field_path, string_value)`` for every searchable JSON string.

    Credentials/identity keys are skipped. The node budget prevents a huge
    task history from monopolizing a search.
    """
    if budget is None:
        budget = [MAX_CODX_JSON_NODES]
    if budget[0] <= 0 or depth > 14:
        return
    budget[0] -= 1

    if isinstance(value, str):
        if value.startswith("data:") and len(value) > 1000:
            return
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in _SKIP_JSON_KEYS:
                continue
            yield from _walk_json_strings(
                item,
                f"{path}.{key_text}" if path else key_text,
                depth + 1,
                budget,
            )
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _walk_json_strings(
                item, f"{path}[{index}]", depth + 1, budget
            )


def _field_score(field: str) -> int:
    """Rank a JSON field by how likely it is to be the useful hit."""
    leaf = field.rsplit(".", 1)[-1]
    leaf = re.sub(r"\[\d+\]", "", leaf).lower()
    if leaf in ("name", "title"):
        return 10
    if leaf in ("description", "summary", "objective"):
        return 8
    if leaf in ("content", "text", "message", "prompt", "body"):
        return 6
    lowered = field.lower()
    if "message" in lowered or "history" in lowered:
        return 4
    return 2


def _text_matches(
    content: str,
    matcher: _Matcher,
    *,
    context_lines: int,
    max_matches: int,
) -> List[Tuple[int, str, str]]:
    """Return ``(score, field, snippet)`` matches for a text file."""
    matches: List[Tuple[int, str, str]] = []
    lines = content.splitlines()
    if not lines:
        return matches

    context = max(0, min(int(context_lines or 0), 5))
    for index, line in enumerate(lines):
        if not matcher.matches(line):
            continue
        low = max(0, index - context)
        high = min(len(lines), index + context + 1)
        window = "\n".join(lines[low:high])
        matches.append((3, f"line {index + 1}", matcher.snippet(window)))
        if len(matches) >= max_matches:
            break
    return matches


def _search_file(
    item: CodxFile,
    matcher: _Matcher,
    context_lines: int,
) -> List[Tuple[int, str, str]]:
    """
    Search one file.

    Returns ``(score, field, snippet)`` tuples. JSON files are parsed so the
    hit reports the actual field (``name``, ``messages[3].content``); line
    numbers are used for text files and for unparseable JSON.
    """
    try:
        with open(item.path, "r", encoding="utf-8", errors="replace") as file:
            content = file.read()
    except OSError as ex:
        logger.debug("search_codx: cannot read %s: %s", item.path, ex)
        return []

    suffix = os.path.splitext(item.path)[1].lower()
    if suffix in JSON_SUFFIXES:
        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None
        if payload is not None:
            matches: List[Tuple[int, str, str]] = []
            for field, value in _walk_json_strings(payload):
                if not matcher.matches(value):
                    continue
                matches.append(
                    (_field_score(field), field or "value", matcher.snippet(value))
                )
                if len(matches) >= MAX_CODX_MATCHES_PER_FILE:
                    break
            return matches

    return [
        (score, field, snippet)
        for score, field, snippet in _text_matches(
            content,
            matcher,
            context_lines=context_lines,
            max_matches=MAX_CODX_MATCHES_PER_FILE,
        )
    ]


# ── Inventory ───────────────────────────────────────────────────────────────
def _inventory(
    codx_root: str,
    module_names: Sequence[str],
    warnings: Sequence[str],
) -> ToolResponse:
    """Render the module inventory used when ``query`` is empty."""
    lines: List[str] = [
        "# .codx control plane (NOT the codebase)",
        f"root: `{codx_root}`",
        "",
        "Modules available for `search_codx`:",
        "",
    ]

    for module in module_names:
        spec = MODULES[module]
        files = list(_iter_module_files(codx_root, module))
        total_size = sum(item.size for item in files)
        newest = max((item.mtime for item in files), default=0.0)
        newest_text = (
            time.strftime("%Y-%m-%d", time.gmtime(newest)) if newest else "—"
        )
        examples = sorted(files, key=lambda item: item.mtime, reverse=True)[:2]
        example_text = (
            ", ".join(f"`{item.display_path}`" for item in examples)
            if examples else "—"
        )
        lines.append(
            f"- **{module}** — {len(files)} file(s), {_human_size(total_size)}, "
            f"newest {newest_text}; {spec['label']}."
        )
        if example_text != "—":
            lines.append(f"  e.g. {example_text}")

    lines.extend([
        "",
        "> Use `search_codx(query=\"...\", modules=[...])` to search one or more "
        "modules. `logs` is excluded by default; pass `modules=[\"logs\"]`.",
        "> `db`, `computer_library`, `computer_downloads` and "
        "`browser_downloads` are never text-searched.",
        f"> {_README}",
    ])
    if warnings:
        lines.append("")
        lines.extend(f"> Warning: {warning}" for warning in warnings)

    llm_response = "\n".join(lines)
    user_response = (
        f"Listed {len(module_names)} .codx module(s): "
        + ", ".join(module_names)
        + ". Use search_codx(query=\"...\") to search."
    )
    return ToolResponse(user_response=user_response, llm_response=llm_response)


# ── Search ──────────────────────────────────────────────────────────────────
def _select_matches(
    matches: List[CodxMatch],
    module_names: Sequence[str],
    max_results: int,
) -> List[CodxMatch]:
    """
    Pick a diverse, bounded result set.

    Each module gets up to three best hits first, so a module with many matches
    (tasks) does not hide profiles/sessions; the remaining slots are filled by
    global score/recency.
    """
    ordered = sorted(
        matches, key=lambda item: (-item.score, -item.mtime, item.path, item.field)
    )
    by_module: Dict[str, List[CodxMatch]] = {name: [] for name in module_names}
    for item in ordered:
        by_module.setdefault(item.module, []).append(item)

    selected: List[CodxMatch] = []
    selected_ids: set[Tuple[str, str, str]] = set()

    def _add(item: CodxMatch) -> None:
        key = (item.path, item.field, item.snippet)
        if key in selected_ids or len(selected) >= max_results:
            return
        selected_ids.add(key)
        selected.append(item)

    # Give every module a chance even when max_results is small; with a large
    # limit each module can contribute up to three hits before the global fill.
    per_module_first = max(
        1, min(3, max_results // max(1, len(module_names)))
    )
    for name in module_names:
        for item in by_module.get(name, [])[:per_module_first]:
            _add(item)
    for item in ordered:
        if len(selected) >= max_results:
            break
        _add(item)

    order = {name: index for index, name in enumerate(module_names)}
    selected.sort(key=lambda item: (order.get(item.module, 99), -item.score, -item.mtime))
    return selected


def _render_matches(
    *,
    query: str,
    mode: str,
    module_names: Sequence[str],
    matches: Sequence[CodxMatch],
    scanned_files: int,
    scanned_bytes: int,
    elapsed: float,
    warnings: Sequence[str],
    truncated: bool,
    skipped_large: int,
) -> ToolResponse:
    """Render search hits grouped by module."""
    lines: List[str] = [
        f"# .codx search — `{query}` ({mode})",
        f"modules: {', '.join(module_names)} | scanned {scanned_files} file(s) "
        f"({_human_size(scanned_bytes)}) in {elapsed:.2f}s",
    ]
    if warnings:
        lines.extend(f"> Warning: {warning}" for warning in warnings)
    lines.append(f"> {_README}")
    lines.append("")

    grouped: Dict[str, List[CodxMatch]] = {name: [] for name in module_names}
    for item in matches:
        grouped.setdefault(item.module, []).append(item)

    for module in module_names:
        items = grouped.get(module, [])
        if not items:
            continue
        lines.append(f"## {module} ({len(items)} match(es))")
        for item in items:
            field = item.field
            if not field.startswith("line "):
                field = field or "value"
            lines.append(f"- `{item.path}` — {field}")
            if item.snippet:
                lines.append(f"  {item.snippet}")
        lines.append("")

    if truncated:
        lines.append(
            "> Candidate collection was bounded (per-module/scan cap). The list "
            "above is a ranked sample, not every hit: narrow `modules` or make "
            "the query more specific to see more."
        )
    if skipped_large:
        lines.append(
            f"> Skipped {skipped_large} file(s) larger than "
            f"{_human_size(MAX_CODX_FILE_BYTES)}."
        )
    if not matches:
        lines.append("No matches found.")
        lines.append("")
        lines.append(
            "> Try a different module or a shorter query. For source code use "
            "`project_grep` / `project_search` instead."
        )

    llm_response = "\n".join(lines).strip()
    file_count = len({item.path for item in matches})
    if matches:
        user_response = (
            f"Found {len(matches)} match(es) in {file_count} file(s) across "
            f"{len({item.module for item in matches})} module(s) "
            f"(scanned {scanned_files} file(s), {_human_size(scanned_bytes)}, "
            f"{elapsed:.2f}s)."
        )
    else:
        user_response = (
            f"No matches in .codx modules: {', '.join(module_names)} "
            f"({scanned_files} file(s) scanned)."
        )
    if warnings:
        user_response += f" ({len(warnings)} warning(s))"
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def search_codx(
    query: str = "",
    modules: Optional[Iterable[str] | str] = None,
    mode: str = "text",
    max_results: int = DEFAULT_CODX_RESULTS,
    context_lines: int = 1,
    **kwargs,
) -> ToolResponse:
    """
    Search the ``.codx`` control plane (never the codebase).

    ``.codx`` stores the project's operating data: task cards/boards, AI
    profiles, browser/desktop sessions, views, teams, workspaces, chat-turn
    records, orchestration state, project metadata and logs. It is a different
    namespace from the source tree; the ``project_*`` tools always exclude it.

    Call with an empty ``query`` to list the modules, their file counts/sizes
    and the newest examples. With a query, only the selected ``modules`` are
    searched. JSON files are parsed so a hit reports the JSON field
    (``name``, ``description``, ``messages[3].content``); text files report
    line numbers.

    Safety and performance:

    * only the selected modules are walked (never the whole ``.codx``),
    * ``db``, downloads, binaries, locks and sensitive files are skipped,
    * files > 8 MB, > 3000 files or > 300 MB scanned are reported as truncated,
    * results are bounded by ``max_results`` and grouped by module.

    Args:
        query: Text (or regex) to find. Empty lists the module inventory.
        modules: Module name(s) or aliases. Defaults to all safe modules.
            Valid: ``profiles``, ``tasks``, ``browser_sessions``, ``views``,
            ``teams``, ``workspaces``, ``chat_turns``, ``boards``,
            ``orchestration``, ``project``, ``logs``.
        mode: ``text`` (case-insensitive literal) or ``regex``.
        max_results: Maximum hits returned (1-100).
        context_lines: Context lines for text-file hits (0-5).
        **kwargs: Must include ``settings`` (CODXJuniorSettings).

    Returns:
        ToolResponse with a user summary and a Markdown result block.

    Examples:
        >>> search_codx(query="", settings=settings)
        >>> search_codx("wallet", modules=["tasks"], settings=settings)
        >>> search_codx("browser session", modules=["browser_sessions"],
        ...             settings=settings)
    """
    settings = kwargs.get("settings", None)
    if not settings:
        return ToolResponse(
            user_response="search_codx requires project settings",
            llm_response="Search failed: missing project settings.",
        )

    codx_root = _codx_root(settings)
    if not os.path.isdir(codx_root):
        return ToolResponse(
            user_response=f"No .codx folder found at {codx_root}",
            llm_response=(
                f"No `.codx` folder exists at `{codx_root}`. This project has no "
                "control-plane data to search."
            ),
        )

    module_names, warnings = _resolve_modules(modules)
    query_text = "" if query is None else str(query)
    if not query_text.strip():
        return _inventory(codx_root, module_names, warnings)

    normalized_mode = str(mode or "text").strip().lower()
    if normalized_mode not in ("text", "regex"):
        warnings.append(f"Unknown mode '{mode}'; using text.")
        normalized_mode = "text"
    try:
        matcher = _Matcher(query_text, normalized_mode)
    except re.error as ex:
        return ToolResponse(
            user_response=f"Invalid regular expression: {ex}",
            llm_response=(
                f"Invalid regular expression `{query_text}`: {ex}. "
                "Retry with a literal query (mode=\"text\") or a valid regex."
            ),
        )

    try:
        limit = max(1, min(int(max_results or DEFAULT_CODX_RESULTS), MAX_CODX_RESULTS))
    except (TypeError, ValueError):
        limit = DEFAULT_CODX_RESULTS

    started = time.monotonic()
    scanned_files = 0
    scanned_bytes = 0
    skipped_large = 0
    truncated = False
    collected: List[CodxMatch] = []
    seen_keys: set[Tuple[str, str, str]] = set()

    # Collect a bounded sample PER MODULE, then select globally. Without the
    # per-module cap a task-heavy project fills the collector before profiles
    # and browser sessions are ever searched, hiding the very hits the model
    # asked for.
    per_module_collect = max(10, min(limit * 4, 60))

    for module in module_names:
        files = list(_iter_module_files(codx_root, module))
        # Most recent first: the current task/session is usually what matters.
        files.sort(key=lambda item: item.mtime, reverse=True)
        module_collected = 0

        for item in files:
            if scanned_files >= MAX_CODX_FILES:
                truncated = True
                break
            if scanned_bytes >= MAX_CODX_TOTAL_BYTES:
                truncated = True
                break
            if item.size > MAX_CODX_FILE_BYTES:
                skipped_large += 1
                continue

            scanned_files += 1
            scanned_bytes += item.size
            for score, field, snippet in _search_file(
                item, matcher, context_lines=context_lines
            ):
                key = (item.display_path, field, snippet)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                collected.append(
                    CodxMatch(
                        module=module,
                        path=item.display_path,
                        field=field,
                        snippet=snippet,
                        score=score,
                        mtime=item.mtime,
                    )
                )
                module_collected += 1
                if module_collected >= per_module_collect:
                    truncated = True
                    break
            if module_collected >= per_module_collect:
                break
        if len(collected) >= MAX_CODX_COLLECTED_MATCHES:
            truncated = True
            break

    selected = _select_matches(collected, module_names, limit)
    elapsed = time.monotonic() - started
    logger.info(
        "search_codx: query='%s' modules=%s files=%d bytes=%d matches=%d "
        "selected=%d elapsed=%.2fs",
        query_text,
        module_names,
        scanned_files,
        scanned_bytes,
        len(collected),
        len(selected),
        elapsed,
    )

    return _render_matches(
        query=query_text,
        mode=normalized_mode,
        module_names=module_names,
        matches=selected,
        scanned_files=scanned_files,
        scanned_bytes=scanned_bytes,
        elapsed=elapsed,
        warnings=warnings,
        truncated=truncated,
        skipped_large=skipped_large,
    )


SEARCH_CODX_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "search_codx",
        "description": (
            "Search the `.codx` CONTROL PLANE — NOT the codebase. `.codx` holds "
            "the project's operating data: task cards and boards, AI profiles, "
            "browser/desktop sessions, views, teams, workspaces, chat-turn "
            "records, orchestration state, project metadata and logs. The "
            "project_* tools always exclude `.codx`; use this tool instead of "
            "project_search/project_grep for these questions. "
            "\n\nCall with query=\"\" to list the available modules with file "
            "counts/sizes and examples. Then search with modules=[...]. JSON "
            "hits report the JSON field (name, description, "
            "messages[3].content); text hits report line numbers. "
            "\n\nExamples: search_codx(\"wallet\", modules=[\"tasks\"]); "
            "search_codx(\"browser session\", modules=[\"browser_sessions\"]); "
            "search_codx(\"reviewer\", modules=[\"profiles\"]). "
            "\n\nNever searches `db`, image/download folders, binaries, locks or "
            "sensitive files (.env/keys). Large files (>8 MB) and huge scans are "
            "bounded and reported as truncated."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Text or regex to find. Empty string lists the module "
                        "inventory (counts, sizes, examples)."
                    ),
                },
                "modules": {
                    "type": ["string", "array"],
                    "description": (
                        "Module name(s) or aliases to search. Valid: profiles, "
                        "tasks, browser_sessions, views, teams, workspaces, "
                        "chat_turns, boards, orchestration, project, logs. "
                        "Defaults to all safe modules (logs excluded). "
                        "Aliases include browser/browsers/computers, chat/chats, "
                        "board, run/runs, and all/*."
                    ),
                },
                "mode": {
                    "type": "string",
                    "enum": ["text", "regex"],
                    "description": (
                        "Matching mode. 'text' is a case-insensitive literal; "
                        "'regex' is a Python regular expression. Defaults to text."
                    ),
                    "default": "text",
                },
                "max_results": {
                    "type": "integer",
                    "description": (
                        "Maximum hits returned, grouped by module (1-100). "
                        "Defaults to 30."
                    ),
                    "default": DEFAULT_CODX_RESULTS,
                    "minimum": 1,
                    "maximum": MAX_CODX_RESULTS,
                },
                "context_lines": {
                    "type": "integer",
                    "description": (
                        "Context lines around a text-file match (0-5). "
                        "Defaults to 1. JSON hits use the field value as context."
                    ),
                    "default": 1,
                    "minimum": 0,
                    "maximum": 5,
                },
            },
            "required": [],
        },
    },
}
