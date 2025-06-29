#!/usr/bin/env python3
"""
Contract tests for Wyrm public API.

These tests ensure that refactoring does not break the public interface
by importing and testing the availability of all public classes and functions.
"""

import pytest
import inspect


def test_main_package_imports():
    """Test that main package imports work correctly."""
    try:
        import wyrm
        assert hasattr(wyrm, '__version__')
        assert isinstance(wyrm.__version__, str)
    except ImportError as e:
        pytest.fail(f"Failed to import main wyrm package: {e}")


def test_services_module_imports():
    """Test that all declared services can be imported."""
    expected_services = [
        "ConfigurationService",
        "NavigationService", 
        "ParsingService",
        "ProgressService",
        "SelectorsService",
        "StorageService",
        "Orchestrator",
    ]
    
    try:
        from wyrm import services
        
        # Check that all expected services are in __all__
        assert hasattr(services, '__all__')
        for service_name in expected_services:
            assert service_name in services.__all__, f"{service_name} missing from services.__all__"
            
        # Check that all services can actually be imported
        for service_name in expected_services:
            assert hasattr(services, service_name), f"Cannot import {service_name} from services"
            service_class = getattr(services, service_name)
            assert inspect.isclass(service_class), f"{service_name} is not a class"
            
    except ImportError as e:
        pytest.fail(f"Failed to import services module: {e}")


def test_models_module_imports():
    """Test that all declared models can be imported."""
    expected_models = [
        # Configuration models
        "AppConfig",
        "BehaviorConfig", 
        "DebugConfig",
        "DelaysConfig",
        "WebDriverConfig",
        # Scraping models
        "HeaderGroup",
        "ResumeInfo",
        "ScrapedContent",
        "SidebarItem", 
        "SidebarStructure",
    ]
    
    try:
        from wyrm import models
        
        # Check that all expected models are in __all__
        assert hasattr(models, '__all__')
        for model_name in expected_models:
            assert model_name in models.__all__, f"{model_name} missing from models.__all__"
            
        # Check that all models can actually be imported
        for model_name in expected_models:
            assert hasattr(models, model_name), f"Cannot import {model_name} from models"
            model_class = getattr(models, model_name)
            assert inspect.isclass(model_class), f"{model_name} is not a class"
            
    except ImportError as e:
        pytest.fail(f"Failed to import models module: {e}")


def test_orchestrator_public_interface():
    """Test that Orchestrator maintains its expected public interface."""
    try:
        from wyrm.services import Orchestrator
        
        # Check that class exists and is callable
        assert inspect.isclass(Orchestrator)
        
        # Check that it can be instantiated
        orchestrator = Orchestrator()
        assert orchestrator is not None
        
        # Check that key methods exist (add methods as needed)
        expected_methods = ['run_scraping_workflow']  # Add other public methods as they exist
        
        for method_name in expected_methods:
            assert hasattr(orchestrator, method_name), f"Orchestrator missing method: {method_name}"
            method = getattr(orchestrator, method_name)
            assert callable(method), f"Orchestrator.{method_name} is not callable"
            
    except Exception as e:
        pytest.fail(f"Orchestrator contract test failed: {e}")


def test_configuration_service_interface():
    """Test that ConfigurationService maintains its expected interface."""
    try:
        from wyrm.services import ConfigurationService
        
        assert inspect.isclass(ConfigurationService)
        
        # Test instantiation
        config_service = ConfigurationService()
        assert config_service is not None
        
    except Exception as e:
        pytest.fail(f"ConfigurationService contract test failed: {e}")


def test_navigation_service_interface():
    """Test that NavigationService maintains its expected interface."""
    try:
        from wyrm.services import NavigationService
        
        assert inspect.isclass(NavigationService)
        
        # Test instantiation
        nav_service = NavigationService()
        assert nav_service is not None
        
    except Exception as e:
        pytest.fail(f"NavigationService contract test failed: {e}")


def test_parsing_service_interface():
    """Test that ParsingService maintains its expected interface.""" 
    try:
        from wyrm.services import ParsingService
        
        assert inspect.isclass(ParsingService)
        
        # Test instantiation  
        parsing_service = ParsingService()
        assert parsing_service is not None
        
    except Exception as e:
        pytest.fail(f"ParsingService contract test failed: {e}")


def test_storage_service_interface():
    """Test that StorageService maintains its expected interface."""
    try:
        from wyrm.services import StorageService
        
        assert inspect.isclass(StorageService)
        
        # Test instantiation
        storage_service = StorageService()
        assert storage_service is not None
        
    except Exception as e:
        pytest.fail(f"StorageService contract test failed: {e}")


def test_pydantic_models_instantiation():
    """Test that Pydantic models can be instantiated with valid data."""
    try:
        from wyrm.models import AppConfig, SidebarItem
        
        # Test basic model instantiation with minimal valid data
        # You'll need to adjust these based on actual model requirements
        
        # Test SidebarItem (adjust fields as needed)
        sidebar_item = SidebarItem(
            text="Test Item",
            type="item",
            level=1
        )
        assert sidebar_item.text == "Test Item"
        assert sidebar_item.type == "item"
        
    except Exception as e:
        pytest.fail(f"Pydantic models contract test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
