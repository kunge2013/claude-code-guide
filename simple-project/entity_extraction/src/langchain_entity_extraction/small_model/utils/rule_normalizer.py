"""
Rule-based Entity Normalizer.

Normalizes entities extracted by the NER model into canonical forms.
Reuses existing TimeNormalizer and EntityMapper from the rewrite module.
"""

from datetime import date
from typing import Dict, List, Any, Optional


class RuleNormalizer:
    """
    Rule-based entity normalization engine.

    Normalizes time expressions, product names, and field names
    into canonical forms suitable for SQL generation.
    """

    # Product mappings
    PRODUCT_MAPPING = {
        "cdn": "cdn",
        "ecs": "ecs",
        "oss": "oss",
        "rds": "rds",
        "slb": "slb",
        "CDN": "cdn",
        "ECS": "ecs",
        "OSS": "oss",
        "RDS": "rds",
        "SLB": "slb",
    }

    # Field mappings
    FIELD_MAPPING = {
        "金额": "出账金额",
        "数量": "订单数量",
        "收入": "营业收入",
        "流量": "流量",
        "用户数": "用户数",
        "费用": "出账金额",
        "总额": "出账金额",
        "总金额": "出账金额",
    }

    # Time expressions mapping
    TIME_EXPRESSIONS = {
        "今年": None,  # Will be set dynamically
        "去年": None,
        "本月": None,
        "上月": None,
        "本季度": None,
        "上季度": None,
    }

    def __init__(self):
        """Initialize the normalizer with current date info."""
        self._init_time_mappings()

    def _init_time_mappings(self):
        """Initialize time mappings based on current date."""
        today = date.today()
        current_year = today.year
        current_month = today.month
        current_quarter = (today.month - 1) // 3 + 1

        # Set dynamic time mappings
        self.TIME_EXPRESSIONS.update({
            "今年": f"{current_year}年",
            "去年": f"{current_year - 1}年",
            "本月": f"{current_year}年{current_month}月",
            "上月": self._get_last_month_str(current_year, current_month),
            "本季度": f"{current_year}年Q{current_quarter}",
            "上季度": self._get_last_quarter_str(current_year, current_quarter),
        })

    @staticmethod
    def _get_last_month_str(year: int, month: int) -> str:
        """Get string representation of last month."""
        if month == 1:
            return f"{year - 1}年12月"
        else:
            return f"{year}年{month - 1}月"

    @staticmethod
    def _get_last_quarter_str(year: int, quarter: int) -> str:
        """Get string representation of last quarter."""
        if quarter == 1:
            return f"{year - 1}年Q4"
        else:
            return f"{year}年Q{quarter - 1}"

    def normalize_entities(
        self,
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Normalize a list of entities into canonical form.

        Args:
            entities: List of entity dicts with 'entity', 'label', 'start', 'end'

        Returns:
            Dict with normalized entity values:
                {
                    "product_id": "cdn",
                    "time": "2026年",
                    "field": "出账金额",
                    ...
                }
        """
        normalized = {}

        for entity in entities:
            entity_text = entity.get("entity", "")
            entity_label = entity.get("label", "")

            if entity_label == "PRODUCT":
                normalized["product_id"] = self.normalize_product(entity_text)
            elif entity_label == "TIME":
                normalized["time"] = self.normalize_time(entity_text)
            elif entity_label == "FIELD":
                normalized["field"] = self.normalize_field(entity_text)
            elif entity_label == "ORG":
                normalized["organization"] = entity_text
            elif entity_label == "PERSON":
                normalized["person"] = entity_text
            elif entity_label == "LOCATION":
                normalized["location"] = entity_text

        return normalized

    def normalize_time(self, time_expr: str) -> str:
        """
        Normalize time expression.

        Args:
            time_expr: Time expression like "今年", "2026年", "1月"

        Returns:
            Normalized time string

        Examples:
            >>> normalizer = RuleNormalizer()
            >>> normalizer.normalize_time("今年")
            "2026年"
            >>> normalizer.normalize_time("上月")
            "2025年12月"
        """
        # Direct mapping
        if time_expr in self.TIME_EXPRESSIONS:
            return self.TIME_EXPRESSIONS[time_expr]

        # Check for year pattern
        if "年" in time_expr:
            return time_expr

        # Check for month pattern
        if "月" in time_expr and "年" not in time_expr:
            current_year = date.today().year
            return f"{current_year}年{time_expr}"

        # Check for quarter pattern
        if "Q" in time_expr or "季度" in time_expr:
            current_year = date.today().year
            if "年" not in time_expr:
                return f"{current_year}年{time_expr}"
            return time_expr

        # Return original if no match
        return time_expr

    def normalize_product(self, product_name: str) -> str:
        """
        Normalize product name to lowercase ID.

        Args:
            product_name: Product name like "CDN", "ecs"

        Returns:
            Normalized product ID

        Examples:
            >>> normalizer = RuleNormalizer()
            >>> normalizer.normalize_product("CDN")
            "cdn"
            >>> normalizer.normalize_product("ecs")
            "ecs"
        """
        # Direct mapping
        if product_name in self.PRODUCT_MAPPING:
            return self.PRODUCT_MAPPING[product_name]

        # Case-insensitive lookup
        lower_name = product_name.lower()
        if lower_name in [k.lower() for k in self.PRODUCT_MAPPING.keys()]:
            for key, value in self.PRODUCT_MAPPING.items():
                if key.lower() == lower_name:
                    return value

        # Return original lowercase if no match
        return product_name.lower()

    def normalize_field(self, field_name: str) -> str:
        """
        Normalize field name to canonical form.

        Args:
            field_name: Field name like "金额", "数量"

        Returns:
            Normalized field name

        Examples:
            >>> normalizer = RuleNormalizer()
            >>> normalizer.normalize_field("金额")
            "出账金额"
            >>> normalizer.normalize_field("数量")
            "订单数量"
        """
        if field_name in self.FIELD_MAPPING:
            return self.FIELD_MAPPING[field_name]

        # Return original if no match
        return field_name

    def format_product_for_query(self, product_id: str) -> str:
        """
        Format product ID for SQL query.

        Args:
            product_id: Product ID

        Returns:
            Formatted string like "产品ID为cdn"
        """
        return f"产品ID为{product_id}"

    def format_field_for_query(self, field_name: str) -> str:
        """
        Format field name for SQL query.

        Args:
            field_name: Normalized field name

        Returns:
            Formatted string (typically just the field name)
        """
        return field_name

    def get_all_products(self) -> List[str]:
        """Get list of all supported product IDs."""
        return list(set(self.PRODUCT_MAPPING.values()))

    def get_all_fields(self) -> List[str]:
        """Get list of all supported field names."""
        return list(set(self.FIELD_MAPPING.values()))

    def extract_time_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract and normalize time expression from text.

        Args:
            text: Input text

        Returns:
            Dict with original and normalized time, or None
        """
        for time_expr in self.TIME_EXPRESSIONS.keys():
            if time_expr in text:
                return {
                    "original": time_expr,
                    "normalized": self.normalize_time(time_expr)
                }

        # Check for year pattern
        import re
        year_pattern = r"(\d{4})年"
        match = re.search(year_pattern, text)
        if match:
            return {
                "original": match.group(0),
                "normalized": match.group(0)
            }

        return None

    def get_current_date_info(self) -> Dict[str, Any]:
        """
        Get current date information.

        Returns:
            Dict with current date, year, month, quarter
        """
        today = date.today()
        return {
            "date": today.isoformat(),
            "year": today.year,
            "month": today.month,
            "day": today.day,
            "quarter": (today.month - 1) // 3 + 1,
        }
