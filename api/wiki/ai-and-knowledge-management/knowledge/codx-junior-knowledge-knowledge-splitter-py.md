# Knowledge Splitter

The `KnowledgeSplitter` class is designed to facilitate the process of **code splitting** for knowledge enrichment. It leverages the `RecursiveCharacterTextSplitter` from the `langchain_text_splitters` library to divide documents into manageable chunks.

## Initialization

The class can be initialized directly or through a class method:

### `__init__(self, language, chunk_size, chunk_overlap)`

This is the constructor for the `KnowledgeSplitter` class. It takes the following parameters:
* `language`: Specifies the programming language for splitting.
* `chunk_size`: Defines the maximum size of each chunk.
* `chunk_overlap`: Sets the number of characters that overlap between consecutive chunks.

### `from_language(cls, language, chunk_size, chunk_overlap)`

This class method provides an alternative way to instantiate `KnowledgeSplitter`. It takes the same parameters as the `__init__` method.

## Methods

### `split_documents(self, documents)`

This method performs the actual splitting of the provided documents.

1.  It initializes a `RecursiveCharacterTextSplitter` specifically configured for **Python** code, with a `chunk_size` of 2000 and a `chunk_overlap` of 200.
2.  It then uses this splitter to divide the input `documents` into smaller chunks.
3.  Finally, it returns a list of these generated chunks.

```python /codx/junior/knowledge/knowledge_splitter.py
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

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
```