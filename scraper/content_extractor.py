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
    Looks for either 'app-api-doc-endpoint' or 'markdown' within it.
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

        # Strategy 1: Look for structured API endpoint content as DESCENDANT of content_pane
        try:
            endpoint_element = content_pane.find_element(
                By.CSS_SELECTOR, "app-api-doc-endpoint" # Search anywhere under content_pane
            )
            logging.debug(f"Found '<app-api-doc-endpoint>' structure inside {pane_selector_str}.")
            html_content = endpoint_element.get_attribute("innerHTML")
            if not html_content:
                logging.warning("Found app-api-doc-endpoint tag, but it was empty.")
                return None

            # --- REVISED PRE-PROCESSING STRATEGY for app-api-doc-endpoint ---
            logging.debug("Pre-processing HTML for app-api-doc-endpoint using BeautifulSoup...")
            soup = BeautifulSoup(html_content, 'html.parser')
            markdown_pieces = []
            md_opts = {"heading_style": "ATX"} # Options for markdownify

            # Selectors for general sections (excluding responses initially)
            general_selectors = [
                "div.dds__mb-4",  # Contains H3 (Method/Title) and Path Pre
                "div > markdown", # Top-level description paragraphs
                "app-api-doc-security", # Security (if present)
                "div.dds__my-4 > app-api-doc-server", # Servers section
                "app-show-parameters", # Parameter sections (Path, Query, Header, Cookie)
            ]

            processed_tags = set() # Keep track of tags to avoid processing children if parent done

            # Process general sections first
            for selector in general_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Simple check to avoid processing children if parent already captured
                    is_child_of_processed = False
                    parent = element.parent
                    while parent and parent != soup:
                        if parent in processed_tags:
                            is_child_of_processed = True
                            break
                        parent = parent.parent
                    if is_child_of_processed or element in processed_tags:
                        continue

                    if element.text.strip():
                        try:
                            md_piece = markdownify(str(element), **md_opts).strip()
                            if md_piece:
                                markdown_pieces.append(md_piece)
                                processed_tags.add(element) # Mark this tag as processed
                        except Exception as piece_e:
                            logging.warning(f"Failed to markdownify general piece: {element.name}. Error: {piece_e}")

            # Process Responses section specifically and carefully
            response_section = soup.find("app-api-doc-response")
            if response_section:
                logging.debug("Processing app-api-doc-response section...")
                responses_header = response_section.find("h4")
                if responses_header and responses_header not in processed_tags:
                    markdown_pieces.append(markdownify(str(responses_header), **md_opts).strip())
                    processed_tags.add(responses_header)

                response_tab_content = response_section.select_one("div.dds__tabs__pane-container > div.dds__tabs__pane-custom")
                if response_tab_content:
                    response_desc = response_tab_content.select_one("div.dds__mt-2 > markdown")
                    if response_desc and response_desc not in processed_tags:
                        markdown_pieces.append(markdownify(str(response_desc), **md_opts).strip())
                        processed_tags.add(response_desc)

                    body_content = response_tab_content.find("app-api-doc-body-content")
                    if body_content:
                        model_content = body_content.find("app-api-doc-model", id="application/json")
                        if model_content:
                            logging.debug("Found app-api-doc-model#application/json.")
                            json_header_button = body_content.select_one('button[id="example-tab-application/json"]')
                            if json_header_button and json_header_button not in processed_tags:
                                markdown_pieces.append(f"### {json_header_button.text.strip()}")
                                processed_tags.add(json_header_button)

                            schema_pane = model_content.find("div", {"role": "tabpanel", "id": "schema"})
                            if schema_pane:
                                logging.debug("Found schema tab panel.")
                                schema_button = model_content.select_one('button[id="schema-tab"]')
                                if schema_button and schema_button not in processed_tags:
                                    markdown_pieces.append(f"### {schema_button.text.strip()}")
                                    processed_tags.add(schema_button)

                                    schema_table = schema_pane.select_one("div.dds__table > table.dds__table")
                                    if schema_table and schema_table not in processed_tags:
                                        logging.debug("Found schema table. Converting...")
                                        try:
                                            md_piece = markdownify(str(schema_table), **md_opts).strip()
                                            if md_piece:
                                                markdown_pieces.append(md_piece)
                                                processed_tags.add(schema_table) # Mark table as processed
                                            else:
                                                logging.warning("Schema table conversion resulted in empty markdown.")
                                        except Exception as table_e:
                                            logging.warning(f"Failed to markdownify schema table: {table_e}")
                                    else:
                                        logging.warning("Schema table not found or already processed.")
                            else:
                                logging.warning("Schema tab pane not found.")
                        else:
                            logging.warning("Model content not found.")
                    else:
                        logging.warning("Body content not found.")
                else:
                    logging.warning("Active response tab content container not found.")
            else:
                logging.debug("No app-api-doc-response section found.")

            if not markdown_pieces:
                logging.warning("Pre-processing did not yield any markdown pieces.")
                return None

            # Join the pieces, filtering out potential empty strings
            processed_markdown_content = "\n\n".join(filter(None, markdown_pieces))
            logging.info(f"Successfully pre-processed app-api-doc-endpoint content into {len(markdown_pieces)} pieces.")
            return processed_markdown_content
            # --- END REVISED PRE-PROCESSING --- #

        except NoSuchElementException:
            logging.debug(f"No '<app-api-doc-endpoint>' found inside {pane_selector_str}. Checking for general '<markdown>'...")
            # Strategy 2: Look for general markdown content (unchanged)
            try:
                markdown_element = content_pane.find_element(
                    By.CSS_SELECTOR, "markdown"
                )
                logging.debug(f"Found '<markdown>' structure inside {pane_selector_str}.")
                html_content = markdown_element.get_attribute("innerHTML")
                if not html_content or not html_content.strip():
                    logging.warning("Found markdown tag, but it was empty.")
                    return None

                markdown_options = {"heading_style": "ATX"}
                markdown_content = markdownify(html_content, **markdown_options)
                if not markdown_content or not markdown_content.strip():
                    logging.warning("Conversion of markdown resulted in empty markdown.")
                    return None

                logging.info("Successfully extracted content from '<markdown>' and converted to Markdown.")
                return markdown_content.strip()

            except NoSuchElementException:
                logging.warning(
                    f"Could not find 'app-api-doc-endpoint' OR 'markdown' "
                    f"as a descendant inside {pane_selector_str}."
                )
                return None

    except NoSuchElementException:
        pane_selector_str = f"#{selectors.CONTENT_PANE_INNER_HTML_TARGET[1]}"
        logging.error(f"Content pane element ({pane_selector_str}) not found.")
        return None
    except Exception as e:
        logging.exception(f"An unexpected error occurred during content extraction/conversion: {e}")
        return None