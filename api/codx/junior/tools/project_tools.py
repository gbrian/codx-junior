import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.utils.utils import document_to_context

def project_search(search: str, **kwargs) -> str:
    """
    Search for documents within a project using the provided search string.

    Args:
        search (str): The search query string used to find relevant documents.
        **kwargs: Additional keyword arguments that may include:
            - settings (CODXJuniorSettings): Optional settings for configuring the search.

    Returns:
        str: A concatenated string of document contexts that match the search query.
             Returns an empty string if no settings are provided or no documents are found.

    Raises:
        ValueError: If the `search` argument is not provided or is empty.
    """
    if not search:
        raise ValueError("The search argument must be provided and cannot be empty.")

    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if settings:
        documents = Knowledge(settings=settings).get_db().search(query=search)
        doc_content = "\n".join([document_to_context(doc) for doc in documents])
        return f"""
        QUERY: {search}
        RETURNED:
        {doc_content}
        """
    return "No results. Missing settings"

def project_read_file(file_path: str) -> str:
    """
    Read the content of a file.

    Args:
        file_path (str): The path to the file to read.

    Returns:
        str: The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise