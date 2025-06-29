"""Merging module for configuration precedence and overrides."""

from typing import Dict
from wyrm.models.config import AppConfig


def merge_cli_overrides(config: AppConfig, cli_args: Dict) -> AppConfig:
    from wyrm.services.configuration.cli_override_handler import CLIOverrideHandler

    cli_handler = CLIOverrideHandler()
    return cli_handler.merge_cli_overrides(config, cli_args)
