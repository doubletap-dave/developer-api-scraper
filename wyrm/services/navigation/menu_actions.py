"""Menu actions module for click and expand behaviors.

This module handles clicking actions, menu expansions, and verifying expansion states.
"""

import logging
from typing import Dict
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
import asyncio

class MenuActions:
    """Handles click and expand operations for menu elements."""

    def __init__(self, driver: WebDriver) -> None:
        """Initialize the menu actions handler.

        Args:
            driver: WebDriver instance
        """
        self.driver = driver

    async def expand_specific_menu(self, menu_info: Dict, timeout: int = 10, expand_delay: float = 0.2) -> bool:
        """Ensure a specific menu (identified by its visible text) is expanded.

        Args:
            menu_info: Dictionary containing menu text and XPath details
            timeout: Maximum time to wait for menu expansion
            expand_delay: Delay time after expansion

        Returns:
            True if menu expanded, False otherwise
        """
        if not menu_info.get("menu_text"):
            logging.warning("expand_specific_menu called with no menu_text. Skipping.")
            return False

        safe_menu_text = menu_info["menu_text"]
        logging.debug(f"Starting expansion for menu: '{safe_menu_text}'")

        try:
            # Find the menu LI element
            logging.debug("Locating menu LI element using XPath...")
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, menu_info["li_xpath"]))
            )
            logging.debug(
                f"Found menu LI for '{safe_menu_text}'. Checking expansion state...")

            # Check if already expanded
            if menu_info.get("is_expanded"):
                logging.debug(f"Menu '{safe_menu_text}' already expanded.")
                return True

            # Find and click collapsed icon
            collapsed_icon = menu_info.get("collapsed_icon")
            if collapsed_icon:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView(false);", collapsed_icon)
                await asyncio.sleep(0.1)
                collapsed_icon.click()

                await self.wait_for_loader_to_disappear(timeout=timeout)
                await asyncio.sleep(expand_delay)
                # Menu expansion completed
                return True
        except (ElementClickInterceptedException, TimeoutException) as e:
            logging.warning(f"Error during menu expansion for '{safe_menu_text}': {e}")

        return False

    async def click_expander_and_verify(self, expander_icon, menu_text, timeout, expand_delay):
        """Handle clicking an expander icon and verify the menu expansion.

        Args:
            expander_icon: The expander icon WebElement
            menu_text: Text of the menu
            timeout: Maximum time to wait for operation
            expand_delay: Delay time after click
        """
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(false);", expander_icon)
            await asyncio.sleep(0.1)
            expander_icon.click()

            logging.info(f"Clicked expander for '{menu_text}'. Verifying expansion...")
            await asyncio.sleep(expand_delay)
            await self.wait_for_loader_to_disappear(timeout=timeout)

        except ElementClickInterceptedException:
            logging.warning(
                f"Click intercepted for expander '{menu_text}'. Retrying...")
            await self.retry_click_expander(expander_icon, menu_text, timeout, expand_delay)

    async def retry_click_expander(self, expander_icon, menu_text, timeout, expand_delay):
        """Retry clicking an expander if the first attempt is intercepted.

        Args:
            expander_icon: The expander icon WebElement
            menu_text: Text of the menu
            timeout: Maximum time to wait for operation
            expand_delay: Delay time after retry
        """
        await asyncio.sleep(0.5)
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(false);", expander_icon)
            await asyncio.sleep(0.1)
            self.driver.execute_script("arguments[0].click();", expander_icon)
            logging.info(f"Successfully retried expander click for '{menu_text}'.")
            await asyncio.sleep(expand_delay)
        except Exception as e:
            logging.error(f"Retry click failed for '{menu_text}': {e}")

    async def wait_for_loader_to_disappear(self, timeout: int = 10):
        """Wait for the loader overlay to disappear.

        Args:
            timeout: Maximum time to wait for loader to disappear
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.loader-overlay"))
            )
        except TimeoutException:
            logging.warning(f"Loader overlay did not disappear within {timeout} seconds.")

    async def expand_menu_containing_node(self, menu_info: Dict, target_node_id: str, timeout: int = 10, expand_delay: float = 0.2) -> bool:
        """Expand a menu and verify it contains the target node.

        Args:
            menu_info: Dictionary containing menu details
            target_node_id: ID of the target node element
            timeout: Maximum time to wait for expansion
            expand_delay: Delay time after operation

        Returns:
            True if the target node is found and visible, False otherwise
        """
        await self.expand_specific_menu(menu_info, timeout, expand_delay)

        try:
            target_element = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.ID, target_node_id))
            )
            return target_element.is_displayed()
        except TimeoutException:
            return False

    async def expand_all_menus_comprehensive(self, menu_scanner, timeout: int = 60) -> None:
        """Expand all collapsible menus in the sidebar comprehensively.

        Args:
            menu_scanner: Instance of MenuScanner to find expandable sections
            timeout: Maximum time to wait for all expansions
        """
        logging.info("Starting comprehensive menu expansion to reveal all items...")

        expandable_sections = menu_scanner.find_expandable_sections()
        logging.info(f"Found {len(expandable_sections)} expandable sections.")

        for section in expandable_sections:
            try:
                await self.click_expander_and_verify(section["element"], section["menu_text"], timeout, 0.3)
            except Exception as e:
                logging.warning(f"Failed to expand section {section['menu_text']}: {e}")

        logging.info("Menu expansion completed.")
        await asyncio.sleep(1.0)  # Allow time for any final expansions to complete
    
    async def reveal_standalone_pages(self, standalone_containers, timeout: int = 10):
        """Attempt to reveal standalone pages that may be hidden.

        Args:
            standalone_containers: List of containers containing standalone pages
            timeout: Maximum time to wait for operation
        """
        for container in standalone_containers:
            try:
                expanders = container.find_elements(
                    "css selector",
                    "i.dds__icon--chevron-right, i[class*='chevron'][class*='right']"
                )
        
                for expander in expanders:
                    if expander.is_displayed():
                        try:
                            await self.click_expander_and_verify(expander, "standalone page", timeout, 0.5)
                            logging.info("Expanded container for standalone pages.")
                            break
                        except Exception:
                            continue
        
            except Exception as e:
                logging.debug(f"Error expanding standalone page container: {e}")
                continue

        await asyncio.sleep(2.0)

    async def expand_powerflex_path_to_item(self, expansion_data: Dict, timeout: int = 10):
        """Expand PowerFlex menus to reveal a specific item.

        Args:
            expansion_data: Dictionary containing expansion path information
            timeout: Maximum time to wait for operation
        """
        expansions = expansion_data["expansions"]
        for expansion in expansions:
            menu_text = expansion["menuText"]
            xpath = expansion["xpath"]
            logging.debug(f"Expanding menu with text '{menu_text}'.")
            chevron_to_click = self.driver.find_element_by_xpath(xpath)
            await self.click_expander_and_verify(chevron_to_click, menu_text, timeout, 0.5)

        await asyncio.sleep(1.0)  # Allow time for all expansions before proceeding

