"""Worker coordination for parallel processing operations.

This module handles the coordination of parallel workers, task distribution,
and result collection for the ParallelOrchestrator.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import structlog
from wyrm.models.scrape import SidebarItem
from wyrm.models.config import AppConfig
from ..parallel_worker import ParallelWorker


class WorkerCoordinator:
    """Coordinates parallel workers for processing tasks."""

    def __init__(self, progress_service) -> None:
        """Initialize the worker coordinator.

        Args:
            progress_service: Progress tracking service
        """
        self.progress_service = progress_service
        self.logger = structlog.get_logger(__name__)

    async def execute_parallel_processing(
        self,
        sidebar_items: List[SidebarItem],
        app_config: AppConfig,
        config_values: Dict,
    ) -> Dict[str, int]:
        """Execute parallel processing of sidebar items.

        Args:
            sidebar_items: List of items to process
            app_config: Application configuration
            config_values: Extracted configuration values

        Returns:
            Dictionary containing processing results
        """
        max_workers = config_values.get('max_concurrent_tasks', 3)
        start_delay = config_values.get('task_start_delay', 0.5)

        self.logger.info(
            "Starting parallel processing",
            items=len(sidebar_items),
            max_workers=max_workers,
            start_delay=start_delay
        )

        # Initialize progress tracking
        self.progress_service.set_total_items(len(sidebar_items))
        progress_display = self.progress_service.create_progress_display()

        results = {"processed": 0, "failed": 0, "skipped": 0}

        with self.progress_service._suppress_console_logging():
            with progress_display:
                task_id = progress_display.add_task(
                    "Processing items (parallel)...",
                    total=len(sidebar_items)
                )

                # Process items in parallel using ThreadPoolExecutor
                results = await self._process_with_thread_pool(
                    sidebar_items, app_config, config_values, max_workers,
                    start_delay, progress_display, task_id
                )

        return results

    async def _process_with_thread_pool(
        self,
        sidebar_items: List[SidebarItem],
        app_config: AppConfig,
        config_values: Dict,
        max_workers: int,
        start_delay: float,
        progress_display,
        task_id,
    ) -> Dict[str, int]:
        """Process items using ThreadPoolExecutor.

        Args:
            sidebar_items: Items to process
            app_config: Application configuration
            config_values: Configuration values
            max_workers: Maximum number of worker threads
            start_delay: Delay between starting workers
            progress_display: Progress display instance
            task_id: Task ID for progress tracking

        Returns:
            Dictionary containing processing results
        """
        results = {"processed": 0, "failed": 0, "skipped": 0}

        # Create worker instances for each thread
        workers = [
            ParallelWorker(worker_id=i, app_config=app_config)
            for i in range(max_workers)
        ]

        # Distribute items among workers
        item_batches = self._distribute_items(sidebar_items, max_workers)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tasks with staggered start times
            futures = []
            for i, (worker, batch) in enumerate(zip(workers, item_batches)):
                if batch:  # Only submit if there are items to process
                    # Calculate start delay for this worker
                    worker_start_delay = i * start_delay

                    future = executor.submit(
                        self._process_worker_batch,
                        worker, batch, config_values, worker_start_delay
                    )
                    futures.append(future)

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    worker_results = future.result()
                    self._merge_results(results, worker_results)

                    # Update progress for completed batch
                    items_in_batch = worker_results.get('total_items', 0)
                    progress_display.update(
                        task_id,
                        advance=items_in_batch,
                        description=f"Processed batch: {worker_results['processed']} succeeded"
                    )

                except Exception as e:
                    self.logger.error("Worker failed", error=str(e))
                    results["failed"] += 1

        return results

    def _distribute_items(self, items: List[SidebarItem], num_workers: int) -> List[List[SidebarItem]]:
        """Distribute items evenly among workers.

        Args:
            items: Items to distribute
            num_workers: Number of workers

        Returns:
            List of item batches for each worker
        """
        batches = [[] for _ in range(num_workers)]
        for i, item in enumerate(items):
            batches[i % num_workers].append(item)
        return batches

    def _process_worker_batch(
        self,
        worker: ParallelWorker,
        batch: List[SidebarItem],
        config_values: Dict,
        start_delay: float,
    ) -> Dict[str, int]:
        """Process a batch of items with a single worker.

        Args:
            worker: Worker instance
            batch: Items to process
            config_values: Configuration values
            start_delay: Delay before starting processing

        Returns:
            Dictionary containing batch processing results
        """
        # Apply start delay for staggered startup
        if start_delay > 0:
            import time
            time.sleep(start_delay)

        batch_results = {"processed": 0, "failed": 0, "skipped": 0, "total_items": len(batch)}

        for item in batch:
            try:
                # Process item with worker
                success = worker.process_item_sync(item, config_values)
                if success:
                    batch_results["processed"] += 1
                else:
                    batch_results["failed"] += 1

            except Exception as e:
                self.logger.error(
                    "Error processing item in worker",
                    worker_id=worker.worker_id,
                    item_id=getattr(item, 'id', 'unknown'),
                    error=str(e)
                )
                batch_results["failed"] += 1

        return batch_results

    def _merge_results(self, total_results: Dict[str, int], worker_results: Dict[str, int]) -> None:
        """Merge worker results into total results.

        Args:
            total_results: Total results dictionary to update
            worker_results: Worker results to merge in
        """
        total_results["processed"] += worker_results.get("processed", 0)
        total_results["failed"] += worker_results.get("failed", 0)
        total_results["skipped"] += worker_results.get("skipped", 0)

    async def estimate_processing_time(
        self, num_items: int, config_values: Dict
    ) -> Dict[str, float]:
        """Estimate processing time for parallel vs sequential execution.

        Args:
            num_items: Number of items to process
            config_values: Configuration values

        Returns:
            Dictionary containing time estimates and speedup factor
        """
        # Base processing time per item (estimated)
        base_time_per_item = config_values.get('navigation_timeout', 15) * 1.2
        
        # Sequential estimate
        sequential_estimate = num_items * base_time_per_item
        
        # Parallel estimate
        max_workers = min(config_values.get('max_concurrent_tasks', 3), num_items)
        parallel_efficiency = 0.75  # Account for overhead
        parallel_estimate = (num_items / max_workers) * base_time_per_item / parallel_efficiency
        
        # Calculate speedup
        speedup = sequential_estimate / parallel_estimate if parallel_estimate > 0 else 1.0
        
        return {
            'sequential_estimate': sequential_estimate,
            'parallel_estimate': parallel_estimate,
            'parallel_speedup': speedup,
            'max_workers': max_workers
        }
