"""Structure flattening utilities for StructureParser.

This module provides utilities for flattening nested structures into
processable lists while preserving hierarchy information.
"""

import logging
from typing import Dict, List, Optional


class StructureFlattener:
    """Handles flattening of nested structures into processable lists."""

    def __init__(self, markdown_converter):
        """Initialize with markdown converter dependency.

        Args:
            markdown_converter: MarkdownConverter instance for validation and formatting
        """
        self.markdown_converter = markdown_converter

    def flatten_sidebar_structure(self, structured_data: List[Dict]) -> List[Dict]:
        """Flatten the nested structure into a single list of items, preserving hierarchy info.

        Args:
            structured_data: List of header groups with nested children

        Returns:
            Flattened list of items with hierarchy information
        """
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
        """Recursive helper to flatten the structure.

        Args:
            item: Current item to process
            result_list: List to append flattened items to
            header: Header group this item belongs to
            menu: Immediate parent menu text
            parent_menu_text: Parent menu text (for nested menus)
            level: Nesting level (0 = top level)
        """
        # Validate and format the item
        if not self.markdown_converter.validate_item_data(item):
            return

        # Add the current item/menu itself to the list
        flat_entry = self._create_flat_entry(item, header, menu, parent_menu_text, level)
        result_list.append(flat_entry)

        # If it's a menu, recurse into its children
        if self._should_process_children(item):
            self._process_menu_children(
                item, result_list, header, level
            )

    def _create_flat_entry(
        self, item: Dict, header: Optional[str], menu: Optional[str],
        parent_menu_text: Optional[str], level: int
    ) -> Dict:
        """Create a flattened entry for an item.

        Args:
            item: Item to create entry for
            header: Header group
            menu: Menu this item belongs to
            parent_menu_text: Parent menu text
            level: Nesting level

        Returns:
            Formatted flat entry dictionary
        """
        entry_data = {
            "id": item.get("id"),
            "text": item.get("text"),
            "type": item.get("type"),
            "header": header,
            "menu": menu,
            "parent_menu_text": parent_menu_text,
            "level": level,
        }

        return self.markdown_converter.format_item_entry(entry_data)

    def _should_process_children(self, item: Dict) -> bool:
        """Check if an item's children should be processed.

        Args:
            item: Item to check

        Returns:
            True if children should be processed
        """
        return (item.get("type") == "menu" and
                item.get("is_expandable") and
                item.get("children"))

    def _process_menu_children(
        self, item: Dict, result_list: List[Dict], header: Optional[str], level: int
    ) -> None:
        """Process children of a menu item.

        Args:
            item: Menu item with children
            result_list: List to append children to
            header: Header group
            level: Current nesting level
        """
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
