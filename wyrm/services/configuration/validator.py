"""Pydantic validation module for configuration."""

from pydantic import ValidationError
from wyrm.models.config import AppConfig


def validate_config(config_data: dict) -> AppConfig:
    try:
        return AppConfig(**config_data)
    except ValidationError as e:
        raise ValueError(f"Invalid configuration data: {e}")
