#!/usr/bin/env python3
"""
Interactive Demo: Full LangGraph Workflow

This script demonstrates the complete ChatBI LangGraph workflow
from user question to final answer.

Usage:
    python demos/demo_full_workflow.py
"""

import asyncio
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_chatbi.llm.langchain_llm import create_langchain_llm
from langchain_chatbi.graph.workflow import get_chatbi_graph, print_workflow_graph


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


async def run_query(graph, question: str, config: dict):
    """Run a single query through the workflow."""
    print_section(f"Processing: {question}")

    # Initial state
    initial_state = {
        "question": question,
        "session_id": "demo-session",
        "language": "zh-CN",
        "messages": [],
        "sql_retry_count": 0,
        "should_stop": False
    }

    print(f"📝 Question: {question}")
    print("\n🔄 Executing workflow...\n")

    # Stream events
    event_count = 0
    async for event in graph.astream(initial_state, config=config):
        for node_name, node_output in event.items():
            if node_name != "__end__":
                event_count += 1

                # Extract key information from node output
                output_lines = []
                if "intent" in node_output and node_output["intent"]:
                    output_lines.append(f"Intent: {node_output['intent']}")

                if "reasoning" in node_output and node_output["reasoning"]:
                    reasoning = node_output["reasoning"][:100]
                    output_lines.append(f"Reasoning: {reasoning}...")

                if "generated_sql" in node_output and node_output["generated_sql"]:
                    sql = node_output["generated_sql"][:60]
                    output_lines.append(f"SQL: {sql}...")

                if "query_result" in node_output and node_output["query_result"]:
                    count = len(node_output["query_result"])
                    output_lines.append(f"Results: {count} rows")

                if "chart_config" in node_output and node_output["chart_config"]:
                    chart_type = node_output["chart_config"].get("chartType", "unknown")
                    output_lines.append(f"Chart: {chart_type}")

                if "answer" in node_output and node_output["answer"]:
                    answer = node_output["answer"][:100]
                    output_lines.append(f"Answer: {answer}...")

                if "sql_error" in node_output and node_output["sql_error"]:
                    output_lines.append(f"SQL Error: {node_output['sql_error'][:50]}...")

                if output_lines:
                    print(f"  [{node_name}]")
                    for line in output_lines:
                        print(f"    {line}")

    print(f"\n✅ Workflow completed ({event_count} events processed)")


async def main():
    print("=" * 60)
    print("ChatBI Full Workflow Demo")
    print("=" * 60)

    # Check for API key
    if not os.getenv("LLM_API_KEY"):
        print("\n⚠️  LLM_API_KEY not set. Please set it to run this demo.")
        print("   Example: export LLM_API_KEY='your-api-key'")
        return

    # Create LLM and graph
    print("\n🔧 Initializing LLM and LangGraph workflow...")
    llm = create_langchain_llm()
    graph = get_chatbi_graph()

    # Sample table schemas
    sample_schemas = [
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

    # Graph configuration
    config = {
        "configurable": {
            "llm": llm,
            "table_schemas": sample_schemas
        }
    }

    print("✅ Ready!")

    # Print workflow graph
    print("\n📊 Workflow Structure:")
    print_workflow_graph()

    # Test queries
    test_queries = [
        "Hello!",  # Greeting - should short-circuit
        "Show me the top 5 products by sales",  # Full query
    ]

    for question in test_queries:
        try:
            await run_query(graph, question, config)
        except Exception as e:
            print(f"\n❌ Error processing query: {e}")

        await asyncio.sleep(1)  # Brief pause between queries

    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
