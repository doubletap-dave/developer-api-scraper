#!/usr/bin/env python3
"""
Test script to verify the scraper can find and interact with elements
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

def test_element_detection():
    """Test if we can find the specific elements mentioned"""
    
    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("Loading page...")
        driver.get("https://developer.dell.com/apis/4033/versions/4.6.1/docs/PowerFlex%20Gateway")
        
        # Wait for page to load
        time.sleep(5)
        
        print("\n=== Testing Element Detection ===")
        
        # Test 1: Look for the Volume Management item (docs-node-105189)
        print("\n1. Looking for Volume Management item (docs-node-105189):")
        try:
            volume_mgmt = driver.find_element(By.ID, "docs-node-105189")
            text_span = volume_mgmt.find_element(By.ID, "docs-node-105189-sp")
            print(f"   ✓ Found: {text_span.text}")
        except NoSuchElementException:
            print("   ✗ Not found")
        
        # Test 2: Look for Device menu section
        print("\n2. Looking for Device menu section:")
        try:
            device_menus = driver.find_elements(By.XPATH, "//li[contains(@class, 'toc-item-highlight') and contains(text(), 'Device')]")
            print(f"   ✓ Found {len(device_menus)} Device menu(s)")
            for i, menu in enumerate(device_menus):
                aria_expanded = menu.get_attribute("aria-expanded")
                print(f"     Menu {i+1}: aria-expanded = {aria_expanded}")
        except NoSuchElementException:
            print("   ✗ Device menu not found")
        
        # Test 3: Look for all items with docs-node IDs
        print("\n3. Looking for all items with docs-node IDs:")
        all_items = driver.find_elements(By.CSS_SELECTOR, "[id^='docs-node-']")
        print(f"   ✓ Found {len(all_items)} items with docs-node IDs")
        
        # Test 4: Look for individual clickable items (not in sub-menus)
        print("\n4. Looking for individual clickable items:")
        individual_items = driver.find_elements(
            By.CSS_SELECTOR, 
            "li.toc-item-highlight.clickable[id^='docs-node-']:not(.toc-item-group-items)"
        )
        print(f"   ✓ Found {len(individual_items)} individual items")
        
        # Show first few individual items
        for i, item in enumerate(individual_items[:5]):
            item_id = item.get_attribute("id")
            try:
                text_span = item.find_element(By.CSS_SELECTOR, "span[id$='-sp']")
                item_text = text_span.text.strip()
                print(f"     {i+1}. {item_id}: {item_text}")
            except NoSuchElementException:
                print(f"     {i+1}. {item_id}: [no text found]")
        
        # Test 5: Look for expandable menu sections
        print("\n5. Looking for expandable menu sections:")
        menu_sections = driver.find_elements(
            By.CSS_SELECTOR,
            "li.toc-item-highlight[aria-expanded]"
        )
        print(f"   ✓ Found {len(menu_sections)} expandable menu sections")
        
        # Show menu sections
        for i, menu in enumerate(menu_sections[:5]):
            aria_expanded = menu.get_attribute("aria-expanded")
            menu_text = menu.text.strip().split('\n')[0]  # First line only
            print(f"     {i+1}. {menu_text} (expanded: {aria_expanded})")
        
        # Test 6: Look for sub-items in menus
        print("\n6. Looking for sub-items in menus:")
        sub_items = driver.find_elements(By.CSS_SELECTOR, "li.toc-item-group-items[id^='docs-node-']")
        print(f"   ✓ Found {len(sub_items)} sub-items")
        
        # Show first few sub-items
        for i, item in enumerate(sub_items[:5]):
            item_id = item.get_attribute("id")
            try:
                text_span = item.find_element(By.CSS_SELECTOR, "span[id$='-sp']")
                item_text = text_span.text.strip()
                
                # Check for HTTP method badge
                try:
                    method_badge = item.find_element(By.CSS_SELECTOR, ".http-method-get, .http-method-post, .http-method-put, .http-method-delete")
                    method = method_badge.text.strip()
                    print(f"     {i+1}. {item_id}: [{method}] {item_text}")
                except NoSuchElementException:
                    print(f"     {i+1}. {item_id}: {item_text}")
                    
            except NoSuchElementException:
                print(f"     {i+1}. {item_id}: [no text found]")
        
        print("\n=== Test completed successfully! ===")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_element_detection()
