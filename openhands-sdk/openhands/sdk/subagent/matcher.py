"""Vector similarity matcher for task-agent matching."""

from __future__ import annotations

from typing import Any

import numpy as np


class VectorMatcher:
    """Vector-based similarity matcher for task-agent matching.

    This matcher computes similarity between task descriptions and agent
    capability profiles using vector embeddings.
    """

    def __init__(self) -> None:
        """Initialize the vector matcher."""
        self._dimension = 128

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding vector for text.

        This is a simplified implementation. In production, this should
        use a proper embedding model (e.g., sentence-transformers).

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        text_hash = hash(text.lower().strip())
        np.random.seed(abs(text_hash) % (2**32))
        return np.random.randn(self._dimension)

    def compute_similarity(
        self,
        query_vector: np.ndarray,
        candidate_vectors: list[np.ndarray],
    ) -> list[float]:
        """Compute cosine similarity between query and candidates.

        Args:
            query_vector: Query embedding vector
            candidate_vectors: List of candidate embedding vectors

        Returns:
            List of similarity scores
        """
        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0:
            return [0.0] * len(candidate_vectors)

        similarities = []
        for candidate in candidate_vectors:
            candidate_norm = np.linalg.norm(candidate)
            if candidate_norm == 0:
                similarities.append(0.0)
            else:
                sim = np.dot(query_vector, candidate) / (query_norm * candidate_norm)
                similarities.append(float(sim))

        return similarities

    def rank_by_similarity(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        text_field: str = "description",
    ) -> list[tuple[int, float]]:
        """Rank candidates by similarity to query.

        Args:
            query: Query text
            candidates: List of candidate dictionaries
            text_field: Field name containing candidate text

        Returns:
            List of (index, score) tuples sorted by similarity
        """
        query_vector = self.embed_text(query)

        candidate_vectors = []
        for candidate in candidates:
            text = candidate.get(text_field, "")
            candidate_vectors.append(self.embed_text(text))

        similarities = self.compute_similarity(query_vector, candidate_vectors)

        ranked = sorted(
            enumerate(similarities),
            key=lambda x: x[1],
            reverse=True,
        )

        return ranked


def create_matcher() -> VectorMatcher:
    """Factory function to create a VectorMatcher.

    Returns:
        A VectorMatcher instance
    """
    return VectorMatcher()
