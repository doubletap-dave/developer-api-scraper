"""Performance analysis for processing mode selection.

Analyzes workload and estimates processing times to determine
the optimal processing strategy (sequential vs parallel).
"""

from typing import Dict, List

import structlog


class PerformanceAnalyzer:
    """Analyzes performance characteristics to select optimal processing mode."""

    def __init__(self):
        """Initialize performance analyzer."""
        self.logger = structlog.get_logger(__name__)

    def should_use_sequential_processing(self, items_to_process: List[Dict], config_values: Dict) -> bool:
        """Determine if sequential processing should be used.
        
        Args:
            items_to_process: List of items to be processed
            config_values: Configuration values including concurrency settings
            
        Returns:
            bool: True if sequential processing should be used
        """
        num_items = len(items_to_process)

        # Check if parallel processing is disabled
        if not config_values.get('concurrency_enabled', True):
            self.logger.info(
                "Parallel processing disabled in configuration, using sequential mode"
            )
            return True

        # For small numbers of items, sequential might be faster due to overhead
        min_items_for_parallel = 5
        if num_items < min_items_for_parallel:
            self.logger.info(
                "Item count below parallel threshold, using sequential mode",
                item_count=num_items,
                threshold=min_items_for_parallel
            )
            return True

        return False

    def log_performance_estimates(self, num_items: int, time_estimates: Dict) -> None:
        """Log performance analysis information.
        
        Args:
            num_items: Number of items to be processed
            time_estimates: Dictionary containing processing time estimates
        """
        self.logger.info(
            "Processing mode analysis",
            items=num_items,
            sequential_estimate_min=int(time_estimates['sequential_estimate'] / 60),
            parallel_estimate_min=int(time_estimates['parallel_estimate'] / 60),
            speedup_factor=f"{time_estimates['parallel_speedup']:.1f}x"
        )

    def is_parallel_worthwhile(self, time_estimates: Dict, min_speedup: float = 1.3) -> bool:
        """Check if parallel processing provides sufficient benefit.
        
        Args:
            time_estimates: Dictionary containing processing time estimates
            min_speedup: Minimum speedup factor required to use parallel processing
            
        Returns:
            bool: True if parallel processing is worth the overhead
        """
        if time_estimates['parallel_speedup'] < min_speedup:
            self.logger.info(
                "Sequential processing preferred based on performance analysis",
                speedup_factor=f"{time_estimates['parallel_speedup']:.1f}x",
                min_required=f"{min_speedup}x"
            )
            return False
        return True
