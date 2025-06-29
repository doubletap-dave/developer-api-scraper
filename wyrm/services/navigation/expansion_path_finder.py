"""Expansion path finding for DOM traversal operations.

Handles finding the full chain of ancestor menus for deeply nested items
using JavaScript execution in the browser.
"""

import logging
from typing import List


class ExpansionPathFinder:
    """Finds expansion paths for nested menu items."""

    def __init__(self, driver):
        """Initialize expansion path finder.
        
        Args:
            driver: WebDriver instance for JavaScript execution
        """
        self.driver = driver

    def find_expansion_path(self, item_id: str, item_text: str) -> List[str]:
        """Find the full chain of ancestor menus for a deeply nested item.

        Args:
            item_id: ID of the target item
            item_text: Text of the target item

        Returns:
            List of ancestor menu texts in order from top-level to immediate parent
        """
        try:
            js_script = self._build_ancestor_traversal_script()
            ancestor_menus = self.driver.execute_script(js_script, item_id, item_text)

            self._log_expansion_path_results(item_text, ancestor_menus)
            return ancestor_menus or []

        except Exception as e:
            logging.warning(f"Error discovering ancestor menus for '{item_text}': {e}")
            return []

    def _build_ancestor_traversal_script(self) -> str:
        """Build JavaScript for traversing DOM to find ancestor menus."""
        return """
            function findAncestorMenus(targetId, targetText) {
                let targetElement = null;

                // Find target element by ID first, then by text content
                if (targetId) {
                    targetElement = document.getElementById(targetId);
                }

                if (!targetElement && targetText) {
                    // Find by text content in LI elements
                    const lis = document.querySelectorAll('li');
                    for (let li of lis) {
                        if (li.textContent && li.textContent.includes(targetText)) {
                            targetElement = li;
                            break;
                        }
                    }
                }

                if (!targetElement) {
                    return [];
                }

                const ancestors = [];
                let current = targetElement.parentElement;

                while (current && current !== document.body) {
                    // Look for ancestor LI elements that might be menus
                    if (current.tagName === 'LI' && current.classList.contains('toc-item')) {
                        // Check if this LI has an expander icon (indicating it's a menu)
                        const expanderIcon = current.querySelector('i[class*="chevron"]');
                        if (expanderIcon) {
                            // Find the menu text
                            const menuTextDiv = current.querySelector('div:first-child');
                            if (menuTextDiv && menuTextDiv.textContent) {
                                ancestors.unshift(menuTextDiv.textContent.trim());
                            }
                        }
                    }
                    current = current.parentElement;
                }

                return ancestors;
            }

            return findAncestorMenus(arguments[0], arguments[1]);
        """

    def _log_expansion_path_results(self, item_text: str, ancestor_menus: List[str]) -> None:
        """Log the results of expansion path discovery."""
        if ancestor_menus:
            logging.debug(f"Discovered ancestor menus for '{item_text}': {ancestor_menus}")
        else:
            logging.debug(f"No ancestor menus found for '{item_text}' in DOM")
