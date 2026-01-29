"""
LangChain LLM factory.

Creates and configures LangChain chat models for use in agents.
"""

import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from loguru import logger


def create_langchain_llm(
    provider: str = "openai",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    temperature: float = 0.0,
    **kwargs
) -> BaseChatModel:
    """
    Create a LangChain chat model instance.

    Args:
        provider: LLM provider ('openai', 'zhipuai', etc.)
        model: Model name (if None, uses default for provider)
        api_key: API key (if None, reads from environment)
        api_base: API base URL (if None, uses default)
        temperature: Sampling temperature
        **kwargs: Additional arguments for the model

    Returns:
        BaseChatModel instance
    """
    provider = provider.lower()

    if provider == "openai":
        return _create_openai_llm(model, api_key, api_base, temperature, **kwargs)
    elif provider == "zhipuai":
        return _create_zhipuai_llm(model, api_key, api_base, temperature, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _create_openai_llm(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    temperature: float = 0.0,
    **kwargs
) -> ChatOpenAI:
    """
    Create OpenAI chat model.

    Args:
        model: Model name (default: gpt-4)
        api_key: OpenAI API key
        api_base: API base URL
        temperature: Sampling temperature
        **kwargs: Additional arguments

    Returns:
        ChatOpenAI instance
    """
    model = model or os.getenv("OPENAI_MODEL", "gpt-4")
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    api_base = api_base or os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

    if not api_key:
        raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=api_base,
        temperature=temperature,
        **kwargs
    )

    logger.info(f"Created OpenAI LLM: model={model}, base_url={api_base}")
    return llm


def _create_zhipuai_llm(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    temperature: float = 0.0,
    **kwargs
) -> ChatOpenAI:
    """
    Create ZhipuAI (智谱AI) chat model.

    Args:
        model: Model name (default: glm-4)
        api_key: ZhipuAI API key
        api_base: API base URL
        temperature: Sampling temperature
        **kwargs: Additional arguments

    Returns:
        ChatOpenAI instance configured for ZhipuAI
    """
    model = model or os.getenv("ZHIPUAI_MODEL", "glm-4")
    api_key = api_key or os.getenv("ZHIPUAI_API_KEY")
    api_base = api_base or os.getenv("ZHIPUAI_API_BASE", "https://open.bigmodel.cn/api/paas/v4")

    if not api_key:
        raise ValueError("ZhipuAI API key not provided. Set ZHIPUAI_API_KEY environment variable.")

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=api_base,
        temperature=temperature,
        **kwargs
    )

    logger.info(f"Created ZhipuAI LLM: model={model}, base_url={api_base}")
    return llm


def get_default_llm() -> BaseChatModel:
    """
    Get the default LLM based on environment configuration.

    Checks environment variables to determine which LLM to use.
    Priority:
    1. If ZHIPUAI_API_KEY is set, use ZhipuAI
    2. If OPENAI_API_KEY is set, use OpenAI
    3. Otherwise, raise error

    Returns:
        BaseChatModel instance

    Raises:
        ValueError: If no API key is configured
    """
    if os.getenv("ZHIPUAI_API_KEY"):
        return create_langchain_llm(provider="zhipuai")
    elif os.getenv("OPENAI_API_KEY"):
        return create_langchain_llm(provider="openai")
    else:
        raise ValueError(
            "No LLM API key configured. "
            "Set either OPENAI_API_KEY or ZHIPUAI_API_KEY environment variable."
        )
