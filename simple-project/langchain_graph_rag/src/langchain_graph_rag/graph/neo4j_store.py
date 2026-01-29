"""
Neo4j graph store implementation.

Provides graph storage and query operations using Neo4j.
"""

from typing import List, Dict, Any, Optional
import json
from neo4j import AsyncGraphDatabase
from loguru import logger
from ..models.graph_models import (
    GraphNode, GraphEdge, GraphPath, Subgraph,
    GraphStatistics, NodeType, RelationType
)


class Neo4jGraphStore:
    """
    Neo4j-based graph storage implementation.

    Provides CRUD operations for nodes and edges, as well as
    advanced graph queries like shortest path and neighbors.
    """

    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize Neo4j graph store.

        Args:
            uri: Neo4j connection URI (e.g., bolt://localhost:7687)
            user: Neo4j username
            password: Neo4j password
        """
        self._uri = uri
        self._user = user
        self._password = password
        self.driver = None
        self._initialized = False
        self._event_loop_id = None
        logger.info(f"Neo4j store configured: {uri}")

    def _get_driver(self):
        """
        Get or create the Neo4j driver for the current event loop.

        This method ensures that the driver is created for the current event loop,
        avoiding issues with asyncio event loop mismatches when using asyncio.run().
        """
        import asyncio
        current_loop = asyncio.get_event_loop()
        current_loop_id = id(current_loop)

        # If driver doesn't exist or we're in a different event loop, recreate it
        if self.driver is None or self._event_loop_id != current_loop_id:
            # Store old driver for async cleanup later
            old_driver = self.driver

            # Create new driver for this event loop
            self.driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password)
            )
            self._event_loop_id = current_loop_id
            self._initialized = False  # Need to reinitialize
            logger.debug(f"Neo4j driver created for event loop {current_loop_id}")

            # Schedule old driver cleanup (don't await to avoid blocking)
            if old_driver is not None:
                try:
                    # Create a task to close the old driver
                    asyncio.create_task(self._close_driver_async(old_driver))
                except Exception:
                    pass

        return self.driver

    async def _close_driver_async(self, driver):
        """Async close driver helper."""
        try:
            await driver.close()
        except Exception:
            pass

    async def initialize(self) -> None:
        """
        Initialize the graph database.

        Create indexes and constraints for optimal performance.
        """
        if self._initialized:
            return

        async with self._get_driver().session() as session:
            # Create unique constraint on node id
            await session.run(
                "CREATE CONSTRAINT node_id_unique IF NOT EXISTS "
                "FOR (n:Node) REQUIRE n.id IS UNIQUE"
            )

            # Create indexes
            await session.run(
                "CREATE INDEX node_type_idx IF NOT EXISTS "
                "FOR (n:Node) ON (n.node_type)"
            )

            await session.run(
                "CREATE INDEX edge_relation_type_idx IF NOT EXISTS "
                "FOR ()-[r:RELATES]->() ON (r.relation_type)"
            )

        self._initialized = True
        logger.info("Neo4j graph store initialized with indexes")

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        await self.driver.close()
        logger.info("Neo4j connection closed")

    async def clear(self) -> None:
        """
        Clear all nodes and edges from the graph.

        Warning: This will delete all data!
        """
        async with self._get_driver().session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        logger.info("Graph cleared")

    # ============================================================================
    # Node Operations
    # ============================================================================

    async def add_node(self, node: GraphNode) -> None:
        """
        Add a node to the graph.

        Args:
            node: GraphNode object to add
        """
        cypher = """
            MERGE (n:Node {id: $id})
            SET n.label = $label,
                n.node_type = $node_type,
                n.properties = $properties,
                n.size = $size,
                n.color = $color,
                n.shape = $shape,
                n.x = $x,
                n.y = $y
        """

        async with self._get_driver().session() as session:
            await session.run(
                cypher,
                id=node.id,
                label=node.label,
                node_type=node.node_type.value,
                properties=json.dumps(node.properties, ensure_ascii=False),
                size=node.size,
                color=node.color,
                shape=node.shape,
                x=node.x,
                y=node.y
            )

    async def add_nodes_batch(self, nodes: List[GraphNode]) -> int:
        """
        Add multiple nodes in a batch.

        Args:
            nodes: List of GraphNode objects

        Returns:
            Number of nodes added
        """
        if not nodes:
            return 0

        # Use UNWIND for batch processing
        cypher = """
            UNWIND $nodes AS node
            MERGE (n:Node {id: node.id})
            SET n.label = node.label,
                n.node_type = node.node_type,
                n.properties = node.properties,
                n.size = node.size,
                n.color = node.color,
                n.shape = node.shape,
                n.x = node.x,
                n.y = node.y
        """

        node_data = [
            {
                "id": n.id,
                "label": n.label,
                "node_type": n.node_type.value,
                "properties": json.dumps(n.properties, ensure_ascii=False),
                "size": n.size,
                "color": n.color,
                "shape": n.shape,
                "x": n.x,
                "y": n.y
            }
            for n in nodes
        ]

        async with self._get_driver().session() as session:
            result = await session.run(cypher, nodes=node_data)
            summary = await result.consume()
            return summary.counters.properties_set

    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        """
        Get a node by ID.

        Args:
            node_id: Node ID

        Returns:
            GraphNode object or None if not found
        """
        cypher = "MATCH (n:Node {id: $id}) RETURN n"

        async with self._get_driver().session() as session:
            result = await session.run(cypher, id=node_id)
            record = await result.single()

            if record:
                return self._record_to_node(record["n"])
            return None

    async def get_all_nodes(self) -> List[GraphNode]:
        """
        Get all nodes in the graph.

        Returns:
            List of GraphNode objects
        """
        cypher = "MATCH (n:Node) RETURN n"

        async with self._get_driver().session() as session:
            result = await session.run(cypher)
            nodes = []
            async for record in result:
                nodes.append(self._record_to_node(record["n"]))
            return nodes

    # ============================================================================
    # Edge Operations
    # ============================================================================

    async def add_edge(self, edge: GraphEdge) -> None:
        """
        Add an edge to the graph.

        Args:
            edge: GraphEdge object to add
        """
        cypher = """
            MATCH (source:Node {id: $source})
            MATCH (target:Node {id: $target})
            MERGE (source)-[r:RELATES {id: $id}]->(target)
            SET r.relation_type = $relation_type,
                r.label = $label,
                r.properties = $properties,
                r.weight = $weight,
                r.width = $width,
                r.color = $color,
                r.style = $style
        """

        async with self._get_driver().session() as session:
            await session.run(
                cypher,
                source=edge.source,
                target=edge.target,
                id=edge.id,
                relation_type=edge.relation_type.value,
                label=edge.label,
                properties=json.dumps(edge.properties, ensure_ascii=False),
                weight=edge.weight,
                width=edge.width,
                color=edge.color,
                style=edge.style
            )

    async def add_edges_batch(self, edges: List[GraphEdge]) -> int:
        """
        Add multiple edges in a batch.

        Args:
            edges: List of GraphEdge objects

        Returns:
            Number of edges added
        """
        if not edges:
            return 0

        cypher = """
            UNWIND $edges AS edge
            MATCH (source:Node {id: edge.source})
            MATCH (target:Node {id: edge.target})
            MERGE (source)-[r:RELATES {id: edge.id}]->(target)
            SET r.relation_type = edge.relation_type,
                r.label = edge.label,
                r.properties = edge.properties,
                r.weight = edge.weight,
                r.width = edge.width,
                r.color = edge.color,
                r.style = edge.style
        """

        edge_data = [
            {
                "source": e.source,
                "target": e.target,
                "id": e.id,
                "relation_type": e.relation_type.value,
                "label": e.label,
                "properties": json.dumps(e.properties, ensure_ascii=False),
                "weight": e.weight,
                "width": e.width,
                "color": e.color,
                "style": e.style
            }
            for e in edges
        ]

        async with self._get_driver().session() as session:
            result = await session.run(cypher, edges=edge_data)
            summary = await result.consume()
            return summary.counters.relationships_created

    async def get_all_edges(self) -> List[GraphEdge]:
        """
        Get all edges in the graph.

        Returns:
            List of GraphEdge objects
        """
        cypher = "MATCH (a:Node)-[r:RELATES]->(b:Node) RETURN a, r, b"

        async with self._get_driver().session() as session:
            result = await session.run(cypher)
            edges = []
            async for record in result:
                edge = self._record_to_edge(record["a"], record["r"], record["b"])
                edges.append(edge)
            return edges

    # ============================================================================
    # Query Operations
    # ============================================================================

    async def find_shortest_path(
        self,
        start_node: str,
        end_node: str,
        max_hops: int = 5,
        relation_types: Optional[List[str]] = None
    ) -> Optional[GraphPath]:
        """
        Find the shortest path between two nodes.

        Args:
            start_node: Start node ID
            end_node: End node ID
            max_hops: Maximum number of hops
            relation_types: Optional filter by relation types

        Returns:
            GraphPath object or None if no path found
        """
        # Build relation type filter
        rel_filter = ""
        if relation_types:
            rel_types_str = "|".join(relation_types)
            rel_filter = f":RELATES{{{rel_types_str}}}"

        cypher = f"""
            MATCH path = shortestPath(
                (start:Node {{id: $start_id}})-[*1..{max_hops}]{rel_filter}-(end:Node {{id: $end_id}})
            )
            RETURN path,
                   [node IN nodes(path) | node.id] as node_ids,
                   [rel IN relationships(path) | {{source: startNode(rel).id, target: endNode(rel).id, rel: rel}}] as rels_data,
                   length(path) as path_length
            LIMIT 1
        """

        async with self._get_driver().session() as session:
            result = await session.run(
                cypher,
                start_id=start_node,
                end_id=end_node
            )
            record = await result.single()

            if record:
                return self._build_graph_path(record)

        return None

    async def find_neighbors(
        self,
        node_id: str,
        depth: int = 1,
        relation_types: Optional[List[str]] = None
    ) -> List[GraphNode]:
        """
        Find neighbors of a node.

        Args:
            node_id: Center node ID
            depth: Search depth (1 = direct neighbors only)
            relation_types: Optional filter by relation types

        Returns:
            List of neighbor GraphNode objects
        """
        # Build relation type filter
        rel_filter = ""
        if relation_types:
            rel_types_str = "|".join(relation_types)
            rel_filter = f":RELATES{{{rel_types_str}}}"
        else:
            rel_filter = ":RELATES"

        cypher = f"""
            MATCH (center:Node {{id: $node_id}})
            MATCH (center)-[{rel_filter}*1..{depth}]-(neighbor:Node)
            WHERE neighbor.id <> $node_id
            RETURN DISTINCT neighbor
            LIMIT 100
        """

        async with self._get_driver().session() as session:
            result = await session.run(cypher, node_id=node_id)
            neighbors = []
            async for record in result:
                neighbors.append(self._record_to_node(record["neighbor"]))
            return neighbors

    async def get_subgraph(
        self,
        center_node: str,
        depth: int = 1
    ) -> Subgraph:
        """
        Get a subgraph around a center node.

        Args:
            center_node: Center node ID
            depth: Depth of the subgraph

        Returns:
            Subgraph object
        """
        cypher = f"""
            MATCH (center:Node {{id: $center_id}})
            MATCH (center)-[r:RELATES*1..{depth}]-(neighbor:Node)
            RETURN center, collect(DISTINCT neighbor) as neighbors,
                   collect(DISTINCT r) as relationships
        """

        async with self._get_driver().session() as session:
            result = await session.run(cypher, center_id=center_node)
            record = await result.single()

            if not record:
                return Subgraph(nodes=[], edges=[], center_node=center_node, depth=depth)

            # Build nodes list
            nodes = [self._record_to_node(record["center"])]
            for neighbor in record["neighbors"]:
                nodes.append(self._record_to_node(neighbor))

            # Build edges list
            edges = []
            for rels_chain in record["relationships"]:
                for rel in rels_chain:
                    start_id = rel.start_node.id
                    end_id = rel.end_node.id
                    edge = GraphEdge(
                        id=f"{start_id}->{end_id}",
                        source=start_id,
                        target=end_id,
                        relation_type=RelationType(rel.get("relation_type", "join")),
                        label=rel.get("label", ""),
                        properties=rel.get("properties", {}),
                        weight=rel.get("weight", 1.0),
                        width=rel.get("width", 2),
                        color=rel.get("color", "#95a5a6")
                    )
                    edges.append(edge)

            return Subgraph(
                nodes=nodes,
                edges=edges,
                center_node=center_node,
                depth=depth
            )

    async def get_statistics(self) -> GraphStatistics:
        """
        Get graph statistics.

        Returns:
            GraphStatistics object
        """
        cypher = """
            MATCH (n:Node)
            WITH count(n) as node_count
            MATCH ()-[r:RELATES]->()
            WITH node_count, count(r) as edge_count
            MATCH (n:Node)
            RETURN node_count,
                   edge_count,
                   count(CASE WHEN n.node_type = 'table' THEN 1 END) as table_count,
                   count(CASE WHEN n.node_type = 'column' THEN 1 END) as column_count
        """

        async with self._get_driver().session() as session:
            result = await session.run(cypher)
            record = await result.single()

            # Get relation type breakdown
            rel_cypher = """
                MATCH ()-[r:RELATES]->()
                RETURN r.relation_type as type, count(r) as count
            """
            rel_result = await session.run(rel_cypher)
            relation_types = {}
            async for rel_record in rel_result:
                relation_types[rel_record["type"]] = rel_record["count"]

            return GraphStatistics(
                node_count=record["node_count"],
                edge_count=record["edge_count"],
                table_count=record["table_count"],
                column_count=record["column_count"],
                relation_types=relation_types
            )

    # ============================================================================
    # Helper Methods
    # ============================================================================

    def _record_to_node(self, record) -> GraphNode:
        """Convert a Neo4j record to GraphNode."""
        # Deserialize properties from JSON string
        properties_value = record.get("properties", {})
        if isinstance(properties_value, str):
            try:
                properties_value = json.loads(properties_value)
            except (json.JSONDecodeError, TypeError):
                properties_value = {}

        return GraphNode(
            id=record["id"],
            label=record["label"],
            node_type=NodeType(record["node_type"]),
            properties=properties_value,
            size=record.get("size", 30),
            color=record.get("color", "#3498db"),
            shape=record.get("shape", "ellipse"),
            x=record.get("x"),
            y=record.get("y")
        )

    def _record_to_edge(self, start_record, rel_record, end_record) -> GraphEdge:
        """Convert Neo4j records to GraphEdge."""
        # Deserialize properties from JSON string
        properties_value = rel_record.get("properties", {})
        if isinstance(properties_value, str):
            try:
                properties_value = json.loads(properties_value)
            except (json.JSONDecodeError, TypeError):
                properties_value = {}

        return GraphEdge(
            id=rel_record["id"],
            source=start_record["id"],
            target=end_record["id"],
            relation_type=RelationType(rel_record["relation_type"]),
            label=rel_record.get("label", ""),
            properties=properties_value,
            weight=rel_record.get("weight", 1.0),
            width=rel_record.get("width", 2),
            color=rel_record.get("color", "#95a5a6"),
            style=rel_record.get("style", "solid")
        )

    def _build_graph_path(self, record) -> GraphPath:
        """Build GraphPath from a Neo4j path record."""
        path = record["path"]
        node_ids = record["node_ids"]
        rels_data = record["rels_data"]
        path_length = record["path_length"]

        # Build edges
        edges = []
        for rel_data in rels_data:
            # Deserialize properties from JSON string
            properties_value = rel_data["rel"].get("properties", {})
            if isinstance(properties_value, str):
                try:
                    properties_value = json.loads(properties_value)
                except (json.JSONDecodeError, TypeError):
                    properties_value = {}

            edges.append(GraphEdge(
                id=rel_data["rel"]["id"],
                source=rel_data["source"],
                target=rel_data["target"],
                relation_type=RelationType(rel_data["rel"].get("relation_type", "join")),
                label=rel_data["rel"].get("label", ""),
                properties=properties_value,
                weight=rel_data["rel"].get("weight", 1.0)
            ))

        return GraphPath(
            nodes=node_ids,
            edges=edges,
            length=path_length,
            total_weight=sum(e.weight for e in edges),
            explanation="",
            sql_join_hint=""
        )
