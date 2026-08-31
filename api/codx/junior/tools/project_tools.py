import os
import logging
import glob
import errno
from typing import List, Union


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


from codx.junior.settings import CODXJuniorSettings
from codx.junior.engine import CODXJuniorSession

from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.utils.utils import document_to_code_block

from codx.junior.ai import AI
from codx.junior.model.model import CodxUser
from codx.junior.tools.model import ToolResponse


def get_ai(settings: CODXJuniorSettings, tool_name: str) -> AI:
    """Initialize and return an AI instance for the given settings and tool.

    Args:
        settings (CODXJuniorSettings): The project settings.
        tool_name (str): The name of the tool requesting the AI instance.

    Returns:
        AI: An initialized AI instance.

    Made with ❤️ by codx-junior
    """
    ai_settings = settings.get_llm_settings()
    user = CodxUser(username=tool_name)
    return AI(settings=settings, user=user)


async def code_block(file_path: str, code: str, code_language: str, **kwargs) -> str:
    """Ensure the code follows the project's standards and best practices and return it in a code block format.

    Args:
        file_path (str): Absolute file path.
        code (str): The code to process.
        code_language (str): The programming language of the code.

    Returns:
        str: The processed code in a code block format.

    Made with ❤️ by codx-junior
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")
    
    session = CODXJuniorSession(settings=settings)
    processed_code = await session.process_project_file_before_saving(file_path=file_path, content=code)
    
    return f"```{code_language} {file_path}\n{processed_code}\n```"


def path_to_absolute_project_path(settings: CODXJuniorSettings, file_path: str) -> Union[str, None]:
    """Convert a relative or absolute file path to an absolute project path.

    Args:
        settings (CODXJuniorSettings): The project settings containing the absolute project path.
        file_path (str): The file path to convert (can be relative or absolute).

    Returns:
        Union[str, None]: The absolute path if the file exists within the project, None otherwise.

    Made with ❤️ by codx-junior
    """
    if not file_path.startswith(settings.abs_project_path):
        if file_path[0] == '/':
            file_path = file_path[1:]
        new_file_path = os.path.join(settings.abs_project_path, file_path)
        if os.path.isfile(new_file_path):
            return new_file_path
        res = glob.glob(file_path, root_dir=settings.abs_project_path, recursive=True, include_hidden=True)
        return str(res[0]) if res else None
    return file_path


def project_read_file(file_paths: List[str], **kwargs) -> Union[str, ToolResponse]:
    """Read the content of multiple files in a project.

    Supports bulk operations: pass multiple file paths in a single call to reduce API calls.
    Returns code blocks for valid files and error blocks for invalid ones.
    
    Returns a ToolResponse with full content for users and a concise summary for LLM context.

    Args:
        file_paths (List[str]): Array of paths to files to read. Can include multiple files
                               to reduce API calls (e.g., ['src/config.py', 'src/main.py']).
        **kwargs: Additional keyword arguments:
            - settings (CODXJuniorSettings): Optional settings for configuring file reading.

    Returns:
        Union[str, ToolResponse]: ToolResponse with detailed file contents and summary,
                                 or error string if settings are invalid.

    Raises:
        ValueError: If file_paths is not provided or is empty.
        Exception: If settings are invalid or missing.

    Example:
        Read multiple related files in a single call:
        >>> project_read_file(['src/auth.py', 'src/models.py', 'tests/test_auth.py'])

    Made with ❤️ by codx-junior
    """
    if not file_paths:
        raise ValueError("The file_paths argument must be provided and cannot be empty.")

    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")

    results: List[str] = []
    file_summaries: List[str] = []
    successful_files: int = 0
    failed_files: int = 0

    for file_path in file_paths:
        try:
            resolved_path = path_to_absolute_project_path(settings=settings, file_path=file_path)
            
            # Check if path resolution failed
            if not resolved_path:
                error_block = f"```error {file_path}\nERROR: {file_path} file not found\n```"
                results.append(error_block)
                file_summaries.append(f"- {file_path}: NOT FOUND")
                failed_files += 1
                logger.warning("File path resolution failed for: %s", file_path)
                continue

            # Check if path is within project root (redundant check but safe)
            if not resolved_path.startswith(settings.abs_project_path):
                error_block = f"```error {file_path}\nERROR: {file_path} path not within project root\n```"
                results.append(error_block)
                file_summaries.append(f"- {file_path}: OUTSIDE PROJECT ROOT")
                failed_files += 1
                logger.warning("File path is outside project root: %s", file_path)
                continue

            # Check if file exists
            if not os.path.exists(resolved_path):
                error_block = f"```error {file_path}\nERROR: {file_path} file not found\n```"
                results.append(error_block)
                file_summaries.append(f"- {file_path}: NOT FOUND")
                failed_files += 1
                logger.warning("File does not exist at resolved path: %s", resolved_path)
                continue

            # Read file content
            with open(resolved_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Extract extension for code block syntax
            extension = os.path.splitext(resolved_path)[1][1:] or "txt"
            
            # Format success block
            success_block = f"```{extension} {resolved_path}\n{content}\n```"
            results.append(success_block)
            
            # Create summary: file path and line count
            line_count = len(content.splitlines())
            file_summaries.append(f"- {file_path}: {line_count} lines")
            successful_files += 1

        except Exception as e:
            # Catch unexpected errors during reading or processing
            error_block = f"```error {file_path}\nERROR: {file_path} {str(e)}\n```"
            results.append(error_block)
            file_summaries.append(f"- {file_path}: ERROR - {str(e)}")
            failed_files += 1
            logger.error("Error reading file %s: %s", file_path, str(e))

    # Join all results with double newlines to separate blocks
    user_content = "\n\n".join(results)
    
    # Create LLM summary
    llm_summary = f"Read {successful_files} file(s) successfully"
    if failed_files > 0:
        llm_summary += f" and {failed_files} file(s) failed"
    llm_summary += ":\n" + "\n".join(file_summaries)
    
    return ToolResponse(user_content=user_content, llm_content=llm_summary)


def project_search(search: Union[str, List[str]], validation: str = None, **kwargs) -> Union[str, ToolResponse]:
    """Search for documents within a project using provided search strings.

    Supports bulk operations: pass multiple search queries in a single call to reduce API calls.
    Each query returns the most relevant documents from the project knowledge base.
    
    Returns a ToolResponse with full search results for users and a concise summary for LLM context.

    Args:
        search (Union[str, List[str]]): Search query or list of search queries.
                                       Use list for multiple searches in one call:
                                       ['authentication logic', 'user schema', 'API endpoints']
        validation (str, optional): Brief text to validate and filter search results.
                                   Helps reduce large documents and extract only relevant content.
        **kwargs: Additional keyword arguments:
            - settings (CODXJuniorSettings): Optional settings for configuring the search.

    Returns:
        Union[str, ToolResponse]: ToolResponse with detailed search results and summary,
                                 or error message string if no settings provided.

    Raises:
        ValueError: If search argument is not provided or is empty.

    Example:
        Search for multiple topics in a single call:
        >>> project_search(['database queries', 'authentication', 'error handling'], 
        ...                validation='security and performance')

    Made with ❤️ by codx-junior
    """
    if not search:
        raise ValueError("The search argument must be provided and cannot be empty.")

    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        return "No results. Missing settings"

    # Normalize search input to list
    search_queries: List[str] = search if isinstance(search, list) else [search]

    all_doc_sources: dict = {}
    ai = get_ai(settings=settings, tool_name=__name__)
    validation_text = validation or " ".join(search_queries)

    try:
        # Process each search query
        for query in search_queries:
            logger.debug("Executing search query: %s", query)
            documents = Knowledge(settings=settings).get_db().search(query=query, _limit=10)
            
            if not documents:
                logger.info("No results found for search query: %s", query)
                continue

            # Sort documents by index for consistent ordering
            documents.sort(key=lambda doc: doc.metadata.get('index', 0))

            # Aggregate documents by source to avoid duplicates
            for doc in documents:
                source = doc.metadata.get('source')
                if source:
                    if source not in all_doc_sources:
                        all_doc_sources[source] = doc
                    else:
                        # Append content for duplicate sources
                        all_doc_sources[source].page_content += "\n" + doc.page_content

        if not all_doc_sources:
            search_description = " or ".join(f"'{q}'" for q in search_queries)
            no_results_msg = f"> No results found for: {search_description} in project: '{settings.project_name}'"
            return ToolResponse(user_content=no_results_msg, llm_content="Search completed: no documents found")

        # Extract relevant content using AI if available
        if ai:
            filtered_docs = []
            for source, doc in all_doc_sources.items():
                try:
                    filtered_content = ai.chat(
                        prompt=f"Content:\n```\n{doc.page_content}\n```\n"
                                f"Extract from the content all lines related with this request:\n{validation_text}"
                    )[-1].content
                    doc.page_content = filtered_content
                    filtered_docs.append(doc)
                except Exception as e:
                    logger.warning("Error filtering document from %s: %s", source, str(e))
                    filtered_docs.append(doc)
        else:
            filtered_docs = list(all_doc_sources.values())

        # Generate output
        doc_content = "\n".join([document_to_code_block(doc) for doc in filtered_docs])
        search_description = " or ".join(f"'{q}'" for q in search_queries)
        
        user_content = "\n".join([
            f"> {settings.project_name} results for: {search_description}",
            doc_content
        ])
        
        # Create LLM summary
        llm_summary = f"Found {len(filtered_docs)} document(s) matching: {search_description}"
        
        return ToolResponse(user_content=user_content, llm_content=llm_summary)

    except Exception as e:
        logger.error("Error during project search: %s", str(e))
        search_description = " or ".join(f"'{q}'" for q in search_queries)
        error_msg = f"> Error searching for {search_description}: {str(e)}"
        return ToolResponse(user_content=error_msg, llm_content=f"Search failed: {str(e)}")


def project_write_file(file_path: str, content: str, **kwargs) -> ToolResponse:
    """Write content to a file in the project.
    
    Returns a ToolResponse with confirmation for users and a summary for LLM context.

    Args:
        file_path (str): The path to the file to write (relative or absolute within project).
        content (str): The content to write to the file.
        **kwargs: Additional keyword arguments:
            - settings (CODXJuniorSettings): Settings for configuring file writing.

    Returns:
        ToolResponse: Confirmation message with user content and LLM summary.

    Raises:
        Exception: If settings are invalid or file path is outside project root.

    Made with ❤️ by codx-junior
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")
    
    file_path = path_to_absolute_project_path(settings=settings, file_path=file_path)
    if not file_path or not file_path.startswith(settings.abs_project_path):
        raise Exception("File path '%s' must belong to '%s'" % (file_path, settings.abs_project_path))
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    
    logger.info("Successfully wrote content to file: %s", file_path)
    
    # Create user-facing and LLM summary content
    line_count = len(content.splitlines())
    char_count = len(content)
    
    user_content = f"File written successfully: {file_path}"
    llm_summary = f"File written: {file_path} ({line_count} lines, {char_count} characters)"
    
    return ToolResponse(user_content=user_content, llm_content=llm_summary)

# Made with ❤️ by codx-junior