"""
SQL query templates for database operations.
"""
from typing import List, Dict, Any, Optional, Tuple
from collections import OrderedDict
from .connection import ConnectionManager


class QueryManager:
    """Manages SQL query execution for the application."""

    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize the query manager.

        Args:
            connection_manager: Database connection manager instance
        """
        self.db = connection_manager

    def get_instance_info(self, prod_inst_id: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Query prod_inst table for instance information.

        Args:
            prod_inst_id: The product instance ID to query

        Returns:
            Tuple of (list of dictionaries containing instance information, SQL query)
        """
        sql = """
            SELECT t.remark, t.OWNER_CUST_ID, t.BELONG_ORG, t.EXT_PROD_INST_ID, t.cycle_type,
                   t.acct_id, t.PROD_NAME, t.prod_Id, t.BILL_TYPE, t.STOP_RENT_DATE,
                   t.BEGIN_RENT_CD, t.STOP_RENT_CD, t.Z_ORG_ID, t.Z_LAN_ID, t.A_ORG_ID,
                   t.A_LAN_ID, t.NET_NBR, t.*
            FROM prod_inst t
            WHERE prod_inst_id = %s
        """
        results = self.db.execute_query(sql, (prod_inst_id,))
        return results, sql.strip()

    def get_change_log(self, prod_inst_id: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Query prod_inst_log table for change logs.

        Args:
            prod_inst_id: The product instance ID to query

        Returns:
            Tuple of (list of dictionaries containing change log records, SQL query)
        """
        sql = """
            SELECT PROD_INST_ID, BEGIN_DATE, INPUT_DATE, ATTR_ID, ATTR_NAME,
                   MOD_BEFORE, MOD_AFTER, MOD_BEFORE_VAL, MOD_AFTER_VAL, MOD_DATE, MOD_REASON
            FROM prod_inst_log
            WHERE prod_inst_id = %s
            ORDER BY AUD_DATE DESC
        """
        results = self.db.execute_query(sql, (prod_inst_id,))
        return results, sql.strip()

    def get_change_record(self, prod_inst_id: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Query cal_acct_record table with JOIN to acct_item_type.

        Args:
            prod_inst_id: The product instance ID to query

        Returns:
            Tuple of (list of dictionaries containing change records, SQL query)
        """
        sql = """
            SELECT a.ACCT_ITEM_TYPE_ID, a.ID, a.PROD_INST_ID, b.NAME, a.START_DATE,
                   a.END_DATE, a.START_FLAG, a.LATEST_FLAG, a.LOOP_MONEY,
                   a.CAL_ACCT_RECORD_ID, a.ACCT_ID, a.CREATE_DATE, a.UPDATE_DATE
            FROM cal_acct_record a
            LEFT JOIN acct_item_type b ON a.ACCT_ITEM_TYPE_ID = b.ACCT_ITEM_TYPE_ID
            WHERE a.PROD_INST_ID = %s
            ORDER BY a.ACCT_ITEM_TYPE_ID DESC, a.START_DATE ASC
        """
        results = self.db.execute_query(sql, (prod_inst_id,))

        # Define the desired column order
        column_order = [
            'ACCT_ITEM_TYPE_ID', 'ID', 'PROD_INST_ID', 'NAME', 'START_DATE',
            'END_DATE', 'START_FLAG', 'LATEST_FLAG', 'LOOP_MONEY',
            'CAL_ACCT_RECORD_ID', 'ACCT_ID', 'CREATE_DATE', 'UPDATE_DATE'
        ]

        # Reorder each row's columns using OrderedDict
        ordered_results = []
        for row in results:
            ordered_row = OrderedDict()
            for col in column_order:
                if col in row:
                    ordered_row[col] = row[col]
            ordered_results.append(ordered_row)

        return ordered_results, sql.strip()

    def validate_change_record(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate change record data against three rules:
        1. Uniqueness: For each (ACCT_ITEM_TYPE_ID, PROD_INST_ID), only ONE row can have START_FLAG = 1
        2. Continuity: Adjacent rows (sorted by START_DATE) must satisfy: next.START_DATE = previous.END_DATE
        3. Latest Flag: If any row has NULL END_DATE, that row MUST have LATEST_FLAG = 1;
                        otherwise, the row with MAX END_DATE MUST have LATEST_FLAG = 1

        Args:
            data: List of change record dictionaries

        Returns:
            Dictionary with 'invalid_groups' (list of group keys) and 'summary' text
        """
        from collections import defaultdict
        from datetime import datetime
        from decimal import Decimal

        def to_int(value):
            """Convert Decimal or other numeric types to int."""
            if value is None or value == '':
                return None
            if isinstance(value, Decimal):
                return int(value)
            return int(value)

        # Group data by (ACCT_ITEM_TYPE_ID, PROD_INST_ID)
        groups = defaultdict(list)
        for row in data:
            key = (row.get('ACCT_ITEM_TYPE_ID'), row.get('PROD_INST_ID'))
            groups[key].append(row)

        invalid_groups = set()

        for group_key, rows in groups.items():
            if len(rows) == 0:
                continue

            # Sort rows by START_DATE
            sorted_rows = sorted(rows, key=lambda r: r.get('START_DATE') or '')

            # Rule 1: Uniqueness - only ONE row can have START_FLAG = 1
            start_flag_count = 0
            for r in rows:
                flag = r.get('START_FLAG')
                if flag is not None and to_int(flag) == 1:
                    start_flag_count += 1

            if start_flag_count != 1:
                invalid_groups.add(group_key)
                continue

            # Rule 2: Continuity - adjacent rows must have matching END_DATE and START_DATE
            continuity_violated = False
            for i in range(len(sorted_rows) - 1):
                current_end = sorted_rows[i].get('END_DATE')
                next_start = sorted_rows[i + 1].get('START_DATE')

                # Skip validation if either date is None (gap is allowed with null dates)
                if current_end is None or next_start is None:
                    continue

                # Parse dates if they're strings
                if isinstance(current_end, str):
                    try:
                        current_end = datetime.strptime(current_end, '%Y-%m-%d:%H:%M:%S')
                    except ValueError:
                        try:
                            current_end = datetime.strptime(current_end, '%Y-%m-%d')
                        except ValueError:
                            continuity_violated = True
                            break

                if isinstance(next_start, str):
                    try:
                        next_start = datetime.strptime(next_start, '%Y-%m-%d:%H:%M:%S')
                    except ValueError:
                        try:
                            next_start = datetime.strptime(next_start, '%Y-%m-%d')
                        except ValueError:
                            continuity_violated = True
                            break

                if current_end != next_start:
                    continuity_violated = True
                    break

            if continuity_violated:
                invalid_groups.add(group_key)
                continue

            # Rule 3: Latest Flag validation
            null_end_date_rows = [r for r in rows if r.get('END_DATE') is None]

            if null_end_date_rows:
                # If any row has NULL END_DATE, that row MUST have LATEST_FLAG = 1
                all_have_flag = True
                for r in null_end_date_rows:
                    flag = r.get('LATEST_FLAG')
                    if flag is None or to_int(flag) != 1:
                        all_have_flag = False
                        break
                if not all_have_flag:
                    invalid_groups.add(group_key)
                    continue
            else:
                # Otherwise, the row with MAX END_DATE MUST have LATEST_FLAG = 1
                max_end_date = None
                for r in rows:
                    end_date = r.get('END_DATE')
                    if max_end_date is None or (end_date is not None and end_date > max_end_date):
                        max_end_date = end_date

                latest_flag_correct = False
                for r in rows:
                    if r.get('END_DATE') == max_end_date:
                        flag = r.get('LATEST_FLAG')
                        if flag is not None and to_int(flag) == 1:
                            latest_flag_correct = True
                            break

                if not latest_flag_correct:
                    invalid_groups.add(group_key)
                    continue

        # Create formatted keys for frontend (e.g., "11907111_114453109")
        invalid_group_keys = [f"{acct}_{prod}" for acct, prod in invalid_groups]

        return {
            'invalid_groups': invalid_group_keys,
            'summary': f"{len(invalid_groups)} group(s) violate validation rules"
        }

    def get_all_queries(self, prod_inst_id: str) -> Dict[str, Any]:
        """
        Execute all three queries for a given PROD_INST_ID.

        Args:
            prod_inst_id: The product instance ID to query

        Returns:
            Dictionary with keys 'instance_info', 'change_log', 'change_record' and their SQL
        """
        instance_info, instance_sql = self.get_instance_info(prod_inst_id)
        change_log, change_log_sql = self.get_change_log(prod_inst_id)
        change_record, change_record_sql = self.get_change_record(prod_inst_id)

        return {
            'instance_info': instance_info,
            'change_log': change_log,
            'change_record': change_record,
            'sql': {
                'instance_info': instance_sql,
                'change_log': change_log_sql,
                'change_record': change_record_sql
            }
        }
