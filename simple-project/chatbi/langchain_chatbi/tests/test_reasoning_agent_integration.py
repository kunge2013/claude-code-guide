"""
Integration Tests for QueryReasoningAgent

Uses real LLM (via langchain_llm fixture) for testing.
Requires .env file with LLM_API_KEY, LLM_BASE_URL, LLM_MODEL configured.
"""

import pytest
from langchain_chatbi.agents.reasoning_agent import QueryReasoningAgent
from loguru import logger

# ============================================================================
# Test Class
# ============================================================================


@pytest.mark.integration
class TestQueryReasoningAgentIntegration:
    """Integration tests for QueryReasoningAgent using real LLM."""

    # Sample MDL context for testing
    SAMPLE_MDL = """
Available Models:
- Orders: Contains order information (id, customer_id, product_id, total_amount, order_date)
- Products: Contains product information (id, name, category, price)
- Customers: Contains customer information (id, name, email, region)

Measures available:
- Orders.total_amount (sum, avg, count)
- Products.price (sum, avg)

Dimensions available:
- Orders.customer_id, Orders.product_id
- Products.name, Products.category
- Customers.name, Customers.region
- Time dimensions: Orders.order_date (day, month, year)
"""

    # Sample historical queries
    SAMPLE_HISTORY = """
Similar queries:
- "Show me top 10 products by revenue" → SELECT name, SUM(total_amount) FROM orders GROUP BY name ORDER BY revenue DESC LIMIT 10
- "What's the total sales by month?" → SELECT DATE_TRUNC('month', order_date), SUM(total_amount) FROM orders GROUP BY 1
- "Count customers by region" → SELECT region, COUNT(*) FROM customers GROUP BY region
"""

    # ========================================================================
    # Non-Streaming Reasoning Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_generate_reasoning_basic_query(self, langchain_llm):
        """Test reasoning generation for a basic query."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        question = "上个月销售额最高的5个产品是什么？"
        reasoning = await agent.generate_reasoning(
            question,
            mdl_context=self.SAMPLE_MDL,
            history_queries=self.SAMPLE_HISTORY
        )

        assert isinstance(reasoning, str)
        assert len(reasoning) > 50
        # Should contain relevant keywords
        assert any(keyword in reasoning.lower() for keyword in
                   ["产品", "销售额", "top", "order", "product"])

    @pytest.mark.asyncio
    async def test_generate_reasoning_with_aggregation(self, langchain_llm):
        """Test reasoning for aggregation query."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        question = "统计每个地区的客户数量"
        reasoning = await agent.generate_reasoning(
            question,
            mdl_context=self.SAMPLE_MDL
        )
        logger.debug(f'test_generate_reasoning_with_aggregation :\n {reasoning}')
        assert isinstance(reasoning, str)
        assert len(reasoning) > 50
        # Should mention aggregation and grouping
        assert any(keyword in reasoning for keyword in
                   ["group", "count", "地区", "region", "聚合"])

    @pytest.mark.asyncio
    async def test_generate_reasoning_with_time_filter(self, langchain_llm):
        """Test reasoning for time-filtered query."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        question = "2024年第一季度的销售趋势"
        reasoning = await agent.generate_reasoning(
            question,
            mdl_context=self.SAMPLE_MDL
        )

        assert isinstance(reasoning, str)
        assert len(reasoning) > 50
        # Should mention time filtering
        assert any(keyword in reasoning for keyword in
                   ["时间", "date", "filter", "季度", "quarter"])

    @pytest.mark.asyncio
    async def test_generate_reasoning_no_context(self, langchain_llm):
        """Test reasoning generation without MDL context."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        reasoning = await agent.generate_reasoning(
            "显示销售额",
            mdl_context="",
            history_queries=""
        )

        # Should still generate some reasoning even without context
        assert isinstance(reasoning, str)
        assert len(reasoning) > 20

    @pytest.mark.asyncio
    async def test_generate_reasoning_with_history(self, langchain_llm):
        """Test reasoning generation with historical queries."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        reasoning_with_history = await agent.generate_reasoning(
            "销售额前10的产品",
            mdl_context=self.SAMPLE_MDL,
            history_queries=self.SAMPLE_HISTORY
        )

        reasoning_without_history = await agent.generate_reasoning(
            "销售额前10的产品",
            mdl_context=self.SAMPLE_MDL,
            history_queries=""
        )

        # Both should generate valid reasoning
        assert len(reasoning_with_history) > 50
        assert len(reasoning_without_history) > 50

    # ========================================================================
    # Streaming Reasoning Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_generate_reasoning_stream_basic(self, langchain_llm):
        """Test streaming reasoning generation."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        question = "分析各产品类别的销售表现"
        chunks = []
        total_length = 0

        async for chunk in agent.generate_reasoning_stream(
            question,
            mdl_context=self.SAMPLE_MDL
        ):
            chunks.append(chunk)
            total_length += len(chunk)

        # Should receive multiple chunks
        assert len(chunks) > 0
        assert total_length > 50

        # Combine chunks and verify
        full_reasoning = "".join(chunks)
        assert len(full_reasoning) > 50
        assert any(keyword in full_reasoning for keyword in
                   ["产品", "类别", "销售", "category", "sales"])

    @pytest.mark.asyncio
    async def test_generate_reasoning_stream_content(self, langchain_llm):
        """Test that streaming produces coherent content."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        question = "哪个地区的客户最多？"
        chunks = []

        async for chunk in agent.generate_reasoning_stream(
            question,
            mdl_context=self.SAMPLE_MDL,
            history_queries=self.SAMPLE_HISTORY
        ):
            chunks.append(chunk)

        full_reasoning = "".join(chunks)

        # Verify the reasoning makes sense
        assert isinstance(full_reasoning, str)
        assert len(full_reasoning) > 50
        # Should contain reasoning about regions and customers
        assert any(keyword in full_reasoning for keyword in
                   ["地区", "客户", "region", "customer"])

    @pytest.mark.asyncio
    async def test_generate_reasoning_stream_empty_context(self, langchain_llm):
        """Test streaming with empty context."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        chunks = []
        async for chunk in agent.generate_reasoning_stream(
            "简单查询",
            mdl_context="",
            history_queries=""
        ):
            chunks.append(chunk)

        full_reasoning = "".join(chunks)
        assert isinstance(full_reasoning, str)
        assert len(full_reasoning) > 10

    # ========================================================================
    # Structure and Format Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_reasoning_structure(self, langchain_llm):
        """Test that reasoning has proper structure."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        reasoning = await agent.generate_reasoning(
            "显示销售额前5的产品，按金额降序排列",
            mdl_context=self.SAMPLE_MDL
        )

        # Should contain structured elements
        # Check for markdown-style headers or numbered steps
        assert any(marker in reasoning for marker in ["##", "Step", "步骤", "1.", "一、"])

    @pytest.mark.asyncio
    async def test_reasoning_mentions_key_elements(self, langchain_llm):
        """Test that reasoning mentions key query elements."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        reasoning = await agent.generate_reasoning(
            "统计每个产品类别的平均价格",
            mdl_context=self.SAMPLE_MDL
        )

        # Should mention key concepts
        combined_text = reasoning.lower()
        assert any(term in combined_text for term in
                   ["category", "类别", "price", "价格", "avg", "average", "平均"])

    # ========================================================================
    # Edge Case Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_reasoning_complex_query(self, langchain_llm):
        """Test reasoning for a complex multi-part query."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        question = "显示2024年每个季度的销售额，并与2023年同期对比"
        reasoning = await agent.generate_reasoning(
            question,
            mdl_context=self.SAMPLE_MDL
        )

        assert isinstance(reasoning, str)
        assert len(reasoning) > 50
        # Complex query should generate longer reasoning
        assert len(reasoning) > 100

    @pytest.mark.asyncio
    async def test_reasoning_vague_question(self, langchain_llm):
        """Test reasoning with a vague question."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        reasoning = await agent.generate_reasoning(
            "给我看看数据",
            mdl_context=self.SAMPLE_MDL
        )

        # Should still produce some reasoning
        assert isinstance(reasoning, str)
        assert len(reasoning) > 20

    @pytest.mark.asyncio
    async def test_reasoning_long_context(self, langchain_llm):
        """Test reasoning with large MDL context."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        large_mdl = self.SAMPLE_MDL + """
Additional Models:
- Inventory: (id, product_id, quantity, warehouse_id, last_updated)
- Warehouses: (id, name, location, capacity)
- Shipments: (id, order_id, warehouse_id, ship_date, delivery_date)
- Suppliers: (id, name, contact_info, rating)
""" * 5  # Make it larger

        reasoning = await agent.generate_reasoning(
            "库存最少的5个产品",
            mdl_context=large_mdl
        )

        assert isinstance(reasoning, str)
        assert len(reasoning) > 50

    # ========================================================================
    # Chinese Language Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_reasoning_chinese_questions(self, langchain_llm):
        """Test reasoning with various Chinese question types."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        test_questions = [
            ("销售额最高的产品", "top product by sales"),
            ("按月份统计订单", "orders by month"),
            ("各地区客户分布", "customers by region"),
            ("平均订单金额", "average order amount"),
        ]

        for question, description in test_questions:
            reasoning = await agent.generate_reasoning(
                question,
                mdl_context=self.SAMPLE_MDL
            )

            assert isinstance(reasoning, str)
            assert len(reasoning) > 30, f"Failed for: {description}"

    @pytest.mark.asyncio
    async def test_reasoning_chinese_output(self, langchain_llm):
        """Test that reasoning output handles Chinese properly."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        reasoning = await agent.generate_reasoning(
            "销售额是多少？",
            mdl_context=self.SAMPLE_MDL
        )

        # Should handle Chinese characters properly
        assert isinstance(reasoning, str)
        # Verify it's not corrupted encoding
        try:
            reasoning.encode('utf-8')
        except UnicodeEncodeError:
            pytest.fail("Chinese characters not properly encoded")

    # ========================================================================
    # Comparison Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_streaming_vs_non_streaming_consistency(self, langchain_llm):
        """Test that streaming and non-streaming produce similar output."""
        agent = QueryReasoningAgent(llm=langchain_llm)

        question = "显示前10个产品的销售额"

        # Non-streaming
        reasoning_non_stream = await agent.generate_reasoning(
            question,
            mdl_context=self.SAMPLE_MDL
        )

        # Streaming
        chunks = []
        async for chunk in agent.generate_reasoning_stream(
            question,
            mdl_context=self.SAMPLE_MDL
        ):
            chunks.append(chunk)
        reasoning_stream = "".join(chunks)

        # Both should be valid and reasonably similar in length
        assert len(reasoning_non_stream) > 50
        assert len(reasoning_stream) > 50
        # Lengths should be in the same order of magnitude
        ratio = max(len(reasoning_non_stream), len(reasoning_stream)) / \
                min(len(reasoning_non_stream), len(reasoning_stream))
        assert ratio < 3.0, "Streaming and non-streaming outputs differ too much"
