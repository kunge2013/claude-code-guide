"""
LangGraph Workflow Compilation

Compiles the ChatBI agent workflow using LangGraph.
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from langchain_chatbi.graph.state import ChatBIState
from langchain_chatbi.graph.nodes import (
    intent_node,
    schema_node,
    reasoning_node,
    sql_node,
    execution_node,
    chart_node,
    diagnosis_node,
    answer_node,
)
from langchain_chatbi.graph.edges import route_after_intent, route_after_execution


def create_chatbi_graph():
    """
    Create the ChatBI LangGraph workflow.

    The workflow processes user questions through multiple agents:
    1. Intent classification → routes based on question type
    2. Schema selection → selects relevant tables
    3. Query reasoning → generates step-by-step plan
    4. SQL generation → creates SQL query
    5. SQL execution → runs query against database
       - On error: retry with correction (max 3 attempts)
    6. Chart generation → creates visualization config
    7. Diagnosis → extracts insights
    8. Answer summarization → generates natural language response

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the state graph
    workflow = StateGraph(ChatBIState)

    # ============================================================================
    # Add Nodes
    # ============================================================================

    workflow.add_node("intent", intent_node)
    workflow.add_node("schema", schema_node)
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("sql", sql_node)
    workflow.add_node("execution", execution_node)
    workflow.add_node("chart", chart_node)
    workflow.add_node("diagnosis", diagnosis_node)
    workflow.add_node("answer", answer_node)

    # ============================================================================
    # Define Entry Point
    # ============================================================================

    workflow.set_entry_point("intent")

    # ============================================================================
    # Define Edges
    # ============================================================================

    # Intent → conditional routing
    workflow.add_conditional_edges(
        "intent",
        route_after_intent,
        {
            "schema": "schema",
            "__end__": END,
        }
    )

    # Schema → Reasoning
    workflow.add_edge("schema", "reasoning")

    # Reasoning → SQL
    workflow.add_edge("reasoning", "sql")

    # SQL → Execution
    workflow.add_edge("sql", "execution")

    # Execution → conditional routing (retry or proceed)
    workflow.add_conditional_edges(
        "execution",
        route_after_execution,
        {
            "sql": "sql",  # Retry SQL with error correction
            "chart": "chart",  # Proceed to chart generation
            "__end__": END,  # Max retries exceeded
        }
    )

    # Chart → Diagnosis
    workflow.add_edge("chart", "diagnosis")

    # Diagnosis → Answer
    workflow.add_edge("diagnosis", "answer")

    # Answer → End
    workflow.add_edge("answer", END)

    # ============================================================================
    # Compile Graph
    # ============================================================================

    # Add memory checkpointer for conversation state
    memory = MemorySaver()

    # Compile the graph
    app = workflow.compile(checkpointer=memory)

    return app


def print_workflow_graph():
    """
    Print a text representation of the workflow graph.
    """
    print("ChatBI LangGraph Workflow:")
    print("=" * 50)
    print("""
    User Question
        │
        ▼
    [intent_node]
        │
        ├─→ (query) ──────────────────────┐
        │                                  │
        ▼                                  │
    [schema_node]                         │
        │                                  │
        ▼                                  │
    [reasoning_node]                      │
        │                                  │
        ▼                                  │
    [sql_node] ───────────────┐           │
        │                      │           │
        ▼                      │           │
    [execution_node] ─────────┤ (error)    │
        │ (success)           │   │        │
        │                     ▼   ▼        │
        │                 [sql_node]       │
        │                      │           │
        └──────────────────────┘           │
        │                                  │
        ▼                                  │
    [chart_node]                          │
        │                                  │
        ▼                                  │
    [diagnosis_node]                      │
        │                                  │
        ▼                                  │
    [answer_node]                          │
        │                                  │
        ▼                                  ▼
      END                               END
    (other intents: greeting, help, unknown)
    """)


# Create singleton instance
_chatbi_graph = None


def get_chatbi_graph():
    """
    Get the ChatBI graph instance (singleton pattern).

    Returns:
        Compiled StateGraph
    """
    global _chatbi_graph
    if _chatbi_graph is None:
        _chatbi_graph = create_chatbi_graph()
    return _chatbi_graph
