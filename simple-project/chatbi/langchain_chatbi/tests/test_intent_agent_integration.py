"""
Integration Tests for IntentClassificationAgent

Uses real LLM (via langchain_llm fixture) for testing.
Requires .env file with LLM_API_KEY, LLM_BASE_URL, LLM_MODEL configured.
"""

import pytest

from langchain_chatbi.agents.intent_agent import IntentClassificationAgent
from langchain_chatbi.models.response_models import (
    IntentClassification,
    AmbiguityDetection,
)


# ============================================================================
# Test Class
# ============================================================================


@pytest.mark.integration
class TestIntentClassificationAgentIntegration:
    """Integration tests for IntentClassificationAgent using real LLM."""

    # ========================================================================
    # Async Intent Classification Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_classify_query(self, langchain_llm):
        """Test data query intent classification."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        result = await agent.classify("上个月销售额是多少？")

        assert isinstance(result, IntentClassification)
        assert result.intent == "query"
        assert result.confidence > 0.5
        assert len(result.reasoning) > 0

    @pytest.mark.asyncio
    async def test_classify_greeting(self, langchain_llm):
        """Test greeting intent classification."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        result = await agent.classify("你好")

        assert isinstance(result, IntentClassification)
        assert result.intent == "greeting"
        assert result.confidence > 0.5
        assert len(result.reasoning) > 0

    @pytest.mark.asyncio
    async def test_classify_help(self, langchain_llm):
        """Test help intent classification."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        result = await agent.classify("帮我")

        assert isinstance(result, IntentClassification)
        assert result.intent == "help"
        assert result.confidence > 0.5
        assert len(result.reasoning) > 0

    @pytest.mark.asyncio
    async def test_classify_with_context(self, langchain_llm):
        """Test classification with conversation context."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        context = "Previous question was about product sales trends"
        result = await agent.classify(
            "按类别显示结果",
            context=context
        )

        assert isinstance(result, IntentClassification)
        assert result.intent in ["query", "clarification", "unknown"]
        assert len(result.reasoning) > 0

    @pytest.mark.asyncio
    async def test_check_ambiguity_clear_question(self, langchain_llm):
        """Test ambiguity detection with a clear question."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        result = await agent.check_ambiguity("显示销售额前5的产品")

        assert isinstance(result, AmbiguityDetection)
        assert result.is_ambiguous is False
        assert result.ambiguity_type == "none"

    @pytest.mark.asyncio
    async def test_check_ambiguity_vague_question(self, langchain_llm):
        """Test ambiguity detection with a vague question."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        result = await agent.check_ambiguity("给我看看数据")

        assert isinstance(result, AmbiguityDetection)
        # The LLM should recognize this is vague
        assert result.is_ambiguous is True
        assert result.ambiguity_type in [
            "completely_vague",
            "multiple_interpretations",
            "missing_critical_context"
        ]
        assert len(result.clarification_question) > 0

    @pytest.mark.asyncio
    async def test_classify_full_query(self, langchain_llm):
        """Test full classification with query intent."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        intent_result, ambiguity_result = await agent.classify_full(
            "上个月销售额最高的产品是什么？"
        )

        assert isinstance(intent_result, IntentClassification)
        assert intent_result.intent == "query"
        assert intent_result.confidence > 0.5

        assert ambiguity_result is not None
        assert isinstance(ambiguity_result, AmbiguityDetection)
        # This question is specific enough that it should not be ambiguous
        assert ambiguity_result.is_ambiguous is False

    @pytest.mark.asyncio
    async def test_classify_full_non_query(self, langchain_llm):
        """Test full classification with non-query intent."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        intent_result, ambiguity_result = await agent.classify_full("你好")

        assert isinstance(intent_result, IntentClassification)
        assert intent_result.intent == "greeting"

        # Ambiguity check should be skipped for non-query intents
        assert ambiguity_result is None

    # ========================================================================
    # Sync Method Tests
    # ========================================================================

    def test_classify_sync(self, langchain_llm):
        """Test synchronous intent classification."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        result = agent.classify_sync("上个月销售额是多少？")

        assert isinstance(result, IntentClassification)
        assert result.intent == "query"
        assert result.confidence > 0.5
        assert len(result.reasoning) > 0

    def test_check_ambiguity_sync(self, langchain_llm):
        """Test synchronous ambiguity detection."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        result = agent.check_ambiguity_sync("显示前5个产品")

        assert isinstance(result, AmbiguityDetection)
        assert result.is_ambiguous is False
        assert result.ambiguity_type == "none"

    def test_classify_full_sync(self, langchain_llm):
        """Test synchronous full classification."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        intent_result, ambiguity_result = agent.classify_full_sync(
            "销售额按月份分组统计"
        )

        assert isinstance(intent_result, IntentClassification)
        assert intent_result.intent == "query"
        assert intent_result.confidence > 0.5

        assert ambiguity_result is not None
        assert isinstance(ambiguity_result, AmbiguityDetection)

    # ========================================================================
    # Edge Case Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_classify_empty_question(self, langchain_llm):
        """Test classification with empty/minimal input."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        result = await agent.classify("")

        # Should handle gracefully - either unknown or clarification
        assert isinstance(result, IntentClassification)
        assert result.intent in ["unknown", "clarification", "greeting"]

    @pytest.mark.asyncio
    async def test_classify_multiple_sentences(self, langchain_llm):
        """Test classification with complex multi-sentence input."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        result = await agent.classify(
            "你好，我想问一下，上个月销售额最高的产品是什么？"
        )

        # The primary intent should be query despite the greeting
        assert isinstance(result, IntentClassification)
        assert result.intent == "query"
        assert result.confidence > 0.5

    def test_classify_sync_with_help_question(self, langchain_llm):
        """Test sync classification with help question."""
        agent = IntentClassificationAgent(llm=langchain_llm)

        result = agent.classify_sync("怎么使用这个系统？")

        assert isinstance(result, IntentClassification)
        assert result.intent == "help"
        assert result.confidence > 0.5
