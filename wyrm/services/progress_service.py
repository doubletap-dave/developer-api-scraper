"""Progress tracking service for Wyrm application.

This service handles progress reporting, statistics tracking, and user feedback
during the scraping process using Rich progress bars and logging.
"""

import logging

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)


class ProgressService:
    """Service for tracking and displaying progress during scraping operations.

    Provides comprehensive progress tracking with Rich-based progress bars,
    statistics collection, and logging integration. Tracks various metrics
    including processed items, skipped items, errors, and timing information.

    Attributes:
        total_items: Total number of items to process.
        processed_count: Number of successfully processed items.
        skipped_count: Number of skipped items.
        error_count: Number of items that failed processing.
        no_content_count: Number of items with no extractable content.
    """

    def __init__(self) -> None:
        """Initialize the Progress service.

        Sets up initial counters and state for progress tracking.
        All counters start at zero and are updated during processing.

        Args:
            None

        Returns:
            None
        """
        self.total_items = 0
        self.processed_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.no_content_count = 0

    def set_total_items(self, total: int) -> None:
        """Set the total number of items to be processed.

        Establishes the baseline for progress calculations and reporting.
        Should be called before processing begins.

        Args:
            total: Total number of items that will be processed.

        Returns:
            None

        Raises:
            ValueError: If total is negative.
        """
        if total < 0:
            raise ValueError("Total items cannot be negative")
        self.total_items = total
        logging.info(f"Progress tracking initialized for {total} total items")

    def create_progress_display(self) -> Progress:
        """Create a Rich progress display with comprehensive columns.

        Sets up a progress bar with multiple information columns including
        task description, progress bar, completion ratio, percentage,
        elapsed time, and estimated remaining time.

        Args:
            None

        Returns:
            Progress: Configured Rich Progress instance ready for use.
        """
        return Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            expand=True,
        )

    def increment_processed(self) -> None:
        """Increment the count of successfully processed items.

        Updates internal statistics for items that were successfully
        processed and had their content extracted and saved.

        Args:
            None

        Returns:
            None
        """
        self.processed_count += 1

    def increment_skipped(self) -> None:
        """Increment the count of skipped items.

        Updates internal statistics for items that were skipped,
        typically because their output files already existed.

        Args:
            None

        Returns:
            None
        """
        self.skipped_count += 1

    def increment_errors(self) -> None:
        """Increment the count of items that encountered errors.

        Updates internal statistics for items that failed processing
        due to errors during navigation, extraction, or saving.

        Args:
            None

        Returns:
            None
        """
        self.error_count += 1

    def increment_no_content(self) -> None:
        """Increment the count of items with no extractable content.

        Updates internal statistics for items that were processed
        successfully but contained no extractable content.

        Args:
            None

        Returns:
            None
        """
        self.no_content_count += 1

    async def log_final_summary(self) -> None:
        """Log a comprehensive summary of processing results.

        Outputs detailed statistics about the scraping session including
        total items, success rates, and breakdown of different outcomes.
        Provides percentage calculations for easy interpretation.

        Args:
            None

        Returns:
            None
        """
        total_attempted = (
            self.processed_count + self.skipped_count +
            self.error_count + self.no_content_count
        )

        success_rate = (
            self.processed_count / total_attempted * 100
            if total_attempted > 0 else 0
        )

        logging.info("=" * 60)
        logging.info("FINAL PROCESSING SUMMARY")
        logging.info("=" * 60)
        logging.info(f"Total items found: {self.total_items}")
        logging.info(f"Items processed successfully: {self.processed_count}")
        logging.info(f"Items skipped (already exist): {self.skipped_count}")
        logging.info(f"Items with errors: {self.error_count}")
        logging.info(f"Items with no content: {self.no_content_count}")
        logging.info(f"Success rate: {success_rate:.1f}%")
        logging.info("=" * 60)

    def reset_counters(self) -> None:
        """Reset all counters to zero.

        Useful for reusing the same service instance across multiple
        scraping sessions or for testing purposes.

        Args:
            None

        Returns:
            None
        """
        self.processed_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.no_content_count = 0
        self.total_items = 0
