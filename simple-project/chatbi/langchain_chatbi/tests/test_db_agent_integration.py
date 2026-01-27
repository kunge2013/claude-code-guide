"""
Integration Tests for DbAgent

Uses real LLM (via langchain_llm fixture) for testing.
Requires .env file with LLM_API_KEY, LLM_BASE_URL, LLM_MODEL configured.
"""

import pytest

from langchain_chatbi.agents.db_agent import DbAgent
from langchain_chatbi.models.response_models import (
    DbResponse
)


# ============================================================================
# Test Class
# ============================================================================


@pytest.mark.integration
class TestDbAgentIntegration:
    """Integration tests for DbAgent using real LLM."""

    # ========================================================================
    # Async Intent Classification Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_classify_query(self, langchain_llm):
        """Test data query intent classification."""
        agent = DbAgent(llm=langchain_llm)

        result = await agent.select_db("上个月销售额是多少？")

        assert isinstance(result, DbResponse)
        assert result.dbtype == "mysql"
        assert result.confidence > 0.5


