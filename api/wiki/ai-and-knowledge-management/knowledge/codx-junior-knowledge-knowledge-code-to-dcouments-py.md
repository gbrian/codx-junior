This Python script, `knowledge_code_to_documents.py`, is designed to process code files and convert them into a structured format suitable for knowledge management. It leverages the `langchain` library for AI interactions and document handling.

### Core Functionality

The main class, `KnowledgeCodeToDocuments`, handles the conversion process.

*   **Initialization (`__init__`)**:
    *   Initializes with `CODXJuniorSettings` to configure the AI and other settings.
    *   Instantiates `KnowledgePrompts` for prompt management.
    *   Initializes the AI instance lazily using `get_ai()`.

*   **AI Instance (`get_ai`)**:
    *   This method ensures that an AI instance is available. If not already created, it builds one using the `build_ai` function from the `codx.junior` module.

*   **Loading and Processing (`load`)**:
    *   Takes a `file_path` as input.
    *   Determines the programming language based on the file extension (using `LANGUAGE_FROM_EXTENSION`).
    *   Reads the entire content of the code file.
    *   Creates a `langchain.documents.Document` object with the file's content and metadata including source, language, and loader type.
    *   Uses `CodeToChunksPrompt` to generate a prompt for the AI, including the file's source, language, and content.
    *   Sends the prompt to the AI via `self.get_ai().chat()`.
    *   **Chunk Extraction**: Attempts to parse the AI's response to extract code chunks. If parsing fails, it prompts the AI to "Continue!" and retries.
    *   **Document Creation from Chunks**:
        *   Iterates through the extracted `chunks`.
        *   For each chunk, it creates a new `Document` object.
        *   The `page_content` of this new document is a JSON string of the chunk.
        *   The `metadata` is inherited from the original document and augmented with chunk-specific details (like function name, description, etc., if present in the chunk) and an `index`.
    *   Returns a list of these chunk-based `Document` objects.
    *   Includes error handling for JSON parsing and AI response processing.

### Dependencies

*   `logging`: For logging information and errors.
*   `json`: For handling JSON data.
*   `langchain.messages`: For constructing AI messages (`AIMessage`, `HumanMessage`, `SystemMessage`).
*   `langchain_core.documents.Document`: The core document object used by Langchain.
*   `codx.junior.utils.utils.extract_json_blocks`: A utility function (presumably) for extracting JSON from text.
*   `codx.junior.ai.AI`: The AI interface class.
*   `codx.junior.settings.CODXJuniorSettings`: Settings for the junior CODX components.
*   `codx.junior.knowledge.knowledge_prompts.KnowledgePrompts`: Manages prompts specific to the knowledge module.
*   `codx.junior.prompts.CodeToChunksPrompt`: A prompt template for converting code to document chunks.
*   `codx.junior.knowledge.settings.LANGUAGE_FROM_EXTENSION`: A mapping from file extensions to programming languages.

```python /codx/junior/knowledge/knowledge_code_to_dcouments.py
import logging
import json

from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.documents import Document

from codx.junior.utils.utils import extract_json_blocks 

from codx.junior.ai import AI
from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge_prompts import KnowledgePrompts
from codx.junior.prompts import CodeToChunksPrompt

from codx.junior.knowledge.settings import (
    LANGUAGE_FROM_EXTENSION
)

logger = logging.getLogger(__name__)

class KnowledgeCodeToDocuments:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.knowledge_prompts = KnowledgePrompts(settings=settings)
        self.ai = None

    def get_ai(self):
        from codx.junior import build_ai
        if not self.ai:
          self.ai = build_ai(settings=self.settings)
        return self.ai

    def load(self, file_path):
      suffix = file_path.split(".")[-1] if "." in file_path else "txt"
      language = LANGUAGE_FROM_EXTENSION.get(suffix) or suffix
      doc = None
      metadata = {
          "source": file_path,
          "language": language,
          "loader_type": "code_to_chunks"
      } 
      with open(file_path) as f:
          page_content = f.read()
          doc = Document(page_content=page_content, metadata=metadata)
      prompter = CodeToChunksPrompt()
      prompt = prompter.get_prompt(source=file_path, language=language, page_content=page_content)
      messages = []
      messages = self.get_ai().chat(messages=[], prompt=prompt) 
      chunks = []
      try:
          chunks = prompter.get_output(messages[-1].content).chunks
      except:
          logger.exception(f"Error parsing document, trying continue for {file_path}")
          # Try continue
          messages = self.get_ai().chat(messages=messages, prompt="Continue!") 
      try:
          chunks = chunks if chunks else prompter.get_output(messages[-1].content).chunks
          def doc_from_chunk(ix, chunk):
              page_content = json.dumps(chunk)
              del chunk["code"]
              metadata = {
                **doc.metadata,
                **chunk,
                "index": ix
              }
              return Document(page_content=page_content, metadata=metadata)
          return [ doc_from_chunk(ix, chunk.__dict__) for ix, chunk in enumerate(chunks) ]
      except:
          logger.exception(f"Error parsing document {messages[-1].content}")
```