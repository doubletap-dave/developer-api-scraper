"""CLI helper functions for main.py.

This module provides utility functions for setting up logging, processing
CLI parameters, and coordinating the orchestrator workflow.
"""

import asyncio
import signal
import sys
from typing import Optional, Dict, Any

from rich.console import Console
from wyrm.services.orchestration import Orchestrator
from wyrm.services.logging_service import LoggingService

console = Console()


class CLISetup:
    """Handles CLI setup and parameter processing."""

    @staticmethod
    def setup_logging(log_level: Optional[str], debug: bool) -> LoggingService:
        """Setup logging service with appropriate log level.
        
        Args:
            log_level: Explicit log level if provided
            debug: Debug mode flag
            
        Returns:
            Configured LoggingService instance
        """
        logging_service = LoggingService()
        effective_log_level = log_level if log_level else ("DEBUG" if debug else "INFO")
        logging_service.setup_logging(log_level=effective_log_level)
        return logging_service

    @staticmethod
    def process_cli_parameters(
        save_structure: Optional[str],
        save_html: Optional[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Process CLI parameters into workflow arguments.
        
        Args:
            save_structure: Save structure filename
            save_html: Save HTML filename
            **kwargs: Additional CLI parameters
            
        Returns:
            Dictionary of processed workflow arguments
        """
        # Convert save flags to boolean
        save_structure_flag = save_structure is not None
        save_html_flag = save_html is not None

        # Build workflow arguments
        workflow_args = {
            'save_structure': save_structure_flag,
            'save_html': save_html_flag,
            'structure_filename': save_structure,
            'html_filename': save_html,
        }
        
        # Add other parameters
        workflow_args.update(kwargs)
        
        return workflow_args


class OrchestratorRunner:
    """Handles orchestrator execution and cleanup."""

    def __init__(self):
        """Initialize runner."""
        self.orchestrator = None

    def setup_orchestrator(self) -> Orchestrator:
        """Create and setup orchestrator instance.
        
        Returns:
            Configured Orchestrator instance
        """
        self.orchestrator = Orchestrator()
        self._setup_signal_handlers()
        return self.orchestrator

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._graceful_exit)

    async def run_workflow(self, orchestrator: Orchestrator, **kwargs) -> None:
        """Run the scraping workflow with error handling.
        
        Args:
            orchestrator: Orchestrator instance
            **kwargs: Workflow arguments
        """
        try:
            await orchestrator.run_scraping_workflow(**kwargs)
        except KeyboardInterrupt:
            console.print("\\n[yellow]Operation cancelled by user.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise

    def _graceful_exit(self, signum, frame):
        """Handle graceful shutdown on SIGINT (Ctrl+C)."""
        console.print(
            "\\n[yellow]Received interrupt signal. Gracefully shutting "
            "down...[/yellow]"
        )

        try:
            if self.orchestrator:
                self._cleanup_orchestrator()
            console.print("[green]Cleanup completed successfully.[/green]")
        except Exception as e:
            console.print(f"[red]Error during cleanup: {e}[/red]")
        finally:
            console.print("[yellow]Exiting application.[/yellow]")
            sys.exit(0)

    def _cleanup_orchestrator(self) -> None:
        """Cleanup orchestrator resources."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, schedule cleanup and exit
                loop.create_task(self.orchestrator._cleanup())
            else:
                # If loop is not running, run cleanup directly
                asyncio.run(self.orchestrator._cleanup())
        except RuntimeError:
            # No event loop available, run cleanup in new loop
            asyncio.run(self.orchestrator._cleanup())


def execute_main_workflow(
    config: str,
    headless: Optional[bool],
    log_level: Optional[str],
    save_structure: Optional[str],
    save_html: Optional[str],
    debug: bool,
    max_expand_attempts: Optional[int],
    force: bool,
    test_item_id: Optional[str],
    max_items: Optional[int],
    resume_info: bool,
    force_full_expansion: bool,
) -> None:
    """Execute the main workflow with all CLI parameters.
    
    Args:
        config: Configuration file path
        headless: Browser headless mode override
        log_level: Logging level
        save_structure: Save structure filename
        save_html: Save HTML filename
        debug: Debug mode flag
        max_expand_attempts: Maximum expansion attempts
        force: Force overwrite flag
        test_item_id: Test item ID (deprecated)
        max_items: Maximum items to process
        resume_info: Resume info flag
        force_full_expansion: Force full expansion flag
    """
    # Setup logging
    CLISetup.setup_logging(log_level, debug)

    # Process CLI parameters
    workflow_args = CLISetup.process_cli_parameters(
        save_structure=save_structure,
        save_html=save_html,
        config_path=config,
        headless=headless,
        log_level=log_level,
        debug=debug,
        max_expand_attempts=max_expand_attempts,
        force=force,
        test_item_id=test_item_id,
        max_items=max_items,
        resume_info=resume_info,
        force_full_expansion=force_full_expansion,
    )

    # Setup and run orchestrator
    runner = OrchestratorRunner()
    orchestrator = runner.setup_orchestrator()
    
    asyncio.run(runner.run_workflow(orchestrator, **workflow_args))
