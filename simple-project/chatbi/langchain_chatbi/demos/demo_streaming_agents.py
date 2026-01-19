#!/usr/bin/env python3
"""
Interactive Demo: Streaming Agents

This script demonstrates the streaming capabilities of:
1. QueryReasoningAgent - Streams reasoning plan
2. AnswerSummarizationAgent - Streams natural language answer

Usage:
    python demos/demo_streaming_agents.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_chatbi.llm.langchain_llm import create_langchain_llm
from langchain_chatbi.agents.reasoning_agent import QueryReasoningAgent
from langchain_chatbi.agents.answer_agent import AnswerSummarizationAgent


async def demo_reasoning_streaming(agent: QueryReasoningAgent):
    """Demo reasoning agent streaming."""
    print("\n" + "=" * 60)
    print("📊 Query Reasoning Agent (Streaming)")
    print("=" * 60)

    question = "分析2023年各地区的销售趋势"
    print(f"\n❓ Question: {question}")
    print("\n🤔 Generating reasoning plan...\n")

    accumulated = ""
    async for chunk in agent.generate_reasoning_stream(
        question=question,
        mdl_context="Sales table with region, date, amount columns",
        history_queries=""
    ):
        print(chunk, end="", flush=True)
        accumulated += chunk

    print(f"\n\n✅ Completed ({len(accumulated)} characters)")


async def demo_answer_streaming(agent: AnswerSummarizationAgent):
    """Demo answer agent streaming."""
    print("\n" + "=" * 60)
    print("💬 Answer Summarization Agent (Streaming)")
    print("=" * 60)

    question = "各地区销售额如何？"
    result_data = [
        {"region": "North", "total": 150000},
        {"region": "South", "total": 120000},
        {"region": "East", "total": 180000},
        {"region": "West", "total": 90000}
    ]

    print(f"\n❓ Question: {question}")
    print(f"📊 Data: {len(result_data)} regions")
    print("\n✍️  Generating answer...\n")

    accumulated = ""
    async for chunk in agent.generate_answer_stream(
        question=question,
        query_metadata={},
        result_data=result_data,
        chart_config={"chartType": "bar", "title": "Sales by Region"},
        language="zh-CN"
    ):
        print(chunk, end="", flush=True)
        accumulated += chunk

    print(f"\n\n✅ Completed ({len(accumulated)} characters)")


async def main():
    print("=" * 60)
    print("Streaming Agents Demo")
    print("=" * 60)

    # Check for API key
    if not os.getenv("LLM_API_KEY"):
        print("\n⚠️  LLM_API_KEY not set. Please set it to run this demo.")
        print("   Example: export LLM_API_KEY='your-api-key'")
        return

    # Create LLM and agents
    print("\n🔧 Initializing LLM and agents...")
    llm = create_langchain_llm()
    reasoning_agent = QueryReasoningAgent(llm=llm)
    answer_agent = AnswerSummarizationAgent(llm=llm)
    print("✅ Ready!")

    # Run demos
    await demo_reasoning_streaming(reasoning_agent)
    await demo_answer_streaming(answer_agent)

    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
