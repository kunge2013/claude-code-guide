"""
Base agent class for LangChain-based agents.

Provides common initialization and utilities for all agents in the LangChain refactoring.
"""

import asyncio
from typing import Optional, List, Any
from langchain_core.language_models import BaseChatModel
from langchain_core.callbacks import Callbacks, BaseCallbackHandler
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from loguru import logger


class LangChainAgentBase:
    """
    Base class for all LangChain-based agents.

    Attributes:
        name: Agent identifier name
        llm: LangChain ChatModel instance
        callbacks: List of callback handlers for observability
    """

    def __init__(
        self,
        name: str,
        llm: BaseChatModel,
        callbacks: Callbacks = None,
    ):
        """
        Initialize the base agent.

        Args:
            name: Agent identifier
            llm: LangChain ChatModel instance
            callbacks: Optional callback handlers for observability (Langfuse, etc.)
        """
        self.name = name
        self.llm = llm
        self.callbacks = callbacks or []

        logger.debug(f"Initialized agent: {self.name}")

    def _get_invoke_config(self, **kwargs) -> dict[str, Any]:
        """
        Get configuration for LLM invocation.

        Args:
            **kwargs: Additional configuration options

        Returns:
            Configuration dictionary for ainvoke/astream calls
        """
        config = {"callbacks": self.callbacks}
        config.update(kwargs)
        return config

    def _invoke(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AIMessage:
        """
        Invoke LLM synchronously with messages.

        Args:
            messages: List of LangChain messages
            **kwargs: Additional parameters for invocation

        Returns:
            AI message response
        """
        config = self._get_invoke_config(**kwargs)
        response = self.llm.invoke(messages, config=config)
        return response

    async def _ainvoke(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> AIMessage:
        """
        Invoke LLM asynchronously with messages.

        Args:
            messages: List of LangChain messages
            **kwargs: Additional parameters for invocation

        Returns:
            AI message response
        """
        config = self._get_invoke_config(**kwargs)
        try:
            # Try async invoke with shorter timeout
            response = await asyncio.wait_for(
                self.llm.ainvoke(messages, config=config),
                timeout=30.0  # 30 second timeout for faster feedback
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"[{self.name}]: Async invoke timed out after 30s")
            raise TimeoutError(f"LLM call timed out for {self.name}. Please try again or check your API connection.")
        except Exception as e:
            logger.error(f"[{self.name}]: Async invoke failed: {e}")
            raise

    async def _astream(
        self,
        messages: List[BaseMessage],
        **kwargs
    ):
        """
        Stream LLM responses asynchronously.

        Args:
            messages: List of LangChain messages
            **kwargs: Additional parameters for streaming

        Yields:
            Message chunks as they are generated
        """
        config = self._get_invoke_config(**kwargs)
        async for chunk in self.llm.astream(messages, config=config):
            yield chunk

    def add_callback(self, callback: BaseCallbackHandler):
        """
        Add a callback handler to the agent.

        Args:
            callback: Callback handler to add
        """
        self.callbacks.append(callback)
        logger.debug(f"Added callback to agent {self.name}: {callback.__class__.__name__}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
