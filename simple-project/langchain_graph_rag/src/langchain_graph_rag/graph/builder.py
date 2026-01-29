"""
Graph builder for constructing knowledge graphs from table structures.

Builds graph nodes and edges from database table models.
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from ..models.table_models import TableModel, TableRelationModel
from ..models.graph_models import (
    GraphNode, GraphEdge, NodeType, RelationType, GraphBuildResult
)
from .neo4j_store import Neo4jGraphStore
from .enricher import GraphEnricher


class GraphBuilder:
    """
    Knowledge graph builder.

    Builds a knowledge graph from table structures and relationships.
    """

    def __init__(
        self,
        graph_store: Neo4jGraphStore,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize graph builder.

        Args:
            graph_store: Graph store implementation
            config: Optional configuration dictionary
        """
        self.store = graph_store
        self.config = config or {}
        self.enricher = GraphEnricher(config)

        # Get configuration
        self.auto_enrich = self.config.get("auto_enrich", True)
        self.infer_relations = self.config.get("infer_relations", True)
        self.batch_size = self.config.get("batch_size", 100)

        logger.info("GraphBuilder initialized")

    async def build_graph(
        self,
        tables: List[TableModel],
        relations: List[TableRelationModel],
        clear_existing: bool = True
    ) -> GraphBuildResult:
        """
        Build the knowledge graph from tables and relations.

        Args:
            tables: List of table models
            relations: List of table relations
            clear_existing: Whether to clear existing graph before building

        Returns:
            GraphBuildResult with statistics
        """
        import time
        start_time = time.time()

        stats = GraphBuildResult(
            success=False,
            tables_processed=len(tables),
            relations_processed=len(relations),
            build_time_ms=0.0
        )

        try:
            # Initialize store if needed
            await self.store.initialize()

            # Clear existing graph if requested
            if clear_existing:
                await self.store.clear()
                logger.info("Cleared existing graph")

            # Create nodes from tables
            nodes = self._create_table_nodes(tables)
            stats.nodes_created = len(nodes)

            # Add nodes in batches
            for i in range(0, len(nodes), self.batch_size):
                batch = nodes[i:i + self.batch_size]
                await self.store.add_nodes_batch(batch)
                logger.debug(f"Added batch of {len(batch)} nodes")

            logger.info(f"Created {stats.nodes_created} table nodes")

            # Create edges from relations
            edges = self._create_relation_edges(relations, tables)
            stats.edges_created = len(edges)

            # Add edges in batches
            for i in range(0, len(edges), self.batch_size):
                batch = edges[i:i + self.batch_size]
                await self.store.add_edges_batch(batch)
                logger.debug(f"Added batch of {len(batch)} edges")

            logger.info(f"Created {stats.edges_created} relation edges")

            # Enrich graph if enabled
            if self.auto_enrich:
                enrichment_stats = await self.enricher.enrich(
                    self.store, tables, relations
                )
                stats.nodes_created += enrichment_stats.get("nodes_added", 0)
                stats.edges_created += enrichment_stats.get("edges_added", 0)

            # Calculate build time
            stats.build_time_ms = (time.time() - start_time) * 1000
            stats.success = True

            logger.info(f"Graph built successfully: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Error building graph: {e}")
            stats.build_time_ms = (time.time() - start_time) * 1000
            stats.error_message = str(e)
            return stats

    def _create_table_nodes(self, tables: List[TableModel]) -> List[GraphNode]:
        """
        Create graph nodes from table models.

        Args:
            tables: List of TableModel objects

        Returns:
            List of GraphNode objects
        """
        nodes = []

        for table in tables:
            # Determine node color based on table type
            color = self._get_table_color(table)

            # Determine node size based on column count
            size = self._get_table_size(table)

            # Build semantic labels
            semantic_labels = self._get_semantic_labels(table)

            node = GraphNode(
                id=table.graph_node_id or f"table:{table.database}.{table.name}",
                label=table.name,
                node_type=NodeType.TABLE,
                properties={
                    "database": table.database,
                    "row_count": table.row_count or 0,
                    "comment": table.comment or "",
                    "column_count": len(table.columns),
                    "primary_keys": table.primary_keys,
                    "foreign_key_count": len(table.foreign_keys),
                    "columns": [
                        {
                            "name": col.name,
                            "type": col.type,
                            "nullable": col.nullable,
                            "primary_key": col.primary_key,
                            "comment": col.comment or "",
                            "max_length": col.max_length,
                            "aliases": col.aliases or []
                        }
                        for col in table.columns
                    ]
                },
                size=size,
                color=color,
                shape="ellipse"
            )

            # Add semantic labels to properties
            if semantic_labels:
                node.properties["semantic_labels"] = semantic_labels

            nodes.append(node)

        return nodes

    def _create_relation_edges(self, relations: List[TableRelationModel], tables: List[TableModel]) -> List[GraphEdge]:
        """
        Create graph edges from table relation models.

        Args:
            relations: List of TableRelationModel objects
            tables: List of TableModel objects for node ID mapping

        Returns:
            List of GraphEdge objects
        """
        edges = []

        # Build table name to node ID mapping
        table_to_node_id = {}
        for table in tables:
            node_id = table.graph_node_id or f"table:{table.database}.{table.name}"
            table_to_node_id[table.name] = node_id

        for relation in relations:
            # Get source and target node IDs
            source_id = table_to_node_id.get(relation.from_table)
            target_id = table_to_node_id.get(relation.to_table)

            # Skip if source or target node not found
            if source_id is None or target_id is None:
                logger.warning(
                    f"Skipping relation {relation.from_table} -> {relation.to_table}: "
                    f"nodes not found (from_table_id={source_id}, to_table_id={target_id})"
                )
                continue

            # Determine edge color and width based on relation type
            color, width = self._get_relation_style(relation)

            edge = GraphEdge(
                id=relation.graph_edge_id or relation.key,
                source=source_id,
                target=target_id,
                relation_type=RelationType(relation.relation_type),
                label=f"{relation.from_column} → {relation.to_column}",
                properties={
                    "from_column": relation.from_column,
                    "to_column": relation.to_column,
                    "join_type": relation.join_type,
                    "cardinality": relation.cardinality,
                    "confidence": relation.confidence
                },
                weight=relation.weight,
                width=width,
                color=color,
                style="solid" if relation.confidence > 0.8 else "dashed"
            )

            edges.append(edge)

        return edges

    def _get_table_color(self, table: TableModel) -> str:
        """
        Get color for a table based on its type.

        Args:
            table: TableModel object

        Returns:
            Hex color string
        """
        table_name_lower = table.name.lower()

        # Fact tables
        if any(kw in table_name_lower for kw in ["fact", "transaction", "log", "event", "order", "sale"]):
            return "#e74c3c"  # Red

        # Dimension tables
        if any(kw in table_name_lower for kw in ["dim", "lookup", "ref", "category", "customer"]):
            return "#2ecc71"  # Green

        # Bridge tables
        if any(kw in table_name_lower for kw in ["bridge", "link", "mapping", "relation", "_has_"]):
            return "#f39c12"  # Orange

        # Default blue
        return "#3498db"

    def _get_table_size(self, table: TableModel) -> int:
        """
        Get size for a table node based on column count.

        Args:
            table: TableModel object

        Returns:
            Node size (20-60)
        """
        base_size = 30
        column_factor = min(len(table.columns) * 2, 30)
        return base_size + column_factor

    def _get_semantic_labels(self, table: TableModel) -> List[str]:
        """
        Get semantic labels for a table.

        Args:
            table: TableModel object

        Returns:
            List of semantic labels
        """
        labels = []
        table_name_lower = table.name.lower()

        # Business domain labels
        if any(kw in table_name_lower for kw in ["order", "purchase", "sale", "transaction"]):
            labels.append("销售域")
        elif any(kw in table_name_lower for kw in ["customer", "user", "account", "client"]):
            labels.append("客户域")
        elif any(kw in table_name_lower for kw in ["product", "item", "sku", "inventory"]):
            labels.append("产品域")
        elif any(kw in table_name_lower for kw in ["payment", "invoice", "billing", "finance"]):
            labels.append("财务域")

        # Table type labels
        if table.row_count and table.row_count > 1000000:
            labels.append("大表")

        if any(kw in table_name_lower for kw in ["fact", "log", "event"]):
            labels.append("事实表")

        if any(kw in table_name_lower for kw in ["dim", "lookup", "ref"]):
            labels.append("维度表")

        return labels

    def _get_relation_style(self, relation: TableRelationModel) -> tuple:
        """
        Get color and width for a relation edge.

        Args:
            relation: TableRelationModel object

        Returns:
            Tuple of (color, width)
        """
        relation_type = relation.relation_type

        if relation_type == "foreign_key":
            return "#e67e22", 3  # Orange, thick
        elif relation_type == "join":
            return "#3498db", 2  # Blue, medium
        elif relation_type == "semantic":
            return "#1abc9c", 1  # Teal, thin
        elif relation_type == "reference":
            return "#9b59b6", 2  # Purple, medium
        else:
            return "#95a5a6", 2  # Gray, medium
