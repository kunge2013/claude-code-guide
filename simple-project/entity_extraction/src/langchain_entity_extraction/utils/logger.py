"""Logger configuration for entity extraction."""

import sys
from pathlib import Path
from loguru import logger

from langchain_entity_extraction.config.settings import get_settings


def setup_logger(log_level: str = None, log_file: str = None) -> None:
    """
    Configure the logger for the application.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
    """
    settings = get_settings()

    if log_level is None:
        log_level = settings.log_level

    if log_file is None:
        log_file = settings.log_file

    # Remove default handler
    logger.remove()

    # Add console handler with color
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # Add file handler if log file is specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | "
                   "{level: <8} | "
                   "{name}:{function}:{line} | "
                   "{message}",
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
        )

    logger.info(f"Logger configured with level: {log_level}")


# Get logger instance
def get_logger(name: str = None):
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__ of the module)

    Returns:
        Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger
