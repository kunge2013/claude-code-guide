"""
Base classes for search strategies.

Defines the abstract interface and data structures for all search strategies.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MatchResult:
    """Represents a single match result from a search query."""
    template_name: str
    download_link: str
    score: float
    match_type: str = ""  # e.g., "fuzzy", "vector"

    def __post_init__(self):
        """Normalize score to 0-1 range."""
        if self.score > 1:
            self.score = self.score / 100


@dataclass
class SearchResult:
    """Represents the complete result of a search query."""
    strategy_type: str
    matches: List[MatchResult]
    query: str
    total_results: int = field(init=False)

    def __post_init__(self):
        """Calculate total results."""
        self.total_results = len(self.matches)

    def get_best_match(self) -> Optional[MatchResult]:
        """Get the best matching result."""
        if not self.matches:
            return None
        return max(self.matches, key=lambda x: x.score)

    def get_matches_above_threshold(self, threshold: float) -> List[MatchResult]:
        """Get matches with score above threshold."""
        return [m for m in self.matches if m.score >= threshold]


class SearchStrategy(ABC):
    """
    Abstract base class for search strategies.

    All search strategies must implement the search method.
    """

    @abstractmethod
    def search(self, query: str) -> SearchResult:
        """
        Execute a search query.

        Args:
            query: The search query string

        Returns:
            SearchResult containing matched templates
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        pass

    def _normalize_score(self, score: float, max_score: float = 100) -> float:
        """Normalize score to 0-1 range."""
        return min(score / max_score, 1.0)
