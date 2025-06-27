import argparse
import asyncio
import json  # For printing the structure
import logging
import sys
from pathlib import Path  # Use pathlib for cleaner path handling

# from rich import print as rprint  # F401 Removed
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

# Need selenium exceptions here
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)

# Import all necessary modules
from wyrm import driver_setup  # Re-add selectors
from wyrm import content_extractor, navigation, sidebar_parser, storage, utils

# Add these imports
import os
from urllib.parse import urlparse


async def main():
    parser = argparse.ArgumentParser(description="Scrape Dell Developer API docs.")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to the configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=None,  # Default to None, will use config value if not specified
        help="Run in headless mode (overrides config)",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (overrides config)",
    )
    parser.add_argument(
        "--save-structure",
        metavar="FILENAME",
        nargs="?",
        default=argparse.SUPPRESS,
        help="Save parsed sidebar structure to debug dir. Optionally specify filename.",
    )
    parser.add_argument(
        "--save-html",
        metavar="FILENAME",
        nargs="?",
        default=argparse.SUPPRESS,
        help="Save raw sidebar HTML to debug dir. Optionally specify filename.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug: DEBUG logs, save structure/HTML, force non-headless.",
    )
    parser.add_argument(
        "--max-expand-attempts",
        type=int,
        default=None,
        help="Max menu expansion clicks (for testing/limiting). Overridden by --debug.",
    )
    # Add force argument for Phase 4
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing output files."
    )
    # Keep test-item-id for isolated testing if needed, but Phase 4 loop is the main goal
    parser.add_argument(
        "--test-item-id",
        type=str,
        default=None,
        help="DEPRECATED (use --max-items=1). Run P3 logic for only this item ID.",
    )
    # Add max-items argument for Phase 4 testing
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,  # Default to None, meaning process all items
        help="Max items to process from sidebar structure (for testing).",
    )
    # Add resume information option
    parser.add_argument(
        "--resume-info",
        action="store_true",
        help="Show resume information (what files exist vs need processing) and exit.",
    )

    args = parser.parse_args()

    # --- Load Config & Setup --- #
    try:
        cfg = utils.load_config(args.config)
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    log_level = args.log_level or cfg.get("log_level", "INFO")
    headless = (
        args.headless
        if args.headless is not None
        else cfg.get("webdriver", {}).get("headless", True)
    )

    # --- Debug Mode Handling ---
    save_structure_flag = hasattr(args, "save_structure")
    save_html_flag = hasattr(args, "save_html")
    debug_max_expand_attempts = 10

    if args.debug:
        logging.info("Debug mode enabled via command line.")
        log_level = "DEBUG"
        # headless = False # Debug implies non-headless
        save_structure_flag = True
        save_html_flag = True
        max_expand_attempts_arg = debug_max_expand_attempts
        logging.info(
            f"Debug mode overriding max expand attempts to: {max_expand_attempts_arg}"
        )
    else:
        max_expand_attempts_arg = args.max_expand_attempts

    utils.setup_logging(
        log_level=log_level, log_file=cfg.get("log_file", "logs/wyrm.log")
    )

    logging.info("--- Starting Wyrm ---")
    logging.debug(f"Config loaded: {cfg}")
    logging.debug(f"Effective log level: {log_level}")
    logging.debug(f"Effective headless mode: {headless}")
    logging.debug(f"Save structure flag present: {save_structure_flag}")
    logging.debug(f"Save HTML flag present: {save_html_flag}")
    logging.debug(f"Debug mode forcing saves: {args.debug}")
    logging.debug(f"Force overwrite enabled: {args.force}")
    logging.debug(
        f"Max items to process: {args.max_items if args.max_items is not None else 'All'}"
    )

    # --- Get Delays and Behavior settings ---
    delays_cfg = cfg.get("delays", {})
    # behavior_cfg = cfg.get("behavior", {}) # F841 Removed
    debug_cfg = cfg.get("debug_settings", {})
    output_cfg = cfg.get("output", {})

    # Base values
    navigation_timeout = delays_cfg.get("navigation", 10)
    sidebar_wait_timeout = delays_cfg.get("sidebar_wait", 15)
    expand_delay = delays_cfg.get("expand_menu", 0.5)
    post_expand_settle_delay = delays_cfg.get("post_expand_settle", 1.0)
    # Phase 3/4 delays
    post_click_delay = delays_cfg.get(
        "post_click", 0.5
    )  # Delay after clicking before waiting for content
    content_wait_timeout = delays_cfg.get(
        "content_wait", 20
    )  # Timeout for content appearance

    debug_output_dir = Path(debug_cfg.get("output_directory", "output/debug"))
    default_structure_filename = debug_cfg.get(
        "save_structure_filename", "structure.json"
    )
    default_html_filename = debug_cfg.get("save_html_filename", "sidebar_debug.html")
    non_headless_pause = debug_cfg.get("non_headless_pause_seconds", 10)
    base_output_dir = Path(
        output_cfg.get("directory", "output")
    )  # Main output directory

    # Apply non-headless overrides
    if not headless:
        logging.info(
            "Non-headless mode detected. Applying non-headless specific timings if available."
        )
        navigation_timeout = delays_cfg.get("navigation_noheadless", navigation_timeout)
        sidebar_wait_timeout = delays_cfg.get(
            "sidebar_wait_noheadless", sidebar_wait_timeout
        )
        expand_delay = delays_cfg.get("expand_menu_noheadless", expand_delay)
        post_expand_settle_delay = delays_cfg.get(
            "post_expand_settle_noheadless", post_expand_settle_delay
        )
        post_click_delay = delays_cfg.get("post_click_noheadless", post_click_delay)
        content_wait_timeout = delays_cfg.get(
            "content_wait_noheadless", content_wait_timeout
        )

    logging.debug(f"Using navigation timeout: {navigation_timeout}s")
    logging.debug(f"Using sidebar wait timeout: {sidebar_wait_timeout}s")
    logging.debug(f"Using expand menu delay: {expand_delay}s")
    logging.debug(f"Using post-expand settle delay: {post_expand_settle_delay}s")
    logging.debug(
        f"Using max expand attempts: {max_expand_attempts_arg if max_expand_attempts_arg is not None else 'Unlimited'}"
    )
    logging.debug(f"Using post-click delay: {post_click_delay}s")
    logging.debug(f"Using content wait timeout: {content_wait_timeout}s")
    logging.debug(f"Using debug output directory: {debug_output_dir}")
    logging.debug(f"Using main output directory: {base_output_dir}")
    logging.debug(f"Using non-headless pause: {non_headless_pause}s")

    # <<< START NEW STRUCTURE MAP HANDLING >>>
    # Use storage helper if available, otherwise construct path directly
    structure_filename = getattr(storage, 'get_structure_map_filename', lambda url: f"structure_{urlparse(url).netloc.replace('.', '_')}.json")(cfg["target_url"])
    structure_filepath = base_output_dir / structure_filename
    sidebar_structure = None
    driver = None # Initialize driver to None here
    expansion_performed = False # Track if live expansion happened

    # --- Phase 3: Load or Parse Sidebar Structure --- #
    logging.info("Proceeding to Phase 3: Sidebar Structure Loading/Parsing")

    # First, check if we can load an existing structure to do early resume check
    logging.info(f"Checking for existing structure map: {structure_filepath}")
    sidebar_structure = sidebar_parser.load_structure_map(str(structure_filepath))
    
    # If we have a structure, do an early resume check BEFORE initializing WebDriver
    if sidebar_structure:
        logging.info("Loaded existing sidebar structure map.")
        
        # Flatten the structure for early resume check
        flattened_structure = sidebar_parser.flatten_sidebar_structure(sidebar_structure)
        valid_items = [item for item in flattened_structure if item.get("id")]
        
        # Apply --max-items limit if specified
        items_to_check = valid_items
        if args.max_items is not None and args.max_items >= 0:
            items_to_check = valid_items[: args.max_items]
            logging.info(f"Resume check limited to first {len(items_to_check)} items (--max-items).")
        elif args.test_item_id:
            logging.warning("--test-item-id is deprecated. Use --max-items=1 and check structure file.")
            items_to_check = [item for item in valid_items if item.get("id") == args.test_item_id]
            if not items_to_check:
                logging.error(f"Item with ID '{args.test_item_id}' not found in flattened structure.")
                items_to_check = []
        
        # Pre-filter items to check which already exist
        items_needing_processing = []
        existing_items = []
        
        for item in items_to_check:
            expected_file = storage.get_output_file_path(
                item.get("header"), 
                item.get("menu"), 
                item.get("text", "Unknown Item"), 
                base_output_dir
            )
            if expected_file.exists():
                existing_items.append(item)
            else:
                items_needing_processing.append(item)
        
        # Handle --resume-info option BEFORE any browser operations
        if args.resume_info:
            print(f"\n📊 Resume Information:")
            print(f"  Total items in structure: {len(items_to_check)}")
            print(f"  ✅ Already processed: {len(existing_items)}")
            print(f"  🔄 Need processing: {len(items_needing_processing)}")
            print(f"  📁 Output directory: {base_output_dir}")
            
            if existing_items:
                print(f"\n✅ Existing files ({len(existing_items)}):")
                for item in existing_items[:10]:  # Show first 10
                    file_path = storage.get_output_file_path(
                        item.get("header"), item.get("menu"), 
                        item.get("text", "Unknown Item"), base_output_dir
                    )
                    print(f"    {item.get('text', 'Unknown')} -> {file_path}")
                if len(existing_items) > 10:
                    print(f"    ... and {len(existing_items) - 10} more")
            
            if items_needing_processing:
                print(f"\n🔄 Need processing ({len(items_needing_processing)}):")
                for item in items_needing_processing[:10]:  # Show first 10
                    print(f"    {item.get('text', 'Unknown')} (ID: {item.get('id')})")
                if len(items_needing_processing) > 10:
                    print(f"    ... and {len(items_needing_processing) - 10} more")
            
            print(f"\n💡 To resume processing: python main.py")
            print(f"💡 To force re-process all: python main.py --force")
            sys.exit(0)
        
        # Check if we can skip browser operations entirely
        if not args.force and not items_needing_processing:
            logging.info("All items already processed! Use --force to re-process existing files.")
            print(f"✅ All {len(existing_items)} items already processed!")
            print(f"📁 Output directory: {base_output_dir}")
            print(f"💡 Use --force to re-process existing files")
            print(f"💡 Use --resume-info to see detailed status")
            sys.exit(0)
        
        if not args.force and existing_items:
            logging.info(f"Found {len(existing_items)} existing files - will skip during processing")
            logging.info(f"Will process {len(items_needing_processing)} remaining items")

    driver = None # Initialize driver to None here
    expansion_performed = False # Track if live expansion happened

    if sidebar_structure:
        # We already loaded it above, now initialize driver for navigation
        logging.info("Initializing WebDriver for navigation with existing structure...")
        driver = driver_setup.initialize_driver(
            browser=cfg.get("webdriver", {}).get("browser", "chrome"), headless=headless
        )
        # --- ADDED: Navigate and wait for sidebar even if loaded ---
        logging.info("Navigating to target URL and waiting for sidebar...")
        await navigation.navigate_to_url(driver, cfg["target_url"], timeout=navigation_timeout)
        await navigation.wait_for_sidebar(driver, timeout=sidebar_wait_timeout)
        # --- END ADDED ---
        logging.info("Skipping initial *expansion* as structure was loaded.")
        # No sidebar_html available if loaded from file
        sidebar_html = None
        expansion_performed = False # Still false, as full expansion didn't happen
    else:
        logging.info("Structure map not found or failed to load. Performing live parsing...")
        # --- START LIVE PARSING LOGIC --- #
        if not driver: # Initialize if structure loading failed AND driver is None
             driver = driver_setup.initialize_driver(
                 browser=cfg.get("webdriver", {}).get("browser", "chrome"), headless=headless
             )

        await navigation.navigate_to_url(
            driver, cfg["target_url"], timeout=navigation_timeout
        )
        await navigation.expand_all_menus(
            driver, expand_delay=expand_delay, max_attempts=max_expand_attempts_arg
        )
        expansion_performed = True # Mark expansion as done
        await asyncio.sleep(post_expand_settle_delay)

        sidebar_html = sidebar_parser.get_sidebar_html(driver)

        # Save HTML if needed (only if parsed live)
        html_filename_arg = getattr(args, "save_html", None) if save_html_flag else None
        html_save_filename = (
            html_filename_arg
            if html_filename_arg is not None
            else default_html_filename
        )
        html_save_path = debug_output_dir / html_save_filename
        if sidebar_html and save_html_flag:
            try:
                debug_output_dir.mkdir(parents=True, exist_ok=True)
                with open(html_save_path, "w", encoding="utf-8") as f:
                    f.write(sidebar_html)
                logging.info(f"Raw sidebar HTML saved to '{html_save_path}'")
            except Exception as e:
                logging.exception(
                    f"Failed to save raw sidebar HTML to '{html_save_path}': {e}"
                )
        elif save_html_flag:
            logging.warning(
                "HTML save requested, but sidebar HTML could not be retrieved."
            )

        if not sidebar_html:
            logging.critical("Failed to get sidebar HTML. Cannot parse structure.")
            # No need to quit driver here, finally block handles it
            sys.exit(1)

        sidebar_structure = sidebar_parser.map_sidebar_structure(sidebar_html)

        # Save the NEWLY PARSED structure map
        if sidebar_structure:
            logging.info(f"Attempting to save newly parsed structure map to {structure_filepath}")
            sidebar_parser.save_structure_map(sidebar_structure, str(structure_filepath))
            # Also save to debug if requested
            structure_filename_arg = (
                getattr(args, "save_structure", None) if save_structure_flag else None
            )
            structure_save_filename = (
                structure_filename_arg
                if structure_filename_arg is not None
                else default_structure_filename
            )
            structure_save_path = debug_output_dir / structure_save_filename
            if save_structure_flag:
                try:
                    debug_output_dir.mkdir(parents=True, exist_ok=True)
                    with open(structure_save_path, "w", encoding="utf-8") as f:
                        json.dump(sidebar_structure, f, indent=4, ensure_ascii=False)
                    logging.info(f"Parsed structure saved to '{structure_save_path}'")
                except Exception as e:
                    logging.exception(
                        f"Failed to save parsed structure to '{structure_save_path}': {e}"
                    )
        else:
            logging.critical("Failed to parse sidebar structure from HTML.")
            # No need to quit driver here, finally block handles it
            sys.exit(1)
        # --- END LIVE PARSING LOGIC --- #

    # <<< END NEW STRUCTURE MAP HANDLING >>>

    # Initialize counters here, outside the try/except for structure loading
    processed_count = 0
    skipped_count = 0
    error_count = 0
    no_content_count = 0
    total_items_in_structure = 0  # Track total valid items

    try:
        # --- Phase 4: Loop Through Structure and Scrape --- #
        logging.info("Proceeding to Phase 4: Content Scraping")
        # Ensure structure exists before flattening
        if not sidebar_structure:
            logging.critical("Sidebar structure is missing after load/parse attempt. Cannot proceed.")
            sys.exit(1)

        # Flatten the structure for easier iteration (may be already done above if loaded from file)
        if 'flattened_structure' not in locals():
            flattened_structure = sidebar_parser.flatten_sidebar_structure(sidebar_structure)
        if 'valid_items' not in locals():
            valid_items = [item for item in flattened_structure if item.get("id")]
        total_items_in_structure = len(valid_items)
        logging.info(
            f"Flattened structure contains {total_items_in_structure} valid items with IDs."
        )

        # Apply --max-items limit if specified (may be already done above)
        if 'items_to_process' not in locals():
            items_to_process = valid_items
            if args.max_items is not None and args.max_items >= 0:
                items_to_process = valid_items[: args.max_items]
                logging.info(
                    f"Processing limited to first {len(items_to_process)} items (--max-items)."
                )
            elif args.test_item_id:
                logging.warning(
                    "--test-item-id is deprecated. Use --max-items=1 and check structure file."
                )
                items_to_process = [
                    item for item in valid_items if item.get("id") == args.test_item_id
                ]
                if not items_to_process:
                    logging.error(
                        f"Item with ID '{args.test_item_id}' not found in flattened structure."
                    )
                    items_to_process = [] # Ensure it's empty

        if not items_to_process:
            logging.warning("No items selected for processing. Exiting.")
            # Driver might be None if loading failed before init
            # The finally block will handle driver quit if it exists.
            sys.exit(0)

        # Do final resume check if not already done above
        if 'items_needing_processing' not in locals():
            items_needing_processing = []
            existing_items = []
            
            for item in items_to_process:
                expected_file = storage.get_output_file_path(
                    item.get("header"), 
                    item.get("menu"), 
                    item.get("text", "Unknown Item"), 
                    base_output_dir
                )
                if expected_file.exists():
                    existing_items.append(item)
                else:
                    items_needing_processing.append(item)
        
        if not args.force and existing_items:
            logging.info(f"Found {len(existing_items)} existing files - skipping (use --force to overwrite)")
            logging.debug(f"Existing files: {[item.get('text', 'Unknown') for item in existing_items]}")
            items_to_process = items_needing_processing
            skipped_count += len(existing_items)  # Count pre-skipped items
        elif args.force:
            items_to_process = items_to_process  # Process all items including existing ones
        
        if not items_to_process:
            logging.info("All items already processed! Use --force to re-process existing files.")
            if driver:
                driver.quit()
            sys.exit(0)

        logging.info(f"Starting Phase 4: Processing {len(items_to_process)} items...")
        logging.info(f"Pre-skipped {skipped_count} existing files (use --force to overwrite)")
        
        # Ensure base output dir exists
        base_output_dir.mkdir(parents=True, exist_ok=True)

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed} of {task.total})"),
            TimeElapsedColumn(),
            transient=False, # Keep progress visible after completion
        )

        with progress:
            task_id = progress.add_task(
                "Scraping Items", total=len(items_to_process)
            )

            for item_index, item in enumerate(items_to_process):
                item_id = item.get("id")
                item_text = item.get("text", "Unknown Item")
                item_type = item.get("type", "item")
                current_item_desc = f"{item_type.capitalize()}: '{item_text}' (ID: {item_id})"
                progress.update(task_id, description=f"Processing {current_item_desc}") # Update description

                try:
                    # Should always have ID due to filtering above, but check anyway
                    if not item_id:
                        logging.warning(f"Skipping item {item_text} - Missing ID.")
                        skipped_count += 1
                        progress.update(task_id, advance=1)
                        continue

                    logging.info(f"Processing {current_item_desc}")
                    # logging.debug(f"Target output file: {markdown_filepath}") # Path generated inside save_markdown

                    # Check if driver is still valid inside loop
                    if not driver:
                        logging.error("WebDriver is not initialized. Cannot process item.")
                        error_count += 1
                        progress.update(task_id, advance=1, description=f"Error processing {item_text} - No Driver")
                        continue # Skip to next item

                    # --- SMART Menu Expansion --- #
                    # Use the new function to find the correct menu containing our target node
                    menu_text = item.get("menu")
                    
                    if menu_text:
                        logging.debug(f"Finding and expanding the correct '{menu_text}' menu containing node '{item_id}'")
                        try:
                            success = await navigation.expand_menu_containing_node(
                                driver, menu_text, item_id, timeout=navigation_timeout, expand_delay=expand_delay
                            )
                            if success:
                                logging.debug(f"Successfully found and expanded the correct '{menu_text}' menu")
                            else:
                                logging.warning(f"Could not find target node '{item_id}' in any '{menu_text}' menu")
                        except Exception as expand_err:
                            logging.warning(f"Error during smart menu expansion for '{menu_text}': {expand_err}")
                    
                    # Legacy fallback for parent_menu_text if still used
                    parent_menu_text = item.get("parent_menu_text")
                    if parent_menu_text and parent_menu_text != menu_text:
                        logging.debug(f"Legacy fallback: ensuring parent menu '{parent_menu_text}' is expanded")
                        try:
                            await navigation.expand_specific_menu(
                                driver, parent_menu_text, timeout=navigation_timeout, expand_delay=expand_delay
                            )
                            await asyncio.sleep(0.3)
                        except Exception as expand_err:
                            logging.warning(f"Could not ensure legacy parent menu '{parent_menu_text}' was expanded: {expand_err}")
                    # --- END SMART Menu Expansion --- #

                    # Use the robust click function
                    clicked = await navigation.click_sidebar_item(
                        driver,
                        item_id,
                        timeout=navigation_timeout, # Use nav timeout for finding item
                    )
                    # Add delay manually if needed after the click attempt returns
                    await asyncio.sleep(post_click_delay)

                    if not clicked: # Check the return value if click_sidebar_item provides one (currently doesn't explicitly)
                        # If click_sidebar_item raises exceptions on failure, this check might not be needed
                        # If it returns bool, this check is useful.
                        # Assuming for now it raises on failure, otherwise adjust logic here.
                        pass # Error logged and exception raised within click_sidebar_item

                    # 2. Wait for Content and Extract
                    logging.debug(
                        f"Waiting for content to load after clicking {item_id}... (Timeout: {content_wait_timeout}s)"
                    )
                    # Content wait/extraction needs the driver
                    await navigation.wait_for_content_update(
                        driver, timeout=content_wait_timeout
                    )
                    logging.debug("Content area loaded.")

                    # Get content pane for debug HTML extraction
                    from wyrm import selectors
                    content_pane = driver.find_element(*selectors.CONTENT_PANE_INNER_HTML_TARGET)
                    debug_html_content = content_pane.get_attribute("innerHTML")
                    # Save debug HTML for analysis
                    if args.debug:
                        debug_html_path = debug_output_dir / f"page_content_{item_id}.html"
                        debug_html_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(debug_html_path, 'w', encoding='utf-8') as f:
                            f.write(debug_html_content)
                        logging.debug(f"Saved debug HTML to: {debug_html_path}")

                    # Extract content
                    extracted_content = await content_extractor.extract_and_convert_content(driver)

                    # 3. Save Content
                    if extracted_content:
                        logging.debug(f"Extracted markdown content (length: {len(extracted_content)}). Saving...")
                        # Call the correct save function which handles path generation
                        saved = await storage.save_markdown(
                            header=item.get("header"),
                            menu=item.get("menu"),
                            item_text=item_text,
                            markdown_content=extracted_content,
                            base_output_dir=base_output_dir,
                            overwrite=args.force,
                        )
                        if saved:
                             processed_count += 1
                             progress.update(task_id, advance=1, description=f"Saved {item_text}")
                        else:
                            # save_markdown logs errors/skips, update counters based on return
                            if Path(storage.get_output_file_path(item.get("header"), item.get("menu"), item_text, base_output_dir)).exists() and not args.force:
                                skipped_count += 1 # It likely skipped because file exists
                            else:
                                error_count += 1 # Assume error if not skipped and not saved
                            progress.update(task_id, advance=1, description=f"Skipped/Error saving {item_text}") # General update
                    else:
                        logging.warning(
                            f"No content extracted or converted for item {item_id} ('{item_text}')."
                        )
                        no_content_count += 1
                        progress.update(task_id, advance=1, description=f"No content for {item_text}")
                        
                except Exception as item_error:
                    logging.error(f"Error processing item {item_text} (ID: {item_id}): {item_error}")
                    error_count += 1
                    progress.update(task_id, advance=1, description=f"Error: {item_text}")

    except KeyboardInterrupt:
        logging.warning("--- User interrupted execution ---")
    except Exception as e:
        logging.exception(f"--- An unexpected error occurred in main loop: {e} ---")
    finally:
        if driver:
            if not headless and non_headless_pause > 0:
                logging.info(f"Non-headless mode: Pausing for {non_headless_pause}s before closing browser...")
                await asyncio.sleep(non_headless_pause)
            logging.info("Closing WebDriver...")
            driver.quit()

    logging.info("--- Wyrm Finished ---")
    logging.info(f"Processed: {processed_count}")
    logging.info(f"Skipped (existing/no ID): {skipped_count}")
    logging.info(f"Errors: {error_count}")
    logging.info(f"Items with no content extracted: {no_content_count}")
    logging.info(f"Total valid items found in structure: {total_items_in_structure}")
    
    # Resume information
    if skipped_count > 0 and not args.force:
        logging.info(f"💡 Resume tip: {skipped_count} files were skipped because they already exist.")
        logging.info(f"💡 Use --resume-info to see detailed resume status")
        logging.info(f"💡 Use --force to re-process existing files")


if __name__ == "__main__":
    asyncio.run(main())
