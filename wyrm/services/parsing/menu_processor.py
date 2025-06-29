"""Menu processing for hierarchical structure parsing.

Handles extraction and processing of menu items and their children
in hierarchical sidebar structures.
"""

import logging
from typing import Dict, List, Optional

from bs4 import Tag

from ..selectors_service import SelectorsService


class MenuProcessor:
    """Handles processing of menu items in hierarchical structures."""

    def __init__(self, selectors_service: SelectorsService) -> None:
        """Initialize the menu processor.
        
        Args:
            selectors_service: Configured selectors service
        """
        self.selectors = selectors_service

    def process_menu_item(
        self, 
        app_item: Tag, 
        clickable_li: Tag, 
        item_id: Optional[str], 
        children: List[Dict]
    ) -> str:
        """Process a menu item and extract its children.
        
        Args:
            app_item: The parent app-api-doc-item element
            clickable_li: The clickable list item element
            item_id: The item ID
            children: List to populate with child items
            
        Returns:
            The menu text
        """
        text_div_selector = self.selectors.EXPANDABLE_MENU_TEXT_DIV[1]
        text_element = clickable_li.select_one(text_div_selector)
        item_text = "Unnamed Menu"
        if text_element:
            item_text = text_element.get_text(strip=True)
            item_text = item_text.replace("<!---->", "").strip()
        
        item_id_str = item_id or "Missing"
        logging.debug(f"Found Menu: '{item_text}' (ID: {item_id_str})")

        # Check for children in the *next* sibling UL
        next_sibling = app_item.find_next_sibling()
        if next_sibling and next_sibling.name == "ul":
            self.extract_menu_children(next_sibling, item_text, children)

        return item_text

    def extract_menu_children(
        self, 
        next_sibling: Tag, 
        item_text: str, 
        children: List[Dict]
    ) -> None:
        """Extract children from a menu's sibling UL element.
        
        Args:
            next_sibling: The UL element containing child items
            item_text: Parent menu text for logging
            children: List to populate with child items
        """
        logging.debug(f" -> Found subsequent UL, parsing children for menu '{item_text}'...")
        child_count = 0
        child_selector = self.selectors.APP_API_DOC_ITEM[1]
        
        for child_app_item in next_sibling.find_all(child_selector, recursive=False):
            child_clickable_selector = self.selectors.SIDEBAR_CLICKABLE_LI[1]
            child_li = child_app_item.select_one(child_clickable_selector)
            
            if child_li:
                child_id = child_li.get("id")
                child_text_span_selector = self.selectors.ITEM_TEXT_SPAN[1]
                child_text_element = child_li.select_one(child_text_span_selector)
                child_text = "Unnamed Sub-Item"
                
                if child_text_element:
                    child_text = child_text_element.get_text(strip=True)
                    child_text = child_text.replace("<!---->", "").strip()

                if child_text == "Overview":
                    logging.debug(f"  -> Skipping 'Overview' sub-item (ID: {child_id})")
                    continue

                if child_text and child_id:
                    logging.debug(f"  -> Found Sub-Item: '{child_text}' (ID: {child_id})")
                    children.append({
                        "text": child_text,
                        "id": child_id,
                        "type": "item",
                        "is_expandable": False,
                    })
                    child_count += 1
                else:
                    logging.warning(
                        f"  -> Found child LI but missing text or ID: {child_li.prettify()}"
                    )
        
        logging.debug(
            f" -> Parsed {child_count} children for menu '{item_text}' from subsequent UL."
        )
