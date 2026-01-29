"""
Base agent class for LangChain-based agents.

Provides common initialization and utilities for all agents.
Patterned after the chatbi project's agent design.
"""

import asyncio
from typing import Optional, List, Any, Dict
from langchain_core.language_models import BaseChatModel
from langchain_core.callbacks import Callbacks
from langchain_core.messages import BaseMessage, AIMessage
from loguru import logger


class GraphAgentBase:
    """
    Base class for all LangChain-based agents in the graph knowledge system.

    Provides unified LLM invocation interface with timeout protection
    and callback support for observability.
    """

    def __init__(
        self,
        name: str,
        llm: BaseChatModel,
        callbacks: Callbacks = None,
        graph_service=None
    ):
        """
        Initialize the base agent.

        Args:
            name: Agent identifier name
            llm: LangChain ChatModel instance
            callbacks: Optional callback handlers for observability
            graph_service: Optional graph query service instance
        """
        self.name = name
        self.llm = llm
        self.callbacks = callbacks or []
        self.graph_service = graph_service

        logger.debug(f"Initialized agent: {self.name}")

    def _get_invoke_config(self, **kwargs) -> Dict[str, Any]:
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

        Raises:
            TimeoutError: If LLM call times out after 30 seconds
        """
        config = self._get_invoke_config(**kwargs)
        try:
            # Use 30 second timeout for faster feedback
            response = await asyncio.wait_for(
                self.llm.ainvoke(messages, config=config),
                timeout=30.0
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
        try:
            async for chunk in self.llm.astream(messages, config=config):
                yield chunk
        except Exception as e:
            logger.error(f"[{self.name}]: Async stream failed: {e}")
            raise

    def add_callback(self, callback) -> None:
        """
        Add a callback handler to the agent.

        Args:
            callback: Callback handler to add
        """
        self.callbacks.append(callback)
        logger.debug(f"Added callback to agent {self.name}: {callback.__class__.__name__}")

    def remove_callback(self, callback) -> None:
        """
        Remove a callback handler from the agent.

        Args:
            callback: Callback handler to remove
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            logger.debug(f"Removed callback from agent {self.name}: {callback.__class__.__name__}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
