import logging

from langchain.schema.document import Document
from langchain.text_splitter import Language
from langchain.document_loaders.parsers import LanguageParser
from langchain_community.document_loaders.blob_loaders import Blob

from codx.junior.settings import CODXJuniorSettings

# from codx.junior.browser.browseruse import BrowserUse

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from llama_index.core.node_parser import CodeSplitter
from codx.junior.knowledge.settings import (
    LANGUAGE_FROM_EXTENSION,
    CODE_PARSER_FROM_EXTENSION
)

from codx.junior.utils import exec_command

CURRENT_SPLITTER_LANGUAGES = [lang.lower() for lang in dir(Language)]
LANGUAGE_PARSER_MAPPING = {
    "ts": "js"
}

logger = logging.getLogger(__name__)

class KnowledgeCodeSplitter:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.embeddings_ai_settings = self.settings.get_embeddings_settings()
        chunk_size = self.embeddings_ai_settings.chunk_size or 1000
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=10)

    def load(self, file_path):
        docs = self.file_to_documents(file_path=file_path)
        if docs:
            total_docs = len(docs)
            for ix, doc in enumerate(docs):
              doc.metadata["index"] = ix
              doc.metadata["total_docs"] = total_docs
              doc.metadata["length"] = len(doc.page_content)
        return docs

    def file_to_documents(self, file_path):
        suffix = file_path.split(".")[-1] if "." in file_path else "txt"
        language = LANGUAGE_FROM_EXTENSION.get(suffix, suffix) or suffix
        code_parser_language = CODE_PARSER_FROM_EXTENSION.get(suffix, language) or language 
        try:
            return self.load_with_code_plitter(file_path=file_path, code_parser_language=code_parser_language)
        except Exception as ex:
            #logger.error(f"[KnowledgeCodeSplitter] load_with_code_plitter load error: {ex} - {file_path} language: {code_parser_language}")
            pass

        try:
            return self.load_with_language_parser(file_path=file_path, code_parser_language=code_parser_language)
        except Exception as ex:
            #logger.error(f"[KnowledgeCodeSplitter] load_with_language_parser load error: {ex} - {file_path}")
            pass
          
        try:
            return self.load_as_text(file_path=file_path)
        except Exception as ex:
            #logger.error(f"[KnowledgeCodeSplitter] load_as_text load error: {ex} - {file_path}")
            pass

        logger.exception(f"[KnowledgeCodeSplitter] !!!No valid code splitter found for file {file_path}") 
        return None
    
    def load_with_browser(self, file_path):
        browser = Browser(settings=self.settings)
        

    def load_with_code_plitter(self, file_path, code_parser_language):
        code_parser = CodeSplitter(
            language=code_parser_language,
            # chunk_lines: int = DEFAULT_CHUNK_LINES,
            # chunk_lines_overlap: int = DEFAULT_LINES_OVERLAP,
            max_chars=self.embeddings_ai_settings.chunk_size
            # parser: Any = None,
            # callback_manager: Optional[CallbackManager] = None,
            # include_metadata: bool = True,
            # include_prev_next_rel: bool = True,
            # id_func: Optional[Callable[[int, Document], str]] = None,
        )
        def build_document(page_content):
            metadata = {
                "source": file_path,
                "language": language,
                "code_parser_language": code_parser_language,
                "parser": "CodeSplitter",
                "loader_type": "code",
                "splitter": "CodeSplitter"
            }    
            return Document(page_content=page_content, metadata=metadata)

        with open(file_path, mode='r', encoding='utf-8') as file:
            blocks = code_parser.split_text(file.read())
            return [build_document(block) for block in blocks]

    def load_with_language_parser(self, file_path, code_parser_language):
        language_parser = LanguageParser(language=code_parser_language, chucnk_size=self.embeddings_ai_settings.chunk_size)
        with open(file_path, mode='r', encoding='utf-8') as file:
            blob = Blob(data=file.read(), encoding='utf-8', metadata={ 
                "source": file_path,
                "language": code_parser_language,
                "parser": "LanguageParser"
            })
            docs = language_parser.parse(blob)
            for doc in docs: # Dirty hack for json
                doc.metadata["language"] = doc.metadata.get("language") or code_parser_language or suffix
                doc.metadata["loader_type"] = "code"
                doc.metadata["splitter"] = "LanguageParser"
            return docs

    def load_as_text(self, file_path):
      docs = TextLoader(file_path).load_and_split(
                    text_splitter=self.text_splitter)
      for doc in docs:
          doc.metadata["language"] = "txt"
          doc.metadata["loader_type"] = "text"
          doc.metadata["splitter"] = "TextLoader"
      return docs
      