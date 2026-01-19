"""
Unit Tests for LangChain Agents

Tests each agent independently with mock LLM responses.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from langchain_chatbi.agents.intent_agent import IntentClassificationAgent
from langchain_chatbi.agents.schema_agent import SchemaAgent
from langchain_chatbi.agents.sql_agent import SqlAgent
from langchain_chatbi.agents.reasoning_agent import QueryReasoningAgent
from langchain_chatbi.agents.chart_agent import ChartGenerationAgent
from langchain_chatbi.agents.diagnosis_agent import DiagnosisAgent
from langchain_chatbi.agents.answer_agent import AnswerSummarizationAgent

from langchain_chatbi.models.response_models import (
    IntentClassification,
    AmbiguityDetection,
    ChartConfig,
    InsightSummary,
)


# ============================================================================
# IntentClassificationAgent Tests
# ============================================================================


class TestIntentClassificationAgent:
    """Test IntentClassificationAgent"""

    @pytest.mark.asyncio
    async def test_classify_query(self, mock_llm):
        """Test classifying a query intent."""
        agent = IntentClassificationAgent(llm=mock_llm)

        # Mock the response
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
            content='{"intent": "query", "reasoning": "User is asking for data", "confidence": 0.9}'
        ))

        result = await agent.classify(question="上个月销售额是多少？")

        assert result.intent == "query"
        assert "data" in result.reasoning.lower()
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_classify_greeting(self, mock_llm):
        """Test classifying a greeting."""
        agent = IntentClassificationAgent(llm=mock_llm)

        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
            content='{"intent": "greeting", "reasoning": "User is saying hello", "confidence": 0.95}'
        ))

        result = await agent.classify(question="你好")

        assert result.intent == "greeting"

    @pytest.mark.asyncio
    async def test_check_ambiguity(self, mock_llm):
        """Test ambiguity detection."""
        agent = IntentClassificationAgent(llm=mock_llm)

        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
            content='{"is_ambiguous": false, "ambiguity_type": "none", "clarification_question": "", "options": []}'
        ))

        result = await agent.check_ambiguity(question="Show me sales by product")

        assert result.is_ambiguous is False
        assert result.ambiguity_type == "none"


# ============================================================================
# SchemaAgent Tests
# ============================================================================


class TestSchemaAgent:
    """Test SchemaAgent"""

    @pytest.mark.asyncio
    async def test_select_schemas(self, mock_llm, sample_table_schemas):
        """Test selecting relevant schemas."""
        agent = SchemaAgent(llm=mock_llm)

        # Mock response with JSON array of selected tables
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
            content='''{"tables": [{"name": "orders", "reason": "Question asks about sales data"}], "excluded_tables": []}'''
        ))

        selected = await agent.select_schemas(
            question="Show me total sales by customer",
            table_schemas=sample_table_schemas
        )

        assert len(selected) > 0
        assert any(s["name"] == "orders" for s in selected)


# ============================================================================
# SqlAgent Tests
# ============================================================================


class TestSqlAgent:
    """Test SqlAgent"""

    @pytest.mark.asyncio
    async def test_generate_sql(self, mock_llm, sample_table_schemas):
        """Test SQL generation."""
        agent = SqlAgent(llm=mock_llm)

        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
            content="SELECT * FROM orders ORDER BY total_amount DESC LIMIT 10"
        ))

        sql = await agent.generate_sql(
            question="Show me top 10 orders by amount",
            table_schemas=sample_table_schemas
        )

        assert "SELECT" in sql.upper()
        assert "orders" in sql.lower()

    @pytest.mark.asyncio
    async def test_correct_sql(self, mock_llm, sample_table_schemas):
        """Test SQL error correction."""
        agent = SqlAgent(llm=mock_llm)

        corrected_sql = "SELECT * FROM orders WHERE total_amount > 0"
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content=corrected_sql))

        result = await agent.correct_sql(
            question="Show me orders",
            sql="SELECT * FROM nonexistent_table",
            error="Table 'nonexistent_table' does not exist",
            table_schemas=sample_table_schemas
        )

        assert "orders" in result.lower()


# ============================================================================
# QueryReasoningAgent Tests
# ============================================================================


class TestQueryReasoningAgent:
    """Test QueryReasoningAgent"""

    @pytest.mark.asyncio
    async def test_generate_reasoning(self, mock_llm):
        """Test reasoning generation (non-streaming)."""
        agent = QueryReasoningAgent(llm=mock_llm)

        mock_response = """
## Step 1: Understanding the Question
The user wants to find the top 5 products by sales.

## Step 2: Identify Required Data
- Model: Orders
- Measure: total_amount
- Dimension: product_name
"""
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content=mock_response))

        reasoning = await agent.generate_reasoning(
            question="What are the top 5 products by sales?",
            mdl_context="Orders table with sales data"
        )

        assert "Understanding" in reasoning
        assert len(reasoning) > 0

    @pytest.mark.asyncio
    async def test_generate_reasoning_stream(self, mock_llm):
        """Test reasoning generation with streaming."""
        agent = QueryReasoningAgent(llm=mock_llm)

        # Mock streaming response
        async def mock_stream(messages, config=None):
            chunks = ["Step 1:", " Understanding", " the question"]
            for chunk in chunks:
                mock_chunk = Mock()
                mock_chunk.content = chunk
                yield mock_chunk

        mock_llm.astream = AsyncMock(side_effect=mock_stream)

        chunks = []
        async for chunk in agent.generate_reasoning_stream(
            question="Analyze sales trends",
            mdl_context="Orders table"
        ):
            chunks.append(chunk)

        assert len(chunks) > 0


# ============================================================================
# ChartGenerationAgent Tests
# ============================================================================


class TestChartGenerationAgent:
    """Test ChartGenerationAgent"""

    @pytest.mark.asyncio
    async def test_generate_chart_with_llm(self, mock_llm, sample_query_results):
        """Test chart generation using LLM."""
        agent = ChartGenerationAgent(llm=mock_llm)

        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
            content='''{"chartType": "bar", "title": "Top 5 Products", "description": "Shows products by sales", "spec": {"xField": "product", "yField": "sales"}}'''
        ))

        result = await agent.generate_chart(
            question="Show top 5 products by sales",
            query_metadata={"measures": ["sales"], "dimensions": ["product"]},
            result_data=sample_query_results
        )

        assert result.chartType == "bar"
        assert "products" in result.title.lower()

    @pytest.mark.asyncio
    async def test_auto_detect_chart(self, mock_llm):
        """Test auto-detection without LLM."""
        agent = ChartGenerationAgent(llm=mock_llm)

        query_metadata = {
            "measures": ["total_amount"],
            "dimensions": ["product_name"],
            "timeDimensions": []
        }

        result_data = [
            {"product_name": "A", "total_amount": 100},
            {"product_name": "B", "total_amount": 200}
        ]

        result = agent._auto_detect_chart(
            query_metadata=query_metadata,
            result_data=result_data,
            question="Show sales by product"
        )

        assert result is not None
        assert result.chartType == "bar"


# ============================================================================
# DiagnosisAgent Tests
# ============================================================================


class TestDiagnosisAgent:
    """Test DiagnosisAgent"""

    @pytest.mark.asyncio
    async def test_generate_diagnosis(self, mock_llm):
        """Test diagnosis generation."""
        agent = DiagnosisAgent(llm=mock_llm)

        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
            content='''{"summary": "Sales show positive growth trend", "key_points": ["Product A leads with 125K", "Growth rate of 15%"], "confidence": 0.8}'''
        ))

        result = await agent.generate_diagnosis(
            question="What are the sales trends?",
            sql="SELECT * FROM sales",
            data_sample=[{"product": "A", "sales": 125000}]
        )

        assert "growth" in result.summary.lower()
        assert len(result.key_points) > 0


# ============================================================================
# AnswerSummarizationAgent Tests
# ============================================================================


class TestAnswerSummarizationAgent:
    """Test AnswerSummarizationAgent"""

    @pytest.mark.asyncio
    async def test_generate_answer_chinese(self, mock_llm, sample_query_results):
        """Test answer generation in Chinese."""
        agent = AnswerSummarizationAgent(llm=mock_llm)

        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(
            content="根据分析，销售额最高的产品是产品A，达到125,000元。"
        ))

        result = await agent.generate_answer(
            question="哪个产品销售额最高？",
            query_metadata={},
            result_data=sample_query_results,
            chart_config={"chartType": "bar"},
            language="zh-CN"
        )

        assert "125" in result or "产品" in result

    @pytest.mark.asyncio
    async def test_generate_answer_stream(self, mock_llm, sample_query_results):
        """Test answer generation with streaming."""
        agent = AnswerSummarizationAgent(llm=mock_llm)

        # Mock streaming response
        async def mock_stream(messages, config=None):
            chunks = ["Based", " on", " analysis", "..."]
            for chunk in chunks:
                mock_chunk = Mock()
                mock_chunk.content = chunk
                yield mock_chunk

        mock_llm.astream = AsyncMock(side_effect=mock_stream)

        chunks = []
        async for chunk in agent.generate_answer_stream(
            question="What are the top products?",
            query_metadata={},
            result_data=sample_query_results,
            chart_config={"chartType": "bar"},
            language="en-US"
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
