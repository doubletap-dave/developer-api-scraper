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
from scraper import driver_setup  # Re-add selectors
from scraper import content_extractor, navigation, sidebar_parser, storage, utils


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
        log_level=log_level, log_file=cfg.get("log_file", "logs/scraper.log")
    )

    logging.info("--- Starting Scraper ---")
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

    driver = None
    sidebar_structure = []  # Reinitialize here where it's actually used
    processed_count = 0
    skipped_count = 0
    error_count = 0
    no_content_count = 0
    total_items_in_structure = 0  # Track total valid items

    try:
        # --- Phase 1 & 2: Setup and Sidebar Parsing (Run always) ---
        logging.info(
            "Running Phase 1 & 2: Setup, Navigation, Sidebar Expansion & Parsing"
        )
        driver = driver_setup.initialize_driver(
            browser=cfg.get("webdriver", {}).get("browser", "chrome"), headless=headless
        )
        await navigation.navigate_to_url(
            driver, cfg["target_url"], timeout=navigation_timeout
        )
        await navigation.expand_all_menus(
            driver, expand_delay=expand_delay, max_attempts=max_expand_attempts_arg
        )
        await asyncio.sleep(post_expand_settle_delay)

        sidebar_html = sidebar_parser.get_sidebar_html(driver)

        # Save HTML if needed
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
                f"Could not save sidebar HTML to '{html_save_path}' because it was empty."
            )

        # Parse Structure
        if sidebar_html:
            # The structure is now a list of header blocks, each containing children
            sidebar_structure_blocks = sidebar_parser.map_sidebar_structure(
                sidebar_html
            )
            logging.info(
                f"Phase 1 & 2 completed. Found {len(sidebar_structure_blocks)} top-level header blocks."
            )

            # --- Save Structure if needed ---
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
                    # Save the list of blocks directly
                    with open(structure_save_path, "w", encoding="utf-8") as f:
                        json.dump(
                            sidebar_structure_blocks, f, indent=2, ensure_ascii=False
                        )
                    logging.info(
                        f"Parsed sidebar structure saved to '{structure_save_path}'"
                    )
                except Exception as e:
                    logging.exception(
                        f"Failed to save structure to '{structure_save_path}': {e}"
                    )
            # --- End Save Structure ---

            # Flatten the structure for processing using the dedicated function
            sidebar_structure = sidebar_parser.flatten_sidebar_structure(
                sidebar_structure_blocks
            )
            # Calculate total AFTER flattening
            total_items_in_structure = len(sidebar_structure)
            # Original structure is saved above if needed
            # sidebar_structure = [
            #     item
            #     for block in sidebar_structure_blocks
            #     for item in block.get("children", [])
            # ]
            # total_items_in_structure = len(sidebar_structure)
            # logging.info(
            #     f"Flattened structure contains {total_items_in_structure} clickable items to process."
            # )
        else:
            logging.error(
                "Sidebar HTML was empty. Cannot parse structure or proceed further."
            )
            # Optionally raise an error or exit if structure is essential
            # For now, let's just log and prepare to exit gracefully
            sidebar_structure = []
            total_items_in_structure = 0

        # --- Phase 3 & 4: Item Processing ---
        if args.test_item_id:
            logging.warning(
                "Using deprecated --test-item-id. Prefer --max-items for testing."
            )
            # Find the specific item to test
            test_item = next(
                (
                    item
                    for item in sidebar_structure
                    if item.get("id") == args.test_item_id
                ),
                None,
            )
            if test_item:
                logging.info(f"Processing only test item: {args.test_item_id}")
                sidebar_structure = [test_item]  # Process only this item
                total_items_in_structure = 1
            else:
                logging.error(
                    f"Test item ID '{args.test_item_id}' not found in structure."
                )
                sidebar_structure = []
                total_items_in_structure = 0
        elif args.max_items is not None and args.max_items >= 0:
            logging.info(f"Limiting processing to a maximum of {args.max_items} items.")
            sidebar_structure = sidebar_structure[: args.max_items]
            total_items_in_structure = len(sidebar_structure)
            logging.info(
                f"Actual items to process after limit: {total_items_in_structure}"
            )

        if not sidebar_structure:
            logging.warning("Sidebar structure is empty. No items to process.")
        else:
            # Set up Progress Bar
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed} of {task.total})"),
                TimeElapsedColumn(),
                # TextColumn("[bold blue]Skipped: {task.fields[skipped]}"), # Removed custom fields for now
                # TextColumn("[bold red]Errors: {task.fields[errors]}"),
            )

            with progress:
                task = progress.add_task(
                    "[cyan]Scraping Items...",
                    total=total_items_in_structure,
                    # skipped=0, # Removed custom fields
                    # errors=0,
                )

                for (
                    item
                ) in sidebar_structure:  # sidebar_structure is the flattened list now
                    item_id = item.get("id")  # Might be None
                    item_text = item.get("text", "Unknown Item")
                    item_type = item.get("type")  # Crucial check

                    # --- Skip if not a clickable item with an ID --- #
                    if item_type != "item" or not item_id:
                        if item_type == "menu":
                            log_msg = f"Skipping entry because it's a menu: '{item_text}' (ID: {item_id or 'None'})"
                            logging.debug(log_msg)
                        elif not item_id:
                            log_msg = (
                                f"Skipping item '{item_text}' because it lacks an ID."
                            )
                            logging.warning(log_msg)
                        else:
                            log_msg = f"Skipping entry '{item_text}' (Type: {item_type}, ID: {item_id}). Not a processable item."
                            logging.warning(log_msg)
                        progress.update(
                            task, advance=1
                        )  # Advance progress for skipped non-target items
                        # Consider using a different counter if distinguishing skips is important
                        # skipped_count += 1
                        continue
                    # --- End Skip Check --- #

                    item_header = item.get("header", None)
                    item_menu = item.get("menu", None)
                    logging.info(
                        f"--- Processing Item: '{item_text}' (ID: {item_id}) ---"
                    )

                    try:
                        output_file_path = utils.get_output_file_path(
                            item_header, item_menu, item_text, base_output_dir
                        )
                        if output_file_path.exists() and not args.force:
                            logging.info(
                                f"Item '{item_text}' already exists and --force not used. Skipping."
                            )
                            skipped_count += 1
                            # progress.update(task, advance=1, skipped=skipped_count) # Removed custom fields
                            progress.update(task, advance=1)
                            continue

                        # --- Re-expand parent menu if necessary (dynamic collapse fix) ---
                        parent_menu_text = item.get("parent_menu_text")
                        if parent_menu_text:
                            log_msg = f"Ensuring parent menu '{parent_menu_text}' is expanded before clicking '{item_text}'"
                            logging.debug(log_msg)
                            await navigation.expand_specific_menu(
                                driver, parent_menu_text, expand_delay=expand_delay
                            )
                            # Add a small delay after expanding to let the DOM settle
                            await asyncio.sleep(0.5)
                        # --- End dynamic collapse fix ---

                        await navigation.click_sidebar_item(
                            driver, item_id, timeout=navigation_timeout
                        )
                        await asyncio.sleep(
                            post_click_delay
                        )  # Small delay before content wait

                        # Wait for content pane to potentially update
                        await navigation.wait_for_content_update(
                            driver, timeout=content_wait_timeout
                        )

                        # Extract content
                        markdown_content = (
                            await content_extractor.extract_and_convert_content(driver)
                        )

                        if markdown_content:
                            saved = await storage.save_markdown(
                                item_header,
                                item_menu,
                                item_text,
                                markdown_content,
                                base_output_dir,
                                overwrite=args.force,
                            )
                            if saved:
                                processed_count += 1
                            else:
                                # This case shouldn't happen if we checked file existence above,
                                # but handle potential save errors logged by save_markdown
                                logging.warning(
                                    f"save_markdown indicated failure for item '{item_text}', check previous logs."
                                )
                                error_count += 1
                        else:
                            logging.warning(
                                f"No content extracted for item '{item_text}' (ID: {item_id}). Skipping save."
                            )
                            no_content_count += 1
                            # Optionally treat this as an error or just a skip
                            error_count += 1  # Let's count it as an error for now

                    except TimeoutException as e:
                        logging.error(
                            f"Timeout processing item '{item_text}' (ID: {item_id}): {e}"
                        )
                        error_count += 1
                    except ElementClickInterceptedException as e:
                        logging.error(
                            f"Click intercepted for item '{item_text}' (ID: {item_id}): {e}"
                        )
                        error_count += 1
                    except NoSuchElementException as e:
                        logging.error(
                            f"Could not find element for item '{item_text}' (ID: {item_id}): {e}"
                        )
                        error_count += 1
                    except Exception as e:
                        logging.exception(
                            f"Unexpected error processing item '{item_text}' (ID: {item_id}): {e}"
                        )
                        error_count += 1
                    finally:
                        # Update progress regardless of outcome for this item
                        # progress.update(task, advance=1, errors=error_count, skipped=skipped_count) # Removed custom fields
                        progress.update(task, advance=1)

        # --- End of Processing Loop ---

        # Keep browser open for inspection if not headless and not processing all items
        if not headless and args.max_items is not None:
            logging.info(
                f"Limited run complete. Browser will remain open for {non_headless_pause} seconds for inspection..."
            )
            await asyncio.sleep(non_headless_pause)

    except Exception as e:
        logging.exception(f"An unhandled error occurred in main: {e}")
    finally:
        if driver:
            logging.info("Closing WebDriver.")
            # Optional pause before closing if not headless, useful for debugging
            if not headless:
                logging.info(
                    f"Non-headless mode: Pausing for {non_headless_pause} seconds before closing browser..."
                )
                await asyncio.sleep(non_headless_pause)
            driver.quit()
            logging.info("WebDriver closed.")

    logging.info("--- Scraper Finished ---")
    logging.info("Run Summary:")
    logging.info(f"  Total items in structure: {total_items_in_structure}")
    # Correctly calculate items attempted based on limit or full structure
    items_attempted = len(sidebar_structure)
    logging.info(f"  Items attempted:          {items_attempted}")
    logging.info(f"  Successfully processed:   {processed_count}")
    logging.info(f"  Skipped (already exist):  {skipped_count}")
    logging.info(f"  No content extracted:     {no_content_count}")
    logging.info(f"  Errors during processing: {error_count}")
    logging.info("--- End of Run ---")


if __name__ == "__main__":
    asyncio.run(main())
