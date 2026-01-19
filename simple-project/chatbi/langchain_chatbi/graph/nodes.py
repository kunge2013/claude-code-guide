"""
LangGraph Agent Node Functions

Defines the node functions that execute each agent in the workflow.
Each node takes the current state, runs its agent, and returns updated state.
"""

from typing import Dict, Any, List
from langchain_core.messages import AIMessage, HumanMessage

from langchain_chatbi.graph.state import ChatBIState
from langchain_chatbi.agents.intent_agent import IntentClassificationAgent
from langchain_chatbi.agents.schema_agent import SchemaAgent
from langchain_chatbi.agents.sql_agent import SqlAgent
from langchain_chatbi.agents.reasoning_agent import QueryReasoningAgent
from langchain_chatbi.agents.chart_agent import ChartGenerationAgent
from langchain_chatbi.agents.diagnosis_agent import DiagnosisAgent
from langchain_chatbi.agents.answer_agent import AnswerSummarizationAgent


def intent_node(state: ChatBIState) -> Dict[str, Any]:
    """
    Intent classification node.

    Classifies the user's question to determine routing.
    """
    from langchain_chatbi.llm.langchain_llm import create_langchain_llm

    llm = create_langchain_llm()
    agent = IntentClassificationAgent(llm=llm)

    # Use synchronous agent method
    intent_result, ambiguity_result = agent.classify_full_sync(
        question=state["question"],
        context=None
    )

    updates = {
        "intent": intent_result.intent,
        "messages": [AIMessage(content=f"Intent classified as: {intent_result.intent}")]
    }

    # Store ambiguity info if detected
    if ambiguity_result and ambiguity_result.is_ambiguous:
        updates["ambiguity_info"] = {
            "ambiguity_type": ambiguity_result.ambiguity_type,
            "clarification_question": ambiguity_result.clarification_question,
            "options": ambiguity_result.options
        }

    return updates


def schema_node(state: ChatBIState) -> Dict[str, Any]:
    """
    Schema selection node.

    Selects relevant table schemas from the available options.
    """
    from langchain_chatbi.llm.langchain_llm import create_langchain_llm

    llm = create_langchain_llm()
    agent = SchemaAgent(llm=llm)

    # Get table_schemas from state or use empty list as default
    table_schemas = state.get("table_schemas", [])

    selected = asyncio.run(agent.select_schemas(
        question=state["question"],
        table_schemas=table_schemas
    ))

    return {
        "selected_schemas": selected,
        "messages": [AIMessage(content=f"Selected {len(selected)} relevant tables")]
    }


def reasoning_node(state: ChatBIState) -> Dict[str, Any]:
    """
    Query reasoning node.

    Generates step-by-step reasoning plan for the query.
    """
    from langchain_chatbi.llm.langchain_llm import create_langchain_llm

    llm = create_langchain_llm()
    agent = QueryReasoningAgent(llm=llm)

    reasoning = asyncio.run(agent.generate_reasoning(
        question=state["question"],
        mdl_context=state.get("mdl_context", ""),
        history_queries=state.get("history_queries", "")
    ))

    return {
        "reasoning": reasoning,
        "messages": [AIMessage(content=reasoning)]
    }


def sql_node(state: ChatBIState) -> Dict[str, Any]:
    """
    SQL generation node.

    Generates SQL from natural language with error correction.
    """
    from langchain_chatbi.llm.langchain_llm import create_langchain_llm

    llm = create_langchain_llm()
    agent = SqlAgent(llm=llm)

    # Check if we're in error correction mode
    if state.get("sql_error") and state.get("generated_sql"):
        # Correct the failed SQL
        corrected_sql = asyncio.run(agent.correct_sql(
            question=state["question"],
            sql=state["generated_sql"],
            error=state["sql_error"],
            table_schemas=state["selected_schemas"] or []
        ))

        return {
            "generated_sql": corrected_sql,
            "sql_retry_count": state.get("sql_retry_count", 0) + 1,
            "messages": [AIMessage(content=f"Corrected SQL (attempt {state.get('sql_retry_count', 0) + 1})")]
        }
    else:
        # Generate initial SQL
        sql = asyncio.run(agent.generate_sql(
            question=state["question"],
            table_schemas=state["selected_schemas"] or []
        ))

        return {
            "generated_sql": sql,
            "sql_retry_count": 0,
            "messages": [AIMessage(content=f"Generated SQL query")]
        }


def execution_node(state: ChatBIState) -> Dict[str, Any]:
    """
    SQL execution node.

    Executes the SQL query against the database.
    """
    import asyncio
    import concurrent.futures

    # Get database from state or use demo mode
    db = state.get("db")

    if not db:
        # Demo mode: Return mock results
        mock_results = [
            {"product_name": "Laptop", "sales": 1500.00},
            {"product_name": "Mouse", "sales": 450.50},
            {"product_name": "Keyboard", "sales": 320.00},
            {"product_name": "Monitor", "sales": 890.00},
            {"product_name": "Headphones", "sales": 210.00}
        ]
        return {
            "query_result": mock_results,
            "sql_error": None,
            "messages": [AIMessage(content=f"Demo mode: Returning {len(mock_results)} mock results")]
        }

    try:
        # Run SQL execution in thread pool (synchronous version)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = executor.submit(
                db.run,
                state["generated_sql"],
                fetch="all"  # Fetch all results
            ).result()

        # Convert to list of dicts if needed
        if isinstance(result, list):
            query_result = [dict(row) if hasattr(row, 'keys') else row for row in result]
        else:
            query_result = list(result) if result else []

        return {
            "query_result": query_result,
            "sql_error": None,
            "messages": [AIMessage(content=f"Query executed successfully, returned {len(query_result)} rows")]
        }

    except Exception as e:
        return {
            "sql_error": str(e),
            "messages": [AIMessage(content=f"SQL execution failed: {str(e)}")]
        }


def chart_node(state: ChatBIState) -> Dict[str, Any]:
    """
    Chart generation node.

    Generates chart configuration from query results.
    """
    from langchain_chatbi.llm.langchain_llm import create_langchain_llm

    llm = create_langchain_llm()
    agent = ChartGenerationAgent(llm=llm)

    chart_config = asyncio.run(agent.generate_chart(
        question=state["question"],
        query_metadata={},
        result_data=state["query_result"] or []
    ))

    return {
        "chart_config": chart_config.model_dump(),
        "messages": [AIMessage(content=f"Generated {chart_config.chartType} chart")]
    }


def diagnosis_node(state: ChatBIState) -> Dict[str, Any]:
    """
    Diagnosis/insights node.

    Extracts insights from query results.
    """
    from langchain_chatbi.llm.langchain_llm import create_langchain_llm

    llm = create_langchain_llm()
    agent = DiagnosisAgent(llm=llm)

    diagnosis = asyncio.run(agent.generate_diagnosis(
        question=state["question"],
        sql=state.get("generated_sql", ""),
        data_sample=state["query_result"][:20] if state["query_result"] else []
    ))

    return {
        "diagnosis": diagnosis.model_dump(),
        "messages": [AIMessage(content=f"Generated insights: {diagnosis.summary[:100]}...")]
    }


def answer_node(state: ChatBIState) -> Dict[str, Any]:
    """
    Answer summarization node.

    Generates natural language summary from query results.
    """
    from langchain_chatbi.llm.langchain_llm import create_langchain_llm

    llm = create_langchain_llm()
    agent = AnswerSummarizationAgent(llm=llm)

    answer = asyncio.run(agent.generate_answer(
        question=state["question"],
        query_metadata={},
        result_data=state["query_result"] or [],
        chart_config=state.get("chart_config", {}),
        language=state.get("language", "zh-CN")
    ))

    return {
        "answer": answer,
        "messages": [AIMessage(content=answer)]
    }
