"""Menu scanner module for DOM traversal and element discovery.

This module handles discovering menu elements, ancestor menus, and traversing
the DOM structure to identify expandable menu sections.
"""

import logging
from typing import List, Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException


class MenuScanner:
    """Handles DOM traversal and element discovery for menu operations."""

    def __init__(self, driver: WebDriver) -> None:
        """Initialize the menu scanner.

        Args:
            driver: WebDriver instance
        """
        self.driver = driver

    async def discover_ancestor_menus(self, item_text: str, item_id: str) -> List[str]:
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
        ancestor_menus = []

        try:
            # Try to find the item in the DOM (it might be present but not visible)
            # We'll traverse up the DOM tree to find all ancestor menu containers

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
            is_expanded = False
            try:
                expanded_icon = WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, expanded_icon_xpath))
                )
                is_expanded = expanded_icon.is_displayed()
            except TimeoutException:
                pass

            # Find collapsed icon if not expanded
            collapsed_icon = None
            if not is_expanded:
                try:
                    collapsed_icon = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, collapsed_icon_xpath))
                    )
                except TimeoutException:
                    pass

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
        try:
            logging.info("Looking for standalone pages...")

            # Look for items that might be standalone pages but are currently hidden
            # We'll search for common patterns in page names
            standalone_patterns = [
                "Introduction", "Getting Started", "Overview", "Responses",
                "Authentication", "Authorization", "Error Codes", "Examples",
                "Volume Management", "Storage", "Host", "Protection", "Replication",
                "System", "User Management", "Monitoring", "Configuration",
                "API Reference", "Reference", "Guide", "Tutorial"
            ]

            # Check if any collapsed sections might contain these pages
            all_text_elements = self.driver.find_elements(
                "css selector",
                "li.toc-item-highlight div, li.toc-item-highlight span"
            )

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

            return list(potential_containers)

        except Exception as e:
            logging.debug(f"Error revealing standalone pages: {e}")
            return []
