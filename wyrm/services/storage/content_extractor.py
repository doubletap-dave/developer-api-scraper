"""Content extraction service for Wyrm application.

This module handles the extraction of content from web pages, converting
HTML content to markdown format and managing the extraction workflow.
"""

import asyncio
import logging
from typing import Optional

from bs4 import BeautifulSoup
from markdownify import markdownify
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webdriver import WebDriver

from ..selectors_service import SelectorsService


class ContentExtractor:
    """Service for extracting and processing content from web pages.

    Handles the conversion of HTML content to markdown format and manages
    the complete content extraction workflow including navigation, waiting
    for content to load, and processing the extracted data.
    """

    def __init__(self) -> None:
        """Initialize the content extractor."""
        self.selectors = SelectorsService()

    async def extract_and_convert_content(self, driver: WebDriver) -> Optional[str]:
        """Extract and convert content from the current page.

        Enhanced content extractor that captures all rich information from Dell Developer API docs.

        Extracts:
        - API endpoint details (method, path, description)
        - Code examples (curl commands, responses)
        - Parameter tables (path, query, header, cookie)
        - Response schemas with all HTTP status codes
        - Request body schemas
        - Security information
        - Server information

        Args:
            driver: WebDriver instance

        Returns:
            Complete Markdown content or None if extraction fails
        """
        logging.debug(
            "Attempting to extract and convert content with enhanced extractor...")
        try:
            # Find the main content pane first
            content_pane = driver.find_element(
                *self.selectors.CONTENT_PANE_INNER_HTML_TARGET)
            logging.debug(
                f"Found content pane element: {self.selectors.CONTENT_PANE_INNER_HTML_TARGET}")

            # Get the full HTML content of the documentation div
            html_content = content_pane.get_attribute("innerHTML")
            if not html_content:
                logging.warning("Content pane was found but is empty.")
                return None

            # Parse with BeautifulSoup for better HTML manipulation
            soup = BeautifulSoup(html_content, 'html.parser')
            md_opts = {"heading_style": "ATX", "strip": ["script", "style"]}

            # Strategy 1: Handle API endpoint documentation (app-api-doc-endpoint)
            endpoint_element = soup.find("app-api-doc-endpoint")
            if endpoint_element:
                logging.debug(
                    "Found app-api-doc-endpoint structure - extracting API documentation")
                return await self._extract_api_endpoint_content(endpoint_element, md_opts, driver)

            # Strategy 2: Handle standalone model/schema documentation (app-api-doc-model)
            model_element = soup.find("app-api-doc-model")
            if model_element:
                logging.debug("Found standalone app-api-doc-model structure")
                return await self._extract_model_content(model_element, md_opts)

            # Strategy 3: Handle general markdown content
            markdown_elements = soup.find_all("markdown")
            if markdown_elements:
                logging.debug(
                    f"Found {len(markdown_elements)} markdown elements - extracting general content")
                return await self._extract_markdown_content(markdown_elements, md_opts)

            # Strategy 4: Fallback - extract all text content
            logging.warning(
                "No recognized content structure found, attempting fallback extraction")
            return await self._extract_fallback_content(soup, md_opts)

        except NoSuchElementException:
            logging.error(
                f"Content pane element ({self.selectors.CONTENT_PANE_INNER_HTML_TARGET}) not found.")
            return None
        except Exception as e:
            logging.exception(
                f"An unexpected error occurred during content extraction/conversion: {e}")
            return None

    async def _extract_api_endpoint_content(self, endpoint_element, md_opts, driver: WebDriver) -> str:
        """Extract content from app-api-doc-endpoint structure."""
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
                method_span = method_element.find(
                    "span", class_=lambda x: x and "http-method" in x)
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
            response_md = await self._extract_response_content(response_element, md_opts, driver)
            if response_md:
                markdown_pieces.append(response_md)

        # 8. Extract request body information
        request_body_element = endpoint_element.find("app-api-doc-request-body")
        if request_body_element:
            request_body_md = markdownify(str(request_body_element), **md_opts).strip()
            if request_body_md:
                markdown_pieces.append(request_body_md)

        return "\n\n".join(markdown_pieces)

    async def _extract_response_content(self, response_element, md_opts, driver: WebDriver) -> str:
        """Extract response content with all status codes."""
        markdown_pieces = []

        # Check if this is a multi-tab response structure
        tab_buttons = response_element.find_all("button", {"role": "tab"})

        if tab_buttons and len(tab_buttons) > 1:
            # Multi-tab response: extract each tab's content
            logging.debug(f"Found {len(tab_buttons)} response tabs")

            for tab_button in tab_buttons:
                status_code = tab_button.get_text(strip=True)
                logging.debug(f"Processing response tab: {status_code}")

                try:
                    # Click the tab to activate it
                    driver.execute_script("arguments[0].click();", tab_button)

                    # Wait a moment for content to load
                    await asyncio.sleep(0.5)

                    # Extract content for this tab
                    tab_content = await self._extract_single_response_tab_content(driver, status_code, md_opts)
                    if tab_content:
                        markdown_pieces.append(tab_content)

                except Exception as e:
                    logging.warning(
                        f"Failed to extract content for response tab {status_code}: {e}")
                    continue
        else:
            # Single response: extract directly
            single_response = await self._extract_single_response_content(response_element, md_opts)
            if single_response:
                markdown_pieces.append(single_response)

        return "\n\n".join(markdown_pieces) if markdown_pieces else ""

    async def _extract_single_response_content(self, response_element, md_opts) -> str:
        """Extract content from a single response element."""
        response_md = markdownify(str(response_element), **md_opts).strip()
        return response_md if response_md else ""

    async def _extract_single_response_tab_content(self, driver: WebDriver, status_code: str, md_opts) -> str:
        """Extract content from a single response tab after it's been activated."""
        try:
            # Find the active tab panel
            active_panel = driver.find_element(*self.selectors.ACTIVE_TAB_PANEL)
            if active_panel:
                panel_html = active_panel.get_attribute("innerHTML")
                if panel_html:
                    # Parse and convert to markdown
                    soup = BeautifulSoup(panel_html, 'html.parser')

                    # Clean up tables before conversion
                    for table in soup.find_all('table'):
                        self._clean_table_for_conversion(table)

                    panel_md = markdownify(str(soup), **md_opts).strip()
                    if panel_md:
                        return f"### Response {status_code}\n\n{panel_md}"

            return ""
        except Exception as e:
            logging.warning(f"Failed to extract tab content for {status_code}: {e}")
            return ""

    async def _extract_model_content(self, model_element, md_opts) -> str:
        """Extract content from app-api-doc-model structure."""
        model_md = markdownify(str(model_element), **md_opts).strip()
        return model_md if model_md else ""

    async def _extract_markdown_content(self, markdown_elements, md_opts) -> str:
        """Extract content from markdown elements."""
        markdown_pieces = []

        for markdown_element in markdown_elements:
            # Get the inner HTML of the markdown element
            inner_html = markdown_element.decode_contents() if hasattr(
                markdown_element, 'decode_contents') else str(markdown_element)

            if inner_html.strip():
                # Parse the inner content with BeautifulSoup
                soup = BeautifulSoup(inner_html, 'html.parser')

                # Clean up tables before conversion
                for table in soup.find_all('table'):
                    self._clean_table_for_conversion(table)

                # Convert to markdown
                md_content = markdownify(str(soup), **md_opts).strip()
                if md_content:
                    markdown_pieces.append(md_content)

        return "\n\n".join(markdown_pieces) if markdown_pieces else ""

    async def _extract_fallback_content(self, soup, md_opts) -> str:
        """Fallback content extraction when no specific structure is found."""
        # Try to find any meaningful content containers
        content_containers = soup.find_all(['div', 'section', 'article'],
                                           class_=lambda x: x and any(keyword in x.lower()
                                                                      for keyword in ['content', 'doc', 'api', 'main']))

        if not content_containers:
            # If no specific containers found, try to get all text content
            content_containers = [soup]

        markdown_pieces = []
        for container in content_containers:
            # Clean up tables before conversion
            for table in container.find_all('table'):
                self._clean_table_for_conversion(table)

            # Convert to markdown
            container_md = markdownify(str(container), **md_opts).strip()
            if container_md and len(container_md) > 50:  # Only include substantial content
                markdown_pieces.append(container_md)

        return "\n\n".join(markdown_pieces) if markdown_pieces else ""

    def _clean_table_for_conversion(self, table):
        """Clean up table structure for better markdown conversion."""
        # Remove empty cells and rows
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if not cells or all(not cell.get_text(strip=True) for cell in cells):
                row.decompose()
                continue

            # Clean up individual cells
            for cell in cells:
                # Remove excessive whitespace
                if cell.string:
                    cell.string = cell.get_text(strip=True)
