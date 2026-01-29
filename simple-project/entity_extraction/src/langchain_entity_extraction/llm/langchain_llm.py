"""LangChain LLM factory for entity extraction."""

from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_community.chat_models.tongyi import ChatTongyi

from langchain_entity_extraction.config.settings import get_settings
from langchain_entity_extraction.utils.logger import get_logger

logger = get_logger(__name__)


def create_langchain_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs
) -> ChatOpenAI:
    """
    Create a LangChain LLM instance based on configuration.

    Args:
        provider: LLM provider (openai, zhipuai, etc.)
        model: Model name
        temperature: Temperature for generation
        **kwargs: Additional parameters to pass to the LLM

    Returns:
        LangChain ChatModel instance

    Raises:
        ValueError: If provider is not supported
    """
    settings = get_settings()

    if provider is None:
        provider = settings.llm_provider

    if model is None:
        model = settings.llm_model

    if temperature is None:
        temperature = settings.llm_temperature

    # Set default parameters
    default_params = {
        "temperature": temperature,
        "max_retries": settings.llm_max_retries,
        "request_timeout": settings.llm_request_timeout,
    }
    default_params.update(kwargs)

    logger.info(f"Creating LLM: provider={provider}, model={model}")

    if provider.lower() == "openai":
        return _create_openai_llm(model, **default_params)
    elif provider.lower() in ("zhipuai", "tongyi"):
        return _create_zhipuai_llm(model, **default_params)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: openai, zhipuai"
        )


def _create_openai_llm(model: str, **kwargs) -> ChatOpenAI:
    """
    Create OpenAI LLM instance.

    Args:
        model: Model name
        **kwargs: Additional parameters

    Returns:
        ChatOpenAI instance
    """
    settings = get_settings()

    api_key = kwargs.pop("api_key", None) or settings.openai_api_key
    api_base = kwargs.pop("api_base", None) or settings.openai_api_base

    if not api_key:
        raise ValueError(
            "OpenAI API key not configured. "
            "Please set OPENAI_API_KEY environment variable."
        )

    logger.debug(f"Creating OpenAI LLM with model: {model}")

    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=api_base,
        **kwargs
    )


def _create_zhipuai_llm(model: str, **kwargs) -> ChatTongyi:
    """
    Create ZhipuAI (Tongyi) LLM instance.

    Args:
        model: Model name
        **kwargs: Additional parameters

    Returns:
        ChatTongyi instance
    """
    settings = get_settings()

    api_key = kwargs.pop("api_key", None) or settings.zhipuai_api_key
    api_base = kwargs.pop("api_base", None) or settings.zhipuai_api_base

    if not api_key:
        raise ValueError(
            "ZhipuAI API key not configured. "
            "Please set ZHIPUAI_API_KEY environment variable."
        )

    logger.debug(f"Creating ZhipuAI LLM with model: {model}")

    return ChatTongyi(
        model=model,
        dashscope_api_key=api_key,
        **kwargs
    )
