#!/usr/bin/env python3
"""
Resume Template Agent - Entry Point and Demo Script

This script demonstrates how to use the Resume Template Agent with Zhipu AI.

Usage:
    python resume_agent.py                    # Run demo with example queries
    python resume_agent.py --interactive      # Run in interactive mode
    python resume_agent.py --query "人事行政简历模板"  # Single query mode
"""
import os
import sys
import argparse

# Clear proxy settings to avoid API call issues
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    if proxy_var in os.environ:
        del os.environ[proxy_var]

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from resume_agent import ResumeTemplateAgent, Config


# Example queries for demo
EXAMPLE_QUERIES = [
    "人事行政简历模板",
    "大学生简历模板",
    "通用简历模板",
    "有哪些简历模板？",
    "互联网职位模板",
    "医生护士简历模板",
]


def print_separator(char="=", length=60):
    """Print a separator line"""
    print(char * length)


def run_demo(agent: ResumeTemplateAgent):
    """Run demo with example queries"""
    print_separator()
    print("简历模板知识库 Agent - 演示模式")
    print_separator()
    print(f"模型: {Config.ANTHROPIC_DEFAULT_HAIKU_MODEL}")
    print(f"API: {Config.ANTHROPIC_BASE_URL}")
    print(f"检索模式: {Config.SEARCH_MODE.upper()}")
    print_separator()

    for i, query in enumerate(EXAMPLE_QUERIES, 1):
        print(f"\n【查询 {i}】用户: {query}")
        print("-" * 40)

        response = agent.query(query)
        print(f"Agent: {response}")

        print_separator()


def run_interactive(agent: ResumeTemplateAgent):
    """Run in interactive mode"""
    print_separator()
    print("简历模板知识库 Agent - 交互模式")
    print_separator()
    print("输入 'quit' 或 'exit' 退出")
    print("输入 'help' 查看帮助信息")
    print_separator()

    chat_history = []

    while True:
        try:
            user_input = input("\n您: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "退出"]:
                print("再见！")
                break

            if user_input.lower() in ["help", "帮助"]:
                print("\n使用帮助：")
                print("- 直接输入简历模板名称，如 '人事行政简历模板'")
                print("- 输入关键词，如 '大学生' 或 '互联网'")
                print("- 输入 '有哪些简历模板' 查看所有可用模板")
                print("- 输入 'quit' 或 'exit' 退出")
                continue

            print("\nAgent: ", end="", flush=True)
            response = agent.query(user_input, chat_history)
            print(response)

            # Update chat history (simple implementation)
            # In production, you would want proper message formatting
            # chat_history.extend([...])

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n错误: {e}")


def run_single_query(agent: ResumeTemplateAgent, query: str):
    """Run a single query and print the result"""
    print_separator()
    print(f"查询: {query}")
    print_separator()

    response = agent.query(query)
    print(response)

    print_separator()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="简历模板知识库 Agent - 基于 LangChain 和智谱 AI"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="运行交互模式"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="执行单次查询"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细输出（包括 LangChain 日志）"
    )

    args = parser.parse_args()

    # Set verbose mode for LangChain
    if args.verbose:
        os.environ["LANGCHAIN_VERBOSE"] = "true"

    try:
        # Initialize agent
        print("正在初始化 Agent...")
        agent = ResumeTemplateAgent()
        print(f"Agent 初始化成功: {agent}")
        print()

        # Run in the requested mode
        if args.query:
            run_single_query(agent, args.query)
        elif args.interactive:
            run_interactive(agent)
        else:
            run_demo(agent)

    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
