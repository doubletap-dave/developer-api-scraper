"""Debug file management functionality for parsing operations.

This module handles saving debug HTML and structure files to the debug directory.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional


class DebugManager:
    """Handles debug file operations for parsing service."""

    async def save_debug_html(
        self,
        sidebar_html: str,
        config_values: Dict,
        html_filename: Optional[str] = None,
    ) -> None:
        """Save raw HTML to debug directory.

        Args:
            sidebar_html: Raw sidebar HTML content
            config_values: Configuration values containing debug directory
            html_filename: Custom HTML filename (optional)
        """
        try:
            filename = html_filename or config_values["default_html_filename"]
            html_path = config_values["debug_output_dir"] / filename
            html_path.parent.mkdir(parents=True, exist_ok=True)

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(sidebar_html)

            logging.info(f"Debug HTML saved to: {html_path}")
        except Exception as e:
            logging.error(f"Failed to save debug HTML: {e}")

    async def save_debug_structure(
        self,
        sidebar_structure: Dict,
        config_values: Dict,
        structure_filename: Optional[str] = None,
    ) -> None:
        """Save parsed structure to debug directory.

        Args:
            sidebar_structure: Parsed sidebar structure
            config_values: Configuration values containing debug directory
            structure_filename: Custom structure filename (optional)
        """
        try:
            filename = structure_filename or config_values["default_structure_filename"]
            structure_path = config_values["debug_output_dir"] / filename
            structure_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle SidebarStructure models by converting to dict
            if hasattr(sidebar_structure, 'dict'):
                structure_data = sidebar_structure.dict()
            else:
                structure_data = sidebar_structure

            with open(structure_path, "w", encoding="utf-8") as f:
                json.dump(structure_data, f, indent=2, ensure_ascii=False)

            logging.info(f"Debug structure saved to: {structure_path}")
        except Exception as e:
            logging.error(f"Failed to save debug structure: {e}")

    def get_structure_filepath(self, config_values: Dict) -> Path:
        """Get the filepath for the sidebar structure.

        Args:
            config_values: Configuration values containing debug directory

        Returns:
            Path to structure file in debug directory
        """
        return config_values["debug_output_dir"] / "sidebar_structure.json"
