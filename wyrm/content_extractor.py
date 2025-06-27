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
    Enhanced content extractor that captures all rich information from Dell Developer API docs.
    
    Extracts:
    - API endpoint details (method, path, description)
    - Code examples (curl commands, responses)
    - Parameter tables (path, query, header, cookie)
    - Response schemas with all HTTP status codes
    - Request body schemas
    - Security information
    - Server information
    
    Returns the complete Markdown content or None if extraction fails.
    """
    logging.debug("Attempting to extract and convert content with enhanced extractor...")
    try:
        # Find the main content pane first
        content_pane = driver.find_element(*selectors.CONTENT_PANE_INNER_HTML_TARGET)
        pane_selector_str = f"#{selectors.CONTENT_PANE_INNER_HTML_TARGET[1]}"
        logging.debug(f"Found content pane element: {pane_selector_str}")

        # Get the full HTML content of the documentation div
        html_content = content_pane.get_attribute("innerHTML")
        if not html_content:
            logging.warning("Content pane was found but is empty.")
            return None

        # Parse with BeautifulSoup for better HTML manipulation
        soup = BeautifulSoup(html_content, 'html.parser')
        markdown_pieces = []
        md_opts = {"heading_style": "ATX", "strip": ["script", "style"]}

        # Strategy 1: Handle API endpoint documentation (app-api-doc-endpoint)
        endpoint_element = soup.find("app-api-doc-endpoint")
        if endpoint_element:
            logging.debug("Found app-api-doc-endpoint structure - extracting API documentation")
            return await _extract_api_endpoint_content(endpoint_element, md_opts, driver)

        # Strategy 2: Handle standalone model/schema documentation (app-api-doc-model)
        model_element = soup.find("app-api-doc-model")
        if model_element:
            logging.debug("Found standalone app-api-doc-model structure")
            return await _extract_model_content(model_element, md_opts)

        # Strategy 3: Handle general markdown content
        markdown_elements = soup.find_all("markdown")
        if markdown_elements:
            logging.debug(f"Found {len(markdown_elements)} markdown elements - extracting general content")
            return await _extract_markdown_content(markdown_elements, md_opts)

        # Strategy 4: Fallback - extract all text content
        logging.warning("No recognized content structure found, attempting fallback extraction")
        return await _extract_fallback_content(soup, md_opts)

    except NoSuchElementException:
        pane_selector_str = f"#{selectors.CONTENT_PANE_INNER_HTML_TARGET[1]}"
        logging.error(f"Content pane element ({pane_selector_str}) not found.")
        return None
    except Exception as e:
        logging.exception(f"An unexpected error occurred during content extraction/conversion: {e}")
        return None


async def _extract_api_endpoint_content(endpoint_element, md_opts, driver) -> str:
    """Extract content from app-api-doc-endpoint structure"""
    markdown_pieces = []
    
    # 1. Extract method, title, and path from the header section
    method_title_section = endpoint_element.find("div", class_="dds__mb-4")
    if method_title_section:
        # Extract HTTP method and title together
        method_element = method_title_section.find("app-show-http-method")
        title_element = method_title_section.find("span", class_="dds__pl-3")
        try_button = method_title_section.find("button", string="Try It")
        
        # Build the header line
        header_parts = []
        if method_element:
            method_span = method_element.find("span", class_=lambda x: x and "http-method" in x)
            if method_span:
                method = method_span.get_text(strip=True)
                header_parts.append(method)
        
        if title_element:
            title = title_element.get_text(strip=True)
            header_parts.append(title)
        
        if try_button:
            header_parts.append("Try It")
        
        if header_parts:
            markdown_pieces.append(f"### {' '.join(header_parts)}")
    
    # 2. Extract API path (should be in the first markdown element under the header)
    path_markdown = endpoint_element.find("markdown")
    if path_markdown:
        path_content = path_markdown.find("pre")
        if path_content:
            path_text = path_content.get_text(strip=True)
            markdown_pieces.append(f"```\n{path_text}\n```")
    
    # 3. Extract description (should be in the second markdown element or in dds__mt-2 div)
    desc_container = endpoint_element.find("div", class_="dds__mt-2")
    if desc_container:
        desc_markdown = desc_container.find("markdown")
        if desc_markdown and desc_markdown != path_markdown:  # Avoid duplicate
            desc_text = desc_markdown.get_text(strip=True)
            if desc_text:
                markdown_pieces.append(desc_text)
    
    # 4. Extract security information
    security_element = endpoint_element.find("app-api-doc-security")
    if security_element and security_element.get_text(strip=True):
        security_md = markdownify(str(security_element), **md_opts).strip()
        if security_md:
            markdown_pieces.append("## Security")
            markdown_pieces.append(security_md)
    
    # 5. Extract server information
    server_element = endpoint_element.find("app-api-doc-server")
    if server_element:
        server_md = markdownify(str(server_element), **md_opts).strip()
        if server_md:
            markdown_pieces.append(server_md)
    
    # 6. Extract all parameter sections (Path, Query, Header, Cookie)
    param_elements = endpoint_element.find_all("app-show-parameters")
    for param_element in param_elements:
        param_md = markdownify(str(param_element), **md_opts).strip()
        if param_md:
            markdown_pieces.append(param_md)
    
    # 7. Extract response information with all status codes
    response_element = endpoint_element.find("app-api-doc-response")
    if response_element:
        response_content = await _extract_response_content(response_element, md_opts, driver)
        if response_content:
            markdown_pieces.append(response_content)
    
    # Join all pieces
    if not markdown_pieces:
        logging.warning("No content pieces extracted from app-api-doc-endpoint")
        return None
    
    result = "\n\n".join(filter(None, markdown_pieces))
    logging.info(f"Successfully extracted API endpoint content with {len(markdown_pieces)} sections")
    return result


async def _extract_response_content(response_element, md_opts, driver) -> str:
    """Extract detailed response information including all status codes and schemas"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    import time
    import logging
    
    response_pieces = []
    
    # Add responses header
    response_pieces.append("## Responses")
    
    if not driver:
        logging.warning("No driver available for response tab extraction, falling back to single response")
        return await _extract_single_response_content(response_element, md_opts)
    
    try:
        # Find all response tab buttons by looking for buttons with status codes
        response_tabs = driver.find_elements(
            By.CSS_SELECTOR, 
            "app-api-doc-response button[role='tab']"
        )
        
        if not response_tabs:
            logging.debug("No response tabs found, extracting single response")
            return await _extract_single_response_content(response_element, md_opts)
        
        logging.debug(f"Found {len(response_tabs)} response tabs")
        
        # Extract content from each response tab
        for i in range(len(response_tabs)):
            try:
                # Re-find the response tabs to avoid stale element references
                current_response_tabs = driver.find_elements(
                    By.CSS_SELECTOR, 
                    "app-api-doc-response button[role='tab']"
                )
                
                if i >= len(current_response_tabs):
                    logging.warning(f"Response tab {i} no longer exists, skipping")
                    continue
                
                tab_button = current_response_tabs[i]
                
                # Get the status code from the tab
                try:
                    status_element = tab_button.find_element(By.CSS_SELECTOR, ".dds__tabs__tab__label")
                    status_code = status_element.text.strip() if status_element else f"Response {i+1}"
                except Exception:
                    status_code = f"Response {i+1}"
                
                logging.debug(f"Clicking response tab: {status_code}")
                
                # Click the tab to activate it
                driver.execute_script("arguments[0].click();", tab_button)
                
                # Wait a moment for content to load
                time.sleep(0.5)
                
                # Wait for the content to update
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#CenteredTabContent"))
                )
                
                # Extract the response content for this tab
                tab_response = await _extract_single_response_tab_content(driver, status_code, md_opts)
                if tab_response:
                    response_pieces.append(tab_response)
                    
            except (TimeoutException, WebDriverException) as e:
                logging.warning(f"Failed to extract response tab {i}: {e}")
                continue
                
    except Exception as e:
        logging.error(f"Error extracting response tabs: {e}")
        # Fall back to single response extraction
        return await _extract_single_response_content(response_element, md_opts)
    
    return "\n\n".join(filter(None, response_pieces))


async def _extract_single_response_content(response_element, md_opts) -> str:
    """Extract response content from BeautifulSoup element (fallback method)"""
    response_pieces = []
    
    # Add responses header
    response_pieces.append("## Responses")
    
    # Find all response tabs (status codes)
    tab_buttons = response_element.find_all("button", {"role": "tab"})
    active_tab = None
    
    for button in tab_buttons:
        if "aria-selected" in button.attrs and button["aria-selected"] == "true":
            active_tab = button
            break
    
    if active_tab:
        # Extract status code and description from active tab
        status_code = active_tab.find("span", class_="dds__tabs__tab__label")
        if status_code:
            status_text = status_code.get_text(strip=True)
            response_pieces.append(f"### {status_text}")
    
    # Extract response description
    response_desc = response_element.find("div", class_="dds__mt-2")
    if response_desc:
        markdown_elem = response_desc.find("markdown")
        if markdown_elem:
            desc_text = markdown_elem.get_text(strip=True)
            if desc_text:
                response_pieces.append(desc_text)
    
    # Extract response body content and schemas
    body_content = response_element.find("app-api-doc-body-content")
    if body_content:
        # Extract content type tabs
        content_type_tabs = body_content.find_all("button", {"role": "tab"})
        for tab in content_type_tabs:
            content_type = tab.get_text(strip=True)
            if content_type:
                response_pieces.append(f"### {content_type}")
        
        # Extract schema information
        model_elements = body_content.find_all("app-api-doc-model")
        for model in model_elements:
            model_content = await _extract_model_content(model, md_opts)
            if model_content:
                response_pieces.append(model_content)
    
    return "\n\n".join(filter(None, response_pieces))


async def _extract_single_response_tab_content(driver, status_code: str, md_opts) -> str:
    """Extract content from a single response tab using Selenium driver"""
    from bs4 import BeautifulSoup
    import logging
    
    try:
        # Get the updated page content after tab click
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Find the active tab content
        tab_content = soup.find("div", {"id": "CenteredTabContent"})
        if not tab_content:
            logging.warning(f"No tab content found for status {status_code}")
            return None
        
        response_pieces = []
        response_pieces.append(f"### {status_code}")
        
        # Extract response description
        markdown_elem = tab_content.find("markdown")
        if markdown_elem:
            desc_text = markdown_elem.get_text(strip=True)
            if desc_text:
                response_pieces.append(desc_text)
        
        # Extract content type information
        body_content = tab_content.find("app-api-doc-body-content")
        if body_content:
            # Extract content type tabs
            content_type_tabs = body_content.find_all("button", {"role": "tab"})
            for tab in content_type_tabs:
                content_type = tab.get_text(strip=True)
                if content_type and content_type not in ["Schema"]:  # Avoid duplicate Schema headers
                    response_pieces.append(f"### {content_type}")
            
            # Extract schema information
            model_elements = body_content.find_all("app-api-doc-model")
            for model in model_elements:
                model_content = await _extract_model_content(model, md_opts)
                if model_content:
                    response_pieces.append(model_content)
        
        return "\n\n".join(filter(None, response_pieces))
        
    except Exception as e:
        logging.error(f"Error extracting tab content for {status_code}: {e}")
        return None


async def _extract_model_content(model_element, md_opts) -> str:
    """Extract content from app-api-doc-model structure with proper schema formatting"""
    model_pieces = []
    
    # Extract model title
    title_element = model_element.find("h3")
    if title_element:
        title = title_element.get_text(strip=True)
        if title:
            model_pieces.append(f"### {title}")
    
    # Extract schema table with proper hierarchical structure
    schema_table = model_element.find("table", class_="dds__table")
    if schema_table:
        schema_md = _extract_schema_table(schema_table)
        if schema_md:
            model_pieces.append("### Schema")
            model_pieces.append(schema_md)
    
    return "\n\n".join(filter(None, model_pieces))


def _extract_schema_table(table) -> str:
    """Extract schema table with proper hierarchical formatting"""
    schema_items = []
    
    # Find all table rows
    rows = table.find_all("tr", class_="align-middle")
    
    for row in rows:
        schema_item = _extract_schema_row(row)
        if schema_item:
            schema_items.append(schema_item)
    
    if not schema_items:
        return None
    
    # Format as a proper schema documentation
    result = []
    result.append("| Property | Type | Description |")
    result.append("|----------|------|-------------|")
    
    for item in schema_items:
        # Format with proper indentation for nested properties
        indent = "  " * item.get("level", 0)
        property_name = f"{indent}{item['name']}"
        data_type = item.get("type", "")
        description = item.get("description", "")
        
        # Add allowed values if present
        if item.get("allowed_values"):
            if description:
                description += f" Allowed values: {', '.join(item['allowed_values'])}"
            else:
                description = f"Allowed values: {', '.join(item['allowed_values'])}"
        
        result.append(f"| {property_name} | {data_type} | {description} |")
    
    return "\n".join(result)


def _extract_schema_row(row) -> dict | None:
    """Extract schema information from a single table row"""
    # Get the level of nesting from CSS classes
    level_div = row.find("div", class_=lambda x: x and "level-" in x)
    level = 0
    if level_div:
        level_classes = level_div.get("class", [])
        for cls in level_classes:
            if cls.startswith("level-"):
                try:
                    level = int(cls.split("-")[1])
                except (ValueError, IndexError):
                    level = 0
                break
    
    # Extract property name
    property_name_span = row.find("span", class_="dds__text-dark")
    if not property_name_span:
        # Try alternative selector for root object
        property_name_span = row.find("div", class_="dds__d-flex dds__flex-column dds__w-100")
        if property_name_span:
            # For root objects, get the first meaningful text
            text_content = property_name_span.get_text(strip=True)
            if text_content and not text_content.startswith("object"):
                property_name = text_content.split()[0] if text_content else ""
            else:
                property_name = "System"  # Use the actual object name instead of "root"
        else:
            return None
    else:
        property_name = property_name_span.get_text(strip=True)
    
    if not property_name:
        return None
    
    # Extract data type
    data_type = ""
    type_element = row.find("app-show-data-type")
    if type_element:
        type_spans = type_element.find_all("span")
        type_parts = []
        for span in type_spans:
            span_text = span.get_text(strip=True)
            if span_text and span_text not in ["", "mr-1"]:
                type_parts.append(span_text)
        # Remove duplicates and clean up
        unique_parts = []
        for part in type_parts:
            if part not in unique_parts:
                unique_parts.append(part)
        data_type = " ".join(unique_parts)
    
    # Extract description
    description = ""
    desc_element = row.find("app-show-property-description")
    if desc_element:
        desc_span = desc_element.find("span")
        if desc_span:
            description = desc_span.get_text(strip=True)
    
    # Extract allowed values
    allowed_values = []
    allowed_values_div = row.find("div", class_="w-90")
    if allowed_values_div:
        value_elements = allowed_values_div.find_all("small", class_="bgWhite")
        for value_elem in value_elements:
            value_text = value_elem.get_text(strip=True)
            if value_text:
                allowed_values.append(value_text)
    
    return {
        "name": property_name,
        "type": data_type,
        "description": description,
        "level": level,
        "allowed_values": allowed_values
    }


async def _extract_markdown_content(markdown_elements, md_opts) -> str:
    """Extract content from general markdown elements with enhanced processing"""
    markdown_pieces = []
    
    for markdown_element in markdown_elements:
        # Create a copy to work with
        element_copy = BeautifulSoup(str(markdown_element), 'html.parser')
        
        # Extract and preserve code blocks with syntax highlighting
        code_blocks = element_copy.find_all("pre")
        code_replacements = {}
        
        for i, code_block in enumerate(code_blocks):
            # Determine language from class attribute
            language = "none"
            code_element = code_block.find("code")
            if code_element:
                classes = code_element.get("class", [])
                if isinstance(classes, list):
                    for cls in classes:
                        if cls.startswith("language-"):
                            language = cls.replace("language-", "")
                            break
                code_content = code_element.get_text()
            else:
                code_content = code_block.get_text()
            
            # Create markdown code block
            code_markdown = f"```{language}\n{code_content}\n```"
            
            # Replace with HTML comment placeholder
            placeholder = f"CODEBLOCK{i}PLACEHOLDER"
            code_replacements[placeholder] = code_markdown
            code_block.replace_with(placeholder)
        
        # Extract and preserve tables
        tables = element_copy.find_all("table")
        table_replacements = {}
        
        for i, table in enumerate(tables):
            # Clean table for better conversion
            _clean_table_for_conversion(table)
            
            # Convert table to markdown
            table_md = markdownify(str(table), **md_opts).strip()
            if table_md:
                placeholder = f"TABLE{i}PLACEHOLDER"
                table_replacements[placeholder] = table_md
                table.replace_with(placeholder)
        
        # Process the remaining content
        remaining_html = str(element_copy)
        
        # Convert to markdown
        markdown_content = markdownify(remaining_html, **md_opts).strip()
        
        # Restore code blocks and tables
        for placeholder, replacement in code_replacements.items():
            markdown_content = markdown_content.replace(placeholder, f"\n{replacement}\n")
        
        for placeholder, replacement in table_replacements.items():
            markdown_content = markdown_content.replace(placeholder, f"\n{replacement}\n")
        
        if markdown_content:
            markdown_pieces.append(markdown_content)
    
    if not markdown_pieces:
        logging.warning("No markdown content extracted from markdown elements")
        return None
    
    result = "\n\n".join(filter(None, markdown_pieces))
    logging.info(f"Successfully extracted general markdown content with {len(markdown_pieces)} pieces")
    return result


async def _extract_fallback_content(soup, md_opts) -> str:
    """Fallback extraction method for unrecognized content structures"""
    # Try to extract any meaningful content
    content_pieces = []
    
    # Look for headers
    headers = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    for header in headers:
        header_text = header.get_text(strip=True)
        if header_text:
            level = "#" * int(header.name[1])
            content_pieces.append(f"{level} {header_text}")
    
    # Look for paragraphs
    paragraphs = soup.find_all("p")
    for p in paragraphs:
        p_text = p.get_text(strip=True)
        if p_text and len(p_text) > 10:  # Ignore very short paragraphs
            content_pieces.append(p_text)
    
    # Look for tables
    tables = soup.find_all("table")
    for table in tables:
        _clean_table_for_conversion(table)
        table_md = markdownify(str(table), **md_opts).strip()
        if table_md:
            content_pieces.append(table_md)
    
    # Look for code blocks
    code_blocks = soup.find_all("pre")
    for code_block in code_blocks:
        code_content = code_block.get_text(strip=True)
        if code_content:
            content_pieces.append(f"```\n{code_content}\n```")
    
    if content_pieces:
        result = "\n\n".join(filter(None, content_pieces))
        logging.info(f"Fallback extraction captured {len(content_pieces)} content pieces")
        return result
    
    logging.warning("Fallback extraction found no meaningful content")
    return None


def _clean_table_for_conversion(table):
    """Clean up table elements for better markdown conversion"""
    # Remove empty cells and clean up whitespace
    for cell in table.find_all(["td", "th"]):
        # Remove nested divs that might interfere with table structure
        for div in cell.find_all("div"):
            if not div.get_text(strip=True):
                div.decompose()
        
        # Clean up cell content
        cell_text = cell.get_text(strip=True)
        if cell_text:
            cell.clear()
            cell.string = cell_text
        elif not cell.find_all():  # Empty cell
            cell.string = " "