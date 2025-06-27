"""Configuration service for Wyrm application.

This service handles configuration loading, validation, environment setup,
logging configuration, and utility functions.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

import yaml
from rich.logging import RichHandler


class ConfigurationService:
    """Service for handling configuration and logging setup."""

    def __init__(self) -> None:
        """Initialize the Configuration service."""
        self._config = {}

    def setup_logging(self, log_level: str = "INFO", log_file: Optional[Path] = None) -> None:
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

        # Clear existing handlers (important if this function might be called multiple times)
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

        logging.info(f"Logging setup complete. Level: {log_level}, Console: True, File: {log_file}")

    def load_config(self, config_path: Optional[Path] = None) -> Dict:
        """Load configuration from a YAML file.

        Args:
            config_path: Path to configuration file (defaults to config.yaml)

        Returns:
            Loaded configuration dictionary

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If configuration file is invalid YAML
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
                config = yaml.safe_load(f)
            logging.debug(f"Configuration loaded: {config}")
            self._config = config  # Store for get_config method
            return config
        except yaml.YAMLError as e:
            logging.exception(f"Error parsing configuration file {path}: {e}")
            raise
        except Exception as e:
            logging.exception(f"Error reading configuration file {path}: {e}")
            raise

    def extract_configuration_values(self, config: Dict) -> Dict:
        """Extract and validate configuration values.

        Args:
            config: Raw configuration dictionary

        Returns:
            Processed configuration values dictionary
        """
        logging.info("Extracting configuration values...")

        try:
            # Extract base paths
            base_output_dir = Path(config.get("output", {}).get("base_directory", "output"))
            debug_output_dir = Path(config.get("debug_settings", {}).get("output_directory", "debug"))

            # Extract timeout values
            timeouts = config.get("timeouts", {})
            sidebar_wait_timeout = timeouts.get("sidebar_wait_timeout", 15)
            navigation_timeout = timeouts.get("navigation_timeout", 10)
            content_wait_timeout = timeouts.get("content_wait_timeout", 20)

            # Extract delay values
            delays = config.get("delays", {})
            expand_delay = delays.get("expand_delay", 0.5)
            post_click_delay = delays.get("post_click_delay", 1.0)

            # Extract debug settings
            debug_settings = config.get("debug_settings", {})
            default_html_filename = debug_settings.get("save_html_filename", "sidebar.html")
            default_structure_filename = debug_settings.get("save_structure_filename", "structure.json")

            config_values = {
                "base_output_dir": base_output_dir,
                "debug_output_dir": debug_output_dir,
                "sidebar_wait_timeout": sidebar_wait_timeout,
                "navigation_timeout": navigation_timeout,
                "content_wait_timeout": content_wait_timeout,
                "expand_delay": expand_delay,
                "post_click_delay": post_click_delay,
                "default_html_filename": default_html_filename,
                "default_structure_filename": default_structure_filename,
            }

            # Validate critical values
            self._validate_configuration_values(config_values)

            logging.info("Configuration values extracted and validated successfully.")
            return config_values

        except Exception as e:
            logging.error(f"Failed to extract configuration values: {e}")
            raise

    def _validate_configuration_values(self, config_values: Dict) -> None:
        """Validate extracted configuration values.

        Args:
            config_values: Configuration values to validate

        Raises:
            ValueError: If any configuration value is invalid
        """
        # Validate timeout values
        timeout_fields = ["sidebar_wait_timeout", "navigation_timeout", "content_wait_timeout"]
        for field in timeout_fields:
            value = config_values.get(field)
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"Invalid {field}: must be a positive number, got {value}")

        # Validate delay values
        delay_fields = ["expand_delay", "post_click_delay"]
        for field in delay_fields:
            value = config_values.get(field)
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"Invalid {field}: must be a non-negative number, got {value}")

        # Validate paths
        path_fields = ["base_output_dir", "debug_output_dir"]
        for field in path_fields:
            value = config_values.get(field)
            if not isinstance(value, Path):
                raise ValueError(f"Invalid {field}: must be a Path object, got {type(value)}")

        # Validate filename strings
        filename_fields = ["default_html_filename", "default_structure_filename"]
        for field in filename_fields:
            value = config_values.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Invalid {field}: must be a non-empty string, got {value}")

    def merge_cli_overrides(self, config: Dict, cli_args: Dict) -> Dict:
        """Merge CLI argument overrides into configuration.

        Args:
            config: Base configuration dictionary
            cli_args: CLI arguments to merge

        Returns:
            Updated configuration dictionary
        """
        updated_config = config.copy()

        # Handle headless override
        if cli_args.get("headless") is not None:
            if "webdriver" not in updated_config:
                updated_config["webdriver"] = {}
            updated_config["webdriver"]["headless"] = cli_args["headless"]
            logging.info(f"CLI override: headless = {cli_args['headless']}")

        # Handle log level override
        if cli_args.get("log_level"):
            if "logging" not in updated_config:
                updated_config["logging"] = {}
            updated_config["logging"]["level"] = cli_args["log_level"]
            logging.info(f"CLI override: log_level = {cli_args['log_level']}")

        # Handle max expand attempts override
        if cli_args.get("max_expand_attempts") is not None:
            if "limits" not in updated_config:
                updated_config["limits"] = {}
            updated_config["limits"]["max_expand_attempts"] = cli_args["max_expand_attempts"]
            logging.info(f"CLI override: max_expand_attempts = {cli_args['max_expand_attempts']}")

        return updated_config

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

    def get_config(self) -> Dict:
        """Get the loaded configuration.

        Returns:
            Configuration dictionary
        """
        return self._config.copy()
