"""Hierarchical structure parsing helper for StructureParser.

This module handles parsing of hierarchical API documentation structures (4.x endpoints)
where items are organized under header groups with nested menu/item relationships.
"""

import logging
from typing import Any, Dict, List, Optional

from .html_cleaner import HtmlCleaner
from .markdown_converter import MarkdownConverter
from .link_resolver import LinkResolver


class HierarchicalStructureParser:
    """Handles parsing of hierarchical documentation structures."""

    def __init__(self, html_cleaner: HtmlCleaner, markdown_converter: MarkdownConverter, 
                 link_resolver: LinkResolver) -> None:
        """Initialize with shared components."""
        self.html_cleaner = html_cleaner
        self.markdown_converter = markdown_converter
        self.link_resolver = link_resolver

    def parse_hierarchical_structure(self, sidebar_root: Any) -> List[Dict]:
        """Parse hierarchical structure (4.x endpoints)."""
        structure_by_header: List[Dict[str, Any]] = []
        current_header_group: Optional[Dict[str, Any]] = None

        # Iterate through the direct children of the main UL
        for element in sidebar_root.children:
            if not hasattr(element, 'name'):
                continue  # Skip NavigableStrings like newlines

            if element.name == "app-api-doc-item":
                current_header_group = self._process_app_item_hierarchical(
                    element, structure_by_header, current_header_group
                )
            elif element.name == "ul":
                self._handle_unexpected_ul(element)

        logging.info(
            f"Finished parsing hierarchical structure. Found {len(structure_by_header)} header groups.")
        return structure_by_header

    def _process_app_item_hierarchical(
        self, app_item: Any, structure_by_header: List[Dict], current_header_group: Optional[Dict]
    ) -> Optional[Dict]:
        """Process a single app-api-doc-item in hierarchical structure."""
        # Check for Header LI within app-item
        header_info = self.html_cleaner.extract_header_info(app_item)
        if header_info:
            logging.debug(f"Found Header Group: {header_info['header_text']}")
            new_header_group = {"header_text": header_info['header_text'], "children": []}
            structure_by_header.append(new_header_group)
            return new_header_group

        # If we haven't found a header yet, skip
        if not current_header_group:
            logging.warning("Found sidebar item before finding the first header. Skipping.")
            return current_header_group

        # Process clickable item or menu
        self._process_clickable_item_hierarchical(app_item, current_header_group)
        return current_header_group

    def _process_clickable_item_hierarchical(self, app_item: Any, current_header_group: Dict) -> None:
        """Process a clickable item or menu in hierarchical structure."""
        clickable_li = app_item.select_one("li.toc-item-highlight")
        if not clickable_li:
            return

        item_id = self.link_resolver.extract_item_id(clickable_li)
        is_menu = self.html_cleaner.is_expandable_element(clickable_li)
        
        if is_menu:
            entry = self._create_menu_entry_hierarchical(app_item, clickable_li, item_id)
        else:
            entry = self._create_item_entry_hierarchical(clickable_li, item_id)

        if entry and self._should_add_entry(entry):
            current_header_group["children"].append(entry)

    def _create_menu_entry_hierarchical(self, app_item: Any, clickable_li: Any, item_id: Any) -> Optional[Dict]:
        """Create a menu entry for hierarchical structure."""
        item_text = self.markdown_converter.extract_item_text(clickable_li, is_menu=True)
        item_id_str = item_id or "Missing"
        logging.debug(f"Found Menu: '{item_text}' (ID: {item_id_str})")

        children = self._parse_menu_children_hierarchical(app_item, item_text)
        
        return {
            "text": item_text,
            "id": item_id,
            "type": "menu",
            "is_expandable": True,
            "children": children
        }

    def _create_item_entry_hierarchical(self, clickable_li: Any, item_id: Any) -> Optional[Dict]:
        """Create an item entry for hierarchical structure."""
        item_text = self.markdown_converter.extract_item_text(clickable_li, is_menu=False)
        item_id_str = item_id or "Missing"
        logging.debug(f"Found Item: '{item_text}' (ID: {item_id_str})")

        return {
            "text": item_text,
            "id": item_id,
            "type": "item",
            "is_expandable": False
        }

    def _parse_menu_children_hierarchical(self, app_item: Any, menu_text: str) -> List[Dict]:
        """Parse children for a menu in hierarchical structure."""
        children = []
        children_ul = self.html_cleaner.find_menu_children(app_item)
        
        if not children_ul:
            return children

        logging.debug(f" -> Found subsequent UL, parsing children for menu '{menu_text}'...")
        child_count = 0
        
        for child_app_item in children_ul.find_all("app-api-doc-item", recursive=False):
            child_entry = self._process_child_item(child_app_item)
            if child_entry:
                children.append(child_entry)
                child_count += 1

        logging.debug(f" -> Parsed {child_count} children for menu '{menu_text}' from subsequent UL.")
        return children

    def _process_child_item(self, child_app_item: Any) -> Optional[Dict]:
        """Process a single child item."""
        child_clickable_li = child_app_item.select_one("li.toc-item-highlight")
        if not child_clickable_li:
            return None

        child_id = self.link_resolver.extract_item_id(child_clickable_li)
        child_text = self.markdown_converter.extract_child_text(child_clickable_li)

        if self.markdown_converter.should_skip_item(child_text):
            logging.debug(f"  -> Skipping 'Overview' sub-item (ID: {child_id})")
            return None

        if child_text and child_id:
            logging.debug(f"  -> Found Sub-Item: '{child_text}' (ID: {child_id})")
            return self.markdown_converter.create_child_entry(child_text, child_id)
        else:
            logging.warning(
                f"  -> Found child LI but missing text or ID: {child_clickable_li.prettify()}")
            return None

    def _should_add_entry(self, entry: Dict) -> bool:
        """Check if an entry should be added to the structure."""
        item_text = entry.get("text")
        item_type = entry.get("type")
        item_id = entry.get("id")

        # Skip "Overview" items/menus at the top level
        if self.markdown_converter.should_skip_item(item_text, item_type):
            logging.debug(f"Skipping top-level '{item_text}' {item_type} (ID: {item_id})")
            return False

        # Validate ID requirements
        if not self.link_resolver.validate_id_requirement(item_id, item_type, item_text):
            return False

        # Check for required fields
        if not item_text or not item_type:
            logging.warning(
                f"Could not add entry: Missing text or type. Text='{item_text}', Type='{item_type}', ID={item_id}")
            return False

        return True

    def _handle_unexpected_ul(self, element: Any) -> None:
        """Handle unexpected UL elements in hierarchical structure."""
        logging.warning(
            f"Found a top-level UL sibling to app-api-doc-item. This might be unexpected. "
            f"Content: {element.prettify()[:100]}...")
