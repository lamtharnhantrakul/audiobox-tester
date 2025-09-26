"""Structured logging utilities for production-grade audio processing.

This module provides comprehensive logging infrastructure following Google SRE
best practices for observability, debugging, and monitoring in production systems.

Example:
    >>> from src.utils.logging_utils import setup_logger
    >>> logger = setup_logger("audio_processor", level="INFO")
    >>> logger.info("Processing started", file_count=42, batch_size=10)
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import structlog
from rich.console import Console
from rich.logging import RichHandler


class StructuredLogger:
    """Production-grade structured logger with contextual information.

    Provides structured logging with automatic context injection, performance
    metrics tracking, and integration with monitoring systems.

    Attributes:
        logger: The underlying structlog logger instance.
        context: Current logging context dictionary.
    """

    def __init__(self, name: str, level: str = "INFO") -> None:
        """Initialize structured logger.

        Args:
            name: Logger name, typically module or component name.
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        """
        self.logger = structlog.get_logger(name)
        self.context: Dict[str, Any] = {}
        self._setup_processors()

    def _setup_processors(self) -> None:
        """Configure structlog processors for production use."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def bind(self, **kwargs: Any) -> "StructuredLogger":
        """Bind context to logger for subsequent log calls.

        Args:
            **kwargs: Key-value pairs to bind to logging context.

        Returns:
            New logger instance with bound context.
        """
        new_logger = StructuredLogger.__new__(StructuredLogger)
        new_logger.logger = self.logger.bind(**kwargs)
        new_logger.context = {**self.context, **kwargs}
        return new_logger

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info level message with context."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning level message with context."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error level message with context."""
        self.logger.error(message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug level message with context."""
        self.logger.debug(message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical level message with context."""
        self.logger.critical(message, **kwargs)


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    console_output: bool = True,
    structured: bool = True
) -> Union[StructuredLogger, logging.Logger]:
    """Setup production-grade logger with configurable outputs.

    Creates a logger configured for production use with structured output,
    console formatting, and optional file output.

    Args:
        name: Logger name, typically module or component name.
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to log file for persistent storage.
        console_output: Whether to enable rich console output.
        structured: Whether to use structured logging format.

    Returns:
        Configured logger instance (StructuredLogger or stdlib Logger).

    Example:
        >>> logger = setup_logger("audio_processor", level="DEBUG", log_file="app.log")
        >>> logger.info("Processing started", file_count=10)
    """
    if structured:
        logger = StructuredLogger(name, level)
        return logger

    # Standard library logger setup
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler with rich formatting
    if console_output:
        console = Console(stderr=True)
        console_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            markup=True,
            show_path=False,
        )
        console_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(console_handler)

    # File handler for persistent logging
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(file_handler)

    return logger


def log_performance(func):
    """Decorator to log function performance metrics.

    Automatically logs function execution time and basic performance metrics
    for monitoring and optimization purposes.

    Args:
        func: Function to wrap with performance logging.

    Returns:
        Wrapped function with performance logging.
    """
    import time
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = setup_logger(func.__module__)
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            execution_time = end_time - start_time

            if hasattr(logger, 'info'):
                logger.info(
                    f"Function {func.__name__} completed",
                    execution_time_s=round(execution_time, 4),
                    function=func.__name__,
                    module=func.__module__
                )

            return result

        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time

            if hasattr(logger, 'error'):
                logger.error(
                    f"Function {func.__name__} failed",
                    execution_time_s=round(execution_time, 4),
                    error=str(e),
                    function=func.__name__,
                    module=func.__module__
                )

            raise

    return wrapper