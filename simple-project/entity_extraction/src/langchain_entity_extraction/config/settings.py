"""Configuration loader for entity extraction."""

import os
import re
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


class Settings:
    """Configuration settings for entity extraction."""

    def __init__(self, config_path: str = None):
        """
        Initialize settings.

        Args:
            config_path: Path to the YAML configuration file.
        """
        # Load environment variables from .env file
        load_dotenv()

        # Default config path
        if config_path is None:
            # Get the project root directory (entity_extraction/)
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent.parent
            config_path = project_root / "config" / "extraction_config.yaml"

        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}"
            )

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

        # Substitute environment variables
        self._config = self._substitute_env_vars(self._config)

    def _substitute_env_vars(self, config: Any) -> Any:
        """
        Recursively substitute environment variables in configuration.

        Supports ${VAR_NAME} and ${VAR_NAME:-default} syntax.

        Args:
            config: Configuration value (dict, list, or scalar)

        Returns:
            Configuration with environment variables substituted.
        """
        if isinstance(config, dict):
            return {
                k: self._substitute_env_vars(v)
                for k, v in config.items()
            }
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Match ${VAR_NAME} or ${VAR_NAME:-default}
            pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
            match = re.search(pattern, config)

            if match:
                var_name = match.group(1)
                default_value = match.group(2) if match.group(2) is not None else ""

                # Check environment variable first, then use default
                value = os.getenv(var_name, default_value)

                # If the entire string is just the variable reference, return the value
                if match.group(0) == config:
                    # Try to convert to appropriate type
                    return self._convert_value(value)
                else:
                    # Replace the variable reference in the string
                    return re.sub(pattern, value, config)

            return config
        else:
            return config

    def _convert_value(self, value: str) -> Any:
        """
        Convert string value to appropriate type.

        Args:
            value: String value to convert

        Returns:
            Converted value (int, float, bool, or str)
        """
        # Try boolean
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports nested keys with dot notation).

        Args:
            key: Configuration key (e.g., 'extraction.llm.model')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    # Convenience properties for common configuration values

    @property
    def extraction_strategy(self) -> str:
        """Get extraction strategy."""
        return self.get("extraction.strategy", "pydantic")

    @property
    def llm_provider(self) -> str:
        """Get LLM provider."""
        return self.get("extraction.llm.provider", "openai")

    @property
    def llm_model(self) -> str:
        """Get LLM model name."""
        return self.get("extraction.llm.model", "gpt-4")

    @property
    def llm_temperature(self) -> float:
        """Get LLM temperature."""
        return self.get("extraction.llm.temperature", 0.0)

    @property
    def llm_max_retries(self) -> int:
        """Get LLM max retries."""
        return self.get("extraction.llm.max_retries", 3)

    @property
    def llm_request_timeout(self) -> int:
        """Get LLM request timeout."""
        return self.get("extraction.llm.request_timeout", 60)

    @property
    def enable_strict_validation(self) -> bool:
        """Get strict validation setting."""
        return self.get("extraction.validation.enable_strict_validation", True)

    @property
    def log_level(self) -> str:
        """Get log level."""
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def log_file(self) -> str:
        """Get log file path."""
        return os.getenv("LOG_FILE", "logs/extraction.log")

    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key."""
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def openai_api_base(self) -> str:
        """Get OpenAI API base URL."""
        return os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

    @property
    def zhipuai_api_key(self) -> str:
        """Get ZhipuAI API key."""
        return os.getenv("ZHIPUAI_API_KEY", "")

    @property
    def zhipuai_api_base(self) -> str:
        """Get ZhipuAI API base URL."""
        return os.getenv("ZHIPUAI_API_BASE", "https://open.bigmodel.cn/api/paas/v4")

    @property
    def zhipuai_model(self) -> str:
        """Get ZhipuAI model name."""
        return os.getenv("ZHIPUAI_MODEL", "glm-4")


# Global settings instance
_settings: Settings = None


def get_settings(config_path: str = None) -> Settings:
    """
    Get global settings instance.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings(config_path)
    return _settings
