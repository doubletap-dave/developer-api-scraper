"""Progress tracking service for Wyrm application.

This service handles progress reporting, statistics tracking, and user feedback
during the scraping process using Rich progress bars and logging.
"""

import logging
import structlog
from contextlib import contextmanager
from typing import Generator

from rich.console import Console
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
        self.logger = structlog.get_logger(__name__)
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
        self.logger.info("Progress tracking initialized", total_items=total)

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

        self.logger.info("=" * 60)
        self.logger.info("FINAL PROCESSING SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(
            "Processing completed",
            total_items=self.total_items,
            processed_successfully=self.processed_count,
            skipped_existing=self.skipped_count,
            errors=self.error_count,
            no_content=self.no_content_count,
            success_rate=f"{success_rate:.1f}%"
        )
        self.logger.info("=" * 60)

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
        self._console = Console()

    @contextmanager
    def _suppress_console_logging(self) -> Generator[None, None, None]:
        """Context manager to temporarily suppress console logging during progress display.

        This prevents logging output from interfering with the Rich progress bar display
        by temporarily removing the console handler from the root logger.
        """
        # Get the root logger
        root_logger = logging.getLogger()

        # Find and temporarily remove console handlers
        console_handlers = []
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and hasattr(handler, 'stream'):
                if handler.stream.name in ('<stdout>', '<stderr>'):
                    console_handlers.append(handler)
                    root_logger.removeHandler(handler)

        try:
            yield
        finally:
            # Restore console handlers
            for handler in console_handlers:
                root_logger.addHandler(handler)
