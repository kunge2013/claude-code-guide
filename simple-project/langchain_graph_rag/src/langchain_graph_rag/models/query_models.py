"""
Query models for knowledge graph queries.

Defines Pydantic models for query requests and responses.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PathQueryRequest(BaseModel):
    """Path query request model.

    Request to find a path between two tables.
    """

    start_table: str = Field(..., description="Starting table name")
    end_table: str = Field(..., description="Ending table name")
    max_hops: int = Field(default=5, ge=1, le=10, description="Maximum number of hops")
    relation_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by relation types (e.g., ['foreign_key', 'join'])"
    )
    include_explanation: bool = Field(default=True, description="Include natural language explanation")
    include_sql_hint: bool = Field(default=True, description="Include SQL JOIN hint")

    class Config:
        json_schema_extra = {
            "example": {
                "start_table": "orders",
                "end_table": "products",
                "max_hops": 3
            }
        }


class NeighborQueryRequest(BaseModel):
    """Neighbor query request model.

    Request to find neighbors of a table.
    """

    table_name: str = Field(..., description="Center table name")
    depth: int = Field(default=1, ge=1, le=3, description="Neighbor depth (1 = direct neighbors)")
    relation_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by relation types"
    )
    include_columns: bool = Field(default=False, description="Include column nodes in result")
    max_results: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")

    class Config:
        json_schema_extra = {
            "example": {
                "table_name": "customers",
                "depth": 1,
                "max_results": 50
            }
        }


class NaturalLanguageQueryRequest(BaseModel):
    """Natural language query request model.

    Request to query the graph using natural language.
    """

    question: str = Field(..., description="Natural language question")
    context: Optional[str] = Field(default=None, description="Additional context")
    database: Optional[str] = Field(default=None, description="Filter by database name")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Which tables are related to the customers table?",
                "database": "sales_db"
            }
        }


class RelationQueryRequest(BaseModel):
    """Relation query request model.

    Request to query relationships between tables.
    """

    table_name: str = Field(..., description="Table name")
    direction: str = Field(default="both", description="Direction: 'in', 'out', or 'both'")
    relation_type: Optional[str] = Field(default=None, description="Filter by relation type")

    class Config:
        json_schema_extra = {
            "example": {
                "table_name": "orders",
                "direction": "out",
                "relation_type": "foreign_key"
            }
        }


class StatisticsQueryRequest(BaseModel):
    """Statistics query request model.

    Request for graph statistics.
    """

    include_node_types: bool = Field(default=True, description="Include node type breakdown")
    include_relation_types: bool = Field(default=True, description="Include relation type breakdown")

    class Config:
        json_schema_extra = {
            "example": {
                "include_node_types": True,
                "include_relation_types": True
            }
        }


class PathQueryResponse(BaseModel):
    """Path query response model."""

    found: bool = Field(..., description="Whether a path was found")
    path: Optional[Dict[str, Any]] = Field(default=None, description="Path information")
    explanation: Optional[str] = Field(default=None, description="Natural language explanation")
    sql_hint: Optional[str] = Field(default=None, description="SQL JOIN hint")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "found": True,
                "path": {
                    "nodes": ["table:orders", "table:order_items", "table:products"],
                    "length": 2
                },
                "explanation": "Orders connect to products through order_items",
                "sql_hint": "FROM orders JOIN order_items ...",
                "execution_time_ms": 42.5
            }
        }


class NeighborQueryResponse(BaseModel):
    """Neighbor query response model."""

    center_table: str = Field(..., description="Center table name")
    neighbors: List[Dict[str, Any]] = Field(..., description="Neighbor tables with relationships")
    depth: int = Field(..., description="Depth of the search")
    total_count: int = Field(..., description="Total number of neighbors found")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "center_table": "customers",
                "neighbors": [
                    {
                        "table": "orders",
                        "relation": "customers.id <- orders.customer_id",
                        "relation_type": "foreign_key"
                    }
                ],
                "depth": 1,
                "total_count": 3,
                "execution_time_ms": 25.3
            }
        }


class NaturalLanguageQueryResponse(BaseModel):
    """Natural language query response model."""

    question: str = Field(..., description="Original question")
    answer: str = Field(..., description="Generated answer")
    query_type: str = Field(..., description="Detected query type: path, neighbors, relation, general")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Structured data if applicable")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Which tables are related to customers?",
                "answer": "The customers table is related to 3 other tables: orders, addresses, and payments.",
                "query_type": "neighbors",
                "execution_time_ms": 1234.5
            }
        }


class RelationQueryResponse(BaseModel):
    """Relation query response model."""

    table_name: str = Field(..., description="Table name")
    relations: List[Dict[str, Any]] = Field(..., description="List of relations")
    total_count: int = Field(..., description="Total number of relations")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "table_name": "orders",
                "relations": [
                    {
                        "related_table": "customers",
                        "from_column": "customer_id",
                        "to_column": "id",
                        "relation_type": "foreign_key",
                        "direction": "out"
                    }
                ],
                "total_count": 1,
                "execution_time_ms": 15.2
            }
        }


class StatisticsResponse(BaseModel):
    """Statistics response model."""

    node_count: int = Field(..., description="Total number of nodes")
    edge_count: int = Field(..., description="Total number of edges")
    table_count: int = Field(default=0, description="Number of table nodes")
    node_type_breakdown: Optional[Dict[str, int]] = Field(
        default=None,
        description="Breakdown by node type"
    )
    relation_type_breakdown: Optional[Dict[str, int]] = Field(
        default=None,
        description="Breakdown by relation type"
    )
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "node_count": 25,
                "edge_count": 40,
                "table_count": 10,
                "node_type_breakdown": {
                    "table": 10,
                    "column": 15
                },
                "relation_type_breakdown": {
                    "foreign_key": 30,
                    "semantic": 10
                },
                "execution_time_ms": 10.5
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    error_type: str = Field(..., description="Error type")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Table not found",
                "detail": "No table with name 'xyz' exists in the graph",
                "error_type": "NotFoundError"
            }
        }
