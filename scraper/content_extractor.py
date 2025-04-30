import logging

from markdownify import markdownify
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webdriver import WebDriver

from . import selectors


async def extract_and_convert_content(driver: WebDriver) -> str | None:
    """
    Finds the content markdown element, extracts its inner HTML,
    converts it to Markdown using markdownify, and returns the result.
    Returns None if the element is not found or has no content.
    """
    logging.debug("Attempting to extract and convert content...")
    try:
        # We assume wait_for_content_update was called before this
        content_element = driver.find_element(*selectors.CONTENT_PANE_MARKDOWN)
        selector_str = selectors.CONTENT_PANE_MARKDOWN[1]
        logging.debug(f"Found content element: {selector_str}")

        html_content = content_element.get_attribute("innerHTML")
        if not html_content or not html_content.strip():
            logging.warning(
                "Content markdown element found, but it has no inner HTML content."
            )
            return None

        html_len = len(html_content)
        logging.debug(f"Extracted {html_len} bytes of HTML. Converting to Markdown...")

        # Convert HTML to Markdown
        markdown_content = markdownify(html_content, heading_style="ATX")

        if not markdown_content or not markdown_content.strip():
            log_msg = (
                "HTML content extracted, but conversion to Markdown "
                "resulted in empty content."
            )
            logging.warning(log_msg)
            return None

        logging.info("Successfully extracted and converted content to Markdown.")
        return markdown_content.strip()  # Return stripped content

    except NoSuchElementException:
        selector_str = selectors.CONTENT_PANE_MARKDOWN[1]
        logging.error(
            f"Content markdown element ({selector_str}) not found "
            "when trying to extract content."
        )
        return None
    except Exception as e:
        logging.exception(
            "An unexpected error occurred during content extraction/conversion: " f"{e}"
        )
        return None
