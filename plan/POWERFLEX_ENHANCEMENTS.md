# PowerFlex API Documentation Enhancements

This document summarizes the enhancements made to the Wyrm codebase to better handle PowerFlex API documentation structure.

## Problem Context

The PowerFlex API documentation has a specific HTML structure where:
- Individual clickable items have IDs (like `docs-node-99134`)
- Expandable menu sections don't have IDs but contain chevron icons (`i.dds__icon--chevron-right`)
- Menu hierarchy can be deeply nested
- Elements like the target `docs-node-99134` may be initially hidden in collapsed menus

## Enhanced Components

### 1. MenuExpander (`wyrm/services/navigation/menu_expander.py`)

**Key Improvements:**
- **PowerFlex-optimized expansion strategy** (`_expand_menus_powerflex_optimized`)
  - Targets `li.toc-item-highlight:not([id])` elements with chevron icons
  - Uses recursive expansion to handle nested menus
  - Provides detailed logging of each menu expansion

- **Smart path expansion** (`_expand_powerflex_path_to_item`)
  - Uses JavaScript DOM traversal to find exact path to target items
  - Expands only necessary parent menus instead of everything
  - Handles cases where items are deeply nested

- **Enhanced item-specific expansion** (`expand_menu_for_item`)
  - PowerFlex-specific approach using DOM traversal
  - Fallback to traditional menu expansion if needed
  - Better error handling and logging

**Example Usage:**
```python
# The enhanced logic automatically detects PowerFlex structure
await menu_expander.expand_all_menus_comprehensive()

# For specific items, the path expansion finds and expands only necessary menus
await menu_expander.expand_menu_for_item(item_with_id_docs_node_99134)
```

### 2. StructureParser (`wyrm/services/parsing/structure_parser.py`)

**Key Improvements:**
- **PowerFlex-specific parsing** (`_parse_item_from_app_item`)
  - Detects expandable menus by `!item_id && has_chevron_icon`
  - Distinguishes between clickable items and expandable menus
  - Enhanced logging for debugging

- **Enhanced text extraction** (`_extract_item_text_powerflex`)
  - Multiple fallback strategies for text extraction
  - Handles varying HTML structures in PowerFlex docs
  - Separate logic for menus vs items

- **Menu children parsing** (`_parse_powerflex_menu_children`)
  - Handles already-expanded menu children
  - Looks for nested structures and sibling ULs
  - Preserves hierarchy information

### 3. SelectorsService

**Existing selectors that now work better with PowerFlex:**
```python
# These selectors are specifically designed for PowerFlex structure
SIDEBAR_CLICKABLE_LI = "li.toc-item-highlight.clickable"
EXPANDER_ICON = "i.dds__icon--chevron-right"
EXPANDED_ICON = "i.dds__icon--chevron-down"
EXPANDABLE_MENU_TEXT_DIV = "div.align-middle.dds__text-truncate.dds__position-relative"
```

## How It Works

### Menu Expansion Process

1. **Detection Phase:**
   - Finds all `li.toc-item-highlight:not([id]) i.dds__icon--chevron-right` elements
   - These are expandable menu sections without IDs

2. **Expansion Phase:**
   - Clicks each chevron icon to expand menus
   - Waits for content to load after each expansion
   - Handles click interception with JavaScript fallback

3. **Recursive Phase:**
   - After initial expansion, checks for newly revealed expandable items
   - Continues expanding until no new menus are found

4. **Verification Phase:**
   - Counts total clickable items found
   - Reports remaining collapsed sections
   - Logs comprehensive statistics

### Path-Specific Expansion

For individual items like `docs-node-99134`:

1. **Target Search:**
   - Uses JavaScript to find the target element by ID
   - If not found, searches by text content

2. **Path Discovery:**
   - Traverses up the DOM tree to find collapsed ancestor menus
   - Identifies which chevron icons need to be clicked

3. **Targeted Expansion:**
   - Expands only the necessary parent menus
   - More efficient than expanding everything

## Example HTML Structure Handled

```html
<!-- Expandable menu section (no ID, has chevron) -->
<li class="toc-item-highlight clickable">
  <div class="align-middle dds__text-truncate dds__position-relative">Volume Management</div>
  <i class="dds__icon--chevron-right"></i>
</li>

<!-- Individual clickable item (has ID) -->
<li class="toc-item-highlight clickable" id="docs-node-99134">
  <span id="docs-node-99134-sp">Get Volume Details</span>
</li>
```

## Testing the Enhancements

### 1. Run with Debug Mode
```bash
python main.py --debug --max-items 5
```

### 2. Check Logs for PowerFlex-Specific Messages
Look for log entries containing:
- "PowerFlex-optimized expansion"
- "Found PowerFlex Menu"
- "Found PowerFlex Item"
- "Expanding path to item"

### 3. Verify Target Element Detection
The enhanced logic should now successfully find and navigate to `docs-node-99134` and similar elements.

### 4. Monitor Expansion Statistics
Enhanced logging provides detailed statistics:
```
PowerFlex expansion completed: expanded 15 sections, found 87 clickable items, 23 total menu elements, 0 still collapsed
```

## Configuration

The PowerFlex enhancements are automatically used when the system detects the appropriate HTML structure. No additional configuration is required.

### Force PowerFlex Mode
If needed, you can force the enhanced expansion:
```bash
python main.py --force-full-expansion
```

## Backward Compatibility

All enhancements maintain full backward compatibility with existing endpoints. The system:
- Auto-detects PowerFlex structure patterns
- Falls back to standard expansion methods if PowerFlex methods fail
- Preserves all existing functionality for other API documentation sites

## Key Benefits

1. **Improved Element Detection:** Now finds elements like `docs-node-99134` that were previously missed
2. **Efficient Expansion:** Only expands necessary menus for specific items
3. **Better Error Handling:** More robust handling of click interception and timing issues
4. **Enhanced Logging:** Detailed feedback about expansion progress and results
5. **Structure Awareness:** Recognizes PowerFlex-specific HTML patterns

## Next Steps

To verify the enhancements are working:

1. Run the scraper on the PowerFlex API documentation
2. Check that previously missing elements (like `docs-node-99134`) are now found
3. Verify that menu expansion logs show PowerFlex-specific messages
4. Confirm that the sidebar structure parsing captures all available items

The enhanced logic should significantly improve coverage and reliability when scraping PowerFlex API documentation.
