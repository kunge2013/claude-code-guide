"""
Graph models for knowledge graph representation.

Defines Pydantic models for representing nodes, edges, and paths in the knowledge graph.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class NodeType(str, Enum):
    """Node types in the knowledge graph."""
    TABLE = "table"
    COLUMN = "column"
    VIEW = "view"
    DATABASE = "database"


class RelationType(str, Enum):
    """Relation types in the knowledge graph."""
    FOREIGN_KEY = "foreign_key"
    JOIN = "join"
    REFERENCE = "reference"
    SEMANTIC = "semantic"
    HIERARCHY = "hierarchy"


class GraphNode(BaseModel):
    """Graph node model.

    Represents a node in the knowledge graph (table, column, etc.).
    """

    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Display label")
    node_type: NodeType = Field(..., description="Node type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional node properties")

    # Visualization properties
    x: Optional[float] = Field(default=None, description="X coordinate for visualization")
    y: Optional[float] = Field(default=None, description="Y coordinate for visualization")
    size: int = Field(default=30, description="Node size for visualization")
    color: str = Field(default="#3498db", description="Node color")
    shape: str = Field(default="ellipse", description="Node shape")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "table:sales_db.orders",
                "label": "orders",
                "node_type": "table",
                "properties": {
                    "database": "sales_db",
                    "row_count": 100000,
                    "comment": "Order table"
                },
                "size": 40,
                "color": "#e74c3c"
            }
        }


class GraphEdge(BaseModel):
    """Graph edge model.

    Represents a relationship/edge between two nodes in the knowledge graph.
    """

    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relation_type: RelationType = Field(..., description="Relation type")
    label: str = Field(..., description="Display label")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional edge properties")

    # Visualization properties
    weight: float = Field(default=1.0, ge=0.0, description="Edge weight for path calculations")
    width: int = Field(default=2, description="Edge width for visualization")
    color: str = Field(default="#95a5a6", description="Edge color")
    style: str = Field(default="solid", description="Edge style: solid, dashed, dotted")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "edge:orders.customer_id->customers.id",
                "source": "table:orders",
                "target": "table:customers",
                "relation_type": "foreign_key",
                "label": "customer_id → id",
                "properties": {
                    "from_column": "customer_id",
                    "to_column": "id",
                    "cardinality": "N:1"
                },
                "weight": 1.0,
                "width": 3,
                "color": "#e67e22"
            }
        }


class GraphPath(BaseModel):
    """Graph path model.

    Represents a path through the graph from a start node to an end node.
    """

    nodes: List[str] = Field(..., description="Sequence of node IDs in the path")
    edges: List[GraphEdge] = Field(..., description="Edges connecting the nodes")
    length: int = Field(..., description="Path length (number of hops)")
    total_weight: float = Field(default=0.0, description="Total weight of the path")

    # Path explanation
    explanation: str = Field(default="", description="Natural language explanation of the path")
    sql_join_hint: str = Field(default="", description="SQL JOIN hint for this path")

    class Config:
        json_schema_extra = {
            "example": {
                "nodes": ["table:orders", "table:order_items", "table:products"],
                "edges": [
                    {
                        "source": "table:orders",
                        "target": "table:order_items",
                        "relation_type": "foreign_key"
                    },
                    {
                        "source": "table:order_items",
                        "target": "table:products",
                        "relation_type": "foreign_key"
                    }
                ],
                "length": 2,
                "explanation": "Orders connect to products through order_items table",
                "sql_join_hint": "FROM orders JOIN order_items ON orders.id = order_items.order_id JOIN products ON order_items.product_id = products.id"
            }
        }


class GraphQueryResult(BaseModel):
    """Graph query result model.

    Represents the result of a graph query operation.
    """

    query: str = Field(..., description="Original query string")
    result_type: str = Field(..., description="Result type: path, neighbors, subgraph")
    data: Dict[str, Any] = Field(default_factory=dict, description="Query result data")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")

    # LangChain enhancement
    natural_language_explanation: Optional[str] = Field(
        default=None,
        description="Natural language explanation generated by LLM"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Find path from orders to products",
                "result_type": "path",
                "data": {
                    "found": True,
                    "path": {}
                },
                "execution_time_ms": 45.2,
                "natural_language_explanation": "Orders connect to products through the order_items table..."
            }
        }


class GraphStatistics(BaseModel):
    """Graph statistics model.

    Represents statistics about the knowledge graph.
    """

    node_count: int = Field(..., description="Total number of nodes")
    edge_count: int = Field(..., description="Total number of edges")
    table_count: int = Field(default=0, description="Number of table nodes")
    column_count: int = Field(default=0, description="Number of column nodes")
    relation_types: Dict[str, int] = Field(default_factory=dict, description="Count of each relation type")
    is_connected: bool = Field(default=True, description="Whether the graph is connected")
    density: float = Field(default=0.0, description="Graph density")
    avg_degree: float = Field(default=0.0, description="Average node degree")

    class Config:
        json_schema_extra = {
            "example": {
                "node_count": 25,
                "edge_count": 40,
                "table_count": 10,
                "column_count": 15,
                "relation_types": {
                    "foreign_key": 30,
                    "semantic": 10
                },
                "is_connected": True,
                "density": 0.08,
                "avg_degree": 3.2
            }
        }


class Subgraph(BaseModel):
    """Subgraph model.

    Represents a portion of the knowledge graph (e.g., neighbors of a node).
    """

    nodes: List[GraphNode] = Field(..., description="Nodes in the subgraph")
    edges: List[GraphEdge] = Field(..., description="Edges in the subgraph")
    center_node: Optional[str] = Field(default=None, description="Center node ID (if applicable)")
    depth: int = Field(default=1, description="Depth of the subgraph from center")

    class Config:
        json_schema_extra = {
            "example": {
                "nodes": [
                    {"id": "table:customers", "label": "customers", "node_type": "table"},
                    {"id": "table:orders", "label": "orders", "node_type": "table"}
                ],
                "edges": [
                    {
                        "source": "table:orders",
                        "target": "table:customers",
                        "relation_type": "foreign_key"
                    }
                ],
                "center_node": "table:customers",
                "depth": 1
            }
        }


class GraphBuildResult(BaseModel):
    """Graph build result model.

    Represents the result of a graph build operation.
    """

    success: bool = Field(..., description="Whether the build was successful")
    nodes_created: int = Field(default=0, description="Number of nodes created")
    edges_created: int = Field(default=0, description="Number of edges created")
    tables_processed: int = Field(default=0, description="Number of tables processed")
    relations_processed: int = Field(default=0, description="Number of relations processed")
    build_time_ms: float = Field(..., description="Build time in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "nodes_created": 25,
                "edges_created": 40,
                "tables_processed": 10,
                "relations_processed": 15,
                "build_time_ms": 1234.5
            }
        }
