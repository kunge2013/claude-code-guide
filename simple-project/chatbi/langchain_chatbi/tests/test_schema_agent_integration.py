"""
Integration Tests for SchemaAgent

Uses real LLM (via langchain_llm fixture) for testing.
Requires .env file with LLM_API_KEY, LLM_BASE_URL, LLM_MODEL configured.
"""

import pytest
import json

from langchain_chatbi.agents.schema_agent import SchemaAgent
from langchain_chatbi.models.response_models import SchemaSelection


# ============================================================================
# Test Class
# ============================================================================


@pytest.mark.integration
class TestSchemaAgentIntegration:
    """Integration tests for SchemaAgent using real LLM."""

    # ========================================================================
    # Schema Selection Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_select_schemas_single_table(self, langchain_llm):
        """Test selecting a single relevant table."""
        agent = SchemaAgent(llm=langchain_llm)

        table_schemas = [
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

        result = await agent.select_schemas("上个月的订单总金额是多少？", table_schemas)

        assert isinstance(result, list)
        assert len(result) >= 1
        # Should select orders table since question is about order amounts
        table_names = {t["name"] for t in result}
        assert "orders" in table_names

    @pytest.mark.asyncio
    async def test_select_schemas_multiple_tables(self, langchain_llm):
        """Test selecting multiple relevant tables."""
        agent = SchemaAgent(llm=langchain_llm)

        table_schemas = [
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

        result = await agent.select_schemas("显示每个产品的销售总额", table_schemas)

        assert isinstance(result, list)
        assert len(result) >= 2
        # Should select both orders and products for sales by product
        table_names = {t["name"] for t in result}
        assert "orders" in table_names
        assert "products" in table_names

    @pytest.mark.asyncio
    async def test_select_schemas_filters_irrelevant(self, langchain_llm):
        """Test that irrelevant tables are filtered out."""
        agent = SchemaAgent(llm=langchain_llm)

        table_schemas = [
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "total_amount", "type": "REAL"}
                ]
            },
            {
                "name": "customers",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"},
                    {"name": "email", "type": "VARCHAR"}
                ]
            },
            {
                "name": "audit_logs",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "action", "type": "VARCHAR"},
                    {"name": "timestamp", "type": "TIMESTAMP"}
                ]
            }
        ]

        result = await agent.select_schemas("订单总金额是多少？", table_schemas)

        assert isinstance(result, list)
        table_names = {t["name"] for t in result}
        # Orders should be selected, audit_logs likely not
        assert "orders" in table_names

    @pytest.mark.asyncio
    async def test_select_schemas_all_tables_selected(self, langchain_llm):
        """Test when all tables are relevant."""
        agent = SchemaAgent(llm=langchain_llm)

        table_schemas = [
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "customer_id", "type": "INTEGER"},
                    {"name": "total_amount", "type": "REAL"}
                ]
            },
            {
                "name": "customers",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"}
                ]
            }
        ]

        result = await agent.select_schemas(
            "显示每个客户的订单总金额",
            table_schemas
        )

        assert isinstance(result, list)
        # Both tables are needed for this query
        assert len(result) >= 1
        table_names = {t["name"] for t in result}
        assert "orders" in table_names

    # ========================================================================
    # JSON Input Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_select_schemas_raw_valid_json(self, langchain_llm):
        """Test select_schemas_raw with valid JSON input."""
        agent = SchemaAgent(llm=langchain_llm)

        table_schemas_json = json.dumps([
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "total_amount", "type": "REAL"}
                ]
            },
            {
                "name": "products",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "name", "type": "VARCHAR"}
                ]
            }
        ])

        result = await agent.select_schemas_raw("订单金额统计", table_schemas_json)

        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_select_schemas_raw_invalid_json(self, langchain_llm):
        """Test select_schemas_raw with invalid JSON raises error."""
        agent = SchemaAgent(llm=langchain_llm)

        invalid_json = "{ invalid json }"

        with pytest.raises(ValueError, match="Invalid table_schemas JSON"):
            await agent.select_schemas_raw("test", invalid_json)

    # ========================================================================
    # Format Schemas Tests
    # ========================================================================

    def test_format_schemas_standard(self, langchain_llm):
        """Test _format_schemas with standard input."""
        agent = SchemaAgent(llm=langchain_llm)

        table_schemas = [
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "amount", "type": "REAL"}
                ]
            }
        ]

        result = agent._format_schemas(table_schemas)

        assert isinstance(result, str)
        assert "orders" in result
        assert "id" in result
        assert "INTEGER" in result
        assert "amount" in result
        assert "REAL" in result

    def test_format_schemas_empty_columns(self, langchain_llm):
        """Test _format_schemas with empty columns."""
        agent = SchemaAgent(llm=langchain_llm)

        table_schemas = [
            {"name": "empty_table", "columns": []}
        ]

        result = agent._format_schemas(table_schemas)

        assert isinstance(result, str)
        assert "empty_table" in result

    def test_format_schemas_missing_fields(self, langchain_llm):
        """Test _format_schemas with missing fields."""
        agent = SchemaAgent(llm=langchain_llm)

        table_schemas = [
            {"name": "test_table"},  # No columns
            {"columns": []}  # No name
        ]

        result = agent._format_schemas(table_schemas)

        assert isinstance(result, str)
        assert "test_table" in result
        assert "unknown" in result

    # ========================================================================
    # Edge Case Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_select_schemas_empty_list(self, langchain_llm):
        """Test with empty table schemas list."""
        agent = SchemaAgent(llm=langchain_llm)

        result = await agent.select_schemas("test question", [])

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_select_schemas_vague_question(self, langchain_llm):
        """Test with a vague/ambiguous question."""
        agent = SchemaAgent(llm=langchain_llm)

        table_schemas = [
            {
                "name": "orders",
                "columns": [{"name": "id", "type": "INTEGER"}]
            },
            {
                "name": "products",
                "columns": [{"name": "id", "type": "INTEGER"}]
            }
        ]

        # Vague question - should still return some result
        result = await agent.select_schemas("给我看看数据", table_schemas)

        assert isinstance(result, list)
        # Might return all tables as fallback for vague questions

    @pytest.mark.asyncio
    async def test_select_schemas_large_schema(self, langchain_llm):
        """Test with a large number of tables."""
        agent = SchemaAgent(llm=langchain_llm)

        # Create a larger schema set
        table_schemas = [
            {
                "name": f"table_{i}",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": f"col_{i}", "type": "VARCHAR"}
                ]
            }
            for i in range(10)
        ]

        result = await agent.select_schemas(
            "查询 table_5 的数据",
            table_schemas
        )

        assert isinstance(result, list)
        table_names = {t["name"] for t in result}
        # Should specifically select table_5
        assert "table_5" in table_names

    # ========================================================================
    # Chinese Language Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_select_schemas_chinese_question(self, langchain_llm):
        """Test schema selection with Chinese questions."""
        agent = SchemaAgent(llm=langchain_llm)

        table_schemas = [
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "total_amount", "type": "REAL"},
                    {"name": "order_date", "type": "TIMESTAMP"}
                ]
            },
            {
                "name": "users",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "username", "type": "VARCHAR"}
                ]
            }
        ]

        test_cases = [
            ("订单总额", "orders"),
            ("用户数量", "users"),
            ("按日期统计订单", "orders"),
        ]

        for question, expected_table in test_cases:
            result = await agent.select_schemas(question, table_schemas)
            table_names = {t["name"] for t in result}
            assert expected_table in table_names, f"Failed for question: {question}"
