"""CLI override handling for configuration management.

This module handles merging command-line arguments into configuration objects,
allowing CLI arguments to take precedence over file-based configuration.
"""

import structlog
from typing import Dict

from ...models.config import AppConfig


class CLIOverrideHandler:
    """Handles merging CLI arguments into configuration objects."""

    def __init__(self) -> None:
        """Initialize the CLI override handler."""
        self.logger = structlog.get_logger(__name__)

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
                - force_full_expansion: Override force full expansion setting

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

        # Handle force full expansion override
        if cli_args.get("force_full_expansion") is not None:
            config_dict["behavior"]["force_full_expansion"] = (
                cli_args["force_full_expansion"]
            )
            self.logger.info(
                "CLI override",
                setting="force_full_expansion",
                value=cli_args["force_full_expansion"]
            )

        # Create new AppConfig with merged values
        return AppConfig(**config_dict)
