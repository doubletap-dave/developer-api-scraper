"""Selectors service for Wyrm application.

This service centralizes all CSS selectors and XPath expressions used
throughout the application for web element identification.
"""

from selenium.webdriver.common.by import By


class SelectorsService:
    """Service for centralizing web element selectors."""

    def __init__(self) -> None:
        """Initialize the Selectors service."""
        pass

    # Phase 1 Selectors
    SIDEBAR_CONTAINER = (By.CSS_SELECTOR, "div.filter-api-sidebar-wrapper")

    # Phase 2 Selectors (for Initial Structure Mapping)
    APP_API_DOC_ITEM = (
        By.CSS_SELECTOR,
        "app-api-doc-item",
    )  # Top-level wrapper for each entry

    # Selectors for LI *within* APP_API_DOC_ITEM
    SIDEBAR_HEADER_LI = (By.CSS_SELECTOR, "li.toc-item-divider")  # Header/Divider LI
    SIDEBAR_CLICKABLE_LI = (
        By.CSS_SELECTOR,
        "li.toc-item-highlight.clickable",
    )  # Clickable item or expandable menu LI

    # Selectors for text *within* the LI elements above
    HEADER_TEXT_ANCHOR = (By.CSS_SELECTOR, "a")  # Text is inside the <a> for headers
    ITEM_TEXT_SPAN = (
        By.CSS_SELECTOR,
        "span[id$='-sp']",
    )  # Text for simple items (ends with -sp)
    EXPANDABLE_MENU_TEXT_DIV = (
        By.CSS_SELECTOR,
        "div.align-middle.dds__text-truncate.dds__position-relative",
    )  # Text div for expandable menus

    # Selectors (for Expansion Clicking)
    SIDEBAR_MENU_EXPANDER_ICON = (By.CSS_SELECTOR, "i.dds__icon--chevron-right")
    # XPath to find the ancestor LI element for a given icon/link
    MENU_CLICKABLE_PARENT_XPATH = (
        "ancestor::li[contains(@class, 'toc-item-highlight') "
        "and contains(@class, 'clickable')]"
    )

    SIDEBAR_ITEM_LINK = "a.toc-link"  # Links within sidebar items
    EXPANDER_ICON = (
        By.CSS_SELECTOR,
        "i.dds__icon--chevron-right",
    )  # Icon for collapsed menus
    EXPANDED_ICON = (
        By.CSS_SELECTOR,
        "i.dds__icon--chevron-down",
    )  # Icon for expanded menus
    LOADER_OVERLAY = (
        By.ID,
        "loaderActive",
    )  # Processing overlay

    # Phase 3 Selectors
    CONTENT_PANE = (By.ID, "documentation")  # Main content pane container
    CONTENT_PANE_INNER_HTML_TARGET = (
        By.ID,
        "documentation"
    )  # Target the container div itself

    @classmethod
    def get_sidebar_container(cls):
        """Get sidebar container selector."""
        return cls.SIDEBAR_CONTAINER

    @classmethod
    def get_content_pane(cls):
        """Get content pane selector."""
        return cls.CONTENT_PANE

    @classmethod
    def get_expander_icon(cls):
        """Get expander icon selector."""
        return cls.EXPANDER_ICON

    @classmethod
    def get_expanded_icon(cls):
        """Get expanded icon selector."""
        return cls.EXPANDED_ICON
