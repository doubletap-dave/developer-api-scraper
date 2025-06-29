"""Parallel processing coordination for item processing.

Handles the setup, execution, and error handling for parallel
processing mode when processing multiple items.
"""

from typing import Dict, List

import structlog


class ParallelCoordinator:
    """Coordinates parallel processing execution and fallback handling."""

    def __init__(self, orchestrator):
        """Initialize parallel coordinator.
        
        Args:
            orchestrator: Reference to the main Orchestrator instance
        """
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger(__name__)

    async def try_parallel_processing(self, items_to_process: List[Dict], config_values: Dict) -> bool:
        """Attempt parallel processing and return success status.
        
        Args:
            items_to_process: List of items to process in parallel
            config_values: Configuration values for processing
            
        Returns:
            bool: True if parallel processing succeeded, False if fallback needed
        """
        from wyrm.services.parallel_orchestrator import ParallelOrchestrator
        
        num_items = len(items_to_process)
        
        # Create parallel orchestrator and estimate performance
        parallel_orchestrator = ParallelOrchestrator(self.orchestrator.progress_service)
        time_estimates = await parallel_orchestrator.estimate_processing_time(
            num_items, config_values
        )

        # Execute parallel processing
        return await self._execute_parallel_processing(
            items_to_process, config_values, parallel_orchestrator, time_estimates
        )

    async def _execute_parallel_processing(
        self, items_to_process: List[Dict], config_values: Dict, 
        parallel_orchestrator, time_estimates: Dict
    ) -> bool:
        """Execute parallel processing and return success status.
        
        Args:
            items_to_process: List of items to process
            config_values: Configuration values for processing
            parallel_orchestrator: Configured parallel orchestrator instance
            time_estimates: Performance estimates for logging
            
        Returns:
            bool: True if execution succeeded, False if error occurred
        """
        try:
            self.logger.info(
                "Using parallel processing mode",
                max_workers=config_values.get('max_concurrent_tasks', 3),
                expected_speedup=f"{time_estimates['parallel_speedup']:.1f}x"
            )

            # Convert items to SidebarItem objects
            sidebar_items = self._convert_to_sidebar_items(items_to_process)

            # Process with parallel orchestrator
            results = await parallel_orchestrator.process_items_parallel(
                sidebar_items, self.orchestrator._config, config_values
            )

            self.logger.info(
                "Parallel processing completed",
                processed=results['processed'],
                failed=results['failed'],
                skipped=results['skipped']
            )
            return True

        except Exception as e:
            self.logger.error(
                "Parallel processing failed, falling back to sequential",
                error=str(e)
            )
            return False

    def _convert_to_sidebar_items(self, items_to_process: List[Dict]) -> List:
        """Convert dict items to SidebarItem objects for parallel processing.
        
        Args:
            items_to_process: List of dictionary items to convert
            
        Returns:
            List: Converted SidebarItem objects
        """
        # Delegate to ItemHandler for conversion logic
        from .item_handler import ItemHandler
        item_handler = ItemHandler()
        return item_handler.convert_to_sidebar_items(items_to_process)
