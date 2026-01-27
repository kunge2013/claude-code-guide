"""
MySQL Database Connection for ChatBI

Provides MySQL database connection and query execution capabilities.
"""

import os
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import pymysql
from loguru import logger


class MySQLConnection:
    """
    MySQL database connection wrapper.

    Handles connection management and query execution for MySQL databases.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        charset: str = "utf8mb4"
    ):
        """
        Initialize MySQL connection.

        Args:
            host: Database host (defaults to MYSQL_HOST env var)
            port: Database port (defaults to MYSQL_PORT env var)
            user: Database user (defaults to MYSQL_USER env var)
            password: Database password (defaults to MYSQL_PASSWORD env var)
            database: Database name (defaults to MYSQL_DATABASE env var)
            charset: Character set (default: utf8mb4)
        """
        self.host = host or os.getenv("MYSQL_HOST", "localhost")
        self.port = port or int(os.getenv("MYSQL_PORT", "3306"))
        self.user = user or os.getenv("MYSQL_USER", "root")
        self.password = password or os.getenv("MYSQL_PASSWORD", "")
        self.database = database or os.getenv("MYSQL_DATABASE", "chatbi")
        self.charset = charset

        self._connection = None

    def connect(self) -> pymysql.Connection:
        """
        Establish database connection.

        Returns:
            pymysql.Connection: Database connection object
        """
        try:
            self._connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=self.charset,
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info(
                f"[MySQL]: Connected to {self.host}:{self.port}/{self.database}"
            )
            return self._connection
        except Exception as e:
            logger.error(f"[MySQL]: Connection failed: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("[MySQL]: Disconnected")

    @property
    def connection(self) -> pymysql.Connection:
        """
        Get or create database connection.

        Returns:
            pymysql.Connection: Active database connection
        """
        if self._connection is None:
            return self.connect()
        return self._connection

    @contextmanager
    def get_cursor(self):
        """
        Context manager for database cursor.

        Yields:
            pymysql.cursors.DictCursor: Database cursor
        """
        conn = self.connection
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def run(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results.

        Args:
            sql: SQL query to execute
            params: Optional query parameters for parameterized queries

        Returns:
            List of dictionaries representing rows
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, params)

                # For SELECT queries, fetch results
                if sql.strip().upper().startswith("SELECT"):
                    result = cursor.fetchall()
                    logger.info(f"[MySQL]: Query returned {len(result)} rows")
                    return result
                else:
                    # For INSERT/UPDATE/DELETE, return affected rows info
                    self.connection.commit()
                    logger.info(f"[MySQL]: Query affected {cursor.rowcount} rows")
                    return [{"affected_rows": cursor.rowcount}]

        except Exception as e:
            logger.error(f"[MySQL]: Query execution failed: {e}")
            # Rollback on error for non-SELECT queries
            if not sql.strip().upper().startswith("SELECT"):
                self.connection.rollback()
            raise

    def run_many(self, sql: str, params_list: List[tuple]) -> List[Dict[str, Any]]:
        """
        Execute SQL query multiple times with different parameters.

        Args:
            sql: SQL query to execute
            params_list: List of parameter tuples

        Returns:
            Summary of execution results
        """
        try:
            with self.get_cursor() as cursor:
                affected = cursor.executemany(sql, params_list)
                self.connection.commit()
                logger.info(f"[MySQL]: Batch execution affected {affected} rows")
                return [{"affected_rows": affected}]

        except Exception as e:
            logger.error(f"[MySQL]: Batch execution failed: {e}")
            self.connection.rollback()
            raise

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get schema information for a specific table.

        Args:
            table_name: Name of the table

        Returns:
            Dictionary with table schema information
        """
        sql = """
            SELECT
                COLUMN_NAME as name,
                DATA_TYPE as type,
                IS_NULLABLE as nullable,
                COLUMN_KEY as column_key,
                COLUMN_DEFAULT as default_value,
                COLUMN_COMMENT as comment
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """

        result = self.run(sql, (self.database, table_name))

        return {
            "name": table_name,
            "columns": [
                {
                    "name": col["name"],
                    "type": col["type"],
                    "nullable": col["nullable"] == "YES",
                    "primary_key": col["column_key"] == "PRI",
                    "default": col["default_value"],
                    "comment": col["comment"]
                }
                for col in result
            ]
        }

    def get_all_tables(self) -> List[str]:
        """
        Get list of all tables in the database.

        Returns:
            List of table names
        """
        sql = """
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME
        """

        result = self.run(sql, (self.database,))
        return [row["TABLE_NAME"] for row in result]

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """
        Get schema information for all tables in the database.

        Returns:
            List of table schema dictionaries
        """
        tables = self.get_all_tables()
        return [self.get_table_schema(table) for table in tables]

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            result = self.run("SELECT 1 as test")
            return len(result) > 0 and result[0]["test"] == 1
        except Exception as e:
            logger.error(f"[MySQL]: Connection test failed: {e}")
            return False


def create_mysql_connection(
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None
) -> MySQLConnection:
    """
    Create a MySQL connection instance.

    Reads configuration from environment variables if not provided.

    Environment Variables:
        MYSQL_HOST: Database host (default: localhost)
        MYSQL_PORT: Database port (default: 3306)
        MYSQL_USER: Database user (default: root)
        MYSQL_PASSWORD: Database password
        MYSQL_DATABASE: Database name (default: chatbi)

    Args:
        host: Database host
        port: Database port
        user: Database user
        password: Database password
        database: Database name

    Returns:
        MySQLConnection: Configured MySQL connection instance
    """
    return MySQLConnection(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )
