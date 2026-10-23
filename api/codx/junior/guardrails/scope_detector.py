"""Local embedding-based scope relevance detector.

Uses the same in-process sentence-transformers model already used by the
knowledge subsystem to embed both the profile's scope description and the
incoming user text, then compares them with cosine similarity. This is the
cheap "is this question on-topic" layer that needs no fine-tuned model.
"""
import logging
import math
from typing import List, Optional

from codx.junior.knowledge.embeddings import LocalEmbeddingsModel

logger = logging.getLogger(__name__)

_EMBEDDINGS: Optional[LocalEmbeddingsModel] = None


def _get_embeddings() -> LocalEmbeddingsModel:
    """Return (lazily creating) the module-level embeddings singleton."""
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        _EMBEDDINGS = LocalEmbeddingsModel(model_name="all-MiniLM-L6-v2")
    return _EMBEDDINGS


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two equal-length vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def embedding_similarity(scope_text: str, text: str) -> float:
    """Return cosine similarity between *scope_text* and *text*."""
    model = _get_embeddings()
    scope_vector = model.embed_query(scope_text)
    text_vector = model.embed_query(text or "")
    return _cosine_similarity(scope_vector, text_vector)