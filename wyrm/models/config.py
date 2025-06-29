"""Configuration models for Wyrm application.

This module defines Pydantic models for type-safe configuration management,
replacing dictionary-based config access with validated data structures.
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, validator


class WebDriverConfig(BaseModel):
    """WebDriver configuration settings."""

    browser: str = Field(
        default="chrome",
        description="Browser type: chrome, firefox, or edge")
    headless: bool = Field(default=True, description="Run browser in headless mode")

    @validator("browser")
    def validate_browser(cls, v: str) -> str:
        """Validate browser type."""
        allowed_browsers = {"chrome", "firefox", "edge"}
        if v.lower() not in allowed_browsers:
            raise ValueError(f"Browser must be one of {allowed_browsers}, got {v}")
        return v.lower()


class DelaysConfig(BaseModel):
    """Timing and delay configuration settings."""

    # Base delays (used in headless mode)
    navigation: float = Field(default=10.0,
                              description="Timeout for initial page navigation")
    element_wait: float = Field(default=10.0,
                                description="Default timeout for waiting for elements")
    sidebar_wait: float = Field(default=15.0,
                                description="Timeout for waiting for sidebar container")
    expand_menu: float = Field(default=0.5,
                               description="Delay between clicking menu expanders")
    post_expand_settle: float = Field(
        default=1.0, description="Delay after expansion loop before parsing")

    # Non-headless mode overrides
    navigation_noheadless: Optional[float] = Field(
        default=30.0, description="Navigation timeout for non-headless mode")
    sidebar_wait_noheadless: Optional[float] = Field(
        default=30.0, description="Sidebar wait timeout for non-headless mode")
    expand_menu_noheadless: Optional[float] = Field(
        default=0.7, description="Menu expand delay for non-headless mode")
    post_expand_settle_noheadless: Optional[float] = Field(
        default=2.0, description="Post-expand settle delay for non-headless mode")
    post_click_noheadless: Optional[float] = Field(
        default=0.7, description="Post-click delay for non-headless mode")
    content_wait_noheadless: Optional[float] = Field(
        default=15.0, description="Content wait timeout for non-headless mode")

    @validator("*", pre=True)
    def validate_positive_numbers(cls, v):
        """Ensure all timing values are positive."""
        if isinstance(v, (int, float)) and v < 0:
            raise ValueError("Timing values must be non-negative")
        return v


class BehaviorConfig(BaseModel):
    """Application behavior configuration settings."""

    max_expand_attempts: int = Field(default=10,
                                     description="Maximum loops to try expanding menus")
    skip_existing: bool = Field(default=True,
                                description="Skip files if they already exist")
    force_full_expansion: bool = Field(default=False,
                                       description="Force full menu expansion even when using cached structure")

    # Non-headless mode overrides
    max_expand_attempts_noheadless: Optional[int] = Field(
        default=15, description="Max expand attempts for non-headless mode")

    @validator("max_expand_attempts", "max_expand_attempts_noheadless")
    def validate_positive_integers(cls, v):
        """Ensure attempt counts are positive."""
        if v is not None and v <= 0:
            raise ValueError("Attempt counts must be positive integers")
        return v


class ConcurrencyConfig(BaseModel):
    """Parallel processing configuration settings."""

    max_concurrent_tasks: int = Field(
        default=3,
        description="Maximum number of concurrent content extraction tasks")
    enabled: bool = Field(
        default=True,
        description="Enable parallel processing")
    task_start_delay: float = Field(
        default=0.5,
        description="Minimum delay between starting new tasks (seconds)")
    max_parallel_retries: int = Field(
        default=2,
        description="Maximum retries for failed parallel tasks before fallback")

    @validator("max_concurrent_tasks")
    def validate_max_concurrent_tasks(cls, v: int) -> int:
        """Ensure max_concurrent_tasks is reasonable."""
        if v < 1:
            raise ValueError("max_concurrent_tasks must be at least 1")
        if v > 10:
            raise ValueError("max_concurrent_tasks should not exceed 10 for stability")
        return v

    @validator("task_start_delay")
    def validate_task_start_delay(cls, v: float) -> float:
        """Ensure task_start_delay is non-negative."""
        if v < 0:
            raise ValueError("task_start_delay must be non-negative")
        return v

    @validator("max_parallel_retries")
    def validate_max_parallel_retries(cls, v: int) -> int:
        """Ensure max_parallel_retries is reasonable."""
        if v < 0:
            raise ValueError("max_parallel_retries must be non-negative")
        if v > 5:
            raise ValueError("max_parallel_retries should not exceed 5")
        return v


class DebugConfig(BaseModel):
    """Debug and development configuration settings."""

    output_directory: Path = Field(
        default=Path("debug"),
        description="Directory for debug outputs")
    save_structure_filename: str = Field(
        default="structure_debug.json",
        description="Filename for saved structure JSON")
    save_html_filename: str = Field(
        default="sidebar_debug.html",
        description="Filename for saved sidebar HTML")
    non_headless_pause_seconds: float = Field(
        default=10.0, description="Pause duration in non-headless mode")

    @validator("output_directory", pre=True)
    def convert_to_path(cls, v):
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v

    @validator("save_structure_filename", "save_html_filename")
    def validate_filenames(cls, v: str) -> str:
        """Ensure filenames are not empty."""
        if not v.strip():
            raise ValueError("Filenames cannot be empty")
        return v.strip()


class AppConfig(BaseModel):
    """Main application configuration model."""

    target_url: str = Field(..., description="Target URL to scrape")
    output_directory: Path = Field(
        default=Path("output"),
        description="Base output directory")
    log_file: Path = Field(default=Path("logs/wyrm.log"), description="Log file path")
    log_level: str = Field(default="INFO", description="Logging level")

    # Nested configuration sections
    webdriver: WebDriverConfig = Field(default_factory=WebDriverConfig)
    delays: DelaysConfig = Field(default_factory=DelaysConfig)
    behavior: BehaviorConfig = Field(default_factory=BehaviorConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    debug_settings: DebugConfig = Field(default_factory=DebugConfig)

    @validator("target_url")
    def validate_url(cls, v: str) -> str:
        """Basic URL validation."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Target URL must start with http:// or https://")
        return v

    @validator("output_directory", "log_file", pre=True)
    def convert_paths(cls, v):
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v

    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level."""
        allowed_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}, got {v}")
        return v.upper()

    class Config:
        """Pydantic configuration."""
        # Allow arbitrary types (like Path)
        arbitrary_types_allowed = True
        # Validate assignment
        validate_assignment = True
