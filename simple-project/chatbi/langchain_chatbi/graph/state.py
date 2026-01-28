"""
LangGraph State Definition for ChatBI

Defines the state structure that flows through the agent workflow.
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import MessagesState


class ChatBIState(MessagesState):
    """
    State for ChatBI LangGraph workflow.

    This state is passed between agent nodes and contains all
    intermediate results from the query processing pipeline.
    """

    # ============================================================================
    # Input Fields
    # ============================================================================

    question: str
    """The user's natural language question"""

    session_id: Optional[str]
    """Session identifier for conversation tracking"""

    language: str
    """Output language (e.g., 'zh-CN', 'en-US')"""

    # ============================================================================
    # Configuration
    # ============================================================================

    table_schemas: Optional[List[Dict[str, Any]]]
    """Available table schemas for schema selection"""

    # Note: db connection is passed via config["configurable"]["db"] instead of state
    # to avoid msgpack serialization issues

    # ============================================================================
    # Agent Outputs
    # ============================================================================

    intent: Optional[str]
    """Classified intent: 'query', 'greeting', 'help', 'clarification', 'unknown'"""

    ambiguity_info: Optional[Dict[str, Any]]
    """Ambiguity detection result if intent is 'clarification'"""

    selected_schemas: Optional[List[Dict[str, Any]]]
    """Selected table schemas relevant to the question"""

    generated_sql: Optional[str]
    """Generated SQL query"""

    sql_error: Optional[str]
    """SQL execution error message (if any)"""

    sql_retry_count: int
    """Number of SQL generation retry attempts"""

    reasoning: Optional[str]
    """Query reasoning/explanation text"""

    query_result: Optional[List[Dict[str, Any]]]
    """Query execution result data"""

    chart_config: Optional[Dict[str, Any]]
    """Chart configuration for visualization"""

    diagnosis: Optional[Dict[str, Any]]
    """Data insights and key findings"""

    answer: Optional[str]
    """Natural language answer summary"""

    # ============================================================================
    # Metadata
    # ============================================================================

    mdl_context: Optional[str]
    """Metadata layer context (available models/columns)"""

    history_queries: Optional[str]
    """Similar historical queries for context"""

    # ============================================================================
    # Error Handling
    # ============================================================================

    error: Optional[str]
    """Error message if workflow failed"""

    should_stop: bool
    """Flag to stop the workflow early"""
