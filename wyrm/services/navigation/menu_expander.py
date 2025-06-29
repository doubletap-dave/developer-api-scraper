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
        """Handle menu expansion and item clicking for a specific item.

        Ensures that all ancestor menus in the path to the target item are expanded,
        including deeply nested hierarchies. This provides robust navigation when global
        expansion is skipped by discovering and expanding the full ancestor chain.

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

        logging.debug(f"Expanding menus for item '{item_text}' (level {level})")

        # For items at level > 1, we need to discover and expand the full ancestor chain
        # This handles deeply nested menu structures robustly
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

        # Fallback: expand parent menu first if different from direct menu
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

        Simple approach: find all collapsed menu icons and click them.
        No complex loops or timeouts needed.
        """
        logging.info("Starting menu expansion to reveal all items...")

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

        logging.info("Menu expansion completed")

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
