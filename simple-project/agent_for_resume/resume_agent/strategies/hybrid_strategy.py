"""
Hybrid search strategy combining fuzzy and vector search.

This strategy merges results from both fuzzy matching and vector search,
applying weighted scoring to provide the best results.
"""
from typing import Dict, List

from .base import SearchStrategy, SearchResult, MatchResult
from .fuzzy_strategy import FuzzySearchStrategy
from .vector_strategy import VectorSearchStrategy


class HybridSearchStrategy(SearchStrategy):
    """
    Hybrid search strategy combining fuzzy and vector search.

    Executes both search strategies and merges results with weighted scoring
    to provide the most accurate results.
    """

    def __init__(self, config):
        """
        Initialize hybrid search strategy.

        Args:
            config: Config object with hybrid search weights
        """
        self.config = config
        self._fuzzy_strategy: FuzzySearchStrategy = None
        self._vector_strategy: VectorSearchStrategy = None

    @property
    def fuzzy_strategy(self) -> FuzzySearchStrategy:
        """Lazy load fuzzy strategy."""
        if self._fuzzy_strategy is None:
            self._fuzzy_strategy = FuzzySearchStrategy(self.config)
        return self._fuzzy_strategy

    @property
    def vector_strategy(self) -> VectorSearchStrategy:
        """Lazy load vector strategy."""
        if self._vector_strategy is None:
            self._vector_strategy = VectorSearchStrategy(self.config)
        return self._vector_strategy

    def search(self, query: str) -> SearchResult:
        """
        Search for templates using hybrid approach.

        Args:
            query: Search query string

        Returns:
            SearchResult with merged matches from both strategies
        """
        # Execute both searches
        fuzzy_result = self.fuzzy_strategy.search(query)
        vector_result = self.vector_strategy.search(query)

        # Merge results
        merged_matches = self._merge_results(
            fuzzy_result.matches,
            vector_result.matches
        )

        return SearchResult(
            strategy_type="hybrid",
            matches=merged_matches,
            query=query
        )

    def _merge_results(
        self,
        fuzzy_matches: List[MatchResult],
        vector_matches: List[MatchResult]
    ) -> List[MatchResult]:
        """
        Merge results from both strategies with weighted scoring.

        Args:
            fuzzy_matches: Results from fuzzy search
            vector_matches: Results from vector search

        Returns:
            Merged and sorted list of MatchResult
        """
        # Use dictionary to deduplicate by template name
        merged: Dict[str, Dict] = {}

        # Process fuzzy matches
        for match in fuzzy_matches:
            if match.match_type == "suggestion":
                # Skip suggestions in hybrid mode (only use real matches)
                continue

            # Apply fuzzy weight
            weighted_score = match.score * self.config.HYBRID_WEIGHT_FUZZY

            merged[match.template_name] = {
                "match": match,
                "score": weighted_score,
                "has_fuzzy": True,
                "has_vector": False
            }

        # Process vector matches
        for match in vector_matches:
            if match.match_type == "suggestion":
                continue

            weighted_score = match.score * self.config.HYBRID_WEIGHT_VECTOR

            if match.template_name in merged:
                # Already exists - combine scores
                existing = merged[match.template_name]
                existing["score"] += weighted_score
                existing["has_vector"] = True

                # Update match to have vector data (prefer vector link)
                if match.download_link:
                    existing["match"].download_link = match.download_link
            else:
                # New entry
                merged[match.template_name] = {
                    "match": match,
                    "score": weighted_score,
                    "has_fuzzy": False,
                    "has_vector": True
                }

        # Sort by combined score
        sorted_results = sorted(
            merged.values(),
            key=lambda x: x["score"],
            reverse=True
        )

        # Return list of matches with updated scores
        result = []
        for item in sorted_results:
            match = item["match"]
            # Update the score to the combined weighted score
            match.score = min(item["score"], 1.0)  # Cap at 1.0
            # Update match_type to reflect hybrid
            if item["has_fuzzy"] and item["has_vector"]:
                match.match_type = "hybrid_both"
            elif item["has_vector"]:
                match.match_type = "hybrid_vector"
            else:
                match.match_type = "hybrid_fuzzy"
            result.append(match)

        return result

    def get_strategy_name(self) -> str:
        """Get the strategy name."""
        return "hybrid"
