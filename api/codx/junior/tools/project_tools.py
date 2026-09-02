"""
Project tools for file operations, searching, and reading within a project.

This module provides tools for interacting with project files including reading,
writing, and searching functionality with support for bulk operations.

Made with ❤️ by codx-junior
"""

import os
import logging
import glob
from typing import List, Optional, Union

from codx.junior.settings import CODXJuniorSettings
from codx.junior.engine import CODXJuniorSession
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.utils.utils import document_to_code_block
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
            formatted = f"```{extension} {file_path}\n{content}\n```"
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

    # Read all files
    contents = []
    successful_reads = []
    failed_reads = []

    for fp in file_paths:
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


def project_search(
    search: Union[str, List[str]], validation: Optional[str] = None, **kwargs
) -> ToolResponse:
    """
    Search for documents within a project using one or more search queries.

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
            - llm_response: Summary of search queries and results found.

    Raises:
        ValueError: If search argument is not provided or is empty.

    Example:
        Search for multiple concepts at once:
        >>> project_search(["authentication", "user session", "login"])
        # Returns ToolResponse with results for all queries and summary
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

            all_results.append(document_to_code_block(doc))

    # Build responses
    if not all_results:
        llm_response = (
            f"> No results found for: '{', '.join(search_queries)}' "
            f"in project: '{settings.project_name}'"
        )
        user_response = f"Search completed: 0 queries executed, 0 documents found"
    else:
        llm_response = "\n".join(
            [
                f"> {settings.project_name} results for: '{', '.join(search_queries)}'",
                "\n".join(all_results),
            ]
        )
        user_response = (
            f"Search completed: {queries_executed} queries executed, "
            f"{total_documents_found} documents found"
        )

    logger.info("Search operation completed: %s", llm_response)
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def project_write_file(file_path: str, content: str, **kwargs) -> ToolResponse:
    """
    Write content to a project file, creating it if it doesn't exist.

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
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as file:
            file.write(content)

        logger.info("Successfully wrote to file: %s", file_path)
        file_size = len(content.encode("utf-8"))

        user_response = f"✓ File written successfully: `{file_path}` ({file_size} bytes)"
        llm_response = f"Write completed: {file_path} ({file_size} bytes)"

        return ToolResponse(user_response=user_response, llm_response=llm_response)

    except (IOError, OSError) as e:
        error_msg = str(e)
        logger.error("Error writing to file %s: %s", file_path, error_msg)
        return ToolResponse(
            user_response=f"error [{file_path}]\nERROR: {file_path} {error_msg}",
            llm_response=f"Write failed: {error_msg}",
        )

# Made with ❤️ by codx-junior