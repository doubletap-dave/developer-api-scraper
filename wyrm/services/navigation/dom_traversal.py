"""DOM traversal utilities for menu scanning operations.

This module provides utilities for traversing and analyzing DOM structures
specifically for menu expansion and element discovery operations.
"""

import logging
from typing import List, Dict, Any, Set
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class DOMTraversal:
    """Handles DOM traversal and element analysis for menu operations."""

    def __init__(self, driver: WebDriver) -> None:
        """Initialize the DOM traversal helper.

        Args:
            driver: WebDriver instance
        """
        self.driver = driver

    def find_expandable_sections(self) -> List[Dict[str, Any]]:
        """Find all expandable menu sections in the PowerFlex structure.

        Returns:
            List of dictionaries containing expandable section information
        """
        expandable_sections = []
        
        try:
            # Find all expandable sections using CSS selector
            sections = self.driver.find_elements(
                "css selector",
                "li.toc-item-highlight:not([id]) i.dds__icon--chevron-right"
            )

            for i, chevron_icon in enumerate(sections):
                try:
                    if not chevron_icon.is_displayed():
                        continue

                    # Get the menu text for this section
                    menu_text = self._extract_menu_text(chevron_icon)

                    expandable_sections.append({
                        "element": chevron_icon,
                        "menu_text": menu_text,
                        "index": i
                    })

                except Exception as e:
                    logging.debug(f"Error processing expandable section {i}: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error finding expandable sections: {e}")

        return expandable_sections

    def _extract_menu_text(self, chevron_icon) -> str:
        """Extract menu text from a chevron icon's parent element."""
        menu_text = "Unknown Menu"
        try:
            parent_li = chevron_icon.find_element(
                "xpath",
                "ancestor::li[contains(@class, 'toc-item-highlight')][1]"
            )
            text_elements = parent_li.find_elements(
                "css selector",
                "div.align-middle.dds__text-truncate, span, div"
            )
            for elem in text_elements:
                text = elem.text.strip()
                if text and len(text) > 1:
                    menu_text = text
                    break
        except Exception:
            pass
        return menu_text

    def find_menu_by_text(self, menu_text: str) -> Dict[str, Any]:
        """Find a specific menu element by its text content.

        Args:
            menu_text: Text content of the menu to find

        Returns:
            Dictionary containing menu element information or empty dict if not found
        """
        if not menu_text:
            return {}

        safe_menu_text = menu_text.replace('"', "'").replace("'", '"')
        
        # XPath to find the LI containing the specific text
        menu_li_xpath = (
            f"//li[contains(@class, 'toc-item') and "
            f".//div[normalize-space(.)='{safe_menu_text}']]"
        )
        collapsed_icon_xpath = f"{menu_li_xpath}//i[contains(@class, 'dds__icon--chevron-right')]"
        expanded_icon_xpath = f"{menu_li_xpath}//i[contains(@class, 'dds__icon--chevron-down')]"

        try:
            # Find the menu LI element
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, menu_li_xpath))
            )

            # Check if already expanded
            is_expanded = self._check_menu_expansion_state(expanded_icon_xpath)
            
            # Find collapsed icon if not expanded
            collapsed_icon = None
            if not is_expanded:
                collapsed_icon = self._find_collapsed_icon(collapsed_icon_xpath)

            return {
                "menu_text": safe_menu_text,
                "li_xpath": menu_li_xpath,
                "collapsed_icon": collapsed_icon,
                "is_expanded": is_expanded,
                "collapsed_icon_xpath": collapsed_icon_xpath,
                "expanded_icon_xpath": expanded_icon_xpath
            }

        except (TimeoutException, NoSuchElementException):
            logging.debug(f"Could not find menu elements for '{safe_menu_text}'")
            return {}

    def _check_menu_expansion_state(self, expanded_icon_xpath: str) -> bool:
        """Check if a menu is currently expanded."""
        try:
            expanded_icon = WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located((By.XPATH, expanded_icon_xpath))
            )
            return expanded_icon.is_displayed()
        except TimeoutException:
            return False

    def _find_collapsed_icon(self, collapsed_icon_xpath: str):
        """Find the collapsed icon for a menu."""
        try:
            return WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, collapsed_icon_xpath))
            )
        except TimeoutException:
            return None

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

    def find_expansion_path(self, item_id: str, item_text: str) -> List[str]:
        """Find the full chain of ancestor menus for a deeply nested item.

        Args:
            item_id: ID of the target item
            item_text: Text of the target item

        Returns:
            List of ancestor menu texts in order from top-level to immediate parent
        """
        ancestor_menus = []

        try:
            # JavaScript to traverse up and find ancestor menus
            js_script = """
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

            ancestor_menus = self.driver.execute_script(js_script, item_id, item_text)

            if ancestor_menus:
                logging.debug(
                    f"Discovered ancestor menus for '{item_text}': {ancestor_menus}")
            else:
                logging.debug(f"No ancestor menus found for '{item_text}' in DOM")

        except Exception as e:
            logging.warning(f"Error discovering ancestor menus for '{item_text}': {e}")

        return ancestor_menus or []
