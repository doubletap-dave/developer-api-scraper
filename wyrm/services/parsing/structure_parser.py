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

    def __init__(self, selectors_service: Optional[SelectorsService] = None) -> None:
        """Initialize the structure parser.
        
        Args:
            selectors_service: Optional configured selectors service
        """
        self.selectors = selectors_service or SelectorsService()

    def map_sidebar_structure(self, sidebar_html: str) -> List[Dict]:
        """Parse the sidebar HTML and map its structure.

        Builds: List[Header] -> Header[Children] -> Child[Item | Menu] -> Menu[Children]
        Returns a list of dictionaries, each representing a top-level header group.
        
        Handles both hierarchical (4.x) and flat (3.x) endpoint structures.
        """
        if not sidebar_html:
            logging.error("Cannot map structure: sidebar HTML is empty.")
            return []

        logging.info("Parsing sidebar HTML structure (expecting expanded state)...")
        soup = BeautifulSoup(sidebar_html, "html.parser")
        structure_by_header: List[Dict[str, Any]] = []
        current_header_group: Optional[Dict[str, Any]] = None
        
        # Use dynamically detected structure type if available
        structure_type = getattr(self.selectors, 'CONTENT_STRUCTURE_TYPE', 'hierarchical_with_leading_header')
        
        # If structure type is unknown, try to auto-detect
        if structure_type == 'unknown':
            # Simple heuristic: check if we have headers and their position
            headers = soup.select("li.toc-item-divider")
            items_with_ids = soup.select("li.toc-item-highlight[id]")
            items_without_ids = soup.select("li.toc-item-highlight:not([id])")
            
            if len(items_without_ids) > len(items_with_ids) and len(headers) > 0:
                structure_type = "flat_with_trailing_header"
            else:
                structure_type = "hierarchical_with_leading_header"
            
            logging.info(f"Auto-detected structure type: {structure_type}")
        
        if structure_type == "flat_with_trailing_header":
            return self._parse_flat_structure_with_trailing_header(soup)
        else:
            return self._parse_hierarchical_structure(soup)

    def _parse_hierarchical_structure(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse hierarchical structure (4.x endpoints)."""
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
                    header_link = header_li.select_one(
                        self.selectors.HEADER_TEXT_ANCHOR[1])
                    header_text = "Unknown Header"
                    if header_link:
                        header_text = header_link.get_text(strip=True)
                    logging.debug(f"Found Header Group: {header_text}")
                    current_header_group = {"header_text": header_text, "children": []}
                    structure_by_header.append(current_header_group)
                    continue  # Move to the next element in sidebar_root_ul

                # If we haven't found a header yet, skip
                if not current_header_group:
                    logging.warning(
                        "Found sidebar item before finding the first header. Skipping.")
                    continue

                # 1b. Check for Clickable LI (Item or Menu) within app-item
                clickable_li = app_item.select_one(
                    self.selectors.SIDEBAR_CLICKABLE_LI[1])
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
                            logging.debug(
                                f" -> Found subsequent UL, parsing children for menu '{item_text}'...")
                            child_count = 0
                            child_selector = self.selectors.APP_API_DOC_ITEM[1]
                            for child_app_item in next_sibling.find_all(child_selector, recursive=False):
                                child_clickable_selector = self.selectors.SIDEBAR_CLICKABLE_LI[1]
                                child_li = child_app_item.select_one(
                                    child_clickable_selector)
                                if child_li:
                                    child_id = child_li.get("id")
                                    child_text_span_selector = self.selectors.ITEM_TEXT_SPAN[1]
                                    child_text_element = child_li.select_one(
                                        child_text_span_selector)
                                    child_text = "Unnamed Sub-Item"
                                    if child_text_element:
                                        child_text = child_text_element.get_text(
                                            strip=True)
                                        child_text = child_text.replace(
                                            "<!---->", "").strip()

                                    if child_text == "Overview":
                                        logging.debug(
                                            f"  -> Skipping 'Overview' sub-item (ID: {child_id})")
                                        continue

                                    if child_text and child_id:
                                        logging.debug(
                                            f"  -> Found Sub-Item: '{child_text}' (ID: {child_id})")
                                        children.append({
                                            "text": child_text,
                                            "id": child_id,
                                            "type": "item",
                                            "is_expandable": False,
                                        })
                                        child_count += 1
                                    else:
                                        logging.warning(
                                            f"  -> Found child LI but missing text or ID: {child_li.prettify()}")
                            logging.debug(
                                f" -> Parsed {child_count} children for menu '{item_text}' from subsequent UL.")

                    else:  # Not a menu, must be a simple item
                        item_type = "item"
                        text_span_selector = self.selectors.ITEM_TEXT_SPAN[1]
                        text_element = clickable_li.select_one(text_span_selector)
                        item_text = "Unnamed Item"
                        if text_element:
                            item_text = text_element.get_text(strip=True)
                            item_text = item_text.replace("<!---->", "").strip()
                        if not text_element:
                            logging.warning(
                                f"Classified as ITEM but couldn't find text span for LI ID {item_id}: {clickable_li.prettify()}")
                        item_id_str = item_id or "Missing"
                        logging.debug(f"Found Item: '{item_text}' (ID: {item_id_str})")

                    # Skip "Overview" items/menus at the top level too
                    if item_text == "Overview":
                        logging.debug(
                            f"Skipping top-level '{item_text}' {item_type} (ID: {item_id})")
                        continue

                    # Add the found item/menu. Check for text/type, ID is optional for menus.
                    if item_text and item_type:
                        # Log a warning if an ID is missing, especially for items
                        if not item_id:
                            if item_type == "item":
                                logging.warning(
                                    f"Found ITEM without ID, will be skipped during processing. Text='{item_text}'")
                            else:  # item_type == "menu"
                                logging.debug(
                                    f"Found MENU without ID. Will process children. Text='{item_text}'")

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
                        logging.warning(
                            f"Could not add entry: Missing text or type. Text='{item_text}', Type='{item_type}', ID={item_id}")

            # Case 2: It might be a plain UL (e.g., for menu children)
            elif element.name == "ul":
                logging.warning(
                    f"Found a top-level UL sibling to app-api-doc-item. This might be unexpected. Content: {element.prettify()[:100]}...")

        logging.info(
            f"Finished parsing hierarchical structure. Found {len(structure_by_header)} header groups.")
        return structure_by_header
    
    def _parse_flat_structure_with_trailing_header(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse flat structure with trailing header (3.x endpoints).
        
        In 3.x endpoints, items come first, then headers appear at the end.
        We need to collect all items first, then assign them to headers.
        """
        structure_by_header: List[Dict[str, Any]] = []
        
        # Find the main UL containing the app-api-doc-item elements
        ul_selector_1 = f"{self.selectors.SIDEBAR_CONTAINER[1]} > app-api-doc-sidebar > ul"
        ul_selector_2 = f"{self.selectors.SIDEBAR_CONTAINER[1]} > ul"
        sidebar_root_ul = soup.select_one(f"{ul_selector_1}, {ul_selector_2}")
        if not sidebar_root_ul:
            logging.error("Could not find the main UL element within the sidebar HTML.")
            return []
        
        # First pass: collect all headers and their positions
        headers_found = []
        items_before_header = []
        
        element_index = 0
        for element in sidebar_root_ul.children:
            if not isinstance(element, Tag):
                continue
                
            if element.name == self.selectors.APP_API_DOC_ITEM[1]:
                app_item = element
                
                # Check if this is a header
                header_li = app_item.select_one(self.selectors.SIDEBAR_HEADER_LI[1])
                if header_li:
                    header_link = header_li.select_one(self.selectors.HEADER_TEXT_ANCHOR[1])
                    header_text = "Unknown Header"
                    if header_link:
                        header_text = header_link.get_text(strip=True)
                    
                    logging.debug(f"Found Header Group: {header_text} at position {element_index}")
                    headers_found.append({
                        "header_text": header_text,
                        "position": element_index,
                        "children": []
                    })
                    continue
                
                # This is a regular item - parse it
                item_data = self._parse_item_from_app_item(app_item)
                if item_data:
                    items_before_header.append({
                        "data": item_data,
                        "position": element_index
                    })
            
            element_index += 1
        
        # Create a default header if no headers found, or use the first header found
        if not headers_found:
            # Create a default header for all items
            default_header = {
                "header_text": "API Documentation",
                "children": [item["data"] for item in items_before_header]
            }
            structure_by_header.append(default_header)
            logging.info(f"Created default header with {len(items_before_header)} items")
        else:
            # Use the first header found and assign all items to it
            # In 3.x, typically there's one main header that covers all items
            main_header = headers_found[0]
            main_header["children"] = [item["data"] for item in items_before_header]
            structure_by_header.append(main_header)
            logging.info(f"Assigned {len(items_before_header)} items to header '{main_header['header_text']}'")
        
        logging.info(
            f"Finished parsing flat structure. Found {len(structure_by_header)} header groups.")
        return structure_by_header
    
    def _parse_item_from_app_item(self, app_item: Tag) -> Optional[Dict[str, Any]]:
        """Parse a single item/menu from an app-api-doc-item element.
        
        Enhanced for PowerFlex API documentation structure where:
        - Individual clickable items have IDs (like 'docs-node-99134')
        - Expandable menu sections don't have IDs but contain chevron icons
        - Text extraction may vary between items and menus
        
        Args:
            app_item: BeautifulSoup Tag representing the app-api-doc-item
            
        Returns:
            Dictionary with item data or None if parsing failed
        """
        clickable_li = app_item.select_one(self.selectors.SIDEBAR_CLICKABLE_LI[1])
        if not clickable_li:
            return None
            
        item_id = clickable_li.get("id")
        item_type = "item"  # Default
        is_expandable = False
        children = []  # For menus
        
        # PowerFlex-specific logic: Items without IDs but with chevron icons are expandable menus
        has_chevron_right = bool(clickable_li.select_one("i.dds__icon--chevron-right"))
        has_chevron_down = bool(clickable_li.select_one("i.dds__icon--chevron-down"))
        has_expander_icon = has_chevron_right or has_chevron_down
        
        # Determine if this is a menu based on PowerFlex structure patterns
        is_menu = False
        if not item_id and has_expander_icon:
            # No ID but has chevron = expandable menu section
            is_menu = True
        elif has_expander_icon:
            # Has ID and chevron = might be an expandable item (treat as menu)
            is_menu = True
        
        # Enhanced text extraction for PowerFlex structure
        item_text = self._extract_item_text_powerflex(clickable_li, is_menu)
        
        if is_menu:
            item_type = "menu"
            is_expandable = True
            logging.debug(f"Found PowerFlex Menu: '{item_text}' (ID: {item_id or 'None'}, Chevron: {has_chevron_right or has_chevron_down})")
            
            # For PowerFlex, expanded menus might have visible children in the DOM
            # Try to parse any immediate children if they exist
            children = self._parse_powerflex_menu_children(app_item, clickable_li)
            
        else:
            # This is a regular clickable item
            item_type = "item"
            logging.debug(f"Found PowerFlex Item: '{item_text}' (ID: {item_id or 'None'})")
            
            # For PowerFlex endpoints, validate that items have meaningful IDs
            if not item_id and self._looks_like_api_endpoint(item_text):
                # Generate a synthetic ID based on the text
                item_id = f"synthetic-{item_text.lower().replace(' ', '-').replace('(', '').replace(')', '')}"
                logging.debug(f"Generated synthetic ID for API endpoint: {item_id}")
            elif not item_id:
                logging.warning(f"PowerFlex item without ID may not be processable: '{item_text}'")
        
        # Skip "Overview" items at top level
        if item_text == "Overview":
            logging.debug(f"Skipping '{item_text}' {item_type}")
            return None
        
        # Return the parsed item data
        if item_text and item_type:
            entry: Dict[str, Any] = {
                "text": item_text,
                "id": item_id,
                "type": item_type,
                "is_expandable": is_expandable,
            }
            if item_type == "menu":
                entry["children"] = children
            return entry
        
        return None
    
    def _looks_like_api_endpoint(self, text: str) -> bool:
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
    
    def _extract_item_text_powerflex(self, clickable_li: Tag, is_menu: bool) -> str:
        """Enhanced text extraction for PowerFlex API documentation structure.
        
        This method tries multiple strategies to extract text content from items and menus
        in the PowerFlex API docs, which may have varying HTML structures.
        
        Args:
            clickable_li: The clickable li element
            is_menu: Whether this element is identified as a menu
            
        Returns:
            Extracted text content
        """
        item_text = "Unknown Item"
        
        if is_menu:
            # For menus, try multiple selectors for text extraction
            text_selectors = [
                "div.align-middle.dds__text-truncate.dds__position-relative",  # Primary PowerFlex menu text
                "div.align-middle.dds__text-truncate",  # Alternative
                "div.align-middle",  # Broader fallback
                "span",  # Generic span
                "div",  # Any div as last resort
            ]
            
            for selector in text_selectors:
                text_element = clickable_li.select_one(selector)
                if text_element and text_element.get_text(strip=True):
                    item_text = text_element.get_text(strip=True)
                    item_text = item_text.replace("<!---->", "").strip()
                    if item_text and len(item_text) > 1:  # Valid non-empty text
                        break
        else:
            # For regular items, try the standard span selector first, then fallbacks
            text_selectors = [
                "span[id$='-sp']",  # PowerFlex item text spans
                "span",  # Any span
                "a",  # Anchor text
                "div",  # Any div
            ]
            
            for selector in text_selectors:
                text_element = clickable_li.select_one(selector)
                if text_element and text_element.get_text(strip=True):
                    item_text = text_element.get_text(strip=True)
                    item_text = item_text.replace("<!---->", "").strip()
                    if item_text and len(item_text) > 1:  # Valid non-empty text
                        break
        
        # Final cleanup and validation
        if not item_text or item_text in ["Unknown Item", "Unknown Menu"]:
            # Last resort: try to get any text content from the entire li
            all_text = clickable_li.get_text(strip=True)
            if all_text:
                # Clean up the text (remove extra whitespace, Angular artifacts)
                clean_text = " ".join(all_text.split())
                clean_text = clean_text.replace("<!---->", "").strip()
                if clean_text and len(clean_text) > 1:
                    item_text = clean_text[:100]  # Limit length
        
        return item_text if item_text else ("Unknown Menu" if is_menu else "Unknown Item")
    
    def _parse_powerflex_menu_children(self, app_item: Tag, menu_li: Tag) -> List[Dict[str, Any]]:
        """Parse children of an expanded PowerFlex menu.
        
        In PowerFlex API docs, when a menu is expanded, its children might be:
        1. In a subsequent UL sibling of the app_item
        2. Nested within the current app_item structure
        3. Not immediately visible (will be loaded when expanded)
        
        Args:
            app_item: The app-api-doc-item containing the menu
            menu_li: The li element representing the menu
            
        Returns:
            List of child item dictionaries
        """
        children = []
        
        try:
            # Strategy 1: Look for a subsequent UL sibling (common in hierarchical structures)
            next_sibling = app_item.find_next_sibling()
            if next_sibling and next_sibling.name == "ul":
                child_count = 0
                for child_app_item in next_sibling.find_all(self.selectors.APP_API_DOC_ITEM[1], recursive=False):
                    child_data = self._parse_item_from_app_item(child_app_item)
                    if child_data and child_data.get("text") != "Overview":
                        children.append(child_data)
                        child_count += 1
                
                if child_count > 0:
                    logging.debug(f"Found {child_count} children in subsequent UL for PowerFlex menu")
                    return children
            
            # Strategy 2: Look for nested structure within the current menu_li
            # This might happen if the menu is already expanded
            nested_items = menu_li.find_all("li", class_="toc-item-highlight", recursive=True)
            for nested_li in nested_items:
                # Skip the menu li itself
                if nested_li == menu_li:
                    continue
                
                # Check if this nested li has an ID (indicating it's a clickable item)
                if nested_li.get("id"):
                    child_text = self._extract_item_text_powerflex(nested_li, False)
                    if child_text and child_text != "Overview":
                        children.append({
                            "text": child_text,
                            "id": nested_li.get("id"),
                            "type": "item",
                            "is_expandable": False,
                        })
            
            if children:
                logging.debug(f"Found {len(children)} nested children for PowerFlex menu")
            
        except Exception as e:
            logging.debug(f"Error parsing PowerFlex menu children: {e}")
        
        return children

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
        logging.info(
            f"Flattened structure contains {len(flattened_list)} processable items.")
        return flattened_list

    def _flatten_recursive(
        self,
        item: Dict,
        result_list: List[Dict],
        header: Optional[str],
        menu: Optional[str],  # The immediate parent menu's text
        # The parent menu's text (could be same as menu)
        parent_menu_text: Optional[str],
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
        # Menus still need text and type
        elif item_type == "menu" and (not item_text or not item_type):
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
