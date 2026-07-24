#!/usr/bin/env python3
"""
SBP Circulars Scraper (Selenium version) — CLI entry point
=============================================================
Drives a headless Chrome browser to page through the SBP circulars
search results (the site's pagination is client-side JS, so a plain
`requests` client can never reach page 2+).

Logic lives in the sbp_scraper/ package:
    config.py            constants + output column schema
    url_builder.py        builds the page-1 search URL
    browser.py            headless Chrome driver setup
    parser.py             HTML parsing (page indicator + circular rows)
    pagination.py         clicking the ">" next-page link
    scraper.py             scrape_all(): pages through the whole site
    storage.py             Excel load / diff / save + changelog JSON
    emailer.py             (optional) Outlook email alert
    run_log.py             persistent run log (sbp_scraper.log)
    job.py                 run_scrape_job(): one full run, shared by
                            this CLI and the dashboard's "run" button
    dashboard_server.py    local web server for the live dashboard
    dashboard.html          the dashboard page itself

SETUP
-----
    pip install selenium webdriver-manager beautifulsoup4 pandas openpyxl

You do NOT need to separately download a chromedriver - `webdriver-manager`
fetches the correct one automatically the first time you run this
(as long as you have Google Chrome installed).

USAGE
-----
    python scrape.py
    python scrape.py --category "" --department "BPRD"
    python scrape.py --output my_circulars.xlsx
    python scrape.py --show-browser   (to watch it work)
    python scrape.py --alert-email "you@example.com"
"""

import sys
import argparse

from sbp_scraper.job import run_scrape_job


def main():
    parser = argparse.ArgumentParser(
        description="Scrape SBP circulars into an Excel sheet (Selenium version)."
    )
    parser.add_argument("--search-doc", default="", help="Free-text search term")
    parser.add_argument("--department", default="",
                         help="Department filter (used only to narrow the search "
                              "on the site; not stored in the output)")
    parser.add_argument("--category", default="Microfinance", help="Category filter")
    parser.add_argument("--circular-type", default="", help="Circular type filter")
    parser.add_argument("--start-date", default="", help="Start date filter")
    parser.add_argument("--end-date", default="", help="End date filter")
    parser.add_argument("--output", default="sbp_circulars.csv", help="CSV file to read/write")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds to wait after each page click")
    parser.add_argument("--show-browser", action="store_true",
                         help="Show the Chrome window instead of running headless (useful for debugging)")
    parser.add_argument("--alert-email", default="",
                         help="Email address to notify when a change is detected. Sent via "
                              "SMTP if SBP_SMTP_HOST/USER/PASS env vars are set (works "
                              "anywhere, including GitHub Actions); otherwise falls back to "
                              "desktop Outlook (Windows only, requires pywin32). Leave blank "
                              "to disable email alerts.")
    args = parser.parse_args()

    result = run_scrape_job(
        output=args.output,
        search_doc=args.search_doc,
        department=args.department,
        category=args.category,
        circular_type=args.circular_type,
        start_date=args.start_date,
        end_date=args.end_date,
        headless=not args.show_browser,
        delay=args.delay,
        alert_email=args.alert_email,
    )

    if not result.get("ok"):
        print(f"\nRun failed: {result.get('error')}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
