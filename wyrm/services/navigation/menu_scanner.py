"""Menu scanner module for DOM traversal and element discovery.

This module handles discovering menu elements, ancestor menus, and traversing
the DOM structure to identify expandable menu sections.
"""

import logging
from typing import List, Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver
from .dom_traversal import DOMTraversal


class MenuScanner:
    """Handles DOM traversal and element discovery for menu operations."""

    def __init__(self, driver: WebDriver) -> None:
        """Initialize the menu scanner.

        Args:
            driver: WebDriver instance
        """
        self.driver = driver
        self.dom_traversal = DOMTraversal(driver)

    def discover_ancestor_menus(self, item_text: str, item_id: str) -> List[str]:
        """Discover the full chain of ancestor menus for a deeply nested item.

        This method uses DOM traversal to find all ancestor menus that need to be
        expanded to make the target item visible. It's particularly useful when
        global expansion is skipped and we need to expand only the necessary path.

        Args:
            item_text: Text of the target item
            item_id: ID of the target item

        Returns:
            List of ancestor menu texts in order from top-level to immediate parent
        """
        return self.dom_traversal.find_expansion_path(item_id, item_text)

    def find_expandable_sections(self) -> List[Dict[str, Any]]:
        """Find all expandable menu sections in the PowerFlex structure.

        Returns:
            List of dictionaries containing expandable section information
        """
        return self.dom_traversal.find_expandable_sections()

    def find_menu_by_text(self, menu_text: str) -> Dict[str, Any]:
        """Find a specific menu element by its text content.

        Args:
            menu_text: Text content of the menu to find

        Returns:
            Dictionary containing menu element information or empty dict if not found
        """
        return self.dom_traversal.find_menu_by_text(menu_text)

    def find_powerflex_expansion_path(self, item_id: str, item_text: str) -> Dict[str, Any]:
        """Find the expansion path for a PowerFlex item using DOM traversal.

        Args:
            item_id: ID of the target item
            item_text: Text content of the target item

        Returns:
            Dictionary containing expansion path information
        """
        try:
            js_script = self._get_powerflex_expansion_script()
            return self.driver.execute_script(js_script, item_id, item_text)
        except Exception as e:
            logging.error(f"Error finding PowerFlex expansion path for '{item_text}': {e}")
            return {"found": False, "expansions": []}

    def _get_powerflex_expansion_script(self) -> str:
        """Generate JavaScript for PowerFlex expansion path detection."""
        return """
            // PowerFlex-specific DOM traversal to find expansion path
            function findExpansionPath(targetId, targetText) {
                var expansionsNeeded = [];
                var targetFound = false;

                // First, try to find by ID
                var targetElement = document.getElementById(targetId);

                // If not found by ID, search by text content in li elements
                if (!targetElement) {
                    var allLis = document.querySelectorAll('li.toc-item-highlight[id]');
                    for (var i = 0; i < allLis.length; i++) {
                        var li = allLis[i];
                        if (li.textContent && li.textContent.trim().indexOf(targetText) !== -1) {
                            targetElement = li;
                            break;
                        }
                    }
                }

                if (!targetElement) {
                    return { found: false, expansions: [] };
                }

                // Check if already visible
                if (targetElement.offsetParent !== null) {
                    return { found: true, expansions: [], alreadyVisible: true };
                }

                // Traverse up the DOM tree to find collapsed ancestor menus
                var current = targetElement.parentElement;
                while (current && current !== document.body) {
                    // Look for li elements that don't have IDs (these are expandable menus)
                    if (current.tagName === 'LI' &&
                        current.classList.contains('toc-item-highlight') &&
                        !current.hasAttribute('id')) {

                        // Check if this menu is collapsed (has right chevron)
                        var chevronRight = current.querySelector('i.dds__icon--chevron-right');
                        if (chevronRight && chevronRight.offsetParent !== null) {
                            // This menu needs to be expanded
                            var menuText = 'Unknown Menu';
                            var textDiv = current.querySelector('div.align-middle.dds__text-truncate');
                            if (textDiv && textDiv.textContent) {
                                menuText = textDiv.textContent.trim();
                            }

                            expansionsNeeded.unshift({ // Add to beginning (top-level first)
                                menuText: menuText,
                                xpath: getXPathForElement(chevronRight)
                            });
                        }
                    }
                    current = current.parentElement;
                }

                return { found: true, expansions: expansionsNeeded, alreadyVisible: false };
            }

            function getXPathForElement(element) {
                var xpath = '';
                var current = element;
                while (current && current.tagName) {
                    var tagName = current.tagName.toLowerCase();
                    var sibling = current.previousElementSibling;
                    var index = 1;
                    while (sibling) {
                        if (sibling.tagName && sibling.tagName.toLowerCase() === tagName) {
                            index++;
                        }
                        sibling = sibling.previousElementSibling;
                    }
                    xpath = '/' + tagName + '[' + index + ']' + xpath;
                    current = current.parentElement;
                }
                return xpath;
            }

            return findExpansionPath(arguments[0], arguments[1]);
        """

    def reveal_standalone_pages(self) -> List[Dict[str, Any]]:
        """Look for and identify standalone pages that aren't under expandable menus.

        These pages like 'Introduction to PowerFlex', 'Responses', 'Volume Management'
        may exist at the top level or be hidden in collapsed sections.

        Returns:
            List of potential containers that might contain standalone pages
        """
        return self.dom_traversal.reveal_standalone_pages()
