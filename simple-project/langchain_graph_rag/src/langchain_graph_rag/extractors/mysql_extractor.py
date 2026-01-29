"""
MySQL metadata extractor.

Extracts table structures and relationships from MySQL INFORMATION_SCHEMA.
"""

import re
from typing import List, Dict, Any, Optional
import pymysql
from loguru import logger
from .base_extractor import BaseExtractor
from ..models.table_models import TableModel, ColumnModel, TableRelationModel


class MySQLExtractor(BaseExtractor):
    """
    MySQL database metadata extractor.

    Extracts table structures, columns, and foreign key relationships
    from MySQL's INFORMATION_SCHEMA.
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        charset: str = "utf8mb4",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize MySQL extractor.

        Args:
            host: MySQL host
            port: MySQL port
            user: MySQL user
            password: MySQL password
            database: Database name to extract
            charset: Connection charset (default: utf8mb4)
            config: Optional additional configuration
        """
        super().__init__(name="mysql_extractor", config=config)
        self.host = host
        self.port = int(port) if isinstance(port, str) else port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self._connection: Optional[pymysql.connections.Connection] = None

    async def connect(self) -> bool:
        """
        Establish MySQL database connection.

        Returns:
            True if connection successful, False otherwise
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
            logger.info(f"Connected to MySQL: {self.host}:{self.port}/{self.database}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            return False

    async def disconnect(self) -> None:
        """Close MySQL connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Disconnected from MySQL")

    async def validate_connection(self) -> bool:
        """
        Validate MySQL connection.

        Returns:
            True if connection is valid, False otherwise
        """
        if not self._connection:
            return await self.connect()

        try:
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return False

    async def extract_tables(self) -> List[TableModel]:
        """
        Extract all tables from the database.

        Returns:
            List of TableModel objects
        """
        if not self._connection:
            await self.connect()

        tables = []

        # SQL queries for metadata
        tables_sql = """
            SELECT
                TABLE_NAME,
                TABLE_COMMENT,
                TABLE_ROWS,
                TABLE_SCHEMA
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """

        columns_sql = """
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                IS_NULLABLE,
                COLUMN_KEY,
                COLUMN_DEFAULT,
                COLUMN_COMMENT,
                ORDINAL_POSITION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """

        primary_keys_sql = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = %s
                AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
        """

        try:
            with self._connection.cursor() as cursor:
                # Get all tables
                cursor.execute(tables_sql, (self.database,))
                table_rows = cursor.fetchall()

                for table_row in table_rows:
                    table_name = table_row['TABLE_NAME']

                    # Get columns
                    cursor.execute(columns_sql, (self.database, table_name))
                    column_rows = cursor.fetchall()

                    columns = []
                    for col_row in column_rows:
                        # Build column type string
                        col_type = col_row['DATA_TYPE']
                        if col_row['CHARACTER_MAXIMUM_LENGTH']:
                            col_type += f"({col_row['CHARACTER_MAXIMUM_LENGTH']})"

                        column = ColumnModel(
                            name=col_row['COLUMN_NAME'],
                            type=col_type,
                            nullable=col_row['IS_NULLABLE'] == 'YES',
                            primary_key=col_row['COLUMN_KEY'] == 'PRI',
                            comment=col_row['COLUMN_COMMENT'] or '',
                            max_length=col_row['CHARACTER_MAXIMUM_LENGTH']
                        )
                        columns.append(column)

                    # Get primary keys
                    cursor.execute(primary_keys_sql, (self.database, table_name))
                    pk_rows = cursor.fetchall()
                    primary_keys = [row['COLUMN_NAME'] for row in pk_rows]

                    # Get foreign keys (extracted separately)
                    foreign_keys = await self._get_foreign_keys_for_table(table_name)

                    table = TableModel(
                        name=table_name,
                        database=table_row['TABLE_SCHEMA'],
                        columns=columns,
                        primary_keys=primary_keys,
                        foreign_keys=foreign_keys,
                        row_count=table_row['TABLE_ROWS'],
                        comment=table_row['TABLE_COMMENT'] or '',
                        graph_node_id=f"table:{self.database}.{table_name}"
                    )

                    tables.append(table)

            logger.info(f"Extracted {len(tables)} tables from {self.database}")
            return tables

        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
            raise

    async def _get_foreign_keys_for_table(self, table_name: str) -> List[Dict[str, str]]:
        """
        Get foreign key information for a specific table.

        Args:
            table_name: Table name

        Returns:
            List of foreign key dictionaries
        """
        fk_sql = """
            SELECT
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = %s
                AND REFERENCED_TABLE_NAME IS NOT NULL
        """

        foreign_keys = []
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(fk_sql, (self.database, table_name))
                fk_rows = cursor.fetchall()

                for fk_row in fk_rows:
                    foreign_keys.append({
                        "column": fk_row['COLUMN_NAME'],
                        "ref_table": fk_row['REFERENCED_TABLE_NAME'],
                        "ref_column": fk_row['REFERENCED_COLUMN_NAME']
                    })

        except Exception as e:
            logger.warning(f"Error getting foreign keys for {table_name}: {e}")

        return foreign_keys

    async def extract_relations(self) -> List[TableRelationModel]:
        """
        Extract all table relationships from the database.

        Returns:
            List of TableRelationModel objects
        """
        if not self._connection:
            await self.connect()

        relations = []

        # Extract foreign key relations
        fk_sql = """
            SELECT
                TABLE_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
                AND REFERENCED_TABLE_NAME IS NOT NULL
        """

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(fk_sql, (self.database,))
                fk_rows = cursor.fetchall()

                for fk_row in fk_rows:
                    relation = TableRelationModel(
                        from_table=fk_row['TABLE_NAME'],
                        from_column=fk_row['COLUMN_NAME'],
                        to_table=fk_row['REFERENCED_TABLE_NAME'],
                        to_column=fk_row['REFERENCED_COLUMN_NAME'],
                        relation_type="foreign_key",
                        join_type="INNER",
                        cardinality="N:1",
                        confidence=1.0,
                        graph_edge_id=f"edge:{fk_row['TABLE_NAME']}.{fk_row['COLUMN_NAME']}->{fk_row['REFERENCED_TABLE_NAME']}.{fk_row['REFERENCED_COLUMN_NAME']}"
                    )
                    relations.append(relation)

            # Infer additional relations based on naming patterns
            inferred_relations = await self._infer_join_relations(relations)
            relations.extend(inferred_relations)

            logger.info(f"Extracted {len(relations)} relations from {self.database}")
            return relations

        except Exception as e:
            logger.error(f"Error extracting relations: {e}")
            raise

    async def _infer_join_relations(
        self,
        existing_relations: List[TableRelationModel]
    ) -> List[TableRelationModel]:
        """
        Infer additional JOIN relations based on column naming patterns.

        Args:
            existing_relations: Already extracted foreign key relations

        Returns:
            List of inferred TableRelationModel objects
        """
        inferred = []
        exclude_patterns = self.get_config("exclude_patterns", ["created_by", "updated_by", "deleted_by"])

        # Get all tables to check for potential relations
        tables = await self.extract_tables()
        table_names = {t.name for t in tables}

        for table in tables:
            for column in table.columns:
                # Skip primary keys and already defined foreign keys
                if column.primary_key or column.foreign_key:
                    continue

                # Check if column matches pattern: {table}_id
                match = re.match(r'^(.+)_id$', column.name.lower())
                if not match:
                    continue

                potential_ref_table = match.group(1)

                # Check if referenced table exists
                if potential_ref_table not in table_names:
                    continue

                # Skip if relation already exists
                if any(
                    r.from_table == table.name and r.from_column == column.name
                    for r in existing_relations
                ):
                    continue

                # Skip excluded patterns
                if any(pattern in column.name.lower() for pattern in exclude_patterns):
                    continue

                # Create inferred relation
                inferred.append(TableRelationModel(
                    from_table=table.name,
                    from_column=column.name,
                    to_table=potential_ref_table,
                    to_column="id",  # Assume primary key is 'id'
                    relation_type="join",
                    join_type="INNER",
                    cardinality="N:1",
                    confidence=0.7,  # Lower confidence for inferred relations
                    graph_edge_id=f"edge:{table.name}.{column.name}->{potential_ref_table}.id"
                ))

        if inferred:
            logger.info(f"Inferred {len(inferred)} additional relations")

        return inferred
