"""
Pytest configuration and fixtures.
"""

import pytest
import asyncio
from typing import AsyncGenerator


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_tables():
    """Sample table data for testing."""
    from src.langchain_graph_rag.models.table_models import TableModel, ColumnModel

    return [
        TableModel(
            name="orders",
            database="test_db",
            columns=[
                ColumnModel(name="id", type="int", primary_key=True),
                ColumnModel(name="customer_id", type="int"),
                ColumnModel(name="order_date", type="datetime")
            ],
            primary_keys=["id"],
            foreign_keys=[
                {"column": "customer_id", "ref_table": "customers", "ref_column": "id"}
            ],
            graph_node_id="table:test_db.orders"
        ),
        TableModel(
            name="customers",
            database="test_db",
            columns=[
                ColumnModel(name="id", type="int", primary_key=True),
                ColumnModel(name="name", type="varchar"),
                ColumnModel(name="email", type="varchar")
            ],
            primary_keys=["id"],
            foreign_keys=[],
            graph_node_id="table:test_db.customers"
        )
    ]


@pytest.fixture
def sample_relations():
    """Sample relation data for testing."""
    from src.langchain_graph_rag.models.table_models import TableRelationModel

    return [
        TableRelationModel(
            from_table="orders",
            from_column="customer_id",
            to_table="customers",
            to_column="id",
            relation_type="foreign_key",
            join_type="INNER",
            cardinality="N:1",
            confidence=1.0
        )
    ]
