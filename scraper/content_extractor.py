import logging

# Import BeautifulSoup
from bs4 import BeautifulSoup
from markdownify import markdownify
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webdriver import WebDriver
# Import By for more specific searches within the container
from selenium.webdriver.common.by import By

from . import selectors


async def extract_and_convert_content(driver: WebDriver) -> str | None:
    """
    Finds the main content container (div#documentation).
    Looks for either 'app-api-doc-endpoint' or 'markdown' within its 'div.dds__m-2' child.
    Extracts the inner HTML from the specific element found.
    Converts the extracted HTML to Markdown using appropriate options.
    Returns the Markdown string or None if content cannot be extracted or converted.
    """
    logging.debug("Attempting to extract and convert content...")
    try:
        # Find the main content pane first
        content_pane = driver.find_element(*selectors.CONTENT_PANE_INNER_HTML_TARGET)
        pane_selector_str = f"#{selectors.CONTENT_PANE_INNER_HTML_TARGET[1]}"
        logging.debug(f"Found content pane element: {pane_selector_str}")

        html_content = None
        markdown_options = {"heading_style": "ATX"} # Default options
        content_source_tag = "unknown"

        # Strategy 1: Look for structured API endpoint content as DESCENDANT of content_pane
        try:
            endpoint_element = content_pane.find_element(
                By.CSS_SELECTOR, "app-api-doc-endpoint" # Search anywhere under content_pane
            )
            logging.debug(f"Found '<app-api-doc-endpoint>' structure inside {pane_selector_str}.")
            html_content = endpoint_element.get_attribute("innerHTML")
            content_source_tag = "app-api-doc-endpoint"

            # --- PRE-PROCESSING STRATEGY for app-api-doc-endpoint ---
            if html_content:
                logging.debug("Pre-processing HTML for app-api-doc-endpoint using BeautifulSoup...")
                soup = BeautifulSoup(html_content, 'html.parser')
                markdown_pieces = []
                # Define selectors for key block elements *within* app-api-doc-endpoint
                # Prioritize elements that provide structure
                # This list might need refinement based on inspection
                key_block_selectors = [
                    "h3", "h4", "p",
                    "pre", "ul", "ol",
                    "div.dds__table", # Tables within divs
                    "div.dds__table-responsive", # Responsive table wrappers
                    "table", # Direct tables if not in divs
                    "div.dds__mt-2 > markdown", # Description markdown sections
                    "div.dds__my-4", # Spacing divs often wrap sections
                ]

                # Find all elements matching the selectors directly under the root
                # Use find_all with recursive=False initially?
                # Or just find all and let the order dictate?
                # Let's find all potential blocks and process them.
                # We might need a more sophisticated way to handle nesting if needed.
                potential_blocks = soup.find_all(key_block_selectors, recursive=True)

                logging.debug(f"Found {len(potential_blocks)} potential blocks for conversion.")

                md_opts = {"heading_style": "ATX"} # Simple options for individual pieces
                for block in potential_blocks:
                    # Avoid double-processing nested blocks if parent already handled
                    # Simple check: if parent is also in potential_blocks, skip? Risky.
                    # Better: convert block to string, check if non-empty, then markdownify
                    block_html = str(block)
                    if block_html.strip(): # Ensure there's content
                        # Attempt markdown conversion for the individual block
                        try:
                            md_piece = markdownify(block_html, **md_opts).strip()
                            if md_piece:
                                markdown_pieces.append(md_piece)
                        except Exception as piece_e:
                            logging.warning(f"Failed to markdownify piece: {block.name}. Error: {piece_e}")

                if not markdown_pieces:
                     logging.warning("Pre-processing found blocks, but markdown conversion resulted in empty list.")
                     return None

                # Join the pieces with double newlines
                processed_markdown_content = "\n\n".join(markdown_pieces)
                logging.info(f"Successfully pre-processed app-api-doc-endpoint content into {len(markdown_pieces)} pieces.")
                return processed_markdown_content # Return the processed markdown
            else:
                logging.warning("Found app-api-doc-endpoint tag, but it was empty.")
                return None
            # --- END PRE-PROCESSING --- #

        except NoSuchElementException:
            logging.debug(f"No '<app-api-doc-endpoint>' found inside {pane_selector_str}. Checking for general '<markdown>'...")
            # Strategy 2: Look for general markdown content as DESCENDANT of content_pane
            try:
                markdown_element = content_pane.find_element(
                    By.CSS_SELECTOR, "markdown" # Search anywhere under content_pane
                )
                logging.debug(f"Found '<markdown>' structure inside {pane_selector_str}.")
                html_content = markdown_element.get_attribute("innerHTML")
                content_source_tag = "markdown"
                # Use default markdown_options for general markdown
                markdown_options = {"heading_style": "ATX"}

                # --- Standard Conversion for <markdown> tag ---
                if not html_content or not html_content.strip():
                    logging.warning(f"Found {content_source_tag} tag, but it was empty.")
                    return None

                html_len = len(html_content)
                logging.debug(f"Extracted {html_len} bytes of HTML from '{content_source_tag}'. Converting to Markdown...")
                markdown_content = markdownify(html_content, **markdown_options)
                if not markdown_content or not markdown_content.strip():
                    logging.warning(f"Conversion of {content_source_tag} resulted in empty markdown.")
                    return None

                logging.info(f"Successfully extracted content from '{content_source_tag}' and converted to Markdown.")
                return markdown_content.strip()
                # --- END Standard Conversion ---

            except NoSuchElementException:
                # Update the warning message
                logging.warning(
                    f"Could not find 'app-api-doc-endpoint' OR 'markdown' "
                    f"as a descendant inside {pane_selector_str}."
                )
                return None # Neither expected structure found

    except NoSuchElementException:
        pane_selector_str = f"#{selectors.CONTENT_PANE_INNER_HTML_TARGET[1]}"
        logging.error(
            f"Content pane element ({pane_selector_str}) not found "
            "when trying to extract content."
        )
        return None
    except Exception as e:
        logging.exception(
            "An unexpected error occurred during content extraction/conversion: " f"{e}"
        )
        return None
