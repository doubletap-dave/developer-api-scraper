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
from .extraction_helpers import EndpointHeaderExtractor, ComponentExtractor, ResponseExtractor


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
        component_extractor = ComponentExtractor(md_opts)
        response_extractor = ResponseExtractor(self.selectors, md_opts)

        # 1. Extract method, title, and path from the header section
        header = EndpointHeaderExtractor.extract_method_title_header(endpoint_element)
        if header:
            markdown_pieces.append(header)

        # 2. Extract API path
        path_markdown = endpoint_element.find("markdown")
        api_path = EndpointHeaderExtractor.extract_api_path(endpoint_element)
        if api_path:
            markdown_pieces.append(api_path)

        # 3. Extract description
        description = EndpointHeaderExtractor.extract_description(endpoint_element, path_markdown)
        if description:
            markdown_pieces.append(description)

        # 4. Extract security information
        security_info = component_extractor.extract_security_info(endpoint_element)
        if security_info:
            markdown_pieces.append(security_info)

        # 5. Extract server information
        server_info = component_extractor.extract_server_info(endpoint_element)
        if server_info:
            markdown_pieces.append(server_info)

        # 6. Extract all parameter sections
        parameter_sections = component_extractor.extract_parameters(endpoint_element)
        markdown_pieces.extend(parameter_sections)

        # 7. Extract response information with all status codes
        response_element = endpoint_element.find("app-api-doc-response")
        if response_element:
            response_md = await response_extractor.extract_response_content(response_element, driver)
            if response_md:
                markdown_pieces.append(response_md)

        # 8. Extract request body information
        request_body = component_extractor.extract_request_body(endpoint_element)
        if request_body:
            markdown_pieces.append(request_body)

        return "\n\n".join(markdown_pieces)


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
