import asyncio
import logging
from typing import cast

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from . import selectors

# --- Wait Utilities ---


async def wait_for_loader_to_disappear(driver: WebDriver, timeout: int = 10):
    """Wait for the 'Processing, please wait...' overlay to disappear."""
    log_msg = (
        f"Loader overlay detected: '{selectors.LOADER_OVERLAY}'. "
        f"Waiting up to {timeout}s for it to disappear..."
    )
    logging.debug(log_msg)
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located(selectors.LOADER_OVERLAY)
        )
        logging.debug("Loader overlay is not visible.")
    except TimeoutException:
        log_warn = f"Loader overlay did not disappear within {timeout} seconds."
        logging.warning(log_warn)
        # Decide if this should raise an error or just log a warning
        # For now, let's just log it.
    except Exception as e:
        # Catch potential NoSuchElementException if it's *never* there
        # invisibility_of_element should handle that.
        log_err = (
            "An unexpected error occurred while waiting for loader "
            f"to disappear: {e}"
        )
        logging.exception(log_err)
        # Decide on recovery or re-raise


# --- Navigation and Basic Waits ---


async def navigate_to_url(driver: WebDriver, url: str, timeout: int = 10):
    """Navigate WebDriver to URL and wait for initial load + loader."""
    logging.info(f"Navigating to URL: {url}")
    try:
        driver.get(url)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((selectors.By.TAG_NAME, "body"))
        )
        logging.info(f"Successfully navigated to {url}")
        # Wait for sidebar before checking loader
        await wait_for_sidebar(driver, timeout)
        # Now, wait for any initial loader
        await wait_for_loader_to_disappear(driver)
    except TimeoutException:
        log_err = (
            f"Timeout ({timeout}s) occurred during navigation or "
            f"initial waits for {url}"
        )
        logging.error(log_err)
        raise
    except Exception as e:
        log_err = (
            "An error occurred during navigation or initial waits for " f"{url}: {e}"
        )
        logging.exception(log_err)
        raise


def wait_for_element(
    driver: WebDriver,
    by: selectors.By,
    value: str,
    timeout: int = 10,
    description: str = "element",
) -> WebElement:
    """Wait for a specific element to be present in the DOM."""
    log_msg = f"Waiting up to {timeout}s for {description} ({by}: {value})..."
    logging.debug(log_msg)
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        logging.debug(f"{description.capitalize()} found.")
        return element
    except TimeoutException:
        log_err = f"Timeout ({timeout}s) waiting for {description} ({by}: {value})."
        logging.error(log_err)
        raise TimeoutException(f"Timeout waiting for {description} ({by}: {value})")
    except Exception as e:
        log_err = f"Error waiting for {description} ({by}: {value}): {e}"
        logging.exception(log_err)
        raise


async def wait_for_sidebar(driver: WebDriver, timeout: int = 15) -> WebElement:
    """Wait specifically for the sidebar container element (now async)."""
    logging.info(f"Waiting up to {timeout}s for sidebar container...")
    try:
        sidebar = wait_for_element(
            driver,
            cast(selectors.By, selectors.SIDEBAR_CONTAINER[0]),
            selectors.SIDEBAR_CONTAINER[1],
            timeout,
            description="sidebar container",
        )
        logging.info("Sidebar container found.")
        return sidebar
    except TimeoutException:
        log_err = f"Sidebar container did not appear within {timeout} seconds."
        logging.error(log_err)
        raise
    except Exception as e:
        log_err = f"An unexpected error occurred while waiting for the sidebar: {e}"
        logging.exception(log_err)
        raise


# --- Sidebar Interaction ---


async def expand_all_menus(
    driver: WebDriver, expand_delay: float = 0.5, max_attempts: int | None = None
):
    """
    Expands all collapsible sidebar menus by repeatedly clicking expander icons.
    Stops when no more icons are found or max_attempts is reached.
    Includes delays, retries, and loader waits.
    """
    max_attempts_str = max_attempts or "Unlimited"
    log_start = f"Starting sidebar menu expansion... (Max attempts: {max_attempts_str})"
    logging.info(log_start)
    attempts = 0
    while max_attempts is None or attempts < max_attempts:
        attempts += 1
        attempt_log_str = f" Attempt {attempts}/{max_attempts}" if max_attempts else ""
        logging.info(f"Looking for next menu to expand...{attempt_log_str}")

        found_and_clicked_expander = False
        try:
            icon_selector = selectors.SIDEBAR_MENU_EXPANDER_ICON
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(icon_selector)
                )
                logging.debug("At least one expander icon is present in the DOM.")
            except TimeoutException:
                log_info = (
                    "No expander icons found (presence check). "
                    "Assuming expansion is complete."
                )
                logging.info(log_info)
                break

            logging.debug(f"Looking for expander icons using: {icon_selector}")
            expander_icons = driver.find_elements(*icon_selector)

            if not expander_icons:
                logging.info("No more collapsed menus found. Expansion complete.")
                break

            icon_count = len(expander_icons)
            logging.info(
                f"Found {icon_count} potential menus to expand this iteration."
            )

            expander_icon = expander_icons[0]
            parent_li_for_wait = None
            parent_id_str = "No ID"  # Default if parent lookup fails

            try:
                try:
                    xpath = selectors.MENU_CLICKABLE_PARENT_XPATH
                    parent_li_for_wait = expander_icon.find_element(
                        selectors.By.XPATH, xpath
                    )
                    parent_id_str = parent_li_for_wait.get_attribute("id") or "No ID"
                    logging.debug(f"Identified parent LI ({parent_id_str}) for icon.")
                except NoSuchElementException:
                    logging.warning("Could not find parent LI for icon.")

                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView(false);", expander_icon
                    )
                    log_scroll = (
                        f"Scrolled expander icon (Parent LI ID: {parent_id_str}) "
                        f"into view (aligned bottom)."
                    )
                    logging.debug(log_scroll)
                    await asyncio.sleep(0.2)
                except Exception as scroll_err:
                    logging.warning(f"Could not scroll icon into view: {scroll_err}")

                expander_icon.click()
                logging.info(f"Clicked expander icon (Parent LI ID: {parent_id_str})")
                found_and_clicked_expander = True

                # --- Wait for Loader ---
                await wait_for_loader_to_disappear(driver)
                # --- End Wait for Loader ---

                # Keep small delay for animations post-loader
                await asyncio.sleep(expand_delay)

            except ElementClickInterceptedException:
                log_warn = (
                    f"Click intercepted for icon (Parent LI ID: {parent_id_str}). "
                    f"Trying next pass."
                )
                logging.warning(log_warn)
                # Wait for loader in case interception was caused by loader
                await wait_for_loader_to_disappear(driver)
            except NoSuchElementException:
                log_warn = (
                    f"Could not find expander icon or its parent "
                    f"(Parent LI ID: {parent_id_str}). It might have "
                    f"disappeared. Trying next pass."
                )
                logging.warning(log_warn)
            except Exception as e:
                log_err = (
                    f"Unexpected error clicking expander "
                    f"(Parent LI ID: {parent_id_str}): {e}. Trying next pass."
                )
                logging.exception(log_err)
                # Also wait for loader after unexpected error
                await wait_for_loader_to_disappear(driver)

            if not found_and_clicked_expander:
                log_debug = (
                    "Did not click an expander this pass, " "moving to next attempt."
                )
                logging.debug(log_debug)
                await asyncio.sleep(0.5)  # Small delay if nothing was clicked

        except NoSuchElementException:
            log_info = (
                "No expander icons found with selector. "
                "Assuming expansion is complete."
            )
            logging.info(log_info)
            break
        except Exception as e:
            log_err = f"An error occurred during menu expansion outer loop: {e}"
            logging.exception(log_err)
            logging.error("Error during expansion, pausing before retry or exit...")
            if max_attempts is not None and attempts >= max_attempts:
                log_err_max = f"Max attempts ({max_attempts}) reached after error."
                logging.error(log_err_max)
                break
            # Wait for loader even after outer loop error
            await wait_for_loader_to_disappear(driver)
            await asyncio.sleep(1.0)

    if max_attempts is not None and attempts >= max_attempts:
        log_warn = (
            f"Sidebar expansion stopped after reaching max attempts "
            f"({max_attempts}). Some menus might not be expanded."
        )
        logging.warning(log_warn)
    else:
        log_info = (
            "Finished sidebar expansion process " "(no more expandable items found)."
        )
        logging.info(log_info)


# --- Item Interaction ---


async def expand_specific_menu(
    driver: WebDriver, menu_text: str, timeout: int = 10, expand_delay: float = 0.2
):
    """
    Ensures a specific menu (identified by its visible text) is expanded.

    Checks if already expanded. If not, finds the LI, its expander icon,
    scrolls, clicks, and waits for the loader.
    Uses XPath to locate elements based on text content.
    """
    if not menu_text:
        logging.warning("expand_specific_menu called with no menu_text. Skipping.")
        return

    # --- Log Start ---
    # Escape quotes in menu_text for safe use in XPath and logs
    safe_menu_text = menu_text.replace('"', "'").replace("'", '"')
    log_start_msg = f"[expand_specific_menu] Starting for menu_text: '{safe_menu_text}'"
    logging.debug(log_start_msg)

    # XPath to find the LI containing the specific text (div with normalized text)
    menu_li_xpath = (
        f"//li[contains(@class, 'toc-item') and "
        f".//div[normalize-space(.)='{safe_menu_text}']]"
    )
    # XPath for the collapsed icon relative to the found LI
    collapsed_icon_xpath = (
        f"{menu_li_xpath}//i[contains(@class, 'dds__icon--chevron-right')]"
    )
    # XPath for the expanded icon relative to the found LI
    expanded_icon_xpath = (
        f"{menu_li_xpath}//i[contains(@class, 'dds__icon--chevron-down')]"
    )

    log_xpath_msg = (
        f"[expand_specific_menu] Using XPath to find menu LI: {menu_li_xpath}"
    )
    logging.debug(log_xpath_msg)

    try:
        # Find the menu LI element first
        log_locate_msg = (
            "[expand_specific_menu] Locating menu LI element using XPath..."
        )
        logging.debug(log_locate_msg)
        menu_li = WebDriverWait(driver, 5).until(  # noqa: F841
            EC.presence_of_element_located((selectors.By.XPATH, menu_li_xpath))
        )
        log_found_msg = (
            f"[expand_specific_menu] Found menu LI for text "
            f"'{safe_menu_text}'. Checking expansion state..."
        )
        logging.debug(log_found_msg)

        # Check if already expanded (look for expanded icon *within* the found menu_li)
        try:
            log_check_expanded = (
                f"[expand_specific_menu] Checking for expanded icon "
                f"using XPath: {expanded_icon_xpath}"
            )
            logging.debug(log_check_expanded)
            # Use find_element relative to menu_li or absolute xpath
            expanded_icon = driver.find_element(selectors.By.XPATH, expanded_icon_xpath)
            if expanded_icon.is_displayed():
                log_already_expanded = (
                    f"[expand_specific_menu] Menu '{safe_menu_text}' "
                    f"appears already expanded. Returning."
                )
                logging.debug(log_already_expanded)
                return
            else:
                log_expanded_not_disp = (
                    f"[expand_specific_menu] Expanded icon found "
                    f"for '{safe_menu_text}', but not displayed. "
                    f"Will check/click collapsed icon."
                )
                logging.debug(log_expanded_not_disp)
        except NoSuchElementException:
            log_expanded_not_found = (
                f"[expand_specific_menu] Expanded icon not found "
                f"for '{safe_menu_text}' using XPath. Assuming collapsed."
            )
            logging.debug(log_expanded_not_found)
            pass

        # Find the collapsed icon relative to the menu LI
        log_find_collapsed = (
            f"[expand_specific_menu] Looking for collapsed icon "
            f"using XPath: {collapsed_icon_xpath}"
        )
        logging.debug(log_find_collapsed)
        collapsed_icon = WebDriverWait(driver, 5).until(
            # Expect icon present if LI found and not expanded
            EC.presence_of_element_located((selectors.By.XPATH, collapsed_icon_xpath))
        )
        log_found_collapsed = (
            f"[expand_specific_menu] Found collapsed icon for '{safe_menu_text}'."
        )
        logging.debug(log_found_collapsed)

        log_expanding = (
            f"[expand_specific_menu] Expanding specific menu by text: "
            f"'{safe_menu_text}'"
        )
        logging.info(log_expanding)
        log_scroll_click = (
            "[expand_specific_menu] Scrolling collapsed icon into view "
            "and preparing to click."
        )
        logging.debug(log_scroll_click)
        driver.execute_script("arguments[0].scrollIntoView(false);", collapsed_icon)
        await asyncio.sleep(0.1)
        collapsed_icon.click()
        log_click_attempt = (
            f"[expand_specific_menu] Click attempted on collapsed icon "
            f"for menu '{safe_menu_text}'."
        )
        logging.debug(log_click_attempt)

        log_wait_loader = (
            "[expand_specific_menu] Waiting for loader to disappear after click."
        )
        logging.debug(log_wait_loader)
        await wait_for_loader_to_disappear(driver, timeout=timeout)
        await asyncio.sleep(expand_delay)
        log_finish_expand = (
            f"[expand_specific_menu] Finished expanding menu "
            f"'{safe_menu_text}' and waited for loader."
        )
        logging.info(log_finish_expand)

    except TimeoutException as e:
        # Could be timeout finding LI or collapsed icon
        log_warn_timeout = (
            f"[expand_specific_menu] TimeoutException for menu "
            f"'{safe_menu_text}'. XPath: {menu_li_xpath} / "
            f"{collapsed_icon_xpath}. Error: {e}"
        )
        logging.warning(log_warn_timeout)
        # Check if it's actually expanded now
        try:
            driver.find_element(selectors.By.XPATH, expanded_icon_xpath)
            log_info_expanded_after_timeout = (
                f"[expand_specific_menu] Menu "
                f"'{safe_menu_text}' seems expanded "
                f"after TimeoutException."
            )
            logging.info(log_info_expanded_after_timeout)
        except NoSuchElementException:
            log_err_not_found_after_timeout = (
                f"[expand_specific_menu] Could not find LI, "
                f"collapsed, or expanded icon for menu "
                f"'{safe_menu_text}' after timeout."
            )
            logging.error(log_err_not_found_after_timeout)

    except ElementClickInterceptedException:
        log_warn_intercept = (
            f"[expand_specific_menu] Click intercepted for expander "
            f"icon of menu '{safe_menu_text}'. Waiting for loader "
            f"and retrying."
        )
        logging.warning(log_warn_intercept)
        await wait_for_loader_to_disappear(driver, timeout=5)
        try:
            log_retry_find_click = (
                f"[expand_specific_menu] Retrying find/click for "
                f"collapsed icon '{safe_menu_text}'."
            )
            logging.debug(log_retry_find_click)
            collapsed_icon = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (selectors.By.XPATH, collapsed_icon_xpath)
                )
            )
            driver.execute_script("arguments[0].scrollIntoView(false);", collapsed_icon)
            await asyncio.sleep(0.1)
            collapsed_icon.click()
            log_info_retry_success = (
                f"[expand_specific_menu] Successfully clicked expander "
                f"for '{safe_menu_text}' after interception."
            )
            logging.info(log_info_retry_success)
            log_debug_wait_loader_retry = (
                "[expand_specific_menu] Waiting for loader " "after retry click."
            )
            logging.debug(log_debug_wait_loader_retry)
            await wait_for_loader_to_disappear(driver, timeout=timeout)
            await asyncio.sleep(expand_delay)
        except Exception as retry_e:
            log_err_retry_failed = (
                f"[expand_specific_menu] Failed to click expander "
                f"for menu '{safe_menu_text}' even after retry: "
                f"{retry_e}"
            )
            logging.error(log_err_retry_failed)

    except NoSuchElementException as e:
        # Likely initial LI search failed
        log_err_nse = (
            f"[expand_specific_menu] NoSuchElementException. Could not find "
            f"menu LI or icons for text '{safe_menu_text}'. "
            f"XPath: {menu_li_xpath}. Error: {e}"
        )
        logging.error(log_err_nse)

    except Exception as e:
        log_err_unexpected = (
            f"[expand_specific_menu] An unexpected error occurred "
            f"expanding specific menu by text '{safe_menu_text}': {e}"
        )
        logging.exception(log_err_unexpected)

    log_finish_func = (
        f"[expand_specific_menu] Finishing for menu_text: '{safe_menu_text}'"
    )
    logging.debug(log_finish_func)


# Selector for the tooltip (based on error message)
TOOLTIP_SELECTOR = (selectors.By.CSS_SELECTOR, "span#dds__tooltip__body")


async def click_sidebar_item(driver: WebDriver, item_id: str, timeout: int = 10):
    """Clicks item link by parent LI ID using JavaScript to bypass interceptions."""
    log_start_click = (
        f"Attempting to JAVASCRIPT click sidebar item link "
        f"associated with LI ID: {item_id}"
    )
    logging.info(log_start_click)
    item_link_selector_str = f"li[id='{item_id}'] a"
    item_link_selector = (selectors.By.CSS_SELECTOR, item_link_selector_str)
    try:
        log_wait_present = (
            f"Waiting for sidebar item link to be present: {item_link_selector}"
        )
        logging.debug(log_wait_present)
        item_link = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(item_link_selector)
        )
        logging.debug("Sidebar item link is present in DOM.")

        logging.debug(f"Scrolling item link {item_id} into view.")
        driver.execute_script("arguments[0].scrollIntoView(false);", item_link)
        await asyncio.sleep(0.1)  # Tiny sleep after scrolling

        # --- CHANGED: Use JavaScript click --- #
        logging.debug(f"Attempting JavaScript click on item link {item_id}.")
        driver.execute_script("arguments[0].click();", item_link)
        # --- END CHANGED --- #

        log_success_click = (
            f"Successfully triggered JavaScript click on sidebar item link {item_id}."
        )
        logging.info(log_success_click)

    except TimeoutException:
        log_err_timeout = (
            f"Timeout waiting for presence of link "
            f"({item_link_selector_str}) for sidebar item ID: {item_id}"
        )
        logging.error(log_err_timeout)
        raise
    except (
        ElementClickInterceptedException
    ):  # Still catch this, though hopefully less likely
        log_warn_intercept = (
            f"JavaScript click intercepted for sidebar item link ID: "
            f"{item_id}. Waiting for loader and retrying JS click once..."
        )
        logging.warning(log_warn_intercept)
        await wait_for_loader_to_disappear(driver, timeout=5)
        try:
            item_link = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(item_link_selector)
            )
            logging.debug("Found item link again for retry.")
            driver.execute_script("arguments[0].scrollIntoView(false);", item_link)
            await asyncio.sleep(0.1)

            # --- CHANGED: Use JavaScript click for retry --- #
            log_debug_retry_click = (
                f"Attempting JavaScript RETRY click on item link {item_id}."
            )
            logging.debug(log_debug_retry_click)
            driver.execute_script("arguments[0].click();", item_link)
            # --- END CHANGED --- #

            log_info_retry_success = (
                f"Successfully triggered JavaScript click on item "
                f"link {item_id} after interception."
            )
            logging.info(log_info_retry_success)
        except Exception as retry_e:
            # Log the specific retry error
            log_err_retry = (
                f"Failed JavaScript RETRY click for item link {item_id}: {retry_e}"
            )
            logging.error(log_err_retry)
            # Re-raise a specific error indicating the retry failed
            raise ElementClickInterceptedException(
                f"JavaScript click still failed for {item_id} after retry."
            ) from retry_e

    except Exception as e:
        # Catch any other errors during the process
        log_err_unexpected = (
            f"An unexpected error occurred while trying JavaScript "
            f"click on sidebar item link {item_id}: {e}"
        )
        logging.exception(log_err_unexpected)
        raise


async def wait_for_content_update(driver: WebDriver, timeout: int = 20):
    """
    Waits for the page content to update after an action.
    1. Wait for loader (#loaderActive) to become invisible.
    2. Wait for content markdown element (div#documentation markdown) present.
    """
    logging.info(f"Waiting for content update (max {timeout}s)...")
    try:
        # Step 1: Wait for loader overlay to disappear
        logging.debug("Step 1: Waiting for loader overlay to disappear...")
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located(selectors.LOADER_OVERLAY)
        )
        logging.debug("Loader overlay is invisible.")

        # Step 2: Wait for the actual content markdown element to be present
        content_timeout = timeout  # Use full remaining timeout
        content_selector = selectors.CONTENT_PANE_MARKDOWN[1]
        log_step2_wait = (
            f"Step 2: Waiting for content markdown element "
            f"({content_selector}) to be present "
            f"(timeout: {content_timeout}s)..."
        )
        logging.debug(log_step2_wait)
        content_element = WebDriverWait(driver, content_timeout).until(
            EC.presence_of_element_located(selectors.CONTENT_PANE_MARKDOWN)
        )
        log_info_update_complete = (
            "Content update complete: Loader disappeared "
            "and content markdown element is present."
        )
        logging.info(log_info_update_complete)
        return content_element

    except TimeoutException as e:
        # Check if loader *never* disappeared or content *never* appeared
        try:
            loader_is_visible = driver.find_element(
                *selectors.LOADER_OVERLAY
            ).is_displayed()
        except NoSuchElementException:
            loader_is_visible = False

        if loader_is_visible:
            loader_selector = selectors.LOADER_OVERLAY[1]
            log_err_loader_timeout = (
                f"Timeout ({timeout}s) waiting for content update: "
                f"Loader overlay ({loader_selector}) never disappeared."
            )
            logging.error(log_err_loader_timeout)
            raise TimeoutException(
                f"Timeout waiting for loader to disappear: {e}"
            ) from e
        else:
            content_selector = selectors.CONTENT_PANE_MARKDOWN[1]
            log_err_content_timeout = (
                f"Timeout ({timeout}s) waiting for content update: "
                f"Loader disappeared, but content markdown "
                f"({content_selector}) did not appear."
            )
            logging.error(log_err_content_timeout)
            raise TimeoutException(
                f"Timeout waiting for content markdown element: {e}"
            ) from e
    except Exception as e:
        log_err_unexpected = (
            f"An unexpected error occurred during " f"wait_for_content_update: {e}"
        )
        logging.exception(log_err_unexpected)
        raise
