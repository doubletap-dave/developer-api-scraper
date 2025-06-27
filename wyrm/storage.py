import asyncio
import logging
from pathlib import Path

from .utils import get_output_file_path


# Helper synchronous function for file writing
def _write_file_sync(output_file: Path, markdown_content: str):
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
    except Exception:
        # Log explicitly here or let the caller handle it.
        # Letting the caller handle it provides more context (item name etc.)
        raise


async def save_markdown(
    header: str | None,
    menu: str | None,
    item_text: str,
    markdown_content: str,
    base_output_dir: str | Path,
    overwrite: bool = False,
) -> bool:
    """
    Saves the markdown content to a structured file path.

    Args:
        header: The header name.
        menu: The menu name.
        item_text: The item text.
        markdown_content: The content to save.
        base_output_dir: The base directory for output.
        overwrite: Whether to overwrite existing files.

    Returns:
        True if the file was saved successfully, False otherwise (e.g., skipped).
    """
    try:
        output_file = get_output_file_path(header, menu, item_text, base_output_dir)

        if output_file.exists() and not overwrite:
            log_skip = f"Skipping existing file: {output_file}"
            logging.info(log_skip)
            return False  # Indicate skipped

        # Ensure the parent directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write the file asynchronously by running the sync helper in a thread
        await asyncio.to_thread(_write_file_sync, output_file, markdown_content)

        log_success = f"Successfully saved content to: {output_file}"
        logging.info(log_success)
        return True  # Indicate success

    except Exception as exc:
        # Log the exception before returning False
        output_file_str = "<unknown path>"
        if "output_file" in locals():
            output_file_str = str(output_file)
        log_err = (
            f"Error saving markdown for '{item_text}' to " f"{output_file_str}: {exc}"
        )
        logging.exception(log_err)
        return False  # Indicate failure
