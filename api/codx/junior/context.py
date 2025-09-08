import logging
import re
import os

from pathlib import Path
from typing import Union, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain.schema import AIMessage, HumanMessage, SystemMessage

from codx.junior.utils.utils import (
  document_to_context,
  extract_json_blocks
)
from codx.junior.ai.ai import AI
from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge_milvus import Knowledge 
from codx.junior.profiling.profiler import profile_function
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, field_validator
import pydantic

logger = logging.getLogger(__name__)
logger.info(f"PYDANTIC VERSION: {pydantic.__version__}")

class AICodeValidateResponse(BaseModel):
    new_content: str = Field(description="Full generated content that will overwrite source file.")

class AICodeChange(BaseModel):
    change_type: str = Field(description="Enumeration: new, update, delete, delete_file")
    file_path: str = Field(description="/file/path/to/file")
    existing_content: Optional[str] = Field(description="Existing content to be changed if applies", default="")
    new_content: Optional[str] = Field(description="New content if applies", default="")

class AICodePatch(BaseModel):
    file_path: str = Field(description="/file/path/to/file", default="")
    patch: str = Field(description="A file patch with the changes to be applied to the file")
    description: str = Field(description="Brief human friendly description about the change highlighting the most important changes", default="")

class AICodeGenerator(BaseModel):
    code_changes: List[AICodeChange] = Field(description="Code changes")
    code_patches: List[AICodePatch] = Field(description="A list of file patches for each modified file")

class AIRAGDocument(BaseModel):
    file_id: str = Field(description="Document id")
    file_path: str = Field(description="Document file path")
    content: str = Field(description="Document content")
    score: Optional[float] = Field(description="Score 0 to 1. Indicates how important is this RAG document related to the user's request")

class AIRAGValidate(BaseModel):
    user_request: str = Field(description="User request")
    documents: List[AIRAGDocument] = Field(description="List of documents found from user's request")

AI_CODE_VALIDATE_RESPONSE_PARSER = PydanticOutputParser(pydantic_object=AICodeValidateResponse)
AI_CODE_GENERATOR_PARSER = PydanticOutputParser(pydantic_object=AICodeGenerator)
AI_RAG_VALIDATE_PARSER = PydanticOutputParser(pydantic_object=AIRAGValidate)

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
class AIDocValidateResponse(BaseModel):
    score: float = Field(description="Scores how important is this document from 0 to 1")
    analysis: str = Field(description=analysis_doc)

    @field_validator("score")
    def score_is_valid(cls, field):
        return field

@profile_function
def parallel_validate_contexts(prompt, documents, settings: CODXJuniorSettings):
    ai = AI(settings=settings)
    score = float(settings.knowledge_context_cutoff_relevance_score or 0)
    if score == -1:
      logger.info(f"Validating RAG documents disabled!!")
      return documents
    
    logger.info(f"Validating RAG documents. Min score: {score}")
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
        return [doc for doc in valid_documents if doc and doc.metadata.get('relevance_score', 0) >= score]

@profile_function
def ai_validate_context(ai, prompt, doc, retry_count=0):
    assert prompt
    
    json_example = """{
      "score": 0.8,
      "analysis": "Brief explanation on why this document is relevant for the user request"
    }"""

    validation_prompt = f"""
    <document>
    {document_to_context(doc)}
    </document>
    <user_request>
    {prompt}
    </user_request>

    INSTRUCTIONS:
    Score from 0 to 1 how important is the document for the user_request.
    Where 0 is not important at all or has low value and 1 is highly imortant.
    Return a single JSON object like this:
    ```json
    {json_example}
    ```
    """
    messages = [HumanMessage(content=validation_prompt)]
    score = None
    response = None
    doc.metadata["relevance_score"] = -1
    try:
        messages = ai.chat(messages=messages)
        response = next(extract_json_blocks(messages[-1].content))
        score = float(response["score"])
        doc.metadata["relevance_score"] = score
        doc.metadata["score_analysis"] = response["analysis"]
    except Exception as ex:
        doc.metadata["score_error"] = str(ex)
        logger.error(f"Error parsing content validation: {ex}")

    if score is None:
        logger.error(f"[validate_context] failed to validate. Messages: {messages[-1]}")

    return doc

@profile_function
def find_relevant_documents(query: str, settings, knowledge_documents, ignore_documents=[], ai_validate=True):
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
    ai_validate: {ai_validate}
    """)
  
    if documents:
        # Filter out irrelevant documents based on a relevance score
        relevant_documents = documents
        if ai_validate:
            relevant_documents = validate_search_documents(query, documents, settings)
        file_list = [os.path.join(settings.project_path, str(Path(doc.metadata["source"]).absolute())) for doc in relevant_documents]
        file_list = list(dict.fromkeys(file_list))  # Remove duplicates
        return relevant_documents, file_list
    return [], []

@profile_function
def validate_search_documents(query, documents, settings):
    return [doc for doc in \
        parallel_validate_contexts(query, 
                            documents, 
                            settings) if doc]

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
