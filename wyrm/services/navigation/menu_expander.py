"""Menu expansion module for Wyrm application.

This module handles expanding sidebar menus and waiting for UI elements.
"""

import asyncio
import logging
from typing import Dict, Optional

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

    async def expand_menu_for_item(self, item: Dict, config_values: Dict) -> None:
        """Handle menu expansion and item clicking for a specific item.

        Args:
            item: Item dictionary containing menu and ID information
            config_values: Configuration values for timeouts and delays
        """
        item_id = item.get("id")
        menu_text = item.get("menu")

        # Smart menu expansion
        if menu_text:
            logging.debug(f"Finding and expanding menu '{menu_text}' for node '{item_id}'")
            try:
                success = await self._expand_menu_containing_node(
                    menu_text,
                    item_id,
                    timeout=config_values["navigation_timeout"],
                    expand_delay=config_values["expand_delay"],
                )
                if success:
                    logging.debug(f"Successfully expanded '{menu_text}' menu")
                else:
                    logging.warning(f"Could not find node '{item_id}' in '{menu_text}' menu")
            except Exception as expand_err:
                logging.warning(f"Error during menu expansion for '{menu_text}': {expand_err}")

        # Legacy fallback
        parent_menu_text = item.get("parent_menu_text")
        if parent_menu_text and parent_menu_text != menu_text:
            logging.debug(f"Legacy fallback: expanding parent menu '{parent_menu_text}'")
            try:
                await self._expand_specific_menu(
                    parent_menu_text,
                    timeout=config_values["navigation_timeout"],
                    expand_delay=config_values["expand_delay"],
                )
                await asyncio.sleep(0.3)
            except Exception as expand_err:
                logging.warning(f"Could not expand parent menu '{parent_menu_text}': {expand_err}")

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
            menu_li = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, menu_li_xpath))
            )
            logging.debug(f"Found menu LI for '{safe_menu_text}'. Checking expansion state...")

            # Check if already expanded
            try:
                expanded_icon = WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, expanded_icon_xpath))
                )
                if expanded_icon.is_displayed():
                    logging.debug(f"Menu '{safe_menu_text}' already expanded.")
                    return
            except TimeoutException:
                logging.debug(f"Expanded icon not found for '{safe_menu_text}'. Assuming collapsed.")

            # Find and click collapsed icon
            collapsed_icon = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, collapsed_icon_xpath))
            )

            logging.info(f"Expanding menu: '{safe_menu_text}'")
            self.driver.execute_script("arguments[0].scrollIntoView(false);", collapsed_icon)
            await asyncio.sleep(0.1)
            collapsed_icon.click()

            await self._wait_for_loader_to_disappear(timeout=timeout)
            await asyncio.sleep(expand_delay)
            logging.info(f"Finished expanding menu '{safe_menu_text}'")
            clicked_successfully = True

        except ElementClickInterceptedException:
            logging.warning(f"Click intercepted for menu '{safe_menu_text}'. Retrying...")
            await self._wait_for_loader_to_disappear(timeout=5)
            try:
                collapsed_icon = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, collapsed_icon_xpath))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(false);", collapsed_icon)
                await asyncio.sleep(0.1)
                self.driver.execute_script("arguments[0].click();", collapsed_icon)

                logging.info(f"Successfully clicked expander for '{safe_menu_text}' after interception.")
                clicked_successfully = True
                await self._wait_for_loader_to_disappear(timeout=timeout)
                await asyncio.sleep(expand_delay)
            except Exception as retry_e:
                logging.error(f"Failed to expand menu '{safe_menu_text}' even after retry: {retry_e}")

        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Could not find menu elements for '{safe_menu_text}': {e}")
        except Exception as e:
            logging.exception(f"Unexpected error expanding menu '{safe_menu_text}': {e}")

        # Verify expansion
        if clicked_successfully:
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.XPATH, expanded_icon_xpath))
                )
                logging.debug(f"Verified expansion of menu '{safe_menu_text}'")
            except TimeoutException:
                logging.warning(f"Could not verify expansion of menu '{safe_menu_text}'")

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

    async def _wait_for_loader_to_disappear(self, timeout: int = 10):
        """Wait for the 'Processing, please wait...' overlay to disappear."""
        logging.debug(f"Waiting up to {timeout}s for loader overlay to disappear...")
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located(self.selectors.LOADER_OVERLAY)
            )
            logging.debug("Loader overlay is not visible.")
        except TimeoutException:
            logging.warning(f"Loader overlay did not disappear within {timeout} seconds.")
        except Exception as e:
            logging.exception(f"Unexpected error waiting for loader to disappear: {e}")
