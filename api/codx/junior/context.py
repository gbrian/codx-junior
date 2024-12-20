import logging
import re
from pathlib import Path
from typing import Union, List, Optional

from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)
from codx.junior.utils import document_to_context
from codx.junior.ai.ai import AI
from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge import Knowledge

from codx.junior.utils import extract_json_blocks 

logger = logging.getLogger(__name__)

KNOWLEDGE_CONTEXT_SCORE_MATCH = re.compile(r".*([0-9]+)%", re.MULTILINE)

def parallel_validate_contexts(prompt, documents, settings: CODXJuniorSettings):
    ai = AI(settings=settings)
    score = float(settings.knowledge_context_cutoff_relevance_score)
    if not score:
      return documents
    
    # This function uses ThreadPoolExecutor to parallelize validation of contexts.
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(ai_validate_context, ai=ai, prompt=prompt, doc=doc): doc for doc in documents}
        valid_documents = []
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                valid_documents.append(result)

        doc_validation = '\n'.join([f"{doc.metadata['source']}: {doc.metadata['relevance_score']}" for doc in valid_documents if doc])
        logger.info(f"""[VALIDATE WITH CONTEXT]: {prompt}"
          {doc_validation}
          """)
        return [doc for doc in valid_documents \
          if doc and doc.metadata.get('relevance_score', 0) >= score]

from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field, validator
class AIDocValidateResponse(BaseModel):
    analysis_example = \
    """
    In this document we can see how to access to API methods getBookings with an example:
    ```ts
      this.API.getBookings({ "from": "now", "to: "now + 10d" })
    ```
    """
    analysis_doc = \
    """
    Analyse the document and create an explanation with examples of the important parts that can help answering user's request.
    Return a simple JSON object with your response like:
    ```json
    {{
      "score": 0.8,
      "analysis": {analysis_example}
      "
    }}
    """
    score: float = Field(description="Scores how important is this document from 0 to 1")
    analysis: str = Field(description=analysis_doc)

    # You can add custom validation logic easily with Pydantic.
    @validator("score")
    def score_is_valid(cls, field):
        return field

class AICodeValidateResponse(BaseModel):
  new_content: str = Field(description="Full generated content that will overwrite source file.")

AI_CODE_VALIDATE_RESPONSE_PARSER = PydanticOutputParser(pydantic_object=AICodeValidateResponse)


class AICodeChange(BaseModel):
    change_type: str = Field(description="Enumeration: new, update, delete, delete_file")
    file_path: str = Field(description="/file/path/to/file")
    existing_content: Optional[str] = Field(description="Existing content to be changed if applies", default="")
    new_content: Optional[str] = Field(description="New content if applies", default="")

class AICodeGerator(BaseModel):
    code_changes: List[AICodeChange] = Field(description="Conde changes")

AI_CODE_GENERATOR_PARSER = PydanticOutputParser(pydantic_object=AICodeGerator)

def ai_validate_context(ai, prompt, doc, retry_count=0):
    assert prompt
    parser = PydanticOutputParser(pydantic_object=AIDocValidateResponse)
    validation_prompt = \
    f"""
    Given this document:
    {document_to_context(doc)}
    
    Explain how important it is for the user's request:
    >>> "{prompt}" <<<

    OUPUT INSTRUCTIONS:
    {parser.get_format_instructions()}
    ```
    Where "score" is a value from 0 to 1 indicatting how important is this document, been 1 really important.
    """
    messages = [
      HumanMessage(content=validation_prompt),
    ]
    score = None
    response = None
    doc.metadata["relevance_score"] = -1
    try:
        messages = ai.chat(messages=messages)
        response = parser.invoke(messages[-1].content.strip())
        score = response.score
    except Exception as ex:
        logger.error(f"Error parsing content validation: {ex}")

    if score is not None:
        doc.metadata["relevance_score"] = score
        doc.metadata["analysis"] = response.analysis
        logger.debug(f"[validate_context] {doc.metadata.get('source')}: {score}")
    else:
      if not retry_count:
        logger.exception(f"[validate_context] re-trying failed validation\n{prompt}\n{response}")
        return ai_validate_context(ai, prompt, doc, retry_count=1)

      logger.error(f"[validate_context] failed to validate. Messages: {messages}")

    return doc

def find_relevant_documents (query: str, settings, ignore_documents=[]):
  
  knowledge_documents = Knowledge(settings=settings).search(query)
  def is_valid_document(doc):
    source = doc.metadata["source"]
    checks = [check for check in ignore_documents if check in source]
    if checks:
      return False
    return True
  
  documents = [doc for doc in knowledge_documents if is_valid_document(doc)]
  logger.info(f"""find_relevant_documents: 
    found {len(documents)} from project '{settings.project_name}' knowledge base.
    ignore_documents: {ignore_documents}
    total_valid: {len(documents)}
    """)
  
  if documents:
      # Filter out irrelevant documents based on a relevance score
      relevant_documents = [doc for doc in parallel_validate_contexts(
          query, documents, settings) if doc]
      file_list = [str(Path(doc.metadata["source"]).absolute())
                  for doc in relevant_documents]
      file_list = list(dict.fromkeys(file_list))  # Remove duplicates
      return relevant_documents, file_list
  return [], []



class DisplayablePath:
    display_filename_prefix_middle = "├── "
    display_filename_prefix_last = "└── "
    display_parent_prefix_middle = "    "
    display_parent_prefix_last = "│   "

    def __init__(self, path: Path, parent=None, is_last=False):
        self.path = Path(str(path))
        self.parent = parent
        self.is_last = is_last
        self.depth = self.parent.depth + 1 if self.parent else 0

    @property
    def display_name(self):
        return self.path.name + '/' if self.path.is_dir() else self.path.name

    @classmethod
    def make_tree(cls, root: Union[str, Path], parent=None, is_last=False, criteria=None):
        root = Path(str(root))
        criteria = criteria or cls._default_criteria

        displayable_root = cls(root, parent, is_last)
        yield displayable_root

        children = sorted(
            list(path for path in root.iterdir() if criteria(path)),
            key=lambda s: str(s).lower(),
        )
        count = 1
        for path in children:
            is_last = count == len(children)
            if path.is_dir():
                yield from cls.make_tree(
                    path, parent=displayable_root, is_last=is_last, criteria=criteria
                )
            count += 1

    @classmethod
    def _default_criteria(cls, path: Path) -> bool:
        return path.is_dir()

    @classmethod
    def make_tree_from_folders(cls, folders: List[Path], parent=None, is_last=False):
        if not folders:
            return

        # Sort folders to ensure consistent order
        folders = sorted(folders, key=lambda s: str(s).lower())

        # Create a dictionary to hold the folder structure
        folder_dict = {}
        for folder in folders:
            parts = folder.parts
            current_level = folder_dict
            for part in parts:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]

        # Helper function to recursively create DisplayablePath objects
        def create_displayable_paths(current_level, parent, is_last):
            items = sorted(current_level.items(), key=lambda s: str(s[0]).lower())
            count = 1
            for name, sub_level in items:
                path = Path(name)
                displayable_path = cls(path, parent, is_last=(count == len(items)))
                yield displayable_path
                if sub_level:
                    yield from create_displayable_paths(sub_level, displayable_path, is_last)
                count += 1

        # Start creating DisplayablePath objects from the root level
        yield from create_displayable_paths(folder_dict, parent, is_last)

    def displayable(self) -> str:
        if self.parent is None:
            return self.display_name

        _filename_prefix = (
            self.display_filename_prefix_last
            if self.is_last
            else self.display_filename_prefix_middle
        )

        parts = ["{!s} {!s}".format(_filename_prefix, self.display_name)]

        parent = self.parent
        while parent and parent.parent is not None:
            parts.append(
                self.display_parent_prefix_middle
                if parent.is_last
                else self.display_parent_prefix_last
            )
            parent = parent.parent

        return "".join(reversed(parts))

def extract_folders_from_files(files: List[Union[str, Path]]) -> List[Path]:
    folders = set()
    for file in files:
        file_path = Path(file)
        if file_path.is_file():
            folders.add(file_path.parent)
    return sorted(folders)

def generate_markdown_tree(files: List[Union[str, Path]]) -> str:
    folders = extract_folders_from_files(files)
    tree_generator = DisplayablePath.make_tree_from_folders(folders)
    markdown_lines = [node.displayable() for node in tree_generator]
    return "\n".join(markdown_lines)