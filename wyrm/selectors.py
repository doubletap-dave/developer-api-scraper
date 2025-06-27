from selenium.webdriver.common.by import By

# Phase 1 Selectors
SIDEBAR_CONTAINER = (By.CSS_SELECTOR, "div.filter-api-sidebar-wrapper")

# Phase 2 Selectors (for Initial Structure Mapping)
APP_API_DOC_ITEM = (
    By.CSS_SELECTOR,
    "app-api-doc-item",
)  # New: Top-level wrapper for each entry

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
)  # PRECISE Text div for expandable menus

# Selectors (for Expansion Clicking - Keep separate from mapping)
SIDEBAR_MENU_EXPANDER_ICON = (By.CSS_SELECTOR, "i.dds__icon--chevron-right")
# XPath to find the ancestor LI element for a given icon/link
MENU_CLICKABLE_PARENT_XPATH = (
    "ancestor::li[contains(@class, 'toc-item-highlight') "
    "and contains(@class, 'clickable')]"
)

# Remove incorrect/unused selectors
# SIDEBAR_MENU_LI = (By.CSS_SELECTOR, "li.toc-item-highlight") # Replaced
# SIDEBAR_MENU_TITLE_DIV = (By.CSS_SELECTOR, "div.align-middle") # Replaced
# SIDEBAR_ITEM_LI = (By.CSS_SELECTOR, "li.toc-item-group-items") # Incorrect
# SIDEBAR_ITEM_TEXT_SPAN = (By.CSS_SELECTOR, "span.unselectedSpan") # Incorrect

# Add other selectors here as needed for future phases

SIDEBAR_ITEM_LINK = "a.toc-link"  # Links within sidebar items
EXPANDER_ICON = (
    By.CSS_SELECTOR,
    "i.dds__icon--chevron-right",
)  # Icon for collapsed menus - Tuple format
EXPANDED_ICON = (
    By.CSS_SELECTOR,
    "i.dds__icon--chevron-down",
)  # Icon for expanded menus - Tuple format
LOADER_OVERLAY = (
    By.ID,
    "loaderActive",
)  # Processing overlay (Using ID for uniqueness and changed to tuple)

# Phase 3 Selectors
CONTENT_PANE = (By.ID, "documentation")  # Main content pane container
# CONTENT_PANE_MARKDOWN = (
#     By.CSS_SELECTOR,
#     "div#documentation markdown",
# )  # Old selector: Only gets first <markdown>
CONTENT_PANE_INNER_HTML_TARGET = (
    By.ID,
    "documentation"
) # New selector: Target the container div itself
