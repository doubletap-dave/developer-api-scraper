"""Hierarchical structure parsing for 4.x API endpoints.

This module handles parsing of hierarchical sidebar structures commonly
found in 4.x API documentation endpoints.
"""

import logging
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag

from ..selectors_service import SelectorsService


class HierarchicalParser:
    """Handles parsing of hierarchical sidebar structures."""

    def __init__(self, selectors_service: SelectorsService) -> None:
        """Initialize the hierarchical parser.

        Args:
            selectors_service: Configured selectors service
        """
        self.selectors = selectors_service

    def parse_hierarchical_structure(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse hierarchical structure (4.x endpoints).
        
        Args:
            soup: BeautifulSoup object of the sidebar HTML
            
        Returns:
            List of header group dictionaries
        """
        structure_by_header: List[Dict[str, Any]] = []
        current_header_group: Optional[Dict[str, Any]] = None

        # Find the main UL containing the app-api-doc-item elements
        ul_selector_1 = f"{self.selectors.SIDEBAR_CONTAINER[1]} > app-api-doc-sidebar > ul"
        ul_selector_2 = f"{self.selectors.SIDEBAR_CONTAINER[1]} > ul"
        sidebar_root_ul = soup.select_one(f"{ul_selector_1}, {ul_selector_2}")
        if not sidebar_root_ul:
            logging.error("Could not find the main UL element within the sidebar HTML.")
            return []

        # Iterate through the direct children of the main UL
        for element in sidebar_root_ul.children:
            if not isinstance(element, Tag):
                continue  # Skip NavigableStrings like newlines

            # Case 1: It's an app-api-doc-item wrapper
            if element.name == self.selectors.APP_API_DOC_ITEM[1]:
                current_header_group = self._process_app_api_doc_item(
                    element, current_header_group, structure_by_header
                )

        return structure_by_header

    def _process_app_api_doc_item(
        self, 
        app_item: Tag, 
        current_header_group: Optional[Dict[str, Any]], 
        structure_by_header: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Process an app-api-doc-item element.
        
        Args:
            app_item: The app-api-doc-item element
            current_header_group: Current header group being processed
            structure_by_header: List of all header groups
            
        Returns:
            Updated current header group or None
        """
        # Check for Header LI within app-item
        header_li = app_item.select_one(self.selectors.SIDEBAR_HEADER_LI[1])
        if header_li:
            return self._process_header_item(header_li, structure_by_header)

        # If we haven't found a header yet, skip
        if not current_header_group:
            logging.warning(
                "Found sidebar item before finding the first header. Skipping."
            )
            return current_header_group

        # Check for Clickable LI (Item or Menu) within app-item
        clickable_li = app_item.select_one(self.selectors.SIDEBAR_CLICKABLE_LI[1])
        if clickable_li:
            self._process_clickable_item(app_item, clickable_li, current_header_group)

        return current_header_group

    def _process_header_item(
        self, 
        header_li: Tag, 
        structure_by_header: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process a header item.
        
        Args:
            header_li: The header list item element
            structure_by_header: List of all header groups
            
        Returns:
            New header group dictionary
        """
        header_link = header_li.select_one(self.selectors.HEADER_TEXT_ANCHOR[1])
        header_text = "Unknown Header"
        if header_link:
            header_text = header_link.get_text(strip=True)
        
        logging.debug(f"Found Header Group: {header_text}")
        current_header_group = {"header_text": header_text, "children": []}
        structure_by_header.append(current_header_group)
        return current_header_group

    def _process_clickable_item(
        self, 
        app_item: Tag, 
        clickable_li: Tag, 
        current_header_group: Dict[str, Any]
    ) -> None:
        """Process a clickable item (menu or regular item).
        
        Args:
            app_item: The parent app-api-doc-item element
            clickable_li: The clickable list item element
            current_header_group: Current header group to add item to
        """
        item_id = clickable_li.get("id")
        item_type = "item"  # Default
        is_expandable = False
        children = []  # For menus

        # Check if menu by looking for expander icons
        is_menu = bool(
            clickable_li.select_one(self.selectors.EXPANDER_ICON[1])
            or clickable_li.select_one(self.selectors.EXPANDED_ICON[1])
        )

        if is_menu:
            item_text = self._process_menu_item(
                app_item, clickable_li, item_id, children
            )
            item_type = "menu"
            is_expandable = True
        else:
            item_text = self._process_regular_item(clickable_li, item_id)

        # Skip "Overview" items/menus at the top level
        if item_text == "Overview":
            logging.debug(f"Skipping top-level '{item_text}' {item_type} (ID: {item_id})")
            return

        # Add the found item/menu
        if item_text and item_type:
            self._add_item_to_group(
                current_header_group, item_text, item_id, item_type, 
                is_expandable, children
            )

    def _process_menu_item(
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
            self._extract_menu_children(next_sibling, item_text, children)

        return item_text

    def _extract_menu_children(
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

    def _process_regular_item(self, clickable_li: Tag, item_id: Optional[str]) -> str:
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

    def _add_item_to_group(
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
