"""
MySQL Execution Demo

Demonstrates how to use MySQL connection with the ChatBI workflow.
"""

import asyncio
from dotenv import load_dotenv

from langchain_chatbi.db.mysql_db import create_mysql_connection
from langchain_chatbi.graph.state import ChatBIState
from langchain_chatbi.graph.nodes import execution_node

# Load environment variables
load_dotenv()


async def demo_mysql_query_execution():
    """
    Demo: Execute a SQL query against MySQL database.
    """
    print("=" * 60)
    print("MySQL Query Execution Demo")
    print("=" * 60)

    # Create MySQL connection
    print("\n1. Creating MySQL connection...")
    mysql_conn = create_mysql_connection()

    # Test connection
    print("2. Testing connection...")
    try:
        is_connected = mysql_conn.test_connection()
        print(f"   Connection status: {'✓ Connected' if is_connected else '✗ Failed'}")

        if not is_connected:
            print("\n   Please check your MySQL configuration in .env:")
            print("   - MYSQL_HOST")
            print("   - MYSQL_PORT")
            print("   - MYSQL_USER")
            print("   - MYSQL_PASSWORD")
            print("   - MYSQL_DATABASE")
            return
    except Exception as e:
        print(f"   Connection failed: {e}")
        return

    # Get all tables
    print("\n3. Getting database tables...")
    try:
        tables = mysql_conn.get_all_tables()
        print(f"   Found {len(tables)} tables:")
        for table in tables[:5]:  # Show first 5
            print(f"   - {table}")
        if len(tables) > 5:
            print(f"   ... and {len(tables) - 5} more")
    except Exception as e:
        print(f"   Failed to get tables: {e}")

    # Get schema for a table
    if tables:
        print(f"\n4. Getting schema for '{tables[0]}'...")
        try:
            schema = mysql_conn.get_table_schema(tables[0])
            print(f"   Columns:")
            for col in schema["columns"][:5]:  # Show first 5 columns
                print(f"   - {col['name']}: {col['type']}")
            if len(schema["columns"]) > 5:
                print(f"   ... and {len(schema['columns']) - 5} more")
        except Exception as e:
            print(f"   Failed to get schema: {e}")

    # Prepare state for execution_node
    print("\n5. Running execution_node with sample SQL...")
    state: ChatBIState = {
        "question": "Show me the first 5 records",
        "session_id": "demo_session",
        "language": "zh-CN",
        "table_schemas": None,
        "db": mysql_conn,
        "intent": None,
        "ambiguity_info": None,
        "selected_schemas": None,
        "generated_sql": "SELECT 1 as id, 'Sample' as name, 100 as value",
        "sql_error": None,
        "sql_retry_count": 0,
        "reasoning": None,
        "query_result": None,
        "chart_config": None,
        "diagnosis": None,
        "answer": None,
        "mdl_context": None,
        "history_queries": None,
        "error": None,
        "should_stop": False,
        "messages": []
    }

    try:
        result = await execution_node(state)

        print(f"   Query executed successfully!")
        print(f"   Rows returned: {len(result['query_result'])}")
        print(f"   Sample data:")
        for row in result['query_result'][:3]:
            print(f"   - {row}")

    except Exception as e:
        print(f"   Execution failed: {e}")

    finally:
        mysql_conn.disconnect()
        print("\n6. Disconnected from MySQL")


async def demo_workflow_with_mysql():
    """
    Demo: Complete workflow with MySQL database.
    """
    print("\n" + "=" * 60)
    print("Complete Workflow with MySQL Demo")
    print("=" * 60)

    # Create MySQL connection
    print("\n1. Setting up MySQL connection...")
    mysql_conn = create_mysql_connection()

    try:
        is_connected = mysql_conn.test_connection()
        if not is_connected:
            print("   ✗ Cannot connect to MySQL")
            return
        print("   ✓ Connected to MySQL")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return

    # Get table schemas for the database
    print("\n2. Loading table schemas...")
    try:
        schemas = mysql_conn.get_all_schemas()
        print(f"   Loaded {len(schemas)} table schemas")
    except Exception as e:
        print(f"   Failed to load schemas: {e}")
        schemas = []

    # Example state with real MySQL connection
    print("\n3. Preparing workflow state...")

    # Use a real table if available, otherwise use a generic query
    if schemas:
        first_table = schemas[0]["name"]
        sample_sql = f"SELECT * FROM {first_table} LIMIT 5"
    else:
        sample_sql = "SELECT 1 as id, 'Demo' as name"

    state: ChatBIState = {
        "question": "显示前5条数据",
        "session_id": "workflow_demo",
        "language": "zh-CN",
        "table_schemas": schemas,
        "db": mysql_conn,
        "intent": "query",
        "ambiguity_info": None,
        "selected_schemas": schemas[:1] if schemas else None,
        "generated_sql": sample_sql,
        "sql_error": None,
        "sql_retry_count": 0,
        "reasoning": None,
        "query_result": None,
        "chart_config": None,
        "diagnosis": None,
        "answer": None,
        "mdl_context": None,
        "history_queries": None,
        "error": None,
        "should_stop": False,
        "messages": []
    }

    print(f"   Question: {state['question']}")
    print(f"   SQL: {state['generated_sql']}")

    # Execute the query
    print("\n4. Executing query...")
    try:
        result = await execution_node(state)

        if result.get("sql_error"):
            print(f"   ✗ Query failed: {result['sql_error']}")
        else:
            print(f"   ✓ Query succeeded")
            print(f"   Rows returned: {len(result['query_result'])}")

            if result['query_result']:
                print("\n5. Results:")
                # Print header
                columns = list(result['query_result'][0].keys())
                print("   " + " | ".join(columns))

                # Print rows
                for row in result['query_result'][:5]:
                    values = [str(row[col])[:20] for col in columns]
                    print("   " + " | ".join(values))

                if len(result['query_result']) > 5:
                    print(f"   ... and {len(result['query_result']) - 5} more rows")

    except Exception as e:
        print(f"   ✗ Execution failed: {e}")

    finally:
        mysql_conn.disconnect()
        print("\n6. Cleanup completed")


async def demo_query_with_user_input():
    """
    Demo: Interactive query execution with user input.
    """
    print("\n" + "=" * 60)
    print("Interactive Query Demo")
    print("=" * 60)

    # Create connection
    mysql_conn = create_mysql_connection()

    try:
        is_connected = mysql_conn.test_connection()
        if not is_connected:
            print("Cannot connect to MySQL database")
            return

        print("\nConnected to MySQL database")
        print(f"Database: {mysql_conn.database}")

        # Show available tables
        tables = mysql_conn.get_all_tables()
        if tables:
            print(f"\nAvailable tables ({len(tables)}):")
            for i, table in enumerate(tables, 1):
                print(f"  {i}. {table}")

        # Sample queries to try
        sample_queries = [
            f"SELECT COUNT(*) as row_count FROM {tables[0]}" if tables else None,
            "SELECT 1 as test, NOW() as current_time",
            "SELECT VERSION() as mysql_version",
        ]

        print("\nRunning sample queries...")

        for i, sql in enumerate(sample_queries, 1):
            if not sql:
                continue
            print(f"\nQuery {i}: {sql}")
            try:
                result = mysql_conn.run(sql)
                print(f"Result: {result[0] if result else 'No results'}")
            except Exception as e:
                print(f"Error: {e}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        mysql_conn.disconnect()
        print("\nDisconnected")


async def main():
    """Run all demos."""
    try:
        await demo_mysql_query_execution()
        await demo_workflow_with_mysql()
        await demo_query_with_user_input()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
