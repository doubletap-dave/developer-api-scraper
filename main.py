"""Wyrm - Developer API Documentation Scraper.

Thin entrypoint that uses Typer for CLI and delegates to the Orchestrator service.
"""

import asyncio
import signal
import sys
from typing import Optional

import typer
from rich.console import Console

from wyrm.services import Orchestrator
from wyrm.services.logging_service import LoggingService

console = Console()

# Global variable to track the orchestrator for cleanup
_orchestrator = None


def main(
    config: str = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to YAML configuration file",
    ),
    headless: Optional[bool] = typer.Option(
        None,
        "--headless/--no-headless",
        help="Override browser headless mode setting",
    ),
    log_level: Optional[str] = typer.Option(
        None,
        "--log-level",
        "-l",
        help="Set logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    ),
    save_structure: Optional[str] = typer.Option(
        None,
        "--save-structure",
        help="Save parsed sidebar structure to debug directory",
    ),
    save_html: Optional[str] = typer.Option(
        None,
        "--save-html",
        help="Save raw sidebar HTML to debug directory",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode: DEBUG logs, save files, visible browser",
    ),
    max_expand_attempts: Optional[int] = typer.Option(
        None,
        "--max-expand-attempts",
        help="Maximum menu expansion attempts (for testing)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing output files",
    ),
    test_item_id: Optional[str] = typer.Option(
        None,
        "--test-item-id",
        help="[DEPRECATED] Process only specified item ID (use --max-items=1)",
    ),
    max_items: Optional[int] = typer.Option(
        None,
        "--max-items",
        help="Maximum number of items to process (for testing)",
    ),
    resume_info: bool = typer.Option(
        False,
        "--resume-info",
        help="Show resume information and exit (no processing)",
    ),
    force_full_expansion: bool = typer.Option(
        False,
        "--force-full-expansion",
        help="Force full menu expansion even when using cached "
             "structure (useful for debugging cache issues)",
    ),
) -> None:
    """Scrape developer API documentation with intelligent navigation.

    Intelligently navigates documentation sites, expands menus, and extracts
    content into organized markdown files.

    Features: Resume capability, debug mode, progress tracking, error handling.
    """
    # Setup logging first (before any other operations)
    logging_service = LoggingService()
    effective_log_level = log_level if log_level else ("DEBUG" if debug else "INFO")
    logging_service.setup_logging(log_level=effective_log_level)

    # Convert save flags to boolean
    save_structure_flag = save_structure is not None
    save_html_flag = save_html is not None

    # Create orchestrator and run workflow
    orchestrator = Orchestrator()

    global _orchestrator
    _orchestrator = orchestrator

    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, graceful_exit)

    try:
        asyncio.run(
            orchestrator.run_scraping_workflow(
                config_path=config,
                headless=headless,
                log_level=log_level,
                save_structure=save_structure_flag,
                save_html=save_html_flag,
                debug=debug,
                max_expand_attempts=max_expand_attempts,
                force=force,
                test_item_id=test_item_id,
                max_items=max_items,
                resume_info=resume_info,
                structure_filename=save_structure,
                html_filename=save_html,
                force_full_expansion=force_full_expansion,
            )
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def graceful_exit(signum, frame):
    """Handle graceful shutdown on SIGINT (Ctrl+C)."""
    console.print(
        "\n[yellow]Received interrupt signal. Gracefully shutting "
        "down...[/yellow]"
    )

    try:
        if _orchestrator:
            # Use asyncio to run cleanup if event loop is available
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, schedule cleanup and exit
                    loop.create_task(_orchestrator._cleanup())
                else:
                    # If loop is not running, run cleanup directly
                    asyncio.run(_orchestrator._cleanup())
            except RuntimeError:
                # No event loop available, run cleanup in new loop
                asyncio.run(_orchestrator._cleanup())

        console.print("[green]Cleanup completed successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Error during cleanup: {e}[/red]")
    finally:
        console.print("[yellow]Exiting application.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    typer.run(main)
