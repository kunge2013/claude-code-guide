#!/usr/bin/env python3
"""
Interactive Demo: IntentClassificationAgent

This script demonstrates the IntentClassificationAgent's ability to:
1. Classify user intents (query, greeting, help, clarification)
2. Detect ambiguity in questions
3. Provide confidence scores

Usage:
    python demos/demo_intent_agent.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_chatbi.llm.langchain_llm import create_langchain_llm
from langchain_chatbi.agents.intent_agent import IntentClassificationAgent


async def main():
    print("=" * 60)
    print("Intent Classification Agent Demo")
    print("=" * 60)
    print()

    # Check for API key
    if not os.getenv("LLM_API_KEY"):
        print("⚠️  LLM_API_KEY not set. Please set it to run this demo.")
        print("   Example: export LLM_API_KEY='your-api-key'")
        return

    # Create LLM and agent
    print("🔧 Initializing LLM and agent...")
    llm = create_langchain_llm()
    agent = IntentClassificationAgent(llm=llm)
    print("✅ Ready!\n")

    # Test questions
    test_questions = [
        ("上个月销售额是多少？", "Query about sales data"),
        ("Hello!", "Greeting"),
        ("How can you help me?", "Help request"),
        ("给我看看数据", "Potentially ambiguous"),
        ("What are the top 5 products by revenue in 2023?", "Clear query"),
    ]

    print("📝 Testing Intent Classification")
    print("-" * 60)

    for question, description in test_questions:
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        print(f"Description: {description}")
        print("-" * 60)

        try:
            # Classify intent
            intent_result = await agent.classify(question)

            print(f"📊 Intent: {intent_result.intent}")
            print(f"💭 Reasoning: {intent_result.reasoning}")
            print(f"📈 Confidence: {intent_result.confidence:.2f}")

            # If it's a query, check for ambiguity
            if intent_result.intent == "query":
                ambiguity_result = await agent.check_ambiguity(question)

                if ambiguity_result.is_ambiguous:
                    print(f"\n⚠️  Ambiguity Detected!")
                    print(f"   Type: {ambiguity_result.ambiguity_type}")
                    print(f"   Clarification: {ambiguity_result.clarification_question}")
                    if ambiguity_result.options:
                        print(f"   Options: {ambiguity_result.options}")
                else:
                    print(f"\n✅ Question is clear")

        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"\n{'='*60}")
    print("Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
