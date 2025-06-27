"""Storage service package for Wyrm application.

This package provides storage operations through specialized sub-modules:
- ContentExtractor: Handles content extraction from web pages
- FileOperations: Manages file saving and path generation
- ResumeManager: Handles resume information and status management
"""

from typing import Dict, List
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver

from .content_extractor import ContentExtractor
from .file_operations import FileOperations
from .resume_manager import ResumeManager


class StorageService:
    """Main storage service that coordinates specialized sub-modules.

    This service delegates to specialized sub-modules while maintaining
    backward compatibility with the original StorageService interface.
    """

    def __init__(self) -> None:
        """Initialize the storage service with sub-modules."""
        self.content_extractor = ContentExtractor()
        self.file_operations = FileOperations()
        self.resume_manager = ResumeManager()

    async def save_content_for_item(
        self,
        item,
        driver: WebDriver,
        config_values: Dict
    ) -> bool:
        """Extract and save content for a single item.

        Args:
            item: Item (SidebarItem model or dict) containing metadata
            driver: WebDriver instance
            config_values: Configuration values

        Returns:
            True if content was saved successfully, False otherwise
        """
        # Handle both SidebarItem models and dict items for backward compatibility
        if hasattr(item, 'text'):
            item_text = item.text
            header = item.header
            menu = item.menu
            item_id = item.id
        else:
            item_text = item.get("text", "Unknown Item")
            header = item.get("header")
            menu = item.get("menu")
            item_id = item.get("id")

        # Extract content using content extractor
        extracted_content = await self.content_extractor.extract_and_convert_content(driver)

        # Save content if extracted
        if extracted_content:
            saved = await self.file_operations.save_markdown(
                header=header,
                menu=menu,
                item_text=item_text,
                markdown_content=extracted_content,
                base_output_dir=config_values["base_output_dir"],
                overwrite=True,  # Force is handled at item level
            )
            return saved
        else:
            import logging
            logging.warning(f"No content extracted for item {item_id} ('{item_text}').")
            return False

    # Delegate methods to resume manager
    async def save_debug_page_content(
        self,
        item_id: str,
        driver: WebDriver,
        config_values: Dict
    ) -> None:
        """Save debug page content for troubleshooting."""
        await self.resume_manager.save_debug_page_content(item_id, driver, config_values)

    def check_existing_files(
        self,
        items,
        base_output_dir: Path
    ):
        """Check which items already have saved files."""
        return self.resume_manager.check_existing_files(items, base_output_dir)

    def save_structure_to_output(
        self,
        sidebar_structure: Dict,
        structure_filepath: Path
    ) -> None:
        """Save sidebar structure to output directory."""
        self.resume_manager.save_structure_to_output(sidebar_structure, structure_filepath)

    def display_resume_info(
        self,
        valid_items: List[Dict],
        existing_items: List[Dict],
        items_needing_processing: List[Dict],
        base_output_dir: Path,
    ) -> None:
        """Display resume information showing current status."""
        self.resume_manager.display_resume_info(
            valid_items, existing_items, items_needing_processing, base_output_dir
        )


# Maintain backward compatibility by exposing the main class
__all__ = ['StorageService']
