"""Navigation service package for Wyrm application.

This package provides navigation operations through specialized sub-modules:
- DriverManager: Handles WebDriver setup and cleanup
- MenuExpander: Manages menu expansion operations
- ContentNavigator: Handles item clicking and content waiting
"""

import asyncio
from typing import Dict, Optional

import structlog
from selenium.common.exceptions import TimeoutException
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
        self.logger = structlog.get_logger(__name__)
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
            # Trigger dynamic structure detection
            if hasattr(self.selectors, 'detect_structure_type'):
                self.selectors.detect_structure_type(driver)
            
            self.menu_expander = MenuExpander(driver)
            self.menu_expander.selectors = self.selectors  # Pass endpoint-aware selectors
            self.content_navigator = ContentNavigator(driver)

    async def navigate_and_wait(self, config, config_values: Dict) -> str:
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

        # Handle both AppConfig models and dict config for backward compatibility
        if hasattr(config, 'target_url'):
            url = config.target_url
        else:
            url = config.get("url") or config.get("target_url")
        if not url:
            raise ValueError("No URL specified in configuration")

        self.logger.info("Navigating to target URL", url=url)
        driver.get(url)
        self.logger.info("Successfully navigated to target URL", url=url)

        # Add delay for page to start loading
        await asyncio.sleep(2.0)

        self.logger.info("Waiting for sidebar to load...")
        await self._wait_for_sidebar(
            timeout=config_values["sidebar_wait_timeout"]
        )
        self.logger.info("Sidebar container loaded. Waiting for content...")

        # Wait for the actual sidebar content to load with extended timeout
        # Angular apps can take a while to fully load navigation structures
        extended_timeout = max(config_values["sidebar_wait_timeout"] * 2, 30)
        await self._wait_for_sidebar_content(
            timeout=extended_timeout
        )
        self.logger.info("Sidebar loaded successfully.")

        # Get and return sidebar HTML
        return await self._get_sidebar_html()

    async def _wait_for_sidebar(self, timeout: int = 15) -> WebElement:
        """Wait for the sidebar container to be present and visible.
        
        Enhanced for 3.x endpoints which may need more time in headless mode.
        """
        driver = self.driver_manager.get_driver()
        if not driver:
            raise RuntimeError("WebDriver not initialized")
        
        # Increase timeout for 3.x endpoints which seem to need more time in headless mode
        endpoint_version = getattr(self.selectors, 'endpoint_version', '4.6')
        if endpoint_version.startswith('3.'):
            # Give 3.x endpoints more time, especially in headless mode
            timeout = max(timeout, 45)  # At least 45 seconds for 3.x
            self.logger.debug(
                "Using extended timeout for 3.x endpoint", 
                original_timeout=15, 
                extended_timeout=timeout
            )

        self.logger.debug(
            "Waiting for sidebar container", 
            timeout=timeout, 
            endpoint_version=endpoint_version
        )

        # Add retry logic with enhanced diagnostics
        max_retries = 3
        base_timeout = timeout // max_retries if max_retries > 1 else timeout

        for attempt in range(max_retries):
            try:
                effective_timeout = base_timeout if attempt < max_retries - 1 else timeout
                sidebar_element = WebDriverWait(driver, effective_timeout).until(
                    EC.presence_of_element_located(self.selectors.SIDEBAR_CONTAINER)
                )
                self.logger.debug("Sidebar container found.", attempt=attempt + 1)
                return sidebar_element

            except TimeoutException:
                self.logger.warning(
                    f"Sidebar container not found (attempt {attempt + 1}/{max_retries})",
                    timeout=effective_timeout,
                    current_url=driver.current_url
                )

                if attempt < max_retries - 1:
                    # Add diagnostic information
                    try:
                        page_title = driver.title
                        page_state = driver.execute_script("return document.readyState")
                        self.logger.debug(
                            "Page diagnostics before retry",
                            title=page_title,
                            ready_state=page_state,
                            url=driver.current_url
                        )

                        # Check if there are any error elements on the page
                        error_elements = driver.find_elements(
                            "css selector", "[class*='error'], [class*='Error']")
                        if error_elements:
                            self.logger.warning(
                                f"Found {len(error_elements)} potential error elements on page")

                    except Exception as diagnostic_error:
                        self.logger.debug("Error collecting diagnostics",
                                          error=str(diagnostic_error))

                    # Wait a bit before retry
                    await asyncio.sleep(2.0)
                    continue

        # Final failure
        self.logger.error(
            "Sidebar container not found after all retries",
            timeout=timeout,
            retries=max_retries,
            current_url=driver.current_url
        )
        raise TimeoutException(
            f"Sidebar container not found within {timeout} seconds after {max_retries} attempts")

    async def _wait_for_sidebar_content(self, timeout: int = 15) -> None:
        """Wait for the actual sidebar content (app-api-doc-item elements) to load.

        The sidebar container may be present but empty while Angular loads the content.
        This method waits for the actual navigation items to appear.

        Args:
            timeout: Maximum time to wait for content to load

        Raises:
            TimeoutException: If sidebar content doesn't load within timeout
        """
        driver = self.driver_manager.get_driver()
        if not driver:
            raise RuntimeError("WebDriver not initialized")

        self.logger.debug("Waiting for sidebar content to load", timeout=timeout)

        # Wait for app-api-doc-item elements to appear with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located(self.selectors.APP_API_DOC_ITEM)
                )
                self.logger.debug(
                    "Sidebar content loaded - app-api-doc-item elements found.")

                # Additional short wait for content to stabilize
                await asyncio.sleep(2.0)
                return

            except TimeoutException:
                self.logger.warning(
                    f"Sidebar content not found (attempt {attempt + 1}/{max_retries})",
                    timeout=timeout
                )

                if attempt < max_retries - 1:
                    # Try refreshing the page and waiting again
                    self.logger.info("Refreshing page and retrying...")
                    driver.refresh()
                    await asyncio.sleep(3.0)  # Wait for page to start loading
                    continue
                else:
                    # Final attempt failed, log diagnostic info
                    self.logger.warning(
                        "Final attempt failed, collecting diagnostic info")

                    # Let's check what's actually in the sidebar
                    try:
                        sidebar_html = await self._get_sidebar_html()
                        self.logger.debug("Current sidebar HTML preview",
                                          html_preview=sidebar_html[:500])

                        # Check if there are any other elements that might indicate loading
                        other_elements = driver.find_elements(
                            "css selector", "div.filter-api-sidebar-wrapper *")
                        self.logger.debug(
                            "Elements found in sidebar container", element_count=len(other_elements))

                    except Exception as e:
                        self.logger.debug(
                            "Error examining sidebar content", error=str(e))

                    raise TimeoutException(
                        f"Sidebar content did not load within {timeout} seconds after {max_retries} attempts")

    async def _get_sidebar_html(self) -> str:
        """Get the raw HTML content of the sidebar."""
        driver = self.driver_manager.get_driver()
        if not driver:
            raise RuntimeError("WebDriver not initialized")

        try:
            sidebar_element = driver.find_element(*self.selectors.SIDEBAR_CONTAINER)
            sidebar_html = sidebar_element.get_attribute("outerHTML")
            self.logger.debug("Retrieved sidebar HTML", html_length=len(sidebar_html))
            return sidebar_html
        except Exception as e:
            self.logger.error("Failed to get sidebar HTML", error=str(e))
            raise

    # Delegate methods to sub-modules
    async def expand_menu_for_item(self, item, config_values: Dict) -> None:
        """Handle menu expansion for a specific item."""
        if not self.menu_expander:
            raise RuntimeError("MenuExpander not initialized")
        await self.menu_expander.expand_menu_for_item(item, config_values)

    async def expand_all_menus_comprehensive(self, timeout: int = 60) -> None:
        """Comprehensively expand all collapsible menus in the sidebar."""
        if not self.menu_expander:
            raise RuntimeError("MenuExpander not initialized")
        await self.menu_expander.expand_all_menus_comprehensive(timeout)

    async def click_item_and_wait(self, item, config_values: Dict) -> None:
        """Click sidebar item and wait for content to load."""
        if not self.content_navigator:
            raise RuntimeError("ContentNavigator not initialized")
        await self.content_navigator.click_item_and_wait(item, config_values)

    async def get_sidebar_html(self) -> str:
        """Get the raw HTML content of the sidebar.

        Public method to retrieve the current sidebar HTML content.
        Useful after menu expansion to get the updated HTML structure.

        Returns:
            str: Raw HTML content of the sidebar element

        Raises:
            RuntimeError: If WebDriver is not initialized
            Exception: If HTML retrieval fails
        """
        return await self._get_sidebar_html()

    async def navigate_to_item(self, item) -> None:
        """Navigate to an item by expanding menus and clicking the item.

        This method combines menu expansion and item clicking operations
        to provide a complete navigation workflow for a sidebar item.

        Args:
            item: Item (SidebarItem model or dict) containing navigation metadata

        Raises:
            RuntimeError: If sub-modules are not initialized or driver is missing
            Exception: If navigation fails
        """
        # Check driver initialization first
        if not self.driver_manager.get_driver():
            raise RuntimeError(
                "WebDriver not initialized. Call initialize_driver() first.")

        # Check sub-module initialization
        if not self.menu_expander or not self.content_navigator:
            raise RuntimeError(
                "Navigation sub-modules not initialized. Call initialize_driver() first.")

        # Handle both SidebarItem models and dict items for backward compatibility
        if hasattr(item, 'text'):
            item_text = item.text
        else:
            item_text = item.get('text', 'Unknown')

        self.logger.info("Navigating to item", item_text=item_text)

        # Ensure the sidebar path to the item is visible before clicking.
        # This expands the menu that directly contains the target node (and, if
        # provided, its parent menu) so that the node element actually exists in
        # the DOM.
        await self.menu_expander.expand_menu_for_item(
            item,
            {
                "navigation_timeout": 10,
                "expand_delay": 0.25,
            },
        )

        # Default timeouts/delays for the click-and-wait routine.  These should
        # ideally come from the orchestrator-level config, but we keep sensible
        # fall-backs here so that the helper can be used in isolation.
        default_config_values = {
            "navigation_timeout": 10,
            "post_click_delay": 1.0,
            "content_wait_timeout": 15,
        }

        # Click the item and wait for the main content pane to load.
        await self.content_navigator.click_item_and_wait(item, default_config_values)

        self.logger.info("Successfully navigated to item", item_text=item_text)

    def get_driver(self) -> Optional[WebDriver]:
        """Get the current WebDriver instance."""
        return self.driver_manager.get_driver()

    async def cleanup(self, config) -> None:
        """Clean up the WebDriver and perform any necessary cleanup."""
        await self.driver_manager.cleanup(config)
        # Reset helper classes
        self.menu_expander = None
        self.content_navigator = None


# Maintain backward compatibility by exposing the main class
__all__ = ['NavigationService']
