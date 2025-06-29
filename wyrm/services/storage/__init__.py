"""Storage service package for Wyrm application.

This package provides storage operations through specialized sub-modules:
- ContentExtractor: Handles content extraction from web pages
- FileWriter: Manages atomic file writing with resume and checksum support
- PathBuilder: Generates deterministic paths from item metadata
- MarkdownSanitizer: Cleans and post-processes markdown content
- ResumeManager: Handles resume information and status management
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver

from .content_extractor import ContentExtractor
from .file_writer import FileWriter
from .path_builder import PathBuilder
from .markdown_sanitizer import MarkdownSanitizer
from .resume_manager import ResumeManager


class StorageService:
    """Main storage service that coordinates specialized sub-modules.

    This service delegates to specialized sub-modules while maintaining
    backward compatibility with the original StorageService interface.
    """

    def __init__(self) -> None:
        """Initialize the storage service with sub-modules."""
        self.content_extractor = ContentExtractor()
        self.file_writer = FileWriter()
        self.path_builder = PathBuilder()
        self.markdown_sanitizer = MarkdownSanitizer()
        self.resume_manager = ResumeManager()

    def get_output_path(self, item, base_output_dir: Path) -> Path:
        """Get the output file path for an item.

        Args:
            item: Item (SidebarItem model or dict) containing metadata
            base_output_dir: Base output directory

        Returns:
            Path: Complete file path for the output file
        """
        # Handle both SidebarItem models and dict items for backward compatibility
        if hasattr(item, 'text'):
            item_text = item.text
            header = item.header
            menu = item.menu
        else:
            item_text = item.get("text", "Unknown Item")
            header = item.get("header")
            menu = item.get("menu")

        return self.path_builder.get_output_file_path(
            header=header,
            menu=menu,
            item_text=item_text,
            base_output_dir=base_output_dir
        )

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
        # Verify driver is provided and valid
        if not driver:
            raise ValueError("WebDriver instance is required for content extraction")

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
            saved = await self.save_markdown(
                header=header,
                menu=menu,
                item_text=item_text,
                markdown_content=extracted_content,
                base_output_dir=config_values["base_output_dir"],
                overwrite=True,  # Force is handled at item level
            )
            return saved
        else:
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
        self.resume_manager.save_structure_to_output(
            sidebar_structure, structure_filepath)

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
    
    async def save_markdown(
        self,
        header: Optional[str],
        menu: Optional[str],
        item_text: str,
        markdown_content: str,
        base_output_dir: Path,
        overwrite: bool = False,
        sanitize_content: bool = True,
        verify_checksum: bool = True
    ) -> bool:
        """Save markdown content to file using coordinated sub-modules.
        
        This is the main entry point for saving markdown content. It coordinates
        the path building, content sanitization, and atomic file writing.
        
        Args:
            header: Header text for path generation
            menu: Menu text for path generation  
            item_text: Item text for filename
            markdown_content: Content to save
            base_output_dir: Base output directory
            overwrite: Whether to overwrite existing files
            sanitize_content: Whether to sanitize markdown content
            verify_checksum: Whether to verify content integrity
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Build and validate output path
            output_file = self._build_and_validate_path(
                header, menu, item_text, base_output_dir
            )
            if not output_file:
                return False
            
            # Check file existence and handle skipping
            if self._should_skip_existing_file(output_file, markdown_content, overwrite):
                return True
            
            # Process content and write file
            return self._process_and_write_content(
                markdown_content, output_file, header, menu, item_text,
                sanitize_content, verify_checksum
            )
            
        except Exception as e:
            logging.error(f"Failed to save markdown content: {e}")
            return False

    def _build_and_validate_path(self, header, menu, item_text, base_output_dir):
        """Build output path and validate safety."""
        # Build output file path using PathBuilder
        output_file = self.path_builder.get_output_file_path(
            header=header,
            menu=menu,
            item_text=item_text,
            base_output_dir=base_output_dir
        )
        
        # Validate path safety
        if not self.path_builder.validate_path_safety(output_file):
            logging.error(f"Path safety validation failed: {output_file}")
            return None
        
        return output_file

    def _should_skip_existing_file(self, output_file, markdown_content, overwrite):
        """Check if existing file should be skipped."""
        # Check if file already exists and overwrite is not enabled
        if self.file_writer.check_file_exists(output_file) and not overwrite:
            # Check if we can resume (content matches)
            if self.file_writer.can_resume_write(output_file, markdown_content):
                logging.info(f"File already exists with same content, skipping: {output_file}")
                return True
            else:
                logging.info(f"File already exists, skipping: {output_file}")
                return True
        return False

    def _process_and_write_content(
        self, markdown_content, output_file, header, menu, item_text,
        sanitize_content, verify_checksum
    ):
        """Process content and write to file."""
        # Sanitize content if requested
        processed_content = markdown_content
        if sanitize_content:
            processed_content = self.markdown_sanitizer.sanitize_content(
                markdown_content,
                remove_empty_lines=True,
                fix_headers=True,
                clean_tables=True,
                normalize_whitespace=True
            )
        
        # Write file atomically using FileWriter
        success = self.file_writer.write_file_atomic(
            content=processed_content,
            output_path=output_file,
            item_info=f"{header}/{menu}/{item_text}" if header or menu else item_text,
            verify_checksum=verify_checksum
        )
        
        if success:
            logging.info(f"Successfully saved markdown to: {output_file}")
        
        return success


# Maintain backward compatibility by exposing the main class
__all__ = ['StorageService']
