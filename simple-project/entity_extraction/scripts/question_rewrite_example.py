#!/usr/bin/env python3
"""
Question Rewrite Example Script

This script demonstrates how to use the QuestionRewrite service
to rewrite natural language questions into structured, explicit questions
that are easier for downstream entity extraction and SQL generation.

Usage:
    python scripts/question_rewrite_example.py
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_entity_extraction.rewrite import (
    QuestionRewriter,
    TimeNormalizer,
    EntityMapper,
)
from langchain_entity_extraction.utils.logger import setup_logger

# Setup logger
setup_logger()


async def example_1_basic_rewrite():
    """Example 1: Basic question rewriting."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Question Rewriting")
    print("=" * 70)

    questions = [
        "今年cdn产品金额是多少",
        "上月ecs产品数量是多少",
        "去年oss产品收入是多少",
    ]

    rewriter = QuestionRewriter()

    for question in questions:
        print(f"\n原始问题: {question}")
        result = await rewriter.rewrite(question, use_simple_prompt=True)

        if result.success:
            print(f"改写问题: {result.rewritten.rewritten}")
            print(f"识别实体: {result.rewritten.entities}")
            if result.rewritten.reasoning:
                print(f"推理过程: {result.rewritten.reasoning}")
            if result.rewritten.changes_made:
                print(f"改动内容: {', '.join(result.rewritten.changes_made)}")
        else:
            print(f"改写失败: {result.errors}")


async def example_2_time_normalization():
    """Example 2: Time normalization demonstrations."""
    print("\n" + "=" * 70)
    print("Example 2: Time Normalization")
    print("=" * 70)

    normalizer = TimeNormalizer()

    time_expressions = [
        "今年",
        "去年",
        "本月",
        "上月",
        "本季度",
        "上季度",
        "最近7天",
    ]

    print("\n时间表达规范化:")
    for expr in time_expressions:
        normalized = normalizer.normalize(expr)
        print(f"  {expr:12} → {normalized}")


async def example_3_entity_mapping():
    """Example 3: Entity mapping demonstrations."""
    print("\n" + "=" * 70)
    print("Example 3: Entity Mapping")
    print("=" * 70)

    mapper = EntityMapper()

    # Product mapping examples
    print("\n产品名称映射:")
    product_names = ["cdn", "CDN", "内容分发网络", "ecs", "云主机"]
    for name in product_names:
        mapped = mapper.map_product_name(name)
        formatted = mapper.format_product_for_query(mapped)
        print(f"  {name:12} → {mapped:6} → {formatted}")

    # Field mapping examples
    print("\n字段名称映射:")
    field_names = ["金额", "费用", "数量", "收入", "用户数"]
    for name in field_names:
        mapped = mapper.map_field_name(name)
        print(f"  {name:6} → {mapped}")


async def example_4_batch_rewriting():
    """Example 4: Batch question rewriting."""
    print("\n" + "=" * 70)
    print("Example 4: Batch Question Rewriting")
    print("=" * 70)

    questions = [
        "今年cdn产品金额是多少",
        "上月ecs产品数量是多少",
        "去年oss产品收入是多少",
        "本季度rds产品用户数是多少",
        "最近7天slb产品流量是多少",
    ]

    print(f"\n批量改写 {len(questions)} 个问题...")

    rewriter = QuestionRewriter()
    batch_result = await rewriter.rewrite_batch(
        questions,
        max_concurrency=3,
        use_simple_prompt=True
    )

    print(f"\n批量改写结果:")
    print(f"  总数: {batch_result.total_count}")
    print(f"  成功: {batch_result.successful_count}")
    print(f"  失败: {batch_result.failed_count}")
    print(f"  耗时: {batch_result.total_time_ms:.2f}ms")

    print("\n详细结果:")
    for i, result in enumerate(batch_result.results, 1):
        if result.success:
            print(f"\n  [{i}] {result.original.content}")
            print(f"      → {result.rewritten.rewritten}")
        else:
            print(f"\n  [{i}] {result.original.content}")
            print(f"      → 失败: {result.errors}")


async def example_5_complex_questions():
    """Example 5: Complex question rewriting."""
    print("\n" + "=" * 70)
    print("Example 5: Complex Question Rewriting")
    print("=" * 70)

    complex_questions = [
        "今年cdn和ecs产品的总金额是多少",
        "上月北京地区的云主机订单数量",
        "去年三季度对象存储的收入",
        "cdn产品本月比上月的增长率",
    ]

    rewriter = QuestionRewriter()

    for question in complex_questions:
        print(f"\n原始问题: {question}")
        result = await rewriter.rewrite(question, use_simple_prompt=True)

        if result.success:
            print(f"改写问题: {result.rewritten.rewritten}")
            print(f"识别实体: {result.rewritten.entities}")
        else:
            print(f"改写失败: {result.errors}")


async def example_6_context_aware_rewriting():
    """Example 6: Context-aware question rewriting."""
    print("\n" + "=" * 70)
    print("Example 6: Context-Aware Rewriting")
    print("=" * 70)

    rewriter = QuestionRewriter()

    # First question establishes context
    print("\n对话示例:")
    print("  用户: 今年cdn产品金额是多少")

    result1 = await rewriter.rewrite("今年cdn产品金额是多少", use_simple_prompt=True)
    if result1.success:
        print(f"  改写: {result1.rewritten.rewritten}")

    # Follow-up question using context
    print("\n  用户: 那ecs呢？")

    result2 = await rewriter.rewrite(
        "ecs产品金额是多少",
        context={
            "previous_question": "今年cdn产品金额是多少",
            "time": "2026年",
            "field": "出账金额"
        },
        use_simple_prompt=True
    )
    if result2.success:
        print(f"  改写: {result2.rewritten.rewritten}")


async def example_7_synchronous_api():
    """Example 7: Using synchronous API."""
    print("\n" + "=" * 70)
    print("Example 7: Synchronous API Usage")
    print("=" * 70)

    rewriter = QuestionRewriter()

    # Use synchronous wrapper
    question = "今年cdn产品金额是多少"
    print(f"\n原始问题: {question}")

    result = rewriter.rewrite_sync(question, use_simple_prompt=True)

    if result.success:
        print(f"改写问题: {result.rewritten.rewritten}")
        print(f"耗时: {result.processing_time_ms:.2f}ms")


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("LangChain Question Rewrite Service - Examples")
    print("=" * 70)
    print("\n注意: 这些示例需要配置有效的 LLM API Key")
    print("请在 .env 文件中设置 OPENAI_API_KEY 或 ZHIPUAI_API_KEY")

    try:
        # Time and entity mapping examples (no LLM required)
        await example_2_time_normalization()
        await example_3_entity_mapping()

        print("\n" + "=" * 70)
        print("LLM-dependent Examples")
        print("=" * 70)
        print("\n以下示例需要 LLM API 调用...")

        # Uncomment these to run with actual LLM calls
        await example_1_basic_rewrite()
        await example_4_batch_rewriting()
        await example_5_complex_questions()
        await example_6_context_aware_rewriting()
        await example_7_synchronous_api()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
