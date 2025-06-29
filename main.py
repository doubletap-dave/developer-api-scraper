"""Wyrm - Developer API Documentation Scraper.

Thin entrypoint that uses Typer for CLI and delegates to the Orchestrator service.
"""

from typing import Optional

import typer
from rich.console import Console

from cli_helpers import execute_main_workflow

console = Console()


def _get_config_option():
    """Get config file option definition."""
    return typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to YAML configuration file",
    )

def _get_headless_option():
    """Get headless mode option definition."""
    return typer.Option(
        None,
        "--headless/--no-headless",
        help="Override browser headless mode setting",
    )

def _get_log_level_option():
    """Get log level option definition."""
    return typer.Option(
        None,
        "--log-level",
        "-l",
        help="Set logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )

def _get_save_structure_option():
    """Get save structure option definition."""
    return typer.Option(
        None,
        "--save-structure",
        help="Save parsed sidebar structure to debug directory",
    )

def _get_save_html_option():
    """Get save HTML option definition."""
    return typer.Option(
        None,
        "--save-html",
        help="Save raw sidebar HTML to debug directory",
    )

def _get_debug_option():
    """Get debug mode option definition."""
    return typer.Option(
        False,
        "--debug",
        help="Enable debug mode: DEBUG logs, save files, visible browser",
    )

def _get_max_expand_attempts_option():
    """Get max expand attempts option definition."""
    return typer.Option(
        None,
        "--max-expand-attempts",
        help="Maximum menu expansion attempts (for testing)",
    )

def _get_force_option():
    """Get force overwrite option definition."""
    return typer.Option(
        False,
        "--force",
        help="Overwrite existing output files",
    )

def _get_test_item_id_option():
    """Get test item ID option definition."""
    return typer.Option(
        None,
        "--test-item-id",
        help="[DEPRECATED] Process only specified item ID (use --max-items=1)",
    )

def _get_max_items_option():
    """Get max items option definition."""
    return typer.Option(
        None,
        "--max-items",
        help="Maximum number of items to process (for testing)",
    )

def _get_resume_info_option():
    """Get resume info option definition."""
    return typer.Option(
        False,
        "--resume-info",
        help="Show resume information and exit (no processing)",
    )

def _get_force_full_expansion_option():
    """Get force full expansion option definition."""
    return typer.Option(
        False,
        "--force-full-expansion",
        help="Force full menu expansion even when using cached "
             "structure (useful for debugging cache issues)",
    )


def main(
    config: str = _get_config_option(),
    headless: Optional[bool] = _get_headless_option(),
    log_level: Optional[str] = _get_log_level_option(),
    save_structure: Optional[str] = _get_save_structure_option(),
    save_html: Optional[str] = _get_save_html_option(),
    debug: bool = _get_debug_option(),
    max_expand_attempts: Optional[int] = _get_max_expand_attempts_option(),
    force: bool = _get_force_option(),
    test_item_id: Optional[str] = _get_test_item_id_option(),
    max_items: Optional[int] = _get_max_items_option(),
    resume_info: bool = _get_resume_info_option(),
    force_full_expansion: bool = _get_force_full_expansion_option(),
) -> None:
    """Scrape developer API documentation with intelligent navigation.

    Intelligently navigates documentation sites, expands menus, and extracts
    content into organized markdown files.

    Features: Resume capability, debug mode, progress tracking, error handling.
    """
    try:
        execute_main_workflow(
            config=config,
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
            force_full_expansion=force_full_expansion,
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)




if __name__ == "__main__":
    typer.run(main)
