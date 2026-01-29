"""
Configuration loading module.

Loads and merges configuration from YAML files.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def load_config(
    graph_config_path: Optional[str] = None,
    data_sources_config_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Load configuration from YAML files.

    Args:
        graph_config_path: Path to graph config file
        data_sources_config_path: Path to data sources config file

    Returns:
        Merged configuration dictionary
    """
    config = {}

    # Default paths
    if not graph_config_path:
        graph_config_path = "config/graph_config.yaml"
    if not data_sources_config_path:
        data_sources_config_path = "config/data_sources.yaml"

    # Load graph configuration
    graph_config_path = Path(graph_config_path)
    if graph_config_path.exists():
        with open(graph_config_path, 'r', encoding='utf-8') as f:
            config['graph'] = yaml.safe_load(f)
            # Replace environment variables
            config['graph'] = _replace_env_vars(config['graph'])

    # Load data sources configuration
    data_sources_config_path = Path(data_sources_config_path)
    if data_sources_config_path.exists():
        with open(data_sources_config_path, 'r', encoding='utf-8') as f:
            config['data_sources'] = yaml.safe_load(f)
            # Replace environment variables
            config['data_sources'] = _replace_env_vars(config['data_sources'])

    return config


def _replace_env_vars(config: Any) -> Any:
    """
    Recursively replace environment variables in configuration.

    Args:
        config: Configuration value (dict, list, or string)

    Returns:
        Configuration with environment variables replaced
    """
    if isinstance(config, dict):
        return {k: _replace_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_replace_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Replace ${VAR_NAME} with environment variable value
        if config.startswith('${') and config.endswith('}'):
            var_name = config[2:-1]
            return os.getenv(var_name, config)
        return config
    else:
        return config


def get_nested_value(config: Dict[str, Any], *keys, default=None) -> Any:
    """
    Get a nested value from configuration dictionary.

    Args:
        config: Configuration dictionary
        *keys: Keys to traverse
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    value = config
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return default
        else:
            return default
    return value if value is not None else default
