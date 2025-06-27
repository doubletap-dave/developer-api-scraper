"""Driver management module for Wyrm application.

This module handles WebDriver setup, configuration, and cleanup operations.
"""

import asyncio
import logging
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager


class DriverManager:
    """Handles WebDriver setup, configuration, and cleanup."""

    def __init__(self) -> None:
        """Initialize the driver manager."""
        self.driver: Optional[WebDriver] = None

    async def initialize_driver(self, config) -> None:
        """Initialize the WebDriver based on configuration.

        Args:
            config: Configuration (AppConfig model or dict) containing webdriver settings
        """
        # Handle both AppConfig models and dict config for backward compatibility
        if hasattr(config, 'webdriver'):
            webdriver_config = config.webdriver
        else:
            webdriver_config = config.get("webdriver", {})
        self.driver = await self._setup_driver(webdriver_config)
        logging.info("WebDriver initialized successfully")

    async def _setup_driver(
        self,
        webdriver_config,
        browser: Optional[str] = None,
        headless: Optional[bool] = None,
    ) -> WebDriver:
        """Set up and configure the WebDriver.

        Args:
            webdriver_config: WebDriver configuration (WebDriverConfig model or dict)
            browser: Browser type override
            headless: Headless mode override

        Returns:
            Configured WebDriver instance
        """
        # Handle both WebDriverConfig models and dict config for backward compatibility
        if hasattr(webdriver_config, 'browser'):
            browser_type = browser or webdriver_config.browser.lower()
            is_headless = headless if headless is not None else webdriver_config.headless
        else:
            browser_type = browser or webdriver_config.get("browser", "chrome").lower()
            is_headless = headless if headless is not None else webdriver_config.get("headless", True)

        logging.info(f"Setting up {browser_type} driver (headless: {is_headless})")

        try:
            if browser_type == "chrome":
                return await self._setup_chrome_driver(is_headless)
            elif browser_type == "firefox":
                return await self._setup_firefox_driver(is_headless)
            elif browser_type == "edge":
                return await self._setup_edge_driver(is_headless)
            else:
                raise ValueError(f"Unsupported browser: {browser_type}")
        except Exception as e:
            logging.error(f"Failed to set up {browser_type} driver: {e}")
            raise

    async def _setup_chrome_driver(self, headless: bool) -> webdriver.Chrome:
        """Set up Chrome WebDriver."""
        options = webdriver.ChromeOptions()

        if headless:
            options.add_argument("--headless")

        # Additional Chrome options for stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    async def _setup_firefox_driver(self, headless: bool) -> webdriver.Firefox:
        """Set up Firefox WebDriver."""
        options = webdriver.FirefoxOptions()

        if headless:
            options.add_argument("--headless")

        # Additional Firefox options
        options.add_argument("--width=1920")
        options.add_argument("--height=1080")

        service = FirefoxService(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options)

    async def _setup_edge_driver(self, headless: bool) -> webdriver.Edge:
        """Set up Edge WebDriver."""
        options = webdriver.EdgeOptions()

        if headless:
            options.add_argument("--headless")

        # Additional Edge options for stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        service = EdgeService(EdgeChromiumDriverManager().install())
        return webdriver.Edge(service=service, options=options)

    def get_driver(self) -> Optional[WebDriver]:
        """Get the current WebDriver instance.

        Returns:
            WebDriver instance or None if not initialized
        """
        return self.driver

    async def cleanup(self, config) -> None:
        """Clean up the WebDriver and perform any necessary cleanup.

        Args:
            config: Configuration dictionary
        """
        if self.driver:
            try:
                # Check if running in non-headless mode and pause if configured
                # Handle both AppConfig models and dict config for backward compatibility
                if hasattr(config, 'webdriver'):
                    webdriver_config = config.webdriver
                    debug_settings = config.debug_settings
                    is_headless = webdriver_config.headless
                    pause_seconds = debug_settings.non_headless_pause_seconds
                else:
                    webdriver_config = config.get("webdriver", {})
                    debug_settings = config.get("debug_settings", {})
                    is_headless = webdriver_config.get("headless", True)
                    pause_seconds = debug_settings.get("non_headless_pause_seconds", 10)

                if not is_headless:
                    if pause_seconds > 0:
                        logging.info(f"Non-headless mode: pausing for {pause_seconds} seconds before cleanup...")
                        await asyncio.sleep(pause_seconds)

                self.driver.quit()
                logging.info("WebDriver cleaned up successfully")
            except Exception as e:
                logging.error(f"Error during driver cleanup: {e}")
            finally:
                self.driver = None
