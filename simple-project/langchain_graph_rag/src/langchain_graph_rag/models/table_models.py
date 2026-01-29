"""
Table structure models for MySQL schema representation.

Defines Pydantic models for representing database tables, columns, and relationships.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ColumnModel(BaseModel):
    """Database column model.

    Represents a single column in a database table with all its metadata.
    """

    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Column data type")
    nullable: bool = Field(default=False, description="Whether the column allows NULL values")
    primary_key: bool = Field(default=False, description="Whether the column is a primary key")
    foreign_key: Optional[Dict[str, str]] = Field(
        default=None,
        description="Foreign key reference: {ref_table: table_name, ref_column: column_name}"
    )
    default: Optional[Any] = Field(default=None, description="Default value")
    comment: Optional[str] = Field(default="", description="Column comment")
    max_length: Optional[int] = Field(default=None, description="Maximum length for string types")
    aliases: List[str] = Field(default_factory=list, description="Semantic aliases for this column")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "customer_id",
                "type": "int",
                "nullable": False,
                "primary_key": False,
                "foreign_key": {"ref_table": "customers", "ref_column": "id"},
                "comment": "Customer ID foreign key",
                "aliases": ["客户ID", "客户编号", "customerId"]
            }
        }


class TableModel(BaseModel):
    """Database table model.

    Represents a complete table with all its columns and metadata.
    """

    name: str = Field(..., description="Table name")
    database: str = Field(..., description="Database name")
    schema_name: str = Field(default="", description="Schema name (if applicable)")
    columns: List[ColumnModel] = Field(default_factory=list, description="List of columns")
    primary_keys: List[str] = Field(default_factory=list, description="List of primary key column names")
    foreign_keys: List[Dict[str, str]] = Field(default_factory=list, description="List of foreign key references")
    row_count: Optional[int] = Field(default=None, description="Estimated row count")
    comment: Optional[str] = Field(default="", description="Table comment")

    # Graph-related properties
    graph_node_id: Optional[str] = Field(default=None, description="Node ID in the knowledge graph")
    semantic_labels: List[str] = Field(default_factory=list, description="Semantic labels (e.g., 'fact', 'dimension')")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "orders",
                "database": "sales_db",
                "columns": [
                    {
                        "name": "id",
                        "type": "int",
                        "nullable": False,
                        "primary_key": True,
                        "comment": "Order ID"
                    },
                    {
                        "name": "customer_id",
                        "type": "int",
                        "nullable": False,
                        "foreign_key": {"ref_table": "customers", "ref_column": "id"},
                        "comment": "Customer ID"
                    }
                ],
                "primary_keys": ["id"],
                "foreign_keys": [{"column": "customer_id", "ref_table": "customers", "ref_column": "id"}],
                "comment": "Order table"
            }
        }

    def get_column(self, column_name: str) -> Optional[ColumnModel]:
        """Get a column by name."""
        for col in self.columns:
            if col.name == column_name:
                return col
        return None

    def has_foreign_key_to(self, table_name: str) -> bool:
        """Check if table has a foreign key to another table."""
        return any(fk.get("ref_table") == table_name for fk in self.foreign_keys)


class TableRelationModel(BaseModel):
    """Table relationship model.

    Represents a relationship between two tables (foreign key, join, reference, etc.).
    """

    from_table: str = Field(..., description="Source table name")
    from_column: str = Field(..., description="Source column name")
    to_table: str = Field(..., description="Target table name")
    to_column: str = Field(..., description="Target column name")
    relation_type: str = Field(..., description="Relation type: foreign_key, join, reference, semantic")
    join_type: str = Field(default="INNER", description="JOIN type: INNER, LEFT, RIGHT, FULL")
    cardinality: str = Field(default="N:1", description="Cardinality: 1:1, 1:N, N:1, N:M")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score for inferred relations")

    # Graph edge properties
    graph_edge_id: Optional[str] = Field(default=None, description="Edge ID in the knowledge graph")
    weight: float = Field(default=1.0, ge=0.0, description="Edge weight for path calculations")
    bidirectional: bool = Field(default=False, description="Whether the relationship is bidirectional")

    class Config:
        json_schema_extra = {
            "example": {
                "from_table": "orders",
                "from_column": "customer_id",
                "to_table": "customers",
                "to_column": "id",
                "relation_type": "foreign_key",
                "cardinality": "N:1",
                "confidence": 1.0
            }
        }

    @property
    def key(self) -> str:
        """Unique key for this relationship."""
        return f"{self.from_table}.{self.from_column}->{self.to_table}.{self.to_column}"


class DatabaseModel(BaseModel):
    """Database model.

    Represents a complete database with all its tables.
    """

    name: str = Field(..., description="Database name")
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    tables: List[TableModel] = Field(default_factory=list, description="List of tables")
    relations: List[TableRelationModel] = Field(default_factory=list, description="List of table relationships")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "sales_db",
                "host": "localhost",
                "port": 3306,
                "tables": [],
                "relations": []
            }
        }

    def get_table(self, table_name: str) -> Optional[TableModel]:
        """Get a table by name."""
        for table in self.tables:
            if table.name == table_name:
                return table
        return None

    def get_relations_for_table(self, table_name: str) -> List[TableRelationModel]:
        """Get all relations involving a specific table."""
        return [
            r for r in self.relations
            if r.from_table == table_name or r.to_table == table_name
        ]
