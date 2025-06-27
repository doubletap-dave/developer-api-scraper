"""Progress service for Wyrm application.

This service handles progress tracking, item counting and statistics,
final summary logging, and user feedback coordination.
"""

import logging
from typing import Dict, List

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)


class ProgressService:
    """Service for handling progress tracking and reporting."""

    def __init__(self) -> None:
        """Initialize the Progress service."""
        self.processed_count: int = 0
        self.skipped_count: int = 0
        self.error_count: int = 0
        self.no_content_count: int = 0
        self.total_items_in_structure: int = 0

    def set_total_items(self, count: int) -> None:
        """Set the total number of items in structure.

        Args:
            count: Total number of items found in structure
        """
        self.total_items_in_structure = count

    def increment_processed(self) -> None:
        """Increment the processed items counter."""
        self.processed_count += 1

    def increment_skipped(self) -> None:
        """Increment the skipped items counter."""
        self.skipped_count += 1

    def increment_errors(self) -> None:
        """Increment the error counter."""
        self.error_count += 1

    def increment_no_content(self) -> None:
        """Increment the no content counter."""
        self.no_content_count += 1

    def create_progress_bar(self, total_items: int) -> Progress:
        """Create and return a Rich progress bar.

        Args:
            total_items: Total number of items to process

        Returns:
            Configured Progress instance
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            expand=True,
        )

    def get_stats(self) -> Dict[str, int]:
        """Get current processing statistics.

        Returns:
            Dictionary containing processing statistics
        """
        return {
            "processed": self.processed_count,
            "skipped": self.skipped_count,
            "errors": self.error_count,
            "no_content": self.no_content_count,
            "total_in_structure": self.total_items_in_structure,
        }

    async def log_final_summary(self) -> None:
        """Log final processing summary."""
        logging.info("--- Wyrm Finished ---")
        logging.info(f"Processed: {self.processed_count}")
        logging.info(f"Skipped (existing/no ID): {self.skipped_count}")
        logging.info(f"Errors: {self.error_count}")
        logging.info(f"Items with no content extracted: {self.no_content_count}")
        logging.info(
            f"Total valid items found in structure: {self.total_items_in_structure}"
        )

        if self.skipped_count > 0:
            logging.info(f"💡 Resume tip: {self.skipped_count} files were skipped.")
            logging.info("💡 Use --resume-info to see detailed resume status")
            logging.info("💡 Use --force to re-process existing files")

    def reset_counters(self) -> None:
        """Reset all counters to zero."""
        self.processed_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.no_content_count = 0
        self.total_items_in_structure = 0
