"""
Pytest Configuration and Fixtures

Provides common fixtures for testing the langchain_chatbi agents.
"""

import os
import sys
import pytest
import tempfile
import sqlite3
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, MagicMock

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env file for environment variables (LLM_API_KEY, etc.)
load_dotenv()


# ============================================================================
# Mock LLM Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response for testing."""

    async def _mock_response(text: str):
        response = Mock(spec=AIMessage)
        response.content = text
        return response

    return _mock_response


@pytest.fixture
def mock_llm_stream():
    """Create a mock LLM streaming response for testing."""

    async def _mock_stream(text: str):
        words = text.split()
        for word in words:
            chunk = Mock()
            chunk.content = word + " "
            yield chunk

    return _mock_stream


@pytest.fixture
def mock_llm():
    """Create a mock LangChain LLM for testing."""
    llm = Mock(spec=ChatOpenAI)

    # Mock ainvoke
    async def _ainvoke(messages, config=None):
        # Return a simple response based on the last message content
        if hasattr(messages, '__iter__'):
            last_msg = list(messages)[-1] if messages else None
            content = last_msg.content if hasattr(last_msg, 'content') else str(messages)
        else:
            content = str(messages)

        response = Mock(spec=AIMessage)
        response.content = f"Mock response to: {content[:50]}..."
        return response

    llm.ainvoke = AsyncMock(side_effect=_ainvoke)

    # Mock astream
    async def _astream(messages, config=None):
        words = ["Mock", "streaming", "response"]
        for word in words:
            chunk = Mock()
            chunk.content = word + " "
            yield chunk

    llm.astream = AsyncMock(side_effect=_astream)

    return llm


@pytest.fixture
def langchain_llm():
    """Create a real LangChain ChatOpenAI instance for integration tests.

    This requires LLM_API_KEY environment variable to be set.
    """
    from langchain_chatbi.llm.langchain_llm import create_langchain_llm

    # Skip if no API key
    if not os.getenv("LLM_API_KEY"):
        pytest.skip("LLM_API_KEY not set")

    return create_langchain_llm()


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_table_schemas() -> List[Dict[str, Any]]:
    """Sample table schemas for testing."""
    return [
        {
            "name": "orders",
            "columns": [
                {"name": "id", "type": "INTEGER"},
                {"name": "customer_id", "type": "INTEGER"},
                {"name": "total_amount", "type": "REAL"},
                {"name": "order_date", "type": "TIMESTAMP"}
            ]
        },
        {
            "name": "products",
            "columns": [
                {"name": "id", "type": "INTEGER"},
                {"name": "name", "type": "VARCHAR"},
                {"name": "category", "type": "VARCHAR"},
                {"name": "price", "type": "REAL"}
            ]
        }
    ]


@pytest.fixture
def sample_query_results() -> List[Dict[str, Any]]:
    """Sample query results for testing."""
    return [
        {"product": "Product A", "sales": 125000},
        {"product": "Product B", "sales": 98000},
        {"product": "Product C", "sales": 86000},
        {"product": "Product D", "sales": 62000},
        {"product": "Product E", "sales": 55000},
    ]


@pytest.fixture
def sample_db():
    """Create an in-memory SQLite database for testing."""
    # Create a temporary database file
    db_path = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(db_path)

    # Create test tables
    conn.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            total_amount REAL,
            order_date TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            price REAL
        )
    """)

    # Insert test data
    conn.execute("""
        INSERT INTO orders VALUES
        (1, 1, 100.0, '2023-01-01'),
        (2, 2, 200.0, '2023-01-02'),
        (3, 1, 150.0, '2023-01-03')
    """)

    conn.execute("""
        INSERT INTO products VALUES
        (1, 'Product A', 'Electronics', 100.0),
        (2, 'Product B', 'Books', 20.0),
        (3, 'Product C', 'Electronics', 150.0)
    """)

    conn.commit()
    conn.close()

    # Create a mock database object with run method
    class MockDB:
        def __init__(self, db_path):
            self.db_path = db_path
            self.conn = sqlite3.connect(db_path)

        def run(self, sql, fetch="all"):
            cursor = self.conn.cursor()
            cursor.execute(sql)
            if fetch == "all":
                results = cursor.fetchall()
                # Convert to list of dicts
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in results]
            return cursor.fetchall()

    yield MockDB(db_path)

    # Cleanup
    os.unlink(db_path)


# ============================================================================
# Graph Config Fixtures
# ============================================================================


@pytest.fixture
def graph_config(mock_llm, sample_table_schemas, sample_db):
    """Create configuration for graph execution."""
    return {
        "configurable": {
            "llm": mock_llm,
            "db": sample_db,
            "table_schemas": sample_table_schemas
        }
    }


@pytest.fixture
def initial_state():
    """Create initial state for graph execution."""
    return {
        "question": "What are the top 5 products by sales?",
        "session_id": "test-session-123",
        "language": "zh-CN",
        "messages": [HumanMessage(content="What are the top 5 products by sales?")],
        "sql_retry_count": 0,
        "should_stop": False
    }


# ============================================================================
# MDL Context Fixtures
# ============================================================================


@pytest.fixture
def sample_mdl_context() -> str:
    """Sample MDL context for testing."""
    return """
Available Models:
- Orders: Contains order information (id, customer_id, total_amount, order_date)
- Products: Contains product information (id, name, category, price)

Measures available:
- Orders.total_amount (sum, avg)
- Products.price (sum, avg)

Dimensions available:
- Orders.customer_id
- Products.name
- Products.category
- Time dimensions: Orders.order_date (day, month, year)
"""


@pytest.fixture
def sample_history_queries() -> str:
    """Sample historical queries for testing."""
    return """
Similar queries:
- "Show me top 10 products by revenue" → SELECT name, SUM(price) FROM products GROUP BY name ORDER BY price DESC LIMIT 10
- "What's the total sales by month?" → SELECT DATE_TRUNC('month', order_date), SUM(total_amount) FROM orders GROUP BY 1
"""
