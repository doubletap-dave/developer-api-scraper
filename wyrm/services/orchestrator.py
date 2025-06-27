"""Orchestrator service for Wyrm application.

This service coordinates the entire scraping workflow by delegating to
specialized services for configuration, navigation, parsing, storage, and progress.
"""


import sys
from typing import Dict, List, Optional

import structlog

from wyrm.models.config import AppConfig
from wyrm.models.scrape import SidebarStructure
from wyrm.services.configuration_service import ConfigurationService
from wyrm.services.navigation import NavigationService
from wyrm.services.parsing import ParsingService
from wyrm.services.progress_service import ProgressService
from wyrm.services.storage import StorageService


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
    ) -> None:
        """Run the complete scraping workflow.

        Coordinates the entire scraping process from configuration loading
        through final content extraction. Handles CLI overrides, debug modes,
        and provides comprehensive error handling with proper cleanup.

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

        Returns:
            None

        Raises:
            Exception: Re-raises any unexpected errors after logging.
            KeyboardInterrupt: Re-raises user interruption after cleanup.
        """
        try:
            # Load configuration and setup
            config = self.config_service.load_config(config_path)

            # Merge CLI overrides
            cli_args = {
                "headless": headless,
                "log_level": log_level,
                "max_expand_attempts": max_expand_attempts,
            }
            config = self.config_service.merge_cli_overrides(config, cli_args)

            if debug:
                save_structure = True
                save_html = True
                self.logger.info(
                    "Debug mode enabled - forcing structure and HTML saves"
                )

            # Get configuration values
            config_values = self.config_service.extract_configuration_values(config)

            # Setup directories
            self.config_service.setup_directories(config_values)

            # Handle sidebar structure loading/parsing
            sidebar_structure = await self._handle_sidebar_structure(
                config, config_values, save_structure, save_html,
                structure_filename, html_filename, resume_info, force
            )

            # Process items from structure
            await self._process_items_from_structure(
                sidebar_structure, config_values, force,
                test_item_id, max_items, resume_info
            )

        except KeyboardInterrupt:
            self.logger.warning("User interrupted execution")
        except Exception as e:
            self.logger.exception("An unexpected error occurred", error=str(e))
        finally:
            await self._cleanup()

    async def _handle_sidebar_structure(
        self,
        config: AppConfig,
        config_values: Dict,
        save_structure: bool,
        save_html: bool,
        structure_filename: Optional[str],
        html_filename: Optional[str],
        resume_info: bool,
        force: bool,
    ) -> SidebarStructure:
        """Handle sidebar structure loading or parsing.

        Attempts to load existing structure from file first. If not found or
        force flag is set, performs live parsing by navigating to the target
        site and extracting the sidebar structure.

        Args:
            config: Application configuration with all settings.
            config_values: Extracted configuration values dictionary.
            save_structure: Whether to save parsed structure to debug directory.
            save_html: Whether to save raw HTML to debug directory.
            structure_filename: Custom filename for structure save (optional).
            html_filename: Custom filename for HTML save (optional).
            resume_info: Whether this is for resume info display only.
            force: Whether to force re-parsing even if structure exists.

        Returns:
            SidebarStructure: Parsed or loaded sidebar structure.

        Raises:
            Exception: If structure loading/parsing fails.
        """
        structure_filepath = self.parsing_service.get_structure_filepath(config_values)

        # Try to load existing structure first
        sidebar_structure = self.parsing_service.load_existing_structure(
            structure_filepath
        )

        if not sidebar_structure or force:
            # Need to parse live
            sidebar_structure = await self._perform_live_parsing(
                config, config_values, save_structure, save_html,
                structure_filename, html_filename, structure_filepath
            )

        # Handle resume check
        await self._handle_resume_check(
            sidebar_structure, config_values, resume_info, force
        )

        return sidebar_structure

    async def _perform_live_parsing(
        self,
        config: AppConfig,
        config_values: Dict,
        save_structure: bool,
        save_html: bool,
        structure_filename: Optional[str],
        html_filename: Optional[str],
        structure_filepath,
    ) -> SidebarStructure:
        """Perform live parsing of sidebar structure.

        Initializes browser driver, navigates to target URL, extracts sidebar HTML,
        and parses it into a structured format. Optionally saves debug files.

        Args:
            config: Application configuration with navigation settings.
            config_values: Extracted configuration values dictionary.
            save_structure: Whether to save parsed structure to debug directory.
            save_html: Whether to save raw HTML to debug directory.
            structure_filename: Custom filename for structure save (optional).
            html_filename: Custom filename for HTML save (optional).
            structure_filepath: Path where structure should be saved.

        Returns:
            SidebarStructure: Newly parsed sidebar structure.

        Raises:
            Exception: If navigation or parsing fails.
        """
        # Initialize driver and navigate
        await self.navigation_service.initialize_driver(config)
        sidebar_html = await self.navigation_service.navigate_and_wait(
            config, config_values
        )

        # Save debug files if requested
        if save_html:
            await self.parsing_service.save_debug_html(
                sidebar_html, config_values, html_filename
            )

        # Parse and save structure
        sidebar_structure = await self.parsing_service.parse_sidebar_structure(
            sidebar_html
        )

        if save_structure:
            await self.parsing_service.save_debug_structure(
                sidebar_structure, config_values, structure_filename
            )

        self.storage_service.save_structure_to_output(
            sidebar_structure, structure_filepath
        )
        return sidebar_structure

    async def _handle_resume_check(
        self,
        sidebar_structure: SidebarStructure,
        config_values: Dict,
        resume_info: bool,
        force: bool,
    ) -> None:
        """Handle resume information display and validation.

        Sets up progress tracking with total item count and optionally displays
        resume information showing existing vs missing files before exiting.

        Args:
            sidebar_structure: Parsed sidebar structure with all items.
            config_values: Configuration values including output directory.
            resume_info: Whether to display resume information and exit.
            force: Whether force mode is enabled (affects resume display).

        Returns:
            None

        Raises:
            SystemExit: If resume_info is True, exits after displaying information.
        """
        valid_items = self.parsing_service._get_valid_items(sidebar_structure)
        self.progress_service.set_total_items(len(valid_items))

        if resume_info:
            existing_items, items_needing_processing = (
                self.storage_service.check_existing_files(
                    valid_items, config_values["base_output_dir"]
                )
            )
            self.storage_service.display_resume_info(
                valid_items,
                existing_items,
                items_needing_processing,
                config_values["base_output_dir"]
            )
            sys.exit(0)

    async def _process_items_from_structure(
        self,
        sidebar_structure: SidebarStructure,
        config_values: Dict,
        force: bool,
        test_item_id: Optional[str],
        max_items: Optional[int],
        resume_info: bool,
    ) -> None:
        """Process items from the sidebar structure.

        Filters items based on provided criteria and processes them for content
        extraction. Handles test mode, item limits, and force overrides.

        Args:
            sidebar_structure: Parsed sidebar structure containing all items.
            config_values: Configuration values for processing.
            force: Whether to overwrite existing files.
            test_item_id: DEPRECATED. Specific item ID to process.
            max_items: Maximum number of items to process.
            resume_info: Whether this is resume info mode (affects processing).

        Returns:
            None

        Raises:
            Exception: If item processing fails.
        """
        valid_items = self.parsing_service._get_valid_items(sidebar_structure)

        # Filter items for processing
        items_to_process = self.parsing_service.filter_items_for_processing(
            valid_items, test_item_id, max_items
        )

        self.logger.info("Processing items", count=len(items_to_process))

        # Process items with progress tracking
        await self._process_items_with_progress(items_to_process, config_values)

    async def _process_items_with_progress(
        self,
        items_to_process: List[Dict],
        config_values: Dict,
    ) -> None:
        """Process items with progress tracking and reporting.

        Iterates through items and processes each one individually while
        maintaining progress reporting and error handling for individual failures.

        Args:
            items_to_process: List of sidebar items to process.
            config_values: Configuration values for processing.

        Returns:
            None

        Raises:
            Exception: If critical processing failures occur.
        """
        progress = self.progress_service.create_progress_display()

        with progress:
            task_id = progress.add_task(
                "Processing items...", total=len(items_to_process)
            )

            for item in items_to_process:
                try:
                    await self._process_single_item(
                        item, config_values, progress, task_id
                    )
                except Exception as e:
                    self.logger.error(
                        "Failed to process item",
                        item_id=item.get('id', 'unknown'),
                        error=str(e)
                    )
                    continue

    async def _process_single_item(
        self,
        item,
        config_values: Dict,
        progress,
        task_id: int,
    ) -> None:
        """Process a single sidebar item.

        Handles the complete processing workflow for an individual item,
        including navigation, content extraction, and file saving.

        Args:
            item: Sidebar item to process (dict or SidebarItem).
            config_values: Configuration values for processing.
            progress: Progress display instance for updates.
            task_id: Task ID for progress tracking.

        Returns:
            None

        Raises:
            Exception: If item processing fails.
        """
        # Handle both dict and SidebarItem objects
        item_text = item.text if hasattr(item, 'text') else item.get('text', 'Unknown')

        progress.update(task_id, description=f"Processing: {item_text}")

        # Check if file already exists (unless force mode)
        if not config_values.get('force', False):
            output_path = self.storage_service.get_output_path(
                item, config_values["base_output_dir"]
            )
            if output_path.exists():
                self.logger.info(
                    "Skipping existing file", path=str(output_path)
                )
                progress.advance(task_id)
                return

        # Navigate to item and extract content
        await self.navigation_service.navigate_to_item(item)
        content = await self.storage_service.extract_content_for_item(item)

        # Save content to file
        await self.storage_service.save_content_to_file(
            content, item, config_values
        )

        progress.advance(task_id)
        self.logger.info("Completed processing", item_text=item_text)

    async def _cleanup(self) -> None:
        """Perform cleanup operations.

        Ensures proper cleanup of resources like browser drivers and
        temporary files. Called in the finally block of the main workflow.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: Logs but doesn't re-raise cleanup errors.
        """
        try:
            await self.navigation_service.cleanup()
            self.logger.info("Cleanup completed successfully")
        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))
