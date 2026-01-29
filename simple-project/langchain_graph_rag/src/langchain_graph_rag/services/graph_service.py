"""
Graph query service.

Provides high-level query operations for the knowledge graph.
"""

import time
from typing import List, Dict, Any, Optional
from functools import lru_cache
from loguru import logger
from ..graph.neo4j_store import Neo4jGraphStore
from ..models.graph_models import (
    GraphNode, GraphEdge, GraphPath, Subgraph, GraphStatistics
)
from ..models.query_models import (
    PathQueryRequest, PathQueryResponse,
    NeighborQueryRequest, NeighborQueryResponse,
    StatisticsResponse
)


class GraphQueryService:
    """
    High-level graph query service.

    Provides a unified interface for querying the knowledge graph
    with caching and performance optimizations.
    """

    def __init__(
        self,
        graph_store: Neo4jGraphStore,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize graph query service.

        Args:
            graph_store: Graph store instance
            config: Optional configuration dictionary
        """
        self.store = graph_store
        self.config = config or {}

        # Cache configuration
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.cache_ttl = self.config.get("cache_ttl_seconds", 3600)

        logger.info("GraphQueryService initialized")

    async def get_all_nodes(self) -> List[GraphNode]:
        """
        Get all nodes in the graph.

        Returns:
            List of GraphNode objects
        """
        return await self.store.get_all_nodes()

    async def get_all_edges(self) -> List[GraphEdge]:
        """
        Get all edges in the graph.

        Returns:
            List of GraphEdge objects
        """
        return await self.store.get_all_edges()

    async def find_shortest_path(
        self,
        start_table: str,
        end_table: str,
        max_hops: int = 5,
        relation_types: Optional[List[str]] = None
    ) -> Optional[GraphPath]:
        """
        Find the shortest path between two tables.

        Args:
            start_table: Starting table name
            end_table: Ending table name
            max_hops: Maximum number of hops
            relation_types: Optional filter by relation types

        Returns:
            GraphPath object or None if no path found
        """
        start_time = time.time()

        # Build node IDs
        start_node = f"table:{start_table}"
        end_node = f"table:{end_table}"

        # Find path
        path = await self.store.find_shortest_path(
            start_node=start_node,
            end_node=end_node,
            max_hops=max_hops,
            relation_types=relation_types
        )

        # Enhance path with explanation and SQL hint
        if path:
            path.explanation = self._generate_path_explanation(path)
            path.sql_join_hint = self._generate_sql_hint(path)

        execution_time_ms = (time.time() - start_time) * 1000
        logger.debug(f"Path query took {execution_time_ms:.2f}ms")

        return path

    async def find_path_with_explanation(
        self,
        start_table: str,
        end_table: str,
        max_hops: int = 5,
        relation_types: Optional[List[str]] = None,
        include_explanation: bool = True,
        include_sql_hint: bool = True
    ) -> Dict[str, Any]:
        """
        Find path and generate explanation.

        Args:
            start_table: Starting table name
            end_table: Ending table name
            max_hops: Maximum number of hops
            relation_types: Optional filter by relation types
            include_explanation: Include natural language explanation
            include_sql_hint: Include SQL JOIN hint

        Returns:
            Dictionary with path information
        """
        start_time = time.time()

        path = await self.find_shortest_path(
            start_table=start_table,
            end_table=end_table,
            max_hops=max_hops,
            relation_types=relation_types
        )

        execution_time_ms = (time.time() - start_time) * 1000

        if not path:
            return {
                "found": False,
                "message": f"No path found between '{start_table}' and '{end_table}'",
                "execution_time_ms": execution_time_ms
            }

        result = {
            "found": True,
            "path": {
                "nodes": path.nodes,
                "length": path.length,
                "total_weight": path.total_weight,
                "edges": [
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "label": edge.label,
                        "relation_type": edge.relation_type.value,
                        "properties": edge.properties
                    }
                    for edge in path.edges
                ]
            },
            "execution_time_ms": execution_time_ms
        }

        if include_explanation:
            result["explanation"] = path.explanation

        if include_sql_hint:
            result["sql_hint"] = path.sql_join_hint

        return result

    async def find_neighbors(
        self,
        table_name: str,
        depth: int = 1,
        relation_types: Optional[List[str]] = None,
        include_columns: bool = False
    ) -> List[GraphNode]:
        """
        Find neighbors of a table.

        Args:
            table_name: Table name
            depth: Search depth (1 = direct neighbors only)
            relation_types: Optional filter by relation types
            include_columns: Include column nodes in result

        Returns:
            List of neighbor GraphNode objects
        """
        start_time = time.time()

        center_node = f"table:{table_name}"
        neighbors = await self.store.find_neighbors(
            node_id=center_node,
            depth=depth,
            relation_types=relation_types
        )

        execution_time_ms = (time.time() - start_time) * 1000
        logger.debug(f"Neighbor query took {execution_time_ms:.2f}ms, found {len(neighbors)} neighbors")

        return neighbors

    async def find_neighbors_with_relations(
        self,
        table_name: str,
        depth: int = 1,
        relation_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Find neighbors with relationship information.

        Args:
            table_name: Table name
            depth: Search depth
            relation_types: Optional filter by relation types

        Returns:
            Dictionary with neighbors and relationships
        """
        start_time = time.time()

        center_node = f"table:{table_name}"

        # Get subgraph
        subgraph = await self.store.get_subgraph(
            center_node=center_node,
            depth=depth
        )

        # Build neighbor information with relations
        neighbors = []
        center_table = table_name

        for edge in subgraph.edges:
            # Determine direction and related table
            if edge.source == center_node:
                related_table = edge.target.replace("table:", "")
                direction = "out"
            elif edge.target == center_node:
                related_table = edge.source.replace("table:", "")
                direction = "in"
            else:
                continue

            neighbors.append({
                "table": related_table,
                "relation": edge.label,
                "relation_type": edge.relation_type.value,
                "direction": direction,
                "from_column": edge.properties.get("from_column"),
                "to_column": edge.properties.get("to_column"),
                "cardinality": edge.properties.get("cardinality"),
                "join_type": edge.properties.get("join_type")
            })

        execution_time_ms = (time.time() - start_time) * 1000

        return {
            "center_table": center_table,
            "neighbors": neighbors,
            "depth": depth,
            "total_count": len(neighbors),
            "execution_time_ms": execution_time_ms
        }

    async def get_statistics(self) -> GraphStatistics:
        """
        Get graph statistics.

        Returns:
            GraphStatistics object
        """
        return await self.store.get_statistics()

    async def get_node(self, table_name: str) -> Optional[GraphNode]:
        """
        Get a node by table name.

        Args:
            table_name: Table name

        Returns:
            GraphNode object or None if not found
        """
        node_id = f"table:{table_name}"
        return await self.store.get_node(node_id)

    async def node_exists(self, table_name: str) -> bool:
        """
        Check if a node exists.

        Args:
            table_name: Table name

        Returns:
            True if node exists, False otherwise
        """
        node = await self.get_node(table_name)
        return node is not None

    async def get_relations_for_table(
        self,
        table_name: str,
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        Get all relations for a specific table.

        Args:
            table_name: Table name
            direction: Direction filter ('in', 'out', 'both')

        Returns:
            List of relation dictionaries
        """
        # Get all edges
        all_edges = await self.get_all_edges()

        node_id = f"table:{table_name}"
        relations = []

        for edge in all_edges:
            if direction in ["in", "both"] and edge.target == node_id:
                relations.append({
                    "related_table": edge.source.replace("table:", ""),
                    "from_column": edge.properties.get("from_column"),
                    "to_column": edge.properties.get("to_column"),
                    "relation_type": edge.relation_type.value,
                    "direction": "in"
                })
            if direction in ["out", "both"] and edge.source == node_id:
                relations.append({
                    "related_table": edge.target.replace("table:", ""),
                    "from_column": edge.properties.get("from_column"),
                    "to_column": edge.properties.get("to_column"),
                    "relation_type": edge.relation_type.value,
                    "direction": "out"
                })

        return relations

    def _generate_path_explanation(self, path: GraphPath) -> str:
        """
        Generate natural language explanation for a path.

        Args:
            path: GraphPath object

        Returns:
            Natural language explanation
        """
        if not path.edges:
            return "No path found."

        # Extract table names
        tables = [node.replace("table:", "") for node in path.nodes]

        if path.length == 1:
            return (
                f"'{tables[0]}' is directly connected to '{tables[1]}' "
                f"via {path.edges[0].properties.get('from_column')} → {path.edges[0].properties.get('to_column')}."
            )

        explanation = f"To get from '{tables[0]}' to '{tables[-1]}', you need to go through {path.length} step"
        if path.length > 1:
            explanation += "s"

        explanation += ": " + " → ".join(tables) + "."

        # Add details about each hop
        details = []
        for i, edge in enumerate(path.edges, 1):
            from_col = edge.properties.get("from_column", "")
            to_col = edge.properties.get("to_column", "")
            cardinality = edge.properties.get("cardinality", "")
            details.append(f"{i}. {edge.source.replace('table:', '')}.{from_col} → {edge.target.replace('table:', '')}.{to_col} ({cardinality})")

        if details:
            explanation += "\n\nDetails:\n" + "\n".join(details)

        return explanation

    def _generate_sql_hint(self, path: GraphPath) -> str:
        """
        Generate SQL JOIN hint for a path.

        Args:
            path: GraphPath object

        Returns:
            SQL JOIN hint string
        """
        if not path.edges:
            return ""

        # Get the first table as the base
        tables = [node.replace("table:", "") for node in path.nodes]
        base_table = tables[0]

        # Build JOIN clauses
        join_clauses = []
        for edge in path.edges:
            from_table = edge.source.replace("table:", "")
            to_table = edge.target.replace("table:", "")
            from_col = edge.properties.get("from_column", "")
            to_col = edge.properties.get("to_column", "")
            join_type = edge.properties.get("join_type", "INNER")

            join_clauses.append(
                f"{join_type} JOIN {to_table} ON {from_table}.{from_col} = {to_table}.{to_col}"
            )

        return f"FROM {base_table}\n  " + "\n  ".join(join_clauses)

    def clear_cache(self) -> None:
        """Clear the query cache."""
        if self.cache_enabled:
            self.get_all_nodes.cache_clear()
            logger.info("Query cache cleared")
