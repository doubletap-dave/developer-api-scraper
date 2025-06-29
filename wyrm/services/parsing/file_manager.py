"""File I/O management functionality for parsing operations.

This module handles loading and saving structure files to/from the filesystem.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional


class FileManager:
    """Handles file I/O operations for parsing service."""

    def load_existing_structure(self, structure_filepath: Path) -> tuple[Optional[Dict], bool]:
        """Load existing sidebar structure from file.

        Args:
            structure_filepath: Path to existing structure file

        Returns:
            Tuple of (loaded structure dictionary or None if loading fails, from_cache flag)
        """
        try:
            if structure_filepath.exists():
                logging.info(f"Loading existing structure from: {structure_filepath}")
                with open(structure_filepath, "r", encoding="utf-8") as f:
                    structure = json.load(f)
                    return structure, True  # from_cache = True
            else:
                logging.debug(f"Structure file does not exist: {structure_filepath}")
                return None, False  # from_cache = False
        except Exception as e:
            logging.error(f"Failed to load existing structure: {e}")
            return None, False  # from_cache = False

    def save_structure_to_file(self, structure_map: List[Dict], filepath: Path) -> None:
        """Save the structured sidebar map to a JSON file.

        Args:
            structure_map: The structured sidebar data
            filepath: Path where to save the structure
        """
        try:
            # Ensure the directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(structure_map, f, indent=4, ensure_ascii=False)
            logging.info(f"Successfully saved sidebar structure map to: {filepath}")
        except IOError as e:
            logging.error(f"Error saving sidebar structure map to {filepath}: {e}")
        except Exception as e:
            logging.exception(f"Unexpected error saving sidebar structure map: {e}")

    def load_structure_from_file(self, filepath: Path) -> Optional[List[Dict]]:
        """Load the structured sidebar map from a JSON file.

        Args:
            filepath: Path to the structure file

        Returns:
            Loaded structure data or None if loading fails
        """
        if not filepath.exists():
            logging.info(f"Structure map file not found: {filepath}")
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                structure_map = json.load(f)
            logging.info(f"Successfully loaded sidebar structure map from: {filepath}")
            return structure_map
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from {filepath}: {e}")
            return None
        except IOError as e:
            logging.error(f"Error reading sidebar structure map from {filepath}: {e}")
            return None
        except Exception as e:
            logging.exception(f"Unexpected error loading sidebar structure map: {e}")
            return None
