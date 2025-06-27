"""Data models for Wyrm application.

This package contains Pydantic models for type-safe data structures
used throughout the application.
"""

from .config import (
    AppConfig,
    BehaviorConfig,
    DebugConfig,
    DelaysConfig,
    WebDriverConfig,
)
from .scrape import (
    HeaderGroup,
    ResumeInfo,
    ScrapedContent,
    SidebarItem,
    SidebarStructure,
)

__all__ = [
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
