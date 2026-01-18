"""
Strategy factory for creating search strategy instances.

This module provides a factory pattern implementation to instantiate
the appropriate search strategy based on configuration.
"""
from typing import Dict, Type, Optional

from .base import SearchStrategy
from .fuzzy_strategy import FuzzySearchStrategy
from .vector_strategy import VectorSearchStrategy
from .hybrid_strategy import HybridSearchStrategy


class StrategyFactory:
    """
    Factory for creating search strategy instances.

    Supported strategies:
    - fuzzy: Fuzzy string matching (default, no external dependencies)
    - vector: Vector-based semantic search using Milvus
    - hybrid: Combined fuzzy + vector search with result fusion
    """

    _strategies: Dict[str, Type[SearchStrategy]] = {
        "fuzzy": FuzzySearchStrategy,
        "vector": VectorSearchStrategy,
        "hybrid": HybridSearchStrategy,
    }

    @classmethod
    def create_strategy(
        cls,
        mode: str,
        config
    ) -> SearchStrategy:
        """
        Create a search strategy instance.

        Args:
            mode: The search mode ("fuzzy", "vector", or "hybrid")
            config: Config object with search configuration

        Returns:
            An instance of the requested SearchStrategy

        Raises:
            ValueError: If the mode is not supported
        """
        mode = mode.lower()
        strategy_class = cls._strategies.get(mode)

        if not strategy_class:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unsupported search mode: '{mode}'. "
                f"Available modes: {available}"
            )

        return strategy_class(config)

    @classmethod
    def get_available_modes(cls) -> list[str]:
        """Get list of available search modes."""
        return list(cls._strategies.keys())

    @classmethod
    def register_strategy(
        cls,
        mode: str,
        strategy_class: Type[SearchStrategy]
    ) -> None:
        """
        Register a custom search strategy.

        Args:
            mode: The mode name for this strategy
            strategy_class: The SearchStrategy class to register
        """
        cls._strategies[mode] = strategy_class
