#!/usr/bin/env python3
"""
Initialize the knowledge graph from data sources.

This script extracts table structures and relationships from MySQL
or static configuration and builds the Neo4j knowledge graph.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from loguru import logger

from src.langchain_graph_rag.utils.logger import setup_logger
from src.langchain_graph_rag.extractors.mysql_extractor import MySQLExtractor
from src.langchain_graph_rag.extractors.static_extractor import StaticExtractor
from src.langchain_graph_rag.graph.neo4j_store import Neo4jGraphStore
from src.langchain_graph_rag.graph.builder import GraphBuilder
from src.langchain_graph_rag.config import load_config


async def main():
    """Main initialization function."""
    # Load environment variables
    load_dotenv()

    # Setup logger
    setup_logger(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file=os.getenv('LOG_FILE', 'logs/init_graph.log')
    )

    logger.info("Starting graph initialization...")

    # Load configuration
    config = load_config()

    # Get Neo4j configuration
    neo4j_config = config.get('graph', {}).get('storage', {}).get('neo4j', {})
    neo4j_uri = neo4j_config.get('uri', os.getenv('NEO4J_URI', 'bolt://localhost:7687'))
    neo4j_user = neo4j_config.get('user', os.getenv('NEO4J_USER', 'neo4j'))
    neo4j_password = neo4j_config.get('password', os.getenv('NEO4J_PASSWORD', ''))

    if not neo4j_password:
        logger.error("Neo4j password not configured. Set NEO4J_PASSWORD environment variable.")
        return 1

    # Initialize graph store
    graph_store = Neo4jGraphStore(
        uri=neo4j_uri,
        user=neo4j_user,
        password=neo4j_password
    )

    await graph_store.initialize()
    logger.info("Connected to Neo4j")

    # Extract data
    data_sources = config.get('data_sources', {})
    merge_strategy = data_sources.get('merge_strategy', 'merge')

    tables = []
    relations = []

    # Try MySQL extraction
    mysql_sources = data_sources.get('mysql_sources', [])
    if mysql_sources:
        for mysql_config in mysql_sources:
            logger.info(f"Extracting from MySQL: {mysql_config.get('name')}")
            extractor = MySQLExtractor(
                host=mysql_config.get('host'),
                port=mysql_config.get('port', 3306),
                user=mysql_config.get('user'),
                password=mysql_config.get('password'),
                database=mysql_config.get('database')
            )

            if await extractor.connect():
                try:
                    mysql_tables = await extractor.extract_tables()
                    mysql_relations = await extractor.extract_relations()
                    tables.extend(mysql_tables)
                    relations.extend(mysql_relations)
                    logger.info(f"Extracted {len(mysql_tables)} tables from MySQL")
                finally:
                    await extractor.disconnect()

    # Try static configuration extraction
    if merge_strategy in ['static_only', 'merge', 'static_override']:
        static_config = data_sources.get('static_schema', {})
        if static_config.get('tables') or static_config.get('relations'):
            logger.info("Extracting from static configuration")
            extractor = StaticExtractor()

            if await extractor.connect():
                static_data = await extractor.extract_all()
                static_tables = static_data['tables']
                static_relations = static_data['relations']

                if merge_strategy == 'static_only':
                    tables = static_tables
                    relations = static_relations
                elif merge_strategy == 'merge':
                    # Merge, MySQL takes precedence
                    mysql_table_names = {t.name for t in tables}
                    for static_table in static_tables:
                        if static_table.name not in mysql_table_names:
                            tables.append(static_table)
                    # Merge relations
                    existing_keys = {(r.from_table, r.from_column, r.to_table, r.to_column) for r in relations}
                    for rel in static_relations:
                        key = (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
                        if key not in existing_keys:
                            relations.append(rel)
                elif merge_strategy == 'static_override':
                    # Merge, static config takes precedence
                    static_table_names = {t.name for t in static_tables}
                    tables = [t for t in tables if t.name not in static_table_names]
                    tables.extend(static_tables)

                    # Override relations
                    existing_keys = {(r.from_table, r.from_column, r.to_table, r.to_column) for r in relations}
                    for rel in static_relations:
                        key = (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
                        if key in existing_keys:
                            # Remove existing relation
                            relations = [r for r in relations if not (
                                r.from_table == rel.from_table and
                                r.from_column == rel.from_column and
                                r.to_table == rel.to_table and
                                r.to_column == rel.to_column
                            )]
                        relations.append(rel)

    # Build graph
    logger.info(f"Building graph with {len(tables)} tables and {len(relations)} relations")

    builder_config = config.get('graph', {})
    builder = GraphBuilder(graph_store=graph_store, config=builder_config)

    result = await builder.build_graph(
        tables=tables,
        relations=relations,
        clear_existing=True
    )

    if result.success:
        logger.info(f"Graph built successfully!")
        logger.info(f"  Nodes created: {result.nodes_created}")
        logger.info(f"  Edges created: {result.edges_created}")
        logger.info(f"  Build time: {result.build_time_ms:.2f}ms")
        return 0
    else:
        logger.error(f"Graph build failed: {result.error_message}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
