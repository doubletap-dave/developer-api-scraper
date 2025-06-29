"""Menu state module for state caching and retry logic.

This module manages caching of expanded states and retrying certain operations.
"""

import logging
from typing import Dict, Any

class MenuState:
    """Handles state caching and retry logic for menu operations."""

    def __init__(self) -> None:
        """Initialize the menu state manager."""
        self.cache = {}

    def cache_expansion_state(self, menu_text: str, state: Any) -> None:
        """Cache the expanded state of a menu.

        Args:
            menu_text: The text of the menu item
            state: The expanded state to cache (True for expanded, False for collapsed)
        """
        self.cache[menu_text] = state
        logging.debug(f"Cached state for menu '{menu_text}': {state}")

    def get_cached_state(self, menu_text: str) -> Any:
        """Get the cached state of a menu.

        Args:
            menu_text: The text of the menu item

        Returns:
            The cached state or None if not cached
        """
        state = self.cache.get(menu_text)
        logging.debug(f"Retrieved cached state for menu '{menu_text}': {state}")
        return state

    def clear_cache(self) -> None:
        """Clear the state cache."""
        self.cache.clear()
        logging.debug("Cleared menu state cache.")

    def retry_operation(self, operation, args=(), kwargs=None, retries=3) -> Any:
        """Retry an operation with a specified number of attempts.

        Args:
            operation: The operation to retry
            args: Positional arguments for the operation
            kwargs: Keyword arguments for the operation
            retries: Number of retries

        Returns:
            The result of the operation if successful

        Raises:
            Exception if all retries fail
        """
        if kwargs is None:
            kwargs = {}

        for attempt in range(retries):
            try:
                result = operation(*args, **kwargs)
                logging.debug(f"Operation successful on attempt {attempt+1}")
                return result
            except Exception as e:
                logging.warning(f"Operation failed on attempt {attempt+1}: {e}")
                if attempt == retries - 1:
                    logging.error("All retry attempts failed.")
                    raise

        return None

