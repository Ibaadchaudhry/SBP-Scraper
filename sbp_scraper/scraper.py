"""Fetches every page of results and collects the circular rows.

Each page gets its own short-lived browser. That looks wasteful, but the
site sits behind a CDN that serves its block page ("Sorry, you have been
blocked") to every request after the first one in a browser session --
regardless of the URL, the delay between requests, or whether cookies are
cleared in between. A fresh browser per page is the only thing that gets
past it, and there are only a handful of pages per search.
"""

import time

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from .browser import browser_session
from .pagination import next_page_url
from .parser import get_page_indicator, looks_blocked, parse_listing_page
from .run_log import get_logger
from .url_builder import build_search_url

# Stops a malformed page indicator from turning the loop into a crawl of
# the whole site. The normal exit is `page >= total_pages`.
MAX_PAGES = 200

# How many times to re-fetch a page that came back blocked or empty.
MAX_ATTEMPTS = 3

# Seconds to wait before re-fetching a page that came back blocked.
RETRY_BACKOFF = 5.0


def _load(driver, url, settle):
    """Load `url` and hand back whatever HTML we ended up with.

    Waits for the client-side render to produce the "Showing page X of Y"
    line, but a timeout is not fatal: the caller can tell a block page or
    an unexpected page number apart from a good one, and says so.
    """
    driver.get(url)
    try:
        WebDriverWait(driver, 20).until(
            lambda d: "Showing page" in d.page_source or looks_blocked(d.page_source)
        )
    except TimeoutException:
        pass
    time.sleep(settle)
    return driver.page_source


def fetch_page(url, expected_page, headless=True, settle=1.5):
    """Fetch one results page in its own browser and return its HTML.

    Retries on a CDN block page or on HTML whose page indicator doesn't
    match `expected_page`. Returns None if every attempt failed.
    """
    logger = get_logger()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with browser_session(headless=headless) as driver:
                html = _load(driver, url, settle)
        except WebDriverException as e:
            logger.warning(f"  -> browser error on attempt {attempt}: "
                           f"{type(e).__name__}: {str(e).splitlines()[0]}")
            html = None

        if html is not None:
            if looks_blocked(html):
                logger.warning(f"  -> attempt {attempt}: blocked by the site's CDN.")
            else:
                current_page, _ = get_page_indicator(html)
                if current_page == expected_page:
                    return html
                logger.warning(f"  -> attempt {attempt}: asked for page "
                               f"{expected_page} but the page indicator reads "
                               f"{current_page}.")

        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_BACKOFF * attempt)

    return None


def scrape_all(search_doc="", department="", category="Microfinance",
                circular_type="", start_date="", end_date="",
                headless=True, delay=1.0):
    logger = get_logger()
    url = build_search_url(search_doc, department, category, circular_type,
                            start_date, end_date)

    all_rows = []
    seen_urls = set()

    def collect(rows):
        """Keep the first occurrence of each circular URL."""
        new = [r for r in rows if r["url"] not in seen_urls]
        seen_urls.update(r["url"] for r in new)
        all_rows.extend(new)
        return len(new)

    page = 1
    page_size = 0
    visited = set()

    while True:
        visited.add(url)
        logger.info(f"Loading page {page}: {url}")

        html = fetch_page(url, page, headless=headless)
        if html is None:
            logger.warning(f"  -> giving up on page {page} after {MAX_ATTEMPTS} "
                           f"attempt(s); results may be incomplete.")
            break

        page, total_pages = get_page_indicator(html)
        rows = parse_listing_page(html)
        added = collect(rows)
        logger.info(f"Page {page} of {total_pages}: found {len(rows)} circular(s)"
                    + ("" if added == len(rows) else f" ({added} new)"))

        if page_size == 0:
            page_size = len(rows)
        if page >= total_pages:
            break
        if added == 0:
            logger.warning("  -> page repeated rows we already had; stopping.")
            break

        next_url = next_page_url(html, url, page, total_pages, page_size)
        if not next_url:
            logger.warning("  -> no next-page link found; stopping.")
            break
        if next_url in visited:
            logger.warning("  -> next-page link points at a page we already "
                           "fetched; stopping.")
            break

        if page + 1 > MAX_PAGES:
            logger.warning(f"  -> stopped at the {MAX_PAGES}-page safety limit.")
            break

        url = next_url
        page += 1
        time.sleep(delay)

    logger.info(f"Collected {len(all_rows)} circular(s) across {len(visited)} page(s).")
    return all_rows
