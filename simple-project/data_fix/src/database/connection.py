"""
Database connection manager for MySQL.
"""
import os
import json
import pymysql
from typing import Optional, Dict, Any


class ConnectionManager:
    """Manages MySQL database connections."""

    def __init__(self, config_path: str = None):
        """
        Initialize the connection manager.

        Args:
            config_path: Path to the config.json file. Defaults to ./config.json
        """
        if config_path is None:
            # Get the directory of this file and navigate to project root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            config_path = os.path.join(project_root, 'config.json')

        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.connection: Optional[pymysql.connections.Connection] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from config.json file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            # Create default config if file doesn't exist
            self.config = {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'database': '',
                'charset': 'utf8mb4'
            }
            self._save_config()
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in config file: {self.config_path}")

    def _save_config(self) -> None:
        """Save configuration to config.json file."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def update_config(self, **kwargs) -> None:
        """
        Update configuration parameters.

        Args:
            **kwargs: Configuration parameters to update (host, port, user, password, database)
        """
        self.config.update(kwargs)
        self._save_config()

    def connect(self) -> pymysql.connections.Connection:
        """
        Establish MySQL connection.

        Returns:
            pymysql.connections.Connection: Active database connection

        Raises:
            pymysql.Error: If connection fails
        """
        if self.connection is not None and self.connection.open:
            return self.connection

        try:
            self.connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset=self.config.get('charset', 'utf8mb4'),
                cursorclass=pymysql.cursors.DictCursor
            )
            return self.connection
        except pymysql.Error as e:
            raise pymysql.Error(f"Failed to connect to database: {e}")

    def disconnect(self) -> None:
        """Close the database connection."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def test_connection(self) -> bool:
        """
        Test if the database connection works.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            conn = self.connect()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception:
            return False

    def execute_query(self, sql: str, params: tuple = None) -> list:
        """
        Execute a SQL query and return results.

        Args:
            sql: SQL query string
            params: Optional parameters for the query

        Returns:
            list: Query results as list of dictionaries
        """
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
