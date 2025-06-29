"""Selectors service for Wyrm application.

This service centralizes all CSS selectors and XPath expressions used
throughout the application for web element identification.
"""

from selenium.webdriver.common.by import By


class SelectorsService:
    """Service for centralizing web element selectors."""

    def __init__(self, endpoint_version: str = "4.6") -> None:
        """Initialize the Selectors service.
        
        Args:
            endpoint_version: API version (e.g., "4.6", "3.6") to adapt selectors
        """
        self.endpoint_version = endpoint_version
        self._setup_version_specific_selectors()

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
    
    # Tab panel selector for multi-tab responses
    ACTIVE_TAB_PANEL = (By.CSS_SELECTOR, "div[role='tabpanel'][aria-hidden='false']")

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

    def _setup_version_specific_selectors(self) -> None:
        """Setup version-specific selectors based on endpoint version."""
        # Default structure type - will be dynamically detected
        self.CONTENT_STRUCTURE_TYPE = "unknown"
        
    def detect_structure_type(self, driver) -> str:
        """Dynamically detect the structure type from the actual DOM.
        
        Args:
            driver: WebDriver instance to examine the DOM
            
        Returns:
            Structure type: 'flat_with_trailing_header', 'hierarchical_with_leading_header', or 'mixed'
        """
        try:
            # Count different types of elements to determine structure
            headers_count = len(driver.find_elements("css selector", "li.toc-item-divider"))
            items_with_ids = len(driver.find_elements("css selector", "li.toc-item-highlight[id]"))
            items_without_ids = len(driver.find_elements("css selector", "li.toc-item-highlight:not([id])"))
            expandable_menus = len(driver.find_elements("css selector", "li.toc-item-highlight i.dds__icon--chevron-right"))
            
            # Log structure analysis
            import structlog
            logger = structlog.get_logger(__name__)
            logger.info(
                "Structure analysis",
                headers_count=headers_count,
                items_with_ids=items_with_ids,
                items_without_ids=items_without_ids,
                expandable_menus=expandable_menus
            )
            
            # Detect structure patterns
            if items_without_ids > items_with_ids and expandable_menus > 0:
                # Lots of items without IDs but with expandable menus - likely flat structure
                structure_type = "flat_with_trailing_header"
            elif headers_count > 0 and items_with_ids > items_without_ids:
                # Clear headers with mostly ID-based items - likely hierarchical
                structure_type = "hierarchical_with_leading_header"
            else:
                # Mixed or unclear structure
                structure_type = "mixed"
            
            logger.info("Detected structure type", structure_type=structure_type)
            self.CONTENT_STRUCTURE_TYPE = structure_type
            return structure_type
            
        except Exception as e:
            import structlog
            logger = structlog.get_logger(__name__)
            logger.warning("Failed to detect structure type", error=str(e))
            # Default to hierarchical
            self.CONTENT_STRUCTURE_TYPE = "hierarchical_with_leading_header"
            return "hierarchical_with_leading_header"
    
    def needs_enhanced_expansion(self, driver) -> bool:
        """Determine if enhanced expansion strategies are needed.
        
        Args:
            driver: WebDriver instance to examine
            
        Returns:
            True if enhanced expansion is recommended
        """
        try:
            # Check for indicators that suggest enhanced expansion is needed
            standalone_items = len(driver.find_elements(
                "css selector", 
                "li.toc-item-highlight[id]:not(:has(i.dds__icon--chevron-right)):not(:has(i.dds__icon--chevron-down))"
            ))
            
            unexpanded_menus = len(driver.find_elements(
                "css selector", 
                "li.toc-item-highlight:not([id]) i.dds__icon--chevron-right"
            ))
            
            # If we have many standalone items or unexpanded menus, use enhanced expansion
            return standalone_items > 5 or unexpanded_menus > 3
            
        except Exception:
            # If detection fails, err on the side of enhanced expansion
            return True
    
    def detect_endpoint_version(self, url: str) -> str:
        """Detect endpoint version from URL.
        
        Args:
            url: Target URL to analyze
            
        Returns:
            Detected version string (e.g., "3.6", "4.6")
        """
        import re
        # Extract version from URL like /versions/3.6/docs or /versions/4.6/docs
        version_match = re.search(r'/versions/([0-9]+\.[0-9]+)/', url)
        if version_match:
            return version_match.group(1)
        # Default to 4.6 if not detected
        return "4.6"
    
    @classmethod
    def create_for_url(cls, url: str) -> 'SelectorsService':
        """Create a SelectorsService instance configured for the given URL.
        
        Args:
            url: Target URL to configure selectors for
            
        Returns:
            Configured SelectorsService instance
        """
        temp_instance = cls()
        version = temp_instance.detect_endpoint_version(url)
        return cls(endpoint_version=version)

    @classmethod
    def get_expanded_icon(cls):
        """Get expanded icon selector."""
        return cls.EXPANDED_ICON
