"""Resume and status management module for Wyrm application.

This module handles checking existing files, managing resume information,
and debug operations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

from selenium.webdriver.remote.webdriver import WebDriver


class ResumeManager:
    """Handles resume information and status management operations."""

    def __init__(self) -> None:
        """Initialize the resume manager."""
        pass

    async def save_debug_page_content(
        self,
        item_id: str,
        driver: WebDriver,
        config_values: Dict
    ) -> None:
        """Save debug page content for troubleshooting.

        Args:
            item_id: Unique identifier for the item
            driver: WebDriver instance
            config_values: Configuration values containing debug directory
        """
        try:
            # Get the page source
            page_source = driver.page_source

            # Save to debug directory
            debug_file = (
                config_values["debug_output_dir"] / f"page_content_{item_id}.html"
            )
            debug_file.parent.mkdir(parents=True, exist_ok=True)

            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(page_source)

            logging.debug(f"Debug page content saved to: {debug_file}")
        except Exception as e:
            logging.error(f"Failed to save debug page content: {e}")

    def check_existing_files(
        self,
        items,
        base_output_dir: Path
    ):
        """Check which items already have saved files.

        Args:
            items: List of items to check
            base_output_dir: Base output directory

        Returns:
            Tuple of (existing_items, items_needing_processing)
        """
        existing_items = []
        items_needing_processing = []

        for item in items:
            # Handle both SidebarItem models and dict items for backward compatibility
            if hasattr(item, 'text'):
                header = item.header
                menu = item.menu
                item_text = item.text
                item_id = item.id
            else:
                header = item.get("header")
                menu = item.get("menu")
                item_text = item.get("text", "")
                item_id = item.get("id")

            # Generate the expected file path
            from .file_operations import FileOperations
            file_ops = FileOperations()
            expected_path = file_ops._get_output_file_path(
                header=header,
                menu=menu,
                item_text=item_text,
                base_output_dir=base_output_dir
            )

            if expected_path.exists():
                existing_items.append(item)
                logging.debug(f"File exists for item {item_id}: {expected_path}")
            else:
                items_needing_processing.append(item)
                logging.debug(f"File missing for item {item_id}: {expected_path}")

        return existing_items, items_needing_processing

    def save_structure_to_output(
        self,
        sidebar_structure: Dict,
        structure_filepath: Path
    ) -> None:
        """Save sidebar structure to output directory.

        Args:
            sidebar_structure: Sidebar structure data
            structure_filepath: Path to save the structure
        """
        try:
            structure_filepath.parent.mkdir(parents=True, exist_ok=True)
            # Handle SidebarStructure models by converting to dict
            if hasattr(sidebar_structure, 'dict'):
                structure_data = sidebar_structure.dict()
            else:
                structure_data = sidebar_structure

            with open(structure_filepath, 'w', encoding='utf-8') as f:
                json.dump(structure_data, f, indent=4, ensure_ascii=False)
            logging.info(f"Sidebar structure saved to: {structure_filepath}")
        except Exception as e:
            logging.error(f"Failed to save sidebar structure: {e}")

    def display_resume_info(
        self,
        valid_items: List[Dict],
        existing_items: List[Dict],
        items_needing_processing: List[Dict],
        base_output_dir: Path,
    ) -> None:
        """Display resume information showing current status.

        Args:
            valid_items: All valid items found
            existing_items: Items that already have files
            items_needing_processing: Items that need processing
            base_output_dir: Base output directory
        """
        total_items = len(valid_items)
        existing_count = len(existing_items)
        remaining_count = len(items_needing_processing)

        print("\n📊 Resume Information")
        print(f"{'='*50}")
        print(f"📁 Output Directory: {base_output_dir}")
        print(f"📄 Total Items Found: {total_items}")
        print(f"✅ Files Already Exist: {existing_count}")
        print(f"⏳ Files Needing Processing: {remaining_count}")

        if remaining_count > 0:
            print("\n🔄 Next items to process:")
            for i, item in enumerate(items_needing_processing[:5]):  # Show first 5
                # Handle both SidebarItem models and dict items
                if hasattr(item, 'text'):
                    item_text = item.text
                    item_id = item.id
                else:
                    item_text = item.get("text", "Unknown")
                    item_id = item.get("id", "Unknown")
                print(f"  {i+1}. {item_text} (ID: {item_id})")

            if remaining_count > 5:
                print(f"  ... and {remaining_count - 5} more items")
        else:
            print("\n🎉 All items have been processed!")

        print(f"{'='*50}")

        # Log the same information
        logging.info(f"Resume info - Total: {total_items}, Existing: {existing_count}, Remaining: {remaining_count}")
