#!/usr/bin/env python3
"""
向量检索功能演示脚本

展示如何使用三种不同的检索模式：
- fuzzy: 模糊字符串匹配
- vector: 基于向量的语义搜索
- hybrid: 混合检索
"""
import os

# 设置离线模式（避免联网问题）
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

from resume_agent.config import Config
from resume_agent.strategies import StrategyFactory


def demo_search_modes():
    """演示三种检索模式"""
    # 配置
    config = Config()
    config.VECTOR_THRESHOLD = 0.5

    # 测试查询
    test_queries = [
        "人事行政",
        "互联网",
        "大学生",
        "销售",  # 知识库中没有的
    ]

    print("=" * 80)
    print("简历模板知识库 - 三种检索模式演示")
    print("=" * 80)
    print(f"向量阈值: {config.VECTOR_THRESHOLD}")
    print(f"混合权重 - 向量: {config.HYBRID_WEIGHT_VECTOR}, 模糊: {config.HYBRID_WEIGHT_FUZZY}")
    print("=" * 80)

    for query in test_queries:
        print(f"\n【查询】: {query}")
        print("-" * 80)

        results = {}

        # 测试三种模式
        for mode in ["fuzzy", "vector", "hybrid"]:
            try:
                strategy = StrategyFactory.create_strategy(mode, config)
                result = strategy.search(query)
                best_match = result.get_best_match()

                if best_match and best_match.download_link:
                    results[mode] = {
                        "name": best_match.template_name,
                        "score": best_match.score,
                        "type": best_match.match_type
                    }
                else:
                    results[mode] = None
            except Exception as e:
                results[mode] = f"错误: {e}"

        # 显示结果
        for mode, data in results.items():
            if data and isinstance(data, dict):
                print(f"  {mode:6s}: {data['name']:20s} (score: {data['score']:.4f}, type: {data['type']})")
            elif data:
                print(f"  {mode:6s}: {data}")
            else:
                print(f"  {mode:6s}: 无匹配结果")


def demo_strategy_usage():
    """演示直接使用策略"""
    print("\n" + "=" * 80)
    print("直接使用策略 API")
    print("=" * 80)

    from resume_agent.strategies import VectorSearchStrategy

    config = Config()
    strategy = VectorSearchStrategy(config)

    # 单次搜索
    result = strategy.search("人事行政")
    print(f"\n查询: 人事行政")
    print(f"策略: {result.strategy_type}")
    print(f"匹配数: {result.total_results}")

    for i, match in enumerate(result.matches[:3], 1):
        print(f"  {i}. {match.template_name} (score: {match.score:.4f})")

    # 获取最佳匹配
    best = result.get_best_match()
    if best:
        print(f"\n最佳匹配: {best.template_name}")


def demo_with_agent():
    """演示通过 Agent 使用"""
    print("\n" + "=" * 80)
    print("通过 Agent 使用（推荐）")
    print("=" * 80)

    from resume_agent import ResumeTemplateAgent

    # 设置检索模式
    Config.SEARCH_MODE = "vector"

    agent = ResumeTemplateAgent()
    result = agent.query("互联网")
    print(f"\nAgent 回复:\n{result}")


if __name__ == "__main__":
    # 运行演示
    demo_search_modes()
    demo_strategy_usage()
    demo_with_agent()

    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)
