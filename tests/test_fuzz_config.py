import random
import pytest
from pydantic import ValidationError
from wyrm.models.config import AppConfig


@pytest.mark.parametrize("num_tests", [100])
def test_fuzz_random_config_combinations(num_tests):
    """Generate random configuration and validate."""
    # Test a set number of random configurations
    for _ in range(num_tests):
        config_data = generate_random_config_data()
        try:
            AppConfig(**config_data)
        except ValidationError:
            # Expected for invalid random configurations
            continue


def generate_random_config_data():
    """Generates random configuration data."""
    return {
        "target_url": random.choice(["http://valid.url/", "https://another.valid.url/", "invalid_url"]),
        "output_directory": random.choice(["output", "debug"]),
        "log_file": random.choice(["logs/wyrm.log", "invalid_path"]),
        "log_level": random.choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
        "webdriver": {
            "browser": random.choice(["chrome", "firefox", "edge", "invalid"]),
            "headless": random.choice([True, False]),
        },
        "delays": {
            "navigation": random.uniform(-1.0, 50.0),
            "element_wait": random.uniform(-1.0, 50.0),
        },
        "behavior": {
            "max_expand_attempts": random.randint(-10, 20),
            "skip_existing": random.choice([True, False]),
        },
        "concurrency": {
            "max_concurrent_tasks": random.randint(0, 15),
        },
        "debug_settings": {
            "output_directory": random.choice(["debug"]),
            "save_structure_filename": random.choice(["structure.json", ""]),
        },
    }

