import logging
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService

# Remove webdriver-manager import for Chrome as we're specifying the path manually
# from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import (
    WebDriver as RemoteWebDriver,  # Alias for clarity
)
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager


def initialize_driver(
    browser: str = "chrome", headless: bool = True
) -> RemoteWebDriver:
    """Initialize the Selenium WebDriver."""
    log_msg = f"Initializing {browser} WebDriver... Headless: {headless}"
    logging.info(log_msg)
    browser = browser.lower()

    driver: RemoteWebDriver  # Declare type hint
    options: ChromeOptions | FirefoxOptions | EdgeOptions  # Union type for options
    service: ChromeService | FirefoxService | EdgeService  # Union type for service

    try:
        if browser == "chrome":
            options = ChromeOptions()
            chrome_binary_path = "C:\\Users\\dave\\Downloads\\chrome-win64\\chrome.exe"
            options.binary_location = chrome_binary_path
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("log-level=3")

            driver_dir = os.path.abspath("chromedriver")
            driver_path = os.path.join(driver_dir, "chromedriver.exe")
            logging.info(f"Using manually specified ChromeDriver path: {driver_path}")
            if not os.path.exists(driver_path):
                log_err = f"ChromeDriver not found at specified path: {driver_path}"
                logging.error(log_err)
                raise FileNotFoundError(f"ChromeDriver not found at {driver_path}")

            chromedriver_log_path = os.path.abspath("logs/chromedriver.log")
            log_redir = (
                f"Redirecting ChromeDriver service log to: {chromedriver_log_path}"
            )
            logging.debug(log_redir)

            # Explicitly cast service type
            service = ChromeService(executable_path=driver_path)
            # service argument is valid for Chrome
            driver = webdriver.Chrome(service=service, options=options)  # type: ignore[call-arg]
        elif browser == "firefox":
            options = FirefoxOptions()
            if headless:
                options.add_argument("-headless")
            options.add_argument("--window-size=1920,1080")
            gecko_path = GeckoDriverManager().install()
            # Explicitly cast service type
            service = FirefoxService(gecko_path)
            # service argument is valid for Firefox
            driver = webdriver.Firefox(service=service, options=options)  # type: ignore[call-arg]
        elif browser == "edge":
            edge_options = EdgeOptions()
            edge_options.use_chromium = True  # type: ignore[attr-defined]
            if headless:
                edge_options.add_argument("headless")  # type: ignore[attr-defined]
                edge_options.add_argument("disable-gpu")  # type: ignore[attr-defined]

            edgedriver_log_path = os.path.abspath("logs/msedgedriver.log")
            log_redir_edge = f"Redirecting EdgeDriver log to: {edgedriver_log_path}"
            logging.debug(log_redir_edge)

            edge_driver_path = EdgeChromiumDriverManager().install()
            # Explicitly cast service type
            service = EdgeService(edge_driver_path)
            # Pass the specifically typed options
            driver = webdriver.Edge(service=service, options=edge_options)  # type: ignore[call-arg]

            logging.debug("Setting Edge window size to 1920x1080.")
            driver.set_window_size(1920, 1080)

        else:
            raise ValueError(f"Unsupported browser: {browser}")

        log_success = f"{browser.capitalize()} WebDriver initialized successfully."
        logging.info(log_success)
        return driver  # Type is WebDriver which covers Chrome, Firefox, Edge

    except Exception as e:
        logging.exception(f"Failed to initialize {browser} WebDriver: {e}")
        raise
