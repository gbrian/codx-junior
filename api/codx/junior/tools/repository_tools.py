"""
Repository tools for codx-junior.

Agent facing helpers behind the ``repository`` profile. They turn the git
repository into plain, human readable facts and they build commit messages that
follow the **50/72 rule**:

- :func:`repository_overview`: where the repository stands (branch, sync,
  working tree, lock, worktrees, last commits).
- :func:`repository_status`: what is staged, what is not, what is untracked.
- :func:`repository_branches`: local/remote branches with their tip commit.
- :func:`repository_log`: history of a branch or of a single file.
- :func:`repository_compare`: differences between two refs, with the commits in
  between.
- :func:`repository_commit_message`: 50/72 compliant commit message draft, built
  from the staged content.

Commit messages: how they are built
-----------------------------------
A commit message has two parts with different jobs:

- **Subject**: *what the commit does*, imperative mood (``add``, ``fix``,
  ``rename``), at most **50 characters** so ``git log --oneline`` and the forge
  sidebars never truncate it.
- **Body**: *why the change exists*, at most **72 characters per line** (the
  width of a terminal or a mail client), separated from the subject by one blank
  line. The diff already says *what* changed, so the body explains the reason,
  the trade-off or the follow-up.

Reading the staged content
--------------------------
A file list says *which* files change; it does not say *what* they do. Before a
message is written, :func:`repository_commit_message` therefore reads the
**staged content** of every changed file (the blob in the index, ``git show
:<path>``), together with the staged patch and the per-file line counts. New,
renamed and modified files all come with their real code, so the model can
recognise the intent (a new endpoint, a fixed condition, a renamed symbol)
instead of guessing it from a file name.

The reading is bounded: at most ``MAX_CONTENT_FILES`` files,
``MAX_FILE_CONTENT_CHARS`` characters per file and ``MAX_CONTENT_CHARS``
characters in total. Binary, deleted and empty files are skipped, and the files
left out are still listed, never silently dropped.

The tools cannot read the developer's intent. :func:`repository_commit_message`
therefore builds a **compliant draft** from the facts it can prove (conventional
type inferred from the paths, scope from the common folder, per-file status and
line counts, staged content, user hint) and returns those facts to the model so
it can rewrite the subject with the real intent and turn the content into a
*why*-focused body. The draft is always valid on its own: if the model changes
nothing, the user still gets a message that respects the rule.

```mermaid
flowchart TD
    subgraph tools[repository_*]
        overview[repository_overview]
        status[repository_status]
        branches[repository_branches]
        log[repository_log]
        compare[repository_compare]
        message[repository_commit_message]
    end
    overview --> get_repo_info
    overview --> get_commit_list
    status --> _collect_changes
    branches --> get_repo_graph
    log --> get_commit_list
    log --> get_file_history
    compare --> _run_git
    message --> _collect_changes
    message --> _build_commit_draft
    _collect_changes --> _run_diff
    _collect_changes --> _collect_contents
    _collect_contents --> _read_scope_content
    _build_commit_draft --> normalize_commit_message
    normalize_commit_message --> _truncate_commit_line
    normalize_commit_message --> _wrap_commit_body
```

Every tool is read only: they inspect the repository, they never stage, commit,
push or delete anything.

Made with ❤️ by codx-junior
"""

import json
import logging
import os
import re
import textwrap

from typing import Dict, List, Optional, Tuple

from codx.junior.settings import CODXJuniorSettings
from .model import ToolResponse

logger = logging.getLogger(__name__)

# 50/72 rule: maximum subject length and maximum body line width
COMMIT_SUBJECT_LIMIT = 50
COMMIT_BODY_LIMIT = 72

# Maximum characters of a patch included in a tool response
MAX_DIFF_CHARS = 6000

# Maximum characters of changed file content included in a commit message prompt
MAX_CONTENT_CHARS = 8000

# Maximum number of files whose content is included
MAX_CONTENT_FILES = 10

# Files bigger than this contribute only their first characters
MAX_FILE_CONTENT_CHARS = 4000

# Maximum files listed in a tool response (bigger commits are summarised)
MAX_FILES_IN_SUMMARY = 40

# Maximum commits returned by repository_log
MAX_LOG_LIMIT = 100

# Empty tree object: diff target used while the repository has no commits yet
EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# git status/diff status code -> human readable status
STATUS_LABELS = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "T": "typechange",
    "U": "conflict",
    "?": "untracked",
}

# Icon per status, so the summaries are scannable
STATUS_ICONS = {
    "added": "➕",
    "modified": "✏️",
    "deleted": "🗑️",
    "renamed": "➡️",
    "copied": "📄",
    "typechange": "🔀",
    "conflict": "⚠️",
    "untracked": "❓",
}

# List markers kept as a hanging indent when the body is wrapped
LIST_MARKER_PATTERN = re.compile(r"^([-*+]\s+|\d+[.)]\s+)")

# Path hints used to infer the conventional commit type from the changed files
COMMIT_TYPE_HINTS: List[Tuple[str, Tuple[str, ...]]] = [
    ("docs", ("docs/", ".md", ".mdx", ".rst")),
    ("test", ("tests/", "test/", "test_", "_test.", ".spec.", ".test.")),
    ("ci", (".github/", ".gitlab-ci", "jenkins", "azure-pipelines")),
    (
        "build",
        (
            "dockerfile",
            "docker-compose",
            "requirements",
            "pyproject.toml",
            "package.json",
            "poetry.lock",
            "makefile",
        ),
    ),
]


class _RepoSession:
    """
    Minimal session facade for :class:`codx.junior.engine.git_graph.GitGraphEngine`.

    Tools are executed by the agent runtime, which injects ``settings`` for the
    tools declared with ``project_settings=True``. ``GitGraphEngine`` only reads
    ``session.settings`` (and logs through ``session.log_info``), so this facade
    is enough to build a full repository engine from the project settings.

    Attributes:
        settings: Project settings the engine operates on.
    """

    def __init__(self, settings: CODXJuniorSettings) -> None:
        self.settings = settings

    def log_info(self, msg: str, *args) -> None:
        """Mirror CODXJuniorSession.log_info for engine methods that log."""
        logger.info("[%s] " + msg, self.settings.project_name, *args)


def _resolve_repo_engine(**kwargs):
    """
    Resolve the repository engine for the current tool execution.

    Resolution order:
        1. The injected project session (``session``), which already carries the
           settings the engine needs.
        2. The project ``settings`` injected by the runtime, wrapped in a
           :class:`_RepoSession` facade.

    :class:`GitGraphEngine` is used (instead of the plain ``GitEngine`` exposed
    by ``session.get_git_engine()``) because the repository tools need the graph
    and working tree operations: ``get_repo_info``, ``get_repo_graph``,
    ``get_commit_detail``, ``get_status_changes``, ``list_worktrees``...

    Args:
        **kwargs: Tool keyword arguments; ``session`` and/or ``settings`` are
            injected by the agent runtime.

    Returns:
        A :class:`GitGraphEngine` bound to the project.

    Raises:
        Exception: When neither a project session nor project settings are
            available.
    """
    from codx.junior.engine.git_graph import GitGraphEngine

    session = kwargs.get("session")
    settings = kwargs.get("settings") or getattr(session, "settings", None)
    if settings is None:
        raise Exception(
            "Invalid session - repository engine not available "
            "(no project session or project settings injected)"
        )

    if session is not None and getattr(session, "settings", None) is not None:
        return GitGraphEngine(session=session)

    return GitGraphEngine(session=_RepoSession(settings=settings))


def _error_response(tool_name: str, error: Exception) -> ToolResponse:
    """
    Build the response returned when a tool cannot read the repository.

    Args:
        tool_name: Tool that failed.
        error: Exception raised while talking to git.

    Returns:
        ToolResponse describing the failure to both the user and the model.
    """
    message = f"{type(error).__name__}: {error}"
    logger.exception("%s failed: %s", tool_name, error)
    return ToolResponse(
        user_response=(
            f"⚠️ **{tool_name}** could not read the repository\n\n> {message}"
        ),
        llm_response=f"{tool_name} failed: {message}",
    )


# -----------------------------------------------------------------------------
# Rendering helpers
# -----------------------------------------------------------------------------


def _truncate(text: str, limit: int = MAX_DIFF_CHARS) -> str:
    """
    Truncate a long text (a patch) keeping the result readable.

    Args:
        text: Text to truncate.
        limit: Maximum number of characters (0 disables the truncation).

    Returns:
        The text unchanged when it fits, a cut version plus a marker otherwise.
    """
    text = text or ""
    if limit and len(text) > limit:
        return text[:limit].rstrip() + "\n... (truncated)"
    return text


def _render_files(files: List[dict], limit: int = MAX_FILES_IN_SUMMARY) -> List[str]:
    """
    Render changed files as readable bullets.

    Args:
        files: Entries with 'path', 'code', 'status', 'additions', 'deletions'.
        limit: Maximum number of files listed.

    Returns:
        One bullet per file (plus, when needed, a "more files" bullet).

    Example:
        >>> _render_files([{"path": "app.py", "code": "M", "status": "modified",
        ...                 "additions": 2, "deletions": 1}])
        ['- ✏️ modified: `app.py` (+2/-1)']
    """
    lines: List[str] = []

    for file in files[:limit]:
        code = file.get("code") or "M"
        status = file.get("status") or STATUS_LABELS.get(code, "modified")
        icon = STATUS_ICONS.get(status, "•")
        counts = ""
        additions = file.get("additions") or 0
        deletions = file.get("deletions") or 0
        if additions or deletions:
            counts = f" (+{additions}/-{deletions})"
        lines.append(f"- {icon} {status}: `{file.get('path')}`{counts}")

    remaining = len(files) - limit
    if remaining > 0:
        lines.append(f"- ... and {remaining} more file(s)")

    return lines


def _stats_line(files: List[dict]) -> str:
    """
    Build the "N files changed, +A/-D" line of a change set.

    Args:
        files: Entries with 'additions' and 'deletions'.

    Returns:
        One line summary of the change size.
    """
    additions = sum((file.get("additions") or 0) for file in files)
    deletions = sum((file.get("deletions") or 0) for file in files)
    return f"{len(files)} file(s) changed, +{additions}/-{deletions}"


def _commit_line(short: str, date: str, author: str, subject: str) -> str:
    """
    Render one commit as a readable bullet.

    Args:
        short: Short commit hash.
        date: Commit date (ISO string).
        author: Author name.
        subject: Commit subject.

    Returns:
        Bullet with the hash, the date, the author and the subject.
    """
    return (
        f"- `{short or '?'}` {(date or '')[:10]} · {author or '?'} · {subject or ''}"
    ).rstrip()


# -----------------------------------------------------------------------------
# Diff helpers
# -----------------------------------------------------------------------------


def _scope_args(scope: str, flags: List[str]) -> Tuple[List[str], Optional[List[str]]]:
    """
    Build the ``git diff`` arguments of a scope and their empty-tree fallback.

    Scopes:
        - ``staged``: index against HEAD (what the next commit would contain).
        - ``unstaged``: index against the working tree (tracked changes only).
        - ``worktree``: HEAD against the working tree (everything not committed).

    A repository without commits has no HEAD to diff against, so a second
    argument list using the empty tree hash is returned as fallback.

    Args:
        scope: 'staged', 'unstaged' or 'worktree'.
        flags: Diff flags, e.g. ``["--numstat"]``.

    Returns:
        Tuple of ``(args, fallback_args)``; ``fallback_args`` is None when no
        fallback is needed.

    Example:
        >>> _scope_args("staged", ["--shortstat"])
        (['diff', '--cached', '--shortstat'],
         ['diff', '--cached', '--shortstat', '4b825dc...'])
    """
    if scope == "staged":
        args = ["diff", "--cached"] + list(flags)
        return args, args + [EMPTY_TREE_HASH]

    if scope == "unstaged":
        args = ["diff"] + list(flags)
        return args, None

    return (
        ["diff"] + list(flags) + ["HEAD"],
        ["diff"] + list(flags) + [EMPTY_TREE_HASH],
    )


def _run_diff(engine, args: List[str], fallback_args: Optional[List[str]] = None) -> dict:
    """
    Run a diff command, retrying on the empty tree when HEAD does not exist.

    Args:
        engine: Repository engine.
        args: Arguments of the first attempt.
        fallback_args: Arguments retried when the first attempt fails.

    Returns:
        Dict returned by ``_run_git`` (``ok``, ``output``, ``error``).
    """
    result = engine._run_git(args)
    if result["ok"] or not fallback_args:
        return result

    retry = engine._run_git(fallback_args)
    return retry if retry["ok"] else result


def _read_scope_content(engine, path: str, scope: str) -> str:
    """
    Read the content of a changed file in the state the scope represents.

    The content is read from the **index** for the ``staged`` scope (``git show
    :<path>``), so it is exactly what ``git commit`` would record, not what the
    developer still has on disk. For the working tree scopes the file is read
    from disk.

    Args:
        engine: Repository engine.
        path: Repo-relative file path.
        scope: 'staged' (index), 'unstaged' or 'worktree' (working tree).

    Returns:
        File content, or an empty string when it cannot be read (deleted,
        binary, unknown path).

    Example:
        >>> _read_scope_content(engine, "app.py", "staged")[:10]
        'print(1)\\n'
    """
    if not path:
        return ""

    if scope == "staged":
        result = engine._run_git(["show", f":{path}"])
        return result["output"] if result["ok"] else ""

    repo_root = engine._get_repo_root()
    abs_path = path if os.path.isabs(path) else os.path.join(repo_root, path)
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as ex:
        logger.debug("Could not read %s: %s", abs_path, ex)
        return ""


def _content_language(path: str) -> str:
    """
    Return a code fence language from a file extension.

    Args:
        path: File path (repo-relative or absolute).

    Returns:
        Extension as the fence language, ``txt`` when the file has none.

    Example:
        >>> _content_language("codx/junior/api/git.py")
        'py'
    """
    name = (path or "").rsplit("/", 1)[-1]
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return extension or "txt"


def _collect_contents(
    engine,
    files: List[dict],
    scope: str,
    max_files: int = MAX_CONTENT_FILES,
    max_file_chars: int = MAX_FILE_CONTENT_CHARS,
    budget: int = MAX_CONTENT_CHARS,
) -> List[dict]:
    """
    Collect the content of the changed files, within a bounded budget.

    Deleted, binary and empty files are skipped: their content cannot help to
    understand the change. Every other file contributes at most
    *max_file_chars* characters, and the whole set at most *budget* characters,
    so a huge commit never blows up the prompt.

    Args:
        engine: Repository engine.
        files: Entries with 'path', 'code', 'status' and 'binary'.
        scope: Scope the content is read from ('staged', 'worktree'...).
        max_files: Maximum number of files with content.
        max_file_chars: Maximum characters per file.
        budget: Maximum characters in total.

    Returns:
        List of dicts with 'path', 'status', 'content' and 'truncated'.

    Example:
        >>> entries = _collect_contents(engine, files, "staged")
        >>> entries[0]["path"]
        'codx/junior/api/git.py'
    """
    contents: List[dict] = []
    remaining = budget

    for file in files:
        if len(contents) >= max_files or remaining <= 0:
            break
        if file.get("code") == "D" or file.get("binary"):
            continue

        path = file.get("path") or ""
        content = _read_scope_content(engine, path, scope)
        if not content.strip():
            continue

        truncated = len(content) > max_file_chars
        excerpt = content[:max_file_chars]
        if truncated:
            excerpt = excerpt.rstrip() + "\n... (file truncated)"

        if len(excerpt) > remaining:
            excerpt = excerpt[:remaining].rstrip() + "\n... (content budget reached)"
            truncated = True
        remaining -= len(excerpt)

        contents.append({
            "path": path,
            "status": file.get("status") or STATUS_LABELS.get(
                file.get("code") or "M", "modified"
            ),
            "content": excerpt,
            "truncated": truncated,
        })

    return contents


def _collect_changes(
    engine,
    scope: str = "staged",
    include_diff: bool = True,
    include_content: bool = False,
) -> dict:
    """
    Collect the files, line counts, stat, patch and content of a change set.

    This is the single data source of :func:`repository_status` and
    :func:`repository_commit_message`: the same files, stats, patch and content
    are shown to the user and handed to the model, so the message never
    describes something the user cannot see.

    Args:
        engine: Repository engine.
        scope: 'staged', 'unstaged' or 'worktree' (unknown values fall back to
            'worktree').
        include_diff: Include the patch (truncated to ``MAX_DIFF_CHARS``).
        include_content: Include the content of the changed files (see
            :func:`_collect_contents`).

    Returns:
        Dict with 'scope', 'files' (each one with 'path', 'code', 'status',
        'additions', 'deletions' and 'binary'), 'stat', 'patch',
        'patch_truncated', 'contents' and 'contents_truncated'.

    Example:
        >>> changes = _collect_changes(engine, "staged", include_content=True)
        >>> changes["files"]
        [{'path': 'app.py', 'code': 'M', 'status': 'modified',
          'additions': 2, 'deletions': 1, 'binary': False}]
    """
    if scope not in ("staged", "unstaged", "worktree"):
        scope = "worktree"

    name_result = _run_diff(engine, *_scope_args(scope, ["--name-status"]))
    numstat_result = _run_diff(engine, *_scope_args(scope, ["--numstat"]))
    stat_result = _run_diff(engine, *_scope_args(scope, ["--shortstat"]))

    # Line counts per file: "additions<TAB>deletions<TAB>path"
    counts: Dict[str, Tuple[int, int]] = {}
    binaries = set()
    for line in numstat_result["output"].split("\n"):
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        additions, deletions, path = parts[0], parts[1], parts[-1]
        path = path.strip()
        # Binary files report "-" instead of line counts
        if not additions.isdigit() and not deletions.isdigit():
            binaries.add(path)
        counts[path] = (
            int(additions) if additions.isdigit() else 0,
            int(deletions) if deletions.isdigit() else 0,
        )

    files: List[dict] = []
    seen = set()
    for line in name_result["output"].split("\n"):
        if not line.strip() or "\t" not in line:
            continue
        parts = line.split("\t")
        code = (parts[0] or "").strip()[:1]
        # Rename/copy entries end with the destination path
        path = (parts[-1] or "").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        additions, deletions = counts.get(path, (0, 0))
        files.append({
            "path": path,
            "code": code,
            "status": STATUS_LABELS.get(code, "modified"),
            "additions": additions,
            "deletions": deletions,
            "binary": path in binaries,
        })

    # Untracked files never show up in a diff: list them from the status
    if scope in ("unstaged", "worktree"):
        changes = engine.get_status_changes(engine.get_working_tree_status()["files"])
        for entry in changes["unstaged"]:
            if entry.get("code") != "?" or entry["path"] in seen:
                continue
            seen.add(entry["path"])
            files.append({
                "path": entry["path"],
                "code": "?",
                "status": "untracked",
                "additions": 0,
                "deletions": 0,
                "binary": False,
            })

    patch = ""
    if include_diff:
        patch = _run_diff(engine, *_scope_args(scope, ["--no-color"]))["output"]

    contents: List[dict] = []
    if include_content:
        contents = _collect_contents(engine, files, scope)

    return {
        "scope": scope,
        "files": files,
        "stat": stat_result["output"].strip(),
        "patch": _truncate(patch),
        "patch_truncated": bool(patch) and len(patch) > MAX_DIFF_CHARS,
        "contents": contents,
        "contents_truncated": any(entry["truncated"] for entry in contents),
    }


# -----------------------------------------------------------------------------
# Commit message helpers (50/72 rule)
# -----------------------------------------------------------------------------


def _clean_commit_message(message: str) -> str:
    """
    Strip the decorations a model usually adds around a commit message.

    Code fences, surrounding quotes and leading/trailing blank lines are
    removed; the inner formatting (blank line between subject and body) is
    preserved.

    Args:
        message: Raw commit message.

    Returns:
        Cleaned commit message, empty when nothing usable is left.

    Example:
        >>> _clean_commit_message('"fix: login timeout"')
        'fix: login timeout'
    """
    text = (message or "").replace("\r\n", "\n").strip()
    if not text:
        return ""

    lines = [
        line.rstrip()
        for line in text.split("\n")
        if not line.strip().startswith("```")
    ]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    cleaned = "\n".join(lines).strip()

    if len(cleaned) >= 2 and cleaned[0] in "\"'`" and cleaned[-1] == cleaned[0]:
        cleaned = cleaned[1:-1].strip()

    return cleaned


def _truncate_commit_line(text: str, limit: int = COMMIT_SUBJECT_LIMIT) -> str:
    """
    Cut a commit message line at *limit* characters, never mid-word.

    Trailing punctuation is removed too: a subject must not end with a period,
    and a dangling comma or dash looks like a truncated line.

    Args:
        text: Line to truncate.
        limit: Maximum number of characters allowed.

    Returns:
        The line unchanged when it fits, a word-aligned cut otherwise.

    Example:
        >>> _truncate_commit_line("word " * 20, 50)
        'word word word word word word word word word word'
    """
    text = (text or "").strip()
    if len(text) <= limit:
        return text

    cut = text[:limit]
    space = cut.rfind(" ")
    if space > 0:
        cut = cut[:space]
    cut = cut.rstrip(" ,.;:-")
    return cut or text[:limit].strip()


def _wrap_commit_body(
    body_lines: List[str], width: int = COMMIT_BODY_LIMIT
) -> List[str]:
    """
    Re-wrap the body of a commit message so every line fits *width* characters.

    Blank lines are kept as paragraph separators and list markers
    (``- ``, ``* ``, ``1. ``) are kept as a hanging indent, so wrapped items
    stay aligned. Paths and hashes longer than the width are not broken:
    splitting a path is worse than exceeding the rule by a few characters.

    Args:
        body_lines: Body lines of the commit message.
        width: Maximum line width (72 by the 50/72 rule).

    Returns:
        Wrapped body lines, without trailing blank lines.

    Example:
        >>> lines = _wrap_commit_body(["- " + "word " * 40])
        >>> all(len(line) <= 72 for line in lines)
        True
    """
    wrapped: List[str] = []

    for line in body_lines:
        text = (line or "").strip()
        if not text:
            if wrapped and wrapped[-1] != "":
                wrapped.append("")
            continue

        marker = LIST_MARKER_PATTERN.match(text)
        prefix = marker.group(1) if marker else ""
        content = text[len(prefix):] if prefix else text

        chunks = textwrap.wrap(
            content,
            width=max(10, width - len(prefix)),
            break_long_words=False,
            break_on_hyphens=False,
        ) or [""]

        wrapped.append(prefix + chunks[0])
        wrapped += [" " * len(prefix) + chunk for chunk in chunks[1:]]

    while wrapped and wrapped[-1] == "":
        wrapped.pop()

    return wrapped


def normalize_commit_message(message: str) -> dict:
    """
    Normalize a commit message to the 50/72 rule.

    The first line becomes the subject (truncated at a word boundary) and the
    remaining lines become the body, re-wrapped and separated by a blank line.

    Args:
        message: Raw commit message.

    Returns:
        Dict with 'title', 'body' and 'message' (the full normalized message).
        Every value is empty when the input has no content.

    Example:
        >>> normalize_commit_message("fix: login timeout")["message"]
        'fix: login timeout'
    """
    cleaned = _clean_commit_message(message)
    if not cleaned:
        return {"title": "", "body": "", "message": ""}

    lines = cleaned.split("\n")
    title = _truncate_commit_line(lines[0], COMMIT_SUBJECT_LIMIT)
    body = "\n".join(_wrap_commit_body(lines[1:]))

    return {
        "title": title,
        "body": body,
        "message": f"{title}\n\n{body}".strip() if body else title,
    }


def _path_has_hint(path: str, hints: Tuple[str, ...]) -> bool:
    """
    Return whether a file path matches any of the given hints.

    Args:
        path: Repo-relative file path (lowercase is not required).
        hints: Substrings suggesting a commit type.

    Returns:
        True when at least one hint is contained in the path.
    """
    lowered = (path or "").lower()
    return any(hint in lowered for hint in hints)


def _infer_commit_type(files: List[dict]) -> str:
    """
    Infer the conventional commit type from the changed files.

    Path based first (documentation, tests, CI, build), then changes based (new
    files suggest a feature, deletions only suggest a refactor). The inference is
    deliberately conservative: ``chore`` is the neutral fallback and the model is
    asked to choose the real type when the intent is known.

    Args:
        files: Entries with 'path' and 'code'.

    Returns:
        One of 'docs', 'test', 'ci', 'build', 'feat', 'refactor' or 'chore'.

    Example:
        >>> _infer_commit_type([{"path": "docs/setup.md", "code": "M"}])
        'docs'
    """
    paths = [(file.get("path") or "") for file in files]
    if not paths:
        return "chore"

    for commit_type, hints in COMMIT_TYPE_HINTS:
        if all(_path_has_hint(path, hints) for path in paths):
            return commit_type

    codes = [(file.get("code") or "M") for file in files]
    if any(code == "A" for code in codes):
        return "feat"
    if all(code == "D" for code in codes):
        return "refactor"

    return "chore"


def _infer_scope(files: List[dict]) -> str:
    """
    Infer the commit scope from the common folder of the changed files.

    Args:
        files: Entries with 'path'.

    Returns:
        Last segment of the common folder (e.g. ``tools`` for
        ``codx/junior/tools/x.py``), or an empty string when the files live in
        the repository root or in unrelated folders.

    Example:
        >>> _infer_scope([{"path": "codx/junior/tools/a.py"},
        ...               {"path": "codx/junior/tools/b.py"}])
        'tools'
    """
    folders: List[str] = []
    for file in files:
        parts = (file.get("path") or "").split("/")
        folders.append("/".join(parts[:-1]) if len(parts) > 1 else "")

    if not folders or any(not folder for folder in folders):
        return ""

    try:
        common = os.path.commonpath(folders)
    except ValueError:
        return ""

    if not common or common == ".":
        return ""
    return common.split("/")[-1]


def _subject_from_files(commit_type: str, scope: str, files: List[dict]) -> str:
    """
    Build the draft subject line from the changed files.

    Args:
        commit_type: Conventional commit type.
        scope: Commit scope (may be empty).
        files: Entries with 'path' and 'code'.

    Returns:
        Subject line such as ``feat(tools): add repository_tools.py`` (already
        truncated to the 50 characters limit).

    Example:
        >>> _subject_from_files("feat", "tools",
        ...                     [{"path": "a/repository_tools.py", "code": "A"}])
        'feat(tools): add repository_tools.py'
    """
    prefix = f"{commit_type}({scope}): " if scope else f"{commit_type}: "

    if len(files) == 1:
        code = files[0].get("code") or "M"
        verb = {"A": "add", "D": "remove"}.get(code, "update")
        what = os.path.basename(files[0].get("path") or "") or "file"
    else:
        codes = {(file.get("code") or "M") for file in files}
        verb = "add" if codes == {"A"} else "remove" if codes == {"D"} else "update"
        what = f"{len(files)} files"

    return _truncate_commit_line(f"{prefix}{verb} {what}")


def _body_from_files(files: List[dict]) -> List[str]:
    """
    Build the draft body lines from the changed files.

    The deterministic body can only state *what* changed (one bullet per file,
    with its line counts). The model turns it into *why* the change exists,
    which is what a reader actually needs.

    Args:
        files: Entries with 'path', 'code', 'status', 'additions', 'deletions'.

    Returns:
        Body lines (status + path + line counts), bounded by
        ``MAX_FILES_IN_SUMMARY``.

    Example:
        >>> _body_from_files([{"path": "app.py", "code": "A",
        ...                    "status": "added", "additions": 3,
        ...                    "deletions": 0}])
        ['- added: app.py (+3/-0)']
    """
    lines: List[str] = []

    for file in files[:MAX_FILES_IN_SUMMARY]:
        code = file.get("code") or "M"
        status = file.get("status") or STATUS_LABELS.get(code, "modified")
        additions = file.get("additions") or 0
        deletions = file.get("deletions") or 0
        counts = f" (+{additions}/-{deletions})" if (additions or deletions) else ""
        lines.append(f"- {status}: {file.get('path')}{counts}")

    remaining = len(files) - MAX_FILES_IN_SUMMARY
    if remaining > 0:
        lines.append(f"- and {remaining} more file(s)")

    return lines


def _build_commit_draft(files: List[dict], hint: str = "") -> dict:
    """
    Build a 50/72 compliant commit message draft from the changed files.

    Args:
        files: Entries with 'path', 'code', 'status', 'additions', 'deletions'.
        hint: Optional user instruction (intent, issue reference) used as the
            first body line.

    Returns:
        Dict with 'title', 'body', 'message', 'type' and 'scope'.

    Example:
        >>> draft = _build_commit_draft([{"path": "a/b.py", "code": "A",
        ...                               "status": "added"}])
        >>> draft["type"], draft["scope"], draft["title"]
        ('feat', 'a', 'feat(a): add b.py')
    """
    commit_type = _infer_commit_type(files)
    scope = _infer_scope(files)
    subject = _subject_from_files(commit_type, scope, files)

    body_lines = _body_from_files(files)
    hint = (hint or "").strip()
    if hint:
        body_lines = [hint, ""] + body_lines

    normalized = normalize_commit_message("\n".join([subject, ""] + body_lines))
    normalized.update({"type": commit_type, "scope": scope})
    return normalized


def _max_line_length(text: str) -> int:
    """
    Return the length of the longest line of a text block.

    Args:
        text: Text block (may be empty).

    Returns:
        Length of the longest line (0 when the text has no lines).
    """
    return max((len(line) for line in (text or "").split("\n")), default=0)


# -----------------------------------------------------------------------------
# Tools
# -----------------------------------------------------------------------------


def repository_overview(**kwargs) -> ToolResponse:
    """
    Return a plain-language snapshot of the git repository.

    Use it when the user asks where the repository stands: current branch,
    default branch, remote and sync state, how many files are staged or not,
    whether the repository is locked, which worktrees exist and what the last
    commits are.

    Args:
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings, injected by the runtime.
            - session: Project session, injected by the runtime when available.

    Returns:
        ToolResponse: Contains:
            - user_response: Markdown snapshot of the repository.
            - llm_response: The same facts as machine friendly JSON.

    Example:
        >>> repository_overview(settings=settings).user_response
        '### 📚 Repository snapshot\\n...'
    """
    try:
        engine = _resolve_repo_engine(**kwargs)
        info = engine.get_repo_info()
        commits = engine.get_commit_list(limit=5)
    except Exception as ex:
        return _error_response("repository_overview", ex)

    staged = info.get("staged") or []
    unstaged = info.get("unstaged") or []
    remote_url = info.get("remote_url") or ""
    ahead = info.get("ahead") or 0
    behind = info.get("behind") or 0

    lines: List[str] = ["### 📚 Repository snapshot", ""]
    lines.append(f"- **Path**: `{info.get('repo_path')}`")
    lines.append(
        f"- **Branch**: `{info.get('active_branch') or '(detached)'}`"
        f" · default `{info.get('default_branch') or '?'}`"
    )
    if remote_url:
        lines.append(f"- **Remote**: `{remote_url}` — {ahead} ahead, {behind} behind")
    else:
        lines.append("- **Remote**: none configured")

    if info.get("dirty"):
        lines.append(
            f"- **Working tree**: {len(staged)} staged · {len(unstaged)} not staged"
        )
    else:
        lines.append("- **Working tree**: clean, nothing to commit")

    if info.get("locked"):
        lines.append(f"- **Lock**: ⚠️ `{info.get('lock_path')}`")
    else:
        lines.append("- **Lock**: free")

    worktrees = info.get("worktrees") or []
    if worktrees:
        lines.append(f"- **Worktrees**: {len(worktrees)}")

    if staged:
        lines += ["", "**Staged** (included in the next commit)"] + _render_files(staged, 5)
    if unstaged:
        lines += ["", "**Not staged**"] + _render_files(unstaged, 5)

    if commits:
        lines += ["", "**Last commits**"]
        for commit in commits:
            author = (commit.get("author") or {}).get("name", "")
            lines.append(
                _commit_line(
                    commit.get("short_commit"),
                    commit.get("date"),
                    author,
                    commit.get("message"),
                )
            )

    lines += [
        "",
        "_Ask me about a branch, the diff of a file, or for a commit message._",
    ]

    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=json.dumps(
            {
                "repo_path": info.get("repo_path"),
                "active_branch": info.get("active_branch"),
                "default_branch": info.get("default_branch"),
                "remote_url": remote_url,
                "ahead": ahead,
                "behind": behind,
                "dirty": info.get("dirty"),
                "staged": staged,
                "unstaged": unstaged,
                "locked": info.get("locked"),
                "lock_path": info.get("lock_path"),
                "worktrees": worktrees,
                "last_commits": commits,
            },
            indent=2,
            default=str,
        ),
    )


def repository_status(include_patch: bool = False, **kwargs) -> ToolResponse:
    """
    Return what is staged, what is not staged and what is untracked.

    Use it when the user asks what changed, what the next commit will contain, or
    why a file is missing from a commit. Staged files are the ones the commit
    will include; "not staged" files stay in the working tree.

    Args:
        include_patch: Include the patches (truncated) in the response.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings, injected by the runtime.
            - session: Project session, injected by the runtime when available.

    Returns:
        ToolResponse: Contains:
            - user_response: Markdown list of staged, unstaged and untracked files.
            - llm_response: File lists, stats and (optional) patches.

    Example:
        >>> repository_status(settings=settings).user_response
        '### 🧾 Working tree\\n...'
    """
    try:
        engine = _resolve_repo_engine(**kwargs)
        staged = _collect_changes(engine, "staged", include_diff=include_patch)
        unstaged = _collect_changes(engine, "unstaged", include_diff=include_patch)
        branch = engine.get_project_current_branch()
    except Exception as ex:
        return _error_response("repository_status", ex)

    modified = [file for file in unstaged["files"] if file.get("code") != "?"]
    untracked = [file for file in unstaged["files"] if file.get("code") == "?"]

    lines: List[str] = ["### 🧾 Working tree", ""]
    lines.append(f"- **Branch**: `{branch or '(detached)'}`")

    if not staged["files"] and not unstaged["files"]:
        lines += ["- **Status**: clean, nothing to commit", ""]
        lines.append("_Nothing to stage or commit._")
        return ToolResponse(
            user_response="\n".join(lines),
            llm_response=json.dumps(
                {"branch": branch, "staged": [], "unstaged": [], "untracked": []},
                indent=2,
            ),
        )

    lines.append(f"- **Staged**: {_stats_line(staged['files'])}")
    lines.append(f"- **Not staged**: {_stats_line(modified)}")
    if untracked:
        lines.append(f"- **Untracked**: {len(untracked)} file(s)")

    if staged["files"]:
        lines += ["", "**Staged** — the next commit will include these"] + _render_files(
            staged["files"]
        )
    if modified:
        lines += ["", "**Not staged**"] + _render_files(modified)
    if untracked:
        lines += ["", "**Untracked** (not tracked by git yet)"] + _render_files(
            untracked
        )

    if include_patch:
        for title, changes in (("Staged patch", staged), ("Working tree patch", unstaged)):
            if not changes["patch"]:
                continue
            lines += ["", f"**{title}**", "```diff", changes["patch"], "```"]

    lines += [
        "",
        "**Next step**: `git commit` includes only the staged files; add more with "
        "`git add <path>`.",
    ]

    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=json.dumps(
            {
                "branch": branch,
                "staged": {"stat": staged["stat"], "files": staged["files"],
                           "patch": staged["patch"]},
                "unstaged": {"stat": unstaged["stat"], "files": modified,
                             "patch": unstaged["patch"]},
                "untracked": untracked,
            },
            indent=2,
        ),
    )


def repository_branches(
    include_remote: bool = True,
    limit: int = 200,
    **kwargs,
) -> ToolResponse:
    """
    Return the repository branches with their tip commit.

    Local branches are always listed with their tip commit hash and subject;
    remote-tracking branches are summarised (and listed when there are few of
    them). The current and the default branch are flagged, and worktrees are
    included so the user knows which branch lives in a separate folder.

    Args:
        include_remote: Include remote-tracking branches.
        limit: Number of commits read to resolve the branch tips (1-1000).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings, injected by the runtime.
            - session: Project session, injected by the runtime when available.

    Returns:
        ToolResponse: Contains:
            - user_response: Markdown branch and worktree lists.
            - llm_response: Branches, tips, worktrees and default branch as JSON.

    Example:
        >>> repository_branches(settings=settings).user_response
        '### 🌿 Branches\\n...'
    """
    try:
        engine = _resolve_repo_engine(**kwargs)
        graph = engine.get_repo_graph(limit=limit, include_remote=include_remote)
        worktrees = engine.list_worktrees()
    except Exception as ex:
        return _error_response("repository_branches", ex)

    subjects = {commit["hash"]: commit["subject"] for commit in graph.get("commits", [])}
    active_branch = graph.get("active_branch") or ""
    default_branch = graph.get("default_branch") or ""

    local = [ref for ref in graph.get("branches", []) if ref.get("type") == "local"]
    remote = [ref for ref in graph.get("branches", []) if ref.get("type") == "remote"]
    tags = [ref for ref in graph.get("branches", []) if ref.get("type") == "tag"]

    lines: List[str] = ["### 🌿 Branches", ""]
    lines.append(
        f"- **Current**: `{active_branch or '(detached)'}` · "
        f"**Default**: `{default_branch or '?'}`"
    )
    lines.append(
        f"- **Local**: {len(local)} · **Remote**: {len(remote)} · **Tags**: {len(tags)}"
    )

    lines += ["", "**Local branches**"]
    for ref in local:
        name = ref.get("name", "")
        tip = (ref.get("commit") or "")[:8]
        marks = []
        if name == active_branch:
            marks.append("current")
        if name == default_branch:
            marks.append("default")
        suffix = f" *({', '.join(marks)})*" if marks else ""
        subject = subjects.get(ref.get("commit"))
        detail = f" — {subject}" if subject else ""
        lines.append(f"- `{name}`{suffix} · `{tip}`{detail}")

    if remote:
        lines += ["", "**Remote branches**"]
        for ref in remote[:15]:
            tip = (ref.get("commit") or "")[:8]
            lines.append(f"- `{ref.get('name')}` · `{tip}`")
        if len(remote) > 15:
            lines.append(f"- ... and {len(remote) - 15} more")

    if worktrees:
        lines += ["", "**Worktrees**"]
        for worktree in worktrees:
            lines.append(
                f"- `{worktree.get('path')}` → `{worktree.get('branch') or '(detached)'}`"
            )

    lines += [
        "",
        "_Ask me to compare two branches, or for the commits of one of them._",
    ]

    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=json.dumps(
            {
                "active_branch": active_branch,
                "default_branch": default_branch,
                "local": local,
                "remote": remote,
                "tags": tags,
                "worktrees": worktrees,
                "notes": (
                    "A branch tip without subject was outside the commit window: "
                    "call this tool again with a bigger limit."
                ),
            },
            indent=2,
        ),
    )


def repository_log(
    branch: Optional[str] = None,
    path: Optional[str] = None,
    limit: int = 15,
    **kwargs,
) -> ToolResponse:
    """
    Return the commit history of a branch or of a single file.

    Use it for "what happened lately?" (branch history) and for "who touched
    this file and why?" (file history, follow-renames included).

    Args:
        branch: Branch to read. Defaults to the checked out branch.
        path: Optional file path; when given, the history of that file is
            returned instead of the branch history.
        limit: Maximum number of commits (1-100).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings, injected by the runtime.
            - session: Project session, injected by the runtime when available.

    Returns:
        ToolResponse: Contains:
            - user_response: Markdown commit list.
            - llm_response: The same commits as JSON.

    Example:
        >>> repository_log(path="codx/junior/api/git.py", limit=5, settings=settings)
    """
    try:
        limit = max(1, min(int(limit or 15), MAX_LOG_LIMIT))
        engine = _resolve_repo_engine(**kwargs)

        if path:
            commits = [
                {
                    "commit": commit.get("commit"),
                    "short": commit.get("short_commit"),
                    "date": commit.get("date"),
                    "author": commit.get("author"),
                    "subject": commit.get("message"),
                }
                for commit in engine.get_file_history(path=path, limit=limit)
            ]
            title = f"### 🕘 History of `{path}`"
        else:
            commits = [
                {
                    "commit": commit.get("commit"),
                    "short": commit.get("short_commit"),
                    "date": commit.get("date"),
                    "author": (commit.get("author") or {}).get("name", ""),
                    "subject": commit.get("message"),
                }
                for commit in engine.get_commit_list(branch=branch, limit=limit)
            ]
            title = f"### 🕘 History of `{branch or 'HEAD'}`"
    except Exception as ex:
        return _error_response("repository_log", ex)

    lines: List[str] = [title, ""]
    if not commits:
        lines.append("_No commits found._")
    else:
        lines.append(f"- {len(commits)} commit(s), newest first")
        lines.append("")
        for commit in commits:
            lines.append(
                _commit_line(
                    commit["short"],
                    commit["date"],
                    commit["author"],
                    commit["subject"],
                )
            )

    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=json.dumps(
            {"branch": branch, "path": path, "commits": commits}, indent=2
        ),
    )


def repository_compare(
    from_ref: str,
    to_ref: str = "HEAD",
    include_patch: bool = False,
    max_files: int = 30,
    **kwargs,
) -> ToolResponse:
    """
    Compare two references and return the changes ``from_ref`` adds on top of ``to_ref``.

    Works with branches, tags and commit hashes. The comparison is
    ``git diff to_ref...from_ref`` (three dots), i.e. *what the source adds since
    it diverged from the base*, which is what a review looks like. Nothing is
    fetched and no file is checked out.

    Args:
        from_ref: Source reference (the branch/commit that holds the changes).
        to_ref: Base reference (default ``HEAD``).
        include_patch: Include the patch (truncated).
        max_files: Maximum number of files listed (1-200).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings, injected by the runtime.
            - session: Project session, injected by the runtime when available.

    Returns:
        ToolResponse: Contains:
            - user_response: Markdown summary, file list and commits in between.
            - llm_response: Files, stats, commits and (optional) patch as JSON.

    Example:
        >>> repository_compare("feature/login", "main", settings=settings)
    """
    from_ref = (from_ref or "").strip()
    to_ref = (to_ref or "HEAD").strip() or "HEAD"

    if not from_ref:
        return ToolResponse(
            user_response="⚠️ **repository_compare** needs a `from_ref` (branch or commit).",
            llm_response="repository_compare called without from_ref.",
        )

    range_ref = f"{to_ref}...{from_ref}"
    max_files = max(1, min(int(max_files or 30), 200))

    try:
        engine = _resolve_repo_engine(**kwargs)
        name_status = engine._run_git(["diff", "--name-status", range_ref])
        if not name_status["ok"]:
            return ToolResponse(
                user_response=(
                    f"⚠️ Could not compare `{to_ref}` with `{from_ref}`\n\n"
                    f"> {name_status['error'] or 'unknown git error'}"
                ),
                llm_response=(
                    f"git diff {range_ref} failed: "
                    f"{name_status['error'] or 'unknown git error'}"
                ),
            )

        numstat = engine._run_git(["diff", "--numstat", range_ref])
        shortstat = engine._run_git(["diff", "--shortstat", range_ref])
        commits_result = engine._run_git([
            "log",
            "--no-decorate",
            "--pretty=format:%h %s (%an)",
            "-n",
            "50",
            f"{to_ref}..{from_ref}",
        ])
        patch = ""
        if include_patch:
            patch = _truncate(engine._run_git(["diff", "--no-color", range_ref])["output"])
    except Exception as ex:
        return _error_response("repository_compare", ex)

    counts: Dict[str, Tuple[int, int]] = {}
    for line in numstat["output"].split("\n"):
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        additions, deletions, path = parts[0], parts[1], parts[-1]
        counts[path.strip()] = (
            int(additions) if additions.isdigit() else 0,
            int(deletions) if deletions.isdigit() else 0,
        )

    files: List[dict] = []
    for line in name_status["output"].split("\n"):
        if not line.strip() or "\t" not in line:
            continue
        parts = line.split("\t")
        code = (parts[0] or "").strip()[:1]
        path = (parts[-1] or "").strip()
        if not path:
            continue
        additions, deletions = counts.get(path, (0, 0))
        files.append({
            "path": path,
            "code": code,
            "status": STATUS_LABELS.get(code, "modified"),
            "additions": additions,
            "deletions": deletions,
        })

    commits = [line for line in commits_result["output"].split("\n") if line.strip()]

    lines: List[str] = [f"### 🔍 Comparing `{to_ref}` ← `{from_ref}`", ""]
    if not files:
        lines.append("- No differences: the source has nothing new compared to the base.")
    else:
        lines.append(f"- {_stats_line(files)}")
        lines.append(
            f"- {len(commits)} commit(s) in `{from_ref}` that are not in `{to_ref}`"
        )
        lines += ["", "**Files**"] + _render_files(files, max_files)
        if shortstat["output"].strip():
            lines.append(f"- {shortstat['output'].strip()}")

    if commits:
        lines += ["", "**Commits**"] + [f"- `{line}`" for line in commits]

    if patch:
        lines += ["", "**Patch**", "```diff", patch, "```"]

    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=json.dumps(
            {
                "from_ref": from_ref,
                "to_ref": to_ref,
                "range": range_ref,
                "stat": shortstat["output"].strip(),
                "files": files,
                "commits": commits,
                "patch": patch,
            },
            indent=2,
        ),
    )


def repository_commit_message(
    source: str = "auto",
    hint: Optional[str] = None,
    include_diff: bool = True,
    include_content: bool = True,
    **kwargs,
) -> ToolResponse:
    """
    Build a commit message draft from the staged changes, following the 50/72 rule.

    Steps:
        1. Read the changes: the **staged** ones (the index) by default; the
           working tree is used only when nothing is staged, so the user always
           gets something.
        2. Read their content: the staged patch **and** the real content of
           every changed file (the blob in the index, not the working copy),
           bounded by ``MAX_CONTENT_FILES`` / ``MAX_FILE_CONTENT_CHARS``.
        3. Infer the conventional type from the paths, the scope from the common
           folder and a subject from the file status.
        4. Normalize the result to the 50/72 rule: **subject <= 50 characters**,
           **body lines <= 72 characters**, one blank line in between.

    The draft is a starting point, not a verdict: the caller is expected to read
    the returned content, rewrite the subject with the real intent and turn the
    content into a *why*-focused body (the facts and the rules are returned in
    ``llm_response`` for exactly that).

    Args:
        source: 'staged' (committed next), 'worktree' (everything not committed)
            or 'auto' (staged when available, working tree otherwise).
        hint: Optional user instruction (intent, issue reference) added as the
            first body line.
        include_diff: Include the patch excerpt used to judge the change.
        include_content: Include the content of the changed files. Keep it on:
            without the content, the message can only repeat file names.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings, injected by the runtime.
            - session: Project session, injected by the runtime when available.

    Returns:
        ToolResponse: Contains:
            - user_response: Markdown with the message in a `text` block, the
              files and the content it was built from, and the 50/72 usage.
            - llm_response: Facts, staged content, patch, draft and the rules to
              write the final message.

    Example:
        >>> repository_commit_message(hint="fixes #42", settings=settings)
    """
    try:
        engine = _resolve_repo_engine(**kwargs)

        scope = source if source in ("staged", "worktree") else "auto"
        if scope == "auto":
            staged = _collect_changes(engine, "staged", include_diff=False)
            scope = "staged" if staged["files"] else "worktree"

        changes = _collect_changes(
            engine, scope, include_diff=include_diff, include_content=include_content
        )
    except Exception as ex:
        return _error_response("repository_commit_message", ex)

    files = changes["files"]
    contents = changes["contents"]
    if not files:
        return ToolResponse(
            user_response=(
                "### 📝 Commit message\n\n"
                "Nothing to commit: the working tree is clean.\n\n"
                "_Stage the files to commit (`git add <path>`) and ask again._"
            ),
            llm_response="No changes to summarize: the working tree is clean.",
        )

    draft = _build_commit_draft(files, hint=hint or "")
    subject_length = len(draft["title"])
    max_body_line = _max_line_length(draft["body"])

    user_lines: List[str] = ["### 📝 Commit message draft", ""]
    user_lines += ["```text", draft["message"], "```", ""]
    user_lines.append(
        f"- Subject: {subject_length}/{COMMIT_SUBJECT_LIMIT} characters"
        f" · longest body line: {max_body_line}/{COMMIT_BODY_LIMIT}"
    )
    user_lines.append(f"- Built from {changes['scope']} changes: {_stats_line(files)}")

    if contents:
        user_lines.append(
            f"- {changes['scope'].capitalize()} content read: "
            f"{len(contents)} file(s) — "
            + ", ".join(f"`{entry['path']}`" for entry in contents)
        )
    elif include_content:
        user_lines.append("- Content read: none (binary, deleted or empty files)")

    user_lines += [""] + _render_files(files)

    if changes["scope"] == "worktree":
        user_lines += [
            "",
            "> Nothing is staged: this draft describes the working tree. "
            "Stage the files you want before committing.",
        ]

    user_lines += [
        "",
        "> Tell me the intent (why this change exists, the issue it fixes) and I "
        "will rewrite the subject and the body.",
    ]

    facts = {
        "scope": changes["scope"],
        "stat": changes["stat"],
        "files": files,
        "content_files": [entry["path"] for entry in contents],
        "hint": hint or "",
        "inferred_type": draft["type"],
        "inferred_scope": draft["scope"],
    }

    llm_lines: List[str] = [
        "Facts read from the repository (use them, do not invent):",
        json.dumps(facts, indent=2),
        "",
        "Draft message (already compliant with the 50/72 rule):",
        draft["message"],
        "",
    ]

    if contents:
        source_label = "staged" if changes["scope"] == "staged" else "working tree"
        llm_lines += [
            f"Content of the changed files ({source_label}; read it, this is what "
            "the commit really does):"
        ]
        for entry in contents:
            llm_lines += [
                f"### {entry['path']} ({entry['status']})",
                f"```{_content_language(entry['path'])}",
                entry["content"],
                "```",
                "",
            ]

    if include_diff and changes["patch"]:
        llm_lines += [
            "Patch excerpt (what changed line by line):",
            changes["patch"],
            "",
        ]

    llm_lines += [
        "Write the final commit message:",
        "- subject: imperative mood, `type(scope): summary`, at most "
        f"{COMMIT_SUBJECT_LIMIT} characters, no trailing period;",
        f"- blank line, then a body explaining WHY the change exists, at most "
        f"{COMMIT_BODY_LIMIT} characters per line;",
        "- use the file content to name the real change (endpoint, function, "
        "setting), not the file name;",
        "- never list files again: the diff already shows them;",
        "- return only the commit message (no fences, no quotes, no explanation).",
    ]

    return ToolResponse(
        user_response="\n".join(user_lines),
        llm_response="\n".join(llm_lines),
    )

# Made with ❤️ by codx-junior