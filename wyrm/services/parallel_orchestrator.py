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
from wyrm.services.parallel_worker import ParallelWorker
from wyrm.services.progress_service import ProgressService


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
            return await self._fallback_to_sequential(items, config, config_values)

        try:
            return await self._execute_parallel_processing(items, config, config_values)
        except Exception as e:
            return await self._handle_parallel_failure(e, items, config, config_values)

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

                tasks = self._create_worker_tasks(
                    items, config, config_values, semaphore, task_delay, progress, task_id
                )
                
                return await self._collect_task_results(tasks)

    def _create_worker_tasks(
        self, items: List[SidebarItem], config, config_values: Dict,
        semaphore: asyncio.Semaphore, task_delay: float, progress, task_id: int
    ) -> List[asyncio.Task]:
        """Create worker tasks for parallel processing."""
        tasks = []
        for i, item in enumerate(items):
            start_delay = i * task_delay
            task = asyncio.create_task(
                self._delayed_worker_start(
                    i, item, config, config_values,
                    semaphore, start_delay, progress, task_id
                )
            )
            tasks.append(task)
        return tasks

    async def _collect_task_results(self, tasks: List[asyncio.Task]) -> Dict[str, int]:
        """Collect and process results from worker tasks."""
        results = {'processed': 0, 'failed': 0, 'skipped': 0}
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(task_results):
            if isinstance(result, Exception):
                self.logger.error(
                    "Worker task failed with exception",
                    worker_id=i,
                    error=str(result)
                )
                results['failed'] += 1
            elif result is True:
                results['processed'] += 1
            elif result is False:
                results['failed'] += 1
            else:
                results['skipped'] += 1

        self.logger.info(
            "Parallel processing completed",
            processed=results['processed'],
            failed=results['failed'],
            skipped=results['skipped']
        )
        return results

    async def _handle_parallel_failure(
        self, error: Exception, items: List[SidebarItem], config, config_values: Dict
    ) -> Dict[str, int]:
        """Handle parallel processing failure and attempt fallback."""
        self.logger.error(
            "Parallel processing failed, attempting fallback",
            error=str(error)
        )

        max_retries = config_values.get('max_parallel_retries', 2)
        if max_retries > 0:
            self.logger.info("Falling back to sequential processing")
            return await self._fallback_to_sequential(items, config, config_values)
        else:
            raise

    async def _delayed_worker_start(
        self,
        worker_id: int,
        item: SidebarItem,
        config,
        config_values: Dict,
        semaphore: asyncio.Semaphore,
        delay: float,
        progress,
        task_id: int,
    ) -> bool:
        """Start a worker with a delay to stagger requests.

        Args:
            worker_id: Unique ID for this worker
            item: Item to process
            config: Application configuration
            config_values: Configuration values
            semaphore: Concurrency control semaphore
            delay: Delay before starting worker
            progress: Progress display instance
            task_id: Progress task ID

        Returns:
            bool: True if successful, False otherwise
        """
        # Wait for the specified delay before starting
        if delay > 0:
            await asyncio.sleep(delay)

        # Update progress with current item
        progress.update(task_id, description=f"Processing: {item.text}")

        # Create and run worker
        worker = ParallelWorker(worker_id)
        success = await worker.process_item(item, config, config_values, semaphore)

        # Update progress
        progress.advance(task_id)

        return success

    async def _fallback_to_sequential(
        self,
        items: List[SidebarItem],
        config,
        config_values: Dict,
    ) -> Dict[str, int]:
        """Fallback to sequential processing when parallel processing fails.

        This provides a safety net when parallel processing encounters issues.
        It processes items one at a time using a simplified approach.

        Args:
            items: Items to process
            config: Application configuration
            config_values: Configuration values

        Returns:
            Dict with processing statistics
        """
        self.logger.info(
            "Using sequential fallback processing",
            total_items=len(items)
        )

        results = {
            'processed': 0,
            'failed': 0,
            'skipped': 0
        }

        # Create progress display
        progress = self.progress_service.create_progress_display()

        with self.progress_service._suppress_console_logging():
            with progress:
                task_id = progress.add_task(
                    "Processing items (sequential fallback)...",
                    total=len(items)
                )

                # Process items sequentially
                for i, item in enumerate(items):
                    progress.update(task_id, description=f"Processing: {item.text}")

                    try:
                        # Create worker for this single item
                        worker = ParallelWorker(f"sequential-{i}")
                        # Use a large semaphore (essentially no limit for sequential)
                        sequential_semaphore = asyncio.Semaphore(1)

                        success = await worker.process_item(
                            item, config, config_values, sequential_semaphore
                        )

                        if success:
                            results['processed'] += 1
                        else:
                            results['failed'] += 1

                    except Exception as e:
                        self.logger.error(
                            "Sequential fallback failed for item",
                            item_text=item.text,
                            error=str(e)
                        )
                        results['failed'] += 1

                    progress.advance(task_id)

        self.logger.info(
            "Sequential fallback completed",
            processed=results['processed'],
            failed=results['failed'],
            skipped=results['skipped']
        )

        return results

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
