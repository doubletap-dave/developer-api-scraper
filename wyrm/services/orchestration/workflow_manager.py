"""Workflow management for Wyrm orchestration.

This module handles the main scraping workflow coordination,
including configuration loading, CLI overrides, and high-level flow control.
"""

import sys
from typing import Dict, Optional

import structlog

from wyrm.models.config import AppConfig
from wyrm.models.scrape import SidebarStructure


class WorkflowManager:
    """Manages the main scraping workflow execution.
    
    Coordinates configuration loading, CLI overrides, service initialization,
    and the high-level flow of the scraping process.
    """
    
    def __init__(self, orchestrator):
        """Initialize workflow manager with orchestrator reference.
        
        Args:
            orchestrator: Reference to the main Orchestrator instance.
        """
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger(__name__)
    
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
            await self._run_workflow_with_error_handling(
                config_path, headless, log_level, max_expand_attempts, force_full_expansion,
                debug, save_structure, save_html, structure_filename, html_filename,
                resume_info, force, test_item_id, max_items
            )
        except KeyboardInterrupt:
            self.logger.warning("User interrupted execution")
            raise
        except Exception as e:
            self.logger.exception("An unexpected error occurred", error=str(e))
            raise
        finally:
            await self.orchestrator._cleanup()
    
    def _setup_configuration(self, config_path, headless, log_level, max_expand_attempts, force_full_expansion):
        """Setup and load configuration with CLI overrides."""
        # Load configuration
        config = self.orchestrator.config_service.load_config(config_path)

        # Merge CLI overrides
        cli_args = {
            "headless": headless,
            "log_level": log_level,
            "max_expand_attempts": max_expand_attempts,
            "force_full_expansion": force_full_expansion,
        }
        config = self.orchestrator.config_service.merge_cli_overrides(config, cli_args)
        
        # Get configuration values
        config_values = self.orchestrator.config_service.extract_configuration_values(config)
        
        return config, config_values
    
    def _handle_debug_mode(self, debug, save_structure, save_html):
        """Handle debug mode activation and related settings."""
        if debug:
            save_structure = True
            save_html = True
            self.logger.info(
                "Debug mode enabled - forcing structure and HTML saves"
            )
        return save_structure, save_html
    
    def _initialize_workflow_services(self, config, config_values):
        """Initialize orchestrator services and setup directories."""
        # Store config for cleanup
        self.orchestrator._config = config
        
        # Initialize endpoint-aware services
        self.orchestrator._initialize_endpoint_aware_services(config)

        # Setup directories
        self.orchestrator.config_service.setup_directories(config_values)
    
    async def _execute_workflow(self, config, config_values, save_structure, save_html,
                               structure_filename, html_filename, resume_info, force,
                               test_item_id, max_items):
        """Execute the main workflow of structure handling and item processing."""
        # Handle sidebar structure loading/parsing
        sidebar_structure, from_cache = await self.orchestrator.structure_handler.handle_sidebar_structure(
            config, config_values, save_structure, save_html,
            structure_filename, html_filename, resume_info, force
        )

        # Process items from structure
        await self.orchestrator.item_processor.process_items_from_structure(
            sidebar_structure, config_values, force,
            test_item_id, max_items, resume_info, from_cache
        )
    
    async def _run_workflow_with_error_handling(
        self, config_path, headless, log_level, max_expand_attempts, force_full_expansion,
        debug, save_structure, save_html, structure_filename, html_filename,
        resume_info, force, test_item_id, max_items
    ):
        """Run workflow with proper setup and coordination."""
        # Setup configuration
        config, config_values = self._setup_configuration(
            config_path, headless, log_level, max_expand_attempts, force_full_expansion
        )
        
        # Handle debug mode
        save_structure, save_html = self._handle_debug_mode(debug, save_structure, save_html)
        
        # Initialize services and directories
        self._initialize_workflow_services(config, config_values)
        
        # Execute main workflow
        await self._execute_workflow(
            config, config_values, save_structure, save_html,
            structure_filename, html_filename, resume_info, force,
            test_item_id, max_items
        )
