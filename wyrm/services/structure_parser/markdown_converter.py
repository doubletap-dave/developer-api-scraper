"""Markdown conversion functionality for text extraction and formatting.

This module handles text extraction from HTML elements and formatting operations
for the structure parser package.
"""

import logging
from typing import Any, Dict, List, Optional

from bs4 import Tag

from ..selectors_service import SelectorsService


class MarkdownConverter:
    """Handles text extraction and formatting operations."""

    def __init__(self, selectors_service: Optional[SelectorsService] = None) -> None:
        """Initialize the markdown converter.

        Args:
            selectors_service: Optional configured selectors service
        """
        self.selectors = selectors_service or SelectorsService()

    def extract_item_text(self, clickable_li: Tag, is_menu: bool = False) -> str:
        """Extract text content from a clickable element.

        This method tries multiple strategies to extract text content from items and menus
        in API documentation, which may have varying HTML structures.

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
                self.selectors.EXPANDABLE_MENU_TEXT_DIV[1],  # Standard menu text
                "div.align-middle.dds__text-truncate.dds__position-relative",  # PowerFlex menu text
                "div.align-middle.dds__text-truncate",  # Alternative
                "div.align-middle",  # Broader fallback
                "span",  # Generic span
                "div",  # Any div as last resort
            ]

            for selector in text_selectors:
                text_element = clickable_li.select_one(selector)
                if text_element and text_element.get_text(strip=True):
                    item_text = self._clean_extracted_text(text_element.get_text(strip=True))
                    if item_text and len(item_text) > 1:  # Valid non-empty text
                        break
        else:
            # For regular items, try the standard span selector first, then fallbacks
            text_selectors = [
                self.selectors.ITEM_TEXT_SPAN[1],  # Standard item text
                "span[id$='-sp']",  # PowerFlex item text spans
                "span",  # Any span
                "a",  # Anchor text
                "div",  # Any div
            ]

            for selector in text_selectors:
                text_element = clickable_li.select_one(selector)
                if text_element and text_element.get_text(strip=True):
                    item_text = self._clean_extracted_text(text_element.get_text(strip=True))
                    if item_text and len(item_text) > 1:  # Valid non-empty text
                        break

        # Final cleanup and validation
        if not item_text or item_text in ["Unknown Item", "Unknown Menu"]:
            # Last resort: try to get any text content from the entire li
            all_text = clickable_li.get_text(strip=True)
            if all_text:
                # Clean up the text (remove extra whitespace, Angular artifacts)
                clean_text = self._clean_extracted_text(all_text)
                if clean_text and len(clean_text) > 1:
                    item_text = clean_text[:100]  # Limit length

        return item_text if item_text else ("Unknown Menu" if is_menu else "Unknown Item")

    def _clean_extracted_text(self, text: str) -> str:
        """Clean extracted text content.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text content
        """
        if not text:
            return text

        # Remove Angular artifacts and clean whitespace
        cleaned = text.replace("<!---->", "").strip()
        cleaned = " ".join(cleaned.split())  # Normalize whitespace
        
        return cleaned

    def format_item_entry(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format an item entry for flattened structure.

        Args:
            item_data: Raw item data dictionary

        Returns:
            Formatted item entry
        """
        formatted_entry = {
            "id": item_data.get("id"),
            "text": item_data.get("text", "").strip(),
            "type": item_data.get("type", "item"),
            "header": item_data.get("header"),
            "menu": item_data.get("menu"),
            "parent_menu_text": item_data.get("parent_menu_text"),
            "level": item_data.get("level", 0),
        }

        # Clean the text content
        if formatted_entry["text"]:
            formatted_entry["text"] = self._clean_extracted_text(formatted_entry["text"])

        return formatted_entry

    def should_skip_item(self, item_text: str, item_type: str = "item") -> bool:
        """Determine if an item should be skipped based on its text content.

        Args:
            item_text: The text content of the item
            item_type: The type of item ('item' or 'menu')

        Returns:
            True if the item should be skipped
        """
        # Skip "Overview" items at any level
        if item_text == "Overview":
            logging.debug(f"Skipping '{item_text}' {item_type}")
            return True

        # Skip items with no meaningful text
        if not item_text or item_text.strip() == "":
            logging.debug(f"Skipping empty {item_type}")
            return True

        # Skip items with placeholder text
        placeholder_texts = ["Unknown Item", "Unknown Menu", "Unnamed Item", "Unnamed Menu", "Unnamed Sub-Item"]
        if item_text in placeholder_texts:
            logging.debug(f"Skipping placeholder {item_type}: '{item_text}'")
            return True

        return False

    def validate_item_data(self, item_data: Dict[str, Any]) -> bool:
        """Validate that item data contains required fields.

        Args:
            item_data: Item data dictionary to validate

        Returns:
            True if item data is valid
        """
        item_id = item_data.get("id")
        item_text = item_data.get("text")
        item_type = item_data.get("type")

        # Skip non-menu items if they lack critical data (ID, text, type)
        # Allow menus through even with missing ID because we need to process children
        if item_type != "menu" and (not item_id or not item_text or not item_type):
            logging.warning(f"Invalid non-menu item due to missing data: {item_data}")
            return False
        
        # Menus still need text and type
        elif item_type == "menu" and (not item_text or not item_type):
            logging.warning(f"Invalid menu item due to missing text/type: {item_data}")
            return False

        return True

    def extract_child_text(self, child_element: Tag) -> str:
        """Extract text from a child element with fallback strategies.

        Args:
            child_element: The child element to extract text from

        Returns:
            Extracted text content
        """
        # Try standard child text extraction
        child_text_span_selector = self.selectors.ITEM_TEXT_SPAN[1]
        text_element = child_element.select_one(child_text_span_selector)
        
        if text_element and text_element.get_text(strip=True):
            return self._clean_extracted_text(text_element.get_text(strip=True))

        # Fallback to PowerFlex-style extraction
        return self.extract_item_text(child_element, is_menu=False)

    def create_child_entry(self, child_text: str, child_id: str) -> Dict[str, Any]:
        """Create a child entry dictionary.

        Args:
            child_text: Text content of the child
            child_id: ID of the child element

        Returns:
            Child entry dictionary
        """
        return {
            "text": self._clean_extracted_text(child_text),
            "id": child_id,
            "type": "item",
            "is_expandable": False,
        }
