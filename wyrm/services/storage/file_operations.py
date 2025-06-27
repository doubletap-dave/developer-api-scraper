"""File operations module for Wyrm application.

This module handles file path generation, markdown saving, and file system operations.
"""

import logging
import re
import unicodedata
from pathlib import Path
from typing import Dict, Optional


class FileOperations:
    """Handles file operations and path management."""

    def __init__(self) -> None:
        """Initialize the file operations handler."""
        pass

    async def save_markdown(
        self,
        header: Optional[str],
        menu: Optional[str],
        item_text: str,
        markdown_content: str,
        base_output_dir: Path,
        overwrite: bool = False,
    ) -> bool:
        """Save markdown content to file.

        Args:
            header: Header text for path generation
            menu: Menu text for path generation
            item_text: Item text for filename
            markdown_content: Content to save
            base_output_dir: Base output directory
            overwrite: Whether to overwrite existing files

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            output_file = self._get_output_file_path(header, menu, item_text, base_output_dir)

            # Check if file already exists and overwrite is not enabled
            if output_file.exists() and not overwrite:
                logging.info(f"File already exists, skipping: {output_file}")
                return True

            # Ensure parent directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            self._write_file_sync(output_file, markdown_content)

            logging.info(f"Successfully saved markdown to: {output_file}")
            return True

        except Exception as e:
            logging.error(f"Failed to save markdown content: {e}")
            return False

    def _write_file_sync(self, output_file: Path, markdown_content: str):
        """Write content to file synchronously.

        Args:
            output_file: Path to output file
            markdown_content: Content to write
        """
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

    def _get_output_file_path(
        self,
        header: Optional[str],
        menu: Optional[str],
        item_text: str,
        base_output_dir: Path,
    ) -> Path:
        """Generate output file path based on item metadata.

        Args:
            header: Header text for directory structure
            menu: Menu text for directory structure
            item_text: Item text for filename
            base_output_dir: Base output directory

        Returns:
            Complete file path for the output file
        """
        # Start with base directory
        path_parts = [base_output_dir]

        # Add header if available
        if header and header.strip():
            header_slug = self._slugify(header)
            if header_slug:
                path_parts.append(header_slug)

        # Add menu if available and different from header
        if menu and menu.strip() and menu != header:
            menu_slug = self._slugify(menu)
            if menu_slug:
                path_parts.append(menu_slug)

        # Create the directory path
        directory_path = Path(*path_parts)

        # Generate filename from item text
        filename_slug = self._slugify(item_text)
        if not filename_slug:
            filename_slug = "untitled"

        # Ensure .md extension
        if not filename_slug.endswith('.md'):
            filename_slug += '.md'

        return directory_path / filename_slug

    def _slugify(self, value, allow_unicode=False):
        """Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
        Remove characters that aren't alphanumerics, underscores, or hyphens.
        Convert to lowercase. Also strip leading and trailing whitespace.

        Args:
            value: String to slugify
            allow_unicode: Whether to allow unicode characters

        Returns:
            Slugified string suitable for file/directory names
        """
        if not value:
            return ""

        value = str(value)
        if allow_unicode:
            value = unicodedata.normalize('NFKC', value)
        else:
            value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')

        # Replace spaces and other separators with hyphens
        value = re.sub(r'[-\s_/\\]+', '-', value)

        # Remove characters that aren't alphanumerics, underscores, hyphens, or dots
        value = re.sub(r'[^\w\-\.]', '', value)

        # Convert to lowercase and strip
        value = value.lower().strip('-_.')

        # Limit length to reasonable filename size
        if len(value) > 100:
            value = value[:100].rstrip('-_.')

        return value
