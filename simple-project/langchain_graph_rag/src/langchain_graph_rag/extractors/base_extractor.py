"""
Base extractor for data source abstraction.

Provides abstract interface for extracting table structures and relationships
from various data sources (MySQL, PostgreSQL, static configuration, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models.table_models import TableModel, TableRelationModel


class BaseExtractor(ABC):
    """
    Abstract base class for data extractors.

    All data source extractors should inherit from this class and implement
    the required methods for extracting table structures and relationships.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the extractor.

        Args:
            name: Extractor name for identification
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the data source.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to the data source.
        """
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate that the connection to the data source is working.

        Returns:
            True if connection is valid, False otherwise
        """
        pass

    @abstractmethod
    async def extract_tables(self) -> List[TableModel]:
        """
        Extract table structures from the data source.

        Returns:
            List of TableModel objects representing the tables
        """
        pass

    @abstractmethod
    async def extract_relations(self) -> List[TableRelationModel]:
        """
        Extract table relationships from the data source.

        Returns:
            List of TableRelationModel objects representing the relationships
        """
        pass

    async def extract_all(self) -> Dict[str, Any]:
        """
        Extract both tables and relations in one operation.

        Returns:
            Dictionary with 'tables' and 'relations' keys
        """
        tables = await self.extract_tables()
        relations = await self.extract_relations()

        return {
            "tables": tables,
            "relations": relations,
            "table_count": len(tables),
            "relation_count": len(relations)
        }

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self.config.get(key, default)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
