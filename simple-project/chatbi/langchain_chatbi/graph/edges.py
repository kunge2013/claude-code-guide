"""
LangGraph Conditional Routing Functions

Defines the conditional routing logic between nodes in the workflow.
"""

from typing import Literal
from langchain_chatbi.graph.state import ChatBIState


def route_after_intent(state: ChatBIState) -> Literal["schema", "end", "__end__"]:
    """
    Route after intent classification.

    - query → proceed to schema selection
    - greeting/help/unknown → end workflow
    - clarification → end workflow (request clarification from user)
    """
    intent = state.get("intent")

    if intent == "query":
        return "schema"
    else:
        # greeting, help, unknown, clarification → end
        return "__end__"


def route_after_execution(state: ChatBIState) -> Literal["sql", "chart", "__end__"]:
    """
    Route after SQL execution.

    - SQL error and retry count < 3 → retry SQL generation
    - SQL error and retry count >= 3 → end with error
    - Success → proceed to chart generation
    """
    if state.get("sql_error"):
        retry_count = state.get("sql_retry_count", 0)
        if retry_count < 3:
            return "sql"  # Retry with error correction
        else:
            # Max retries exceeded, end workflow
            return "__end__"
    else:
        return "chart"
