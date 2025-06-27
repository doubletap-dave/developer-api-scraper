"""Orchestrator service for Wyrm application.

This service coordinates the entire scraping workflow by delegating to
specialized services for configuration, navigation, parsing, storage, and progress.
"""


import logging
import sys
from typing import Dict, List, Optional

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
    services for different aspects of the scraping process.
    """

    def __init__(self) -> None:
        """Initialize the Orchestrator service."""
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

        Args:
            config_path: Path to configuration file
            headless: Override headless mode setting
            log_level: Override log level setting
            save_structure: Save parsed structure to debug directory
            save_html: Save raw HTML to debug directory
            debug: Enable debug mode with additional logging and saves
            max_expand_attempts: Maximum menu expansion attempts
            force: Overwrite existing output files
            test_item_id: Process only specific item ID (deprecated)
            max_items: Maximum number of items to process
            resume_info: Show resume information and exit
            structure_filename: Custom structure filename
            html_filename: Custom HTML filename
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

            # Setup logging
            effective_log_level = log_level or config.log_level
            if debug:
                effective_log_level = "DEBUG"
                save_structure = True
                save_html = True
                logging.info("Debug mode enabled - forcing structure and HTML saves.")

            self.config_service.setup_logging(effective_log_level)

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
            logging.warning("--- User interrupted execution ---")
        except Exception as e:
            logging.exception(f"--- An unexpected error occurred: {e} ---")
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
        """Handle sidebar structure loading or parsing."""
        structure_filepath = self.parsing_service.get_structure_filepath(config_values)

        # Try to load existing structure first
        sidebar_structure = self.parsing_service.load_existing_structure(structure_filepath)

        if not sidebar_structure or force:
            # Need to parse live
            sidebar_structure = await self._perform_live_parsing(
                config, config_values, save_structure, save_html,
                structure_filename, html_filename, structure_filepath
            )

        # Handle resume check
        await self._handle_resume_check(sidebar_structure, config_values, resume_info, force)

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
        """Perform live parsing of sidebar structure."""
        # Initialize driver and navigate
        await self.navigation_service.initialize_driver(config)
        sidebar_html = await self.navigation_service.navigate_and_wait(config, config_values)

        # Save debug files if requested
        if save_html:
            await self.parsing_service.save_debug_html(sidebar_html, config_values, html_filename)

        # Parse and save structure
        sidebar_structure = await self.parsing_service.parse_sidebar_structure(sidebar_html)

        if save_structure:
            await self.parsing_service.save_debug_structure(sidebar_structure, config_values, structure_filename)

        self.storage_service.save_structure_to_output(sidebar_structure, structure_filepath)
        return sidebar_structure

    async def _handle_resume_check(self, sidebar_structure: SidebarStructure, config_values: Dict, resume_info: bool, force: bool) -> None:
        """Handle resume information display."""
        valid_items = self.parsing_service._get_valid_items(sidebar_structure)
        self.progress_service.set_total_items(len(valid_items))

        if resume_info:
            existing_items, items_needing_processing = self.storage_service.check_existing_files(
                valid_items, config_values["base_output_dir"]
            )
            self.storage_service.display_resume_info(
                valid_items, existing_items, items_needing_processing, config_values["base_output_dir"]
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
        """Process items from the sidebar structure."""
        valid_items = self.parsing_service._get_valid_items(sidebar_structure)

        # Filter items for processing
        items_to_process = self.parsing_service.filter_items_for_processing(
            valid_items, max_items, test_item_id
        )

        # Handle resume logic if not forcing
        if not force:
            existing_items, items_needing_processing = self.storage_service.check_existing_files(
                items_to_process, config_values["base_output_dir"]
            )
            items_to_process = items_needing_processing
            self.progress_service.skipped_count = len(existing_items)

        # Process items with progress tracking
        await self._process_items_with_progress(items_to_process, config_values)

        # Log final summary
        await self.progress_service.log_final_summary()

    async def _process_items_with_progress(
        self,
        items_to_process: List[Dict],
        config_values: Dict,
    ) -> None:
        """Process items with progress bar."""
        if not items_to_process:
            logging.info("No items to process.")
            return

        progress = self.progress_service.create_progress_bar(len(items_to_process))

        with progress:
            task_id = progress.add_task("Processing items...", total=len(items_to_process))

            for item in items_to_process:
                await self._process_single_item(item, config_values, progress, task_id)

    async def _process_single_item(
        self,
        item,
        config_values: Dict,
        progress,
        task_id: int,
    ) -> None:
        """Process a single item."""
        # Handle both SidebarItem models and dict items for backward compatibility
        if hasattr(item, 'id'):
            item_id = item.id
            item_text = item.text
            item_type = item.type
        else:
            item_id = item.get("id")
            item_text = item.get("text", "Unknown Item")
            item_type = item.get("type", "item")

        current_item_desc = f"{item_type.capitalize()}: '{item_text}' (ID: {item_id})"
        progress.update(task_id, description=f"Processing {current_item_desc}")

        try:
            if not item_id:
                logging.warning(f"Skipping item {item_text} - Missing ID.")
                self.progress_service.increment_skipped()
                progress.update(task_id, advance=1)
                return

            logging.info(f"Processing {current_item_desc}")

            # Expand menus and click item
            await self.navigation_service.expand_menu_for_item(item, config_values)
            await self.navigation_service.click_item_and_wait(item, config_values)

            # Save debug content if needed
            await self.storage_service.save_debug_page_content(
                item_id, self.navigation_service.get_driver(), config_values
            )

            # Extract and save content
            success = await self.storage_service.save_content_for_item(
                item, self.navigation_service.get_driver(), config_values
            )

            if success:
                self.progress_service.increment_processed()
                progress.update(task_id, advance=1, description=f"Saved {item_text}")
            else:
                self.progress_service.increment_no_content()
                progress.update(task_id, advance=1, description=f"No content for {item_text}")

        except Exception as item_error:
            logging.error(f"Error processing item {item_text} (ID: {item_id}): {item_error}")
            self.progress_service.increment_errors()
            progress.update(task_id, advance=1, description=f"Error: {item_text}")

    async def _cleanup(self) -> None:
        """Cleanup resources."""
        await self.navigation_service.cleanup(self.config_service.get_config())
