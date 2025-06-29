"""Link resolution functionality for ID generation and link processing.

This module handles ID generation, link processing, and URL/reference resolution
for the structure parser package.
"""

import logging
from typing import Any, Dict, List, Optional
import re

from bs4 import Tag

from ..selectors_service import SelectorsService


class LinkResolver:
    """Handles ID generation, link processing, and reference resolution."""

    def __init__(self, selectors_service: Optional[SelectorsService] = None) -> None:
        """Initialize the link resolver.

        Args:
            selectors_service: Optional configured selectors service
        """
        self.selectors = selectors_service or SelectorsService()

    def extract_item_id(self, clickable_li: Tag) -> Optional[str]:
        """Extract ID from a clickable element.

        Args:
            clickable_li: The clickable li element

        Returns:
            Element ID or None if not found
        """
        id_value = clickable_li.get("id")
        if isinstance(id_value, str):
            return id_value
        elif isinstance(id_value, list) and id_value:
            return id_value[0]  # Take first ID if multiple
        return None

    def generate_synthetic_id(self, item_text: str) -> str:
        """Generate a synthetic ID based on item text.

        Args:
            item_text: Text content to base the ID on

        Returns:
            Generated synthetic ID
        """
        # Clean the text and create a synthetic ID
        clean_text = item_text.lower()
        clean_text = re.sub(r'[^\w\s-]', '', clean_text)  # Remove special chars except hyphens
        clean_text = re.sub(r'\s+', '-', clean_text)  # Replace spaces with hyphens
        clean_text = re.sub(r'-+', '-', clean_text)  # Collapse multiple hyphens
        clean_text = clean_text.strip('-')  # Remove leading/trailing hyphens
        
        return f"synthetic-{clean_text}"

    def looks_like_api_endpoint(self, text: str) -> bool:
        """Check if text looks like an API endpoint that should be processed.

        Args:
            text: Item text to analyze

        Returns:
            True if this looks like a processable API endpoint
        """
        # Common patterns for API endpoints
        api_patterns = [
            "(GET)", "(POST)", "(PUT)", "(DELETE)", "(PATCH)",
            "Query", "Add", "Create", "Update", "Delete", "Modify",
            "Get ", "Set ", "List ", "Remove ", "Retrieve"
        ]

        text_lower = text.lower()
        return any(pattern.lower() in text_lower for pattern in api_patterns)

    def resolve_item_id(self, clickable_li: Tag, item_text: str) -> Optional[str]:
        """Resolve the ID for an item, generating one if necessary.

        Args:
            clickable_li: The clickable li element
            item_text: Text content of the item

        Returns:
            Resolved or generated ID
        """
        item_id = self.extract_item_id(clickable_li)
        
        # For PowerFlex endpoints, validate that items have meaningful IDs
        if not item_id and self.looks_like_api_endpoint(item_text):
            # Generate a synthetic ID based on the text
            item_id = self.generate_synthetic_id(item_text)
            logging.debug(f"Generated synthetic ID for API endpoint: {item_id}")
        elif not item_id:
            logging.warning(f"Item without ID may not be processable: '{item_text}'")
        
        return item_id

    def validate_id_requirement(self, item_id: Optional[str], item_type: str, item_text: str) -> bool:
        """Validate whether an item meets ID requirements.

        Args:
            item_id: The item's ID (may be None)
            item_type: Type of the item ('item' or 'menu')
            item_text: Text content of the item

        Returns:
            True if ID requirements are met
        """
        # Log a warning if an ID is missing, especially for items
        if not item_id:
            if item_type == "item":
                logging.warning(
                    f"Found ITEM without ID, will be skipped during processing. Text='{item_text}'")
                return False
            else:  # item_type == "menu"
                logging.debug(
                    f"Found MENU without ID. Will process children. Text='{item_text}'")
                return True  # Menus can exist without IDs if they have children
        
        return True

    def resolve_link_references(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve any link references in item data.

        Args:
            item_data: Item data dictionary

        Returns:
            Item data with resolved references
        """
        # Currently, this is a placeholder for future link resolution logic
        # In the future, this could handle:
        # - Resolving relative URLs to absolute URLs
        # - Processing anchor links
        # - Validating link targets
        # - Extracting href attributes from link elements
        
        return item_data

    def extract_anchor_href(self, element: Tag) -> Optional[str]:
        """Extract href attribute from an anchor element.

        Args:
            element: HTML element that might contain an anchor

        Returns:
            Href value or None if not found
        """
        anchor = element.find("a")
        if anchor and hasattr(anchor, 'get'):
            href_value = anchor.get("href")
            if isinstance(href_value, str):
                return href_value
            elif isinstance(href_value, list) and href_value:
                return href_value[0]  # Take first href if multiple
        return None

    def normalize_id(self, element_id: str) -> str:
        """Normalize an element ID for consistent processing.

        Args:
            element_id: Raw element ID

        Returns:
            Normalized ID
        """
        if not element_id:
            return element_id
        
        # Remove common prefixes and normalize format
        normalized = element_id.strip()
        
        # Remove any leading/trailing whitespace or special characters
        normalized = re.sub(r'^[\s\-_]+|[\s\-_]+$', '', normalized)
        
        return normalized

    def create_reference_map(self, items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Create a reference map for quick ID lookups.

        Args:
            items: List of parsed items

        Returns:
            Dictionary mapping IDs to item data
        """
        reference_map = {}
        
        for item in items:
            item_id = item.get("id")
            if item_id:
                normalized_id = self.normalize_id(item_id)
                reference_map[normalized_id] = item
        
        return reference_map

    def validate_references(self, items: List[Dict[str, Any]]) -> List[str]:
        """Validate that all references in items are resolvable.

        Args:
            items: List of parsed items to validate

        Returns:
            List of validation error messages
        """
        errors = []
        reference_map = self.create_reference_map(items)
        
        for item in items:
            item_id = item.get("id")
            item_text = item.get("text", "Unknown")
            
            # Check for duplicate IDs
            if item_id:
                normalized_id = self.normalize_id(item_id)
                if reference_map.get(normalized_id) != item:
                    errors.append(f"Duplicate ID found: {item_id} for item '{item_text}'")
        
        return errors
