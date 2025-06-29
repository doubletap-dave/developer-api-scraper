import pytest
from pydantic import ValidationError
from wyrm.models.config import AppConfig, WebDriverConfig, DelaysConfig, BehaviorConfig, ConcurrencyConfig, DebugConfig


def test_webdriver_config_edge_cases():
    # Test invalid browser type
    with pytest.raises(ValidationError):
        WebDriverConfig(browser="invalid_browser")

    # Test valid browser types
    for browser in ["chrome", "firefox", "edge"]:
        config = WebDriverConfig(browser=browser)
        assert config.browser == browser


def test_delays_config_edge_cases():
    # Negative delays should raise validation error
    with pytest.raises(ValidationError):
        DelaysConfig(navigation=-1.0)

    # Valid delay settings
    config = DelaysConfig(navigation=0.1, element_wait=0.1)
    assert config.navigation == 0.1
    assert config.element_wait == 0.1


def test_behavior_config_edge_cases():
    # Negative max_expand_attempts should raise validation error
    with pytest.raises(ValidationError):
        BehaviorConfig(max_expand_attempts=-1)

    # Valid attempts
    config = BehaviorConfig(max_expand_attempts=1)
    assert config.max_expand_attempts == 1


def test_concurrency_config_edge_cases():
    # Zero or negative max_concurrent_tasks should raise validation error
    with pytest.raises(ValidationError):
        ConcurrencyConfig(max_concurrent_tasks=0)

    # Valid max tasks
    config = ConcurrencyConfig(max_concurrent_tasks=2)
    assert config.max_concurrent_tasks == 2


def test_debug_config_edge_cases():
    # Empty save_structure_filename should raise validation error
    with pytest.raises(ValidationError):
        DebugConfig(save_structure_filename="")

    # Valid filenames
    config = DebugConfig(save_structure_filename="valid.json")
    assert config.save_structure_filename == "valid.json"


def test_app_config_edge_cases():
    # Invalid URL should raise validation error
    with pytest.raises(ValidationError):
        AppConfig(target_url="invalid_url")

    # Valid URL
    config = AppConfig(target_url="http://valid.url/", output_directory="output")
    assert config.target_url == "http://valid.url/"

