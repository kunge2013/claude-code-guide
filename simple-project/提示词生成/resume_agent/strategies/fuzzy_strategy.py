"""
Fuzzy search strategy using string matching.

This strategy implements the original fuzzy matching approach
using thefuzz library for string similarity comparison.
"""
import pandas as pd
from typing import Optional

try:
    from thefuzz import fuzz
except ImportError:
    fuzz = None

from .base import SearchStrategy, SearchResult, MatchResult


class FuzzySearchStrategy(SearchStrategy):
    """
    Fuzzy string matching search strategy.

    Uses thefuzz library to find similar templates based on
    partial string matching and keyword detection.
    """

    def __init__(self, config):
        """
        Initialize fuzzy search strategy.

        Args:
            config: Config object
        """
        self.config = config
        self._knowledge_base: Optional[pd.DataFrame] = None

    def _load_knowledge_base(self) -> pd.DataFrame:
        """Load the Excel knowledge base file."""
        if self._knowledge_base is not None:
            return self._knowledge_base

        if not pd.io.common.file_exists(self.config.EXCEL_FILE_PATH):
            raise FileNotFoundError(
                f"Knowledge base file not found: {self.config.EXCEL_FILE_PATH}"
            )

        self._knowledge_base = pd.read_excel(self.config.EXCEL_FILE_PATH)
        return self._knowledge_base

    def search(self, query: str) -> SearchResult:
        """
        Search for templates using fuzzy matching.

        Args:
            query: Search query string

        Returns:
            SearchResult with matched templates
        """
        if fuzz is None:
            raise ImportError(
                "thefuzz is required for fuzzy search. "
                "Install it with: pip install thefuzz"
            )

        df = self._load_knowledge_base()
        all_templates = df['问题'].tolist()

        # Find best match
        best_match = None
        best_score = 0
        scores = []

        for template in all_templates:
            # Calculate similarity score
            score = fuzz.partial_ratio(query, template)

            # Bonus for exact keyword matches
            for keyword in query.split():
                if keyword in template:
                    score += 20

            scores.append((template, score))

            if score > best_score:
                best_score = score
                best_match = template

        # Threshold for matching (60% similarity)
        THRESHOLD = 60

        matches = []
        if best_match and best_score >= THRESHOLD:
            # Find the corresponding download link
            result_row = df[df['问题'] == best_match].iloc[0]
            download_link = result_row['答案']

            # Normalize score to 0-1
            normalized_score = self._normalize_score(best_score)

            matches.append(MatchResult(
                template_name=best_match,
                download_link=download_link,
                score=normalized_score,
                match_type="fuzzy"
            ))
        else:
            # No good match - include all available templates as suggestions
            for template in all_templates:
                matches.append(MatchResult(
                    template_name=template,
                    download_link="",  # No link for suggestions
                    score=0.0,
                    match_type="suggestion"
                ))

        return SearchResult(
            strategy_type="fuzzy",
            matches=matches,
            query=query
        )

    def get_strategy_name(self) -> str:
        """Get the strategy name."""
        return "fuzzy"
