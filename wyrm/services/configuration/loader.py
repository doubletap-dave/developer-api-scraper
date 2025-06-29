"""Configuration loading module.

This module reads configurations from environment variables, CLI,
and default settings.
"""

import structlog
from pathlib import Path
from typing import Optional

import yaml
from wyrm.models.config import AppConfig


class ConfigurationLoader:
    """Handles configuration loading from YAML files."""

    def __init__(self, logger: Optional[structlog.stdlib.BoundLogger] = None) -> None:
        self.logger = logger or structlog.get_logger(__name__)

    def load_config(self, config_path: Optional[Path] = None) -> AppConfig:
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

            config = AppConfig(**raw_config)
            self.logger.debug(
                "Configuration loaded and validated", config=str(config)
            )
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
