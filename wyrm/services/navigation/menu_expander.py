"""Menu expansion module for Wyrm application.

This module handles expanding sidebar menus and waiting for UI elements.
"""

import asyncio
import logging
from typing import Dict

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..selectors_service import SelectorsService


class MenuExpander:
    """Handles menu expansion operations and UI waiting."""

    def __init__(self, driver: WebDriver) -> None:
        """Initialize the menu expander.

        Args:
            driver: WebDriver instance
        """
        self.driver = driver
        self.selectors = SelectorsService()

    async def expand_menu_for_item(self, item, config_values: Dict) -> None:
        """Handle menu expansion for a specific item in PowerFlex API docs.

        This method is optimized for the PowerFlex API documentation structure where:
        - Individual clickable items have IDs (like 'docs-node-99134')
        - Expandable menu sections don't have IDs but contain chevron icons
        - Menu hierarchy can be deeply nested

        Args:
            item: Item dictionary containing menu and ID information
            config_values: Configuration values for timeouts and delays
        """
        # Handle both SidebarItem models and dict items for backward compatibility
        if hasattr(item, 'id'):
            item_id = item.id
            item_text = item.text
            menu_text = item.menu
            parent_menu_text = item.parent_menu_text
            level = getattr(item, 'level', 0)
        else:
            item_id = item.get("id")
            item_text = item.get("text", "Unknown")
            menu_text = item.get("menu")
            parent_menu_text = item.get("parent_menu_text")
            level = item.get("level", 0)

        logging.debug(f"Expanding menus for PowerFlex item '{item_text}' (ID: {item_id}, level: {level})")

        # PowerFlex-specific approach: Use DOM traversal to find the exact path
        # to the target item and expand all necessary parent menus
        try:
            success = await self._expand_powerflex_path_to_item(item_id, item_text)
            if success:
                logging.debug(f"Successfully expanded path to item '{item_text}'")
                return
        except Exception as e:
            logging.warning(f"PowerFlex path expansion failed for '{item_text}': {e}")

        # Fallback to traditional menu expansion approach
        logging.debug(f"Using fallback menu expansion for '{item_text}'")
        
        # For items at level > 1, discover and expand the full ancestor chain
        if level > 1:
            ancestor_menus = await self._discover_ancestor_menus(item_text, item_id)
            for ancestor_menu in ancestor_menus:
                try:
                    logging.debug(f"Expanding ancestor menu: '{ancestor_menu}'")
                    await self._expand_specific_menu(
                        ancestor_menu,
                        timeout=config_values["navigation_timeout"],
                        expand_delay=config_values["expand_delay"],
                    )
                    await asyncio.sleep(0.3)
                except Exception as expand_err:
                    logging.warning(
                        f"Could not expand ancestor menu '{ancestor_menu}': {expand_err}")

        # Expand parent menu first if different from direct menu
        elif parent_menu_text and parent_menu_text != menu_text:
            logging.debug(f"Expanding parent menu '{parent_menu_text}' first")
            try:
                await self._expand_specific_menu(
                    parent_menu_text,
                    timeout=config_values["navigation_timeout"],
                    expand_delay=config_values["expand_delay"],
                )
                await asyncio.sleep(0.3)
            except Exception as expand_err:
                logging.warning(
                    f"Could not expand ancestor menu '{parent_menu_text}': {expand_err}")

        # Smart menu expansion for the direct parent menu
        if menu_text:
            logging.debug(
                f"Finding and expanding direct menu '{menu_text}' for node '{item_id}'")
            try:
                success = await self._expand_menu_containing_node(
                    menu_text,
                    item_id,
                    timeout=config_values["navigation_timeout"],
                    expand_delay=config_values["expand_delay"],
                )
                if success:
                    logging.debug(
                        f"Successfully expanded '{menu_text}' menu and verified item visibility")
                else:
                    logging.warning(
                        f"Could not find node '{item_id}' in '{menu_text}' menu after expansion")
                    # Fallback: try expanding without verification
                    await self._expand_specific_menu(
                        menu_text,
                        timeout=config_values["navigation_timeout"],
                        expand_delay=config_values["expand_delay"],
                    )
            except Exception as expand_err:
                logging.warning(
                    f"Error during menu expansion for '{menu_text}': {expand_err}")

    async def _discover_ancestor_menus(self, item_text: str, item_id: str) -> list:
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

    async def _expand_specific_menu(
        self, menu_text: str, timeout: int = 10, expand_delay: float = 0.2
    ):
        """Ensure a specific menu (identified by its visible text) is expanded."""
        if not menu_text:
            logging.warning("expand_specific_menu called with no menu_text. Skipping.")
            return

        clicked_successfully = False
        safe_menu_text = menu_text.replace('"', "'").replace("'", '"')
        logging.debug(f"Starting expansion for menu: '{safe_menu_text}'")

        # XPath to find the LI containing the specific text
        menu_li_xpath = (
            f"//li[contains(@class, 'toc-item') and "
            f".//div[normalize-space(.)='{safe_menu_text}']]"
        )
        collapsed_icon_xpath = f"{menu_li_xpath}//i[contains(@class, 'dds__icon--chevron-right')]"
        expanded_icon_xpath = f"{menu_li_xpath}//i[contains(@class, 'dds__icon--chevron-down')]"

        try:
            # Find the menu LI element
            logging.debug("Locating menu LI element using XPath...")
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, menu_li_xpath))
            )
            logging.debug(
                f"Found menu LI for '{safe_menu_text}'. Checking expansion state...")

            # Check if already expanded
            try:
                expanded_icon = WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, expanded_icon_xpath))
                )
                if expanded_icon.is_displayed():
                    logging.debug(f"Menu '{safe_menu_text}' already expanded.")
                    return
            except TimeoutException:
                logging.debug(
                    f"Expanded icon not found for '{safe_menu_text}'. Assuming collapsed.")

            # Find and click collapsed icon
            collapsed_icon = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, collapsed_icon_xpath))
            )

            # Menu expansion happening - logging reduced for cleaner progress display
            self.driver.execute_script(
                "arguments[0].scrollIntoView(false);", collapsed_icon)
            await asyncio.sleep(0.1)
            collapsed_icon.click()

            await self._wait_for_loader_to_disappear(timeout=timeout)
            await asyncio.sleep(expand_delay)
            # Menu expansion completed
            clicked_successfully = True

        except ElementClickInterceptedException:
            logging.warning(
                f"Click intercepted for menu '{safe_menu_text}'. Retrying...")
            await self._wait_for_loader_to_disappear(timeout=5)
            try:
                collapsed_icon = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, collapsed_icon_xpath))
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView(false);", collapsed_icon)
                await asyncio.sleep(0.1)
                self.driver.execute_script("arguments[0].click();", collapsed_icon)

                logging.info(
                    f"Successfully clicked expander for '{safe_menu_text}' after interception.")
                clicked_successfully = True
                await self._wait_for_loader_to_disappear(timeout=timeout)
                await asyncio.sleep(expand_delay)
            except Exception as retry_e:
                logging.error(
                    f"Failed to expand menu '{safe_menu_text}' even after retry: {retry_e}")

        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Could not find menu elements for '{safe_menu_text}': {e}")
        except Exception as e:
            logging.exception(
                f"Unexpected error expanding menu '{safe_menu_text}': {e}")

        # Verify expansion
        if clicked_successfully:
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.XPATH, expanded_icon_xpath))
                )
                logging.debug(f"Verified expansion of menu '{safe_menu_text}'")
            except TimeoutException:
                logging.warning(
                    f"Could not verify expansion of menu '{safe_menu_text}'")

    async def _expand_menu_containing_node(
        self, menu_text: str, target_node_id: str, timeout: int = 10, expand_delay: float = 0.2
    ) -> bool:
        """Expand a menu and verify it contains the target node."""
        if not menu_text or not target_node_id:
            return False

        try:
            await self._expand_specific_menu(menu_text, timeout, expand_delay)

            # Verify the target node is now visible
            try:
                target_element = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.ID, target_node_id))
                )
                return target_element.is_displayed()
            except TimeoutException:
                return False

        except Exception as e:
            logging.warning(f"Error expanding menu containing node: {e}")
            return False

    async def expand_all_menus_comprehensive(self, timeout: int = 60) -> None:
        """Expand all collapsible menus in the sidebar.

        Uses dynamic detection to choose the appropriate expansion strategy,
        with enhanced logic specifically for PowerFlex API documentation structure.
        """
        logging.info("Starting comprehensive menu expansion to reveal all items...")
        
        # Dynamically detect structure type and expansion needs
        if hasattr(self.selectors, 'detect_structure_type'):
            structure_type = self.selectors.detect_structure_type(self.driver)
        else:
            structure_type = "hierarchical_with_leading_header"
        
        needs_enhanced = getattr(self.selectors, 'needs_enhanced_expansion', lambda x: False)(self.driver)
        
        logging.info(f"Detected structure: {structure_type}, enhanced expansion needed: {needs_enhanced}")
        
        # Always use the PowerFlex-optimized expansion strategy
        await self._expand_menus_powerflex_optimized(timeout, structure_type)
        
        logging.info("Menu expansion completed")
    
    async def _expand_menus_standard(self, timeout: int) -> None:
        """Standard menu expansion for hierarchical endpoints."""
        try:
            # Find all collapsed menu icons
            collapsed_icons = self.driver.find_elements(*self.selectors.EXPANDER_ICON)

            if not collapsed_icons:
                logging.info("No collapsed menus found")
                return

            logging.info(f"Found {len(collapsed_icons)} collapsed menus to expand")

            # Click each collapsed icon
            expanded_count = 0
            for icon in collapsed_icons:
                try:
                    # Check if icon is still displayed
                    if not icon.is_displayed():
                        continue

                    # Scroll into view and click
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(false);", icon)
                    await asyncio.sleep(0.1)

                    try:
                        icon.click()
                        expanded_count += 1
                    except ElementClickInterceptedException:
                        # Try JavaScript click if regular click fails
                        self.driver.execute_script("arguments[0].click();", icon)
                        expanded_count += 1

                    # Brief pause between clicks
                    await asyncio.sleep(0.2)

                except Exception as e:
                    logging.debug(f"Failed to expand menu icon: {e}")
                    continue

            logging.info(f"Expanded {expanded_count} menus")

            # Wait for any loading to complete
            await self._wait_for_loader_to_disappear(timeout=5)

        except Exception as e:
            logging.error(f"Error during menu expansion: {e}")
    
    async def _expand_menus_3x_enhanced(self, timeout: int) -> None:
        """Enhanced menu expansion specifically for 3.x endpoints.
        
        3.x endpoints have a different menu structure where menus appear as clickable
        list items rather than icons, and may require different expansion approaches.
        """
        try:
            expanded_count = 0
            
            # Strategy 1: Try standard chevron icons first
            collapsed_icons = self.driver.find_elements(*self.selectors.EXPANDER_ICON)
            logging.info(f"Found {len(collapsed_icons)} collapsed chevron icons")
            
            for icon in collapsed_icons:
                try:
                    if not icon.is_displayed():
                        continue
                    
                    self.driver.execute_script("arguments[0].scrollIntoView(false);", icon)
                    await asyncio.sleep(0.1)
                    
                    try:
                        icon.click()
                        expanded_count += 1
                        await asyncio.sleep(0.3)  # Longer wait for 3.x
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", icon)
                        expanded_count += 1
                        await asyncio.sleep(0.3)
                        
                except Exception as e:
                    logging.debug(f"Failed to expand chevron icon: {e}")
                    continue
            
            # Strategy 2: For 3.x, also try clicking on expandable menu headers directly
            # Look for menu items that don't have IDs but are expandable
            menu_headers = self.driver.find_elements(
                "css selector", 
                "li.toc-item-highlight:not([id]) div.align-middle"
            )
            logging.info(f"Found {len(menu_headers)} potential expandable menu headers")
            
            for header in menu_headers:
                try:
                    if not header.is_displayed():
                        continue
                    
                    # Check if this looks like a menu that should be expanded
                    header_text = header.get_text(strip=True)
                    if not header_text or header_text in ['Overview', '']:
                        continue
                    
                    # Check if there's a chevron icon nearby indicating it's expandable
                    parent_li = header.find_element("xpath", "ancestor::li[1]")
                    chevron = None
                    try:
                        chevron = parent_li.find_element("css selector", "i.dds__icon--chevron-right")
                    except:
                        continue  # No chevron, probably not expandable
                    
                    if chevron and chevron.is_displayed():
                        logging.info(f"Attempting to expand menu: {header_text}")
                        self.driver.execute_script("arguments[0].scrollIntoView(false);", chevron)
                        await asyncio.sleep(0.1)
                        
                        try:
                            chevron.click()
                            expanded_count += 1
                            await asyncio.sleep(0.5)  # Wait for content to load
                            logging.info(f"Successfully expanded menu: {header_text}")
                        except ElementClickInterceptedException:
                            # Try clicking the header itself
                            try:
                                header.click()
                                expanded_count += 1
                                await asyncio.sleep(0.5)
                                logging.info(f"Successfully expanded menu via header: {header_text}")
                            except:
                                logging.debug(f"Failed to expand menu: {header_text}")
                        except Exception as e:
                            logging.debug(f"Failed to expand menu {header_text}: {e}")
                            
                except Exception as e:
                    logging.debug(f"Error processing menu header: {e}")
                    continue
            
            # Strategy 3: Try a more aggressive approach with JavaScript
            if expanded_count == 0:
                logging.info("No menus expanded with standard methods, trying JavaScript approach...")
                try:
                    js_expanded = self.driver.execute_script("""
                        var expandedCount = 0;
                        var chevrons = document.querySelectorAll('i.dds__icon--chevron-right');
                        for (var i = 0; i < chevrons.length; i++) {
                            try {
                                var chevron = chevrons[i];
                                if (chevron.offsetParent !== null) { // Check if visible
                                    chevron.click();
                                    expandedCount++;
                                }
                            } catch (e) {
                                console.log('Failed to click chevron: ' + e);
                            }
                        }
                        return expandedCount;
                    """)
                    expanded_count += js_expanded
                    logging.info(f"JavaScript approach expanded {js_expanded} additional menus")
                    
                    if js_expanded > 0:
                        await asyncio.sleep(2.0)  # Wait for all expansions to complete
                        
                except Exception as e:
                    logging.debug(f"JavaScript expansion failed: {e}")
            
            logging.info(f"Total expanded menus: {expanded_count}")
            
            # Wait for any loading to complete
            await self._wait_for_loader_to_disappear(timeout=10)  # Longer timeout for 3.x

        except Exception as e:
            logging.error(f"Error during enhanced menu expansion: {e}")
    
    async def _expand_menus_enhanced(self, timeout: int, structure_type: str) -> None:
        """Enhanced menu expansion for endpoints that need more comprehensive expansion.
        
        This method combines multiple strategies to ensure all expandable content is revealed,
        including standalone pages that aren't nested under traditional menus.
        """
        try:
            expanded_count = 0
            logging.info(f"Starting enhanced expansion for structure type: {structure_type}")
            
            # Strategy 1: Standard chevron icon clicking
            collapsed_icons = self.driver.find_elements(*self.selectors.EXPANDER_ICON)
            logging.info(f"Found {len(collapsed_icons)} collapsed chevron icons")
            
            for icon in collapsed_icons:
                try:
                    if not icon.is_displayed():
                        continue
                    
                    self.driver.execute_script("arguments[0].scrollIntoView(false);", icon)
                    await asyncio.sleep(0.1)
                    
                    try:
                        icon.click()
                        expanded_count += 1
                        await asyncio.sleep(0.3)
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", icon)
                        expanded_count += 1
                        await asyncio.sleep(0.3)
                        
                except Exception as e:
                    logging.debug(f"Failed to expand chevron icon: {e}")
                    continue
            
            # Strategy 2: Click on expandable menu headers without IDs
            # These are often the collapsed menus that contain the missing pages
            expandable_headers = self.driver.find_elements(
                "css selector", 
                "li.toc-item-highlight:not([id])"
            )
            logging.info(f"Found {len(expandable_headers)} potential expandable headers without IDs")
            
            # Debug: Log all the headers we found
            for i, header_li in enumerate(expandable_headers):
                try:
                    text_element = header_li.find_element("css selector", "div, span")
                    header_text = text_element.text.strip()
                    has_chevron = bool(header_li.find_elements("css selector", "i.dds__icon--chevron-right"))
                    logging.debug(f"Header {i+1}: '{header_text}' (has chevron: {has_chevron})")
                except Exception as e:
                    logging.debug(f"Header {i+1}: Could not get text - {e}")
            
            for header_li in expandable_headers:
                try:
                    if not header_li.is_displayed():
                        continue
                    
                    # Check if this LI has a chevron icon (indicating it's expandable)
                    chevron = None
                    try:
                        chevron = header_li.find_element("css selector", "i.dds__icon--chevron-right")
                    except:
                        continue  # No chevron, not expandable
                    
                    if chevron and chevron.is_displayed():
                        # Get the text to log what we're expanding
                        try:
                            text_element = header_li.find_element("css selector", "div, span")
                            header_text = text_element.text.strip()
                        except:
                            header_text = "Unknown Menu"
                        
                        logging.info(f"Expanding header without ID: {header_text}")
                        
                        self.driver.execute_script("arguments[0].scrollIntoView(false);", chevron)
                        await asyncio.sleep(0.1)
                        
                        try:
                            chevron.click()
                            expanded_count += 1
                            await asyncio.sleep(0.5)  # Wait for content to load
                            logging.info(f"Successfully expanded: {header_text}")
                        except ElementClickInterceptedException:
                            # Try clicking the header LI itself
                            try:
                                header_li.click()
                                expanded_count += 1
                                await asyncio.sleep(0.5)
                                logging.info(f"Successfully expanded via LI click: {header_text}")
                            except:
                                logging.debug(f"Failed to expand: {header_text}")
                        except Exception as e:
                            logging.debug(f"Failed to expand {header_text}: {e}")
                            
                except Exception as e:
                    logging.debug(f"Error processing expandable header: {e}")
                    continue
            
            # Strategy 3: Look for and reveal standalone pages
            # These are pages that exist at the top level but aren't under expandable menus
            await self._reveal_standalone_pages()
            
            # Strategy 4: JavaScript fallback for any remaining collapsed elements
            if expanded_count < 5:  # If we haven't expanded much, try harder
                logging.info("Attempting JavaScript fallback for remaining collapsed elements...")
                try:
                    js_expanded = self.driver.execute_script("""
                        var expandedCount = 0;
                        
                        // Try all types of potential expanders
                        var selectors = [
                            'i.dds__icon--chevron-right',
                            'li.toc-item-highlight:not([id])',
                            '[class*="chevron"][class*="right"]'
                        ];
                        
                        for (var s = 0; s < selectors.length; s++) {
                            var elements = document.querySelectorAll(selectors[s]);
                            for (var i = 0; i < elements.length; i++) {
                                try {
                                    var elem = elements[i];
                                    if (elem.offsetParent !== null) { // Check if visible
                                        elem.click();
                                        expandedCount++;
                                    }
                                } catch (e) {
                                    console.log('Failed to click element: ' + e);
                                }
                            }
                        }
                        return expandedCount;
                    """)
                    expanded_count += js_expanded
                    logging.info(f"JavaScript fallback expanded {js_expanded} additional elements")
                    
                    if js_expanded > 0:
                        await asyncio.sleep(2.0)  # Wait for all expansions to complete
                        
                except Exception as e:
                    logging.debug(f"JavaScript fallback failed: {e}")
            
            logging.info(f"Enhanced expansion completed. Total expanded: {expanded_count}")
            
            # Wait for any loading to complete
            await self._wait_for_loader_to_disappear(timeout=10)

        except Exception as e:
            logging.error(f"Error during enhanced menu expansion: {e}")
    
    async def _reveal_standalone_pages(self) -> None:
        """Look for and reveal standalone pages that aren't under expandable menus.
        
        These pages like 'Introduction to PowerFlex', 'Responses', 'Volume Management'
        may exist at the top level or be hidden in collapsed sections.
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
                            parent_li = element.find_element("xpath", "ancestor::li[contains(@class, 'toc-item-highlight')][1]")
                            potential_containers.add(parent_li)
                            logging.debug(f"Found potential standalone page container: {text}")
                            break
                except Exception:
                    continue
            
            # Try to expand any containers we found
            for container in potential_containers:
                try:
                    # Look for an expander in this container or its siblings
                    expanders = container.find_elements(
                        "css selector", 
                        "i.dds__icon--chevron-right, i[class*='chevron'][class*='right']"
                    )
                    
                    for expander in expanders:
                        if expander.is_displayed():
                            try:
                                expander.click()
                                await asyncio.sleep(0.5)
                                logging.info("Expanded container for potential standalone pages")
                                break
                            except Exception:
                                continue
                                
                except Exception:
                    continue
                    
        except Exception as e:
            logging.debug(f"Error revealing standalone pages: {e}")
    
    async def _expand_menus_powerflex_optimized(self, timeout: int, structure_type: str) -> None:
        """PowerFlex-optimized menu expansion based on the specific HTML structure.
        
        This method is specifically designed for the PowerFlex API documentation structure
        where individual items (with IDs) and expandable menus (without IDs) coexist.
        
        Args:
            timeout: Maximum time to wait for operations
            structure_type: Detected structure type for logging
        """
        try:
            expanded_count = 0
            logging.info(f"Starting PowerFlex-optimized expansion for structure: {structure_type}")
            
            # Phase 1: Identify and expand all expandable menu sections
            # These are li.toc-item-highlight elements without IDs that contain chevron icons
            expandable_sections = self.driver.find_elements(
                "css selector", 
                "li.toc-item-highlight:not([id]) i.dds__icon--chevron-right"
            )
            
            logging.info(f"Found {len(expandable_sections)} expandable menu sections")
            
            # Expand each section and wait for content to load
            for i, chevron_icon in enumerate(expandable_sections):
                try:
                    if not chevron_icon.is_displayed():
                        continue
                        
                    # Get the menu text for logging
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
                    
                    logging.info(f"Expanding section {i+1}/{len(expandable_sections)}: {menu_text}")
                    
                    # Scroll chevron into view
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", 
                        chevron_icon
                    )
                    await asyncio.sleep(0.2)
                    
                    # Click the chevron icon
                    try:
                        chevron_icon.click()
                        expanded_count += 1
                        logging.debug(f"Successfully expanded: {menu_text}")
                    except ElementClickInterceptedException:
                        # Fallback: JavaScript click
                        self.driver.execute_script("arguments[0].click();", chevron_icon)
                        expanded_count += 1
                        logging.debug(f"Expanded via JavaScript: {menu_text}")
                    
                    # Wait for the expansion to complete and content to load
                    await asyncio.sleep(0.5)
                    
                    # Wait for any loader overlays to disappear
                    await self._wait_for_loader_to_disappear(timeout=5)
                    
                except Exception as e:
                    logging.warning(f"Failed to expand section {i+1}: {e}")
                    continue
            
            # Phase 2: Recursive expansion check
            # After expanding top-level sections, check for newly revealed expandable items
            logging.info("Checking for newly revealed expandable items...")
            
            max_recursive_attempts = 3
            for attempt in range(max_recursive_attempts):
                new_expandables = self.driver.find_elements(
                    "css selector", 
                    "li.toc-item-highlight:not([id]) i.dds__icon--chevron-right"
                )
                
                # Filter out already processed elements
                unprocessed_expandables = []
                for expandable in new_expandables:
                    try:
                        # Check if this chevron is in a different position (newly revealed)
                        if expandable.is_displayed():
                            unprocessed_expandables.append(expandable)
                    except Exception:
                        continue
                
                if not unprocessed_expandables:
                    logging.debug(f"No new expandables found in attempt {attempt+1}")
                    break
                    
                logging.info(f"Found {len(unprocessed_expandables)} new expandables in attempt {attempt+1}")
                
                for chevron in unprocessed_expandables:
                    try:
                        if not chevron.is_displayed():
                            continue
                            
                        # Get menu text for logging
                        menu_text = "Nested Menu"
                        try:
                            parent_li = chevron.find_element(
                                "xpath", 
                                "ancestor::li[contains(@class, 'toc-item-highlight')][1]"
                            )
                            text_elem = parent_li.find_element(
                                "css selector", 
                                "div.align-middle, span, div"
                            )
                            if text_elem.text.strip():
                                menu_text = text_elem.text.strip()
                        except Exception:
                            pass
                        
                        logging.debug(f"Expanding nested: {menu_text}")
                        
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", 
                            chevron
                        )
                        await asyncio.sleep(0.1)
                        
                        try:
                            chevron.click()
                            expanded_count += 1
                        except ElementClickInterceptedException:
                            self.driver.execute_script("arguments[0].click();", chevron)
                            expanded_count += 1
                        
                        await asyncio.sleep(0.3)
                        
                    except Exception as e:
                        logging.debug(f"Failed to expand nested item: {e}")
                        continue
                
                # Brief pause between recursive attempts
                await asyncio.sleep(0.5)
            
            # Phase 3: Verify expansion and count items
            total_items = len(self.driver.find_elements(
                "css selector", 
                "li.toc-item-highlight[id]"
            ))
            
            total_menus = len(self.driver.find_elements(
                "css selector", 
                "li.toc-item-highlight:not([id])"
            ))
            
            remaining_collapsed = len(self.driver.find_elements(
                "css selector", 
                "li.toc-item-highlight i.dds__icon--chevron-right"
            ))
            
            logging.info(
                f"PowerFlex expansion completed: "
                f"expanded {expanded_count} sections, "
                f"found {total_items} clickable items, "
                f"{total_menus} total menu elements, "
                f"{remaining_collapsed} still collapsed"
            )
            
            # Phase 4: Final cleanup - wait for all loading to complete
            await self._wait_for_loader_to_disappear(timeout=10)
            await asyncio.sleep(1.0)  # Final stabilization wait
            
        except Exception as e:
            logging.error(f"Error during PowerFlex-optimized menu expansion: {e}")
            # Fallback to standard expansion if PowerFlex method fails
            logging.info("Falling back to standard expansion method")
            await self._expand_menus_standard(timeout)

    async def _wait_for_loader_to_disappear(self, timeout: int = 10):
        """Wait for the 'Processing, please wait...' overlay to disappear."""
        logging.debug(f"Waiting up to {timeout}s for loader overlay to disappear...")
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located(self.selectors.LOADER_OVERLAY)
            )
            logging.debug("Loader overlay is not visible.")
        except TimeoutException:
            logging.warning(
                f"Loader overlay did not disappear within {timeout} seconds.")
        except Exception as e:
            logging.exception(f"Unexpected error waiting for loader to disappear: {e}")
    
    async def _expand_powerflex_path_to_item(self, item_id: str, item_text: str) -> bool:
        """PowerFlex-specific method to expand the exact path to a target item.
        
        This method uses DOM traversal to find the target item and expand all
        necessary parent menus in the PowerFlex API documentation structure.
        
        Args:
            item_id: ID of the target item (e.g., 'docs-node-99134')
            item_text: Text content of the target item for fallback searching
            
        Returns:
            True if the path was successfully expanded, False otherwise
        """
        try:
            # Step 1: Try to find the target element by ID
            target_element = None
            try:
                target_element = self.driver.find_element("id", item_id)
                if target_element.is_displayed():
                    logging.debug(f"Target item '{item_text}' is already visible")
                    return True
            except NoSuchElementException:
                logging.debug(f"Target item '{item_text}' not found by ID, may be in collapsed menu")
            
            # Step 2: Use JavaScript to find all ancestor menus that need expansion
            js_script = """
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
                                element: chevronRight,
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
            
            # Execute the JavaScript to find the expansion path
            result = self.driver.execute_script(js_script, item_id, item_text)
            
            if not result['found']:
                logging.warning(f"Could not find target item '{item_text}' in DOM")
                return False
            
            if result.get('alreadyVisible', False):
                logging.debug(f"Target item '{item_text}' is already visible")
                return True
            
            expansions = result['expansions']
            if not expansions:
                logging.debug(f"No expansions needed for '{item_text}'")
                return True
            
            logging.info(f"Found {len(expansions)} menus to expand for '{item_text}'")
            
            # Step 3: Expand each menu in the path
            for i, expansion in enumerate(expansions):
                try:
                    menu_text = expansion['menuText']
                    logging.debug(f"Expanding menu {i+1}/{len(expansions)}: {menu_text}")
                    
                    # Find the chevron element using CSS selector (more reliable than XPath)
                    chevron_elements = self.driver.find_elements(
                        "css selector", 
                        "li.toc-item-highlight:not([id]) i.dds__icon--chevron-right"
                    )
                    
                    # Find the right chevron by checking the menu text
                    chevron_to_click = None
                    for chevron in chevron_elements:
                        try:
                            parent_li = chevron.find_element(
                                "xpath", 
                                "ancestor::li[contains(@class, 'toc-item-highlight')][1]"
                            )
                            text_div = parent_li.find_element(
                                "css selector", 
                                "div.align-middle.dds__text-truncate, div.align-middle, span"
                            )
                            if text_div.text.strip() == menu_text:
                                chevron_to_click = chevron
                                break
                        except Exception:
                            continue
                    
                    if not chevron_to_click:
                        logging.warning(f"Could not find chevron for menu: {menu_text}")
                        continue
                    
                    if not chevron_to_click.is_displayed():
                        logging.debug(f"Chevron for '{menu_text}' is not displayed, skipping")
                        continue
                    
                    # Scroll into view and click
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", 
                        chevron_to_click
                    )
                    await asyncio.sleep(0.2)
                    
                    try:
                        chevron_to_click.click()
                        logging.debug(f"Successfully expanded menu: {menu_text}")
                    except ElementClickInterceptedException:
                        # Fallback to JavaScript click
                        self.driver.execute_script("arguments[0].click();", chevron_to_click)
                        logging.debug(f"Expanded menu via JavaScript: {menu_text}")
                    
                    # Wait for expansion to complete
                    await asyncio.sleep(0.5)
                    await self._wait_for_loader_to_disappear(timeout=5)
                    
                except Exception as e:
                    logging.warning(f"Failed to expand menu in path: {e}")
                    continue
            
            # Step 4: Verify the target item is now visible
            try:
                target_element = self.driver.find_element("id", item_id)
                if target_element.is_displayed():
                    logging.debug(f"Successfully made target item '{item_text}' visible")
                    return True
                else:
                    logging.warning(f"Target item '{item_text}' found but not visible")
                    return False
            except NoSuchElementException:
                logging.warning(f"Target item '{item_text}' still not found after expansion")
                return False
            
        except Exception as e:
            logging.error(f"Error in PowerFlex path expansion for '{item_text}': {e}")
            return False
