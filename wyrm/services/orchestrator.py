"""Orchestrator service for Wyrm application.

This service coordinates the entire scraping workflow, managing configuration,
navigation, content extraction, and storage operations.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from selenium.webdriver.remote.webdriver import WebDriver

from wyrm import (
    content_extractor,
    driver_setup,
    navigation,
    selectors,
    sidebar_parser,
    storage,
    utils,
)


class Orchestrator:
    """Main orchestrator service for the Wyrm scraping application.

    This service coordinates the entire workflow from configuration loading
    to final content extraction and storage.
    """

    def __init__(self) -> None:
        """Initialize the Orchestrator service."""
        self.driver: Optional[WebDriver] = None
        self.config: Dict = {}
        self.processed_count: int = 0
        self.skipped_count: int = 0
        self.error_count: int = 0
        self.no_content_count: int = 0
        self.total_items_in_structure: int = 0

    async def run_scraping_workflow(
        self,
        config_path: str,
        headless: Optional[bool] = None,
        log_level: Optional[str] = None,
        save_structure: bool = False,
        save_html: bool = False,
        debug: bool = False,
        max_expand_attempts: Optional[int] = None,
        force: bool = False,
        test_item_id: Optional[str] = None,
        max_items: Optional[int] = None,
        resume_info: bool = False,
        structure_filename: Optional[str] = None,
        html_filename: Optional[str] = None,
    ) -> None:
        """Run the complete scraping workflow.

        Args:
            config_path: Path to configuration file
            headless: Override headless mode setting
            log_level: Override log level setting
            save_structure: Save parsed structure to debug directory
            save_html: Save raw HTML to debug directory
            debug: Enable debug mode with additional logging and saves
            max_expand_attempts: Maximum menu expansion attempts
            force: Overwrite existing output files
            test_item_id: Process only specific item ID (deprecated)
            max_items: Maximum number of items to process
            resume_info: Show resume information and exit
            structure_filename: Custom structure filename
            html_filename: Custom HTML filename
        """
        try:
            # Load configuration and setup
            await self._load_config_and_setup(
                config_path, headless, log_level, debug, max_expand_attempts
            )

            # Handle debug mode settings
            save_structure, save_html = self._handle_debug_mode(
                debug, save_structure, save_html
            )

            # Get configuration values
            config_values = self._extract_config_values()

            # Handle sidebar structure loading/parsing
            sidebar_structure = await self._handle_sidebar_structure(
                config_values,
                save_structure,
                save_html,
                structure_filename,
                html_filename,
                resume_info,
                force,
            )

            # Process items from structure
            await self._process_items_from_structure(
                sidebar_structure,
                config_values,
                force,
                test_item_id,
                max_items,
                resume_info,
            )

        except KeyboardInterrupt:
            logging.warning("--- User interrupted execution ---")
        except Exception as e:
            logging.exception(f"--- An unexpected error occurred: {e} ---")
        finally:
            await self._cleanup()

    async def _load_config_and_setup(
        self,
        config_path: str,
        headless: Optional[bool],
        log_level: Optional[str],
        debug: bool,
        max_expand_attempts: Optional[int],
    ) -> None:
        """Load configuration and setup logging."""
        try:
            self.config = utils.load_config(config_path)
        except FileNotFoundError:
            print(
                f"Error: Configuration file '{config_path}' not found.", file=sys.stderr
            )
            sys.exit(1)
        except Exception as e:
            print(f"Error loading configuration: {e}", file=sys.stderr)
            sys.exit(1)

        # Determine effective settings
        effective_log_level = log_level or self.config.get("log_level", "INFO")
        effective_headless = (
            headless
            if headless is not None
            else self.config.get("webdriver", {}).get("headless", True)
        )

        # Handle debug mode
        if debug:
            logging.info("Debug mode enabled via command line.")
            effective_log_level = "DEBUG"

        # Setup logging
        utils.setup_logging(
            log_level=effective_log_level,
            log_file=self.config.get("log_file", "logs/wyrm.log"),
        )

        logging.info("--- Starting Wyrm ---")
        logging.debug(f"Config loaded: {self.config}")
        logging.debug(f"Effective log level: {effective_log_level}")
        logging.debug(f"Effective headless mode: {effective_headless}")

    def _handle_debug_mode(
        self, debug: bool, save_structure: bool, save_html: bool
    ) -> Tuple[bool, bool]:
        """Handle debug mode settings and return effective save flags."""
        if debug:
            save_structure = True
            save_html = True
            logging.info("Debug mode forcing structure and HTML saves.")
        return save_structure, save_html

    def _extract_config_values(self) -> Dict:
        """Extract and calculate configuration values."""
        delays_cfg = self.config.get("delays", {})
        debug_cfg = self.config.get("debug_settings", {})
        output_cfg = self.config.get("output", {})

        # Extract delay values
        navigation_timeout = delays_cfg.get("navigation", 10)
        sidebar_wait_timeout = delays_cfg.get("sidebar_wait", 15)
        expand_delay = delays_cfg.get("expand_menu", 0.5)
        post_expand_settle_delay = delays_cfg.get("post_expand_settle", 1.0)
        post_click_delay = delays_cfg.get("post_click", 0.5)
        content_wait_timeout = delays_cfg.get("content_wait", 20)

        # Extract directory paths
        debug_output_dir = Path(debug_cfg.get("output_directory", "output/debug"))
        base_output_dir = Path(output_cfg.get("directory", "output"))

        # Extract filenames
        default_structure_filename = debug_cfg.get(
            "save_structure_filename", "structure.json"
        )
        default_html_filename = debug_cfg.get(
            "save_html_filename", "sidebar_debug.html"
        )
        non_headless_pause = debug_cfg.get("non_headless_pause_seconds", 10)

        return {
            "navigation_timeout": navigation_timeout,
            "sidebar_wait_timeout": sidebar_wait_timeout,
            "expand_delay": expand_delay,
            "post_expand_settle_delay": post_expand_settle_delay,
            "post_click_delay": post_click_delay,
            "content_wait_timeout": content_wait_timeout,
            "debug_output_dir": debug_output_dir,
            "base_output_dir": base_output_dir,
            "default_structure_filename": default_structure_filename,
            "default_html_filename": default_html_filename,
            "non_headless_pause": non_headless_pause,
        }

    async def _handle_sidebar_structure(
        self,
        config_values: Dict,
        save_structure: bool,
        save_html: bool,
        structure_filename: Optional[str],
        html_filename: Optional[str],
        resume_info: bool,
        force: bool,
    ) -> Dict:
        """Handle sidebar structure loading or parsing."""
        logging.info("Proceeding to Phase 3: Sidebar Structure Loading/Parsing")

        # Get structure filename
        structure_filename_final = structure_filename or getattr(
            storage,
            "get_structure_map_filename",
            lambda url: f"structure_{urlparse(url).netloc.replace('.', '_')}.json",
        )(self.config["target_url"])
        structure_filepath = config_values["base_output_dir"] / structure_filename_final

        # Try to load existing structure
        logging.info(f"Checking for existing structure map: {structure_filepath}")
        sidebar_structure = sidebar_parser.load_structure_map(str(structure_filepath))

        if sidebar_structure:
            logging.info("Loaded existing sidebar structure map.")
            await self._handle_resume_check(
                sidebar_structure, config_values, resume_info, force
            )
            # Initialize driver for navigation
            await self._initialize_driver_for_navigation(config_values)
        else:
            # Perform live parsing
            sidebar_structure = await self._perform_live_parsing(
                config_values,
                save_structure,
                save_html,
                structure_filename,
                html_filename,
                structure_filepath,
            )

        return sidebar_structure

    async def _handle_resume_check(
        self,
        sidebar_structure: Dict,
        config_values: Dict,
        resume_info: bool,
        force: bool,
    ) -> None:
        """Handle resume check for existing structure."""
        flattened_structure = sidebar_parser.flatten_sidebar_structure(
            sidebar_structure
        )
        valid_items = [item for item in flattened_structure if item.get("id")]

        # Check existing vs needed items
        existing_items = []
        items_needing_processing = []

        for item in valid_items:
            expected_file = storage.get_output_file_path(
                item.get("header"),
                item.get("menu"),
                item.get("text", "Unknown Item"),
                config_values["base_output_dir"],
            )
            if expected_file.exists():
                existing_items.append(item)
            else:
                items_needing_processing.append(item)

        # Handle resume info request
        if resume_info:
            self._display_resume_info(
                valid_items,
                existing_items,
                items_needing_processing,
                config_values["base_output_dir"],
            )
            sys.exit(0)

        # Check if all items are processed
        if not force and not items_needing_processing:
            logging.info("All items already processed! Use --force to re-process.")
            print(f"✅ All {len(existing_items)} items already processed!")
            print(f"📁 Output directory: {config_values['base_output_dir']}")
            print("💡 Use --force to re-process existing files")
            print("💡 Use --resume-info to see detailed status")
            sys.exit(0)

    def _display_resume_info(
        self,
        valid_items: List[Dict],
        existing_items: List[Dict],
        items_needing_processing: List[Dict],
        base_output_dir: Path,
    ) -> None:
        """Display resume information."""
        print(f"\n📊 Resume Information:")
        print(f"  Total items in structure: {len(valid_items)}")
        print(f"  ✅ Already processed: {len(existing_items)}")
        print(f"  🔄 Need processing: {len(items_needing_processing)}")
        print(f"  📁 Output directory: {base_output_dir}")

        if existing_items:
            print(f"\n✅ Existing files ({len(existing_items)}):")
            for item in existing_items[:10]:
                file_path = storage.get_output_file_path(
                    item.get("header"),
                    item.get("menu"),
                    item.get("text", "Unknown Item"),
                    base_output_dir,
                )
                print(f"    {item.get('text', 'Unknown')} -> {file_path}")
            if len(existing_items) > 10:
                print(f"    ... and {len(existing_items) - 10} more")

        if items_needing_processing:
            print(f"\n🔄 Need processing ({len(items_needing_processing)}):")
            for item in items_needing_processing[:10]:
                print(f"    {item.get('text', 'Unknown')} (ID: {item.get('id')})")
            if len(items_needing_processing) > 10:
                print(f"    ... and {len(items_needing_processing) - 10} more")

        print(f"\n💡 To resume processing: python main.py")
        print(f"💡 To force re-process all: python main.py --force")

    async def _initialize_driver_for_navigation(self, config_values: Dict) -> None:
        """Initialize WebDriver for navigation with existing structure."""
        logging.info("Initializing WebDriver for navigation with existing structure...")
        headless = self.config.get("webdriver", {}).get("headless", True)
        self.driver = driver_setup.initialize_driver(
            browser=self.config.get("webdriver", {}).get("browser", "chrome"),
            headless=headless,
        )

        logging.info("Navigating to target URL and waiting for sidebar...")
        await navigation.navigate_to_url(
            self.driver,
            self.config["target_url"],
            timeout=config_values["navigation_timeout"],
        )
        await navigation.wait_for_sidebar(
            self.driver, timeout=config_values["sidebar_wait_timeout"]
        )

    async def _perform_live_parsing(
        self,
        config_values: Dict,
        save_structure: bool,
        save_html: bool,
        structure_filename: Optional[str],
        html_filename: Optional[str],
        structure_filepath: Path,
    ) -> Dict:
        """Perform live parsing of sidebar structure."""
        logging.info("Structure map not found. Performing live parsing...")

        # Initialize driver
        headless = self.config.get("webdriver", {}).get("headless", True)
        self.driver = driver_setup.initialize_driver(
            browser=self.config.get("webdriver", {}).get("browser", "chrome"),
            headless=headless,
        )

        # Navigate and expand menus
        await navigation.navigate_to_url(
            self.driver,
            self.config["target_url"],
            timeout=config_values["navigation_timeout"],
        )
        await navigation.expand_all_menus(
            self.driver,
            expand_delay=config_values["expand_delay"],
            max_attempts=None,  # Will be handled by caller
        )
        await asyncio.sleep(config_values["post_expand_settle_delay"])

        # Get sidebar HTML
        sidebar_html = sidebar_parser.get_sidebar_html(self.driver)

        # Save HTML if requested
        if save_html and sidebar_html:
            await self._save_debug_html(sidebar_html, config_values, html_filename)

        if not sidebar_html:
            logging.critical("Failed to get sidebar HTML. Cannot parse structure.")
            sys.exit(1)

        # Parse structure
        sidebar_structure = sidebar_parser.map_sidebar_structure(sidebar_html)

        # Save structure
        if sidebar_structure:
            logging.info(f"Saving newly parsed structure map to {structure_filepath}")
            sidebar_parser.save_structure_map(
                sidebar_structure, str(structure_filepath)
            )

            if save_structure:
                await self._save_debug_structure(
                    sidebar_structure, config_values, structure_filename
                )
        else:
            logging.critical("Failed to parse sidebar structure from HTML.")
            sys.exit(1)

        return sidebar_structure

    async def _save_debug_html(
        self,
        sidebar_html: str,
        config_values: Dict,
        html_filename: Optional[str],
    ) -> None:
        """Save debug HTML file."""
        html_save_filename = html_filename or config_values["default_html_filename"]
        html_save_path = config_values["debug_output_dir"] / html_save_filename

        try:
            config_values["debug_output_dir"].mkdir(parents=True, exist_ok=True)
            with open(html_save_path, "w", encoding="utf-8") as f:
                f.write(sidebar_html)
            logging.info(f"Raw sidebar HTML saved to '{html_save_path}'")
        except Exception as e:
            logging.exception(f"Failed to save HTML to '{html_save_path}': {e}")

    async def _save_debug_structure(
        self,
        sidebar_structure: Dict,
        config_values: Dict,
        structure_filename: Optional[str],
    ) -> None:
        """Save debug structure file."""
        structure_save_filename = (
            structure_filename or config_values["default_structure_filename"]
        )
        structure_save_path = (
            config_values["debug_output_dir"] / structure_save_filename
        )

        try:
            config_values["debug_output_dir"].mkdir(parents=True, exist_ok=True)
            with open(structure_save_path, "w", encoding="utf-8") as f:
                json.dump(sidebar_structure, f, indent=4, ensure_ascii=False)
            logging.info(f"Parsed structure saved to '{structure_save_path}'")
        except Exception as e:
            logging.exception(
                f"Failed to save structure to '{structure_save_path}': {e}"
            )

    async def _process_items_from_structure(
        self,
        sidebar_structure: Dict,
        config_values: Dict,
        force: bool,
        test_item_id: Optional[str],
        max_items: Optional[int],
        resume_info: bool,
    ) -> None:
        """Process items from the sidebar structure."""
        logging.info("Proceeding to Phase 4: Content Scraping")

        if not sidebar_structure:
            logging.critical("Sidebar structure is missing. Cannot proceed.")
            sys.exit(1)

        # Flatten structure and get valid items
        flattened_structure = sidebar_parser.flatten_sidebar_structure(
            sidebar_structure
        )
        valid_items = [item for item in flattened_structure if item.get("id")]
        self.total_items_in_structure = len(valid_items)

        logging.info(
            f"Flattened structure contains {self.total_items_in_structure} valid items."
        )

        # Apply filtering
        items_to_process = self._filter_items_for_processing(
            valid_items, max_items, test_item_id
        )

        if not items_to_process:
            logging.warning("No items selected for processing. Exiting.")
            sys.exit(0)

        # Handle resume logic
        items_to_process = await self._handle_item_resume_logic(
            items_to_process, config_values, force
        )

        if not items_to_process:
            logging.info("All items already processed! Use --force to re-process.")
            sys.exit(0)

        # Process items
        await self._process_items_with_progress(items_to_process, config_values)

    def _filter_items_for_processing(
        self,
        valid_items: List[Dict],
        max_items: Optional[int],
        test_item_id: Optional[str],
    ) -> List[Dict]:
        """Filter items based on max_items and test_item_id parameters."""
        if max_items is not None and max_items >= 0:
            items_to_process = valid_items[:max_items]
            logging.info(f"Processing limited to first {len(items_to_process)} items.")
        elif test_item_id:
            logging.warning("--test-item-id is deprecated. Use --max-items=1.")
            items_to_process = [
                item for item in valid_items if item.get("id") == test_item_id
            ]
            if not items_to_process:
                logging.error(f"Item with ID '{test_item_id}' not found.")
        else:
            items_to_process = valid_items

        return items_to_process

    async def _handle_item_resume_logic(
        self,
        items_to_process: List[Dict],
        config_values: Dict,
        force: bool,
    ) -> List[Dict]:
        """Handle resume logic for item processing."""
        if force:
            return items_to_process

        # Check for existing files
        items_needing_processing = []
        existing_items = []

        for item in items_to_process:
            expected_file = storage.get_output_file_path(
                item.get("header"),
                item.get("menu"),
                item.get("text", "Unknown Item"),
                config_values["base_output_dir"],
            )
            if expected_file.exists():
                existing_items.append(item)
            else:
                items_needing_processing.append(item)

        if existing_items:
            logging.info(f"Found {len(existing_items)} existing files - skipping")
            self.skipped_count += len(existing_items)
            return items_needing_processing

        return items_to_process

    async def _process_items_with_progress(
        self,
        items_to_process: List[Dict],
        config_values: Dict,
    ) -> None:
        """Process items with progress tracking."""
        logging.info(f"Starting Phase 4: Processing {len(items_to_process)} items...")

        # Ensure output directory exists
        config_values["base_output_dir"].mkdir(parents=True, exist_ok=True)

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed} of {task.total})"),
            TimeElapsedColumn(),
            transient=False,
        )

        with progress:
            task_id = progress.add_task("Scraping Items", total=len(items_to_process))

            for item in items_to_process:
                await self._process_single_item(item, config_values, progress, task_id)

        # Log final summary
        await self._log_final_summary()

    async def _process_single_item(
        self,
        item: Dict,
        config_values: Dict,
        progress: Progress,
        task_id: int,
    ) -> None:
        """Process a single item from the structure."""
        item_id = item.get("id")
        item_text = item.get("text", "Unknown Item")
        item_type = item.get("type", "item")
        current_item_desc = f"{item_type.capitalize()}: '{item_text}' (ID: {item_id})"

        progress.update(task_id, description=f"Processing {current_item_desc}")

        try:
            if not item_id:
                logging.warning(f"Skipping item {item_text} - Missing ID.")
                self.skipped_count += 1
                progress.update(task_id, advance=1)
                return

            logging.info(f"Processing {current_item_desc}")

            if not self.driver:
                logging.error("WebDriver is not initialized. Cannot process item.")
                self.error_count += 1
                progress.update(
                    task_id,
                    advance=1,
                    description=f"Error processing {item_text} - No Driver",
                )
                return

            # Expand menus and click item
            await self._handle_menu_expansion_and_click(item, config_values)

            # Extract and save content
            await self._extract_and_save_content(item, config_values, progress, task_id)

        except Exception as item_error:
            logging.error(
                f"Error processing item {item_text} (ID: {item_id}): {item_error}"
            )
            self.error_count += 1
            progress.update(task_id, advance=1, description=f"Error: {item_text}")

    async def _handle_menu_expansion_and_click(
        self, item: Dict, config_values: Dict
    ) -> None:
        """Handle menu expansion and item clicking."""
        item_id = item.get("id")
        menu_text = item.get("menu")

        # Smart menu expansion
        if menu_text:
            logging.debug(
                f"Finding and expanding menu '{menu_text}' for node '{item_id}'"
            )
            try:
                success = await navigation.expand_menu_containing_node(
                    self.driver,
                    menu_text,
                    item_id,
                    timeout=config_values["navigation_timeout"],
                    expand_delay=config_values["expand_delay"],
                )
                if success:
                    logging.debug(f"Successfully expanded '{menu_text}' menu")
                else:
                    logging.warning(
                        f"Could not find node '{item_id}' in '{menu_text}' menu"
                    )
            except Exception as expand_err:
                logging.warning(
                    f"Error during menu expansion for '{menu_text}': {expand_err}"
                )

        # Legacy fallback
        parent_menu_text = item.get("parent_menu_text")
        if parent_menu_text and parent_menu_text != menu_text:
            logging.debug(
                f"Legacy fallback: expanding parent menu '{parent_menu_text}'"
            )
            try:
                await navigation.expand_specific_menu(
                    self.driver,
                    parent_menu_text,
                    timeout=config_values["navigation_timeout"],
                    expand_delay=config_values["expand_delay"],
                )
                await asyncio.sleep(0.3)
            except Exception as expand_err:
                logging.warning(
                    f"Could not expand parent menu '{parent_menu_text}': {expand_err}"
                )

        # Click the sidebar item
        await navigation.click_sidebar_item(
            self.driver, item_id, timeout=config_values["navigation_timeout"]
        )
        await asyncio.sleep(config_values["post_click_delay"])

    async def _extract_and_save_content(
        self,
        item: Dict,
        config_values: Dict,
        progress: Progress,
        task_id: int,
    ) -> None:
        """Extract content and save to file."""
        item_id = item.get("id")
        item_text = item.get("text", "Unknown Item")

        # Wait for content to load
        logging.debug(f"Waiting for content to load after clicking {item_id}...")
        await navigation.wait_for_content_update(
            self.driver, timeout=config_values["content_wait_timeout"]
        )
        logging.debug("Content area loaded.")

        # Save debug HTML if needed
        await self._save_debug_page_content(item_id, config_values)

        # Extract content
        extracted_content = await content_extractor.extract_and_convert_content(
            self.driver
        )

        # Save content
        if extracted_content:
            logging.debug(
                f"Extracted content (length: {len(extracted_content)}). Saving..."
            )
            saved = await storage.save_markdown(
                header=item.get("header"),
                menu=item.get("menu"),
                item_text=item_text,
                markdown_content=extracted_content,
                base_output_dir=config_values["base_output_dir"],
                overwrite=True,  # Force is handled at item level
            )

            if saved:
                self.processed_count += 1
                progress.update(task_id, advance=1, description=f"Saved {item_text}")
            else:
                self.error_count += 1
                progress.update(
                    task_id, advance=1, description=f"Error saving {item_text}"
                )
        else:
            logging.warning(f"No content extracted for item {item_id} ('{item_text}').")
            self.no_content_count += 1
            progress.update(
                task_id, advance=1, description=f"No content for {item_text}"
            )

    async def _save_debug_page_content(self, item_id: str, config_values: Dict) -> None:
        """Save debug page content HTML."""
        try:
            content_pane = self.driver.find_element(
                *selectors.CONTENT_PANE_INNER_HTML_TARGET
            )
            debug_html_content = content_pane.get_attribute("innerHTML")

            debug_html_path = (
                config_values["debug_output_dir"] / f"page_content_{item_id}.html"
            )
            debug_html_path.parent.mkdir(parents=True, exist_ok=True)

            with open(debug_html_path, "w", encoding="utf-8") as f:
                f.write(debug_html_content)
            logging.debug(f"Saved debug HTML to: {debug_html_path}")
        except Exception as e:
            logging.debug(f"Could not save debug HTML for {item_id}: {e}")

    async def _log_final_summary(self) -> None:
        """Log final processing summary."""
        logging.info("--- Wyrm Finished ---")
        logging.info(f"Processed: {self.processed_count}")
        logging.info(f"Skipped (existing/no ID): {self.skipped_count}")
        logging.info(f"Errors: {self.error_count}")
        logging.info(f"Items with no content extracted: {self.no_content_count}")
        logging.info(
            f"Total valid items found in structure: {self.total_items_in_structure}"
        )

        if self.skipped_count > 0:
            logging.info(f"💡 Resume tip: {self.skipped_count} files were skipped.")
            logging.info("💡 Use --resume-info to see detailed resume status")
            logging.info("💡 Use --force to re-process existing files")

    async def _cleanup(self) -> None:
        """Cleanup resources."""
        if self.driver:
            headless = self.config.get("webdriver", {}).get("headless", True)
            if not headless:
                non_headless_pause = self.config.get("debug_settings", {}).get(
                    "non_headless_pause_seconds", 10
                )
                if non_headless_pause > 0:
                    logging.info(
                        f"Non-headless mode: Pausing for {non_headless_pause}s..."
                    )
                    await asyncio.sleep(non_headless_pause)

            logging.info("Closing WebDriver...")
            self.driver.quit()
            self.driver = None
