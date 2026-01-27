"""
LangChain LLM provider wrapper.

Integrates with existing ChatBI configuration to create LangChain ChatModel instances.
"""

import os
from typing import Optional
from functools import lru_cache

from langchain_openai import ChatOpenAI
from loguru import logger

# Global LLM cache to reuse instances
_llm_cache: dict = {}


def create_langchain_llm(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4000,
    streaming: bool = True,
) -> ChatOpenAI:
    """
    Create a LangChain ChatOpenAI instance (cached).

    Uses environment variables if parameters are not provided.
    LLM instances are cached based on configuration to avoid redundant initialization.

    Environment Variables:
        LLM_API_KEY: API key for the LLM provider
        LLM_BASE_URL: Base URL for the LLM API (default: https://api.openai.com/v1)
        LLM_MODEL: Model name (default: gpt-3.5-turbo)
        LLM_TEMPERATURE: Sampling temperature (default: 0.7)
        LLM_MAX_TOKENS: Maximum tokens (default: 4000)

    Args:
        api_key: LLM API key (defaults to LLM_API_KEY env var)
        base_url: LLM base URL (defaults to LLM_BASE_URL env var)
        model: Model name (defaults to LLM_MODEL env var)
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in response
        streaming: Enable streaming support

    Returns:
        Configured ChatOpenAI instance
    """
    # Use environment variables as fallbacks
    api_key = api_key or os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = model or os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    temperature = float(os.getenv("LLM_TEMPERATURE", str(temperature)))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", str(max_tokens)))

    # Create cache key from configuration
    cache_key = f"{model}:{base_url}:{temperature}:{max_tokens}:{streaming}"

    # Return cached instance if available
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    # Create new instance
    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
    )

    logger.info(
        f"Created LangChain LLM: model={model}, base_url={base_url}, "
        f"temperature={temperature}, streaming={streaming}"
    )

    # Cache for reuse
    _llm_cache[cache_key] = llm

    return llm


def create_langchain_llm_from_config(config) -> ChatOpenAI:
    """
    Create a LangChain ChatOpenAI instance from existing ChatBI config.

    Args:
        config: ChatBI Config object with llm attribute

    Returns:
        Configured ChatOpenAI instance
    """
    return create_langchain_llm(
        api_key=config.llm.api_key or os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        model=config.llm.model,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
        streaming=True,
    )
