"""Item processing for hierarchical structure parsing.

Handles extraction and processing of regular items and adding them
to header groups in hierarchical sidebar structures.
"""

import logging
from typing import Any, Dict, List, Optional

from bs4 import Tag

from ..selectors_service import SelectorsService


class ItemProcessor:
    """Handles processing of regular items in hierarchical structures."""

    def __init__(self, selectors_service: SelectorsService) -> None:
        """Initialize the item processor.
        
        Args:
            selectors_service: Configured selectors service
        """
        self.selectors = selectors_service

    def process_regular_item(self, clickable_li: Tag, item_id: Optional[str]) -> str:
        """Process a regular (non-menu) item.
        
        Args:
            clickable_li: The clickable list item element
            item_id: The item ID
            
        Returns:
            The item text
        """
        text_span_selector = self.selectors.ITEM_TEXT_SPAN[1]
        text_element = clickable_li.select_one(text_span_selector)
        item_text = "Unnamed Item"
        
        if text_element:
            item_text = text_element.get_text(strip=True)
            item_text = item_text.replace("<!---->", "").strip()
        
        if not text_element:
            logging.warning(
                f"Classified as ITEM but couldn't find text span for LI ID {item_id}: "
                f"{clickable_li.prettify()}"
            )
        
        item_id_str = item_id or "Missing"
        logging.debug(f"Found Item: '{item_text}' (ID: {item_id_str})")
        
        return item_text

    def add_item_to_group(
        self, 
        current_header_group: Dict[str, Any], 
        item_text: str, 
        item_id: Optional[str], 
        item_type: str, 
        is_expandable: bool, 
        children: List[Dict]
    ) -> None:
        """Add an item to the current header group.
        
        Args:
            current_header_group: Header group to add item to
            item_text: Text of the item
            item_id: ID of the item (can be None for menus)
            item_type: Type of item ('item' or 'menu')
            is_expandable: Whether the item is expandable
            children: List of child items (for menus)
        """
        # Log a warning if an ID is missing, especially for items
        if not item_id:
            if item_type == "item":
                logging.warning(f"Item '{item_text}' has no ID. This may cause issues.")
            else:
                logging.debug(f"Menu '{item_text}' has no ID (this is sometimes normal).")

        # Add to the current header group
        current_header_group["children"].append({
            "text": item_text,
            "id": item_id,
            "type": item_type,
            "is_expandable": is_expandable,
            "children": children,
        })
