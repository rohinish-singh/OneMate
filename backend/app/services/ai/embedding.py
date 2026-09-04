"""
Semantic Embedding Service for OneMate AI.

Manages sentence-transformer embedding model lifecycle, singleton loading,
vector normalization, and fallback execution.
"""

from __future__ import annotations

import hashlib
import logging
import math
import threading
from typing import List, Optional, Protocol, runtime_checkable

from app.core.config import settings

logger = logging.getLogger(__name__)


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Computes exact cosine similarity between two float vectors.
    Handles zero-magnitude and unequal-length vectors safely.
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    sim = dot / (norm_a * norm_b)
    # Clamp to [-1.0, 1.0] to guard against floating-point precision anomalies
    return max(-1.0, min(1.0, round(sim, 6)))


@runtime_checkable
class EmbeddingModel(Protocol):
    """Abstract interface for dense vector embedding models."""

    @property
    def model_name(self) -> str:
        ...

    @property
    def dimension(self) -> int:
        ...

    def encode(self, texts: List[str]) -> List[List[float]]:
        ...


class DeterministicFallbackEmbeddingModel:
    """
    Deterministic pseudo-semantic embedding generator for offline testing
    and environments where sentence-transformers/PyTorch is not available.

    Generates reproducible 384-dimensional unit vectors based on character
    n-grams, token bags, and hashing. Ensures deterministic unit length (||v|| = 1.0).
    """

    def __init__(self, dimension: int = 384) -> None:
        self._dim = dimension
        self._name = "deterministic-fallback-v1"

    @property
    def model_name(self) -> str:
        return self._name

    @property
    def dimension(self) -> int:
        return self._dim

    def encode(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = []
        for text in texts:
            vec = [0.0] * self._dim
            if not text or not text.strip():
                # Zero-magnitude unit vector along first dimension
                vec[0] = 1.0
                results.append(vec)
                continue

            cleaned = text.strip().upper()
            tokens = cleaned.split()

            # Hash token components into vector dimensions
            for i, token in enumerate(tokens):
                token_hash = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
                idx = token_hash % self._dim
                # Add weighted magnitude based on position and character length
                vec[idx] += 1.0 + (len(token) * 0.1)

                # Add bi-gram context
                if i > 0:
                    bigram = f"{tokens[i-1]}_{token}"
                    bi_hash = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16)
                    vec[bi_hash % self._dim] += 1.5

            # Normalize to unit length
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0.0:
                normalized = [round(v / norm, 6) for v in vec]
            else:
                normalized = [0.0] * self._dim
                normalized[0] = 1.0

            results.append(normalized)

        return results


class SentenceTransformerEmbeddingModel:
    """
    Wraps sentence-transformers library for pre-trained all-MiniLM-L6-v2 inference.
    Executes in CPU mode with batch normalization.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu") -> None:
        self._model_name = model_name
        self._device = device
        self._dim = 384

        try:
            import os
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer model '{model_name}' on device '{device}'...")
            try:
                # Attempt to load from local cache first to avoid network hang in sandbox/offline mode
                self._model = SentenceTransformer(model_name, device=device, local_files_only=True)
            except Exception:
                if os.environ.get("HF_HUB_OFFLINE") == "1":
                    raise
                dim_fn = getattr(self._model, "get_embedding_dimension", getattr(self._model, "get_sentence_embedding_dimension", None))
                self._dim = dim_fn() if dim_fn else 384
        except Exception as e:
            logger.warning(f"Failed to load SentenceTransformer '{model_name}': {e}. Falling back to deterministic model.")
            raise

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dim

    def encode(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [[round(float(val), 6) for val in row] for row in embeddings]


class EmbeddingService:
    """
    Thread-safe singleton managing the active embedding model instance.
    Provides graceful degradation to the deterministic fallback model.
    """

    _instance: Optional[EmbeddingService] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._model: EmbeddingModel
        self._initialize_model()

    def _initialize_model(self) -> None:
        if not getattr(settings, "ai_enabled", True):
            logger.info("AI subsystem disabled by configuration. Using deterministic fallback embedding model.")
            self._model = DeterministicFallbackEmbeddingModel(dimension=settings.embedding_dimension)
            return

        model_name = getattr(settings, "embedding_model_name", "all-MiniLM-L6-v2")
        device = getattr(settings, "embedding_device", "cpu")

        try:
            self._model = SentenceTransformerEmbeddingModel(model_name=model_name, device=device)
            logger.info(f"Active embedding model initialized: {self._model.model_name} ({self._model.dimension}-d)")
        except Exception as e:
            logger.warning(f"SentenceTransformer unavailable ({e}). Activating DeterministicFallbackEmbeddingModel.")
            self._model = DeterministicFallbackEmbeddingModel(dimension=getattr(settings, "embedding_dimension", 384))

    @classmethod
    def get_instance(cls) -> EmbeddingService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """For testing: clears singleton state."""
        with cls._lock:
            cls._instance = None

    @property
    def model(self) -> EmbeddingModel:
        return self._model

    @property
    def model_name(self) -> str:
        return self._model.model_name

    @property
    def dimension(self) -> int:
        return self._model.dimension

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Encodes a batch of strings into normalized float vectors."""
        if not texts:
            return []
        return self._model.encode(texts)

    def encode_one(self, text: str) -> List[float]:
        """Encodes a single string into a normalized float vector."""
        res = self.encode([text])
        return res[0] if res else [0.0] * self.dimension
