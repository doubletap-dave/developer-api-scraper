"""Configuration management package.

This package provides configuration loading, validation, and override handling
for the Wyrm application.
"""

import structlog
from pathlib import Path
from typing import Optional

from .cli_override_handler import CLIOverrideHandler
from .loader import ConfigurationLoader
from .validator import validate_config
from .merger import merge_cli_overrides
from ...models.config import AppConfig

__all__ = ['CLIOverrideHandler', 'ConfigurationLoader', 'validate_config', 'merge_cli_overrides', 'ConfigurationService']


class ConfigurationService:
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self.loader = ConfigurationLoader(logger=self.logger)
        self.cli_handler = CLIOverrideHandler()

    def load(self, config_path: Optional[Path] = None) -> AppConfig:
        return self.loader.load_config(config_path)
    
    def load_config(self, config_path: Optional[Path] = None) -> AppConfig:
        """Load configuration from file (alias for load method)."""
        return self.load(config_path)
    
    def merge_cli_overrides(self, config: AppConfig, cli_args: dict) -> AppConfig:
        """Merge CLI overrides into configuration."""
        return self.cli_handler.merge_cli_overrides(config, cli_args)
    
    def extract_configuration_values(self, config: AppConfig) -> dict:
        """Extract configuration values into a dictionary format."""
        # Convert AppConfig to dict for backward compatibility
        config_dict = config.dict()
        
        # Add extracted values that may be expected by other services
        extracted = {
            'target_url': config.target_url,
            'output_directory': config.output_directory,
            'log_file': config.log_file,
            'log_level': config.log_level,
            'browser': config.webdriver.browser,
            'headless': config.webdriver.headless,
            'navigation_timeout': config.delays.navigation,
            'sidebar_wait_timeout': config.delays.sidebar_wait,
            'element_wait_timeout': config.delays.element_wait,
            'expand_menu_delay': config.delays.expand_menu,
            'post_expand_settle_delay': config.delays.post_expand_settle,
            'max_expand_attempts': config.behavior.max_expand_attempts,
            'skip_existing': config.behavior.skip_existing,
            'force_full_expansion': config.behavior.force_full_expansion,
            'max_concurrent_tasks': config.concurrency.max_concurrent_tasks,
            'concurrency_enabled': config.concurrency.enabled,
            'task_start_delay': config.concurrency.task_start_delay,
            'max_parallel_retries': config.concurrency.max_parallel_retries,
            'debug_output_directory': config.debug_settings.output_directory,
            'save_structure_filename': config.debug_settings.save_structure_filename,
            'save_html_filename': config.debug_settings.save_html_filename,
            'non_headless_pause_seconds': config.debug_settings.non_headless_pause_seconds,
        }
        
        # Add non-headless overrides if not headless
        if not config.webdriver.headless:
            extracted.update({
                'navigation_timeout': config.delays.navigation_noheadless or config.delays.navigation,
                'sidebar_wait_timeout': config.delays.sidebar_wait_noheadless or config.delays.sidebar_wait,
                'expand_menu_delay': config.delays.expand_menu_noheadless or config.delays.expand_menu,
                'post_expand_settle_delay': config.delays.post_expand_settle_noheadless or config.delays.post_expand_settle,
                'max_expand_attempts': config.behavior.max_expand_attempts_noheadless or config.behavior.max_expand_attempts,
            })
            
            # Add non-headless specific delays
            if config.delays.post_click_noheadless:
                extracted['post_click_delay'] = config.delays.post_click_noheadless
            if config.delays.content_wait_noheadless:
                extracted['content_wait_timeout'] = config.delays.content_wait_noheadless
        
        return extracted
    
    def setup_directories(self, config_values: dict) -> None:
        """Setup required directories based on configuration."""
        from pathlib import Path
        
        # Create output directory
        output_dir = Path(config_values.get('output_directory', 'output'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log directory
        log_file = Path(config_values.get('log_file', 'logs/wyrm.log'))
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create debug directory if needed
        debug_dir = Path(config_values.get('debug_output_directory', 'debug'))
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(
            "Directories created",
            output_dir=str(output_dir),
            log_dir=str(log_file.parent),
            debug_dir=str(debug_dir)
        )
