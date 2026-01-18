"""
Configuration module for Resume Template Agent
Manages API credentials and model settings for Zhipu AI (BigModel)
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Configuration class for Zhipu AI API"""

    # API Configuration
    ANTHROPIC_AUTH_TOKEN: str = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
    ANTHROPIC_BASE_URL: str = os.getenv(
        "ANTHROPIC_BASE_URL",
        "https://open.bigmodel.cn/api/anthropic"
    )
    API_TIMEOUT_MS: int = int(os.getenv("API_TIMEOUT_MS", "3000000"))
    ANTHROPIC_DEFAULT_HAIKU_MODEL: str = os.getenv(
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "GLM-4.7"
    )

    # File paths (computed at class level)
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    EXCEL_FILE_PATH: str = os.path.join(
        BASE_DIR,
        "9b1af114-6719-4148-8194-412b68c0d44d-tmp.xlsx"
    )
    PROMPT_FILE_PATH: str = os.path.join(BASE_DIR, "resume-template-agent.md")

    # Agent settings
    AGENT_TEMPERATURE: float = 0.0
    AGENT_MAX_TOKENS: int = 2000

    # Search mode configuration
    SEARCH_MODE: str = os.getenv("SEARCH_MODE", "fuzzy")  # fuzzy | vector | hybrid

    # Milvus configuration
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    MILVUS_COLLECTION_NAME: str = os.getenv("MILVUS_COLLECTION_NAME", "resume_templates")
    MILVUS_INDEX_TYPE: str = os.getenv("MILVUS_INDEX_TYPE", "IVF_FLAT")
    MILVUS_METRIC_TYPE: str = os.getenv("MILVUS_METRIC_TYPE", "COSINE")

    # Embedding configuration
    EMBEDDING_MODEL_NAME: str = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "BAAI/bge-small-zh-v1.5"
    )
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "512"))
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")  # cpu | cuda

    # Vector search configuration
    VECTOR_TOP_K: int = int(os.getenv("VECTOR_TOP_K", "5"))
    VECTOR_THRESHOLD: float = float(os.getenv("VECTOR_THRESHOLD", "0.5"))

    # Hybrid search configuration
    HYBRID_WEIGHT_VECTOR: float = float(os.getenv("HYBRID_WEIGHT_VECTOR", "0.7"))
    HYBRID_WEIGHT_FUZZY: float = float(os.getenv("HYBRID_WEIGHT_FUZZY", "0.3"))

    # Embedding cache configuration
    ENABLE_EMBEDDING_CACHE: bool = os.getenv("ENABLE_EMBEDDING_CACHE", "true").lower() == "true"
    EMBEDDING_CACHE_DIR: str = os.path.join(BASE_DIR, "cache", "embeddings")

    # Hugging Face mirror configuration
    HF_ENDPOINT: str = os.getenv(
        "HF_ENDPOINT",
        "https://hf-mirror.com"
    )

    # Set HF_ENDPOINT environment variable immediately after reading config
    # This ensures it's available before any FlagEmbedding imports
    _hf_endpoint_set: bool = False

    def __init__(self):
        """Initialize config and set environment variables for LangChain"""
        # Set HF_ENDPOINT immediately (before any other imports that might need it)
        if not Config._hf_endpoint_set:
            os.environ["HF_ENDPOINT"] = self.HF_ENDPOINT
            Config._hf_endpoint_set = True

        # Set environment variables that langchain-anthropic expects
        os.environ["ANTHROPIC_API_KEY"] = self.ANTHROPIC_AUTH_TOKEN
        os.environ["ANTHROPIC_BASE_URL"] = self.ANTHROPIC_BASE_URL

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        if not cls.ANTHROPIC_AUTH_TOKEN:
            raise ValueError("ANTHROPIC_AUTH_TOKEN is required")
        if not cls.ANTHROPIC_BASE_URL:
            raise ValueError("ANTHROPIC_BASE_URL is required")
        if not os.path.exists(cls.EXCEL_FILE_PATH):
            raise ValueError(f"Excel file not found: {cls.EXCEL_FILE_PATH}")
        return True

    @classmethod
    def get_model_kwargs(cls) -> dict:
        """Get model configuration kwargs for LangChain"""
        return {
            "api_key": cls.ANTHROPIC_AUTH_TOKEN,
            "base_url": cls.ANTHROPIC_BASE_URL,
            "timeout": cls.API_TIMEOUT_MS / 1000,  # Convert to seconds
            "model": cls.ANTHROPIC_DEFAULT_HAIKU_MODEL,
            "temperature": cls.AGENT_TEMPERATURE,
            "max_tokens": cls.AGENT_MAX_TOKENS,
        }

    def __repr__(self) -> str:
        return (
            f"Config(\n"
            f"  base_url={self.ANTHROPIC_BASE_URL}\n"
            f"  model={self.ANTHROPIC_DEFAULT_HAIKU_MODEL}\n"
            f"  timeout={self.API_TIMEOUT_MS}ms\n"
            f"  excel_path={self.EXCEL_FILE_PATH}\n"
            f")"
        )
