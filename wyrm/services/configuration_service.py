"""Configuration service for Wyrm application.

This service handles configuration loading, validation, environment setup,
logging configuration, and utility functions.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

import yaml
from rich.logging import RichHandler

from wyrm.models.config import AppConfig


class ConfigurationService:
    """Service for handling configuration and logging setup."""

    def __init__(self) -> None:
        """Initialize the Configuration service."""
        self._config = {}

    def setup_logging(
            self,
            log_level: str = "INFO",
            log_file: Optional[Path] = None) -> None:
        """Configure logging using RichHandler for console and FileHandler for file.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_file: Path to log file (defaults to wyrm.log)
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
            f"Logging setup complete. Level: {log_level}, Console: True, File: {log_file}")

    def load_config(self, config_path: Optional[Path] = None) -> AppConfig:
        """Load configuration from a YAML file and parse into AppConfig model.

        Args:
            config_path: Path to configuration file (defaults to config.yaml)

        Returns:
            Validated AppConfig model

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If configuration file is invalid YAML
            ValidationError: If configuration doesn't match schema
        """
        if config_path is None:
            config_path = Path("config.yaml")

        path = Path(config_path)
        logging.info(f"Loading configuration from: {path.absolute()}")

        if not path.is_file():
            logging.error(f"Configuration file not found: {path}")
            raise FileNotFoundError(f"Configuration file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)

            # Parse raw config into AppConfig model (this validates the data)
            config = AppConfig(**raw_config)
            logging.debug(f"Configuration loaded and validated: {config}")
            self._config = config  # Store for get_config method
            return config
        except yaml.YAMLError as e:
            logging.exception(f"Error parsing configuration file {path}: {e}")
            raise
        except Exception as e:
            logging.exception(f"Error reading configuration file {path}: {e}")
            raise

    def extract_configuration_values(self, config: AppConfig) -> Dict:
        """Extract configuration values from AppConfig model.

        Args:
            config: Validated AppConfig model

        Returns:
            Processed configuration values dictionary for backward compatibility
        """
        logging.info("Extracting configuration values from AppConfig model...")

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
                "default_html_filename": config.debug_settings.save_html_filename,
                "default_structure_filename": config.debug_settings.save_structure_filename,
            }

            logging.info(
                "Configuration values extracted successfully from AppConfig model.")
            return config_values

        except Exception as e:
            logging.error(f"Failed to extract configuration values: {e}")
            raise

    def merge_cli_overrides(self, config: AppConfig, cli_args: Dict) -> AppConfig:
        """Merge CLI argument overrides into AppConfig model.

        Args:
            config: Base AppConfig model
            cli_args: CLI arguments to merge

        Returns:
            Updated AppConfig model with CLI overrides
        """
        # Create a copy of the config as a dictionary for modification
        config_dict = config.dict()

        # Handle headless override
        if cli_args.get("headless") is not None:
            config_dict["webdriver"]["headless"] = cli_args["headless"]
            logging.info(f"CLI override: headless = {cli_args['headless']}")

        # Handle log level override
        if cli_args.get("log_level"):
            config_dict["log_level"] = cli_args["log_level"]
            logging.info(f"CLI override: log_level = {cli_args['log_level']}")

        # Handle max expand attempts override
        if cli_args.get("max_expand_attempts") is not None:
            config_dict["behavior"]["max_expand_attempts"] = cli_args["max_expand_attempts"]
            logging.info(
                f"CLI override: max_expand_attempts = {
                    cli_args['max_expand_attempts']}")

        # Create new AppConfig with merged values
        return AppConfig(**config_dict)

    def setup_directories(self, config_values: Dict) -> None:
        """Set up required directories.

        Args:
            config_values: Configuration values containing directory paths
        """
        directories = [
            config_values["base_output_dir"],
            config_values["debug_output_dir"],
            Path("logs")  # For log files
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logging.debug(f"Directory ensured: {directory}")
            except Exception as e:
                logging.error(f"Failed to create directory {directory}: {e}")
                raise

    def get_environment_info(self) -> Dict:
        """Get environment information for debugging.

        Returns:
            Dictionary containing environment information
        """
        import platform
        import sys

        return {
            "python_version": sys.version,
            "platform": platform.platform(),
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "python_executable": sys.executable,
        }

    def get_config(self) -> AppConfig:
        """Get the loaded configuration.

        Returns:
            AppConfig model
        """
        return self._config
