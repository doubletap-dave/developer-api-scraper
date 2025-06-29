"""Standalone page detection for DOM traversal operations.

Handles detection of standalone pages that aren't under expandable menus,
such as Introduction pages, Getting Started guides, etc.
"""

import logging
from typing import Any, Dict, List, Set


class StandalonePageDetector:
    """Detects standalone pages in sidebar navigation."""

    def __init__(self, driver):
        """Initialize standalone page detector.
        
        Args:
            driver: WebDriver instance for element detection
        """
        self.driver = driver

    def reveal_standalone_pages(self) -> List[Dict[str, Any]]:
        """Look for and identify standalone pages that aren't under expandable menus.

        These pages like 'Introduction to PowerFlex', 'Responses', 'Volume Management'
        may exist at the top level or be hidden in collapsed sections.

        Returns:
            List of potential containers that might contain standalone pages
        """
        try:
            logging.info("Looking for standalone pages...")

            # Look for items that might be standalone pages but are currently hidden
            standalone_patterns = self._get_standalone_patterns()

            # Check if any collapsed sections might contain these pages
            all_text_elements = self.driver.find_elements(
                "css selector",
                "li.toc-item-highlight div, li.toc-item-highlight span"
            )

            potential_containers = self._find_potential_containers(
                all_text_elements, standalone_patterns
            )

            return list(potential_containers)

        except Exception as e:
            logging.debug(f"Error revealing standalone pages: {e}")
            return []

    def _get_standalone_patterns(self) -> List[str]:
        """Get patterns for standalone page detection."""
        return [
            "Introduction", "Getting Started", "Overview", "Responses",
            "Authentication", "Authorization", "Error Codes", "Examples",
            "Volume Management", "Storage", "Host", "Protection", "Replication",
            "System", "User Management", "Monitoring", "Configuration",
            "API Reference", "Reference", "Guide", "Tutorial"
        ]

    def _find_potential_containers(self, all_text_elements, standalone_patterns) -> Set:
        """Find potential containers for standalone pages."""
        potential_containers = set()
        for element in all_text_elements:
            try:
                text = element.text.strip()
                for pattern in standalone_patterns:
                    if pattern.lower() in text.lower():
                        # Find the parent LI that might need expansion
                        parent_li = element.find_element(
                            "xpath",
                            "ancestor::li[contains(@class, 'toc-item-highlight')][1]"
                        )
                        potential_containers.add(parent_li)
                        logging.debug(f"Found potential standalone page container: {text}")
                        break
            except Exception:
                continue
        return potential_containers
