"""
Main agent implementation for Resume Template Agent
Uses LangChain with Zhipu AI (BigModel) GLM-4.7 model
"""
import os
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain.agents.factory import create_agent
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import BaseTool

from .config import Config
from .tools import search_resume_template, list_all_templates, get_template_by_exact_name


# System prompt for the agent
SYSTEM_PROMPT = """你是一个专业的简历模板知识库助手。你的职责是根据用户的需求，从简历模板数据库中快速找到匹配的模板，并提供对应的下载链接。

## 可用工具

你有以下工具可以使用：

1. **search_resume_template**: 搜索简历模板（推荐使用）
   - 输入：搜索关键词（如"人事行政"、"大学生"、"互联网"）
   - 支持模糊匹配，即使关键词不完全准确也能找到相关模板

2. **list_all_templates**: 列出所有可用的简历模板
   - 当用户询问"有哪些模板"或"查看所有模板"时使用

3. **get_template_by_exact_name**: 按精确名称获取模板
   - 当用户提供完整准确的模板名称时使用

## 输出格式

找到匹配的模板后，按以下格式返回：

**模板名称**: {模板名称}
**下载地址**: {百度网盘链接}

如果找到多个匹配项，依次列出。

## 注意事项

1. **准确性优先**：确保返回的下载链接与用户请求的模板完全匹配
2. **友好提示**：使用清晰的中文，避免技术术语
3. **主动建议**：当找不到精确匹配时，主动列出可用模板供用户选择
4. **链接完整性**：返回完整的百度网盘链接，包括提取码

现在，请帮助用户找到他们需要的简历模板！
"""


class ResumeTemplateAgent:
    """Resume Template Agent using LangChain and Zhipu AI"""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the agent

        Args:
            config: Optional Config object. If not provided, uses default Config.
        """
        self.config = config or Config()
        self.config.validate()

        # Initialize tools
        self.tools: list[BaseTool] = [
            search_resume_template,
            list_all_templates,
            get_template_by_exact_name,
        ]

        # Create the agent graph
        self.agent_graph = self._create_agent()

    def _create_agent(self):
        """Create the LangChain agent with tools using the new API"""
        # Create model string for LangChain's init_chat_model
        # Format: provider:model (e.g., "anthropic:GLM-4.7")
        model = f"anthropic:{self.config.ANTHROPIC_DEFAULT_HAIKU_MODEL}"

        # Create the agent graph using the new create_agent API
        graph = create_agent(
            model=model,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT,
            debug=False,
        )

        return graph

    def query(self, user_input: str, chat_history: Optional[list] = None) -> str:
        """
        Query the agent with user input

        Args:
            user_input: The user's query or request
            chat_history: Optional conversation history (not yet implemented)

        Returns:
            The agent's response as a string

        Examples:
            >>> agent = ResumeTemplateAgent()
            >>> result = agent.query("人事行政简历模板")
            >>> print(result)
            **模板名称**: 人事行政简历模板
            **下载地址**: https://pan.baidu.com/s/...
        """
        try:
            # Prepare the input in the format expected by the new agent API
            inputs = {
                "messages": [
                    {"role": "user", "content": user_input}
                ]
            }

            # Invoke the agent graph
            result = self.agent_graph.invoke(inputs)

            # Extract the last message (the agent's response)
            messages = result.get("messages", [])
            if messages:
                # Get the last AI message
                for msg in reversed(messages):
                    if isinstance(msg, dict):
                        if msg.get("role") == "assistant":
                            return msg.get("content", "")
                    elif hasattr(msg, "content"):
                        return str(msg.content)

            return "未收到响应"

        except Exception as e:
            return f"处理请求时出错: {str(e)}"

    def stream_query(self, user_input: str, chat_history: Optional[list] = None):
        """
        Stream the agent's response

        Args:
            user_input: The user's query or request
            chat_history: Optional conversation history

        Yields:
            Chunks of the response as they are generated
        """
        try:
            inputs = {
                "messages": [
                    {"role": "user", "content": user_input}
                ]
            }

            for chunk in self.agent_graph.stream(inputs):
                yield chunk

        except Exception as e:
            yield {"error": str(e)}

    def __repr__(self) -> str:
        return (
            f"ResumeTemplateAgent(\n"
            f"  model={self.config.ANTHROPIC_DEFAULT_HAIKU_MODEL}\n"
            f"  base_url={self.config.ANTHROPIC_BASE_URL}\n"
            f"  tools={len(self.tools)}\n"
            f")"
        )


__all__ = ["ResumeTemplateAgent"]
