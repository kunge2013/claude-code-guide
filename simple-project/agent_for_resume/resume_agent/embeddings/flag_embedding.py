"""
FlagEmbedding service for generating text embeddings.

Uses FlagEmbedding library (BAAI/bge models) optimized for Chinese text.
"""
import os
import pickle
from hashlib import md5
from pathlib import Path
from typing import List, Optional

import numpy as np


class FlagEmbeddingService:
    """
    Embedding service using FlagEmbedding (BAAI/bge models).

    This service provides text-to-vector conversion for semantic search.
    Includes caching to avoid re-computing embeddings for the same text.

    Features:
    - Chinese optimized (BAAI/bge-small-zh-v1.5)
    - Query-aware encoding (different encoding for queries vs documents)
    - Disk-based caching for faster repeated lookups
    - CPU/GPU support
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        device: str = "cpu",
        cache_dir: Optional[str] = None,
        enable_cache: bool = True
    ):
        """
        Initialize the FlagEmbedding service.

        Args:
            model_name: HuggingFace model name
            device: Device to run on ("cpu" or "cuda")
            cache_dir: Directory for embedding cache
            enable_cache: Whether to enable disk caching
        """
        self.model_name = model_name
        self.device = device
        self.enable_cache = enable_cache

        # Setup cache directory
        if cache_dir and enable_cache:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None

        # Lazy load the model
        self._model = None

    @property
    def model(self):
        """Lazy load the FlagEmbedding model."""
        if self._model is None:
            try:
                from FlagEmbedding import FlagModel
            except ImportError:
                raise ImportError(
                    "FlagEmbedding is required for vector search. "
                    "Install it with: pip install FlagEmbedding"
                )

            self._model = FlagModel(
                self.model_name,
                query_instruction_for_retrieval="为这个句子生成表示以用于检索相关文章：",
                device=self.device
            )
        return self._model

    def encode(self, texts: List[str]) -> np.ndarray:
        """
        Encode a list of texts as document embeddings.

        Args:
            texts: List of text strings to encode

        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])

        embeddings = self.model.encode(texts)
        return embeddings

    def encode_queries(self, queries: List[str]) -> np.ndarray:
        """
        Encode queries with query-specific instruction.

        Queries are encoded differently from documents for better retrieval.

        Args:
            queries: List of query strings

        Returns:
            numpy array of shape (len(queries), embedding_dim)
        """
        if not queries:
            return np.array([])

        embeddings = self.model.encode_queries(queries)
        return embeddings

    def encode_query(self, query: str) -> np.ndarray:
        """
        Encode a single query.

        Args:
            query: Query string

        Returns:
            numpy array of shape (embedding_dim,)
        """
        result = self.encode_queries([query])
        return result[0] if len(result) > 0 else np.array([])

    def get_cached(self, text: str) -> Optional[np.ndarray]:
        """
        Get cached embedding for a text.

        Args:
            text: Text to look up

        Returns:
            Cached embedding if found, None otherwise
        """
        if not self.enable_cache or not self.cache_dir:
            return None

        cache_key = md5(text.encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                return None

        return None

    def set_cached(self, text: str, embedding: np.ndarray) -> None:
        """
        Cache an embedding for a text.

        Args:
            text: Text string
            embedding: Embedding vector to cache
        """
        if not self.enable_cache or not self.cache_dir:
            return

        cache_key = md5(text.encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(embedding, f)
        except Exception:
            pass  # Silently fail on cache write errors

    def encode_with_cache(self, texts: List[str], use_cache: bool = True) -> np.ndarray:
        """
        Encode texts with caching support.

        Args:
            texts: List of texts to encode
            use_cache: Whether to use cache

        Returns:
            numpy array of embeddings
        """
        if not use_cache or not self.enable_cache:
            return self.encode(texts)

        embeddings = []
        uncached_texts = []
        uncached_indices = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cached = self.get_cached(text)
            if cached is not None:
                embeddings.append((i, cached))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Encode uncached texts
        if uncached_texts:
            new_embeddings = self.encode(uncached_texts)
            for idx, text, emb in zip(uncached_indices, uncached_texts, new_embeddings):
                embeddings.append((idx, emb))
                self.set_cached(text, emb)

        # Sort by original index and return
        embeddings.sort(key=lambda x: x[0])
        return np.array([e[1] for e in embeddings])

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        # Test encode to get dimension
        test_emb = self.encode(["test"])
        return test_emb.shape[1] if len(test_emb) > 0 else 0
