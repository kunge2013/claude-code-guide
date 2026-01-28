"""
Flask Web Application for LangChain ChatBI

Provides a web interface to visualize agent execution status in real-time.
"""

import asyncio
import os
import json
from datetime import datetime
from typing import Dict, Any, List
from flask import Flask, render_template, jsonify, request, stream_with_context
from loguru import logger

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_chatbi import create_chatbi_graph
from langchain_chatbi.llm import create_langchain_llm
from langchain_chatbi.dictionary import get_dictionary_service

# Load environment variables
from dotenv import load_dotenv
from langchain_chatbi.db.mysql_db import create_mysql_connection

load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = 'chatbi-secret-key'

# Sample data for demo
SAMPLE_TABLE_SCHEMAS = [
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


# Store execution status
execution_status: Dict[str, Any] = {
    "status": "idle",
    "current_node": None,
    "nodes_completed": [],
    "nodes_failed": [],
    "results": {},
    "start_time": None,
    "end_time": None,
}


def reset_status():
    """Reset execution status."""
    global execution_status
    execution_status = {
        "status": "idle",
        "current_node": None,
        "nodes_completed": [],
        "nodes_failed": [],
        "results": {},
        "start_time": None,
        "end_time": None,
    }


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """Get current execution status."""
    return jsonify(execution_status)


@app.route('/api/execute', methods=['POST'])
def execute_query():
    """Execute a query through the workflow."""
    data = request.json
    question = data.get('question', 'Show me the top 5 products by sales')
    language = data.get('language', 'zh-CN')

    # Reset status
    reset_status()
    execution_status['status'] = 'running'
    execution_status['start_time'] = datetime.now().isoformat()
    execution_status['question'] = question

    # Start async execution
    def run_workflow():
        async def run_async():
            try:
                llm = create_langchain_llm()
                graph = create_chatbi_graph()

                # Create MySQL connection
                mysql_conn = None
                table_schemas = SAMPLE_TABLE_SCHEMAS

                try:
                    mysql_conn = create_mysql_connection()
                    # Test connection
                    if mysql_conn.test_connection():
                        logger.info("MySQL connected successfully")
                        # Get real table schemas
                        table_schemas = mysql_conn.get_all_schemas()
                        logger.info(f"Loaded {len(table_schemas)} table schemas")
                    else:
                        logger.warning("MySQL connection failed, falling back to demo mode")
                        mysql_conn = None
                except Exception as e:
                    logger.error(f"MySQL initialization error: {e}, falling back to demo mode")
                    mysql_conn = None

                # Initialize dictionary service
                dictionary_service = None
                try:
                    dictionary_service = get_dictionary_service(
                        config_path="config/dictionary_config.yaml",
                        synonym_path="config/synonym_config.yaml",
                        db_connection=mysql_conn
                    )
                    await dictionary_service.initialize()
                    logger.info("Dictionary service initialized successfully")
                except Exception as e:
                    logger.warning(f"Dictionary service initialization failed: {e}, continuing without dictionary transformation")

                config = {
                    "configurable": {
                        "thread_id": f"thread-{datetime.now().timestamp()}",
                        "db": mysql_conn,  # Pass db via config (not state) to avoid serialization
                        "dictionary_service": dictionary_service  # Pass dictionary service
                    },
                    "callbacks": [],  # No callbacks for web demo
                }

                initial_state = {
                    "question": question,
                    "session_id": f"web-session-{datetime.now().timestamp()}",
                    "language": language,
                    "messages": [],
                    "sql_retry_count": 0,
                    "should_stop": False,
                    "table_schemas": table_schemas
                }

                # Run async workflow
                event_count = 0
                async for event in graph.astream(initial_state, config=config):
                    for node_name, node_output in event.items():
                        if node_name != "__end__":
                            event_count += 1
                            execution_status['current_node'] = node_name

                            # Extract node results - handle None output
                            node_result = {
                                "timestamp": datetime.now().isoformat(),
                                "node": node_name,
                                "status": "completed"
                            }

                            # Skip processing if node_output is None
                            if node_output is None:
                                execution_status['nodes_completed'].append(node_result)
                                execution_status['results'][node_name] = node_result
                                continue

                            # Extract key information
                            # Dictionary transformation info
                            if "original_question" in node_output and node_output["original_question"]:
                                node_result["original_question"] = node_output["original_question"]

                            if "transformed_question" in node_output and node_output["transformed_question"]:
                                node_result["transformed_question"] = node_output["transformed_question"]

                            if "dictionary_transformations" in node_output and node_output["dictionary_transformations"]:
                                node_result["dictionary_transformations"] = node_output["dictionary_transformations"]

                            if "intent" in node_output and node_output["intent"]:
                                node_result["intent"] = node_output["intent"]

                            if "reasoning" in node_output and node_output["reasoning"]:
                                node_result["reasoning"] = node_output["reasoning"][:200] + "..."

                            if "generated_sql" in node_output and node_output["generated_sql"]:
                                node_result["sql"] = node_output["generated_sql"]

                            if "query_result" in node_output:
                                if node_output["query_result"]:
                                    node_result["result_count"] = len(node_output["query_result"])
                                    node_result["result_preview"] = node_output["query_result"][:3]
                                    node_result["query_result"] = node_output["query_result"]
                                elif node_output.get("sql_error"):
                                    node_result["status"] = "failed"
                                    node_result["error"] = node_output["sql_error"]
                                    execution_status['nodes_failed'].append(node_name)

                            if "chart_config" in node_output and node_output["chart_config"]:
                                chart_config = node_output["chart_config"]
                                # Handle Pydantic model dict conversion
                                if hasattr(chart_config, 'model_dump'):
                                    chart_config = chart_config.model_dump()
                                elif hasattr(chart_config, 'dict'):
                                    chart_config = chart_config.dict()
                                node_result["chart_config"] = chart_config
                                node_result["chart_type"] = chart_config.get("chartType")

                            if "answer" in node_output and node_output["answer"]:
                                node_result["answer"] = node_output["answer"][:300] + "..."

                            # 数据库类型判断
                            if "dbtype" in node_output and node_output["dbtype"]:
                                node_result["dbtype"] = node_output["dbtype"]

                            execution_status['nodes_completed'].append(node_result)
                            execution_status['results'][node_name] = node_result

                execution_status['status'] = 'completed'
                execution_status['current_node'] = None
                execution_status['end_time'] = datetime.now().isoformat()
                execution_status['total_events'] = event_count

            except Exception as e:
                execution_status['status'] = 'failed'
                execution_status['error'] = str(e)
                execution_status['end_time'] = datetime.now().isoformat()
                logger.error(f"Workflow execution failed: {e}")

            finally:
                # Cleanup database connection
                if mysql_conn:
                    try:
                        mysql_conn.disconnect()
                        logger.info("MySQL connection closed")
                    except Exception as e:
                        logger.error(f"Error closing MySQL connection: {e}")

        asyncio.run(run_async())

    # Run in background thread
    import threading
    thread = threading.Thread(target=run_workflow)
    thread.start()

    return jsonify({"status": "started"})


@app.route('/api/stream')
def stream_status():
    """SSE stream for real-time status updates."""
    def generate():
        last_update = ""
        while True:
            current_status = json.dumps(execution_status)
            if current_status != last_update:
                yield f"data: {current_status}\n\n"
                last_update = current_status

            # If completed, stop streaming after a delay
            if execution_status['status'] in ['completed', 'failed']:
                import time
                time.sleep(1)
                break

            import time
            time.sleep(0.5)

    return app.response_class(
        stream_with_context(generate()),
        mimetype='text/event-stream'
    )


@app.route('/api/reset', methods=['POST'])
def reset_execution():
    """Reset execution status."""
    reset_status()
    return jsonify({"status": "reset"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
