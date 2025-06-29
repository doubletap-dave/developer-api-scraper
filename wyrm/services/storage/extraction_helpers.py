"""Content extraction helper functions for API documentation processing.

This module provides utility functions for extracting specific types of content
from API documentation pages, including endpoints, models, and responses.
"""

import asyncio
import logging
from typing import List, Optional

from bs4 import BeautifulSoup
from markdownify import markdownify
from selenium.webdriver.remote.webdriver import WebDriver

from ..selectors_service import SelectorsService


class EndpointHeaderExtractor:
    """Extracts header information from API endpoint documentation."""

    @staticmethod
    def extract_method_title_header(endpoint_element) -> Optional[str]:
        """Extract HTTP method, title, and Try It button from header section.
        
        Args:
            endpoint_element: BeautifulSoup element containing the endpoint
            
        Returns:
            Formatted header string or None if no header found
        """
        method_title_section = endpoint_element.find("div", class_="dds__mb-4")
        if not method_title_section:
            return None

        header_parts = []
        
        # Extract HTTP method
        method_element = method_title_section.find("app-show-http-method")
        if method_element:
            method_span = method_element.find(
                "span", class_=lambda x: x and "http-method" in x)
            if method_span:
                method = method_span.get_text(strip=True)
                header_parts.append(method)

        # Extract title
        title_element = method_title_section.find("span", class_="dds__pl-3")
        if title_element:
            title = title_element.get_text(strip=True)
            header_parts.append(title)

        # Check for Try It button
        try_button = method_title_section.find("button", string="Try It")
        if try_button:
            header_parts.append("Try It")

        return f"### {' '.join(header_parts)}" if header_parts else None

    @staticmethod
    def extract_api_path(endpoint_element) -> Optional[str]:
        """Extract API path from the endpoint documentation.
        
        Args:
            endpoint_element: BeautifulSoup element containing the endpoint
            
        Returns:
            Formatted path code block or None if no path found
        """
        path_markdown = endpoint_element.find("markdown")
        if not path_markdown:
            return None
            
        path_content = path_markdown.find("pre")
        if not path_content:
            return None
            
        path_text = path_content.get_text(strip=True)
        return f"```\n{path_text}\n```" if path_text else None

    @staticmethod
    def extract_description(endpoint_element, path_markdown_element) -> Optional[str]:
        """Extract description from the endpoint documentation.
        
        Args:
            endpoint_element: BeautifulSoup element containing the endpoint
            path_markdown_element: The markdown element containing the path (to avoid duplication)
            
        Returns:
            Description text or None if no description found
        """
        desc_container = endpoint_element.find("div", class_="dds__mt-2")
        if not desc_container:
            return None
            
        desc_markdown = desc_container.find("markdown")
        if not desc_markdown or desc_markdown == path_markdown_element:
            return None
            
        desc_text = desc_markdown.get_text(strip=True)
        return desc_text if desc_text else None


class ComponentExtractor:
    """Extracts various components from API endpoint documentation."""

    def __init__(self, md_opts: dict):
        """Initialize with markdown options.
        
        Args:
            md_opts: Markdown conversion options
        """
        self.md_opts = md_opts

    def extract_security_info(self, endpoint_element) -> Optional[str]:
        """Extract security information from endpoint.
        
        Args:
            endpoint_element: BeautifulSoup element containing the endpoint
            
        Returns:
            Formatted security markdown or None if no security info found
        """
        security_element = endpoint_element.find("app-api-doc-security")
        if not security_element or not security_element.get_text(strip=True):
            return None
            
        security_md = markdownify(str(security_element), **self.md_opts).strip()
        if not security_md:
            return None
            
        return f"## Security\n\n{security_md}"

    def extract_server_info(self, endpoint_element) -> Optional[str]:
        """Extract server information from endpoint.
        
        Args:
            endpoint_element: BeautifulSoup element containing the endpoint
            
        Returns:
            Server markdown or None if no server info found
        """
        server_element = endpoint_element.find("app-api-doc-server")
        if not server_element:
            return None
            
        server_md = markdownify(str(server_element), **self.md_opts).strip()
        return server_md if server_md else None

    def extract_parameters(self, endpoint_element) -> List[str]:
        """Extract all parameter sections from endpoint.
        
        Args:
            endpoint_element: BeautifulSoup element containing the endpoint
            
        Returns:
            List of parameter markdown strings
        """
        param_elements = endpoint_element.find_all("app-show-parameters")
        param_sections = []
        
        for param_element in param_elements:
            param_md = markdownify(str(param_element), **self.md_opts).strip()
            if param_md:
                param_sections.append(param_md)
                
        return param_sections

    def extract_request_body(self, endpoint_element) -> Optional[str]:
        """Extract request body information from endpoint.
        
        Args:
            endpoint_element: BeautifulSoup element containing the endpoint
            
        Returns:
            Request body markdown or None if no request body found
        """
        request_body_element = endpoint_element.find("app-api-doc-request-body")
        if not request_body_element:
            return None
            
        request_body_md = markdownify(str(request_body_element), **self.md_opts).strip()
        return request_body_md if request_body_md else None


class ResponseExtractor:
    """Handles extraction of response information from API documentation."""

    def __init__(self, selectors: SelectorsService, md_opts: dict):
        """Initialize with selectors and markdown options.
        
        Args:
            selectors: SelectorsService instance
            md_opts: Markdown conversion options
        """
        self.selectors = selectors
        self.md_opts = md_opts

    async def extract_response_content(self, response_element, driver: WebDriver) -> str:
        """Extract response content with all status codes.
        
        Args:
            response_element: BeautifulSoup element containing response info
            driver: WebDriver instance for interacting with tabs
            
        Returns:
            Complete response markdown
        """
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
                    await asyncio.sleep(0.5)  # Wait for content to load

                    # Extract content for this tab
                    tab_content = await self._extract_single_response_tab_content(
                        driver, status_code
                    )
                    if tab_content:
                        markdown_pieces.append(tab_content)

                except Exception as e:
                    logging.warning(
                        f"Failed to extract content for response tab {status_code}: {e}")
                    continue
        else:
            # Single response: extract directly
            single_response = await self._extract_single_response_content(response_element)
            if single_response:
                markdown_pieces.append(single_response)

        return "\n\n".join(markdown_pieces) if markdown_pieces else ""

    async def _extract_single_response_content(self, response_element) -> str:
        """Extract content from a single response element."""
        response_md = markdownify(str(response_element), **self.md_opts).strip()
        return response_md if response_md else ""

    async def _extract_single_response_tab_content(self, driver: WebDriver, status_code: str) -> str:
        """Extract content from a single response tab after it's been activated."""
        try:
            # Find the active tab panel
            active_panel = driver.find_element(*self.selectors.ACTIVE_TAB_PANEL)
            if not active_panel:
                return ""

            panel_html = active_panel.get_attribute("innerHTML")
            if not panel_html:
                return ""

            # Parse and convert to markdown
            soup = BeautifulSoup(panel_html, 'html.parser')

            # Clean up tables before conversion
            for table in soup.find_all('table'):
                self._clean_table_for_conversion(table)

            panel_md = markdownify(str(soup), **self.md_opts).strip()
            if panel_md:
                return f"### Response {status_code}\n\n{panel_md}"

            return ""
        except Exception as e:
            logging.warning(f"Failed to extract tab content for {status_code}: {e}")
            return ""

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
