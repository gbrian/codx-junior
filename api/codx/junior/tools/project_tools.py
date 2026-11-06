"""
Project tools for file operations, searching, and reading within a project.

This module provides the LLM-facing tools used to examine and change a project:

- ``project_search``: knowledge/semantic search plus path matching.
- ``project_grep``: exact text/regex search in file contents.
- ``project_glob``: fast file discovery by glob pattern.
- ``project_read_file``: bounded reads with line ranges and line numbers.
- ``project_write_file`` / ``apply_file_changes``: writes and atomic edits.
- ``project_changes``: local working-tree changes (staged, unstaged, untracked).

Made with ❤️ by codx-junior
"""

import fnmatch
import glob
import logging
import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union

from codx.junior.settings import CODXJuniorSettings
from codx.junior.engine import CODXJuniorSession
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.utils.utils import document_to_code_block, exec_command
from codx.junior.ai import AI
from codx.junior.model.model import CodxUser
from .model import ToolResponse

# Configure logging
logger = logging.getLogger(__name__)

# Constants
BULK_OPERATION_THRESHOLD = 3
FILE_READ_ERROR_TEMPLATE = "error [%s]\nERROR: %s %s"
MAX_FILES_BULK_OP = 10
MAX_QUERIES_BULK_OP = 5
# Maximum characters returned per document so search responses stay fast and small.
# Documents are built from chunks and may be concatenated per source; capping the
# content avoids giant payloads without paying for an AI call per document.
MAX_SEARCH_DOC_CHARS = 8000
# Glob wildcards are recognized only by search tools that return file paths
# (see find_project_files). Reading tools always use literal paths.
GLOB_PATTERN_CHARS = ("*", "?", "[")
# Lists tracked and untracked (non-ignored) files, honoring the repo .gitignore
GIT_FILE_LIST_COMMAND = "git ls-files --cached --others --exclude-standard --full-name"
# Maximum number of matching project files returned by project_search
MAX_FILE_MATCHES = 100
# VCS internals never listed when only the repository .gitignore is applied
VCS_IGNORE_PATTERNS = (".git",)

# ── Reading limits ──────────────────────────────────────────────────────────
# Default/maximum characters returned by a single file read. Large files are
# truncated at a line boundary and the model is told how to read the rest.
DEFAULT_MAX_READ_CHARS = 50000
MAX_READ_CHARS = 400000
# Budget shared by every file of a bulk project_read_file call.
MAX_TOTAL_READ_CHARS = 150000
# Very long lines (minified bundles, generated files) are shortened in place.
MAX_READ_LINE_CHARS = 2000
# Bytes inspected to decide whether a file is binary.
BINARY_SAMPLE_BYTES = 8192

# ── Content search (project_grep) limits ────────────────────────────────────
MAX_GREP_FILE_BYTES = 2 * 1024 * 1024
MAX_GREP_RESULTS = 1000
MAX_GREP_CONTEXT_LINES = 10
MAX_GREP_LINE_CHARS = 500
MAX_GREP_MATCHES_PER_FILE = 50

# ── Local change inspection (project_changes) limits ───────────────────────
MAX_CHANGE_FILES = 200
MAX_CHANGE_PATCH_CHARS = 40000
GIT_COMMAND_TIMEOUT = 60
CHANGE_SCOPES = ("all", "staged", "unstaged", "untracked")
GIT_STATUS_LABELS = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "T": "typechange",
    "U": "conflict",
    "?": "untracked",
}


def get_ai(settings: CODXJuniorSettings, tool_name: str) -> AI:
    """
    Initialize and return an AI instance for tool usage.

    Args:
        settings: The project settings.
        tool_name: Name of the tool requesting the AI instance.

    Returns:
        AI: Configured AI instance.
    """
    ai_settings = settings.get_llm_settings()
    user = CodxUser(username=tool_name)
    return AI(settings=settings, user=user)


def _project_root(settings: CODXJuniorSettings) -> str:
    """Return the absolute, normalized project root."""
    return os.path.abspath(settings.abs_project_path)


def is_path_within_project(
    settings: CODXJuniorSettings, abs_path: str
) -> bool:
    """
    Check that an absolute path resolves inside the project root.

    Unlike a plain ``str.startswith`` check, this compares path components and
    resolves symlinks, so it rejects siblings such as ``/project-other`` while
    accepting every real descendant of ``/project``.

    Args:
        settings: The project settings.
        abs_path: Absolute path to validate.

    Returns:
        bool: True when the path is inside (or is) the project root.

    Example:
        >>> is_path_within_project(settings, "/project/src/main.py")
        True
        >>> is_path_within_project(settings, "/project-other/src/main.py")
        False
    """
    if not abs_path:
        return False
    try:
        root = os.path.realpath(_project_root(settings))
        target = os.path.realpath(os.path.abspath(abs_path))
        return os.path.commonpath([root, target]) == root
    except (ValueError, OSError):
        return False


def _to_relative_path(settings: CODXJuniorSettings, abs_path: str) -> str:
    """
    Convert an absolute file path to a relative path within the project.

    Args:
        settings: The project settings.
        abs_path: Absolute path to convert.

    Returns:
        str: Relative path from project root, or the original path when the
        path is outside the project.
    """
    root = _project_root(settings)
    try:
        abs_path = os.path.abspath(abs_path)
        if os.path.commonpath([root, abs_path]) == root:
            return os.path.relpath(abs_path, root)
    except (ValueError, OSError):
        pass
    return abs_path


async def code_block(file_path: str, code: str, code_language: str, **kwargs) -> str:
    """
    Ensure the code follows the project's standards and best practices and return it in a code block format.

    Args:
        file_path: Absolute file path.
        code: The code to process.
        code_language: The programming language of the code.

    Returns:
        str: The processed code in a code block format.
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")

    session = CODXJuniorSession(settings=settings)
    processed_code = await session.process_project_file_before_saving(
        file_path=file_path, content=code
    )

    return f"```{code_language} {file_path}\n{processed_code}\n```"


def path_to_absolute_project_path(
    settings: CODXJuniorSettings, file_path: str
) -> str:
    """
    Convert a relative or absolute file path to an absolute project path.

    Paths are resolved literally: glob wildcards are NOT interpreted. The
    returned path always points inside the project root and does not need to
    exist on disk, which allows callers such as ``project_write_file`` to
    create new files.

    An absolute path is honored only when it really belongs to the project
    (path-component check, symlinks resolved). Any other absolute path keeps
    the historical behavior of being interpreted relative to the project root,
    so a leading ``/`` never escapes the sandbox.

    Args:
        settings: The project settings.
        file_path: Relative or absolute path to resolve.

    Returns:
        str: Absolute path inside the project root.

    Example:
        >>> path_to_absolute_project_path(settings, "src/main.py")
        '/project/src/main.py'
        >>> path_to_absolute_project_path(settings, "/project/src/main.py")
        '/project/src/main.py'
    """
    project_root = _project_root(settings)
    raw_path = (file_path or "").strip()

    if os.path.isabs(raw_path):
        if is_path_within_project(settings, raw_path):
            return os.path.normpath(os.path.abspath(raw_path))
        # Keep the legacy "absolute-looking path is project-relative" mapping,
        # but drop the separator first so it cannot escape the root.
        raw_path = raw_path.lstrip(os.sep)

    return os.path.normpath(os.path.abspath(os.path.join(project_root, raw_path)))


def _is_glob_pattern(path: str) -> bool:
    """
    Check whether a path string contains glob wildcard characters.

    Used only by search tools that return file paths (see
    :func:`find_project_files`). Reading tools treat every path literally.

    Args:
        path: The path string to inspect.

    Returns:
        bool: True if the path contains glob wildcards ('*', '?' or '[').
    """
    return isinstance(path, str) and any(char in path for char in GLOB_PATTERN_CHARS)


def _find_glob_files(
    settings: CODXJuniorSettings, pattern: str, limit: int = MAX_FILE_MATCHES
) -> List[str]:
    """
    Find project-relative files matching a glob pattern.

    Wildcards follow the standard glob syntax (``*``, ``?``, ``[abc]``,
    ``**``). Only matching files inside the project root are returned, and the
    repository ``.gitignore`` plus the project's custom ignore patterns are
    honored (see :func:`list_project_files`).

    Args:
        settings: The project settings.
        pattern: Relative or absolute glob pattern (e.g. ``**/*.py``).
        limit: Maximum number of matching files to return.

    Returns:
        List[str]: Sorted project-relative file paths.

    Example:
        >>> _find_glob_files(settings, "codx/**/*.py")
        ['codx/junior/tools/project_tools.py', ...]
    """
    project_root = os.path.abspath(settings.abs_project_path)
    ignore_patterns = settings.get_ignore_patterns()

    rel_pattern = pattern
    if os.path.isabs(rel_pattern):
        rel_pattern = os.path.relpath(rel_pattern, project_root)
    rel_pattern = rel_pattern.lstrip("/")

    # Reject patterns that escape the project root
    if rel_pattern.startswith(".."):
        logger.warning("Glob pattern outside project root: %s", pattern)
        return []

    matches = glob.glob(
        rel_pattern,
        root_dir=project_root,
        recursive=True,
        include_hidden=True,
    )

    # Build the authoritative file list once: it honors the repository
    # .gitignore (via git ls-files) plus the project's custom ignore patterns.
    # glob() itself walks ignored directories, so matches must be intersected.
    valid_files = None
    try:
        valid_files = set(list_project_files(settings))
    except Exception as ex:
        logger.warning("Could not apply project ignores to glob: %s", ex)

    results = []
    for match in matches:
        abs_match = os.path.normpath(os.path.join(project_root, match))
        # Keep results inside the project (resolving symlinks) and files only
        if not is_path_within_project(settings, abs_match):
            continue
        if not os.path.isfile(abs_match):
            continue
        if any(p and p in abs_match for p in ignore_patterns):
            continue
        rel_match = os.path.relpath(abs_match, project_root)
        if valid_files is not None and rel_match not in valid_files:
            continue
        results.append(rel_match)

    logger.debug("Glob '%s' matched %d file(s)", pattern, len(results))
    return sorted(set(results))[:limit]


def _read_single_file(
    settings: CODXJuniorSettings,
    file_path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    max_chars: Optional[int] = None,
    line_numbers: bool = False,
) -> Tuple[str, Optional[str]]:
    """
    Read a single file (or a line range of it) and return its content or error.

    The read is bounded: a file is never returned whole when it would exceed
    ``max_chars``, binary files are rejected, and very long lines are shortened.
    The returned header always states which lines of the file are shown so the
    model can request the next range.

    Args:
        settings: The project settings.
        file_path: Path to the file to read.
        start_line: First line to return (1-based). Defaults to line 1.
        end_line: Last line to return (inclusive). Defaults to the last line.
        max_chars: Maximum characters in the code block. Defaults to
            ``DEFAULT_MAX_READ_CHARS`` and is clamped to ``MAX_READ_CHARS``.
        line_numbers: Prefix every returned line with its 1-based number.

    Returns:
        tuple: (content_or_error, error_message_or_none)
            - If successful: (formatted_content, None)
            - If failed: (error_block, error_description)
    """
    try:
        abs_path = path_to_absolute_project_path(
            settings=settings, file_path=file_path
        )

        if not is_path_within_project(settings, abs_path):
            error_msg = f"Path must belong to {settings.abs_project_path}"
            error_block = FILE_READ_ERROR_TEMPLATE % (
                file_path, file_path, error_msg
            )
            logger.warning("Invalid file path: %s", file_path)
            return error_block, error_msg

        if not os.path.isfile(abs_path):
            error_msg = "File not found"
            error_block = FILE_READ_ERROR_TEMPLATE % (
                file_path, file_path, error_msg
            )
            logger.warning("File not found: %s", abs_path)
            return error_block, error_msg

        # Binary files (null bytes in the sample) cannot be shown as text.
        try:
            with open(abs_path, "rb") as binary_file:
                sample = binary_file.read(BINARY_SAMPLE_BYTES)
        except OSError as e:
            error_msg = str(e)
            error_block = FILE_READ_ERROR_TEMPLATE % (
                file_path, file_path, error_msg
            )
            logger.error("Error reading file %s: %s", file_path, error_msg)
            return error_block, error_msg

        if b"\x00" in sample:
            error_msg = (
                "File appears to be binary and cannot be read as text"
            )
            error_block = FILE_READ_ERROR_TEMPLATE % (
                file_path, file_path, error_msg
            )
            logger.warning("Binary file rejected: %s", abs_path)
            return error_block, error_msg

        with open(abs_path, "r", encoding="utf-8", errors="replace") as file:
            content = file.read()

        lines = content.splitlines()
        total_lines = len(lines)
        rel_path = _to_relative_path(settings=settings, abs_path=abs_path)
        extension = os.path.splitext(abs_path)[1].lstrip(".")

        if total_lines == 0:
            formatted = f"# {rel_path} (empty file)\n```{extension} {rel_path}\n\n```"
            return formatted, None

        try:
            requested_start = 1 if start_line is None else int(start_line)
            requested_end = total_lines if end_line is None else int(end_line)
        except (TypeError, ValueError):
            error_msg = "start_line and end_line must be integers"
            return (
                FILE_READ_ERROR_TEMPLATE % (file_path, file_path, error_msg),
                error_msg,
            )

        requested_start = max(1, requested_start)
        if requested_start > total_lines:
            error_msg = (
                f"start_line ({requested_start}) is beyond the end of the file "
                f"({total_lines} lines)"
            )
            return (
                FILE_READ_ERROR_TEMPLATE % (file_path, file_path, error_msg),
                error_msg,
            )
        if requested_end < requested_start:
            error_msg = (
                f"end_line ({requested_end}) must be greater than or equal to "
                f"start_line ({requested_start})"
            )
            return (
                FILE_READ_ERROR_TEMPLATE % (file_path, file_path, error_msg),
                error_msg,
            )

        requested_end = min(requested_end, total_lines)
        cap = max(
            200,
            min(int(max_chars or DEFAULT_MAX_READ_CHARS), MAX_READ_CHARS),
        )

        rendered_lines: List[str] = []
        used_chars = 0
        last_line = requested_start - 1
        truncated_by_chars = False

        for line_number, line in enumerate(
            lines[requested_start - 1:requested_end], start=requested_start
        ):
            if len(line) > MAX_READ_LINE_CHARS:
                line = line[:MAX_READ_LINE_CHARS] + " …[line truncated]"
            if line_numbers:
                line = f"{line_number:>6}| {line}"

            if used_chars + len(line) + 1 > cap:
                truncated_by_chars = True
                break

            rendered_lines.append(line)
            used_chars += len(line) + 1
            last_line = line_number

        # Guarantee at least one line, even when the cap is tiny.
        if not rendered_lines:
            line = lines[requested_start - 1]
            if len(line) > MAX_READ_LINE_CHARS:
                line = line[:MAX_READ_LINE_CHARS] + " …[line truncated]"
            if line_numbers:
                line = f"{requested_start:>6}| {line}"
            rendered_lines.append(line[:cap])
            last_line = requested_start
            truncated_by_chars = True

        shown_range = f"lines {requested_start}-{last_line} of {total_lines}"
        formatted = "\n".join(
            [f"# {rel_path} ({shown_range})"]
            + [f"```{extension} {rel_path}"]
            + rendered_lines
            + ["```"]
        )

        remaining = total_lines - last_line
        if truncated_by_chars:
            formatted += (
                f"\n\n> Truncated: showing {shown_range} ({remaining} line(s) "
                f"left). Call project_read_file again with "
                f"`start_line={last_line + 1}` to continue."
            )
        elif last_line < total_lines:
            formatted += (
                f"\n\n> Showing requested range {shown_range}; {remaining} "
                f"more line(s) are available. Call project_read_file with "
                f"`start_line={last_line + 1}` to continue."
            )

        logger.debug(
            "Successfully read file: %s (%s)", file_path, shown_range
        )
        return formatted, None

    except (IOError, OSError, ValueError) as e:
        error_msg = str(e)
        error_block = FILE_READ_ERROR_TEMPLATE % (
            file_path, file_path, error_msg
        )
        logger.error("Error reading file %s: %s", file_path, error_msg)
        return error_block, error_msg


def project_read_file(
    file_path: Union[str, List[str]],
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    max_chars: Optional[int] = None,
    line_numbers: bool = False,
    **kwargs,
) -> ToolResponse:
    """
    Read the content of one or multiple files from the project.

    Supports bulk file reading to reduce tool calls. For optimal performance,
    read multiple related files in a single call instead of multiple individual calls.

    Paths are read literally: glob wildcards ('*', '?', '[') are NOT interpreted.
    Use ``project_search`` to discover files by pattern and then read the paths
    it returns.

    Output is bounded. Large files are truncated at a line boundary and the
    response states which lines were shown; call again with ``start_line`` /
    ``end_line`` to read the rest. Binary files are reported as errors and never
    dumped into the context.

    Args:
        file_path: Single file path (str) or list of file paths to read.
                   Supports relative and absolute paths. Glob patterns are not
                   supported.
        start_line: First line to return (1-based). Applies to every file in a
                   bulk read. Defaults to line 1.
        end_line: Last line to return (inclusive). Applies to every file in a
                  bulk read. Defaults to the last line of each file.
        max_chars: Maximum characters returned per file. Defaults to 50000 and
                   is clamped between 200 and 400000.
        line_numbers: If true, prefix every returned line with its number.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).

    Returns:
        ToolResponse: Contains:
            - user_response: Summary of successfully read files and errors.
            - llm_response: File contents with error blocks for invalid/missing files.

    Raises:
        ValueError: If file_path is not provided or empty.
        Exception: If project settings are not provided.

    Example:
        Read a specific range with line numbers:
        >>> project_read_file("src/main.py", start_line=40, end_line=80,
        ...                   line_numbers=True)

        Read multiple files at once:
        >>> project_read_file(["src/main.py", "config/settings.py"])
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")

    if not file_path:
        raise ValueError("file_path must be provided and cannot be empty")

    # Normalize to list for uniform processing
    file_paths = [file_path] if isinstance(file_path, str) else file_path

    if not file_paths:
        raise ValueError("At least one file path must be provided")

    # Warn if exceeding recommended bulk operation size
    if len(file_paths) > MAX_FILES_BULK_OP:
        logger.warning(
            "Reading %d files exceeds recommended bulk operation limit of %d",
            len(file_paths),
            MAX_FILES_BULK_OP,
        )

    contents: List[str] = []
    successful_reads: List[str] = []
    failed_reads: List[Tuple[str, str]] = []
    skipped_reads: List[str] = []
    total_chars = 0

    for index, fp in enumerate(file_paths):
        # Keep the overall response within the context budget.
        if total_chars >= MAX_TOTAL_READ_CHARS:
            skipped_reads.extend(str(item) for item in file_paths[index:])
            break

        content, error = _read_single_file(
            settings=settings,
            file_path=fp,
            start_line=start_line,
            end_line=end_line,
            max_chars=max_chars,
            line_numbers=line_numbers,
        )
        contents.append(content)
        total_chars += len(content)

        if error:
            failed_reads.append((str(fp), error))
        else:
            successful_reads.append(str(fp))

    # Build LLM content and feedback summary
    llm_response = "\n".join(contents)
    if skipped_reads:
        llm_response += (
            f"\n\n> Skipped {len(skipped_reads)} file(s) after reaching the "
            f"{MAX_TOTAL_READ_CHARS:,}-character read budget: "
            + ", ".join(skipped_reads)
        )

    summary_lines = [f"Read {len(successful_reads)} file(s)"]
    if successful_reads:
        summary_lines.append(f"Successfully read: {', '.join(successful_reads)}")
    if failed_reads:
        summary_lines.append(
            f"Failed to read {len(failed_reads)} file(s): "
            + ", ".join([f[0] for f in failed_reads])
        )
    if skipped_reads:
        summary_lines.append(f"Skipped {len(skipped_reads)} file(s) (budget)")

    user_response = " | ".join(summary_lines)
    logger.info(
        "File read operation completed: %d file(s), %d chars",
        len(successful_reads),
        len(llm_response),
    )

    return ToolResponse(user_response=user_response, llm_response=llm_response)


def _list_git_files(project_root: str) -> Optional[List[str]]:
    """
    List absolute file paths tracked by git, honoring the repository ``.gitignore``.

    Uses ``git ls-files`` so that every folder and file ignored through
    ``.gitignore`` (and its nested ignore files) is discarded automatically.

    Args:
        project_root: Absolute path of the project root.

    Returns:
        Optional[List[str]]: Absolute file paths inside ``project_root``, or
        ``None`` when ``project_root`` is not inside a git repository.

    Example:
        >>> _list_git_files("/project")
        ['/project/src/main.py', '/project/README.md', ...]
    """
    top_level, _ = exec_command("git rev-parse --show-toplevel", cwd=project_root)
    top_level = (top_level or "").strip()
    if not top_level or not os.path.isdir(top_level):
        logger.debug("Not a git repository: %s", project_root)
        return None

    stdout, _ = exec_command(GIT_FILE_LIST_COMMAND, cwd=top_level)
    if not stdout:
        return None

    project_root = os.path.abspath(project_root)
    project_prefix = project_root + os.sep
    git_files = []
    for rel_path in stdout.split("\n"):
        rel_path = rel_path.strip()
        if not rel_path:
            continue
        abs_path = os.path.normpath(os.path.join(top_level, rel_path))
        if not abs_path.startswith(project_prefix):
            continue
        if not os.path.isfile(abs_path):
            continue
        git_files.append(abs_path)
    return git_files


def _list_walk_files(project_root: str, ignore_patterns: List[str]) -> List[str]:
    """
    Fallback file listing that walks the filesystem when git is unavailable.

    Ignored folders are pruned before being traversed, so directories such as
    ``.git`` or ``node_modules`` are never explored.

    Args:
        project_root: Absolute path of the project root.
        ignore_patterns: Custom ignore patterns from the project settings.

    Returns:
        List[str]: Absolute file paths inside the project root.

    Example:
        >>> _list_walk_files("/project", ["node_modules"])
        ['/project/src/main.py', '/project/README.md', ...]
    """
    walk_files = []
    for current_root, dirs, files in os.walk(project_root):
        dirs[:] = [
            d for d in dirs
            if not any(p and p in os.path.join(current_root, d) for p in ignore_patterns)
        ]
        for file_name in files:
            walk_files.append(os.path.join(current_root, file_name))
    return walk_files


def list_project_files(
    settings: CODXJuniorSettings, apply_custom_ignores: bool = True
) -> List[str]:
    """
    List the project files, honoring ``.gitignore`` and optionally custom ignores.

    Files and folders matched by the repository's ``.gitignore`` are discarded
    by querying git directly. When ``apply_custom_ignores`` is True (default),
    every path matched by the custom ignore patterns defined in the project
    settings (``knowledge_file_ignore``, sub-projects, wiki path, ``.git``,
    ``node_modules``, ...) is filtered out as well. When it is False only the
    repository ``.gitignore`` is honored, which allows callers such as
    ``project_structure`` to navigate nested (child) projects.

    Args:
        settings: The project settings.
        apply_custom_ignores: Whether to also apply the project's custom ignore
            patterns on top of ``.gitignore``.

    Returns:
        List[str]: Sorted list of project-relative file paths.

    Example:
        >>> list_project_files(settings)
        ['README.md', 'codx/junior/settings.py', 'codx/junior/tools/project_tools.py']
        >>> list_project_files(settings, apply_custom_ignores=False)
        ['README.md', 'codx/junior/settings.py', 'child-project/src/main.py', ...]
    """
    project_root = os.path.abspath(settings.abs_project_path)

    if apply_custom_ignores:
        ignore_patterns = settings.get_ignore_patterns()
    else:
        # Only the repository .gitignore is applied (via git ls-files); VCS
        # internals are still excluded from the non-git walk fallback.
        ignore_patterns = list(VCS_IGNORE_PATTERNS)

    abs_files = _list_git_files(project_root)
    if abs_files is None:
        logger.debug("Falling back to filesystem walk for project files")
        abs_files = _list_walk_files(project_root, ignore_patterns)

    valid_files = [
        abs_path for abs_path in abs_files
        if not any(p and p in abs_path for p in ignore_patterns)
    ]

    return sorted({os.path.relpath(abs_path, project_root) for abs_path in valid_files})


def find_project_files(
    settings: CODXJuniorSettings, query: str, limit: int = MAX_FILE_MATCHES
) -> List[str]:
    """
    Find project files whose path matches a query.

    Two matching modes are supported:

    - **Glob pattern**: when the query contains glob wildcards (``*``, ``?``,
      ``[``) it is treated as a glob pattern matched against the project file
      paths (e.g. ``**/*.py``).
    - **Keyword search**: otherwise the query is split into whitespace
      separated terms and a file matches when every term is present
      (case-insensitive) in the project-relative path.

    Files are filtered with ``.gitignore`` and the project's custom ignore
    patterns (see :func:`list_project_files`).

    Args:
        settings: The project settings.
        query: Glob pattern or space separated terms matched against the paths.
        limit: Maximum number of matching files to return.

    Returns:
        List[str]: Matching project-relative file paths.

    Example:
        >>> find_project_files(settings, "settings.py")
        ['codx/junior/settings.py']
        >>> find_project_files(settings, "**/*.py")
        ['codx/junior/tools/project_tools.py', ...]
    """
    query = (query or "").strip()
    if not query:
        return []

    # Glob patterns are matched directly against the project file paths
    if _is_glob_pattern(query):
        return _find_glob_files(settings=settings, pattern=query, limit=limit)

    tokens = [token for token in re.split(r"\s+", query.lower()) if token]
    if not tokens:
        return []

    matches = [
        rel_path for rel_path in list_project_files(settings=settings)
        if all(token in rel_path.lower() for token in tokens)
    ]
    return matches[:limit]


def project_search(
    search: Union[str, List[str]], validation: Optional[str] = None, **kwargs
) -> ToolResponse:
    """
    Search for documents and files within a project.

    Searches the project's knowledge base for documents relevant to one or more
    queries. In addition, it finds files in the project folder whose path matches
    the query. The repository's ``.gitignore`` rules are honored so ignored
    folders and files are discarded, and the custom ignore patterns defined in the
    project settings are applied as well.

    File matching supports glob patterns: a query containing glob wildcards
    ('*', '?', '[') is treated as a glob pattern matched against the project
    file paths (e.g. ``**/*.py``).

    This tool is optimized for speed: a single knowledge DB connection is reused
    across all queries and no AI call is made per document. Each document's
    content is returned directly and capped to ``MAX_SEARCH_DOC_CHARS`` so the
    response stays fast even for large files.

    Supports bulk searching to reduce tool calls. For optimal performance,
    search for multiple related concepts in a single call.

    Args:
        search: Single search query (str) or list of queries to execute.
        validation: Kept for backward compatibility. Previously used to filter
                   each document with an AI call; filtering is no longer
                   performed so the search stays fast.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings.

    Returns:
        ToolResponse: Contains:
            - user_response: Formatted search results with code blocks.
            - llm_response: Summary of search queries, results found and the list
              of project files matching the query.

    Raises:
        ValueError: If search argument is not provided or is empty.

    Example:
        Search for multiple concepts at once:
        >>> project_search(["authentication", "user session", "login"])
        # Returns ToolResponse with results for all queries, the matching project
        # files and a summary

        Find every Python file using a glob query:
        >>> project_search("**/*.py")
        # Returns ToolResponse with the matching file paths and a summary
    """
    if not search:
        raise ValueError("The search argument must be provided and cannot be empty.")

    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        return ToolResponse(
            user_response="No results. Missing project settings",
            llm_response="Search failed: missing settings",
        )

    # Normalize to list for uniform processing
    search_queries = [search] if isinstance(search, str) else search

    if not search_queries:
        raise ValueError("At least one search query must be provided")

    # Warn if exceeding recommended bulk operation size
    if len(search_queries) > MAX_QUERIES_BULK_OP:
        logger.warning(
            "Executing %d queries exceeds recommended bulk operation limit of %d",
            len(search_queries),
            MAX_QUERIES_BULK_OP,
        )

    # Reuse a single knowledge DB (and its embeddings model) across every query.
    # Creating ``KnowledgeDB`` is expensive (embeddings model + Milvus connect),
    # so it must not happen inside the query loop. Knowledge search is optional:
    # path/file matching still works when the DB is unavailable.
    knowledge_db = None
    warnings: List[str] = []
    try:
        knowledge_db = Knowledge(settings=settings).get_db()
    except Exception as ex:
        warnings.append(f"Knowledge search unavailable: {ex}")
        logger.warning("Knowledge search unavailable: %s", ex)

    all_results = []
    queries_executed = 0
    total_documents_found = 0

    for query in search_queries:
        queries_executed += 1
        if knowledge_db is None:
            continue

        logger.debug("Executing search query: %s", query)
        try:
            documents = knowledge_db.search(query=query, _limit=10)
        except Exception as ex:
            warnings.append(f"Search failed for '{query}': {ex}")
            logger.warning("Search failed for %s: %s", query, ex)
            continue

        if not documents:
            logger.info("No results found for query: %s", query)
            continue

        total_documents_found += len(documents)

        # Deduplicate documents by source
        doc_sources = {}
        for doc in documents:
            source = doc.metadata.get("source")
            if not source:
                continue

            if source not in doc_sources:
                doc_sources[source] = doc
            else:
                doc_sources[source].page_content += "\n" + doc.page_content

        # Return document content directly (no per-document AI call) and cap the
        # size so the tool stays fast even on large files.
        for doc in doc_sources.values():
            # Convert document source to relative path if it belongs to project
            source = doc.metadata.get("source", "")
            if source and is_path_within_project(settings, source):
                rel_source = _to_relative_path(settings=settings, abs_path=source)
                doc.metadata["source"] = rel_source

            if len(doc.page_content) > MAX_SEARCH_DOC_CHARS:
                doc.page_content = (
                    doc.page_content[:MAX_SEARCH_DOC_CHARS] + "\n... (truncated)"
                )

            all_results.append(document_to_code_block(doc))

    # Find project files whose path matches every query. Each query is matched
    # on its own: joining them would require all terms in the same path and
    # silently drop valid matches (e.g. ["auth", "session"]).
    file_matches: List[str] = []
    seen_files = set()
    for query in search_queries:
        try:
            for rel_path in find_project_files(settings=settings, query=query):
                if rel_path in seen_files:
                    continue
                seen_files.add(rel_path)
                file_matches.append(rel_path)
        except Exception as ex:
            warnings.append(f"Path search failed for '{query}': {ex}")
            logger.warning("Error finding project files for %s: %s", query, ex)
    file_matches = sorted(file_matches)[:MAX_FILE_MATCHES]

    file_section = ""
    if file_matches:
        file_section = "\n".join(
            [f"\n### Matching files ({len(file_matches)})"]
            + [f"- `{rel_path}`" for rel_path in file_matches]
        )

    warning_section = ""
    if warnings:
        warning_section = "\n".join(
            [f"\n### Warnings"] + [f"- {warning}" for warning in warnings]
        )

    # Build responses
    if not all_results and not file_matches:
        llm_response = "\n".join(
            part for part in [
                f"> No results found for: '{', '.join(search_queries)}' "
                f"in project: '{settings.project_name}'",
                warning_section,
            ] if part
        )
        user_response = (
            f"Search completed: {queries_executed} queries executed, "
            "0 documents found, 0 files matched"
            + (f" ({len(warnings)} warning(s))" if warnings else "")
        )
    else:
        llm_response = "\n".join(
            part for part in [
                f"> {settings.project_name} results for: '{', '.join(search_queries)}'",
                "\n".join(all_results),
                file_section,
                warning_section,
            ] if part
        )
        user_response = (
            f"Search completed: {queries_executed} queries executed, "
            f"{total_documents_found} documents found, {len(file_matches)} files matched"
            + (f" ({len(warnings)} warning(s))" if warnings else "")
        )

    logger.info(
        "Search operation completed: %d queries, %d docs, %d files",
        queries_executed,
        total_documents_found,
        len(file_matches),
    )
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def _normalize_globs(include: Optional[Union[str, List[str]]]) -> List[str]:
    """Normalize an include filter (string or list) into a list of globs."""
    if not include:
        return []
    values = [include] if isinstance(include, str) else list(include)
    globs: List[str] = []
    for value in values:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                globs.append(part)
    return globs


def _matches_include(rel_path: str, globs: List[str]) -> bool:
    """Return True when a path matches at least one include glob."""
    if not globs:
        return True
    basename = os.path.basename(rel_path)
    return any(
        fnmatch.fnmatch(rel_path, pattern)
        or fnmatch.fnmatch(basename, pattern)
        for pattern in globs
    )


def project_glob(
    pattern: Union[str, List[str]],
    limit: int = 200,
    **kwargs,
) -> ToolResponse:
    """
    Find project files by glob pattern and return their paths.

    This is the fast, focused way to discover files. Unlike ``project_search``
    it does not query the knowledge base, so it is cheap enough to call before
    reading or editing. The repository ``.gitignore`` and the project's custom
    ignore patterns are honored.

    Args:
        pattern: Glob pattern (string) or list of patterns. Standard wildcards
            are supported: ``*``, ``?``, ``[abc]`` and recursive ``**``.
            Examples: ``**/*.py``, ``src/**/*.ts``, ``Dockerfile*``.
        limit: Maximum number of paths returned (1-1000, default: 200).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).

    Returns:
        ToolResponse: Contains:
            - user_response: Number of files found.
            - llm_response: Markdown list of project-relative paths.

    Raises:
        ValueError: If no pattern is provided.
        Exception: If project settings are not provided.

    Example:
        >>> project_glob("**/*.py")
        >>> project_glob(["src/**/*.ts", "tests/**/*.ts"])
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")

    if isinstance(pattern, str):
        patterns = [pattern]
    elif pattern:
        patterns = [str(item) for item in pattern]
    else:
        patterns = []

    patterns = [item.strip() for item in patterns if item and item.strip()]
    if not patterns:
        raise ValueError("pattern must be provided and cannot be empty")

    try:
        limit = max(1, min(int(limit or 200), 1000))
    except (TypeError, ValueError):
        return ToolResponse(
            user_response="⚠️ `limit` must be an integer.",
            llm_response="project_glob: invalid limit",
        )

    matches: List[str] = []
    seen = set()
    for glob_pattern in patterns:
        try:
            found = _find_glob_files(
                settings=settings, pattern=glob_pattern, limit=limit
            )
        except Exception as ex:
            logger.warning("project_glob '%s' failed: %s", glob_pattern, ex)
            continue
        for rel_path in found:
            if rel_path in seen:
                continue
            seen.add(rel_path)
            matches.append(rel_path)
            if len(matches) >= limit:
                break
        if len(matches) >= limit:
            break

    matches.sort()
    if not matches:
        return ToolResponse(
            user_response=f"No files matched: {', '.join(patterns)}",
            llm_response=(
                f"> No project files matched "
                f"{', '.join(f'`{item}`' for item in patterns)}. "
                "Check the pattern, or use project_grep/project_search to search "
                "by content or name."
            ),
        )

    listing = "\n".join(f"- `{rel_path}`" for rel_path in matches)
    llm_response = (
        f"> {len(matches)} file(s) matched "
        f"{', '.join(f'`{item}`' for item in patterns)}"
        f"{' (limit reached)' if len(matches) >= limit else ''}\n\n{listing}"
    )
    user_response = f"Found {len(matches)} file(s)"
    if len(matches) >= limit:
        user_response += f" (limit {limit})"

    logger.info(
        "project_glob: patterns=%s files=%d", patterns, len(matches)
    )
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def _is_binary_file(abs_path: str) -> bool:
    """Return True when the first bytes of a file contain a null byte."""
    try:
        with open(abs_path, "rb") as binary_file:
            return b"\x00" in binary_file.read(BINARY_SAMPLE_BYTES)
    except OSError:
        return False


def project_grep(
    pattern: str,
    path: str = ".",
    include: Optional[Union[str, List[str]]] = None,
    case_sensitive: bool = False,
    regex: bool = False,
    context_lines: int = 2,
    max_results: int = 100,
    **kwargs,
) -> ToolResponse:
    """
    Search file contents in the project (grep) and return matching lines.

    Unlike ``project_search`` (knowledge/semantic search plus path matching),
    this tool searches the raw text of files. Use it to find an exact symbol,
    string, error message, configuration key or regular expression, and to see
    the surrounding lines.

    The repository ``.gitignore`` and the project's custom ignore patterns are
    honored. Binary files, files larger than 2 MB and output beyond the result
    budget are skipped and reported.

    Args:
        pattern: Literal text or regular expression to search for.
        path: File or folder to search. Defaults to the project root.
        include: Optional glob filter(s), comma-separated or a list. Each glob
            is matched against the project-relative path and the file name,
            e.g. ``*.py`` or ``src/**/*.ts``.
        case_sensitive: Match case when True (default: False).
        regex: Treat ``pattern`` as a regular expression (default: False).
        context_lines: Lines of context before and after each match (0-10).
        max_results: Maximum number of matching lines returned (1-1000).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).

    Returns:
        ToolResponse: Contains:
            - user_response: Match/file counts and any truncation notice.
            - llm_response: Matching lines grouped by file, with context and
              line numbers.

    Raises:
        ValueError: If ``pattern`` is empty.
        Exception: If project settings are not provided.

    Example:
        >>> project_grep("def get_ai", include="*.py")
        >>> project_grep(r"TODO.*", regex=True, path="codx/junior")
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")

    pattern = pattern or ""
    if not pattern:
        raise ValueError("pattern must be provided and cannot be empty")

    root = _project_root(settings)
    search_path = (path or ".").strip() or "."
    abs_search = path_to_absolute_project_path(settings, search_path)

    if not is_path_within_project(settings, abs_search):
        return ToolResponse(
            user_response=f"⚠️ `{search_path}` is outside the project.",
            llm_response=f"project_grep: path outside project: {search_path}",
        )

    try:
        context_lines = max(0, min(int(context_lines or 0), MAX_GREP_CONTEXT_LINES))
        max_results = max(1, min(int(max_results or 100), MAX_GREP_RESULTS))
    except (TypeError, ValueError):
        return ToolResponse(
            user_response="⚠️ `context_lines` and `max_results` must be integers.",
            llm_response="project_grep: invalid numeric arguments",
        )

    globs = _normalize_globs(include)

    if os.path.isfile(abs_search):
        candidates = [os.path.relpath(abs_search, root)]
    elif os.path.isdir(abs_search):
        rel_base = os.path.relpath(abs_search, root)
        all_files = list_project_files(settings)
        if rel_base in (".", ""):
            candidates = all_files
        else:
            prefix = rel_base.rstrip(os.sep) + os.sep
            candidates = [
                rel_path for rel_path in all_files
                if rel_path.startswith(prefix)
            ]
    else:
        return ToolResponse(
            user_response=f"⚠️ Path not found: `{search_path}`",
            llm_response=f"project_grep: path not found: {search_path}",
        )

    matcher: Optional[Any] = None
    if regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            matcher = re.compile(pattern, flags)
        except re.error as ex:
            return ToolResponse(
                user_response=f"⚠️ Invalid regular expression: {ex}",
                llm_response=f"project_grep: invalid regex: {ex}",
            )
    needle = pattern if case_sensitive else pattern.lower()

    matched_files: List[str] = []
    groups: List[str] = []
    total_matches = 0
    skipped_binary = 0
    skipped_large = 0
    truncated = False
    budget_hit = False

    for rel_path in candidates:
        if budget_hit:
            break
        if not _matches_include(rel_path, globs):
            continue

        abs_file = os.path.join(root, rel_path)
        if not os.path.isfile(abs_file):
            continue

        try:
            if os.path.getsize(abs_file) > MAX_GREP_FILE_BYTES:
                skipped_large += 1
                continue
        except OSError:
            continue

        if _is_binary_file(abs_file):
            skipped_binary += 1
            continue

        try:
            with open(abs_file, "r", encoding="utf-8", errors="replace") as file:
                lines = file.read().splitlines()
        except OSError as ex:
            logger.debug("project_grep: cannot read %s: %s", rel_path, ex)
            continue

        hit_lines: List[int] = []
        for line_index, line in enumerate(lines):
            if matcher is not None:
                matched = matcher.search(line) is not None
            elif case_sensitive:
                matched = needle in line
            else:
                matched = needle in line.lower()
            if not matched:
                continue

            hit_lines.append(line_index)
            if len(hit_lines) >= MAX_GREP_MATCHES_PER_FILE:
                truncated = True
                break

        if not hit_lines:
            continue

        # Merge overlapping context ranges so no line is repeated.
        ranges: List[Tuple[int, int]] = []
        for line_index in hit_lines:
            start = max(0, line_index - context_lines)
            end = min(len(lines), line_index + context_lines + 1)
            if ranges and start <= ranges[-1][1]:
                ranges[-1] = (ranges[-1][0], max(ranges[-1][1], end))
            else:
                ranges.append((start, end))

        hit_set = set(hit_lines)
        file_lines = [f"### `{rel_path}`"]
        file_matches = 0

        for start, end in ranges:
            for line_index in range(start, end):
                if total_matches >= max_results:
                    truncated = True
                    budget_hit = True
                    break
                line = lines[line_index]
                if len(line) > MAX_GREP_LINE_CHARS:
                    line = line[:MAX_GREP_LINE_CHARS] + " …[line truncated]"
                separator = ":" if line_index in hit_set else "-"
                file_lines.append(
                    f"{rel_path}{separator}{line_index + 1}{separator}{line}"
                )
                if line_index in hit_set:
                    total_matches += 1
                    file_matches += 1
            if budget_hit:
                break

        if file_matches:
            matched_files.append(rel_path)
            groups.append("\n".join(file_lines))

    notes: List[str] = []
    if skipped_binary:
        notes.append(f"{skipped_binary} binary file(s) skipped")
    if skipped_large:
        notes.append(f"{skipped_large} file(s) larger than 2 MB skipped")
    if total_matches >= max_results:
        notes.append(f"results capped at {max_results}")
    if truncated and total_matches < max_results:
        notes.append(
            f"per-file matches capped at {MAX_GREP_MATCHES_PER_FILE}"
        )

    if not matched_files:
        llm_response = (
            f"> No matches for `{pattern}` in `{search_path}`"
            + (f" ({'; '.join(notes)})" if notes else "")
            + "\n\nTry a shorter pattern, a different `include` filter or "
            "`regex=True`."
        )
        user_response = f"Search completed: 0 matches for `{pattern}`"
    else:
        header = (
            f"> Matches for `{pattern}` in `{search_path}` "
            f"({total_matches} match(es) in {len(matched_files)} file(s))"
        )
        llm_response = "\n\n".join([header] + groups)
        if notes:
            llm_response += f"\n\n> {'; '.join(notes)}."
        user_response = (
            f"Found {total_matches} match(es) in {len(matched_files)} file(s)"
            + (f" ({'; '.join(notes)})" if notes else "")
        )

    logger.info(
        "project_grep: pattern=%r matches=%d files=%d",
        pattern,
        total_matches,
        len(matched_files),
    )
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def _run_git(
    settings: CODXJuniorSettings,
    args: List[str],
    timeout: int = GIT_COMMAND_TIMEOUT,
) -> Tuple[bool, str, str]:
    """
    Run a git command inside the project without a shell.

    Args:
        settings: The project settings (the project path is the working dir).
        args: Git arguments (without the leading ``git``).
        timeout: Maximum seconds before the command is aborted.

    Returns:
        Tuple[bool, str, str]: (ok, stdout, stderr).
    """
    command = ["git", "--no-pager", "-c", "core.quotepath=false", *args]
    try:
        completed = subprocess.run(
            command,
            cwd=_project_root(settings),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as ex:
        return False, "", str(ex)
    return completed.returncode == 0, completed.stdout, completed.stderr


def _parse_name_status(raw: str) -> List[Dict[str, str]]:
    """
    Parse ``git diff --name-status -z`` output.

    Args:
        raw: NUL separated output.

    Returns:
        List of dicts with ``code`` and ``path`` keys. Renames/copies report
        their destination path.
    """
    tokens = [token for token in raw.split("\0") if token]
    entries: List[Dict[str, str]] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if index >= len(tokens):
            break
        path = tokens[index]
        index += 1
        code = (status or "M")[:1]
        if code in ("R", "C") and index < len(tokens):
            # Rename/copy: old path already consumed, destination comes next.
            path = tokens[index]
            index += 1
        entries.append({"code": code, "path": path})
    return entries


def _parse_numstat(raw: str) -> Dict[str, Tuple[int, int]]:
    """
    Parse ``git diff --numstat`` output into a path -> (added, deleted) map.

    Args:
        raw: Tab separated output, one line per file.

    Returns:
        Mapping of file path to its line counts. Binary files (-/-) map to 0/0.
    """
    counts: Dict[str, Tuple[int, int]] = {}
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added_text, deleted_text, path = parts[0], parts[1], parts[-1]
        counts[path.strip()] = (
            int(added_text) if added_text.isdigit() else 0,
            int(deleted_text) if deleted_text.isdigit() else 0,
        )
    return counts


def _untracked_patch(
    settings: CODXJuniorSettings, rel_path: str, max_chars: int
) -> str:
    """
    Build a small diff-like preview for an untracked file.

    Args:
        settings: The project settings.
        rel_path: Project-relative path.
        max_chars: Maximum characters to return.

    Returns:
        str: A synthetic patch header plus the first lines of the file.
    """
    abs_path = os.path.join(_project_root(settings), rel_path)
    if _is_binary_file(abs_path):
        return f"# New untracked binary file: {rel_path}"

    try:
        if os.path.getsize(abs_path) > MAX_GREP_FILE_BYTES:
            return f"# New untracked file is too large to preview: {rel_path}"
    except OSError:
        return f"# Cannot preview untracked file {rel_path}"

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as file:
            lines = file.read().splitlines()
    except OSError as ex:
        return f"# Cannot preview untracked file {rel_path}: {ex}"

    body: List[str] = [
        f"diff --git a/{rel_path} b/{rel_path}",
        "new file mode 100644",
        "--- /dev/null",
        f"+++ b/{rel_path}",
        f"@@ -0,0 +1,{len(lines)} @@",
    ]
    used = 0
    for line in lines[:200]:
        entry = f"+{line}"
        if used + len(entry) + 1 > max_chars:
            body.append("+... (truncated)")
            break
        body.append(entry)
        used += len(entry) + 1
    return "\n".join(body)


def project_changes(
    base: str = "HEAD",
    scope: str = "all",
    paths: Optional[Union[str, List[str]]] = None,
    include_patch: bool = True,
    context_lines: int = 3,
    max_files: int = 20,
    max_patch_chars: int = MAX_CHANGE_PATCH_CHARS,
    **kwargs,
) -> ToolResponse:
    """
    Inspect the changes in the working tree and compare them with a git ref.

    This is the fast way to answer "what changed?" before reviewing or
    committing. Use ``scope`` to choose which layers to show:

    - ``all`` (default): staged + unstaged changes against ``base``, plus
      untracked files.
    - ``staged``: what the next commit will include.
    - ``unstaged``: modifications not staged yet (working tree vs index),
      plus untracked files.
    - ``untracked``: files git does not track yet.

    Paths are optional filters (literal paths or git pathspecs) and every
    response states when files or patches were truncated. For a full
    repository snapshot (branches, remotes, worktrees) use ``repository_*``.

    Args:
        base: Commit, branch or tag to compare against. Defaults to ``HEAD``.
        scope: One of ``all``, ``staged``, ``unstaged`` or ``untracked``.
        paths: Optional path or list of paths to restrict the result.
        include_patch: Include per-file patches (default: True).
        context_lines: Context lines in each patch (0-10, default: 3).
        max_files: Maximum files listed and patched (1-200, default: 20).
        max_patch_chars: Total patch budget in characters (default: 40000).
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).

    Returns:
        ToolResponse: Contains:
            - user_response: Summary and the list of changed files.
            - llm_response: Summary, file list and per-file patches.

    Raises:
        Exception: If project settings are not provided.

    Example:
        >>> project_changes()                       # everything vs HEAD
        >>> project_changes(scope="staged")         # the next commit
        >>> project_changes(base="main", paths="src/")
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")

    base = (base or "HEAD").strip() or "HEAD"
    if base.startswith("-"):
        # Never let a ref filter look like a git option.
        return ToolResponse(
            user_response=f"⚠️ Invalid base revision `{base}`.",
            llm_response=f"project_changes: invalid base {base}",
        )
    scope = (scope or "all").strip().lower()
    if scope not in CHANGE_SCOPES:
        return ToolResponse(
            user_response=(
                f"⚠️ Invalid scope `{scope}`. Use one of: "
                + ", ".join(f"`{item}`" for item in CHANGE_SCOPES)
            ),
            llm_response=f"project_changes: invalid scope {scope}",
        )

    try:
        context_lines = max(0, min(int(context_lines or 0), 10))
        max_files = max(1, min(int(max_files or 20), MAX_CHANGE_FILES))
        max_patch_chars = max(
            1000, min(int(max_patch_chars or MAX_CHANGE_PATCH_CHARS), 200000)
        )
    except (TypeError, ValueError):
        return ToolResponse(
            user_response=(
                "⚠️ `context_lines`, `max_files` and `max_patch_chars` must "
                "be integers."
            ),
            llm_response="project_changes: invalid numeric arguments",
        )

    if isinstance(paths, str):
        path_filters = [paths] if paths.strip() else []
    elif paths:
        path_filters = [str(item).strip() for item in paths if str(item).strip()]
    else:
        path_filters = []

    ok, _, err = _run_git(settings, ["rev-parse", "--is-inside-work-tree"])
    if not ok:
        return ToolResponse(
            user_response=(
                "⚠️ This project is not a git repository, so local changes "
                "cannot be inspected."
            ),
            llm_response=f"project_changes: not a git repository: {err}",
        )

    if scope != "untracked":
        ok, _, err = _run_git(
            settings, ["rev-parse", "--verify", f"{base}^{{commit}}"]
        )
        if not ok:
            return ToolResponse(
                user_response=f"⚠️ Unknown base revision `{base}`.",
                llm_response=f"project_changes: bad base {base}: {err}",
            )

    diff_args: List[str] = []
    if scope == "staged":
        diff_args.append("--cached")
    if scope in ("all", "staged", "unstaged"):
        diff_args.append("--relative")
    base_args: List[str] = [] if scope == "unstaged" else [base]
    if scope == "untracked":
        base_args = []

    entries: List[Dict[str, Any]] = []
    if scope != "untracked":
        ok, name_status, err = _run_git(
            settings,
            [
                "diff", "--no-ext-diff", "--no-textconv",
                *diff_args, "--name-status", "-z",
                *base_args, "--", *path_filters,
            ],
        )
        if not ok:
            return ToolResponse(
                user_response=f"⚠️ Could not read changes: {err.strip() or 'git failed'}",
                llm_response=f"project_changes: git diff failed: {err}",
            )
        entries = _parse_name_status(name_status)

        counts: Dict[str, Tuple[int, int]] = {}
        ok_counts, numstat, _ = _run_git(
            settings,
            [
                "diff", "--no-ext-diff", "--no-textconv",
                *diff_args, "--numstat",
                *base_args, "--", *path_filters,
            ],
        )
        if ok_counts:
            counts = _parse_numstat(numstat)
        for entry in entries:
            added, deleted = counts.get(entry["path"], (0, 0))
            entry["additions"] = added
            entry["deletions"] = deleted

    if scope in ("all", "unstaged", "untracked"):
        ok_untracked, untracked_raw, _ = _run_git(
            settings,
            [
                "ls-files", "--others", "--exclude-standard", "-z",
                "--", *path_filters,
            ],
        )
        if ok_untracked:
            known = {entry["path"] for entry in entries}
            for path in (item for item in untracked_raw.split("\0") if item):
                if path in known:
                    continue
                entries.append({
                    "code": "?",
                    "path": path,
                    "additions": 0,
                    "deletions": 0,
                })

    entries.sort(key=lambda entry: entry["path"])
    total_files = len(entries)
    entries = entries[:max_files]

    added_total = sum(int(entry.get("additions") or 0) for entry in entries)
    deleted_total = sum(int(entry.get("deletions") or 0) for entry in entries)

    if scope == "untracked":
        title = "### 🔍 Untracked files"
    else:
        title = f"### 🔍 Changes vs `{base}` — scope `{scope}`"

    summary_lines: List[str] = [title, ""]
    if not entries:
        summary_lines.append("- No changes found.")
        llm_response = "\n".join(summary_lines)
        return ToolResponse(
            user_response="No changes found.",
            llm_response=llm_response,
        )

    summary_lines.append(
        f"- {total_files} file(s)"
        + (f", +{added_total} / -{deleted_total}" if scope != "untracked" else "")
    )
    if total_files > len(entries):
        summary_lines.append(
            f"- Showing {len(entries)} file(s); "
            f"{total_files - len(entries)} more not listed."
        )
    summary_lines.append("")
    summary_lines.append("**Files**")
    for entry in entries:
        code = entry.get("code", "M")
        label = GIT_STATUS_LABELS.get(code, "modified")
        counts = ""
        if code != "?":
            counts = (
                f" (+{entry.get('additions', 0)}"
                f"/-{entry.get('deletions', 0)})"
            )
        summary_lines.append(f"- `{code}` **{label}** `{entry['path']}`{counts}")

    detail_lines = list(summary_lines)

    if include_patch:
        remaining = max_patch_chars
        patch_sections: List[str] = []
        for entry in entries:
            if remaining <= 0:
                patch_sections.append(
                    f"\n> Patch budget reached; `{entry['path']}` and the "
                    "remaining files are not shown."
                )
                break

            rel_path = entry["path"]
            if entry.get("code") == "?":
                patch = _untracked_patch(settings, rel_path, remaining)
            else:
                ok_patch, patch, patch_err = _run_git(
                    settings,
                    [
                        "diff", "--no-ext-diff", "--no-textconv",
                        *diff_args, "--no-color",
                        f"-U{context_lines}", *base_args, "--", rel_path,
                    ],
                )
                if not ok_patch:
                    patch = f"# git diff failed for {rel_path}: {patch_err}"
                elif not patch.strip():
                    patch = (
                        f"# No textual patch for {rel_path} "
                        "(binary, mode-only or empty change)"
                    )

            if len(patch) > remaining:
                patch = patch[:remaining] + "\n... (patch truncated)"
            remaining -= len(patch)
            patch_sections.append(
                f"\n**`{rel_path}`**\n```diff\n{patch.rstrip()}\n```"
            )

        detail_lines.append("")
        detail_lines.extend(patch_sections)

    llm_response = "\n".join(detail_lines)
    user_response = "\n".join(summary_lines)

    logger.info(
        "project_changes: scope=%s base=%s files=%d shown=%d",
        scope,
        base,
        total_files,
        len(entries),
    )
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def _add_changes_to_git(settings: CODXJuniorSettings, file_path: str) -> bool:
    """
    Add previous changes to git before writing file.

    Args:
        settings: The project settings.
        file_path: The relative file path to stage in git.

    Returns:
        bool: True if git operation succeeded or git is not active, False otherwise.
    """
    try:
        # `git rev-parse` also works when .git is a file (linked worktree).
        ok, _, err = _run_git(settings, ["rev-parse", "--is-inside-work-tree"])
        if not ok:
            logger.debug("Git not initialized in project, skipping git operations")
            return True

        # Stage the file using an argument vector: paths with spaces or shell
        # metacharacters are never interpreted by a shell.
        ok, _, err = _run_git(settings, ["add", "--", file_path])
        if not ok:
            logger.warning("Git add failed for %s: %s", file_path, err)
            return False

        logger.debug("Successfully staged changes for: %s", file_path)
        return True

    except Exception as e:
        logger.warning("Error adding changes to git: %s", str(e))
        return False


def project_write_file(file_path: str, content: str, **kwargs) -> ToolResponse:
    """
    Write content to a project file, creating it if it doesn't exist.

    If git is active, stages the file changes before writing. This ensures
    previous changes are tracked before the new content is written.

    Args:
        file_path: The path to the file to write.
        content: The content to write to the file.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).

    Returns:
        ToolResponse: Contains:
            - user_response: Confirmation message with file path.
            - llm_response: Summary of the write operation.

    Raises:
        Exception: If project settings are not provided or if file path is invalid.

    Example:
        >>> project_write_file("src/new_file.py", "print('hello')")
        # Returns ToolResponse confirming the write operation
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")

    if not file_path:
        raise ValueError("file_path must be provided and cannot be empty")

    try:
        abs_path = path_to_absolute_project_path(
            settings=settings, file_path=file_path
        )
    except (OSError, ValueError) as e:
        error_msg = str(e)
        logger.error("Invalid file path for write operation: %s", file_path)
        return ToolResponse(
            user_response=f"error [{file_path}]\nERROR: {file_path} {error_msg}",
            llm_response=f"Write failed: {error_msg}",
        )

    if not is_path_within_project(settings, abs_path):
        error_msg = f"File path must belong to {settings.abs_project_path}"
        logger.error("Invalid file path for write operation: %s", file_path)
        return ToolResponse(
            user_response=f"error [{file_path}]\nERROR: {file_path} {error_msg}",
            llm_response=f"Write failed: {error_msg}",
        )

    try:
        # Get relative path for git operations
        rel_path = _to_relative_path(settings=settings, abs_path=abs_path)

        # Stage changes in git if git is active
        _add_changes_to_git(settings=settings, file_path=rel_path)

        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as file:
            file.write(content)

        logger.info("Successfully wrote to file: %s", file_path)
        file_size = len(content.encode("utf-8"))

        user_response = f"✓ File written successfully: `{rel_path}` ({file_size} bytes)"
        llm_response = f"Write completed: {rel_path} ({file_size} bytes)"

        return ToolResponse(user_response=user_response, llm_response=llm_response)

    except (IOError, OSError) as e:
        error_msg = str(e)
        logger.error("Error writing to file %s: %s", file_path, error_msg)
        return ToolResponse(
            user_response=f"error [{file_path}]\nERROR: {file_path} {error_msg}",
            llm_response=f"Write failed: {error_msg}",
        )

# Made with ❤️ by codx-junior