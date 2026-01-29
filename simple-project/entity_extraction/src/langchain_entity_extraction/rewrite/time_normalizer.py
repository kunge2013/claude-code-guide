"""Time normalization utilities for question rewriting."""

import re
from datetime import datetime, date
from typing import Optional, Dict, Any

from langchain_entity_extraction.utils.logger import get_logger

logger = get_logger(__name__)


class TimeNormalizer:
    """
    Time normalization utility for converting relative time expressions
    to absolute time expressions.
    """

    # Regex patterns for time expressions
    PATTERNS = {
        "this_year": re.compile(r"今年|本年"),
        "last_year": re.compile(r"去年|上年"),
        "this_month": re.compile(r"本月|这个月|这月"),
        "last_month": re.compile(r"上月|上个月|上月"),
        "this_quarter": re.compile(r"本季度|这个季度"),
        "last_quarter": re.compile(r"上季度|上个季度"),
        "recent_days": re.compile(r"最近(\d+)天|近(\d+)天"),
        "this_week": re.compile(r"本周|这周"),
        "last_week": re.compile(r"上周|上周"),
    }

    def __init__(self, reference_date: Optional[date] = None):
        """
        Initialize the time normalizer.

        Args:
            reference_date: Reference date for normalization (defaults to today)
        """
        self.reference_date = reference_date or date.today()
        self.current_year = self.reference_date.year
        self.current_month = self.reference_date.month
        self.current_quarter = (self.current_month - 1) // 3 + 1

        logger.debug(
            f"TimeNormalizer initialized",
            reference_date=str(self.reference_date),
            current_year=self.current_year,
            current_quarter=self.current_quarter
        )

    def normalize(self, time_expr: str) -> str:
        """
        Normalize a relative time expression to absolute time.

        Args:
            time_expr: Time expression to normalize (e.g., "今年", "上月")

        Returns:
            Normalized time expression (e.g., "2026年", "2025年12月")

        Examples:
            >>> normalizer = TimeNormalizer(date(2026, 1, 15))
            >>> normalizer.normalize("今年")
            "2026年"
            >>> normalizer.normalize("上月")
            "2025年12月"
        """
        # Try each pattern
        if self.PATTERNS["this_year"].search(time_expr):
            return f"{self.current_year}年"

        if self.PATTERNS["last_year"].search(time_expr):
            return f"{self.current_year - 1}年"

        if self.PATTERNS["this_month"].search(time_expr):
            return f"{self.current_year}年{self.current_month}月"

        if self.PATTERNS["last_month"].search(time_expr):
            return self._get_last_month()

        if self.PATTERNS["this_quarter"].search(time_expr):
            return f"{self.current_year}年Q{self.current_quarter}"

        if self.PATTERNS["last_quarter"].search(time_expr):
            return self._get_last_quarter()

        if self.PATTERNS["this_week"].search(time_expr):
            return f"{self.current_year}年第{self._get_week_number()}周"

        if self.PATTERNS["last_week"].search(time_expr):
            return f"{self.current_year}年第{self._get_week_number() - 1}周"

        # Check for "recent N days"
        match = self.PATTERNS["recent_days"].search(time_expr)
        if match:
            days = int(match.group(1) or match.group(2))
            return self._get_recent_days_range(days)

        # If no pattern matches, return original
        logger.debug(f"No time pattern matched for: {time_expr}")
        return time_expr

    def extract_time_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract and normalize time expressions from text.

        Args:
            text: Text to extract time from

        Returns:
            Dictionary with extracted time information

        Examples:
            >>> normalizer = TimeNormalizer(date(2026, 1, 15))
            >>> normalizer.extract_time_from_text("今年cdn产品金额")
            {"original": "今年", "normalized": "2026年", "type": "year"}
        """
        result = {
            "found": False,
            "original": None,
            "normalized": None,
            "type": None
        }

        for pattern_name, pattern in self.PATTERNS.items():
            match = pattern.search(text)
            if match:
                time_type = pattern_name.replace("_", "")
                original = match.group(0)
                normalized = self.normalize(original)

                result.update({
                    "found": True,
                    "original": original,
                    "normalized": normalized,
                    "type": time_type
                })
                break

        return result

    def _get_last_month(self) -> str:
        """Get last month as 'YYYY年M月' format."""
        if self.current_month == 1:
            year = self.current_year - 1
            month = 12
        else:
            year = self.current_year
            month = self.current_month - 1
        return f"{year}年{month}月"

    def _get_last_quarter(self) -> str:
        """Get last quarter as 'YYYY年QN' format."""
        if self.current_quarter == 1:
            year = self.current_year - 1
            quarter = 4
        else:
            year = self.current_year
            quarter = self.current_quarter - 1
        return f"{year}年Q{quarter}"

    def _get_week_number(self) -> int:
        """Get current week number (1-52)."""
        return self.reference_date.isocalendar()[1]

    def _get_recent_days_range(self, days: int) -> str:
        """Get date range for recent N days."""
        from datetime import timedelta
        end_date = self.reference_date
        start_date = end_date - timedelta(days=days - 1)

        return f"{start_date.strftime('%Y-%m-%d')}至{end_date.strftime('%Y-%m-%d')}"

    def get_current_date_info(self) -> Dict[str, Any]:
        """
        Get current date information for prompts.

        Returns:
            Dictionary with current date information
        """
        return {
            "date": str(self.reference_date),
            "year": self.current_year,
            "month": self.current_month,
            "quarter": self.current_quarter,
            "week": self._get_week_number()
        }
