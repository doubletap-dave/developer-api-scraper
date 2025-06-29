"""Parallel worker service for concurrent content extraction.

This service handles individual content extraction tasks in parallel processing mode.
Each worker manages its own WebDriver instance and processes a single item independently.
"""

import asyncio
from typing import Dict, Optional

import structlog
from selenium.webdriver.remote.webdriver import WebDriver

from wyrm.models.scrape import SidebarItem
from wyrm.services.navigation.driver_manager import DriverManager
from wyrm.services.storage import StorageService


class ParallelWorker:
    """Worker service for processing individual items in parallel mode.

    Each worker instance is responsible for:
    - Managing its own WebDriver instance
    - Navigating to a specific documentation item
    - Extracting and saving content
    - Cleaning up resources properly

    Workers are designed to be independent and stateless to support
    safe concurrent execution.
    """

    def __init__(self, worker_id: int) -> None:
        """Initialize a parallel worker.

        Args:
            worker_id: Unique identifier for this worker instance
        """
        self.worker_id = worker_id
        self.logger = structlog.get_logger(__name__)
        self.driver_manager: Optional[DriverManager] = None
        self.storage_service = StorageService()

    async def process_item(
        self,
        item: SidebarItem,
        config,
        config_values: Dict,
        semaphore: asyncio.Semaphore,
    ) -> bool:
        """Process a single item with its own WebDriver instance.

        This method represents the complete lifecycle of processing one
        documentation item in parallel mode. It:
        1. Acquires a semaphore slot to limit concurrency
        2. Initializes its own WebDriver instance
        3. Navigates to the target URL
        4. Expands necessary menus to make the item visible
        5. Navigates to the specific item
        6. Extracts and saves content
        7. Cleans up resources

        Args:
            item: SidebarItem to process
            config: Application configuration
            config_values: Extracted configuration values
            semaphore: Semaphore to limit concurrent workers

        Returns:
            bool: True if processing succeeded, False otherwise
        """
        async with semaphore:
            try:
                # Log worker start
                self.logger.info(
                    "Worker starting item processing",
                    worker_id=self.worker_id,
                    item_text=item.text,
                    item_id=item.id
                )

                # Check if file already exists (unless force mode)
                if not config_values.get('force', False):
                    output_path = self.storage_service.get_output_path(
                        item, config_values["base_output_dir"]
                    )
                    if output_path.exists():
                        self.logger.debug(
                            "Worker skipping existing file",
                            worker_id=self.worker_id,
                            path=str(output_path)
                        )
                        return True

                # Initialize WebDriver for this worker
                await self._initialize_driver(config)

                # Navigate to site and prepare for item processing
                await self._navigate_to_site(config, config_values)

                # Expand menus to make the target item accessible
                await self._ensure_item_accessible(item, config_values)

                # Navigate to the specific item and extract content
                await self._navigate_and_extract(item, config_values)

                self.logger.info(
                    "Worker completed item processing",
                    worker_id=self.worker_id,
                    item_text=item.text
                )
                return True

            except Exception as e:
                self.logger.error(
                    "Worker failed to process item",
                    worker_id=self.worker_id,
                    item_text=getattr(item, 'text', 'unknown'),
                    item_id=getattr(item, 'id', 'unknown'),
                    error=str(e)
                )
                return False
            finally:
                # Always clean up resources
                await self._cleanup()

    async def _initialize_driver(self, config) -> None:
        """Initialize WebDriver for this worker."""
        self.driver_manager = DriverManager()
        await self.driver_manager.initialize_driver(config)

        if not self.driver_manager.get_driver():
            raise RuntimeError(
                f"Worker {self.worker_id}: Failed to initialize WebDriver")

        self.logger.debug(
            "Worker WebDriver initialized",
            worker_id=self.worker_id
        )

    async def _navigate_to_site(self, config, config_values: Dict) -> None:
        """Navigate to the target site and wait for sidebar to load."""
        driver = self.driver_manager.get_driver()
        if not driver:
            raise RuntimeError(f"Worker {self.worker_id}: WebDriver not available")

        # Get target URL from config
        url = getattr(config, 'target_url', None) or config.get('target_url')
        if not url:
            raise ValueError("No target URL specified in configuration")

        self.logger.debug(
            "Worker navigating to target URL",
            worker_id=self.worker_id,
            url=url
        )

        driver.get(url)

        # Basic wait for page load
        await asyncio.sleep(3.0)

        # TODO: Add sidebar wait logic similar to NavigationService
        # For now, we'll use a simple wait
        await asyncio.sleep(2.0)

    async def _ensure_item_accessible(self, item: SidebarItem, config_values: Dict) -> None:
        """Ensure the target item is accessible by expanding necessary menus."""
        # For now, we'll implement a simple approach
        # In a full implementation, we would need menu expansion logic
        # similar to what's in MenuExpander

        self.logger.debug(
            "Worker ensuring item accessibility",
            worker_id=self.worker_id,
            item_text=item.text,
            menu=getattr(item, 'menu', None)
        )

        # Placeholder for menu expansion
        # This would need to be implemented based on the specific
        # menu structure and navigation requirements
        await asyncio.sleep(0.5)

    async def _navigate_and_extract(self, item: SidebarItem, config_values: Dict) -> None:
        """Navigate to the item and extract content."""
        driver = self.driver_manager.get_driver()
        if not driver:
            raise RuntimeError(f"Worker {self.worker_id}: WebDriver not available")

        # For now, this is a placeholder
        # In the full implementation, this would:
        # 1. Click the sidebar item
        # 2. Wait for content to load
        # 3. Extract content using StorageService
        # 4. Save the content to file

        self.logger.debug(
            "Worker extracting content",
            worker_id=self.worker_id,
            item_text=item.text
        )

        # Placeholder content extraction
        await self.storage_service.save_content_for_item(
            item, driver, config_values
        )

    async def _cleanup(self) -> None:
        """Clean up WebDriver and other resources."""
        try:
            if self.driver_manager:
                await self.driver_manager.cleanup(None)
                self.logger.debug(
                    "Worker cleanup completed",
                    worker_id=self.worker_id
                )
        except Exception as e:
            self.logger.warning(
                "Worker cleanup failed",
                worker_id=self.worker_id,
                error=str(e)
            )

    def get_driver(self) -> Optional[WebDriver]:
        """Get the current WebDriver instance for this worker."""
        return self.driver_manager.get_driver() if self.driver_manager else None
