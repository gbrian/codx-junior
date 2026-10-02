"""
In-memory embeddings model for local embedding generation.

This module provides a lightweight, self-contained embeddings solution
that doesn't depend on external AI services.
"""

import logging
from typing import List, Union, Any

logger = logging.getLogger(__name__)


class LocalEmbeddingsModel:
    """
    Wrapper around sentence-transformers for local, in-memory embeddings.
    
    Uses a lightweight model by default (all-MiniLM-L6-v2) which provides
    a good balance between speed and quality for semantic search.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the local embeddings model.

        Args:
            model_name: HuggingFace model identifier.
                       Defaults to all-MiniLM-L6-v2 (384 dims, ~22MB).
        """
        self.model_name = model_name
        self._model = None
        self._embedding_dim = None

    @property
    def model(self):
        """Lazy-load the embeddings model on first access."""
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self) -> None:
        """
        Load the sentence-transformer model.
        
        Raises:
            ImportError: If sentence-transformers is not installed.
            Exception: If model download/loading fails.
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for local embeddings. "
                "Install it with: pip install sentence-transformers"
            ) from e

        try:
            logger.info("Loading embeddings model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            self._embedding_dim = self._model.get_sentence_embedding_dimension()
            logger.info(
                "Embeddings model loaded successfully. "
                "Embedding dimension: %d",
                self._embedding_dim,
            )
        except Exception as e:
            logger.error(
                "Failed to load embeddings model '%s': %s",
                self.model_name,
                e,
            )
            raise

    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single query string.

        Args:
            text: Text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        if not text or not isinstance(text, str):
            logger.warning("Invalid input for embed_query: %s", text)
            return [0.0] * self.embedding_dim

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error("Error embedding query: %s", e)
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (List[List[float]]).
        """
        if not texts or not all(isinstance(t, str) for t in texts):
            logger.warning("Invalid input for embed_documents: %s", texts)
            return [[0.0] * self.embedding_dim for _ in texts]

        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error("Error embedding documents: %s", e)
            raise

    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension."""
        if self._embedding_dim is None:
            _ = self.model  # Trigger lazy load
        return self._embedding_dim


class HybridEmbeddingsModel:
    """
    Hybrid embeddings that falls back to local model when AI service is unavailable.
    
    Attempts to use the configured AI embeddings first, then falls back to
    the local sentence-transformer model if needed.
    """

    def __init__(self, ai_embeddings: Any = None, local_model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize hybrid embeddings.

        Args:
            ai_embeddings: Optional AI embeddings callable (from OpenAI_AI.embeddings()).
            local_model_name: Fallback local model name.
        """
        self.ai_embeddings = ai_embeddings
        self.local_model = LocalEmbeddingsModel(model_name=local_model_name)
        self._use_local = ai_embeddings is None

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query, with fallback to local model."""
        if self._use_local:
            return self.local_model.embed_query(text)

        try:
            if hasattr(self.ai_embeddings, "embed_query"):
                return self.ai_embeddings.embed_query(text)
            # Fallback for AI models that only expose embed_documents
            return self.ai_embeddings.embed_documents([text])[0]
        except Exception as e:
            logger.warning(
                "AI embeddings failed, falling back to local model: %s",
                e,
            )
            self._use_local = True
            return self.local_model.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents, with fallback to local model."""
        if self._use_local:
            return self.local_model.embed_documents(texts)

        try:
            if hasattr(self.ai_embeddings, "embed_documents"):
                return self.ai_embeddings.embed_documents(texts)
            # Fallback for AI models that only expose embed_query
            return [self.ai_embeddings.embed_query(text) for text in texts]
        except Exception as e:
            logger.warning(
                "AI embeddings failed, falling back to local model: %s",
                e,
            )
            self._use_local = True
            return self.local_model.embed_documents(texts)

# Made with ❤️ by codx-junior