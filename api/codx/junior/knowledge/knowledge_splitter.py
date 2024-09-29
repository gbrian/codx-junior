import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter, Language

logger = logging.getLogger(__name__)


class KnowledgeSplitter:
    def __init__(self, language, chunk_size, chunk_overlap):
        logger.debug('Initializing KnowledgeSplitter')
        self.language = language
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.debug('KnowledgeSplitter initialized')

    @classmethod
    def from_language(cls, language, chunk_size, chunk_overlap):
        return cls(language, chunk_size, chunk_overlap)

    def split_documents(self, documents):
        logger.debug('Splitting documents')
        python_splitter = RecursiveCharacterTextSplitter.from_language(
          language=Language.PYTHON, chunk_size=2000, chunk_overlap=200
        )
        chunks = python_splitter.split_documents(documents)
        logger.debug(f'Split into {len(chunks)} chunks')
        return chunks