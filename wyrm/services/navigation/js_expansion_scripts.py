"""JavaScript utilities for PowerFlex expansion path detection.

Contains JavaScript code for DOM traversal and expansion path detection
in PowerFlex documentation sites.
"""


def get_powerflex_expansion_script() -> str:
    """Generate JavaScript for PowerFlex expansion path detection.
    
    Returns:
        JavaScript code as a string for execution in browser
    """
    return """
        // PowerFlex-specific DOM traversal to find expansion path
        function findExpansionPath(targetId, targetText) {
            var expansionsNeeded = [];
            var targetFound = false;

            // First, try to find by ID
            var targetElement = document.getElementById(targetId);

            // If not found by ID, search by text content in li elements
            if (!targetElement) {
                var allLis = document.querySelectorAll('li.toc-item-highlight[id]');
                for (var i = 0; i < allLis.length; i++) {
                    var li = allLis[i];
                    if (li.textContent && li.textContent.trim().indexOf(targetText) !== -1) {
                        targetElement = li;
                        break;
                    }
                }
            }

            if (!targetElement) {
                return { found: false, expansions: [] };
            }

            // Check if already visible
            if (targetElement.offsetParent !== null) {
                return { found: true, expansions: [], alreadyVisible: true };
            }

            // Traverse up the DOM tree to find collapsed ancestor menus
            var current = targetElement.parentElement;
            while (current && current !== document.body) {
                // Look for li elements that don't have IDs (these are expandable menus)
                if (current.tagName === 'LI' &&
                    current.classList.contains('toc-item-highlight') &&
                    !current.hasAttribute('id')) {

                    // Check if this menu is collapsed (has right chevron)
                    var chevronRight = current.querySelector('i.dds__icon--chevron-right');
                    if (chevronRight && chevronRight.offsetParent !== null) {
                        // This menu needs to be expanded
                        var menuText = 'Unknown Menu';
                        var textDiv = current.querySelector('div.align-middle.dds__text-truncate');
                        if (textDiv && textDiv.textContent) {
                            menuText = textDiv.textContent.trim();
                        }

                        expansionsNeeded.unshift({ // Add to beginning (top-level first)
                            menuText: menuText,
                            xpath: getXPathForElement(chevronRight)
                        });
                    }
                }
                current = current.parentElement;
            }

            return { found: true, expansions: expansionsNeeded, alreadyVisible: false };
        }

        function getXPathForElement(element) {
            var xpath = '';
            var current = element;
            while (current && current.tagName) {
                var tagName = current.tagName.toLowerCase();
                var sibling = current.previousElementSibling;
                var index = 1;
                while (sibling) {
                    if (sibling.tagName && sibling.tagName.toLowerCase() === tagName) {
                        index++;
                    }
                    sibling = sibling.previousElementSibling;
                }
                xpath = '/' + tagName + '[' + index + ']' + xpath;
                current = current.parentElement;
            }
            return xpath;
        }

        return findExpansionPath(arguments[0], arguments[1]);
    """
