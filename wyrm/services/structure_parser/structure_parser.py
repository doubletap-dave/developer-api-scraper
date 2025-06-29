"""Coordinator for structure parsing functionality.

This module manages the interaction between HTML cleaning, markdown conversion,
and link resolution components to provide the StructureParser.parse() API.
"""

import logging
from typing import Any, Dict, List, Optional

from .html_cleaner import HtmlCleaner
from .markdown_converter import MarkdownConverter
from .link_resolver import LinkResolver
from .hierarchical_parser import HierarchicalStructureParser

from ..selectors_service import SelectorsService

class StructureParser:
    """Handles structure parsing and component coordination."""

    def __init__(self, selectors_service: Optional[SelectorsService] = None) -> None:
        """Initialize the structure parser.

        Args:
            selectors_service: Optional configured selectors service
        """
        self.html_cleaner = HtmlCleaner(selectors_service)
        self.markdown_converter = MarkdownConverter(selectors_service)
        self.link_resolver = LinkResolver(selectors_service)
        self.hierarchical_parser = HierarchicalStructureParser(
            self.html_cleaner, self.markdown_converter, self.link_resolver
        )

    def parse(self, sidebar_html: str) -> List[Dict]:
        """Parse the sidebar HTML and map its structure.

        Args:
            sidebar_html: Raw HTML content of the sidebar

        Returns:
            Processed and structured data
        """
        soup = self.html_cleaner.parse_html(sidebar_html)
        if not soup:
            return []

        structure_type = self.html_cleaner.detect_structure_type(soup)
        sidebar_root = self.html_cleaner.find_sidebar_root(soup)
        if not sidebar_root:
            return []

        return self._delegate_parsing(sidebar_root, structure_type)

    def _delegate_parsing(self, sidebar_root: Any, structure_type: str) -> List[Dict]:
        """Delegates parsing based on the structure type."""
        if structure_type == "flat_with_trailing_header":
            return self._parse_flat_structure_with_trailing_header(sidebar_root)
        return self.hierarchical_parser.parse_hierarchical_structure(sidebar_root)


    def _parse_flat_structure_with_trailing_header(self, sidebar_root: Any) -> List[Dict]:
        """Parse flat structure with trailing header (3.x endpoints).

        In 3.x endpoints, items come first, then headers appear at the end.
        We need to collect all items first, then assign them to headers.
        """
        structure_by_header: List[Dict[str, Any]] = []

        # First pass: collect all headers and their positions
        headers_found: List[Dict[str, Any]] = []
        items_before_header: List[Dict[str, Any]] = []

        element_index = 0
        for element in sidebar_root.children:
            if not hasattr(element, 'name'):
                continue

            if element.name == "app-api-doc-item":
                app_item = element

                # Check if this is a header
                header_info = self.html_cleaner.extract_header_info(app_item)
                if header_info:
                    logging.debug(f"Found Header Group: {header_info['header_text']} at position {element_index}")
                    headers_found.append({
                        "header_text": header_info['header_text'],
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
            # Assign items to the found headers, matching their positions
            for header in headers_found:
                position = header["position"]
                
                # Gather all items before this header's position
                pertinent_items = [item["data"] for item in items_before_header if item["position"] < position]
                
                # Assign them to the current header
                header["children"].extend(pertinent_items)
                structure_by_header.append(header)
                
                # Remove those items so they aren't reassigned
                items_before_header = [item for item in items_before_header if item["position"] >= position]
            
            # If there are leftover items, assign them to the last header found
            if items_before_header and headers_found:
                last_header = headers_found[-1]
                last_header["children"].extend([item["data"] for item in items_before_header])
                logging.info(f"Assigned items to {len(headers_found)} headers")

        logging.info(
            f"Finished parsing flat structure. Found {len(structure_by_header)} header groups.")
        return structure_by_header

    def _parse_item_from_app_item(self, app_item: Any) -> Optional[Dict[str, Any]]:
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
        clickable_li = app_item.select_one("li.toc-item-highlight")
        if not clickable_li:
            return None

        item_id = self.link_resolver.extract_item_id(clickable_li)
        item_type = "item"  # Default
        is_expandable = False
        children = []  # For menus

        # Determine if this is a menu based on expandable elements
        is_menu = self.html_cleaner.is_expandable_element(clickable_li)

        # Enhanced text extraction
        item_text = self.markdown_converter.extract_item_text(clickable_li, is_menu)

        if is_menu:
            item_type = "menu"
            is_expandable = True
            logging.debug(f"Found PowerFlex Menu: '{item_text}' (ID: {item_id or 'None'})")

            # Parse any immediate children if they exist
            children = self._parse_powerflex_menu_children(app_item, clickable_li)

        else:
            # This is a regular clickable item
            item_type = "item"
            logging.debug(f"Found PowerFlex Item: '{item_text}' (ID: {item_id or 'None'})")

            # Resolve item ID (generate synthetic if needed)
            item_id = self.link_resolver.resolve_item_id(clickable_li, item_text)

        # Skip "Overview" items at top level
        if self.markdown_converter.should_skip_item(item_text, item_type):
            logging.debug(f"Skipping '{item_text}' {item_type}")
            return None

        # Validate item data
        item_data = {
            "text": item_text,
            "id": item_id,
            "type": item_type,
            "is_expandable": is_expandable,
        }
        if item_type == "menu":
            item_data["children"] = children

        if self.markdown_converter.validate_item_data(item_data):
            return item_data

        return None

    def _parse_powerflex_menu_children(self, app_item: Any, menu_li: Any) -> List[Dict[str, Any]]:
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
            children_ul = self.html_cleaner.find_menu_children(app_item)
            if children_ul:
                child_count = 0
                for child_app_item in children_ul.find_all("app-api-doc-item", recursive=False):
                    child_data = self._parse_item_from_app_item(child_app_item)
                    if child_data and not self.markdown_converter.should_skip_item(child_data.get("text", "")):
                        children.append(child_data)
                        child_count += 1

                if child_count > 0:
                    logging.debug(f"Found {child_count} children in subsequent UL for PowerFlex menu")
                    return children

            # Strategy 2: Look for nested structure within the current menu_li
            nested_items = self.html_cleaner.find_nested_items(menu_li)
            for nested_li in nested_items:
                child_text = self.markdown_converter.extract_child_text(nested_li)
                child_id = self.link_resolver.extract_item_id(nested_li)
                if child_text and not self.markdown_converter.should_skip_item(child_text):
                    child_id_str = child_id or "unknown"
                    child_entry = self.markdown_converter.create_child_entry(child_text, child_id_str)
                    children.append(child_entry)

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
        parent_menu_text: Optional[str],  # The parent menu's text (could be same as menu)
        level: int,
    ):
        """Recursive helper to flatten the structure."""
        # Validate and format the item
        if not self.markdown_converter.validate_item_data(item):
            return

        # Add the current item/menu itself to the list
        flat_entry = self.markdown_converter.format_item_entry({
            "id": item.get("id"),
            "text": item.get("text"),
            "type": item.get("type"),
            "header": header,
            "menu": menu,
            "parent_menu_text": parent_menu_text,
            "level": level,
        })
        result_list.append(flat_entry)

        # If it's a menu, recurse into its children
        if item.get("type") == "menu" and item.get("is_expandable"):
            # Children of this menu have the current menu's text as their 'menu'
            # and also as their parent_menu_text
            for child in item.get("children", []):
                self._flatten_recursive(
                    child,
                    result_list,
                    header=header,
                    menu=item.get("text"),  # Child belongs to this menu
                    parent_menu_text=item.get("text"),  # This menu is the parent
                    level=level + 1,
                )
