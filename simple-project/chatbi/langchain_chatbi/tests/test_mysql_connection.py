"""
MySQL Database Connection Tests

Tests for MySQL connection and query execution.
Requires .env file with MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE.
"""

import os
import pytest
from langchain_chatbi.db.mysql_db import (
    create_mysql_connection
)


# ============================================================================
# Configuration
# ============================================================================

# Skip tests if MySQL is not configured
pytestmark = [
    pytest.mark.skipif(
        not os.getenv("MYSQL_HOST"),
        reason="MYSQL_HOST not set"
    ),
    pytest.mark.integration
]


# ============================================================================
# Test Class
# ============================================================================

@pytest.mark.integration
class TestMySQLConnection:
    """Integration tests for MySQL connection."""

    # ========================================================================
    # Connection Tests
    # ========================================================================

    def test_create_connection_from_env(self):
        """Test creating connection from environment variables."""
        conn = create_mysql_connection()

        assert conn.host is not None
        assert conn.user is not None
        assert conn.database is not None

    def test_connection_properties(self):
        """Test connection properties."""
        conn = create_mysql_connection()

        assert conn.host == os.getenv("MYSQL_HOST", "localhost")
        assert conn.port == int(os.getenv("MYSQL_PORT", "3306"))
        assert conn.user == os.getenv("MYSQL_USER", "root")
        assert conn.database == os.getenv("MYSQL_DATABASE", "chatbi")

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_connect_to_database(self):
        """Test actual database connection."""
        conn = create_mysql_connection()

        try:
            connection = conn.connect()
            assert connection is not None
            assert connection.open
        finally:
            conn.disconnect()

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_test_connection(self):
        """Test connection test method."""
        conn = create_mysql_connection()

        try:
            result = conn.test_connection()
            assert result is True
        finally:
            conn.disconnect()

    # ========================================================================
    # Query Execution Tests
    # ========================================================================

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_run_simple_select(self):
        """Test simple SELECT query."""
        conn = create_mysql_connection()

        try:
            result = conn.run("SELECT 1 as test_value, 'hello' as message")

            assert isinstance(result, list)
            assert len(result) > 0
            assert result[0]["test_value"] == 1
            assert result[0]["message"] == "hello"
        finally:
            conn.disconnect()

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_run_select_with_parameters(self):
        """Test SELECT query with parameters."""
        conn = create_mysql_connection()

        try:
            result = conn.run(
                "SELECT %s as value, %s as name",
                (42, "test")
            )

            assert isinstance(result, list)
            assert len(result) > 0
            assert result[0]["value"] == 42
            assert result[0]["name"] == "test"
        finally:
            conn.disconnect()

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_run_show_tables(self):
        """Test SHOW TABLES query."""
        conn = create_mysql_connection()

        try:
            result = conn.run("SHOW TABLES")

            assert isinstance(result, list)
            # Result structure depends on MySQL version
            # May have key like 'Tables_in_chatbi' or similar
        finally:
            conn.disconnect()

    # ========================================================================
    # Schema Information Tests
    # ========================================================================

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_get_all_tables(self):
        """Test getting all tables."""
        conn = create_mysql_connection()

        try:
            tables = conn.get_all_tables()

            assert isinstance(tables, list)
            # At minimum, should be a list
        finally:
            conn.disconnect()

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_get_table_schema_nonexistent(self):
        """Test getting schema for non-existent table."""
        conn = create_mysql_connection()

        try:
            # Should return empty columns for non-existent table
            schema = conn.get_table_schema("nonexistent_table_xyz")

            assert isinstance(schema, dict)
            assert schema["name"] == "nonexistent_table_xyz"
            assert isinstance(schema["columns"], list)
        finally:
            conn.disconnect()

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_get_all_schemas(self):
        """Test getting all table schemas."""
        conn = create_mysql_connection()

        try:
            schemas = conn.get_all_schemas()

            assert isinstance(schemas, list)
            for schema in schemas:
                assert "name" in schema
                assert "columns" in schema
                assert isinstance(schema["columns"], list)
        finally:
            conn.disconnect()

    # ========================================================================
    # Context Manager Tests
    # ========================================================================

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_cursor_context_manager(self):
        """Test cursor context manager."""
        conn = create_mysql_connection()

        try:
            with conn.get_cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()

            assert result["test"] == 1
        finally:
            conn.disconnect()

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_invalid_sql_raises_error(self):
        """Test that invalid SQL raises an error."""
        conn = create_mysql_connection()

        try:
            with pytest.raises(Exception):
                conn.run("INVALID SQL QUERY")
        finally:
            conn.disconnect()

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_syntax_error_raises_error(self):
        """Test that SQL syntax error raises an error."""
        conn = create_mysql_connection()

        try:
            with pytest.raises(Exception):
                conn.run("SELEC * FROM nonexistent_table")
        finally:
            conn.disconnect()

    # ========================================================================
    # Connection Reuse Tests
    # ========================================================================

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_connection_property_reuse(self):
        """Test that connection property reuses existing connection."""
        conn = create_mysql_connection()

        try:
            # First access creates connection
            conn1 = conn.connection
            # Second access should reuse
            conn2 = conn.connection

            assert conn1 is conn2
        finally:
            conn.disconnect()

    @pytest.mark.skipif(
        not os.getenv("MYSQL_PASSWORD"),
        reason="MYSQL_PASSWORD not set"
    )
    def test_multiple_queries_same_connection(self):
        """Test multiple queries on the same connection."""
        conn = create_mysql_connection()

        try:
            result1 = conn.run("SELECT 1 as num")
            result2 = conn.run("SELECT 2 as num")
            result3 = conn.run("SELECT 3 as num")

            assert result1[0]["num"] == 1
            assert result2[0]["num"] == 2
            assert result3[0]["num"] == 3
        finally:
            conn.disconnect()
