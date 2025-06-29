"""Parsing service for Wyrm application.

This service handles sidebar structure parsing, HTML content processing,
item validation and filtering, and debug HTML/structure saving.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from wyrm.models.scrape import SidebarItem, SidebarStructure
from ..selectors_service import SelectorsService
from .debug_manager import DebugManager
from .file_manager import FileManager
from .item_validator import ItemValidator
from .structure_parser import StructureParser


class ParsingService:
    """Service for handling parsing operations."""

    def __init__(self, selectors_service: Optional[SelectorsService] = None) -> None:
        """Initialize the Parsing service.
        
        Args:
            selectors_service: Optional configured selectors service for endpoint-specific parsing
        """
        self.structure_parser = StructureParser(selectors_service)
        self.debug_manager = DebugManager()
        self.item_validator = ItemValidator()
        self.file_manager = FileManager()

    async def parse_sidebar_structure(self, sidebar_html: str) -> SidebarStructure:
        """Parse sidebar HTML into structured format.

        Args:
            sidebar_html: Raw sidebar HTML content

        Returns:
            Parsed SidebarStructure model
        """
        logging.info("Parsing sidebar structure...")

        # Parse HTML structure
        structured_data = self.structure_parser.map_sidebar_structure(sidebar_html)

        # Flatten the structure for processing
        flattened_items_dict = self.structure_parser.flatten_sidebar_structure(
            structured_data)

        # Convert dict items to SidebarItem models
        sidebar_items = []
        for item_dict in flattened_items_dict:
            try:
                sidebar_item = SidebarItem(**item_dict)
                sidebar_items.append(sidebar_item)
            except Exception as e:
                logging.warning(f"Failed to create SidebarItem from {item_dict}: {e}")

        # Build the final structure using SidebarStructure model
        sidebar_structure = SidebarStructure(
            structured_data=structured_data,  # Keep as dict for now
            items=sidebar_items
        )

        # Count valid items using the model's property
        valid_items = sidebar_structure.valid_items
        logging.info(f"Found {len(valid_items)} valid items in sidebar structure.")

        return sidebar_structure

    # Delegate to structure_parser
    def _map_sidebar_structure(self, sidebar_html: str) -> List[Dict]:
        """Parse the sidebar HTML and map its structure."""
        return self.structure_parser.map_sidebar_structure(sidebar_html)

    def _flatten_sidebar_structure(self, structured_data: List[Dict]) -> List[Dict]:
        """Flatten the nested structure into a single list of items."""
        return self.structure_parser.flatten_sidebar_structure(structured_data)

    # Delegate to debug_manager
    async def save_debug_html(
        self,
        sidebar_html: str,
        config_values: Dict,
        html_filename: Optional[str] = None,
    ) -> None:
        """Save raw HTML to debug directory."""
        await self.debug_manager.save_debug_html(sidebar_html, config_values, html_filename)

    async def save_debug_structure(
        self,
        sidebar_structure: Dict,
        config_values: Dict,
        structure_filename: Optional[str] = None,
    ) -> None:
        """Save parsed structure to debug directory."""
        await self.debug_manager.save_debug_structure(sidebar_structure, config_values, structure_filename)

    def get_structure_filepath(self, config_values: Dict) -> Path:
        """Get the filepath for the sidebar structure."""
        return self.debug_manager.get_structure_filepath(config_values)

    # Delegate to item_validator
    def _get_valid_items(self, sidebar_structure) -> List[SidebarItem]:
        """Get valid items from sidebar structure."""
        if isinstance(sidebar_structure, SidebarStructure):
            return sidebar_structure.valid_items
        else:
            # Backward compatibility for dict-based structure
            return self.item_validator.get_valid_items(sidebar_structure)

    def _is_valid_item(self, item: Dict) -> bool:
        """Check if an item is valid for processing."""
        return self.item_validator.is_valid_item(item)

    def filter_items_for_processing(
        self,
        valid_items: List[Dict],
        max_items: Optional[int] = None,
        test_item_id: Optional[str] = None,
    ) -> List[Dict]:
        """Filter items based on processing criteria."""
        return self.item_validator.filter_items_for_processing(valid_items, max_items, test_item_id)

    # Delegate to file_manager
    def load_existing_structure(self, structure_filepath: Path) -> tuple[Optional[Dict], bool]:
        """Load existing sidebar structure from file.

        Returns:
            Tuple of (loaded structure dictionary or None if loading fails, from_cache flag)
        """
        return self.file_manager.load_existing_structure(structure_filepath)

    def save_structure_to_file(self, structure_map: List[Dict], filepath: Path) -> None:
        """Save the structured sidebar map to a JSON file."""
        self.file_manager.save_structure_to_file(structure_map, filepath)

    def load_structure_from_file(self, filepath: Path) -> Optional[List[Dict]]:
        """Load the structured sidebar map from a JSON file."""
        return self.file_manager.load_structure_from_file(filepath)
