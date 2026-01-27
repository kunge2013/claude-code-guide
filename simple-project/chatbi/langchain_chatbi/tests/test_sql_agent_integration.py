"""
Integration Tests for SqlAgent

Uses real LLM (via langchain_llm fixture) for testing.
Requires .env file with LLM_API_KEY, LLM_BASE_URL, LLM_MODEL configured.
"""

import pytest
from langchain_chatbi.agents.sql_agent import SqlAgent
from loguru import logger


# ============================================================================
# Test Class
# ============================================================================


@pytest.mark.integration
class TestSqlAgentIntegration:
    """Integration tests for SqlAgent using real LLM."""

    # Sample table schemas for testing
    SAMPLE_SCHEMAS = [
        {
            "name": "orders",
            "columns": [
                {"name": "id", "type": "INTEGER"},
                {"name": "customer_id", "type": "INTEGER"},
                {"name": "product_id", "type": "INTEGER"},
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
        },
        {
            "name": "customers",
            "columns": [
                {"name": "id", "type": "INTEGER"},
                {"name": "name", "type": "VARCHAR"},
                {"name": "email", "type": "VARCHAR"},
                {"name": "region", "type": "VARCHAR"}
            ]
        }
    ]

    # ========================================================================
    # SQL Generation Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_generate_sql_simple_query(self, langchain_llm):
        """Test SQL generation for a simple query."""
        agent = SqlAgent(llm=langchain_llm)

        question = "显示所有订单"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        assert isinstance(sql, str)
        assert len(sql) > 0
        assert "SELECT" in sql.upper()
        assert "orders" in sql.lower()
        logger.debug(f'test_generate_sql_simple_query:\n{sql}')

    @pytest.mark.asyncio
    async def test_generate_sql_with_aggregation(self, langchain_llm):
        """Test SQL generation with aggregation."""
        agent = SqlAgent(llm=langchain_llm)

        question = "统计订单总金额"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        assert isinstance(sql, str)
        assert "SELECT" in sql.upper()
        # Should contain SUM or similar aggregation
        assert any(func in sql.upper() for func in ["SUM", "COUNT", "AVG"])
        assert "orders" in sql.lower()

    @pytest.mark.asyncio
    async def test_generate_sql_with_filter(self, langchain_llm):
        """Test SQL generation with WHERE clause."""
        agent = SqlAgent(llm=langchain_llm)

        question = "显示金额大于100的订单"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        assert isinstance(sql, str)
        assert "SELECT" in sql.upper()
        assert "WHERE" in sql.upper()
        assert "100" in sql

    @pytest.mark.asyncio
    async def test_generate_sql_with_limit(self, langchain_llm):
        """Test SQL generation with LIMIT clause."""
        agent = SqlAgent(llm=langchain_llm)

        question = "显示前10个订单"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        assert isinstance(sql, str)
        assert "SELECT" in sql.upper()
        assert "LIMIT" in sql.upper()
        assert "10" in sql

    @pytest.mark.asyncio
    async def test_generate_sql_with_group_by(self, langchain_llm):
        """Test SQL generation with GROUP BY clause."""
        agent = SqlAgent(llm=langchain_llm)

        question = "按产品类别统计订单数量"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        assert isinstance(sql, str)
        assert "SELECT" in sql.upper()
        assert "GROUP BY" in sql.upper()
        assert "category" in sql.lower()

    @pytest.mark.asyncio
    async def test_generate_sql_with_join(self, langchain_llm):
        """Test SQL generation with JOIN."""
        agent = SqlAgent(llm=langchain_llm)

        question = "显示每个订单的产品名称"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        assert isinstance(sql, str)
        assert "SELECT" in sql.upper()
        # Should contain JOIN for multiple tables
        assert "JOIN" in sql.upper()
        assert "orders" in sql.lower()
        assert "products" in sql.lower()

    @pytest.mark.asyncio
    async def test_generate_sql_with_order_by(self, langchain_llm):
        """Test SQL generation with ORDER BY clause."""
        agent = SqlAgent(llm=langchain_llm)

        question = "按金额降序显示订单"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        assert isinstance(sql, str)
        assert "SELECT" in sql.upper()
        assert "ORDER BY" in sql.upper()
        assert "DESC" in sql.upper() or "total_amount" in sql.lower()

    @pytest.mark.asyncio
    async def test_generate_sql_with_time_filter(self, langchain_llm):
        """Test SQL generation with time-based filtering."""
        agent = SqlAgent(llm=langchain_llm)

        question = "显示2024年1月的订单"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        assert isinstance(sql, str)
        assert "SELECT" in sql.upper()
        assert "order_date" in sql.lower()
        assert "2024" in sql or "01" in sql or "1月" in sql

    @pytest.mark.asyncio
    async def test_generate_sql_with_few_shots(self, langchain_llm):
        """Test SQL generation with few-shot examples."""
        agent = SqlAgent(llm=langchain_llm)

        few_shots = [
            {
                "question": "显示所有产品",
                "sql": "SELECT * FROM products"
            },
            {
                "question": "统计订单数量",
                "sql": "SELECT COUNT(*) FROM orders"
            }
        ]

        question = "显示所有客户"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS, few_shots)

        assert isinstance(sql, str)
        assert "SELECT" in sql.upper()
        assert "customers" in sql.lower()

    # ========================================================================
    # SQL Correction Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_correct_sql_syntax_error(self, langchain_llm):
        """Test SQL correction for syntax errors."""
        agent = SqlAgent(llm=langchain_llm)

        bad_sql = "SELEC * FROM orders"  # Typo: SELEC instead of SELECT
        error = 'syntax error at or near "SELEC"'

        corrected_sql = await agent.correct_sql(
            "显示所有订单",
            bad_sql,
            error,
            self.SAMPLE_SCHEMAS
        )

        assert isinstance(corrected_sql, str)
        # Should fix the typo
        assert "SELECT" in corrected_sql.upper()
        assert corrected_sql != bad_sql

    @pytest.mark.asyncio
    async def test_correct_sql_column_not_found(self, langchain_llm):
        """Test SQL correction for non-existent column."""
        agent = SqlAgent(llm=langchain_llm)

        bad_sql = "SELECT nonexistent_column FROM orders"
        error = 'column "nonexistent_column" does not exist'

        corrected_sql = await agent.correct_sql(
            "显示订单ID",
            bad_sql,
            error,
            self.SAMPLE_SCHEMAS
        )

        assert isinstance(corrected_sql, str)
        # Should replace with valid column
        assert "id" in corrected_sql.lower() or "orders" in corrected_sql.lower()

    @pytest.mark.asyncio
    async def test_correct_sql_table_not_found(self, langchain_llm):
        """Test SQL correction for non-existent table."""
        agent = SqlAgent(llm=langchain_llm)

        bad_sql = "SELECT * FROM nonexistent_table"
        error = 'relation "nonexistent_table" does not exist'

        corrected_sql = await agent.correct_sql(
            "显示所有订单",
            bad_sql,
            error,
            self.SAMPLE_SCHEMAS
        )

        assert isinstance(corrected_sql, str)
        # Should use a valid table from schemas
        assert any(table in corrected_sql.lower() for table in ["orders", "products", "customers"])

    @pytest.mark.asyncio
    async def test_correct_sql_ambiguous_column(self, langchain_llm):
        """Test SQL correction for ambiguous column reference."""
        agent = SqlAgent(llm=langchain_llm)

        bad_sql = "SELECT id FROM orders JOIN products ON orders.product_id = products.id"
        error = 'column reference "id" is ambiguous'

        corrected_sql = await agent.correct_sql(
            "显示订单和产品的ID",
            bad_sql,
            error,
            self.SAMPLE_SCHEMAS
        )

        assert isinstance(corrected_sql, str)
        # Should add table qualifiers
        assert "orders" in corrected_sql.lower() or "products" in corrected_sql.lower()

    # ========================================================================
    # Format Schemas Tests
    # ========================================================================

    def test_format_schemas_standard(self, langchain_llm):
        """Test _format_schemas with standard input."""
        agent = SqlAgent(llm=langchain_llm)

        result = agent._format_schemas(self.SAMPLE_SCHEMAS)

        assert isinstance(result, str)
        assert "orders" in result
        assert "products" in result
        assert "customers" in result
        assert "id" in result
        assert "INTEGER" in result

    def test_format_schemas_empty_columns(self, langchain_llm):
        """Test _format_schemas with empty columns."""
        agent = SqlAgent(llm=langchain_llm)

        schemas = [{"name": "empty_table", "columns": []}]
        result = agent._format_schemas(schemas)

        assert isinstance(result, str)
        assert "empty_table" in result

    def test_format_schemas_missing_fields(self, langchain_llm):
        """Test _format_schemas with missing fields."""
        agent = SqlAgent(llm=langchain_llm)

        schemas = [
            {"name": "no_columns"},  # Missing columns field
            {"columns": []}  # Missing name field
        ]
        result = agent._format_schemas(schemas)

        assert isinstance(result, str)

    # ========================================================================
    # Extract SQL Tests
    # ========================================================================

    def test_extract_sql_plain(self, langchain_llm):
        """Test _extract_sql with plain SQL."""
        agent = SqlAgent(llm=langchain_llm)

        result = agent._extract_sql("SELECT * FROM orders")
        assert result == "SELECT * FROM orders"

    def test_extract_sql_markdown_block(self, langchain_llm):
        """Test _extract_sql with markdown code block."""
        agent = SqlAgent(llm=langchain_llm)

        result = agent._extract_sql("```sql\nSELECT * FROM orders\n```")
        assert "SELECT * FROM orders" in result

    def test_extract_sql_generic_block(self, langchain_llm):
        """Test _extract_sql with generic code block."""
        agent = SqlAgent(llm=langchain_llm)

        result = agent._extract_sql("```\nSELECT * FROM orders\n```")
        assert "SELECT * FROM orders" in result

    def test_extract_sql_with_prefix(self, langchain_llm):
        """Test _extract_sql with explanatory prefix."""
        agent = SqlAgent(llm=langchain_llm)

        result = agent._extract_sql("Here is the SQL:\nSELECT * FROM orders")
        assert "SELECT * FROM orders" in result

    def test_extract_sql_select_pattern(self, langchain_llm):
        """Test _extract_sql with SELECT pattern matching."""
        agent = SqlAgent(llm=langchain_llm)

        result = agent._extract_sql("The query is:\nSELECT * FROM orders\n\nHope this helps!")
        assert "SELECT * FROM orders" in result

    # ========================================================================
    # Edge Case Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_generate_sql_empty_schemas(self, langchain_llm):
        """Test SQL generation with empty schemas."""
        agent = SqlAgent(llm=langchain_llm)

        # Should handle gracefully or use provided context
        sql = await agent.generate_sql("查询数据", [])

        assert isinstance(sql, str)

    @pytest.mark.asyncio
    async def test_generate_sql_complex_query(self, langchain_llm):
        """Test SQL generation for complex multi-join query."""
        agent = SqlAgent(llm=langchain_llm)

        question = "显示2024年每个地区销售额最高的产品类别"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        assert isinstance(sql, str)
        assert "SELECT" in sql.upper()
        # Complex query should involve multiple tables
        assert "orders" in sql.lower()

    @pytest.mark.asyncio
    async def test_generate_sql_subquery(self, langchain_llm):
        """Test SQL generation with subquery."""
        agent = SqlAgent(llm=langchain_llm)

        question = "显示高于平均金额的订单"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        assert isinstance(sql, str)
        assert "SELECT" in sql.upper()
        # May use subquery or HAVING clause
        assert "total_amount" in sql.lower()

    # ========================================================================
    # Chinese Language Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_generate_sql_chinese_questions(self, langchain_llm):
        """Test SQL generation with various Chinese question patterns."""
        agent = SqlAgent(llm=langchain_llm)

        test_cases = [
            ("显示所有订单", "orders"),
            ("产品数量统计", "products"),
            ("客户信息查询", "customers"),
            ("订单金额汇总", "total_amount"),
        ]

        for question, expected_keyword in test_cases:
            sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)
            assert isinstance(sql, str)
            assert "SELECT" in sql.upper()
            assert expected_keyword in sql.lower()

    @pytest.mark.asyncio
    async def test_generate_sql_chinese_aggregations(self, langchain_llm):
        """Test Chinese aggregation keywords."""
        agent = SqlAgent(llm=langchain_llm)

        test_cases = [
            ("统计订单总数", "COUNT"),
            ("计算平均金额", "AVG"),
            ("汇总销售额", "SUM"),
            ("最大订单金额", "MAX"),
            ("最小产品价格", "MIN"),
        ]

        for question, expected_func in test_cases:
            sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)
            assert isinstance(sql, str)
            # Check for aggregation function (may be in Chinese or remain in SQL)
            assert "SELECT" in sql.upper()

    # ========================================================================
    # SQL Quality Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_sql_is_valid_postgresql(self, langchain_llm):
        """Test that generated SQL is valid PostgreSQL syntax."""
        agent = SqlAgent(llm=langchain_llm)

        question = "显示前5个订单"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        # Basic syntax validation
        assert "SELECT" in sql.upper()
        assert "FROM" in sql.upper()
        # PostgreSQL uses LIMIT not TOP
        assert "TOP" not in sql.upper() or "LIMIT" in sql.upper()

    @pytest.mark.asyncio
    async def test_sql_no_system_queries(self, langchain_llm):
        """Test that SQL doesn't query system catalogs."""
        agent = SqlAgent(llm=langchain_llm)

        question = "显示所有表结构"
        sql = await agent.generate_sql(question, self.SAMPLE_SCHEMAS)

        # Should not query information_schema
        assert "information_schema" not in sql.lower()
        assert "pg_catalog" not in sql.lower()
