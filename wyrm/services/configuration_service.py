"""Configuration service for Wyrm application.

This service handles configuration loading, validation, environment setup,
logging configuration, and utility functions.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

import structlog
import yaml
from rich.logging import RichHandler

from wyrm.models.config import AppConfig


class ConfigurationService:
    """Service for handling configuration and logging setup.

    This service provides comprehensive configuration management including:
    - YAML configuration file loading and validation
    - Pydantic model-based configuration validation
    - Rich logging setup with console and file handlers
    - CLI argument override handling
    - Directory setup and environment management

    Attributes:
        _config: Internal storage for loaded configuration.
    """

    def __init__(self) -> None:
        """Initialize the Configuration service.

        Sets up internal state for configuration storage. The service
        starts with empty configuration that gets populated via load_config().

        Args:
            None

        Returns:
            None
        """
        self.logger = structlog.get_logger(__name__)
        self._config = {}

    def setup_logging(
            self,
            log_level: str = "INFO",
            log_file: Optional[Path] = None) -> None:
        """Configure logging using RichHandler for console and FileHandler for file.

        Sets up comprehensive logging with both console output (using Rich for
        enhanced formatting) and file output. Configures appropriate log levels
        for third-party libraries to reduce noise.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            log_file: Path to log file. If None, defaults to "wyrm.log".

        Returns:
            None

        Raises:
            ValueError: If log_level is not a valid logging level.
            OSError: If log file cannot be created or written to.
        """
        if log_file is None:
            log_file = Path("wyrm.log")

        log_level = log_level.upper()
        numeric_level = getattr(logging, log_level, None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")

        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(log_format, datefmt="[%X]")

        # Get the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)

        # Clear existing handlers (important if this function might be called
        # multiple times)
        if root_logger.hasHandlers():
            root_logger.handlers.clear()

        # Configure RichHandler for console
        console_handler = RichHandler(rich_tracebacks=True, markup=False)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Configure FileHandler for file
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Set lower level for noisy libraries
        logging.getLogger("selenium").setLevel(logging.WARNING)
        logging.getLogger("webdriver_manager").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        # Add other libraries here if they become noisy

        logging.info(
            f"Logging setup complete. Level: {log_level}, "
            f"Console: True, File: {log_file}"
        )

    def load_config(self, config_path: Optional[Path] = None) -> AppConfig:
        """Load configuration from a YAML file and parse into AppConfig model.

        Loads and validates configuration from a YAML file using Pydantic models
        for type safety and validation. The configuration is parsed into an
        AppConfig model that provides structured access to all settings.

        Args:
            config_path: Path to YAML configuration file. If None, defaults to
                "config.yaml".

        Returns:
            AppConfig: Validated configuration model with all settings.

        Raises:
            FileNotFoundError: If configuration file doesn't exist.
            yaml.YAMLError: If configuration file contains invalid YAML.
            ValidationError: If configuration doesn't match the AppConfig schema.
            OSError: If file cannot be read due to permissions or other IO errors.
        """
        if config_path is None:
            config_path = Path("config.yaml")

        path = Path(config_path)
        self.logger.info("Loading configuration", path=str(path.absolute()))

        if not path.is_file():
            self.logger.error(
                "Configuration file not found", path=str(path)
            )
            raise FileNotFoundError(f"Configuration file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)

            # Parse raw config into AppConfig model (this validates the data)
            config = AppConfig(**raw_config)
            self.logger.debug(
                "Configuration loaded and validated", config=str(config)
            )
            self._config = config  # Store for get_config method
            return config
        except yaml.YAMLError as e:
            self.logger.exception(
                "Error parsing configuration file",
                path=str(path),
                error=str(e)
            )
            raise
        except Exception as e:
            self.logger.exception(
                "Error reading configuration file",
                path=str(path),
                error=str(e)
            )
            raise

    def extract_configuration_values(self, config: AppConfig) -> Dict:
        """Extract configuration values from AppConfig model.

        Converts the structured AppConfig model into a flat dictionary format
        for backward compatibility with existing code. Handles nested configuration
        sections and provides sensible defaults for optional values.

        Args:
            config: Validated AppConfig model containing all configuration settings.

        Returns:
            Dict: Flattened configuration dictionary with processed values.

        Raises:
            AttributeError: If required configuration attributes are missing.
            Exception: If configuration extraction fails for any reason.
        """
        self.logger.info(
            "Extracting configuration values from AppConfig model"
        )

        try:
            # Extract values from the validated AppConfig model
            config_values = {
                "base_output_dir": config.output_directory,
                "debug_output_dir": config.debug_settings.output_directory,
                "sidebar_wait_timeout": config.delays.sidebar_wait,
                "navigation_timeout": config.delays.navigation,
                "content_wait_timeout": getattr(
                    config.delays,
                    'content_wait_noheadless',
                    15.0),
                "expand_delay": config.delays.expand_menu,
                "post_click_delay": getattr(
                    config.delays,
                    'post_click_noheadless',
                    1.0),
                "default_html_filename": (
                    config.debug_settings.save_html_filename
                ),
                "default_structure_filename": (
                    config.debug_settings.save_structure_filename
                ),
            }

            self.logger.info(
                "Configuration values extracted successfully from AppConfig model"
            )
            return config_values

        except Exception as e:
            self.logger.error(
                "Failed to extract configuration values", error=str(e)
            )
            raise

    def merge_cli_overrides(self, config: AppConfig, cli_args: Dict) -> AppConfig:
        """Merge CLI argument overrides into AppConfig model.

        Takes CLI arguments and merges them into the base configuration,
        creating a new AppConfig instance with the overridden values.
        This allows command-line arguments to take precedence over file configuration.

        Args:
            config: Base AppConfig model loaded from configuration file.
            cli_args: Dictionary of CLI arguments to override. Supported keys:
                - headless: Override browser headless mode
                - log_level: Override logging level
                - max_expand_attempts: Override maximum menu expansion attempts

        Returns:
            AppConfig: New AppConfig instance with CLI overrides applied.

        Raises:
            ValidationError: If CLI overrides result in invalid configuration.
        """
        # Create a copy of the config as a dictionary for modification
        config_dict = config.dict()

        # Handle headless override
        if cli_args.get("headless") is not None:
            config_dict["webdriver"]["headless"] = cli_args["headless"]
            self.logger.info(
                "CLI override", setting="headless", value=cli_args["headless"]
            )

        # Handle log level override
        if cli_args.get("log_level"):
            config_dict["log_level"] = cli_args["log_level"]
            self.logger.info(
                "CLI override",
                setting="log_level",
                value=cli_args["log_level"]
            )

        # Handle max expand attempts override
        if cli_args.get("max_expand_attempts") is not None:
            config_dict["behavior"]["max_expand_attempts"] = (
                cli_args["max_expand_attempts"]
            )
            self.logger.info(
                "CLI override",
                setting="max_expand_attempts",
                value=cli_args["max_expand_attempts"]
            )

        # Create new AppConfig with merged values
        return AppConfig(**config_dict)

    def setup_directories(self, config_values: Dict) -> None:
        """Set up required directories for the application.

        Creates all necessary directories for output files, debug files, and logs.
        Ensures that the directory structure exists before processing begins.

        Args:
            config_values: Configuration dictionary containing directory paths.
                Expected keys: base_output_dir, debug_output_dir.

        Returns:
            None

        Raises:
            OSError: If directories cannot be created due to permissions or disk space.
            KeyError: If required directory paths are missing from config_values.
        """
        directories = [
            config_values["base_output_dir"],
            config_values["debug_output_dir"],
            Path("logs")  # For log files
        ]

        for directory in directories:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
                self.logger.debug("Directory ensured", directory=str(directory))
            except Exception as e:
                self.logger.error(
                    "Failed to create directory",
                    directory=str(directory),
                    error=str(e)
                )
                raise

        self.logger.info("All required directories have been set up")

    def get_environment_info(self) -> Dict:
        """Get information about the current environment.

        Collects and returns information about the runtime environment
        including Python version, platform, and other relevant details
        for debugging and logging purposes.

        Args:
            None

        Returns:
            Dict: Environment information including system details.
        """
        import platform
        import sys

        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "architecture": platform.architecture(),
            "processor": platform.processor(),
        }

    def get_config(self) -> AppConfig:
        """Get the currently loaded configuration.

        Returns the configuration that was loaded via load_config().
        Useful for services that need access to the full configuration object.

        Args:
            None

        Returns:
            AppConfig: Currently loaded configuration model.

        Raises:
            RuntimeError: If no configuration has been loaded yet.
        """
        if not self._config:
            raise RuntimeError("No configuration loaded. Call load_config() first.")
        return self._config
