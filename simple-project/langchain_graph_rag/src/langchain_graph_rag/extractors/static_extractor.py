"""
Static configuration extractor.

Extracts table structures and relationships from YAML configuration files.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
from loguru import logger
from .base_extractor import BaseExtractor
from ..models.table_models import TableModel, ColumnModel, TableRelationModel


class StaticExtractor(BaseExtractor):
    """
    Static configuration extractor.

    Extracts table structures and relationships from YAML configuration files.
    Useful when database access is not available or for manual overrides.
    """

    def __init__(
        self,
        config_path: str = "config/data_sources.yaml",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize static extractor.

        Args:
            config_path: Path to YAML configuration file
            config: Optional additional configuration
        """
        super().__init__(name="static_extractor", config=config)
        self.config_path = Path(config_path)
        self._config_data: Optional[Dict[str, Any]] = None

    async def connect(self) -> bool:
        """
        Load configuration file.

        Returns:
            True if configuration loaded successfully, False otherwise
        """
        try:
            self._config_data = self._load_config()
            logger.info(f"Loaded static configuration from {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False

    async def disconnect(self) -> None:
        """Clear configuration data."""
        self._config_data = None

    async def validate_connection(self) -> bool:
        """
        Validate configuration file exists and is loadable.

        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.config_path.exists():
            logger.error(f"Configuration file not found: {self.config_path}")
            return False

        try:
            self._load_config()
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def _load_config(self) -> Dict[str, Any]:
        """
        Load YAML configuration file.

        Returns:
            Configuration dictionary
        """
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    async def extract_tables(self) -> List[TableModel]:
        """
        Extract tables from static configuration.

        Returns:
            List of TableModel objects
        """
        if not self._config_data:
            await self.connect()

        if not self._config_data:
            return []

        tables_config = self._config_data.get("static_schema", {}).get("tables", [])
        tables = []

        for table_config in tables_config:
            try:
                # Convert columns dict to ColumnModel objects
                columns = []
                for col_config in table_config.get("columns", []):
                    # Handle foreign key reference
                    foreign_key = None
                    if "foreign_key" in col_config and col_config["foreign_key"]:
                        foreign_key = {
                            "ref_table": col_config["foreign_key"].get("ref_table"),
                            "ref_column": col_config["foreign_key"].get("ref_column")
                        }

                    column = ColumnModel(
                        name=col_config["name"],
                        type=col_config["type"],
                        nullable=col_config.get("nullable", False),
                        primary_key=col_config.get("primary_key", False),
                        foreign_key=foreign_key,
                        comment=col_config.get("comment", ""),
                        max_length=col_config.get("max_length"),
                        aliases=col_config.get("aliases", [])
                    )
                    columns.append(column)

                # Build foreign keys list from columns
                foreign_keys = []
                for col in columns:
                    if col.foreign_key:
                        foreign_keys.append({
                            "column": col.name,
                            "ref_table": col.foreign_key["ref_table"],
                            "ref_column": col.foreign_key["ref_column"]
                        })

                table = TableModel(
                    name=table_config["name"],
                    database=table_config.get("database", "unknown_db"),
                    columns=columns,
                    primary_keys=table_config.get("primary_keys", []),
                    foreign_keys=foreign_keys,
                    comment=table_config.get("comment", ""),
                    graph_node_id=f"table:{table_config.get('database', 'unknown_db')}.{table_config['name']}"
                )
                tables.append(table)

            except Exception as e:
                logger.warning(f"Error parsing table config: {e}")
                continue

        logger.info(f"Extracted {len(tables)} tables from static configuration")
        return tables

    async def extract_relations(self) -> List[TableRelationModel]:
        """
        Extract relations from static configuration.

        Returns:
            List of TableRelationModel objects
        """
        if not self._config_data:
            await self.connect()

        if not self._config_data:
            return []

        relations_config = self._config_data.get("static_schema", {}).get("relations", [])
        relations = []

        for rel_config in relations_config:
            try:
                relation = TableRelationModel(
                    from_table=rel_config["from_table"],
                    from_column=rel_config["from_column"],
                    to_table=rel_config["to_table"],
                    to_column=rel_config["to_column"],
                    relation_type=rel_config.get("relation_type", "foreign_key"),
                    join_type=rel_config.get("join_type", "INNER"),
                    cardinality=rel_config.get("cardinality", "N:1"),
                    confidence=rel_config.get("confidence", 1.0),
                    graph_edge_id=f"edge:{rel_config['from_table']}.{rel_config['from_column']}->{rel_config['to_table']}.{rel_config['to_column']}"
                )
                relations.append(relation)

            except Exception as e:
                logger.warning(f"Error parsing relation config: {e}")
                continue

        logger.info(f"Extracted {len(relations)} relations from static configuration")
        return relations

    async def extract_all(self) -> Dict[str, Any]:
        """
        Extract both tables and relations.

        Returns:
            Dictionary with 'tables' and 'relations' keys
        """
        tables = await self.extract_tables()

        # Also extract relations defined at column level
        column_relations = []
        for table in tables:
            for fk in table.foreign_keys:
                column_relations.append(TableRelationModel(
                    from_table=table.name,
                    from_column=fk["column"],
                    to_table=fk["ref_table"],
                    to_column=fk["ref_column"],
                    relation_type="foreign_key",
                    join_type="INNER",
                    cardinality="N:1",
                    confidence=1.0
                ))

        # Get top-level relations
        config_relations = await self.extract_relations()

        # Merge and deduplicate
        all_relations = column_relations + config_relations
        seen = set()
        unique_relations = []
        for rel in all_relations:
            key = (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
            if key not in seen:
                seen.add(key)
                unique_relations.append(rel)

        return {
            "tables": tables,
            "relations": unique_relations,
            "table_count": len(tables),
            "relation_count": len(unique_relations)
        }
