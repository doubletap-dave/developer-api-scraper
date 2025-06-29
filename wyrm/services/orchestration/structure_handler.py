"""Structure handling for Wyrm orchestration.

This module handles the logic for loading or parsing the sidebar structure,
including validation, caching, and live extraction.
"""

import sys
from typing import Dict, Optional

import structlog

from wyrm.models.config import AppConfig
from wyrm.models.scrape import SidebarStructure, SidebarItem


class StructureHandler:
    """Handles sidebar structure loading and parsing for Wyrm."""

    def __init__(self, orchestrator):
        """Initialize structure handler with orchestrator reference.

        Args:
            orchestrator: Reference to the main Orchestrator instance.
        """
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger(__name__)

    async def handle_sidebar_structure(
        self,
        config: AppConfig,
        config_values: Dict,
        save_structure: bool,
        save_html: bool,
        structure_filename: Optional[str],
        html_filename: Optional[str],
        resume_info: bool,
        force: bool,
    ) -> tuple[SidebarStructure, bool]:
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
        if save_structure:
            structure_filepath = self.orchestrator.parsing_service.get_structure_filepath(
                config_values)
        else:
            structure_filepath = "logs/sidebar_structure.json"

        # Load existing structure or perform live parsing
        sidebar_structure, structure_is_valid = self.load_structure_from_file(
            structure_filepath, force
        )

        if not structure_is_valid:
            # Perform live parsing
            sidebar_structure = await self.perform_live_parsing(
                config, config_values, save_structure, save_html,
                structure_filename, html_filename, structure_filepath
            )

        # Handle resume check
        await self.handle_resume_check(
            sidebar_structure, config_values, resume_info, force
        )

        return sidebar_structure, not structure_is_valid

    async def perform_live_parsing(
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
        await self.orchestrator.navigation_service.initialize_driver(config)
        self.logger.info("Navigating to target URL and waiting for sidebar...")
        sidebar_html = await self.orchestrator.navigation_service.navigate_and_wait(
            config, config_values
        )

        self.logger.info("Performing menu expansion to reveal all items...")
        await self.orchestrator.navigation_service.expand_all_menus_comprehensive()
        self.orchestrator._full_expansion_done = True

        # Get the updated sidebar HTML after expansion
        expanded_sidebar_html = await self.orchestrator.navigation_service.get_sidebar_html()

        # Use the expanded HTML for parsing
        sidebar_html = expanded_sidebar_html

        # Save debug files if requested
        if save_html:
            await self.orchestrator.parsing_service.save_debug_html(
                sidebar_html, config_values, html_filename
            )

        # Parse and save structure
        sidebar_structure = await self.orchestrator.parsing_service.parse_sidebar_structure(
            sidebar_html
        )

        # Save structure to the determined filepath
        self.orchestrator.storage_service.save_structure_to_output(
            sidebar_structure, structure_filepath
        )
        return sidebar_structure

    async def handle_resume_check(
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
        valid_items = self.orchestrator.parsing_service._get_valid_items(sidebar_structure)
        self.orchestrator.progress_service.set_total_items(len(valid_items))

        if resume_info:
            existing_items, items_needing_processing = (
                self.orchestrator.storage_service.check_existing_files(
                    valid_items, config_values["base_output_dir"]
                )
            )
            self.orchestrator.storage_service.display_resume_info(
                valid_items,
                existing_items,
                items_needing_processing,
                config_values["base_output_dir"]
            )
            sys.exit(0)

    def load_structure_from_file(self, structure_filepath, force) -> (Optional[SidebarStructure], bool):
        """Load sidebar structure from file and validate.

        Args:
            structure_filepath: File path to load structure from.
            force: Whether to force re-parsing if structure is found.

        Returns:
            Tuple of (SidebarStructure, is_valid)
        """
        try:
            sidebar_structure, from_cache = self.orchestrator.parsing_service.load_existing_structure(
                structure_filepath
            )

            if sidebar_structure and not force:
                # Check structure validity
                valid_items = SidebarStructure(
                    structured_data=sidebar_structure.get('structured_data', []),
                    items=[SidebarItem(**item) for item in sidebar_structure.get('items', [])]
                ).valid_items
                if len(valid_items) >= 10 and len(valid_items) / len(sidebar_structure.get('items', [])) > 0.1:
                    return sidebar_structure, True
        except Exception as e:
            self.logger.warning(
                "Failed to validate existing structure, will re-parse",
                error=str(e)
            )

        return None, False

