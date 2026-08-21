"""Headless-Chrome driver setup."""

from contextlib import contextmanager
from functools import lru_cache

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


@lru_cache(maxsize=1)
def _chromedriver_path():
    """Resolve the chromedriver binary once per process.

    We start a new browser for every results page, and webdriver-manager
    hits the network to check for a newer driver on each call.
    """
    return ChromeDriverManager().install()


def make_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1400,1000")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    service = Service(_chromedriver_path())
    return webdriver.Chrome(service=service, options=options)


@contextmanager
def browser_session(headless=True):
    """A driver that is always quit, even if the caller raises."""
    driver = make_driver(headless=headless)
    try:
        yield driver
    finally:
        driver.quit()
