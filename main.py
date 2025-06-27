"""Wyrm - Developer API Documentation Scraper.

Thin entrypoint that uses Typer for CLI and delegates to the Orchestrator service.
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from wyrm.services import Orchestrator

console = Console()


def main(
    config: str = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to the configuration file",
    ),
    headless: Optional[bool] = typer.Option(
        None,
        "--headless/--no-headless",
        help="Run in headless mode (overrides config)",
    ),
    log_level: Optional[str] = typer.Option(
        None,
        "--log-level",
        "-l",
        help="Set logging level (overrides config)",
    ),
    save_structure: Optional[str] = typer.Option(
        None,
        "--save-structure",
        help="Save parsed sidebar structure to debug dir. Optionally specify filename.",
    ),
    save_html: Optional[str] = typer.Option(
        None,
        "--save-html",
        help="Save raw sidebar HTML to debug dir. Optionally specify filename.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug: DEBUG logs, save structure/HTML, force non-headless.",
    ),
    max_expand_attempts: Optional[int] = typer.Option(
        None,
        "--max-expand-attempts",
        help="Max menu expansion clicks (for testing/limiting). Overridden by --debug.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing output files.",
    ),
    test_item_id: Optional[str] = typer.Option(
        None,
        "--test-item-id",
        help="DEPRECATED (use --max-items=1). Run logic for only this item ID.",
    ),
    max_items: Optional[int] = typer.Option(
        None,
        "--max-items",
        help="Max items to process from sidebar structure (for testing).",
    ),
    resume_info: bool = typer.Option(
        False,
        "--resume-info",
        help="Show resume information (what files exist vs need processing) and exit.",
    ),
) -> None:
    """Scrape developer API documentation with intelligent navigation.

    This command coordinates the entire scraping workflow from configuration
    loading to final content extraction and storage. It serves as a thin
    entrypoint that delegates all work to the Orchestrator service.

    Args:
        config: Path to the YAML configuration file containing scraping settings.
        headless: Override headless browser mode. If None, uses config setting.
        log_level: Override logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        save_structure: Save parsed sidebar structure to debug directory.
            If provided without value, uses default filename.
        save_html: Save raw sidebar HTML to debug directory.
            If provided without value, uses default filename.
        debug: Enable comprehensive debug mode with DEBUG logging,
            forced structure/HTML saves, and non-headless browser.
        max_expand_attempts: Maximum number of menu expansion attempts.
            Useful for testing or limiting execution time.
        force: Overwrite existing output files instead of skipping them.
        test_item_id: DEPRECATED. Process only the specified item ID.
            Use --max-items=1 instead for testing single items.
        max_items: Maximum number of items to process from sidebar structure.
            Useful for testing or partial runs.
        resume_info: Display resume information showing existing vs missing files,
            then exit without processing.

    Raises:
        typer.Exit: With code 1 if interrupted by user or on error.

    Returns:
        None: Function exits via typer.Exit or completes successfully.
    """
    # Convert save flags to boolean
    save_structure_flag = save_structure is not None
    save_html_flag = save_html is not None

    # Create orchestrator and run workflow
    orchestrator = Orchestrator()

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
            )
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    typer.run(main)
