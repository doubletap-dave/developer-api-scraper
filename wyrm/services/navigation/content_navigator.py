"""Content navigation module for Wyrm application.

This module handles clicking sidebar items and waiting for content to load.
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


class ContentNavigator:
    """Handles clicking sidebar items and waiting for content updates."""

    def __init__(self, driver: WebDriver) -> None:
        """Initialize the content navigator.

        Args:
            driver: WebDriver instance
        """
        self.driver = driver
        self.selectors = SelectorsService()

    async def click_item_and_wait(self, item, config_values: Dict) -> None:
        """Click sidebar item and wait for content to load.

        Args:
            item: Item dictionary containing ID
            config_values: Configuration values for timeouts and delays
        """
        # Handle both SidebarItem models and dict items for backward compatibility
        if hasattr(item, 'id'):
            item_id = item.id
        else:
            item_id = item.get("id")

        # Click the sidebar item
        await self._click_sidebar_item(
            item_id, timeout=config_values["navigation_timeout"]
        )
        await asyncio.sleep(config_values["post_click_delay"])

        # Wait for content to load
        logging.debug(f"Waiting for content to load after clicking {item_id}...")
        await self._wait_for_content_update(
            timeout=config_values["content_wait_timeout"]
        )
        logging.debug("Content area loaded.")

    async def _click_sidebar_item(self, item_id: str, timeout: int = 10):
        """Click a sidebar item by its ID."""
        if not item_id:
            raise ValueError("Item ID is required")

        logging.debug(f"Attempting to click sidebar item with ID: {item_id}")

        try:
            # First, find the li element by ID
            li_element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, item_id))
            )

            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", li_element)
            await asyncio.sleep(0.2)  # Brief pause after scrolling

            # Try to find and click the anchor element inside the li
            try:
                anchor_element = li_element.find_element(By.TAG_NAME, "a")

                # Wait for the anchor to be clickable
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(anchor_element)
                )

                # Click the anchor element
                anchor_element.click()
                logging.debug(f"Successfully clicked anchor inside item: {item_id}")

            except Exception:
                # Fallback: try clicking the li element directly
                logging.debug(f"No clickable anchor found, trying li element directly: {item_id}")

                # Wait for the li element to be clickable
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(li_element)
                )

                # Click the li element
                li_element.click()
                logging.debug(f"Successfully clicked li element: {item_id}")

        except ElementClickInterceptedException:
            logging.warning(f"Click intercepted for {item_id}, trying JavaScript click...")
            try:
                li_element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.ID, item_id))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", li_element)
                await asyncio.sleep(0.2)

                # Try JavaScript click on anchor first
                try:
                    anchor_element = li_element.find_element(By.TAG_NAME, "a")
                    self.driver.execute_script("arguments[0].click();", anchor_element)
                    logging.debug(f"Successfully clicked anchor using JavaScript: {item_id}")
                except Exception:
                    # Fallback to JavaScript click on li
                    self.driver.execute_script("arguments[0].click();", li_element)
                    logging.debug(f"Successfully clicked li using JavaScript: {item_id}")

            except Exception as js_error:
                logging.error(f"JavaScript click also failed for {item_id}: {js_error}")
                raise

        except TimeoutException:
            logging.error(f"Timeout waiting for clickable element: {item_id}")
            raise
        except NoSuchElementException:
            logging.error(f"Element not found: {item_id}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error clicking {item_id}: {e}")
            raise

    async def _wait_for_content_update(self, timeout: int = 20):
        """Wait for the content area to update with new content."""
        logging.debug(f"Waiting up to {timeout}s for content area to update...")

        def content_ready_condition(driver: WebDriver):
            """Custom condition to check if content is ready."""
            try:
                # Check if content pane exists and has content
                content_elements = driver.find_elements(*self.selectors.CONTENT_PANE_INNER_HTML_TARGET)
                if not content_elements:
                    return False

                content_element = content_elements[0]

                # Check if content element has meaningful content
                content_html = content_element.get_attribute("innerHTML")
                if not content_html or len(content_html.strip()) < 100:
                    return False

                # Check for specific content indicators
                content_text = content_element.text.strip()
                if not content_text or len(content_text) < 50:
                    return False

                # Check that we're not seeing loading states
                loading_indicators = [
                    "loading", "please wait", "processing",
                    "fetching", "retrieving"
                ]
                content_lower = content_text.lower()
                if any(indicator in content_lower for indicator in loading_indicators):
                    return False

                return True

            except Exception as e:
                logging.debug(f"Content ready check failed: {e}")
                return False

        try:
            WebDriverWait(self.driver, timeout).until(content_ready_condition)
            logging.debug("Content area successfully updated")
        except TimeoutException:
            logging.warning(f"Content area did not update within {timeout} seconds")
            # Don't raise exception - content might still be usable
        except Exception as e:
            logging.warning(f"Error waiting for content update: {e}")
            # Don't raise exception - continue with processing
