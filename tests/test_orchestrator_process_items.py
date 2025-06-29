"""Tests for Orchestrator._process_items_from_structure method.

This module contains comprehensive unit and integration tests for the
_process_items_from_structure method, focusing on the conditional logic
for calling expand_all_menus_comprehensive based on cache vs live parsing.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from wyrm.services.orchestrator import Orchestrator
from wyrm.models import SidebarStructure, SidebarItem


@pytest.fixture
def orchestrator():
    """Create an Orchestrator instance for testing."""
    orchestrator = Orchestrator()

    # Mock all services to avoid initialization issues
    orchestrator.navigation_service = MagicMock()
    orchestrator.parsing_service = MagicMock()
    orchestrator.storage_service = MagicMock()
    orchestrator.progress_service = MagicMock()
    orchestrator.config_service = MagicMock()
    orchestrator.logger = MagicMock()

    # Mock driver initialization check
    orchestrator.navigation_service.get_driver.return_value = None
    orchestrator.navigation_service.initialize_driver = AsyncMock()
    orchestrator.navigation_service.navigate_and_wait = AsyncMock()
    orchestrator.navigation_service.expand_all_menus_comprehensive = AsyncMock()

    return orchestrator


@pytest.fixture
def sample_sidebar_structure():
    """Create a sample sidebar structure for testing."""
    sample_items = [
        {
            "id": "item1",
            "text": "Item 1",
            "type": "item",
            "level": 1,
            "header": "Menu1",
            "menu": "Menu1"
        },
        {
            "id": "item2",
            "text": "Item 2",
            "type": "item",
            "level": 2,
            "header": "Menu2",
            "menu": "Menu2"
        },
        {
            "id": "item3",
            "text": "Item 3",
            "type": "item",
            "level": 1,
            "header": "Menu1",
            "menu": "Menu1"
        }
    ]

    sidebar_items = [SidebarItem(**item) for item in sample_items]

    return SidebarStructure(
        structured_data=[],
        items=sidebar_items
    )


@pytest.fixture
def config_values():
    """Create sample configuration values."""
    return {
        "base_output_dir": "/tmp/test_output",
        "navigation_timeout": 10,
        "force_full_expansion": False,
        "validate_cache": False,
        "concurrency_enabled": False,  # Disable parallel processing for simpler tests
    }


@pytest.fixture
def mock_config():
    """Create mock configuration object."""
    config = MagicMock()
    config.browser = MagicMock()
    config.navigation = MagicMock()
    return config


class TestProcessItemsFromStructureCaching:
    """Test cases for cache vs live parsing behavior."""

    @pytest.mark.asyncio
    async def test_cached_structure_does_not_call_expand_all_menus(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that processing cached structure does NOT call expand_all_menus_comprehensive.

        This is the critical test case #1: When using cached structure data,
        the method should skip the expensive full menu expansion step.
        """
        # Arrange
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items

        # Mock _process_items_hybrid_mode to avoid complexity
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Act - Process items from cached structure (from_cache=True)
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=True  # This is the key parameter
        )

        # Assert
        # expand_all_menus_comprehensive should NOT be called for cached data
        orchestrator.navigation_service.expand_all_menus_comprehensive.assert_not_called()

        # Verify that driver was initialized and navigation occurred
        orchestrator.navigation_service.initialize_driver.assert_called_once_with(
            mock_config)
        orchestrator.navigation_service.navigate_and_wait.assert_called_once_with(
            mock_config, config_values)

        # Verify processing continued normally
        orchestrator._process_items_hybrid_mode.assert_called_once()

    @pytest.mark.asyncio
    async def test_live_parsed_structure_calls_expand_all_menus(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that processing live-parsed structure DOES call expand_all_menus_comprehensive.

        This is the critical test case #2: When structure was just parsed live,
        the method should call the full menu expansion method.
        """
        # Arrange
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items

        # Mock _process_items_hybrid_mode to avoid complexity
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Act - Process items from live-parsed structure (from_cache=False)
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=False  # This is the key parameter
        )

        # Assert
        # expand_all_menus_comprehensive SHOULD be called for live-parsed data
        orchestrator.navigation_service.expand_all_menus_comprehensive.assert_called_once()

        # Verify that driver was initialized and navigation occurred
        orchestrator.navigation_service.initialize_driver.assert_called_once_with(
            mock_config)
        orchestrator.navigation_service.navigate_and_wait.assert_called_once_with(
            mock_config, config_values)

        # Verify processing continued normally
        orchestrator._process_items_hybrid_mode.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_structure_with_force_full_expansion_calls_expand(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that cached structure with force_full_expansion=True calls expand_all_menus_comprehensive."""
        # Arrange
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Enable force_full_expansion
        config_values["force_full_expansion"] = True

        # Act
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=True
        )

        # Assert
        # Should expand even with cached data due to force_full_expansion
        orchestrator.navigation_service.expand_all_menus_comprehensive.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_structure_with_force_flag_calls_expand(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that cached structure with force=True calls expand_all_menus_comprehensive."""
        # Arrange
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Act with force=True
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=True,  # This should trigger expansion
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=True
        )

        # Assert
        # Should expand even with cached data due to force flag
        orchestrator.navigation_service.expand_all_menus_comprehensive.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_structure_with_validate_cache_calls_expand(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that cached structure with validate_cache=True calls expand_all_menus_comprehensive."""
        # Arrange
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Enable validate_cache
        config_values["validate_cache"] = True

        # Act
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=True
        )

        # Assert
        # Should expand even with cached data due to validate_cache
        orchestrator.navigation_service.expand_all_menus_comprehensive.assert_called_once()

    @pytest.mark.asyncio
    async def test_expansion_already_done_skips_second_expansion(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that if expansion was already done in session, it's skipped for cached data."""
        # Arrange
        orchestrator._config = mock_config
        orchestrator._full_expansion_done = True  # Mark as already expanded
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Act - With from_cache=True and _full_expansion_done=True, should skip
        # expansion
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=True  # Changed to True to test the cache branch
        )

        # Assert
        # Should NOT expand since already done in this session
        orchestrator.navigation_service.expand_all_menus_comprehensive.assert_not_called()

    @pytest.mark.asyncio
    async def test_live_parsing_always_expands_regardless_of_expansion_done(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that live parsing always expands even if _full_expansion_done=True.

        According to the implementation logic, live parsing (from_cache=False)
        takes precedence and always expands, regardless of _full_expansion_done.
        """
        # Arrange
        orchestrator._config = mock_config
        orchestrator._full_expansion_done = True  # Mark as already expanded
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Act - With from_cache=False, should ALWAYS expand regardless of
        # _full_expansion_done
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=False  # Live parsing always takes precedence
        )

        # Assert
        # Should expand because live parsing always takes precedence
        orchestrator.navigation_service.expand_all_menus_comprehensive.assert_called_once()


class TestProcessItemsFromStructureRegression:
    """Regression tests to ensure processing still works correctly."""

    @pytest.mark.asyncio
    async def test_processing_succeeds_with_cached_structure(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that processing succeeds when using cached structure data.

        Regression test case #3: Ensure that even when skipping menu expansion,
        the overall processing workflow completes successfully.
        """
        # Arrange
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items

        # Mock the hybrid processing to simulate successful completion
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Act
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=True
        )

        # Assert
        # Verify all expected method calls occurred
        orchestrator.parsing_service._get_valid_items.assert_called_once_with(
            sample_sidebar_structure)
        orchestrator.parsing_service.filter_items_for_processing.assert_called_once()
        orchestrator.navigation_service.initialize_driver.assert_called_once()
        orchestrator._process_items_hybrid_mode.assert_called_once()

        # Verify the correct items were passed to processing
        args, kwargs = orchestrator._process_items_hybrid_mode.call_args
        processed_items = args[0]
        assert len(processed_items) == 3
        assert all(item.id in ["item1", "item2", "item3"] for item in processed_items)

    @pytest.mark.asyncio
    async def test_processing_succeeds_with_live_parsed_structure(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that processing succeeds when using live-parsed structure data."""
        # Arrange
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Act
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=False
        )

        # Assert
        # Verify all expected method calls occurred, including expansion
        orchestrator.parsing_service._get_valid_items.assert_called_once_with(
            sample_sidebar_structure)
        orchestrator.parsing_service.filter_items_for_processing.assert_called_once()
        orchestrator.navigation_service.initialize_driver.assert_called_once()
        orchestrator.navigation_service.expand_all_menus_comprehensive.assert_called_once()
        orchestrator._process_items_hybrid_mode.assert_called_once()

    @pytest.mark.asyncio
    async def test_collected_items_match_expected_list(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that collected items match the expected list from sidebar structure.

        Regression test to ensure that the item filtering and collection
        process produces the expected results.
        """
        # Arrange
        orchestrator._config = mock_config
        # Only first 2 items are "valid"
        valid_items = sample_sidebar_structure.items[:2]
        orchestrator.parsing_service._get_valid_items.return_value = valid_items
        orchestrator.parsing_service.filter_items_for_processing.return_value = valid_items
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Act
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=2,  # Limit to 2 items
            resume_info=False,
            from_cache=True
        )

        # Assert
        # Verify filter_items_for_processing was called with correct parameters
        orchestrator.parsing_service.filter_items_for_processing.assert_called_once_with(
            valid_items, 2, None  # valid_items, max_items, test_item_id
        )

        # Verify the correct filtered items were passed to processing
        args, kwargs = orchestrator._process_items_hybrid_mode.call_args
        processed_items = args[0]
        assert len(processed_items) == 2
        assert processed_items[0].id == "item1"
        assert processed_items[1].id == "item2"

    @pytest.mark.asyncio
    async def test_driver_initialization_when_not_initialized(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that driver is properly initialized when not already present."""
        # Arrange
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Mock driver as not initialized initially
        orchestrator.navigation_service.get_driver.return_value = None

        # Act
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=True
        )

        # Assert
        # Driver initialization should be called
        orchestrator.navigation_service.initialize_driver.assert_called_once_with(
            mock_config)
        orchestrator.navigation_service.navigate_and_wait.assert_called_once_with(
            mock_config, config_values)

    @pytest.mark.asyncio
    async def test_driver_initialization_when_already_initialized(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test behavior when driver is already initialized."""
        # Arrange
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Mock driver as already initialized
        mock_driver = MagicMock()
        orchestrator.navigation_service.get_driver.return_value = mock_driver

        # Act
        await orchestrator._process_items_from_structure(
            sidebar_structure=sample_sidebar_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=True
        )

        # Assert
        # Driver initialization should NOT be called since already initialized
        orchestrator.navigation_service.initialize_driver.assert_not_called()
        orchestrator.navigation_service.navigate_and_wait.assert_not_called()


class TestProcessItemsFromStructureEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_empty_sidebar_structure(
        self, orchestrator, config_values, mock_config
    ):
        """Test handling of empty sidebar structure."""
        # Arrange
        empty_structure = SidebarStructure(structured_data=[], items=[])
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = []
        orchestrator.parsing_service.filter_items_for_processing.return_value = []
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Act
        await orchestrator._process_items_from_structure(
            sidebar_structure=empty_structure,
            config_values=config_values,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            from_cache=True
        )

        # Assert
        # Should still call processing even with empty list
        orchestrator._process_items_hybrid_mode.assert_called_once_with(
            [], config_values)

    @pytest.mark.asyncio
    async def test_navigation_service_initialization_failure(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test handling of navigation service initialization failure."""
        # Arrange
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items

        # Mock initialization failure
        orchestrator.navigation_service.initialize_driver.side_effect = Exception(
            "Driver init failed")

        # Act & Assert
        with pytest.raises(Exception, match="Driver init failed"):
            await orchestrator._process_items_from_structure(
                sidebar_structure=sample_sidebar_structure,
                config_values=config_values,
                force=False,
                test_item_id=None,
                max_items=None,
                resume_info=False,
                from_cache=True
            )

    @pytest.mark.asyncio
    async def test_menu_expansion_error_handling(
        self, orchestrator, sample_sidebar_structure, config_values, mock_config
    ):
        """Test that menu expansion errors don't crash the entire process."""
        # Arrange
        orchestrator._config = mock_config
        orchestrator.parsing_service._get_valid_items.return_value = sample_sidebar_structure.items
        orchestrator.parsing_service.filter_items_for_processing.return_value = sample_sidebar_structure.items
        orchestrator._process_items_hybrid_mode = AsyncMock()

        # Mock expansion failure
        orchestrator.navigation_service.expand_all_menus_comprehensive.side_effect = Exception(
            "Expansion failed")

        # Act & Assert
        # Should propagate the exception since expansion is critical
        with pytest.raises(Exception, match="Expansion failed"):
            await orchestrator._process_items_from_structure(
                sidebar_structure=sample_sidebar_structure,
                config_values=config_values,
                force=False,
                test_item_id=None,
                max_items=None,
                resume_info=False,
                from_cache=False  # This triggers expansion
            )


if __name__ == "__main__":
    pytest.main([__file__])
