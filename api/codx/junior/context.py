import logging
import re
from termcolor import colored
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
from codx.junior.settings import GPTEngineerSettings
from codx.junior.knowledge.knowledge import Knowledge

from codx.junior.utils import extract_json_blocks 

logger = logging.getLogger(__name__)

KNOWLEDGE_CONTEXT_SCORE_MATCH = re.compile(r".*([0-9]+)%", re.MULTILINE)

def validate_context(ai, dbs, prompt, doc, score):
    # This function now handles a single document.
    if '@ai' in doc.metadata.get('user_input', ''):
        return ai_validate_context(ai, dbs, prompt, doc)
    score = float(doc.metadata.get('user_input'))
    doc.metadata["relevance_score"] = score
    logger.debug(f"[validate_context] {doc.metadata['source']}: {score}")
    if score < score:
        return None
    return doc

def parallel_validate_contexts(dbs, prompt, documents, settings: GPTEngineerSettings):
    ai = AI(settings=settings)
    score = float(settings.knowledge_context_cutoff_relevance_score)
    if not score:
      return documents
    #dbs.input.append(
    #  HISTORY_PROMPT_FILE, f"\n[[VALIDATE_CONTEXT]]\n{prompt}\nNum docs: {len(documents)}"
    #)
    # This function uses ThreadPoolExecutor to parallelize validation of contexts.
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(ai_validate_context, ai=ai, dbs=dbs, prompt=prompt, doc=doc): doc for doc in documents}
        valid_documents = []
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                valid_documents.append(result)

        def colored_result(doc):
          res_str = f"{doc.metadata['source']}: {doc.metadata['relevance_score']}"
          if doc.metadata['relevance_score'] >= score:
            return colored(res_str, "green")
          return colored(res_str, "red")

        print("\n".join([
          "",
          colored(f"[VALIDATE WITH CONTEXT]: {prompt}", "green"),
          "\n".join([colored_result(doc) for doc in valid_documents if doc]),
          ""
        ]))
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

def ai_validate_context(ai, dbs, prompt, doc, retry_count=0):
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
        messages = ai.next(messages=messages, step_name="ai_validate_context")
        response = parser.invoke(messages[-1].content.strip())
        score = response.score
    except:
        pass
    if score:
        doc.metadata["relevance_score"] = score
        doc.metadata["analysis"] = response.analysis
        logger.debug(f"[validate_context] {doc.metadata.get('source')}: {score}")
    else:
      if not retry_count:
        logger.exception(colored(f"[validate_context] re-trying failed validation\n{prompt}\n{response}", "red"))
        return ai_validate_context(ai, dbs, prompt, doc, retry_count=1)

      logger.error(colored(f"[validate_context] failed to validate. prompt: {prompt}\nMessages: {messages}", "red"))

    return doc

def find_relevant_documents (query: str, settings, ignore_documents=[]):
  from codx.junior import build_dbs, build_ai

  ai = AI(settings=settings)
  dbs = build_dbs(settings)
  documents = Knowledge(settings=settings).search(query)
  logger.info(f"find_relevant_documents: [{settings.project_name}] Knowledge.search doc length: {len(documents)}")
  def is_valid_document(doc):
    source = doc.metadata["source"]
    checks = [check for check in ignore_documents if check in source]
    if checks:
      return False
    return True
  
  documents = [doc for doc in documents if is_valid_document(doc)]
  if documents:
      # Filter out irrelevant documents based on a relevance score
      relevant_documents = [doc for doc in parallel_validate_contexts(
          dbs, query, documents, settings) if doc]
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