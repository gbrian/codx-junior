"""
Cross-turn tool memory for chat conversations.

Why this module exists
----------------------
Every turn of a chat starts a NEW :class:`~codx.junior.ai.smol.smol_agent.SmolAgent`
run. The agent only received the *text* of prior assistant messages as
conversation history: the rich information gathered by the tools of previous
turns (``Message.tool_events``: tool name, parsed arguments, result preview and
the user-facing output) was persisted on the chat but NEVER sent back to the
model. As a result the model re-ran the same ``project_read_file`` /
``project_grep`` / ``project_search`` calls on every user request, "reviewing
the same information" over and over — the slowest and most expensive part of a
chat interaction.

This module distils the tool events already stored on the previous turns of a
conversation into a compact, token-budgeted ``<session_memory>`` block that is
appended to the conversation history of the NEXT turn:

* identical ``(tool, arguments)`` calls are **deduplicated** (the latest result
  wins, the repetition count is reported),
* a compact index of the files already inspected is derived from the read
  tools' arguments,
* results are **truncated head+tail** so a big file still leaves a useful
  trace inside a small budget,
* entries whose target file was **modified later** in the conversation are
  flagged as stale, so the model knows when it must read again,
* tool runs still ``running`` (aborted/crashed) are ignored.

The block is plain text (no model call is made to build it), so it is cheap to
produce and bounded in size. See :func:`build_tool_memory_section`.

Flow
----
flowchart TD
    A[Prior chat messages] --> B[Collect done/error tool events]
    B --> C[Deduplicate by tool + canonical arguments]
    C --> D[Flag entries superseded by a later write]
    D --> E[Build index of files already read]
    E --> F[Render within the token budget]
    F --> G[session_memory block appended to conversation history]
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------

# Maximum characters of the whole <session_memory> block. ~3k tokens: small
# compared to the tool round-trips it replaces, and independent of how many
# tools the conversation has executed.
TOOL_MEMORY_MAX_CHARS: int = 12_000

# Maximum characters of a single tool result excerpt (head + tail).
TOOL_MEMORY_ENTRY_MAX_CHARS: int = 700

# Maximum number of deduplicated tool entries rendered.
TOOL_MEMORY_MAX_ENTRIES: int = 40

# Maximum number of files listed in the "already read" index.
TOOL_MEMORY_MAX_FILES: int = 60

# Maximum characters of the rendered tool arguments.
TOOL_MEMORY_REQUEST_MAX_CHARS: int = 240

# Maximum characters of a single argument value before it is abbreviated.
TOOL_MEMORY_ARG_MAX_CHARS: int = 120

# Share of the excerpt spent on the head of the result (the rest goes to the
# tail, which is where the "end of file"/last matches often live).
TOOL_MEMORY_HEAD_RATIO: float = 0.6

# Status values considered "finished" (a running tool has no usable result).
_FINISHED_STATUSES = frozenset({"done", "error"})

# Keys injected by SmolAgent before calling a tool; they are not model input.
_IGNORED_ARGUMENT_KEYS = frozenset({
    "settings", "session", "chat_id", "tool_cache",
})

# Argument keys that carry file(s) for read/write tools.
_FILE_ARGUMENT_KEYS: Tuple[str, ...] = (
    "file_path", "file_paths", "files", "target_file", "file", "path",
)

# Tool-name heuristics. Tool names are dynamic (profiles/orchestration can add
# tools), so the memory classifies them by intent instead of hard-coding every
# name in the project.
# Read-like tools: their results are worth keeping in the tool memory.
# Matched as whole words (the name is split on ``_``/``-``).
_READ_TOOL_HINTS: Tuple[str, ...] = (
    "read", "grep", "glob", "search", "list", "cat", "show", "inspect",
    "diff", "changes", "view", "describe",
)

# File-content tools: only these contribute to the "already inspected files"
# index. A ``project_grep(path="src")`` scope is NOT a file that was read.
# Matched as whole words (the name is split on ``_``/``-``) so a tool named
# ``thread_manager`` is not mistaken for a reader because of "read".
_FILE_READ_TOOL_HINTS: Tuple[str, ...] = (
    "read", "cat", "show", "inspect", "view", "describe",
)

# Keep in sync with ``smol_agent._tool_invalidates_cache`` (which clears the
# per-run tool cache after a mutation).
_MUTATION_TOOL_HINTS: Tuple[str, ...] = (
    "write", "apply", "delete", "remove", "create", "restore", "modify",
    "save", "update", "edit", "abandon", "close_pr",
)

# A tool name counts as a mutation when it contains one of the hints above.
# Short hints are matched as whole words to avoid false positives such as
# "search" matching "cr" or "edit" matching "credit".
_WHOLE_WORD_HINTS = frozenset({"edit", "save", "update", "create"})


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ToolMemoryEntry:
    """One finished tool call of a previous turn."""

    turn: int
    tool: str
    request: Dict[str, Any]
    status: str
    response: str = ""
    output: str = ""
    error: str = ""
    # Number of identical (tool, arguments) calls collapsed into this entry.
    repeated: int = 1
    # True when the same file was written after this result was produced.
    stale: bool = False
    # Files this entry read (only for file-content read tools, see
    # :func:`is_file_read_tool`).
    files: List[str] = field(default_factory=list)

    @property
    def result_text(self) -> str:
        """Return the best available result text for the model."""
        return self.response or self.output or self.error or ""

    def dedupe_key(self) -> Tuple[str, str]:
        """
        Return the identity of this call: tool + canonical arguments.

        The canonical arguments are hashed so a write tool carrying a whole
        file does not keep a huge string as a dictionary key.
        """
        canonical = _canonical_request(self.request)
        return self.tool, hashlib.sha1(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _canonical_request(request: Dict[str, Any]) -> str:
    """
    Return a deterministic string for a tool request.

    Used as the deduplication key, so key order must not matter. Values that
    cannot be serialised fall back to ``str`` (the event request always comes
    from JSON, but older/custom tools may store something else).

    :param request: Parsed tool arguments (may be None).
    :return: Canonical string representation.
    """
    try:
        return json.dumps(request or {}, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(request)


def _truncate(text: str, max_chars: int) -> str:
    """Truncate *text* to *max_chars*, marking the cut."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n… (truncated)"


def _excerpt(text: str, max_chars: int) -> str:
    """
    Return a head+tail excerpt of *text*.

    The head usually contains imports/definitions/first matches and the tail
    contains the end of the file or the last matches, so splitting the budget
    keeps more useful signal than a plain prefix.

    :param text: Full text to excerpt.
    :param max_chars: Maximum characters to return.
    :return: The excerpt (unchanged when it already fits).
    """
    if not text:
        return ""
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text

    marker = "\n… (result truncated)\n"
    budget = max(0, max_chars - len(marker))
    head_chars = int(budget * TOOL_MEMORY_HEAD_RATIO)
    tail_chars = budget - head_chars
    head = text[:head_chars]
    # Cut at a line boundary so the excerpt does not start/end mid-word, but
    # keep the raw head when the split would throw away most of the budget
    # (single-line results such as JSON or a long log line).
    head_cut = head.rfind("\n")
    if head_cut > head_chars // 2:
        head = head[:head_cut]
    head = head.rstrip()
    tail = text[-tail_chars:] if tail_chars else ""
    tail_cut = tail.find("\n")
    if tail_cut != -1 and tail_cut < tail_chars // 2:
        tail = tail[tail_cut + 1:]
    tail = tail.lstrip()
    if tail:
        return f"{head}{marker}{tail}"
    return head + "\n… (result truncated)"


# Argument keys whose value is a whole document/payload: showing a prefix of
# it wastes the memory budget, so only the size is reported.
_LARGE_VALUE_KEYS = frozenset({"content", "data", "script", "body", "text"})

# Argument keys that carry a batch of edits; only the count is reported.
_BATCH_VALUE_KEYS = frozenset({"changes", "edits", "patches"})


def _stringify_argument(key: str, value: Any) -> str:
    """
    Render a single tool argument value compactly.

    :param key: Argument name (used to abbreviate payload arguments).
    :param value: Argument value.
    :return: Compact string representation.
    """
    if isinstance(value, str):
        if key in _LARGE_VALUE_KEYS and len(value) > TOOL_MEMORY_ARG_MAX_CHARS:
            return f"<{len(value)} chars>"
        return _truncate(value, TOOL_MEMORY_ARG_MAX_CHARS).replace("\n", "\\n")
    if isinstance(value, (list, tuple)):
        if key in _BATCH_VALUE_KEYS:
            return f"<{len(value)} item(s)>"
        rendered = [_stringify_argument(key, item) for item in value[:8]]
        if len(value) > 8:
            rendered.append(f"… {len(value) - 8} more")
        return "[" + ", ".join(rendered) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{name}: …" for name in list(value)[:6]) + "}"
    return str(value)


def _format_request(request: Dict[str, Any]) -> str:
    """
    Render tool arguments as a compact ``key=value, key=value`` string.

    Argument values are abbreviated so a ``project_write_file`` call carrying
    a whole file does not blow the memory budget.

    :param request: Parsed tool arguments.
    :return: Compact rendering (empty string when there are no arguments).
    """
    if not request:
        return ""
    parts: List[str] = []
    for key, value in request.items():
        if key in _IGNORED_ARGUMENT_KEYS:
            continue
        if value is None or value == "" or value == [] or value == {}:
            continue
        parts.append(f"{key}={_stringify_argument(key, value)}")
    rendered = ", ".join(parts)
    return _truncate(rendered, TOOL_MEMORY_REQUEST_MAX_CHARS)


def _tool_name_matches(name: str, hints: Iterable[str]) -> bool:
    """Return True when *name* matches any intent hint."""
    lowered = (name or "").lower()
    words = lowered.replace("-", "_").split("_")
    for hint in hints:
        if hint in _WHOLE_WORD_HINTS:
            if hint in words:
                return True
        elif hint in lowered:
            return True
    return False


def is_mutation_tool(tool_name: str) -> bool:
    """Return True when *tool_name* looks like it changes files/state."""
    return _tool_name_matches(tool_name, _MUTATION_TOOL_HINTS)


def is_read_tool(tool_name: str) -> bool:
    """
    Return True when *tool_name* looks like a read/discovery tool.

    Mutation tools are never classified as read even when their name contains
    a read-ish word: ``apply_file_changes`` contains ``changes`` but writes.
    """
    if is_mutation_tool(tool_name):
        return False
    words = (tool_name or "").lower().replace("-", "_").split("_")
    return any(hint in words for hint in _READ_TOOL_HINTS)


def is_file_read_tool(tool_name: str) -> bool:
    """
    Return True when *tool_name* returns file CONTENT (not a search scope).

    Only these tools populate the "already inspected files" index. A
    ``project_grep(path="src")`` call searches inside ``src``; it does not mean
    that ``src`` itself was read.
    """
    if is_mutation_tool(tool_name):
        return False
    words = (tool_name or "").lower().replace("-", "_").split("_")
    return any(hint in words for hint in _FILE_READ_TOOL_HINTS)


def _normalise_path(value: Any) -> Optional[str]:
    """Return a clean project-relative path candidate, or None."""
    if not isinstance(value, str):
        return None
    path = value.strip().strip('"\'')
    if not path or "\n" in path or len(path) > 400:
        return None
    if path in (".", "./", "/", "~"):
        return None
    # Ignore globs: they are search patterns, not files that were read.
    if any(char in path for char in "*?["):
        return None
    # Only the explicit "./" prefix is normalised: ".." must be preserved so
    # a parent-relative path is not confused with a project-relative one.
    if not path.startswith("/") and path.startswith("./"):
        path = path[2:]
    return path


def _extract_file_paths(
    tool_name: str,
    request: Dict[str, Any],
    *,
    include_path_key: bool = True,
) -> List[str]:
    """
    Extract the file paths a tool call targets.

    Only file-like arguments are considered (``file_path``, ``files`` ...),
    so a ``project_grep`` pattern is never mistaken for a file. Globs are
    ignored: they match many files and are not "already read".

    :param tool_name: Name of the tool (used for logging only).
    :param request: Parsed tool arguments.
    :param include_path_key: Whether the generic ``path`` key is considered
                             (read tools) or only explicit file keys.
    :return: Deduplicated path list, order preserved.
    """
    keys = _FILE_ARGUMENT_KEYS if include_path_key else tuple(
        key for key in _FILE_ARGUMENT_KEYS if key != "path"
    )
    paths: List[str] = []
    seen = set()
    for key in keys:
        value = request.get(key)
        values = value if isinstance(value, (list, tuple)) else [value]
        for item in values:
            path = _normalise_path(item)
            if path and path not in seen:
                seen.add(path)
                paths.append(path)
    if not paths:
        logger.debug(
            "ToolMemory: no file paths extracted for tool '%s'", tool_name
        )
    return paths


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def extract_tool_file_paths(
    tool_name: str,
    request: Dict[str, Any],
    *,
    include_path_key: bool = True,
) -> List[str]:
    """
    Return the file paths a tool call targets (public helper).

    Other features (the git Validator correlates tasks with changed files) need
    the same path extraction used by this module, so it is exposed instead of
    importing the private helper.

    :param tool_name: Name of the tool.
    :param request: Parsed tool arguments.
    :param include_path_key: Whether the generic ``path`` key is considered.
    :return: Deduplicated path list, order preserved.
    """
    return _extract_file_paths(
        tool_name, request or {}, include_path_key=include_path_key
    )


def _iter_tool_events(message: Any) -> Iterable[Any]:
    """Yield the tool events of *message* (defensive: attribute may be None)."""
    for event in getattr(message, "tool_events", None) or []:
        yield event


def collect_tool_memory(messages: Sequence[Any]) -> List[ToolMemoryEntry]:
    """
    Collect the finished tool calls of *messages*, oldest first.

    Hidden/improvement messages are skipped. Events that never finished
    (``status == "running"``) are ignored: they carry no reusable result.

    :param messages: Prior messages in chronological order (ancestors first).
    :return: Tool memory entries in conversation order (not deduplicated yet).
    """
    entries: List[ToolMemoryEntry] = []
    for index, message in enumerate(messages):
        if getattr(message, "hide", False) or getattr(message, "improvement", False):
            continue
        for event in _iter_tool_events(message):
            status = str(getattr(event, "status", "") or "").lower()
            if status not in _FINISHED_STATUSES:
                logger.debug(
                    "ToolMemory: skipping '%s' with status '%s'",
                    getattr(event, "tool", "?"),
                    status,
                )
                continue
            tool = str(getattr(event, "tool", "") or "unknown")
            request = getattr(event, "request", None) or {}
            if not isinstance(request, dict):
                request = {"value": request}
            entry = ToolMemoryEntry(
                turn=index + 1,
                tool=tool,
                request=request,
                status=status,
                response=str(getattr(event, "response", "") or ""),
                output=str(getattr(event, "output", "") or ""),
                error=str(getattr(event, "error", "") or ""),
            )
            entry.files = _extract_file_paths(
                tool,
                request,
                # Only a content-read tool treats ``path`` as a file: a grep
                # scope would otherwise appear as an "already read" file.
                include_path_key=is_file_read_tool(tool),
            )
            entries.append(entry)
    return entries


def _deduplicate(entries: Sequence[ToolMemoryEntry]) -> List[ToolMemoryEntry]:
    """
    Collapse identical ``(tool, arguments)`` calls into a single entry.

    The LATEST result wins (it reflects the most recent state) and the
    repetition count is accumulated. Entries are re-sorted by their LATEST
    call so the rendered memory is chronological and the newest-first budget
    pass selects the most recent work.

    :param entries: Entries as returned by :func:`collect_tool_memory`.
    :return: Deduplicated entries in chronological order (by latest call).
    """
    collapsed: Dict[Tuple[str, str], ToolMemoryEntry] = {}
    repeats: Dict[Tuple[str, str], int] = {}
    for entry in entries:
        key = entry.dedupe_key()
        repeats[key] = repeats.get(key, 0) + 1
        collapsed[key] = entry
    result: List[ToolMemoryEntry] = []
    for key, entry in collapsed.items():
        entry.repeated = repeats[key]
        result.append(entry)
    # Stable sort: entries sharing a turn keep their collection order.
    result.sort(key=lambda item: item.turn)
    return result


def _extract_mutations(entries: Sequence[ToolMemoryEntry]) -> List[Tuple[int, str]]:
    """
    Return ``(entry position, path)`` pairs for every write-like call.

    Paths are only extracted from explicit file arguments (never from the
    generic ``path`` key) to avoid treating a grep scope as a written file.

    :param entries: Chronological entries (deduplicated).
    :return: List of mutation markers.
    """
    mutations: List[Tuple[int, str]] = []
    for position, entry in enumerate(entries):
        if not is_mutation_tool(entry.tool):
            continue
        for path in _extract_file_paths(
            entry.tool, entry.request, include_path_key=False
        ):
            mutations.append((position, path))
    return mutations


def _mark_stale(entries: List[ToolMemoryEntry]) -> None:
    """
    Flag read entries whose file was modified by a LATER tool call.

    The result stored for a read is a snapshot: when a following ``write`` /
    ``apply_file_changes`` touched the same file, the model must not trust the
    excerpt anymore. ``entry.stale`` lets the renderer say so explicitly.

    :param entries: Deduplicated entries (mutated in place).
    """
    mutations = _extract_mutations(entries)
    if not mutations:
        return
    for position, entry in enumerate(entries):
        if not entry.files or not is_file_read_tool(entry.tool):
            continue
        for mutation_position, mutated_path in mutations:
            if mutation_position <= position:
                continue
            if any(_paths_match(path, mutated_path) for path in entry.files):
                entry.stale = True
                break


def _paths_match(read_path: str, mutated_path: str) -> bool:
    """Return True when two project paths refer to the same file."""
    read_path = read_path.strip()
    mutated_path = mutated_path.strip()
    if read_path.startswith("./"):
        read_path = read_path[2:]
    if mutated_path.startswith("./"):
        mutated_path = mutated_path[2:]
    if read_path == mutated_path:
        return True
    # An absolute path read and a relative path write (or vice versa).
    return read_path.endswith("/" + mutated_path) or mutated_path.endswith(
        "/" + read_path
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_MEMORY_HEADER = """\
<session_memory>
Information already gathered by tools in EARLIER turns of this conversation.
It is provided so you DO NOT repeat that work.

Rules:
- Do NOT call a tool again with the same arguments shown here: its result is already below.
- Read a file again ONLY if you need lines that are not shown, or if the entry is marked stale.
- Prefer paging a large file with start_line/end_line over re-reading all of it.
- This memory is a summary; when exact content matters, read only the lines you need.
"""

_MEMORY_FOOTER = "</session_memory>"


def render_tool_memory(
    entries: Sequence[ToolMemoryEntry],
    *,
    max_chars: int = TOOL_MEMORY_MAX_CHARS,
    entry_max_chars: int = TOOL_MEMORY_ENTRY_MAX_CHARS,
    max_entries: int = TOOL_MEMORY_MAX_ENTRIES,
    max_files: int = TOOL_MEMORY_MAX_FILES,
) -> str:
    """
    Render tool memory entries as a bounded ``<session_memory>`` block.

    :param entries: Deduplicated entries (see :func:`collect_tool_memory`).
    :param max_chars: Hard limit for the returned block.
    :param entry_max_chars: Per-entry result excerpt budget.
    :param max_entries: Maximum number of entries.
    :param max_files: Maximum number of files in the index.
    :return: The rendered block, or an empty string when there is nothing.
    """
    block, _ = _render_tool_memory(entries, max_chars=max_chars,
                                   entry_max_chars=entry_max_chars,
                                   max_entries=max_entries,
                                   max_files=max_files)
    return block


def _render_tool_memory(
    entries: Sequence[ToolMemoryEntry],
    *,
    max_chars: int,
    entry_max_chars: int,
    max_entries: int,
    max_files: int,
) -> Tuple[str, int]:
    """
    Render tool memory and report how many entries were actually rendered.

    The newest entries are selected first (they describe the current state of
    the conversation) and then rendered chronologically. The file index is
    rendered first when it fits: it is the most compact and most useful part
    of the memory.

    :return: Tuple of ``(block, rendered_entries)``.
    """
    if not entries or max_chars <= 0:
        return "", 0

    # The file index must never eat the whole budget: give it at most ~35% of
    # the block (bounded to a sensible absolute size) and leave the rest for
    # the tool results.
    files_budget = min(max(0, int(max_chars * 0.35)), 4_000)
    files_block = _render_files_index(
        entries,
        max_files=max_files,
        max_chars=files_budget,
    )
    fixed_chars = len(_MEMORY_HEADER) + len(_MEMORY_FOOTER) + 1
    if files_block:
        fixed_chars += len(files_block) + 1
    available = max_chars - fixed_chars
    if available <= 0:
        # Degrade gracefully: return the header-only block rather than an
        # over-budget one (a zero/very small budget must never break a turn).
        return "", 0

    selected: List[str] = []
    # Walk backwards so the most recent calls are kept when the budget is tight.
    for entry in reversed(list(entries)):
        if len(selected) >= max_entries:
            break
        block = _render_entry(entry, entry_max_chars)
        if len(block) + 1 > available:
            # Try to fit a shorter excerpt before giving up on this entry.
            if available < 160:
                break
            block = _render_entry(entry, max(80, available - 80))
        if len(block) + 1 > available:
            break
        selected.append(block)
        available -= len(block) + 1

    selected.reverse()
    if not selected and not files_block:
        return "", 0

    body_parts: List[str] = []
    if files_block:
        body_parts.append(files_block)
    body_parts.extend(selected)
    body = "\n".join(body_parts)

    block = f"{_MEMORY_HEADER}\n{body}\n{_MEMORY_FOOTER}"
    if len(block) > max_chars:
        block = block[:max_chars]
    return block, len(selected)


def _render_files_index(
    entries: Sequence[ToolMemoryEntry],
    *,
    max_files: int,
    max_chars: int = 0,
) -> str:
    """
    Render the "files already read" index.

    :param entries: Deduplicated entries.
    :param max_files: Maximum number of files listed.
    :param max_chars: Optional budget for the index. When it is reached the
                      list is truncated and the omitted count is reported.
    :return: Rendered section (empty when no file was read).
    """
    latest: Dict[str, ToolMemoryEntry] = {}
    for entry in entries:
        if not entry.files or not is_file_read_tool(entry.tool):
            continue
        for path in entry.files:
            latest[path] = entry

    if not latest:
        return ""

    header = "Already inspected files (content was returned in earlier turns):"
    ordered = sorted(latest.items(), key=lambda item: item[1].turn)

    # Select newest-first so the budget keeps the files that matter most, then
    # render chronologically for readability.
    selected: List[str] = []
    rendered_chars = len(header)
    for path, entry in reversed(ordered):
        if len(selected) >= max_files:
            break
        stale = " — STALE: modified later, re-read before using it" if entry.stale else ""
        line = f"- {path} ({entry.tool}, turn {entry.turn}{stale})"
        if max_chars and rendered_chars + len(line) + 1 > max_chars:
            break
        selected.append(line)
        rendered_chars += len(line) + 1
    selected.reverse()

    lines = [header] + selected
    omitted = len(ordered) - len(selected)
    if omitted > 0:
        lines.append(f"- … {omitted} more file(s) omitted")
    return "\n".join(lines)


def _render_entry(entry: ToolMemoryEntry, entry_max_chars: int) -> str:
    """
    Render one tool call with its (truncated) result.

    :param entry: Entry to render.
    :param entry_max_chars: Result excerpt budget.
    :return: Rendered entry block.
    """
    request = _format_request(entry.request)
    head = f"[turn {entry.turn}] {entry.tool}"
    if request:
        head += f"({request})"
    head += f" — {entry.status}"
    if entry.repeated > 1:
        head += f" (called {entry.repeated}x; latest result shown)"
    if entry.stale:
        head += " (STALE: the file changed afterwards)"

    result = _excerpt(entry.result_text, entry_max_chars)
    if not result:
        return head
    return f"{head}\n{_indent(result)}"


def _indent(text: str) -> str:
    """Indent a multi-line excerpt with two spaces for readability."""
    return "\n".join(f"  {line}" for line in text.splitlines())


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_tool_memory_section(
    messages: Sequence[Any],
    *,
    max_chars: int = TOOL_MEMORY_MAX_CHARS,
    entry_max_chars: int = TOOL_MEMORY_ENTRY_MAX_CHARS,
    max_entries: int = TOOL_MEMORY_MAX_ENTRIES,
) -> Tuple[str, Dict[str, int]]:
    """
    Build the ``<session_memory>`` block for the prior messages of a turn.

    :param messages: Prior VISIBLE messages in chronological order (parent
                     chats first, current chat last). The current user message
                     must already be excluded.
    :param max_chars: Hard limit for the returned block.
    :param entry_max_chars: Per-entry result excerpt budget.
    :param max_entries: Maximum number of entries.
    :return: Tuple of ``(block, stats)``. ``stats`` carries ``calls``
             (finished tool calls found), ``entries`` (after deduplication),
             ``rendered`` (entries actually shown within the budget),
             ``files`` (already inspected files) and ``chars`` (size of the
             block). The block is an empty string when the conversation has no
             reusable tool results.
    """
    raw_entries = collect_tool_memory(messages)
    if not raw_entries:
        return "", {"calls": 0, "entries": 0, "rendered": 0, "files": 0, "chars": 0}

    entries = _deduplicate(raw_entries)
    _mark_stale(entries)

    block, rendered = _render_tool_memory(
        entries,
        max_chars=max_chars,
        entry_max_chars=entry_max_chars,
        max_entries=max_entries,
        max_files=TOOL_MEMORY_MAX_FILES,
    )
    stats = {
        "calls": len(raw_entries),
        "entries": len(entries),
        "rendered": rendered,
        "files": len({
            path
            for entry in entries
            for path in entry.files
            if is_file_read_tool(entry.tool)
        }),
        "chars": len(block),
    }
    if stats["calls"]:
        logger.info(
            "ToolMemory: %d prior tool call(s) collapsed into %d entr(ies) "
            "(%d rendered); %d file(s) already inspected; block of %d chars",
            stats["calls"],
            stats["entries"],
            stats["rendered"],
            stats["files"],
            stats["chars"],
        )
    return block, stats
