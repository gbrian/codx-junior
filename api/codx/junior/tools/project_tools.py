"""
Project tools for file operations, searching, and reading within a project.

This module provides tools for interacting with project files including reading,
writing, and searching functionality with support for bulk operations.

Made with ❤️ by codx-junior
"""

import os
import re
import logging
import glob
from typing import List, Optional, Union

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
GLOB_PATTERN_CHARS = ("*", "?", "[")
# Lists tracked and untracked (non-ignored) files, honoring the repo .gitignore
GIT_FILE_LIST_COMMAND = "git ls-files --cached --others --exclude-standard --full-name"
# Maximum number of matching project files returned by project_search
MAX_FILE_MATCHES = 100


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


def _to_relative_path(settings: CODXJuniorSettings, abs_path: str) -> str:
    """
    Convert an absolute file path to a relative path within the project.

    Args:
        settings: The project settings.
        abs_path: Absolute path to convert.

    Returns:
        str: Relative path from project root.
    """
    if abs_path.startswith(settings.abs_project_path):
        rel_path = os.path.relpath(abs_path, settings.abs_project_path)
        return rel_path
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
) -> Optional[str]:
    """
    Convert a relative or absolute file path to an absolute project path.

    Args:
        settings: The project settings.
        file_path: Relative or absolute path to resolve.

    Returns:
        Optional[str]: Absolute path if valid, None otherwise.
    """
    if not file_path.startswith(settings.abs_project_path):
        if file_path[0] == "/":
            file_path = file_path[1:]
        new_file_path = os.path.join(settings.abs_project_path, file_path)
        if os.path.isfile(new_file_path):
            return new_file_path
        res = glob.glob(
            file_path,
            root_dir=settings.abs_project_path,
            recursive=True,
            include_hidden=True,
        )
        return str(res[0]) if res else None
    return file_path


def _is_glob_pattern(path: str) -> bool:
    """
    Check whether a path string contains glob wildcard characters.

    Args:
        path: The path string to inspect.

    Returns:
        bool: True if the path contains glob wildcards ('*', '?' or '[').
    """
    return isinstance(path, str) and any(char in path for char in GLOB_PATTERN_CHARS)


def _expand_glob_pattern(settings: CODXJuniorSettings, pattern: str) -> List[str]:
    """
    Expand a glob pattern into the list of matching absolute file paths.

    The pattern may be relative or absolute, but only matches that resolve
    inside the project root are returned. Directories and paths outside the
    project are ignored.

    Args:
        settings: The project settings.
        pattern: A relative or absolute glob pattern (e.g. ``src/**/*.py``).

    Returns:
        List[str]: Sorted list of matching absolute file paths within the project.

    Example:
        >>> _expand_glob_pattern(settings, "web/src/components/**/*.vue")
        ['/project/web/src/components/Button.vue', ...]
    """
    rel_pattern = pattern
    if os.path.isabs(rel_pattern):
        rel_pattern = os.path.relpath(rel_pattern, settings.abs_project_path)
    rel_pattern = rel_pattern.lstrip("/")

    # Reject patterns that escape the project root
    if rel_pattern.startswith(".."):
        logger.warning("Glob pattern outside project root: %s", pattern)
        return []

    matches = glob.glob(
        rel_pattern,
        root_dir=settings.abs_project_path,
        recursive=True,
        include_hidden=True,
    )

    project_root = os.path.realpath(settings.abs_project_path)
    expanded = []
    for match in matches:
        abs_match = os.path.normpath(os.path.join(settings.abs_project_path, match))
        # Keep results inside the project and limited to files
        if not os.path.realpath(abs_match).startswith(project_root):
            continue
        if not os.path.isfile(abs_match):
            continue
        expanded.append(abs_match)

    logger.debug("Glob '%s' expanded to %d file(s)", pattern, len(expanded))
    return sorted(expanded)


def _read_single_file(settings: CODXJuniorSettings, file_path: str) -> tuple[str, Optional[str]]:
    """
    Read a single file and return its content or error.

    Args:
        settings: The project settings.
        file_path: Path to the file to read.

    Returns:
        tuple: (content_or_error, error_message_or_none)
            - If successful: (formatted_content, None)
            - If failed: (error_block, error_description)
    """
    try:
        abs_path = path_to_absolute_project_path(settings=settings, file_path=file_path)

        if not abs_path or not abs_path.startswith(settings.abs_project_path):
            error_msg = f"Path must belong to {settings.abs_project_path}"
            error_block = FILE_READ_ERROR_TEMPLATE % (file_path, file_path, error_msg)
            logger.warning("Invalid file path: %s", file_path)
            return error_block, error_msg

        if not os.path.isfile(abs_path):
            error_msg = "File not found"
            error_block = FILE_READ_ERROR_TEMPLATE % (file_path, file_path, error_msg)
            logger.warning("File not found: %s", abs_path)
            return error_block, error_msg

        extension = abs_path.split(".")[-1] if "." in abs_path else ""
        with open(abs_path, "r", encoding="utf-8") as file:
            content = file.read()
            rel_path = _to_relative_path(settings=settings, abs_path=abs_path)
            formatted = f"```{extension} {rel_path}\n{content}\n```"
            logger.debug("Successfully read file: %s", file_path)
            return formatted, None

    except (IOError, OSError) as e:
        error_msg = str(e)
        error_block = FILE_READ_ERROR_TEMPLATE % (file_path, file_path, error_msg)
        logger.error("Error reading file %s: %s", file_path, error_msg)
        return error_block, error_msg


def project_read_file(
    file_path: Union[str, List[str]], **kwargs
) -> ToolResponse:
    """
    Read the content of one or multiple files from the project.

    Supports bulk file reading to reduce tool calls. For optimal performance,
    read multiple related files in a single call instead of multiple individual calls.

    Glob patterns are supported for each path: any path containing glob
    wildcards ('*', '?', '[') is expanded and every matching file is read.
    Example: ``/project/web/src/components/**/*.vue`` reads all matching
    ``.vue`` files.

    Args:
        file_path: Single file path (str) or list of file paths to read.
                   Supports relative and absolute paths, and glob patterns.
        **kwargs: Additional arguments including:
            - settings (CODXJuniorSettings): Project settings (required).

    Returns:
        ToolResponse: Contains:
            - user_response: File contents with error blocks for invalid/missing files.
            - llm_response: Summary of successfully read files and errors.

    Raises:
        ValueError: If file_path is not provided or empty.
        Exception: If project settings are not provided.

    Example:
        Read multiple files at once:
        >>> project_read_file(["src/main.py", "config/settings.py"])
        # Returns ToolResponse with both files and summary

        Read every file matching a glob pattern:
        >>> project_read_file("web/src/components/**/*.vue")
        # Returns ToolResponse with all matching .vue files and summary
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

    # Read all files (expanding glob patterns into their matching files)
    contents = []
    successful_reads = []
    failed_reads = []

    for fp in file_paths:
        # Expand glob patterns to all matching files
        if _is_glob_pattern(fp):
            matched_files = _expand_glob_pattern(settings=settings, pattern=fp)
            if not matched_files:
                error_msg = "No files match pattern"
                error_block = FILE_READ_ERROR_TEMPLATE % (fp, fp, error_msg)
                contents.append(error_block)
                failed_reads.append((fp, error_msg))
                logger.warning("Glob pattern matched no files: %s", fp)
                continue

            for matched_path in matched_files:
                content, error = _read_single_file(
                    settings=settings, file_path=matched_path
                )
                contents.append(content)

                if error:
                    failed_reads.append((matched_path, error))
                else:
                    successful_reads.append(
                        _to_relative_path(settings=settings, abs_path=matched_path)
                    )
            continue

        content, error = _read_single_file(settings=settings, file_path=fp)
        contents.append(content)

        if error:
            failed_reads.append((fp, error))
        else:
            successful_reads.append(fp)

    # Build user content
    llm_response = "\n".join(contents)

    # Build LLM feedback summary
    summary_lines = [f"Read {len(successful_reads)} file(s)"]
    if successful_reads:
        summary_lines.append(f"Successfully read: {', '.join(successful_reads)}")
    if failed_reads:
        summary_lines.append(
            f"Failed to read {len(failed_reads)} file(s): "
            + ", ".join([f[0] for f in failed_reads])
        )

    user_response = " | ".join(summary_lines)
    logger.info("File read operation completed: %s", llm_response)

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


def list_project_files(settings: CODXJuniorSettings) -> List[str]:
    """
    List the project files, honoring ``.gitignore`` and custom project ignores.

    Files and folders matched by the repository's ``.gitignore`` are discarded
    by querying git directly. In addition, every path matched by the custom
    ignore patterns defined in the project settings (``knowledge_file_ignore``,
    sub-projects, wiki path, ``.git``, ``node_modules``, ...) is filtered out.

    Args:
        settings: The project settings.

    Returns:
        List[str]: Sorted list of project-relative file paths.

    Example:
        >>> list_project_files(settings)
        ['README.md', 'codx/junior/settings.py', 'codx/junior/tools/project_tools.py']
    """
    project_root = os.path.abspath(settings.abs_project_path)
    ignore_patterns = settings.get_ignore_patterns()

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
    Find project files whose path matches every term in a query.

    Matching is case-insensitive and requires each whitespace-separated token of
    the query to be present in the project-relative path. Files are filtered with
    ``.gitignore`` and the project's custom ignore patterns (see
    :func:`list_project_files`).

    Args:
        settings: The project settings.
        query: Space separated terms matched against the file paths.
        limit: Maximum number of matching files to return.

    Returns:
        List[str]: Matching project-relative file paths.

    Example:
        >>> find_project_files(settings, "settings.py")
        ['codx/junior/settings.py']
    """
    tokens = [token for token in re.split(r"\s+", (query or "").strip().lower()) if token]
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

    Supports bulk searching to reduce tool calls. For optimal performance,
    search for multiple related concepts in a single call.

    Args:
        search: Single search query (str) or list of queries to execute.
        validation: Optional text to validate and filter search results.
                   Helps extracting only relevant content from large documents.
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

    ai = get_ai(settings=settings, tool_name=__name__)
    validation_text = validation or ", ".join(search_queries)

    all_results = []
    queries_executed = 0
    total_documents_found = 0

    for query in search_queries:
        logger.debug("Executing search query: %s", query)
        documents = Knowledge(settings=settings).get_db().search(query=query, _limit=10)

        if not documents:
            logger.info("No results found for query: %s", query)
            continue

        queries_executed += 1
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

        # Filter documents using validation text if AI is available
        for doc in doc_sources.values():
            if ai:
                try:
                    filtered_content = ai.chat(
                        prompt=(
                            f"Content:\n```\n{doc.page_content}\n```\n"
                            f"Extract from the content all lines related with: {validation_text}"
                        )
                    )[-1].content
                    doc.page_content = filtered_content
                except Exception as e:
                    logger.error("Error filtering document content: %s", str(e))

            # Convert document source to relative path if it belongs to project
            source = doc.metadata.get("source", "")
            if source and source.startswith(settings.abs_project_path):
                rel_source = _to_relative_path(settings=settings, abs_path=source)
                doc.metadata["source"] = rel_source

            all_results.append(document_to_code_block(doc))

    # Find project files whose path matches the query.
    # The repository .gitignore and the project's custom ignore patterns are honored.
    file_matches: List[str] = []
    try:
        file_matches = find_project_files(
            settings=settings, query=" ".join(search_queries)
        )
    except Exception as ex:
        logger.warning("Error finding project files: %s", ex)

    file_section = ""
    if file_matches:
        file_section = "\n".join(
            [f"\n### Matching files ({len(file_matches)})"]
            + [f"- `{rel_path}`" for rel_path in file_matches]
        )

    # Build responses
    if not all_results and not file_matches:
        llm_response = (
            f"> No results found for: '{', '.join(search_queries)}' "
            f"in project: '{settings.project_name}'"
        )
        user_response = (
            "Search completed: 0 queries executed, 0 documents found, 0 files matched"
        )
    else:
        llm_response = "\n".join(
            part for part in [
                f"> {settings.project_name} results for: '{', '.join(search_queries)}'",
                "\n".join(all_results),
                file_section,
            ] if part
        )
        user_response = (
            f"Search completed: {queries_executed} queries executed, "
            f"{total_documents_found} documents found, {len(file_matches)} files matched"
        )

    logger.info("Search operation completed: %s", llm_response)
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
        # Check if git is initialized in the project
        git_dir = os.path.join(settings.abs_project_path, ".git")
        if not os.path.isdir(git_dir):
            logger.debug("Git not initialized in project, skipping git operations")
            return True

        # Stage the file changes using git add
        from codx.junior.utils.utils import exec_command
        git_cmd = f"git add {file_path}"
        stdout, stderr = exec_command(git_cmd, cwd=settings.abs_project_path)

        if stderr and "fatal" in stderr.lower():
            logger.warning("Git add failed for %s: %s", file_path, stderr)
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

    abs_path = path_to_absolute_project_path(settings=settings, file_path=file_path)
    if not abs_path or not abs_path.startswith(settings.abs_project_path):
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