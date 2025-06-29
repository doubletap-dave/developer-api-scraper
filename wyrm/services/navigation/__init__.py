"""Navigation service package for Wyrm application.

Coordinates DriverManager, MenuExpander, and ContentNavigator operations.
"""

import asyncio
from typing import Dict, Optional
import structlog
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver

from .driver_manager import DriverManager
from .content_navigator import ContentNavigator
from .menu_scanner import MenuScanner
from .menu_actions import MenuActions
from .menu_state import MenuState
from ..selectors_service import SelectorsService


class MenuExpander:
    """Orchestrates menu expansion using scanner, actions, and state sub-modules."""

    def __init__(self, driver: WebDriver) -> None:
        """Initialize the menu expander with sub-modules."""
        self.driver = driver
        self.scanner = MenuScanner(driver)
        self.actions = MenuActions(driver)
        self.state = MenuState()
        self.selectors = SelectorsService()

    async def expand_menu_for_item(self, item, config_values: Dict) -> None:
        """Handle menu expansion for a specific item using sub-modules."""
        # Extract item attributes
        item_id = getattr(item, 'id', None) or item.get("id")
        item_text = getattr(item, 'text', None) or item.get("text", "Unknown")
        menu_text = getattr(item, 'menu', None) or item.get("menu")
        level = getattr(item, 'level', 0) or item.get("level", 0)

        # Use PowerFlex-specific approach through scanner
        try:
            expansion_data = self.scanner.find_powerflex_expansion_path(item_id, item_text)
            if expansion_data.get('found') and not expansion_data.get('alreadyVisible'):
                await self.actions.expand_powerflex_path_to_item(expansion_data)
                return
        except Exception as e:
            structlog.get_logger().warning(f"PowerFlex path expansion failed: {e}")

        # Fallback to traditional approach
        if level > 1:
            ancestor_menus = await self.scanner.discover_ancestor_menus(item_text, item_id)
            for ancestor_menu in ancestor_menus:
                menu_info = self.scanner.find_menu_by_text(ancestor_menu)
                if menu_info:
                    await self.actions.expand_specific_menu(menu_info, 
                        config_values["navigation_timeout"], config_values["expand_delay"])

        # Expand direct menu if specified
        if menu_text:
            menu_info = self.scanner.find_menu_by_text(menu_text)
            if menu_info:
                await self.actions.expand_menu_containing_node(menu_info, item_id,
                    config_values["navigation_timeout"], config_values["expand_delay"])

    async def expand_all_menus_comprehensive(self, timeout: int = 60) -> None:
        """Comprehensively expand all collapsible menus using sub-modules."""
        await self.actions.expand_all_menus_comprehensive(self.scanner, timeout)

        # Reveal standalone pages
        standalone_containers = self.scanner.reveal_standalone_pages()
        if standalone_containers:
            await self.actions.reveal_standalone_pages(standalone_containers, timeout)


class NavigationService:
    """Main navigation service that coordinates specialized sub-modules."""

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
            self.content_navigator = ContentNavigator(driver)

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

    async def navigate_to_item(self, item) -> None:
        """Navigate to an item by expanding menus and clicking the item."""
        if not self.driver_manager.get_driver():
            raise RuntimeError("WebDriver not initialized. Call initialize_driver() first.")

        if not self.menu_expander or not self.content_navigator:
            raise RuntimeError("Navigation sub-modules not initialized. Call initialize_driver() first.")

        item_text = getattr(item, 'text', None) or item.get('text', 'Unknown')
        self.logger.info("Navigating to item", item_text=item_text)

        await self.menu_expander.expand_menu_for_item(item, {
            "navigation_timeout": 10, "expand_delay": 0.25})
        await self.content_navigator.click_item_and_wait(item, {
            "navigation_timeout": 10, "post_click_delay": 1.0, "content_wait_timeout": 15})

        self.logger.info("Successfully navigated to item", item_text=item_text)

    def get_driver(self) -> Optional[WebDriver]:
        """Get the current WebDriver instance."""
        return self.driver_manager.get_driver()

    async def navigate_and_wait(self, config, config_values: Dict) -> str:
        """Navigate to target URL and wait for page to load.
        
        Args:
            config: Application configuration object
            config_values: Configuration values dictionary
            
        Returns:
            Initial sidebar HTML content
        """
        driver = self.get_driver()
        if not driver:
            raise RuntimeError("WebDriver not initialized. Call initialize_driver() first.")
            
        # Get target URL from config
        if hasattr(config, 'target_url'):
            target_url = config.target_url
        else:
            target_url = config.get('target_url')
            
        if not target_url:
            raise ValueError("No target URL specified in configuration")
            
        self.logger.info("Navigating to target URL", url=target_url)
        driver.get(target_url)
        
        # Wait for initial page load
        import time
        time.sleep(config_values.get('sidebar_wait_timeout', 5.0))
        
        # Return initial sidebar HTML
        return await self.get_sidebar_html()
        
    async def get_sidebar_html(self) -> str:
        """Extract sidebar HTML from the current page.
        
        Returns:
            HTML content of the sidebar
        """
        driver = self.get_driver()
        if not driver:
            raise RuntimeError("WebDriver not initialized. Call initialize_driver() first.")
            
        # Use selectors service to find sidebar content
        try:
            sidebar_elements = driver.find_elements(
                self.selectors.by, self.selectors.sidebar_container
            )
            if sidebar_elements:
                return sidebar_elements[0].get_attribute('outerHTML')
            else:
                # Fallback to page source if no specific sidebar found
                self.logger.warning("No sidebar container found, using page source")
                return driver.page_source
        except Exception as e:
            self.logger.warning(f"Error extracting sidebar HTML: {e}")
            return driver.page_source

    async def cleanup(self, config) -> None:
        """Clean up the WebDriver and perform any necessary cleanup."""
        await self.driver_manager.cleanup(config)
        # Reset helper classes
        self.menu_expander = None
        self.content_navigator = None


# Maintain backward compatibility by exposing the main class
__all__ = ['NavigationService']
