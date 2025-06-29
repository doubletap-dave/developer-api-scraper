"""Error manager for parallel processing error handling and fallback strategies.

Handles fallback strategies and error reporting for parallel processing
failures, including sequential processing fallback when parallel
processing encounters issues.
"""

import asyncio
from typing import Dict, List

import structlog

from wyrm.models.scrape import SidebarItem
from wyrm.services.parallel_worker import ParallelWorker


class ErrorManager:
    """Manages error handling and fallback strategies for parallel processing."""

    def __init__(self, progress_service):
        """Initialize error manager with progress service.
        
        Args:
            progress_service: Service for progress tracking and display
        """
        self.logger = structlog.get_logger(__name__)
        self.progress_service = progress_service

    async def handle_parallel_failure(
        self, error: Exception, items: List[SidebarItem], config, config_values: Dict
    ) -> Dict[str, int]:
        """Handle parallel processing failure and attempt fallback.
        
        Args:
            error: Exception that caused the failure
            items: Items that were being processed
            config: Application configuration
            config_values: Configuration values
            
        Returns:
            Dict with processing statistics from fallback processing
        """
        self.logger.error(
            "Parallel processing failed, attempting fallback",
            error=str(error)
        )

        max_retries = config_values.get('max_parallel_retries', 2)
        if max_retries > 0:
            self.logger.info("Falling back to sequential processing")
            return await self.fallback_to_sequential(items, config, config_values)
        else:
            raise

    async def fallback_to_sequential(
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

    async def collect_task_results(self, tasks: List[asyncio.Task]) -> Dict[str, int]:
        """Collect and process results from worker tasks.
        
        Args:
            tasks: List of asyncio tasks to collect results from
            
        Returns:
            Dict with processing statistics
        """
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
