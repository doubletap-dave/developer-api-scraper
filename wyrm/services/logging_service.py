"""
Logging service for structured logging configuration.

This module provides the LoggingService class that configures structured logging
using structlog with both console and file output handlers.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

import structlog


class LoggingService:
    """Service for configuring structured logging with dual output streams.

    Provides both human-readable console output for development and
    machine-readable JSON file output for analysis and monitoring.
    """

    def __init__(self) -> None:
        """Initialize the logging service."""
        self._configured = False

    def setup_logging(
        self,
        log_level: str = "INFO",
        log_file_path: Optional[str] = None
    ) -> None:
        """Configure structured logging with console and file handlers.

        Args:
            log_level: The minimum log level for console output (INFO, DEBUG, etc.)
            log_file_path: Path to the JSON log file. Defaults to 'logs/wyrm.json'

        Raises:
            ValueError: If log_level is not a valid logging level
        """
        if self._configured:
            return

        # Validate log level
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")

        # Set default log file path
        if log_file_path is None:
            log_file_path = "logs/wyrm.json"

        # Ensure log directory exists
        log_dir = Path(log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Configure standard library logging
        logging.basicConfig(
            format="%(message)s",
            stream=None,  # We'll handle this through structlog
            level=logging.DEBUG,  # Set to DEBUG to capture everything
        )

        # Configure structlog processors
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
        ]

        # Create console handler with human-readable format
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)

        # Create file handler with JSON format
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)

        # Configure structlog
        structlog.configure(
            processors=processors + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Configure formatters
        console_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=processors,
        )

        json_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=processors,
        )

        # Apply formatters to handlers
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(json_formatter)

        # Get root logger and add handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()  # Clear any existing handlers
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        self._configured = True

        # Log successful configuration
        logger = structlog.get_logger(__name__)
        logger.info(
            "Logging configured successfully",
            console_level=log_level,
            file_level="DEBUG",
            log_file=log_file_path,
        )

    def get_logger(self, name: str) -> structlog.stdlib.BoundLogger:
        """Get a structured logger instance.

        Args:
            name: Name for the logger, typically __name__

        Returns:
            Configured structured logger instance

        Raises:
            RuntimeError: If logging has not been configured yet
        """
        if not self._configured:
            raise RuntimeError("Logging must be configured before getting loggers")

        return structlog.get_logger(name)
