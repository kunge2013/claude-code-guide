"""
Logger configuration using Loguru.

Provides centralized logging configuration for the application.
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Optional


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs",
    rotation: str = "500 MB",
    retention: str = "10 days",
    compression: str = "zip"
):
    """
    Configure Loguru logger for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file name (default: app.log)
        log_dir: Directory for log files (default: logs)
        rotation: Log rotation setting (default: 500 MB)
        retention: Log retention setting (default: 10 days)
        compression: Log compression format (default: zip)
    """
    # Remove default handler
    logger.remove()

    # Add console handler with colored output
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    # Add file handler if log_file is specified
    if log_file:
        log_path = Path(log_dir) / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_path,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            backtrace=True,
            diagnose=True,
            encoding="utf-8"
        )

    logger.info(f"Logger configured with level: {log_level}")
    if log_file:
        logger.info(f"Log file: {log_path}")


def get_logger(name: Optional[str] = None):
    """
    Get a logger instance with optional name.

    Args:
        name: Optional name for the logger (typically __name__)

    Returns:
        Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger


class LoggerContext:
    """
    Context manager for adding context to log messages.
    """

    def __init__(self, **context):
        """
        Initialize the logger context.

        Args:
            **context: Key-value pairs to add to log context
        """
        self.context = context
        self.logger = None

    def __enter__(self):
        """Enter the context and bind logger with context."""
        self.logger = logger.bind(**self.context)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context."""
        if exc_type is not None:
            self.logger.error(
                f"Exception in context: {exc_type.__name__}: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb)
            )


# Example usage and testing
if __name__ == "__main__":
    # Setup logger
    setup_logger(log_level="DEBUG", log_file="test.log")

    # Basic logging
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    # With context
    with LoggerContext(module="test", function="main"):
        logger.info("This message has context")

    # Get named logger
    module_logger = get_logger("my_module")
    module_logger.info("This is from a named logger")
