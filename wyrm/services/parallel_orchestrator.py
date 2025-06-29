"""Parallel orchestrator service for managing concurrent content extraction.

This service implements the hybrid approach to parallel processing:
1. Uses single browser for discovery and menu expansion (existing approach)
2. Switches to parallel workers for content extraction
3. Provides graceful fallback to sequential processing if parallel fails
"""

import asyncio
from typing import Dict, List

import structlog

from wyrm.models.scrape import SidebarItem
from wyrm.services.progress_service import ProgressService
from .orchestration.task_manager import TaskManager
from .orchestration.error_manager import ErrorManager


class ParallelOrchestrator:
    """Orchestrator for managing parallel content extraction workers.

    This service implements a hybrid approach:
    - Discovery phase: Uses existing single-browser approach for menu expansion
    - Extraction phase: Uses multiple parallel workers for content extraction
    - Fallback: Can gracefully degrade to sequential processing if needed
    """

    def __init__(self, progress_service: ProgressService) -> None:
        """Initialize the parallel orchestrator.

        Args:
            progress_service: Service for progress tracking and display
        """
        self.logger = structlog.get_logger(__name__)
        self.progress_service = progress_service
        self.task_manager = TaskManager()
        self.error_manager = ErrorManager(progress_service)

    async def process_items_parallel(
        self,
        items: List[SidebarItem],
        config,
        config_values: Dict,
    ) -> Dict[str, int]:
        """Process items using parallel workers.

        This is the main entry point for parallel processing. It:
        1. Creates a semaphore to limit concurrency
        2. Creates worker tasks for each item
        3. Runs tasks concurrently with progress tracking
        4. Handles failures and provides fallback options

        Args:
            items: List of SidebarItems to process
            config: Application configuration
            config_values: Extracted configuration values

        Returns:
            Dict with processing statistics:
            {
                'processed': int,
                'failed': int,
                'skipped': int
            }
        """
        if not config_values.get('concurrency_enabled', True):
            self.logger.info("Parallel processing disabled, using sequential fallback")
            return await self.error_manager.fallback_to_sequential(items, config, config_values)

        try:
            return await self._execute_parallel_processing(items, config, config_values)
        except Exception as e:
            return await self.error_manager.handle_parallel_failure(e, items, config, config_values)

    async def _execute_parallel_processing(
        self, items: List[SidebarItem], config, config_values: Dict
    ) -> Dict[str, int]:
        """Execute the parallel processing workflow."""
        max_workers = config_values.get('max_concurrent_tasks', 3)
        task_delay = config_values.get('task_start_delay', 0.5)

        self.logger.info(
            "Starting parallel content extraction",
            total_items=len(items),
            max_concurrent_workers=max_workers,
            task_start_delay=task_delay
        )

        semaphore = asyncio.Semaphore(max_workers)
        progress = self.progress_service.create_progress_display()

        with self.progress_service._suppress_console_logging():
            with progress:
                task_id = progress.add_task(
                    "Processing items (parallel)...",
                    total=len(items)
                )

                tasks = self.task_manager.create_worker_tasks(
                    items, config, config_values, semaphore, task_delay, progress, task_id
                )
                
                return await self.error_manager.collect_task_results(tasks)


    async def estimate_processing_time(
        self,
        num_items: int,
        config_values: Dict,
    ) -> Dict[str, float]:
        """Estimate processing time for parallel vs sequential approaches.

        Args:
            num_items: Number of items to process
            config_values: Configuration values

        Returns:
            Dict with time estimates in seconds:
            {
                'sequential_estimate': float,
                'parallel_estimate': float,
                'parallel_speedup': float
            }
        """
        # Rough estimates based on typical processing times
        avg_item_time = 8.0  # seconds per item (based on current performance)

        sequential_time = num_items * avg_item_time

        max_workers = config_values.get('max_concurrent_tasks', 3)
        task_delay = config_values.get('task_start_delay', 0.5)

        # Parallel time estimate: divide by workers, add startup delays
        parallel_time = (num_items / max_workers) * avg_item_time
        parallel_time += num_items * task_delay  # Staggered starts
        parallel_time += max_workers * 10.0      # WebDriver startup overhead

        speedup = sequential_time / parallel_time if parallel_time > 0 else 1.0

        return {
            'sequential_estimate': sequential_time,
            'parallel_estimate': parallel_time,
            'parallel_speedup': speedup
        }
