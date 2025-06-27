"""Navigation service package for Wyrm application.

This package provides navigation operations through specialized sub-modules:
- DriverManager: Handles WebDriver setup and cleanup
- MenuExpander: Manages menu expansion operations
- ContentNavigator: Handles item clicking and content waiting
"""

import asyncio
import logging
from typing import Dict, Optional

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from .driver_manager import DriverManager
from .menu_expander import MenuExpander
from .content_navigator import ContentNavigator
from ..selectors_service import SelectorsService


class NavigationService:
    """Main navigation service that coordinates specialized sub-modules.

    This service delegates to specialized sub-modules while maintaining
    backward compatibility with the original NavigationService interface.
    """

    def __init__(self) -> None:
        """Initialize the navigation service with sub-modules."""
        self.driver_manager = DriverManager()
        self.menu_expander: Optional[MenuExpander] = None
        self.content_navigator: Optional[ContentNavigator] = None
        self.selectors = SelectorsService()

    async def initialize_driver(self, config: Dict) -> None:
        """Initialize WebDriver for navigation."""
        await self.driver_manager.initialize_driver(config)

        # Initialize helper classes with the driver
        driver = self.driver_manager.get_driver()
        if driver:
            self.menu_expander = MenuExpander(driver)
            self.content_navigator = ContentNavigator(driver)

    async def navigate_and_wait(self, config: Dict, config_values: Dict) -> str:
        """Navigate to URL and wait for sidebar to load.

        Args:
            config: Configuration dictionary
            config_values: Extracted configuration values

        Returns:
            Raw sidebar HTML
        """
        driver = self.driver_manager.get_driver()
        if not driver:
            raise RuntimeError("WebDriver not initialized")

        url = config.get("url") or config.get("target_url")
        if not url:
            raise ValueError("No URL specified in configuration")

        logging.info(f"Navigating to: {url}")
        driver.get(url)
        logging.info(f"Successfully navigated to {url}")

        # Add delay for page to start loading
        await asyncio.sleep(2.0)

        logging.info("Waiting for sidebar to load...")
        await self._wait_for_sidebar(
            timeout=config_values["sidebar_wait_timeout"]
        )
        logging.info("Sidebar loaded successfully.")

        # Get and return sidebar HTML
        return await self._get_sidebar_html()

    async def _wait_for_sidebar(self, timeout: int = 15) -> WebElement:
        """Wait for the sidebar container to be present and visible."""
        driver = self.driver_manager.get_driver()
        if not driver:
            raise RuntimeError("WebDriver not initialized")

        logging.debug(f"Waiting up to {timeout}s for sidebar container...")
        try:
            sidebar_element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(self.selectors.SIDEBAR_CONTAINER)
            )
            logging.debug("Sidebar container found.")
            return sidebar_element
        except TimeoutException:
            logging.error(f"Sidebar container not found within {timeout} seconds.")
            raise

    async def _get_sidebar_html(self) -> str:
        """Get the raw HTML content of the sidebar."""
        driver = self.driver_manager.get_driver()
        if not driver:
            raise RuntimeError("WebDriver not initialized")

        try:
            sidebar_element = driver.find_element(*self.selectors.SIDEBAR_CONTAINER)
            sidebar_html = sidebar_element.get_attribute("outerHTML")
            logging.debug(f"Retrieved sidebar HTML (length: {len(sidebar_html)})")
            return sidebar_html
        except Exception as e:
            logging.error(f"Failed to get sidebar HTML: {e}")
            raise

    # Delegate methods to sub-modules
    async def expand_menu_for_item(self, item: Dict, config_values: Dict) -> None:
        """Handle menu expansion for a specific item."""
        if not self.menu_expander:
            raise RuntimeError("MenuExpander not initialized")
        await self.menu_expander.expand_menu_for_item(item, config_values)

    async def click_item_and_wait(self, item: Dict, config_values: Dict) -> None:
        """Click sidebar item and wait for content to load."""
        if not self.content_navigator:
            raise RuntimeError("ContentNavigator not initialized")
        await self.content_navigator.click_item_and_wait(item, config_values)

    def get_driver(self) -> Optional[WebDriver]:
        """Get the current WebDriver instance."""
        return self.driver_manager.get_driver()

    async def cleanup(self, config: Dict) -> None:
        """Clean up the WebDriver and perform any necessary cleanup."""
        await self.driver_manager.cleanup(config)
        # Reset helper classes
        self.menu_expander = None
        self.content_navigator = None


# Maintain backward compatibility by exposing the main class
__all__ = ['NavigationService']
