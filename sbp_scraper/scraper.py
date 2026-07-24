"""Drives the browser through every page of results and collects rows."""

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .browser import make_driver
from .pagination import click_next_page
from .parser import get_page_indicator, parse_listing_page
from .url_builder import build_search_url


def scrape_all(search_doc="", department="", category="Microfinance",
                circular_type="", start_date="", end_date="",
                headless=True, delay=1.0):
    url = build_search_url(search_doc, department, category, circular_type,
                            start_date, end_date)

    all_rows = []
    driver = make_driver(headless=headless)
    try:
        print(f"Loading: {url}")
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, ""))
        )
        time.sleep(1.5)  # let any client-side rendering settle

        html = driver.page_source
        current_page, total_pages = get_page_indicator(html)
        print(f"Page {current_page} of {total_pages}")

        rows = parse_listing_page(html)
        print(f"  -> found {len(rows)} circular(s)")
        all_rows.extend(rows)

        while current_page < total_pages:
            advanced = click_next_page(driver, current_page)
            if not advanced:
                print("  -> couldn't advance to the next page; stopping.")
                break
            time.sleep(delay)
            html = driver.page_source
            current_page, total_pages = get_page_indicator(html)
            print(f"Page {current_page} of {total_pages}")
            rows = parse_listing_page(html)
            print(f"  -> found {len(rows)} circular(s)")
            all_rows.extend(rows)
    finally:
        driver.quit()

    return all_rows
