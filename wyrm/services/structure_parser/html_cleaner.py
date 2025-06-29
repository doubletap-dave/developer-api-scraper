"""HTML cleaning functionality for sidebar HTML processing.

This module handles HTML parsing, BeautifulSoup operations, and HTML content cleaning
for the structure parser package.
"""

import logging
from typing import Any, Dict, List, Optional, cast

from bs4 import BeautifulSoup, Tag

from ..selectors_service import SelectorsService


class HtmlCleaner:
    """Handles HTML parsing and cleaning operations."""

    def __init__(self, selectors_service: Optional[SelectorsService] = None) -> None:
        """Initialize the HTML cleaner.

        Args:
            selectors_service: Optional configured selectors service
        """
        self.selectors = selectors_service or SelectorsService()

    def parse_html(self, sidebar_html: str) -> Optional[BeautifulSoup]:
        """Parse the sidebar HTML into a BeautifulSoup object.

        Args:
            sidebar_html: Raw HTML content to parse

        Returns:
            BeautifulSoup object or None if parsing fails
        """
        if not sidebar_html:
            logging.error("Cannot parse HTML: sidebar HTML is empty.")
            return None

        logging.info("Parsing sidebar HTML structure (expecting expanded state)...")
        return BeautifulSoup(sidebar_html, "html.parser")

    def find_sidebar_root(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the main UL element containing the app-api-doc-item elements.

        Args:
            soup: BeautifulSoup object to search in

        Returns:
            The root UL element or None if not found
        """
        ul_selector_1 = f"{self.selectors.SIDEBAR_CONTAINER[1]} > app-api-doc-sidebar > ul"
        ul_selector_2 = f"{self.selectors.SIDEBAR_CONTAINER[1]} > ul"
        sidebar_root_ul = soup.select_one(f"{ul_selector_1}, {ul_selector_2}")
        
        if not sidebar_root_ul:
            logging.error("Could not find the main UL element within the sidebar HTML.")
            return None
            
        return sidebar_root_ul

    def detect_structure_type(self, soup: BeautifulSoup) -> str:
        """Auto-detect the structure type of the sidebar HTML.

        Args:
            soup: BeautifulSoup object to analyze

        Returns:
            Structure type string ('hierarchical_with_leading_header', 'flat_with_trailing_header', or 'unknown')
        """
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

        return structure_type

    def clean_text_content(self, text: str) -> str:
        """Clean text content by removing Angular artifacts and extra whitespace.

        Args:
            text: Raw text content to clean

        Returns:
            Cleaned text content
        """
        if not text:
            return text

        # Remove Angular artifacts and clean whitespace
        cleaned = text.replace("<!---->", "").strip()
        cleaned = " ".join(cleaned.split())  # Normalize whitespace
        
        return cleaned

    def extract_header_info(self, app_item: Tag) -> Optional[Dict[str, str]]:
        """Extract header information from an app-api-doc-item element.

        Args:
            app_item: BeautifulSoup Tag representing the app-api-doc-item

        Returns:
            Dictionary with header information or None if not a header
        """
        header_li = app_item.select_one(self.selectors.SIDEBAR_HEADER_LI[1])
        if not header_li:
            return None

        header_link = header_li.select_one(self.selectors.HEADER_TEXT_ANCHOR[1])
        header_text = "Unknown Header"
        if header_link:
            header_text = self.clean_text_content(header_link.get_text(strip=True))

        return {"header_text": header_text}

    def is_expandable_element(self, clickable_li: Tag) -> bool:
        """Check if a clickable element is expandable (has expander icons).

        Args:
            clickable_li: The clickable li element to check

        Returns:
            True if the element is expandable
        """
        # Check for standard expander icons
        has_standard_expander = bool(
            clickable_li.select_one(self.selectors.EXPANDER_ICON[1])
            or clickable_li.select_one(self.selectors.EXPANDED_ICON[1])
        )

        # Check for PowerFlex-specific chevron icons
        has_chevron_right = bool(clickable_li.select_one("i.dds__icon--chevron-right"))
        has_chevron_down = bool(clickable_li.select_one("i.dds__icon--chevron-down"))

        return has_standard_expander or has_chevron_right or has_chevron_down

    def find_menu_children(self, app_item: Tag) -> Optional[Tag]:
        """Find the UL element containing children of a menu.

        Args:
            app_item: The app-api-doc-item containing the menu

        Returns:
            The UL element with children or None if not found
        """
        # Check for children in the next sibling UL
        next_sibling = app_item.find_next_sibling()
        if next_sibling and hasattr(next_sibling, 'name') and next_sibling.name == "ul":
            return cast(Tag, next_sibling)
        return None

    def find_nested_items(self, menu_li: Tag) -> List[Tag]:
        """Find nested items within a menu element.

        Args:
            menu_li: The menu li element to search in

        Returns:
            List of nested li elements with IDs
        """
        nested_items = menu_li.find_all("li", class_="toc-item-highlight", recursive=True)
        result = []
        
        for nested_li in nested_items:
            # Skip the menu li itself
            if nested_li == menu_li:
                continue
            
            # Check if this nested li has an ID (indicating it's a clickable item)
            if nested_li.get("id"):
                result.append(nested_li)
        
        return result
