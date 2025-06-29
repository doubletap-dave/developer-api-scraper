"""Orchestration package for Wyrm application.

This package provides a modular orchestration system that coordinates
the entire scraping workflow through specialized components.
"""

from typing import Optional

import structlog

from wyrm.services.configuration import ConfigurationService
from wyrm.services.navigation import NavigationService
from wyrm.services.parsing import ParsingService
from wyrm.services.progress_service import ProgressService
from wyrm.services.storage import StorageService

from .workflow_manager import WorkflowManager
from .item_processor import ItemProcessor
from .structure_handler import StructureHandler


class Orchestrator:
    """Main orchestrator service for the Wyrm scraping application.

    This service coordinates the entire workflow by delegating to specialized
    services for different aspects of the scraping process. It handles the
    high-level flow from configuration loading through final content extraction.

    The orchestrator ensures proper error handling, resource cleanup, and
    progress reporting throughout the scraping workflow.

    Attributes:
        config_service: Service for configuration loading and validation.
        navigation_service: Service for browser automation and navigation.
        parsing_service: Service for HTML parsing and structure extraction.
        storage_service: Service for file operations and content storage.
        progress_service: Service for progress tracking and reporting.
        workflow_manager: Manages the main scraping workflow.
        item_processor: Handles item processing and content extraction.
        structure_handler: Manages sidebar structure loading and parsing.
    """

    def __init__(self) -> None:
        """Initialize the Orchestrator service.

        Creates instances of all required services for the scraping workflow.
        Services are initialized with default configurations and can be
        customized through the configuration loading process.

        Args:
            None

        Returns:
            None
        """
        self.logger = structlog.get_logger(__name__)
        self.config_service = ConfigurationService()
        self.navigation_service = NavigationService()
        self.parsing_service = ParsingService()
        self.storage_service = StorageService()
        self.progress_service = ProgressService()
        
        # Initialize orchestration components
        self.workflow_manager = WorkflowManager(self)
        self.item_processor = ItemProcessor(self)
        self.structure_handler = StructureHandler(self)
        
        self._config = None  # Store config for cleanup
        self._full_expansion_done = False  # Prevents duplicate full-site expansions

    async def run_scraping_workflow(
        self,
        config_path: str,
        headless: Optional[bool] = None,
        log_level: Optional[str] = None,
        save_structure: bool = False,
        save_html: bool = False,
        debug: bool = False,
        max_expand_attempts: Optional[int] = None,
        force: bool = False,
        test_item_id: Optional[str] = None,
        max_items: Optional[int] = None,
        resume_info: bool = False,
        structure_filename: Optional[str] = None,
        html_filename: Optional[str] = None,
        force_full_expansion: bool = False,
    ) -> None:
        """Run the complete scraping workflow.

        Delegates to the WorkflowManager for the actual workflow execution.
        This method maintains the same interface as the original orchestrator
        to ensure backward compatibility.

        Args:
            config_path: Path to YAML configuration file.
            headless: Override headless browser mode. If None, uses config value.
            log_level: Override logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            save_structure: Whether to save parsed structure to debug directory.
            save_html: Whether to save raw HTML to debug directory.
            debug: Enable comprehensive debug mode with additional logging and saves.
            max_expand_attempts: Override maximum menu expansion attempts.
            force: Overwrite existing output files instead of skipping them.
            test_item_id: DEPRECATED. Process only the specified item ID.
            max_items: Maximum number of items to process.
            resume_info: Display resume information and exit without processing.
            structure_filename: Custom filename for saved structure (optional).
            html_filename: Custom filename for saved HTML (optional).
            force_full_expansion: Whether to force full menu expansion.

        Returns:
            None

        Raises:
            Exception: Re-raises any unexpected errors after logging.
            KeyboardInterrupt: Re-raises user interruption after cleanup.
        """
        await self.workflow_manager.run_scraping_workflow(
            config_path=config_path,
            headless=headless,
            log_level=log_level,
            save_structure=save_structure,
            save_html=save_html,
            debug=debug,
            max_expand_attempts=max_expand_attempts,
            force=force,
            test_item_id=test_item_id,
            max_items=max_items,
            resume_info=resume_info,
            structure_filename=structure_filename,
            html_filename=html_filename,
            force_full_expansion=force_full_expansion,
        )

    def _initialize_endpoint_aware_services(self, config):
        """Initialize services that need endpoint-specific configuration.

        Args:
            config: Application configuration object.
        """
        # Note: Services are now initialized with default configurations
        # and don't need endpoint-specific initialization
        pass

    async def _cleanup(self):
        """Clean up resources and close browser driver.

        Returns:
            None
        """
        try:
            if self.navigation_service and self._config:
                await self.navigation_service.cleanup(self._config)
                self.logger.info("Navigation service cleanup completed")
        except Exception as e:
            self.logger.warning("Error during cleanup", error=str(e))


# Maintain backward compatibility by exposing Orchestrator at package level
__all__ = ["Orchestrator"]
