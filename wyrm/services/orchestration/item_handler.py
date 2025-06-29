"""Item handling utilities for orchestration operations.

This module provides utilities for validating, converting, and preprocessing
items before they are processed by the main orchestration workflow.
"""

import structlog
from typing import Dict, List, Any, Optional
from pathlib import Path


class ItemHandler:
    """Handles item validation, conversion, and preprocessing operations."""

    def __init__(self) -> None:
        """Initialize the item handler."""
        self.logger = structlog.get_logger(__name__)

    def convert_to_sidebar_items(self, items_to_process: List[Dict]) -> List:
        """Convert dict items to SidebarItem objects for parallel processing.
        
        Args:
            items_to_process: List of item dictionaries to convert
            
        Returns:
            List of SidebarItem objects
        """
        from wyrm.models.scrape import SidebarItem
        
        sidebar_items = []
        for item in items_to_process:
            if hasattr(item, 'id'):  # Already a SidebarItem
                sidebar_items.append(item)
            else:  # Dict item, convert to SidebarItem
                try:
                    sidebar_item = SidebarItem(**item)
                    sidebar_items.append(sidebar_item)
                except Exception as e:
                    self.logger.warning(
                        "Failed to convert item to SidebarItem, skipping",
                        item=item,
                        error=str(e)
                    )
                    continue
        return sidebar_items

    def validate_items(self, items: List[Dict]) -> List[Dict]:
        """Validate and filter items before processing.
        
        Args:
            items: List of items to validate
            
        Returns:
            List of valid items
        """
        valid_items = []
        for item in items:
            if self._is_valid_item(item):
                valid_items.append(item)
            else:
                item_id = self._extract_item_id(item)
                self.logger.warning("Skipping invalid item", item_id=item_id)
        
        self.logger.info(
            "Item validation completed", 
            total_items=len(items),
            valid_items=len(valid_items),
            invalid_items=len(items) - len(valid_items)
        )
        return valid_items

    def _is_valid_item(self, item: Dict) -> bool:
        """Check if an item is valid for processing.
        
        Args:
            item: Item to validate
            
        Returns:
            True if item is valid, False otherwise
        """
        # Extract item details regardless of format
        item_id = self._extract_item_id(item)
        item_text = self._extract_item_text(item)
        
        # Basic validation checks
        if not item_id or not item_text:
            return False
            
        # Skip certain types of items
        if self._should_skip_item(item_text):
            return False
            
        return True

    def _extract_item_id(self, item: Any) -> Optional[str]:
        """Extract item ID from various item formats.
        
        Args:
            item: Item to extract ID from
            
        Returns:
            Item ID if found, None otherwise
        """
        if hasattr(item, 'id'):
            return item.id
        elif isinstance(item, dict):
            return item.get('id')
        return None

    def _extract_item_text(self, item: Any) -> Optional[str]:
        """Extract item text from various item formats.
        
        Args:
            item: Item to extract text from
            
        Returns:
            Item text if found, None otherwise
        """
        if hasattr(item, 'text'):
            return item.text
        elif isinstance(item, dict):
            return item.get('text')
        return None

    def _should_skip_item(self, item_text: str) -> bool:
        """Check if an item should be skipped based on its text.
        
        Args:
            item_text: Text content of the item
            
        Returns:
            True if item should be skipped, False otherwise
        """
        if not item_text:
            return True
            
        # Skip common placeholder or empty items
        skip_patterns = [
            "coming soon",
            "placeholder",
            "todo",
            "tbd",
            "not available",
            "n/a"
        ]
        
        text_lower = item_text.lower().strip()
        return any(pattern in text_lower for pattern in skip_patterns)

    def check_existing_file(
        self, item: Any, base_output_dir: str, force: bool = False
    ) -> tuple[bool, Optional[Path]]:
        """Check if output file already exists for an item.
        
        Args:
            item: Item to check
            base_output_dir: Base output directory
            force: Whether to force processing even if file exists
            
        Returns:
            Tuple of (should_skip, file_path)
        """
        if force:
            return False, None
            
        # This would need to be implemented with access to storage service
        # For now, return a basic implementation
        item_id = self._extract_item_id(item)
        if not item_id:
            return False, None
            
        # Basic file path construction (would need actual storage service logic)
        output_path = Path(base_output_dir) / f"{item_id}.md"
        exists = output_path.exists()
        
        return exists, output_path if exists else None

    def prepare_item_for_processing(self, item: Any) -> Dict[str, Any]:
        """Prepare an item for processing by extracting necessary information.
        
        Args:
            item: Item to prepare
            
        Returns:
            Dictionary with standardized item information
        """
        return {
            'id': self._extract_item_id(item),
            'text': self._extract_item_text(item),
            'type': getattr(item, 'type', 'unknown') if hasattr(item, 'type') else item.get('type', 'unknown'),
            'menu': getattr(item, 'menu', None) if hasattr(item, 'menu') else item.get('menu'),
            'header': getattr(item, 'header', None) if hasattr(item, 'header') else item.get('header'),
            'original_item': item
        }

    def group_items_by_menu(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Group items by their menu for optimized processing.
        
        Args:
            items: List of items to group
            
        Returns:
            Dictionary mapping menu names to lists of items
        """
        groups = {}
        
        for item in items:
            menu = None
            if hasattr(item, 'menu'):
                menu = item.menu
            elif isinstance(item, dict):
                menu = item.get('menu')
                
            menu_key = menu or 'no_menu'
            
            if menu_key not in groups:
                groups[menu_key] = []
            groups[menu_key].append(item)
            
        self.logger.debug(
            "Grouped items by menu",
            total_items=len(items),
            menu_groups=len(groups),
            group_sizes={k: len(v) for k, v in groups.items()}
        )
        
        return groups
