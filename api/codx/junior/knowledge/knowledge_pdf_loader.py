import logging
from typing import List
import fitz  # PyMuPDF
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class KnowledgePDFLoader:
    """
    Loads and extracts text from PDF files using PyMuPDF (fitz).
    Handles multi-page PDFs and maintains metadata for each chunk.
    """

    def __init__(self, settings=None):
        """Initialize PDF loader with optional settings for chunk size."""
        self.settings = settings
        self.chunk_size = None
        if settings:
            embeddings_settings = settings.get_embeddings_settings()
            self.chunk_size = embeddings_settings.chunk_size or 65535

    def load(self, file_path: str) -> List[Document]:
        """
        Load a PDF file and extract text as documents.

        Args:
            file_path: Path to the PDF file.

        Returns:
            List of Document objects with extracted text.
        """
        try:
            return self._extract_pdf(file_path)
        except Exception as ex:
            logger.error(f"[KnowledgePDFLoader] Error loading PDF '{file_path}': {ex}")
            return []

    def _extract_pdf(self, file_path: str) -> List[Document]:
        """
        Internal method to extract text from PDF.

        Args:
            file_path: Path to the PDF file.

        Returns:
            List of Document objects.
        """
        documents = []

        try:
            pdf_doc = fitz.open(file_path)
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                text = page.get_text()

                if not text.strip():
                    logger.debug(f"[KnowledgePDFLoader] Page {page_num + 1} is empty: {file_path}")
                    continue

                metadata = {
                    "source": file_path,
                    "page": page_num + 1,
                    "total_pages": len(pdf_doc),
                    "language": "pdf",
                    "loader_type": "pdf",
                    "splitter": "PyMuPDF",
                    "parser": "PyMuPDF"
                }

                doc = Document(page_content=text, metadata=metadata)
                documents.append(doc)

            pdf_doc.close()
            logger.info(f"[KnowledgePDFLoader] Extracted {len(documents)} pages from '{file_path}'")

        except Exception as ex:
            logger.error(f"[KnowledgePDFLoader] Failed to process PDF '{file_path}': {ex}")
            raise

        return documents