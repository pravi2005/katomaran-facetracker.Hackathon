"""In-memory gallery of registered embeddings + cosine-similarity search.

Metric
------
Embeddings are L2-normalised, so ``cosine_similarity(a, b) == dot(a, b)``.
Range [-1, 1]; higher = more similar. A match requires
``similarity >= similarity_threshold`` (configured in config.json).

The threshold is only a starting point: it depends on the model, camera,
resolution and lighting and must be calibrated on your own video
(see scripts/calibrate_threshold.py and docs/PERFORMANCE.md).

* too LOW  -> false matches   (two people share one Face ID, count too low)
* too HIGH -> false non-matches (one person gets several IDs, count too high)
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from app.errors import RecognitionError


def normalize(vector: np.ndarray) -> np.ndarray:
    """Return a float32 unit-length copy; raise on NaN/inf/zero vectors."""
    flat = np.asarray(vector, dtype=np.float32).reshape(-1)
    if not np.all(np.isfinite(flat)):
        raise RecognitionError("Embedding contains NaN or infinite values.")
    norm = float(np.linalg.norm(flat))
    if norm < 1e-8:
        raise RecognitionError("Embedding has zero length.")
    return flat / norm


class FaceMatcher:
    def __init__(self) -> None:
        self._ids: List[str] = []
        self._matrix: Optional[np.ndarray] = None  # shape (N, dim)

    @property
    def size(self) -> int:
        return len(self._ids)

    @property
    def dimension(self) -> Optional[int]:
        return None if self._matrix is None else int(self._matrix.shape[1])

    def add(self, face_id: str, embedding: np.ndarray) -> None:
        vector = normalize(embedding)
        if self._matrix is None:
            self._matrix = vector[None, :]
        else:
            if vector.shape[0] != self._matrix.shape[1]:
                raise RecognitionError(
                    f"Embedding dimension {vector.shape[0]} != gallery dimension {self._matrix.shape[1]}.")
            self._matrix = np.vstack([self._matrix, vector])
        self._ids.append(face_id)

    def best_match(self, embedding: np.ndarray) -> Tuple[Optional[str], float]:
        """Return (face_id, similarity) of the closest face, or (None, -1.0) if empty."""
        if self._matrix is None:
            return None, -1.0
        vector = normalize(embedding)
        if vector.shape[0] != self._matrix.shape[1]:
            raise RecognitionError(
                f"Embedding dimension {vector.shape[0]} != gallery dimension {self._matrix.shape[1]}.")
        similarities = self._matrix @ vector
        index = int(np.argmax(similarities))
        return self._ids[index], float(similarities[index])
