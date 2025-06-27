"""Structure parsing functionality for sidebar HTML processing.

This module handles the core HTML parsing logic, converting raw sidebar HTML
into structured data and flattening it for processing.
"""

import logging
from typing import Any, Dict, List, Optional, cast

from bs4 import BeautifulSoup, Tag

from ..selectors_service import SelectorsService


class StructureParser:
    """Handles HTML parsing and structure flattening operations."""

    def __init__(self) -> None:
        """Initialize the structure parser."""
        self.selectors = SelectorsService()

    def map_sidebar_structure(self, sidebar_html: str) -> List[Dict]:
        """Parse the sidebar HTML and map its structure.

        Builds: List[Header] -> Header[Children] -> Child[Item | Menu] -> Menu[Children]
        Returns a list of dictionaries, each representing a top-level header group.
        """
        if not sidebar_html:
            logging.error("Cannot map structure: sidebar HTML is empty.")
            return []

        logging.info("Parsing sidebar HTML structure (expecting expanded state)...")
        soup = BeautifulSoup(sidebar_html, "html.parser")
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
                app_item = element

                # 1a. Check for Header LI within app-item
                header_li = app_item.select_one(self.selectors.SIDEBAR_HEADER_LI[1])
                if header_li:
                    header_link = header_li.select_one(self.selectors.HEADER_TEXT_ANCHOR[1])
                    header_text = "Unknown Header"
                    if header_link:
                        header_text = header_link.get_text(strip=True)
                    logging.debug(f"Found Header Group: {header_text}")
                    current_header_group = {"header_text": header_text, "children": []}
                    structure_by_header.append(current_header_group)
                    continue  # Move to the next element in sidebar_root_ul

                # If we haven't found a header yet, skip
                if not current_header_group:
                    logging.warning("Found sidebar item before finding the first header. Skipping.")
                    continue

                # 1b. Check for Clickable LI (Item or Menu) within app-item
                clickable_li = app_item.select_one(self.selectors.SIDEBAR_CLICKABLE_LI[1])
                if clickable_li:
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
                        item_type = "menu"
                        is_expandable = True
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
                                        logging.warning(f"  -> Found child LI but missing text or ID: {child_li.prettify()}")
                            logging.debug(f" -> Parsed {child_count} children for menu '{item_text}' from subsequent UL.")

                    else:  # Not a menu, must be a simple item
                        item_type = "item"
                        text_span_selector = self.selectors.ITEM_TEXT_SPAN[1]
                        text_element = clickable_li.select_one(text_span_selector)
                        item_text = "Unnamed Item"
                        if text_element:
                            item_text = text_element.get_text(strip=True)
                            item_text = item_text.replace("<!---->", "").strip()
                        if not text_element:
                            logging.warning(f"Classified as ITEM but couldn't find text span for LI ID {item_id}: {clickable_li.prettify()}")
                        item_id_str = item_id or "Missing"
                        logging.debug(f"Found Item: '{item_text}' (ID: {item_id_str})")

                    # Skip "Overview" items/menus at the top level too
                    if item_text == "Overview":
                        logging.debug(f"Skipping top-level '{item_text}' {item_type} (ID: {item_id})")
                        continue

                    # Add the found item/menu. Check for text/type, ID is optional for menus.
                    if item_text and item_type:
                        # Log a warning if an ID is missing, especially for items
                        if not item_id:
                            if item_type == "item":
                                logging.warning(f"Found ITEM without ID, will be skipped during processing. Text='{item_text}'")
                            else:  # item_type == "menu"
                                logging.debug(f"Found MENU without ID. Will process children. Text='{item_text}'")

                        # Define entry type explicitly to allow for optional 'children'
                        entry: Dict[str, Any] = {
                            "text": item_text,
                            "id": item_id,  # Store None if missing
                            "type": item_type,
                            "is_expandable": is_expandable,
                        }
                        if item_type == "menu":
                            current_children: List[Dict] = children if children else []
                            entry["children"] = current_children
                        cast(List, current_header_group["children"]).append(entry)
                    else:
                        logging.warning(f"Could not add entry: Missing text or type. Text='{item_text}', Type='{item_type}', ID={item_id}")

            # Case 2: It might be a plain UL (e.g., for menu children)
            elif element.name == "ul":
                logging.warning(f"Found a top-level UL sibling to app-api-doc-item. This might be unexpected. Content: {element.prettify()[:100]}...")

        logging.info(f"Finished parsing structure. Found {len(structure_by_header)} header groups.")
        return structure_by_header

    def flatten_sidebar_structure(self, structured_data: List[Dict]) -> List[Dict]:
        """Flatten the nested structure into a single list of items, preserving hierarchy info."""
        flattened_list: List[Dict] = []
        for header_group in structured_data:
            header_text = header_group.get("header_text", "Unknown Header")
            for top_level_item in header_group.get("children", []):
                # Process top-level items (can be menus or simple items)
                self._flatten_recursive(
                    top_level_item,
                    flattened_list,
                    header=header_text,
                    menu=None,
                    parent_menu_text=None,  # Top level items have no parent menu text within the group
                    level=0,
                )
        logging.info(f"Flattened structure contains {len(flattened_list)} processable items.")
        return flattened_list

    def _flatten_recursive(
        self,
        item: Dict,
        result_list: List[Dict],
        header: Optional[str],
        menu: Optional[str],  # The immediate parent menu's text
        parent_menu_text: Optional[str],  # The parent menu's text (could be same as menu)
        level: int,
    ):
        """Recursive helper to flatten the structure."""
        item_id = item.get("id")
        item_text = item.get("text")
        item_type = item.get("type")

        # Skip non-menu items if they lack critical data (ID, text, type)
        # Allow menus through even with missing ID because we need to process children
        if item_type != "menu" and (not item_id or not item_text or not item_type):
            logging.warning(f"Skipping non-menu item due to missing data: {item}")
            return
        elif item_type == "menu" and (not item_text or not item_type):  # Menus still need text and type
            logging.warning(f"Skipping menu item due to missing text/type: {item}")
            return

        # Add the current item/menu itself to the list
        flat_entry = {
            "id": item_id,  # Might be None for menus
            "text": item_text,
            "type": item_type,
            "header": header,
            "menu": menu,
            "parent_menu_text": parent_menu_text,  # Track parent for re-expansion
            "level": level,
        }
        result_list.append(flat_entry)

        # If it's a menu, recurse into its children
        if item_type == "menu" and item.get("is_expandable"):
            # Children of this menu have the current menu's text as their 'menu'
            # and also as their parent_menu_text
            for child in item.get("children", []):
                self._flatten_recursive(
                    child,
                    result_list,
                    header=header,
                    menu=item_text,  # Child belongs to this menu
                    parent_menu_text=item_text,  # This menu is the parent
                    level=level + 1,
                )
