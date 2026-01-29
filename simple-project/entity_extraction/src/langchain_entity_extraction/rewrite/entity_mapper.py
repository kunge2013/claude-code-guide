"""Entity mapping utilities for question rewriting."""

from typing import Dict, List, Optional

from langchain_entity_extraction.utils.logger import get_logger

logger = get_logger(__name__)


class EntityMapper:
    """
    Entity mapping utility for normalizing product names and field names.

    Maps aliases and abbreviations to standard entity IDs and names.
    """

    # Default product mappings
    DEFAULT_PRODUCT_MAPPINGS = {
        "cdn": {
            "standard_id": "cdn",
            "aliases": ["cdn", "CDN", "内容分发网络", "CDN服务"],
            "full_name": "内容分发网络"
        },
        "ecs": {
            "standard_id": "ecs",
            "aliases": ["ecs", "ECS", "云主机", "弹性计算", "云服务器"],
            "full_name": "云服务器"
        },
        "oss": {
            "standard_id": "oss",
            "aliases": ["oss", "OSS", "对象存储", "存储服务"],
            "full_name": "对象存储服务"
        },
        "rds": {
            "standard_id": "rds",
            "aliases": ["rds", "RDS", "云数据库", "数据库"],
            "full_name": "云数据库"
        },
        "slb": {
            "standard_id": "slb",
            "aliases": ["slb", "SLB", "负载均衡", "负载均衡服务"],
            "full_name": "负载均衡"
        },
    }

    # Default field mappings
    DEFAULT_FIELD_MAPPINGS = {
        "amount": {
            "standard_name": "出账金额",
            "aliases": ["金额", "费用", "钱", "总计", "出账", "账单金额"],
            "data_type": "decimal"
        },
        "quantity": {
            "standard_name": "订单数量",
            "aliases": ["数量", "个数", "单数", "订单数", "笔数"],
            "data_type": "integer"
        },
        "revenue": {
            "standard_name": "营业收入",
            "aliases": ["收入", "营收", "收益", "营业额"],
            "data_type": "decimal"
        },
        "user_count": {
            "standard_name": "用户数",
            "aliases": ["用户数", "用户", "用户数量", "客户数"],
            "data_type": "integer"
        },
        "traffic": {
            "standard_name": "流量",
            "aliases": ["流量", "访问量", "调用量"],
            "data_type": "decimal"
        },
    }

    def __init__(
        self,
        product_mappings: Optional[Dict[str, Dict]] = None,
        field_mappings: Optional[Dict[str, Dict]] = None
    ):
        """
        Initialize the entity mapper.

        Args:
            product_mappings: Custom product mappings
            field_mappings: Custom field mappings
        """
        self.product_mappings = product_mappings or self.DEFAULT_PRODUCT_MAPPINGS
        self.field_mappings = field_mappings or self.DEFAULT_FIELD_MAPPINGS

        # Build reverse lookup dictionaries
        self._product_alias_map = self._build_alias_map(self.product_mappings)
        self._field_alias_map = self._build_alias_map(self.field_mappings)

        logger.info(
            "EntityMapper initialized",
            products_count=len(self.product_mappings),
            fields_count=len(self.field_mappings)
        )

    def _build_alias_map(self, mappings: Dict[str, Dict]) -> Dict[str, str]:
        """
        Build a reverse lookup dictionary from aliases to standard names.

        Args:
            mappings: Mappings dictionary

        Returns:
            Dictionary mapping aliases to standard IDs/names
        """
        alias_map = {}
        for standard_id, config in mappings.items():
            standard = config.get("standard_id", standard_id)
            for alias in config.get("aliases", []):
                alias_map[alias.lower()] = standard
        return alias_map

    def map_product_name(self, name: str) -> str:
        """
        Map a product name or alias to its standard ID.

        Args:
            name: Product name or alias

        Returns:
            Standard product ID

        Examples:
            >>> mapper = EntityMapper()
            >>> mapper.map_product_name("cdn")
            "cdn"
            >>> mapper.map_product_name("CDN")
            "cdn"
            >>> mapper.map_product_name("内容分发网络")
            "cdn"
        """
        name_lower = name.lower()
        standard_id = self._product_alias_map.get(name_lower)

        if standard_id:
            logger.debug(f"Mapped product '{name}' to '{standard_id}'")
            return standard_id

        # If no mapping found, return original
        logger.debug(f"No mapping found for product '{name}', returning original")
        return name

    def map_field_name(self, name: str) -> str:
        """
        Map a field name or alias to its standard name.

        Args:
            name: Field name or alias

        Returns:
            Standard field name

        Examples:
            >>> mapper = EntityMapper()
            >>> mapper.map_field_name("金额")
            "出账金额"
            >>> mapper.map_field_name("费用")
            "出账金额"
        """
        name_lower = name.lower()
        standard_name = self._field_alias_map.get(name_lower)

        if standard_name:
            logger.debug(f"Mapped field '{name}' to '{standard_name}'")
            return standard_name

        # If no mapping found, return original
        logger.debug(f"No mapping found for field '{name}', returning original")
        return name

    def extract_products_from_text(self, text: str) -> List[Dict[str, str]]:
        """
        Extract and map all products mentioned in text.

        Args:
            text: Text to extract products from

        Returns:
            List of dictionaries with product information

        Examples:
            >>> mapper = EntityMapper()
            >>> mapper.extract_products_from_text("cdn和ecs产品的金额")
            [
                {"original": "cdn", "standard_id": "cdn"},
                {"original": "ecs", "standard_id": "ecs"}
            ]
        """
        found = []

        for standard_id, config in self.product_mappings.items():
            for alias in config["aliases"]:
                if alias.lower() in text.lower():
                    found.append({
                        "original": alias,
                        "standard_id": config["standard_id"],
                        "full_name": config.get("full_name", "")
                    })
                    break  # Only add once per product

        return found

    def extract_fields_from_text(self, text: str) -> List[Dict[str, str]]:
        """
        Extract and map all fields mentioned in text.

        Args:
            text: Text to extract fields from

        Returns:
            List of dictionaries with field information
        """
        found = []

        for standard_key, config in self.field_mappings.items():
            for alias in config["aliases"]:
                if alias in text:
                    found.append({
                        "original": alias,
                        "standard_name": config["standard_name"],
                        "data_type": config.get("data_type", "unknown")
                    })
                    break  # Only add once per field

        return found

    def get_all_products(self) -> List[str]:
        """Get list of all available product IDs."""
        return list(self.product_mappings.keys())

    def get_all_fields(self) -> List[str]:
        """Get list of all available field standard names."""
        return [config["standard_name"] for config in self.field_mappings.values()]

    def format_product_for_query(self, product_id: str) -> str:
        """
        Format a product ID for use in a rewritten question.

        Args:
            product_id: Standard product ID

        Returns:
            Formatted product expression (e.g., "产品ID为cdn")
        """
        return f"产品ID为{product_id}"

    def format_field_for_query(self, field_name: str) -> str:
        """
        Format a field name for use in a rewritten question.

        Args:
            field_name: Standard field name

        Returns:
            Formatted field expression (e.g., "出账金额")
        """
        return field_name

    def format_time_for_query(self, time_expr: str) -> str:
        """
        Format a time expression for use in a rewritten question.

        Args:
            time_expr: Time expression

        Returns:
            Formatted time expression (e.g., "时间为2026年")
        """
        return f"时间为{time_expr}"
