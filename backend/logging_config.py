"""
Centralized logging configuration for the TradingAgents backend.
Replaces scattered print() statements with proper logging.
"""

import logging
import os
import sys
from typing import Optional


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Configure logging for the TradingAgents backend.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
               Defaults to DEBUG if DEBUG_LOGGING=true, else INFO.
        format_string: Custom format string for log messages.

    Returns:
        The root logger for the backend module.
    """
    # Determine log level from environment or parameter
    if level is None:
        debug_enabled = os.getenv('DEBUG_LOGGING', 'false').lower() == 'true'
        level = 'DEBUG' if debug_enabled else 'INFO'

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Default format with timestamp, level, and module
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Configure the root backend logger
    logger = logging.getLogger('backend')
    logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(console_handler)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name, will be prefixed with 'backend.'

    Returns:
        Logger instance for the module.
    """
    if not name.startswith('backend.'):
        name = f'backend.{name}'
    return logging.getLogger(name)


# Initialize logging on module import
_root_logger = setup_logging()
