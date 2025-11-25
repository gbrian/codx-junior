import os
import logging
import glob


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


from codx.junior.settings import CODXJuniorSettings
from codx.junior.engine import CODXJuniorSession

from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.utils.utils import document_to_code_block

from codx.junior.ai import AI
from codx.junior.model.model import CodxUser


def get_ai(settings, tool_name):
  # Prepare AI
  ai_settings = settings.get_llm_settings()
  user = CodxUser(username=tool_name)
  return AI(settings=settings, user=user)


async def code_block(file_path: str, code: str, code_language: str, **kwargs) -> str:
    """
    Ensure the code follows the project's standards and best practices and return it in a code block format.

    Args:
        file_path (str): Absolute file path.
        code (str): The code to process.
        code_language (str): The programming language of the code.

    Returns:
        str: The processed code in a code block format.
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")
    
    session = CODXJuniorSession(settings=settings)
    processed_code = await session.process_project_file_before_saving(file_path=file_path, content=code)
    
    return f"```{code_language} {file_path}\n{processed_code}\n```"


def path_to_absolute_project_path(settings: CODXJuniorSettings, file_path: str):
    if not file_path.startswith(settings.project_path):
        if file_path[0] == '/':
            file_path = file_path[1:]
        new_file_path = os.path.join(settings.project_path, file_path)
        if os.path.isfile(new_file_path):
            return new_file_path
        res = glob.glob(file_path, root_dir=settings.project_path, recursive=True, include_hidden=True)
        return str(res[0]) if res else None
    return file_path

def project_search(search: str, validation: str = None, **kwargs) -> str:
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
        documents = Knowledge(settings=settings).get_db().search(query=search, _limit=10)
        if not documents:
            return f"> No resulsts found for: '{search}' in project: '{settings.project_name}'"

        doc_sources = {}
        ai = get_ai(settings=settings, tool_name=__name__)
        if not validation:
            validation = search
        def read_doc(path):
            with open(path, 'r') as f:
                content = f.read()
                if ai:
                    return ai.chat(prompt=f"Content:\n```\n{content}\n```\nExtract from the content all lines related with this request:\n{validation}")[-1].content
                return content

        documents.sort(key=lambda doc: doc.metadata.get('index', 0))
        for doc in documents:
            source = doc.metadata['source']
            if not source in doc_sources:
                doc_sources[source] = doc
            else:
                doc_sources[source].page_content += doc.page_content


        doc_content = "\n".join([document_to_code_block(doc) for doc in doc_sources.values()])
        return "\n".join([
            f"> {settings.project_name} results for: '{search}'",
            doc_content
          ])
    return "No results. Missing settings"

def project_read_file(file_path: str, **kwargs) -> str:
    """
    Read the content of a file.

    Args:
        file_path (str): The path to the file to read.

    Returns:
        str: The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")
    file_path = path_to_absolute_project_path(settings=settings, file_path=file_path) 
    if not file_path or not file_path.startswith(settings.project_path):
        raise Exception("File path '%s' must belong to '%s'" % (file_path, settings.project_path))
    extension = file_path.split(".")[-1] if "." in file_path else ""
    with open(file_path, 'r') as file:
        return f"""```{extension} {file_path}
        {file.read()}
        ```
        """

def project_write_file(file_path: str, content: str, **kwargs) -> str:
    """
    Read the content of a file.

    Args:
        file_path (str): The path to the file to read.

    Returns:
        str: The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    settings: CODXJuniorSettings = kwargs.get("settings", None)
    if not settings:
        raise Exception("Invalid project settings")
    file_path = path_to_absolute_project_path(settings=settings, file_path=file_path)
    if not file_path or not file_path.startswith(settings.project_path):
        raise Exception("File path '%s' must belong to '%s'" % (file_path, settings.project_path))
    
    with open(file_path, 'w') as file:
        file.write(content)
