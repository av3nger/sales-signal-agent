"""Logging configuration for the Sales Signal Agent."""

import logging
import os
import sys
from datetime import datetime, timezone


class UTCFormatter(logging.Formatter):
    """Custom formatter that uses UTC timestamps."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Format time as UTC ISO format."""
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")


def setup_logging() -> None:
    """Configure application-wide logging.

    Format: [timestamp] [level] [module] message
    Log level configurable via LOG_LEVEL environment variable (default: INFO).
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    # Validate log level
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    # Create formatter
    formatter = UTCFormatter(
        fmt="[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: Logger name, typically the module name (e.g., 'main', 'news', 'extractor')

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
