"""Unit tests for question rewriting functionality."""

import pytest
from datetime import date
from unittest.mock import Mock, AsyncMock, patch

from langchain_entity_extraction.rewrite.time_normalizer import TimeNormalizer
from langchain_entity_extraction.rewrite.entity_mapper import EntityMapper
from langchain_entity_extraction.rewrite.question_rewriter import QuestionRewriter
from langchain_entity_extraction.models.rewrite_models import (
    OriginalQuestion,
    RewrittenQuestion,
    RewriteResult,
)


class TestTimeNormalizer:
    """Tests for TimeNormalizer class."""

    def test_normalize_this_year(self):
        """Test normalizing '今年' to current year."""
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("今年")
        assert result == "2026年"

    def test_normalize_last_year(self):
        """Test normalizing '去年' to last year."""
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("去年")
        assert result == "2025年"

    def test_normalize_this_month(self):
        """Test normalizing '本月' to current month."""
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("本月")
        assert result == "2026年1月"

    def test_normalize_last_month(self):
        """Test normalizing '上月' to last month."""
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("上月")
        assert result == "2025年12月"

    def test_normalize_last_month_january(self):
        """Test normalizing '上月' when current month is January."""
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("上月")
        assert result == "2025年12月"

    def test_normalize_last_month_february(self):
        """Test normalizing '上月' when current month is February."""
        normalizer = TimeNormalizer(date(2026, 2, 15))
        result = normalizer.normalize("上月")
        assert result == "2026年1月"

    def test_normalize_this_quarter(self):
        """Test normalizing '本季度' to current quarter."""
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("本季度")
        assert result == "2026年Q1"

    def test_normalize_last_quarter(self):
        """Test normalizing '上季度' to last quarter."""
        normalizer = TimeNormalizer(date(2026, 2, 15))
        result = normalizer.normalize("上季度")
        assert result == "2025年Q4"

    def test_normalize_recent_days(self):
        """Test normalizing '最近N天' to date range."""
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("最近7天")
        assert "2026-01-09" in result
        assert "2026-01-15" in result

    def test_extract_time_from_text(self):
        """Test extracting time expression from text."""
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.extract_time_from_text("今年cdn产品金额")

        assert result["found"] is True
        assert result["original"] == "今年"
        assert result["normalized"] == "2026年"
        assert result["type"] == "thisyear"

    def test_extract_time_not_found(self):
        """Test when time expression is not found."""
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.extract_time_from_text("cdn产品金额")

        assert result["found"] is False
        assert result["original"] is None

    def test_get_current_date_info(self):
        """Test getting current date information."""
        normalizer = TimeNormalizer(date(2026, 1, 15))
        info = normalizer.get_current_date_info()

        assert info["year"] == 2026
        assert info["month"] == 1
        assert info["quarter"] == 1


class TestEntityMapper:
    """Tests for EntityMapper class."""

    def test_map_product_name_lowercase(self):
        """Test mapping lowercase product name."""
        mapper = EntityMapper()
        result = mapper.map_product_name("cdn")
        assert result == "cdn"

    def test_map_product_name_uppercase(self):
        """Test mapping uppercase product name."""
        mapper = EntityMapper()
        result = mapper.map_product_name("CDN")
        assert result == "cdn"

    def test_map_product_name_alias(self):
        """Test mapping product alias."""
        mapper = EntityMapper()
        result = mapper.map_product_name("内容分发网络")
        assert result == "cdn"

    def test_map_product_name_unknown(self):
        """Test mapping unknown product name."""
        mapper = EntityMapper()
        result = mapper.map_product_name("unknown_product")
        assert result == "unknown_product"

    def test_map_field_name_amount(self):
        """Test mapping field name variations to '出账金额'."""
        mapper = EntityMapper()

        assert mapper.map_field_name("金额") == "出账金额"
        assert mapper.map_field_name("费用") == "出账金额"
        assert mapper.map_field_name("总计") == "出账_amount"

    def test_map_field_name_quantity(self):
        """Test mapping field name variations to '订单数量'."""
        mapper = EntityMapper()

        assert mapper.map_field_name("数量") == "订单数量"
        assert mapper.map_field_name("个数") == "订单数量"

    def test_extract_products_from_text(self):
        """Test extracting products from text."""
        mapper = EntityMapper()
        result = mapper.extract_products_from_text("cdn和ecs产品的金额")

        assert len(result) == 2
        assert result[0]["standard_id"] == "cdn"
        assert result[1]["standard_id"] == "ecs"

    def test_extract_fields_from_text(self):
        """Test extracting fields from text."""
        mapper = EntityMapper()
        result = mapper.extract_fields_from_text("查看金额和数量")

        assert len(result) == 2
        assert result[0]["standard_name"] == "出账金额"
        assert result[1]["standard_name"] == "订单数量"

    def test_format_product_for_query(self):
        """Test formatting product for query."""
        mapper = EntityMapper()
        result = mapper.format_product_for_query("cdn")
        assert result == "产品ID为cdn"

    def test_format_field_for_query(self):
        """Test formatting field for query."""
        mapper = EntityMapper()
        result = mapper.format_field_for_query("出账金额")
        assert result == "出账金额"

    def test_format_time_for_query(self):
        """Test formatting time for query."""
        mapper = EntityMapper()
        result = mapper.format_time_for_query("2026年")
        assert result == "时间为2026年"


class TestQuestionRewriter:
    """Tests for QuestionRewriter class."""

    @pytest.mark.asyncio
    async def test_rewrite_simple_question(self):
        """Test rewriting a simple question."""
        mock_llm = Mock()
        mock_llm.ainvoke = AsyncMock(return_value=Mock(
            content='''{"rewritten": "产品ID为cdn，时间为2026年的出账金额是多少", "entities": {"product_id": "cdn", "time": "2026年", "field": "出账金额"}, "reasoning": "改写完成", "changes_made": ["时间规范化", "产品ID规范化"]}'''
        ))

        rewriter = QuestionRewriter(llm=mock_llm)
        result = await rewriter.rewrite("今年cdn产品金额是多少")

        assert result.success is True
        assert result.rewritten is not None
        assert "产品ID为cdn" in result.rewritten.rewritten
        assert "2026年" in result.rewritten.rewritten
        assert "出账金额" in result.rewritten.rewritten

    @pytest.mark.asyncio
    async def test_rewrite_with_context(self):
        """Test rewriting with context information."""
        mock_llm = Mock()
        mock_llm.ainvoke = AsyncMock(return_value=Mock(
            content='''{"rewritten": "产品ID为cdn的出账金额是多少", "entities": {"product_id": "cdn", "field": "出账金额"}, "reasoning": "使用上下文信息", "changes_made": []}'''
        ))

        rewriter = QuestionRewriter(llm=mock_llm)
        result = await rewriter.rewrite(
            "金额是多少",
            context={"product": "cdn", "time": "2026年"}
        )

        assert result.success is True
        assert result.rewritten is not None

    @pytest.mark.asyncio
    async def test_rewrite_batch(self):
        """Test batch rewriting."""
        mock_llm = Mock()
        call_count = 0

        async def mock_invoke(messages):
            call_count += 1
            return Mock(
                content=f'''{{"rewritten": "改写后的问题{call_count}", "entities": {{}}, "reasoning": "", "changes_made": []}}'''
            )

        mock_llm.ainvoke = mock_invoke

        rewriter = QuestionRewriter(llm=mock_llm)
        result = await rewriter.rewrite_batch([
            "问题1",
            "问题2",
            "问题3"
        ], max_concurrency=2)

        assert result.total_count == 3
        assert result.successful_count == 3
        assert result.failed_count == 0

    @pytest.mark.asyncio
    async def test_rewrite_with_llm_error(self):
        """Test handling LLM error."""
        mock_llm = Mock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM error"))

        rewriter = QuestionRewriter(llm=mock_llm, max_retries=1)
        result = await rewriter.rewrite("测试问题")

        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_rewrite_with_invalid_json(self):
        """Test handling invalid JSON response."""
        mock_llm = Mock()
        mock_llm.ainvoke = AsyncMock(return_value=Mock(
            content='改写后问题：产品ID为cdn，时间为2026年的出账金额是多少'
        ))

        rewriter = QuestionRewriter(llm=mock_llm)
        result = await rewriter.rewrite("今年cdn产品金额是多少")

        # Should still succeed but with fallback parsing
        assert result.success is True
        assert result.rewritten is not None


class TestRewriteModels:
    """Tests for rewrite data models."""

    def test_original_question_model(self):
        """Test OriginalQuestion model."""
        question = OriginalQuestion(
            content="测试问题",
            domain="billing",
            context="测试上下文"
        )

        assert question.content == "测试问题"
        assert question.domain == "billing"
        assert question.context == "测试上下文"

    def test_rewritten_question_model(self):
        """Test RewrittenQuestion model."""
        rewritten = RewrittenQuestion(
            original="原始问题",
            rewritten="改写后问题",
            entities={"product_id": "cdn"},
            confidence=0.95,
            reasoning="改写说明",
            changes_made=["改动1"]
        )

        assert rewritten.original == "原始问题"
        assert rewritten.rewritten == "改写后问题"
        assert rewritten.confidence == 0.95
        assert len(rewritten.changes_made) == 1

    def test_rewrite_result_model(self):
        """Test RewriteResult model."""
        original = OriginalQuestion(content="测试")
        rewritten = RewrittenQuestion(
            original="测试",
            rewritten="改写后"
        )

        result = RewriteResult(
            success=True,
            original=original,
            rewritten=rewritten
        )

        assert result.success is True
        assert result.original == original
        assert result.rewritten == rewritten

    def test_confidence_validation(self):
        """Test confidence field validation."""
        with pytest.raises(ValueError):
            RewrittenQuestion(
                original="测试",
                rewritten="改写后",
                confidence=1.5  # Invalid: > 1.0
            )

    def test_rewritten_question_defaults(self):
        """Test RewrittenQuestion default values."""
        rewritten = RewrittenQuestion(
            original="原始",
            rewritten="改写后"
        )

        assert rewritten.confidence == 0.8  # Default
        assert rewritten.entities == {}  # Default
        assert rewritten.changes_made == []  # Default
