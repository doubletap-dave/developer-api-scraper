"""File operations service for Wyrm application.

This module handles file I/O operations including saving content to files,
managing output directories, and handling file system operations.
"""

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import List, Optional

from wyrm.models.scrape import SidebarItem, SidebarStructure


class FileOperations:
    """Service for handling file system operations.

    Manages all file I/O operations including content saving, directory
    management, and file system utilities for the scraping workflow.
    """

    def __init__(self) -> None:
        """Initialize the FileOperations service.

        Sets up the service for handling file operations throughout
        the scraping workflow.

        Args:
            None

        Returns:
            None
        """
        pass

    def save_content_to_file(
        self,
        content: str,
        output_path: Path,
        item_info: Optional[str] = None
    ) -> bool:
        """Save content to a file with proper error handling.

        Writes content to the specified file path, creating parent directories
        as needed. Provides comprehensive error handling and logging.

        Args:
            content: Content string to save to file.
            output_path: Path where the content should be saved.
            item_info: Optional information about the item for logging.

        Returns:
            bool: True if save was successful, False otherwise.

        Raises:
            OSError: If file cannot be written due to permissions or disk space.
        """
        try:
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logging.info(f"Content saved to: {output_path}")
            return True

        except Exception as e:
            error_msg = f"Failed to save content to {output_path}: {e}"
            if item_info:
                error_msg = f"Failed to save {item_info} to {output_path}: {e}"
            logging.error(error_msg)
            return False

    def save_structure_to_file(
        self,
        structure: SidebarStructure,
        output_path: Path
    ) -> bool:
        """Save sidebar structure to JSON file.

        Serializes the sidebar structure to JSON format and saves it to
        the specified path for later use or debugging.

        Args:
            structure: SidebarStructure model to save.
            output_path: Path where the structure should be saved.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        try:
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dictionary and save as JSON
            structure_dict = structure.dict()
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(structure_dict, f, indent=2, ensure_ascii=False)

            logging.info(f"Structure saved to: {output_path}")
            return True

        except Exception as e:
            logging.error(f"Failed to save structure to {output_path}: {e}")
            return False

    def load_structure_from_file(self, file_path: Path) -> Optional[SidebarStructure]:
        """Load sidebar structure from JSON file.

        Loads and deserializes a sidebar structure from a JSON file,
        returning None if the file doesn't exist or is invalid.

        Args:
            file_path: Path to the JSON file containing the structure.

        Returns:
            Optional[SidebarStructure]: Loaded structure or None if failed.
        """
        try:
            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                structure_dict = json.load(f)

            # Convert back to SidebarStructure model
            structure = SidebarStructure(**structure_dict)
            logging.info(f"Structure loaded from: {file_path}")
            return structure

        except Exception as e:
            logging.error(f"Failed to load structure from {file_path}: {e}")
            return None

    def get_output_filename(self, item: SidebarItem) -> str:
        """Generate output filename for a sidebar item.

        Creates a safe filename based on the item's text and ID,
        ensuring compatibility across different file systems.

        Args:
            item: SidebarItem to generate filename for.

        Returns:
            str: Safe filename for the item.
        """
        # Use item text and ID to create filename
        text = item.text if hasattr(item, 'text') else str(item.get('text', 'unknown'))
        item_id = item.id if hasattr(item, 'id') else item.get('id', 'unknown')

        # Clean text for filename
        safe_text = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_text = safe_text.replace(' ', '_')

        # Limit length and add ID
        if len(safe_text) > 50:
            safe_text = safe_text[:50]

        return f"{safe_text}_{item_id}.md"

    def check_file_exists(self, file_path: Path) -> bool:
        """Check if a file exists.

        Simple utility to check file existence with proper error handling.

        Args:
            file_path: Path to check for existence.

        Returns:
            bool: True if file exists, False otherwise.
        """
        try:
            return file_path.exists() and file_path.is_file()
        except Exception as e:
            logging.error(f"Error checking file existence {file_path}: {e}")
            return False

    def get_existing_files(self, directory: Path, items: List[SidebarItem]) -> List[Path]:
        """Get list of existing files for given items.

        Checks which items already have corresponding output files in the
        specified directory.

        Args:
            directory: Directory to check for existing files.
            items: List of sidebar items to check.

        Returns:
            List[Path]: List of existing file paths.
        """
        existing_files = []

        for item in items:
            filename = self.get_output_filename(item)
            file_path = directory / filename

            if self.check_file_exists(file_path):
                existing_files.append(file_path)

        return existing_files

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
