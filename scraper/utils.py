import logging
import re

# import sys  # F401 Removed
import unicodedata
from pathlib import Path

import yaml
from rich.logging import RichHandler


def setup_logging(log_level: str = "INFO", log_file: str | Path = "scraper.log"):
    """Configure logging using RichHandler for console and FileHandler for file."""
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
    console_handler = RichHandler(rich_tracebacks=True, markup=True)
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

    log_msg = (
        f"Logging setup complete. Level: {log_level}, "
        f"Console: True, File: {log_file}"
    )
    logging.info(log_msg)


def load_config(config_path: str | Path = "config.yaml") -> dict:
    """Load configuration from a YAML file."""
    path = Path(config_path)
    logging.info(f"Loading configuration from: {path.absolute()}")
    if not path.is_file():
        logging.error(f"Configuration file not found: {path}")
        raise FileNotFoundError(f"Configuration file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logging.debug(f"Configuration loaded: {config}")
        return config
    except yaml.YAMLError as e:
        logging.exception(f"Error parsing configuration file {path}: {e}")
        raise
    except Exception as e:
        logging.exception(f"Error reading configuration file {path}: {e}")
        raise


def slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.

    Slightly modified from Django's slugify function.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    # Use raw strings for regex patterns
    value = re.sub(r"[^\w\s-]", "", value.lower())  # Remove non-word/space/hyphen chars
    value = re.sub(
        r"[-\s]+", "-", value
    )  # Collapse whitespace/hyphens to single hyphen
    value = value.strip("-_")  # Strip leading/trailing hyphens/underscores

    # Ensure not empty
    if not value:
        return "_"  # Return default for empty slugs
    return value


def get_output_file_path(
    header: str | None,
    menu: str | None,
    item_text: str,
    base_output_dir: str | Path,
) -> Path:
    """
    Generates the full output file path for a scraped item.

    Includes slugified directories based on header and menu.
    """
    base_path = Path(base_output_dir)
    path_parts = []

    # Use slugified names for directories and the filename stem
    if header:
        path_parts.append(slugify(header))
    if menu:
        path_parts.append(slugify(menu))

    # Filename is based on item_text
    filename = f"{slugify(item_text)}.md"

    # Combine path parts and filename
    full_path = base_path.joinpath(*path_parts, filename)

    log_details = (
        f"Generated path: {full_path} (Header: '{header}', "
        f"Menu: '{menu}', Item: '{item_text}')"
    )
    logging.debug(log_details)
    return full_path
