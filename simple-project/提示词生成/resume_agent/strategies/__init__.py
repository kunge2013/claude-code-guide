"""
Search strategies for resume template retrieval.

This module implements the Strategy Pattern to support multiple search methods:
- fuzzy: Fuzzy string matching (existing implementation)
- vector: Vector-based semantic search using Milvus
- hybrid: Combined fuzzy + vector search with result fusion
"""

from .base import SearchStrategy, MatchResult, SearchResult
from .fuzzy_strategy import FuzzySearchStrategy
from .vector_strategy import VectorSearchStrategy
from .hybrid_strategy import HybridSearchStrategy
from .factory import StrategyFactory

__all__ = [
    "SearchStrategy",
    "MatchResult",
    "SearchResult",
    "FuzzySearchStrategy",
    "VectorSearchStrategy",
    "HybridSearchStrategy",
    "StrategyFactory",
]
