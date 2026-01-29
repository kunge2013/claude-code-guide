"""
Graph enricher for adding semantic relationships and labels.

Enhances the knowledge graph with inferred relationships and metadata.
"""

import re
from typing import List, Dict, Any, Optional
from loguru import logger
from ..models.table_models import TableModel, TableRelationModel
from ..models.graph_models import NodeType, RelationType
from .neo4j_store import Neo4jGraphStore


class GraphEnricher:
    """
    Graph enricher for semantic enhancement.

    Adds semantic labels, infers hidden relationships, and enriches
    graph metadata.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize graph enricher.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

        # Get semantic label configuration
        self.semantic_labels = self.config.get("semantic_labels", [])

        # Get table type configuration
        self.table_types = self.config.get("table_types", {})

        # Get column patterns
        self.foreign_key_pattern = self.config.get("foreign_key_pattern", "{table}_id")
        self.exclude_patterns = self.config.get("exclude_patterns", [])

        logger.debug("GraphEnricher initialized")

    async def enrich(
        self,
        graph_store: Neo4jGraphStore,
        tables: List[TableModel],
        relations: List[TableRelationModel]
    ) -> Dict[str, Any]:
        """
        Enrich the graph with semantic information.

        Args:
            graph_store: Graph store instance
            tables: List of table models
            relations: List of table relations

        Returns:
            Dictionary with enrichment statistics
        """
        stats = {
            "nodes_added": 0,
            "edges_added": 0,
            "labels_added": 0
        }

        # Add semantic labels to existing nodes
        for table in tables:
            labels = self._infer_semantic_labels(table)
            if labels:
                stats["labels_added"] += len(labels)

        # Infer additional semantic relationships
        inferred_relations = await self._infer_semantic_relations(tables, relations)
        if inferred_relations:
            from ..models.graph_models import GraphEdge

            edges = []
            for rel in inferred_relations:
                edge = GraphEdge(
                    id=rel.graph_edge_id or rel.key,
                    source=f"table:{rel.from_table}",
                    target=f"table:{rel.to_table}",
                    relation_type=RelationType.SEMANTIC,
                    label=f"{rel.from_column} → {rel.to_column}",
                    properties={
                        "from_column": rel.from_column,
                        "to_column": rel.to_column,
                        "cardinality": rel.cardinality,
                        "inferred": True
                    },
                    weight=rel.confidence * 0.5,  # Lower weight for semantic relations
                    width=1,
                    color="#1abc9c",
                    style="dashed"
                )
                edges.append(edge)

            # Add edges to graph
            await graph_store.add_edges_batch(edges)
            stats["edges_added"] = len(edges)

        logger.info(f"Graph enrichment complete: {stats}")
        return stats

    def _infer_semantic_labels(self, table: TableModel) -> List[str]:
        """
        Infer semantic labels for a table.

        Args:
            table: TableModel object

        Returns:
            List of semantic labels
        """
        labels = []
        table_name_lower = table.name.lower()

        # Business domain labels from configuration
        for domain_config in self.semantic_labels:
            domain = domain_config.get("domain", "")
            keywords = domain_config.get("keywords", [])

            if any(kw in table_name_lower for kw in keywords):
                labels.append(domain)

        # Table type labels from configuration
        for table_type, type_config in self.table_types.items():
            keywords = type_config.get("keywords", [])
            if any(kw in table_name_lower for kw in keywords):
                labels.append(f"type:{table_type}")

        # Size-based labels
        if table.row_count:
            if table.row_count > 10000000:
                labels.append("超大规模")
            elif table.row_count > 1000000:
                labels.append("大规模")
            elif table.row_count > 100000:
                labels.append("中等规模")
            else:
                labels.append("小规模")

        return labels

    async def _infer_semantic_relations(
        self,
        tables: List[TableModel],
        existing_relations: List[TableRelationModel]
    ) -> List[TableRelationModel]:
        """
        Infer semantic relationships between tables.

        Args:
            tables: List of table models
            existing_relations: Already known relations

        Returns:
            List of inferred TableRelationModel objects
        """
        inferred = []
        table_names = {t.name: t for t in tables}

        # Get existing relation keys to avoid duplicates
        existing_keys = {
            (r.from_table, r.from_column, r.to_table, r.to_column)
            for r in existing_relations
        }

        # Check for naming convention-based relations
        for table in tables:
            for column in table.columns:
                # Skip if already has foreign key or is primary key
                if column.foreign_key or column.primary_key:
                    continue

                # Check if column matches foreign key pattern
                match = re.match(r'^(.+)_id$', column.name.lower())
                if not match:
                    continue

                potential_ref_table = match.group(1)
                potential_ref_column = "id"

                # Check if referenced table exists
                if potential_ref_table not in table_names:
                    # Try singular form
                    potential_ref_table = potential_ref_table.rstrip('s')
                    if potential_ref_table not in table_names:
                        continue

                # Skip excluded patterns
                if any(pattern in column.name.lower() for pattern in self.exclude_patterns):
                    continue

                # Skip if relation already exists
                key = (table.name, column.name, potential_ref_table, potential_ref_column)
                if key in existing_keys:
                    continue

                # Create inferred relation
                inferred.append(TableRelationModel(
                    from_table=table.name,
                    from_column=column.name,
                    to_table=potential_ref_table,
                    to_column=potential_ref_column,
                    relation_type="semantic",
                    join_type="LEFT",
                    cardinality="N:1",
                    confidence=0.5,  # Lower confidence for semantic inference
                    graph_edge_id=f"semantic:{table.name}.{column.name}->{potential_ref_table}.{potential_ref_column}"
                ))

                # Add to existing keys to avoid duplicates
                existing_keys.add(key)

        # Look for self-referential relationships (hierarchical)
        for table in tables:
            for column in table.columns:
                if column.foreign_key and column.foreign_key.get("ref_table") == table.name:
                    # This is already captured as FK, but we can mark as hierarchical
                    for existing_rel in existing_relations:
                        if (existing_rel.from_table == table.name and
                            existing_rel.from_column == column.name and
                            existing_rel.to_table == table.name):
                            existing_rel.relation_type = "hierarchy"

        if inferred:
            logger.info(f"Inferred {len(inferred)} semantic relations")

        return inferred

    def detect_table_communities(
        self,
        tables: List[TableModel],
        relations: List[TableRelationModel]
    ) -> Dict[str, List[str]]:
        """
        Detect table communities based on relationship density.

        Args:
            tables: List of table models
            relations: List of table relations

        Returns:
            Dictionary mapping community names to table lists
        """
        communities = {}

        # Build adjacency map
        adjacency = {table.name: set() for table in tables}
        for rel in relations:
            if rel.from_table in adjacency:
                adjacency[rel.from_table].add(rel.to_table)
            if rel.to_table in adjacency:
                adjacency[rel.to_table].add(rel.from_table)

        # Simple community detection using connected components
        visited = set()
        for table_name in adjacency:
            if table_name not in visited:
                component = self._dfs_component(table_name, adjacency, visited)
                if len(component) > 1:
                    community_name = f"community_{len(communities) + 1}"
                    communities[community_name] = component

        return communities

    def _dfs_component(
        self,
        start: str,
        adjacency: Dict[str, set],
        visited: set
    ) -> List[str]:
        """
        DFS to find connected component.

        Args:
            start: Starting table name
            adjacency: Adjacency map
            visited: Set of visited nodes

        Returns:
            List of table names in the component
        """
        component = []
        stack = [start]

        while stack:
            node = stack.pop()
            if node not in visited:
                visited.add(node)
                component.append(node)
                stack.extend(adjacency.get(node, set()) - visited)

        return component
