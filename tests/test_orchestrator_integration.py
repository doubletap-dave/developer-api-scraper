import pytest
import yaml
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from wyrm.services.orchestration import Orchestrator
from wyrm.models.config import AppConfig


@pytest.fixture
def valid_config_data():
    """Provide a valid configuration dictionary for testing."""
    return {
        "target_url": "https://test.example.com",
        "output_directory": "test_output",
        "log_file": "test_logs/test.log",
        "log_level": "INFO",
        "webdriver": {
            "browser": "chrome",
            "headless": True,
        },
        "delays": {
            "navigation": 10.0,
            "element_wait": 10.0,
        },
        "behavior": {
            "max_expand_attempts": 5,
            "skip_existing": True,
        },
        "concurrency": {
            "max_concurrent_tasks": 2,
            "enabled": True,
        },
        "debug_settings": {
            "output_directory": "debug",
            "save_structure_filename": "structure.json",
        },
    }


@pytest.fixture
def temp_config_file(valid_config_data):
    """Create a temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(valid_config_data, f)
        yield f.name
    Path(f.name).unlink()


def test_orchestrator_instantiation():
    """Test that Orchestrator can be instantiated without errors."""
    orchestrator = Orchestrator()
    
    # Verify all required services are present
    assert orchestrator.config_service is not None
    assert orchestrator.navigation_service is not None
    assert orchestrator.parsing_service is not None
    assert orchestrator.storage_service is not None
    assert orchestrator.progress_service is not None
    
    # Verify orchestration components are present
    assert orchestrator.workflow_manager is not None
    assert orchestrator.item_processor is not None
    assert orchestrator.structure_handler is not None


def test_orchestrator_config_service_integration(temp_config_file):
    """Test that orchestrator can use the configuration service."""
    orchestrator = Orchestrator()
    
    # Test that config service can load configuration
    config = orchestrator.config_service.load_config(temp_config_file)
    assert isinstance(config, AppConfig)
    assert config.target_url == "https://test.example.com"


def test_orchestrator_cli_override_integration(temp_config_file):
    """Test that orchestrator can apply CLI overrides through config service."""
    orchestrator = Orchestrator()
    
    # Load base config
    config = orchestrator.config_service.load_config(temp_config_file)
    
    # Apply CLI overrides
    cli_args = {
        "headless": False,
        "log_level": "DEBUG",
        "max_expand_attempts": 15,
        "force_full_expansion": True,
    }
    
    modified_config = orchestrator.config_service.merge_cli_overrides(config, cli_args)
    
    # Verify overrides were applied
    assert modified_config.webdriver.headless is False
    assert modified_config.log_level == "DEBUG"
    assert modified_config.behavior.max_expand_attempts == 15
    assert modified_config.behavior.force_full_expansion is True


@pytest.mark.asyncio
async def test_orchestrator_workflow_interface(temp_config_file):
    """Test that orchestrator maintains its expected workflow interface."""
    orchestrator = Orchestrator()
    
    # Mock all the underlying services to avoid actual browser automation
    with patch.object(orchestrator.workflow_manager, 'run_scraping_workflow', new_callable=AsyncMock) as mock_workflow:
        mock_workflow.return_value = None
        
        # This should work without any changes to the orchestrator interface
        await orchestrator.run_scraping_workflow(
            config_path=temp_config_file,
            headless=True,
            log_level="INFO",
            save_structure=True,
            save_html=True,
            debug=False,
            max_expand_attempts=10,
            force=False,
            test_item_id=None,
            max_items=None,
            resume_info=False,
            structure_filename=None,
            html_filename=None,
            force_full_expansion=False,
        )
        
        # Verify the workflow manager was called with expected arguments
        mock_workflow.assert_called_once()


def test_orchestrator_service_initialization():
    """Test that all services are properly initialized in the orchestrator."""
    orchestrator = Orchestrator()
    
    # Test that services have expected attributes/methods
    assert hasattr(orchestrator.config_service, 'load_config')
    assert hasattr(orchestrator.config_service, 'merge_cli_overrides')
    assert hasattr(orchestrator.navigation_service, 'cleanup')
    assert hasattr(orchestrator.workflow_manager, 'run_scraping_workflow')
    assert hasattr(orchestrator.item_processor, 'process_items_from_structure')
    assert hasattr(orchestrator.structure_handler, 'handle_sidebar_structure')


@pytest.mark.asyncio
async def test_orchestrator_cleanup_integration():
    """Test that orchestrator cleanup works with all services."""
    orchestrator = Orchestrator()
    
    # Mock the navigation service cleanup
    with patch.object(orchestrator.navigation_service, 'cleanup', new_callable=AsyncMock) as mock_cleanup:
        # Set up a config for cleanup
        orchestrator._config = AppConfig(target_url="https://test.example.com")
        
        await orchestrator._cleanup()
        
        # Verify cleanup was called
        mock_cleanup.assert_called_once_with(orchestrator._config)


def test_configuration_validation_integration(valid_config_data):
    """Test that the orchestrator works with the validation service."""
    orchestrator = Orchestrator()
    
    # Test validation through the configuration service
    from wyrm.services.configuration.validator import validate_config
    
    # Should not raise any exceptions
    config = validate_config(valid_config_data)
    assert isinstance(config, AppConfig)
    
    # Test with invalid data
    invalid_data = valid_config_data.copy()
    invalid_data["target_url"] = "invalid_url"
    
    with pytest.raises(ValueError):
        validate_config(invalid_data)


def test_orchestrator_backward_compatibility():
    """Test that the orchestrator maintains backward compatibility with existing interfaces."""
    orchestrator = Orchestrator()
    
    # Verify that the orchestrator has the expected public methods
    expected_methods = [
        'run_scraping_workflow',
        '_initialize_endpoint_aware_services',
        '_cleanup',
    ]
    
    for method_name in expected_methods:
        assert hasattr(orchestrator, method_name), f"Missing method: {method_name}"
        method = getattr(orchestrator, method_name)
        assert callable(method), f"Method {method_name} is not callable"


def test_orchestrator_service_contracts():
    """Test that all services maintain their expected contracts."""
    orchestrator = Orchestrator()
    
    # Note: Some services may be compound services, so we test for callable interfaces
    # rather than exact type matches
    assert callable(getattr(orchestrator.config_service, 'load_config', None))
    assert callable(getattr(orchestrator.navigation_service, 'cleanup', None))
    
    # Test that orchestration components are properly initialized
    assert orchestrator.workflow_manager is not None
    assert orchestrator.item_processor is not None
    assert orchestrator.structure_handler is not None
