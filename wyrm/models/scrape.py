"""Scraping models for Wyrm application.

This module defines Pydantic models for type-safe scraping data structures,
replacing dictionary-based item and content handling.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class SidebarItem(BaseModel):
    """Model for a sidebar item parsed from the HTML structure."""

    id: Optional[str] = Field(None, description="Unique identifier for the item")
    text: str = Field(..., description="Display text of the item")
    type: str = Field(..., description="Type of item: 'item' or 'menu'")
    header: Optional[str] = Field(None, description="Header group this item belongs to")
    menu: Optional[str] = Field(None, description="Parent menu text (if applicable)")
    parent_menu_text: Optional[str] = Field(
        None, description="Parent menu text for re-expansion")
    level: int = Field(default=0, description="Nesting level in the hierarchy")
    is_expandable: bool = Field(default=False,
                                description="Whether this item can be expanded")

    @validator("type")
    def validate_type(cls, v: str) -> str:
        """Validate item type."""
        allowed_types = {"item", "menu"}
        if v not in allowed_types:
            raise ValueError(f"Item type must be one of {allowed_types}, got {v}")
        return v

    @validator("text")
    def validate_text(cls, v: str) -> str:
        """Ensure text is not empty."""
        if not v.strip():
            raise ValueError("Item text cannot be empty")
        return v.strip()

    @validator("level")
    def validate_level(cls, v: int) -> int:
        """Ensure level is non-negative."""
        if v < 0:
            raise ValueError("Level must be non-negative")
        return v


class HeaderGroup(BaseModel):
    """Model for a header group containing sidebar items."""

    header_text: str = Field(..., description="Text of the header")
    children: List[dict] = Field(
        default_factory=list,
        description="Child items under this header")

    @validator("header_text")
    def validate_header_text(cls, v: str) -> str:
        """Ensure header text is not empty."""
        if not v.strip():
            raise ValueError("Header text cannot be empty")
        return v.strip()


class SidebarStructure(BaseModel):
    """Model for the complete sidebar structure."""

    structured_data: List[HeaderGroup] = Field(
        default_factory=list, description="Hierarchical structure data")
    items: List[SidebarItem] = Field(
        default_factory=list,
        description="Flattened list of all items")

    @property
    def total_items(self) -> int:
        """Get total number of items."""
        return len(self.items)

    @property
    def valid_items(self) -> List[SidebarItem]:
        """Get items that are valid for processing (content items with IDs)."""
        return [item for item in self.items if item.id is not None and item.type == "item"]

    @property
    def menu_items(self) -> List[SidebarItem]:
        """Get items that are menus."""
        return [item for item in self.items if item.type == "menu"]

    @property
    def content_items(self) -> List[SidebarItem]:
        """Get items that are content (not menus)."""
        return [item for item in self.items if item.type == "item"]


class ScrapedContent(BaseModel):
    """Model for scraped content from a page."""

    item_id: str = Field(..., description="ID of the sidebar item")
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Page URL")
    markdown_content: str = Field(..., description="Extracted markdown content")
    breadcrumbs: Optional[List[str]] = Field(
        default=None, description="Navigation breadcrumbs")
    header: Optional[str] = Field(None, description="Header group")
    menu: Optional[str] = Field(None, description="Parent menu")
    extraction_timestamp: Optional[str] = Field(
        None, description="When content was extracted")

    @validator("item_id", "title", "url", "markdown_content")
    def validate_required_fields(cls, v: str) -> str:
        """Ensure required fields are not empty."""
        if not v.strip():
            raise ValueError("Required fields cannot be empty")
        return v.strip()

    @validator("url")
    def validate_url(cls, v: str) -> str:
        """Basic URL validation."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @property
    def content_length(self) -> int:
        """Get length of markdown content."""
        return len(self.markdown_content)

    @property
    def has_breadcrumbs(self) -> bool:
        """Check if breadcrumbs are available."""
        return self.breadcrumbs is not None and len(self.breadcrumbs) > 0


class ResumeInfo(BaseModel):
    """Model for resume information tracking."""

    total_items: int = Field(..., description="Total number of items found")
    existing_files: int = Field(..., description="Number of files that already exist")
    items_needing_processing: int = Field(...,
                                          description="Number of items that need processing")
    output_directory: Path = Field(..., description="Output directory path")
    existing_items: List[SidebarItem] = Field(
        default_factory=list, description="Items with existing files")
    pending_items: List[SidebarItem] = Field(
        default_factory=list,
        description="Items needing processing")

    @validator("total_items", "existing_files", "items_needing_processing")
    def validate_counts(cls, v: int) -> int:
        """Ensure counts are non-negative."""
        if v < 0:
            raise ValueError("Counts must be non-negative")
        return v

    @validator("output_directory", pre=True)
    def convert_to_path(cls, v):
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.existing_files / self.total_items) * 100.0

    @property
    def remaining_percentage(self) -> float:
        """Calculate remaining work percentage."""
        return 100.0 - self.completion_percentage

    def __str__(self) -> str:
        """String representation for display."""
        return (
            f"Resume Info: {self.existing_files}/{self.total_items} complete "
            f"({self.completion_percentage:.1f}%), {self.items_needing_processing} remaining"
        )
