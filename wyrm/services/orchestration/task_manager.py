"""Task manager for managing task creation for parallel processing sessions.

This service encapsulates the logic for creating worker tasks
in a parallel processing environment, ensuring tasks are managed
and scheduled correctly with proper concurrency management.
"""

from typing import List
import asyncio
import structlog

from wyrm.models.scrape import SidebarItem
from wyrm.services.parallel_worker import ParallelWorker

class TaskManager:
    """Handles task management for parallel processing flows."""

    def __init__(self):
        """Initialize the task manager."""
        self.logger = structlog.get_logger(__name__)

    def create_worker_tasks(
        self, items: List[SidebarItem], config, config_values: dict,
        semaphore: asyncio.Semaphore, task_delay: float, progress, task_id: int
    ) -> List[asyncio.Task]:
        """Create worker tasks for processing items in parallel.

        Args:
            items: List of SidebarItems to process
            config: Application configuration
            config_values: Configuration values
            semaphore: Concurrency control semaphore
            task_delay: Delay between task starts
            progress: Progress display instance
            task_id: Task identification for progress tracking

        Returns:
            List of asyncio.Task to be executed
        """
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

    async def _delayed_worker_start(
        self,
        worker_id: int,
        item: SidebarItem,
        config,
        config_values: dict,
        semaphore: asyncio.Semaphore,
        delay: float,
        progress,
        task_id: int,
    ) -> bool:
        """Start a worker after a specified delay to stagger task execution.

        Args:
            worker_id: Unique identifier for the worker task
            item: SidebarItem to process
            config: Application configuration
            config_values: Configuration values
            semaphore: Concurrency control semaphore
            delay: Delay before starting a task
            progress: Progress display instance
            task_id: Task identifier for progress tracking

        Returns:
            Boolean indicating success.
        """
        if delay > 0:
            await asyncio.sleep(delay)

        # Update task description in progress
        progress.update(task_id, description=f"Processing: {item.text}")

        # Instantiate and run worker
        worker = ParallelWorker(worker_id)
        success = await worker.process_item(item, config, config_values, semaphore)

        # Advance progress on completion
        progress.advance(task_id)

        return success

