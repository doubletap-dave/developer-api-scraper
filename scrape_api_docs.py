#!/usr/bin/env python3
"""
API Documentation Scraper
Scrapes PowerFlex API documentation by navigating through sidebar items
and capturing page content for each endpoint.
"""

import os
import time
import json
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from datetime import datetime

# Import Wyrm's menu expander
from wyrm.services.navigation.menu_expander import MenuExpander

class APIDocScraper:
    def __init__(self, base_url, output_dir="scraped_content", headless=False):
        self.base_url = base_url
        self.output_dir = output_dir
        self.scraped_items = []
        self.failed_items = []
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Setup Chrome driver
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
        # Initialize menu expander
        self.menu_expander = MenuExpander(self.driver)
        
        # Configuration for menu expansion
        self.config_values = {
            "navigation_timeout": 10,
            "expand_delay": 0.5
        }
        
    def safe_filename(self, text):
        """Convert text to safe filename"""
        safe = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return safe.replace(' ', '_')[:100]  # Limit length
    
    def wait_for_page_load(self, timeout=10):
        """Wait for page to load completely"""
        try:
            # Wait for the main content area to be present
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)  # Additional wait for dynamic content
            return True
        except TimeoutException:
            print("Timeout waiting for page to load")
            return False
    
    def capture_page_content(self, item_id, item_text):
        """Capture the current page content"""
        try:
            # Wait for content to load
            self.wait_for_page_load()
            
            # Get page title and content
            title = self.driver.title
            page_source = self.driver.page_source
            current_url = self.driver.current_url
            
            # Create filename
            filename = f"{item_id}_{self.safe_filename(item_text)}.html"
            filepath = os.path.join(self.output_dir, filename)
            
            # Save content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"<!-- Captured from: {current_url} -->\n")
                f.write(f"<!-- Item ID: {item_id} -->\n")
                f.write(f"<!-- Item Text: {item_text} -->\n")
                f.write(f"<!-- Timestamp: {datetime.now().isoformat()} -->\n")
                f.write(page_source)
            
            item_data = {
                "id": item_id,
                "text": item_text,
                "title": title,
                "url": current_url,
                "filename": filename,
                "timestamp": datetime.now().isoformat()
            }
            
            self.scraped_items.append(item_data)
            print(f"✓ Captured: {item_text} -> {filename}")
            return True
            
        except Exception as e:
            error_data = {
                "id": item_id,
                "text": item_text,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.failed_items.append(error_data)
            print(f"✗ Failed to capture {item_text}: {e}")
            return False
    
    async def click_sidebar_item(self, element, item_id, item_text, item_menu=None):
        """Click on a sidebar item and capture the resulting page"""
        try:
            print(f"Clicking on: {item_text} (ID: {item_id})")
            
            # Create item object for menu expander
            item_obj = {
                "id": item_id,
                "text": item_text,
                "menu": item_menu,
                "parent_menu_text": None,
                "level": 0
            }
            
            # Expand menu path to ensure item is accessible
            try:
                await self.menu_expander.expand_menu_for_item(item_obj, self.config_values)
            except Exception as expand_error:
                print(f"Warning: Menu expansion failed for {item_text}: {expand_error}")
            
            # Wait a moment for expansion to complete
            await asyncio.sleep(0.5)
            
            # Re-find the element after menu expansion (it might have moved)
            try:
                element = self.driver.find_element(By.ID, item_id)
            except NoSuchElementException:
                print(f"Element {item_id} not found after menu expansion")
                return False
            
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            await asyncio.sleep(0.5)
            
            # Try to click the element
            try:
                element.click()
            except ElementClickInterceptedException:
                # If direct click fails, try JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
            
            # Wait for navigation/content change
            await asyncio.sleep(2)
            
            # Capture the page content
            return self.capture_page_content(item_id, item_text)
            
        except Exception as e:
            print(f"Error clicking item {item_text}: {e}")
            return False
    
    def expand_menu_section(self, menu_element):
        """Expand a collapsible menu section"""
        try:
            # Check if menu is already expanded
            aria_expanded = menu_element.get_attribute("aria-expanded")
            if aria_expanded == "true":
                print("Menu already expanded")
                return True
            
            # Look for chevron-right icon (collapsed state)
            chevron = menu_element.find_element(By.CSS_SELECTOR, ".dds__icon--chevron-right")
            if chevron:
                print("Expanding menu...")
                
                # Scroll into view and click
                self.driver.execute_script("arguments[0].scrollIntoView(true);", menu_element)
                time.sleep(0.5)
                
                try:
                    menu_element.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", menu_element)
                
                # Wait for expansion
                time.sleep(1)
                
                # Verify expansion
                aria_expanded = menu_element.get_attribute("aria-expanded")
                return aria_expanded == "true"
            
        except NoSuchElementException:
            # No chevron found, might already be expanded or not expandable
            return True
        except Exception as e:
            print(f"Error expanding menu: {e}")
            return False
    
    def get_menu_subitems(self, menu_element):
        """Get all sub-items from an expanded menu"""
        try:
            # Look for the next sibling ul element that contains sub-items
            parent = menu_element.find_element(By.XPATH, "./parent::app-api-doc-item")
            next_ul = parent.find_element(By.XPATH, "./following-sibling::ul")
            
            # Find all clickable sub-items
            sub_items = next_ul.find_elements(By.CSS_SELECTOR, "li.toc-item-group-items[id^='docs-node-']")
            
            items_data = []
            for item in sub_items:
                item_id = item.get_attribute("id")
                # Get text from the span element
                try:
                    text_span = item.find_element(By.CSS_SELECTOR, "span[id$='-sp']")
                    item_text = text_span.text.strip()
                    if item_text:
                        items_data.append((item, item_id, item_text))
                except NoSuchElementException:
                    continue
            
            return items_data
            
        except NoSuchElementException:
            print("No sub-items found for this menu")
            return []
        except Exception as e:
            print(f"Error getting menu sub-items: {e}")
            return []
    
    async def scrape_all_items(self):
        """Main scraping function with menu expansion handling"""
        try:
            print(f"Loading base URL: {self.base_url}")
            self.driver.get(self.base_url)
            
            if not self.wait_for_page_load():
                print("Failed to load initial page")
                return False
            
            print("Performing comprehensive menu expansion...")
            # Use Wyrm's comprehensive menu expansion to reveal all items
            await self.menu_expander.expand_all_menus_comprehensive(timeout=60)
            
            print("Discovering all available sidebar items...")
            
            # Find all clickable items after full expansion
            all_items = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "li.toc-item-highlight[id^='docs-node-']"
            )
            
            print(f"Found {len(all_items)} total items after menu expansion")
            
            # Process each item
            for i, item in enumerate(all_items, 1):
                try:
                    item_id = item.get_attribute("id")
                    
                    # Get item text
                    try:
                        # Try multiple text extraction methods
                        text_element = None
                        selectors = [
                            "span[id$='-sp']",
                            "div.align-middle",
                            "span",
                            "div"
                        ]
                        
                        for selector in selectors:
                            try:
                                text_element = item.find_element(By.CSS_SELECTOR, selector)
                                item_text = text_element.text.strip()
                                if item_text:
                                    break
                            except NoSuchElementException:
                                continue
                        
                        if not item_text:
                            item_text = item.text.strip()
                            
                    except Exception:
                        item_text = f"Item_{item_id}"
                    
                    if not item_text:
                        continue
                    
                    print(f"\n[{i}/{len(all_items)}] Processing: {item_text} (ID: {item_id})")
                    
                    # Click and capture this item
                    success = await self.click_sidebar_item(item, item_id, item_text)
                    
                    if success:
                        print(f"✓ Successfully processed: {item_text}")
                    else:
                        print(f"✗ Failed to process: {item_text}")
                    
                    # Add a small delay between items
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"Error processing item {i}: {e}")
                    continue
            
            # Save summary
            self.save_summary()
            return True
            
        except Exception as e:
            print(f"Error in scrape_all_items: {e}")
            return False
    
    def save_summary(self):
        """Save a summary of scraped items"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_scraped": len(self.scraped_items),
            "total_failed": len(self.failed_items),
            "scraped_items": self.scraped_items,
            "failed_items": self.failed_items
        }
        
        summary_file = os.path.join(self.output_dir, "scraping_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\nScraping completed!")
        print(f"Successfully scraped: {len(self.scraped_items)} items")
        print(f"Failed: {len(self.failed_items)} items")
        print(f"Summary saved to: {summary_file}")
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()

async def main():
    # Configuration
    BASE_URL = "https://developer.dell.com/apis/4033/versions/4.6.1/docs/PowerFlex%20Gateway"
    OUTPUT_DIR = "scraped_api_docs"
    
    # Create scraper instance
    scraper = APIDocScraper(BASE_URL, OUTPUT_DIR, headless=False)
    
    try:
        # Start scraping
        await scraper.scrape_all_items()
    finally:
        # Always close the browser
        scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
