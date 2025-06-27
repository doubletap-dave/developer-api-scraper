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
    """Service for configuring structured logging with multiple output streams.

    Provides both human-readable console output for development and
    machine-readable JSON file outputs for analysis and monitoring.

    Creates three separate log files:
    - wyrm.jsonl: Normal operational logs (INFO and above)
    - wyrm-trace.jsonl: Complete trace logs (DEBUG and above) for debugging
    - wyrm-error.jsonl: Error logs only (ERROR and above) for monitoring

    All JSON log files use JSONL (JSON Lines) format where each line is a
    separate JSON object. This format is supported by most log ingestion
    systems including ELK stack, Fluentd, and others.

    To parse JSONL format:
    - Each line is a valid JSON object
    - Parse line by line: `[json.loads(line) for line in open('log.jsonl')]`
    - Many log analysis tools natively support JSONL/NDJSON format
    """

    def __init__(self) -> None:
        """Initialize the logging service."""
        self._configured = False

    def setup_logging(
        self,
        log_level: str = "INFO",
        log_dir: Optional[str] = None
    ) -> None:
        """Configure structured logging with console and multiple file handlers.

        Creates three separate log files:
        - wyrm.jsonl: Normal operational logs (INFO and above)
        - wyrm-trace.jsonl: Complete trace logs (DEBUG and above)
        - wyrm-error.jsonl: Error logs only (ERROR and above)

        Args:
            log_level: The minimum log level for console output (INFO, DEBUG, etc.)
            log_dir: Directory for log files. Defaults to 'logs'

        Raises:
            ValueError: If log_level is not a valid logging level
        """
        if self._configured:
            return

        # Validate log level
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")

        # Set default log directory
        if log_dir is None:
            log_dir = "logs"

        # Ensure log directory exists
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)

        # Define log file paths
        normal_log_path = log_dir_path / "wyrm.jsonl"
        trace_log_path = log_dir_path / "wyrm-trace.jsonl"
        error_log_path = log_dir_path / "wyrm-error.jsonl"

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

        # Create normal log handler (INFO and above)
        normal_handler = logging.handlers.RotatingFileHandler(
            normal_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        normal_handler.setLevel(logging.INFO)

        # Create trace log handler (DEBUG and above - everything)
        trace_handler = logging.handlers.RotatingFileHandler(
            trace_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        trace_handler.setLevel(logging.DEBUG)

        # Create error log handler (ERROR and above only)
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)

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
        normal_handler.setFormatter(json_formatter)
        trace_handler.setFormatter(json_formatter)
        error_handler.setFormatter(json_formatter)

        # Get root logger and add handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()  # Clear any existing handlers
        root_logger.addHandler(console_handler)
        root_logger.addHandler(normal_handler)
        root_logger.addHandler(trace_handler)
        root_logger.addHandler(error_handler)

        self._configured = True

        # Log successful configuration
        logger = structlog.get_logger(__name__)
        logger.info(
            "Logging configured successfully",
            console_level=log_level,
            normal_log=str(normal_log_path),
            trace_log=str(trace_log_path),
            error_log=str(error_log_path),
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
