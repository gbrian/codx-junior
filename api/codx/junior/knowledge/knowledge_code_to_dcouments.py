import logging
import json

from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.schema.document import Document

from gpt_engineer.utils import extract_json_blocks 

from gpt_engineer.core.ai import AI
from gpt_engineer.core.settings import GPTEngineerSettings
from gpt_engineer.knowledge.knowledge_prompts import KnowledgePrompts
from gpt_engineer.prompts import CodeToChunksPrompt

from gpt_engineer.settings import (
    LANGUAGE_FROM_EXTENSION
)

logger = logging.getLogger(__name__)

class KnowledgeCodeToDocuments:
    def __init__(self, settings: GPTEngineerSettings):
        self.settings = settings
        self.knowledge_prompts = KnowledgePrompts(settings=settings)
        self.ai = None

    def get_ai(self):
        from gpt_engineer.core import build_ai
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
      messages = self.get_ai().next(messages=[], prompt=prompt, step_name="KnowledgeCodeToDocuments::load") 
      chunks = []
      try:
          chunks = prompter.get_output(messages[-1].content).chunks
      except:
          logger.exception(f"Error parsing document, trying continue for {file_path}")
          # Try continue
          messages = self.get_ai().next(messages=messages, prompt="Continue!", step_name="KnowledgeCodeToDocuments::load") 
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