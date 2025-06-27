"""Item validation and filtering functionality for parsing operations.

This module handles validating parsed items and filtering them for processing.
"""

import logging
from typing import Dict, List, Optional


class ItemValidator:
    """Handles item validation and filtering operations."""

    def get_valid_items(self, sidebar_structure: Dict) -> List[Dict]:
        """Get valid items from sidebar structure.

        Args:
            sidebar_structure: Parsed sidebar structure

        Returns:
            List of valid items with required fields
        """
        items = sidebar_structure.get("items", [])
        valid_items = []

        for item in items:
            if self.is_valid_item(item):
                valid_items.append(item)
            else:
                logging.debug(f"Skipping invalid item: {item}")

        return valid_items

    def is_valid_item(self, item: Dict) -> bool:
        """Check if an item is valid for processing.

        Args:
            item: Item dictionary to validate

        Returns:
            True if item is valid, False otherwise
        """
        # Check required fields
        required_fields = ["id", "text"]
        for field in required_fields:
            if not item.get(field):
                return False

        # Additional validation can be added here
        return True

    def filter_items_for_processing(
        self,
        valid_items,
        max_items: Optional[int] = None,
        test_item_id: Optional[str] = None,
    ):
        """Filter items based on processing criteria.

        Args:
            valid_items: List of valid items
            max_items: Maximum number of items to process
            test_item_id: Specific item ID to process (deprecated)

        Returns:
            Filtered list of items for processing
        """
        items_to_process = valid_items.copy()

        # Handle deprecated test_item_id parameter
        if test_item_id:
            logging.warning(
                "The --test-item-id parameter is deprecated. "
                "Use --max-items=1 for testing with a single item."
            )
            items_to_process = [
                item for item in items_to_process
                if (hasattr(item, 'id') and item.id == test_item_id) or
                   (isinstance(item, dict) and item.get("id") == test_item_id)
            ]
            if not items_to_process:
                logging.warning(f"No item found with ID: {test_item_id}")

        # Apply max_items limit
        if max_items is not None and max_items > 0:
            items_to_process = items_to_process[:max_items]
            logging.info(f"Limited to first {max_items} items for processing.")

        return items_to_process
