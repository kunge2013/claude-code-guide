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

    def __init__(self):
        """Initialize config and set environment variables for LangChain"""
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
