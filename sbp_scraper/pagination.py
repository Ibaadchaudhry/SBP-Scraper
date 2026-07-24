"""Clicking through the site's client-side-rendered pagination."""

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from .parser import get_page_indicator


def click_next_page(driver, current_page, wait_seconds=15):
    """Click the '>' (next page) link and wait for the page indicator to
    actually advance before returning. Returns True if it advanced,
    False if there was no next-page link to click."""
    try:
        next_link = driver.find_element(By.LINK_TEXT, ">")
    except NoSuchElementException:
        return False

    try:
        next_link.click()
    except StaleElementReferenceException:
        return False

    try:
        WebDriverWait(driver, wait_seconds).until(
            lambda d: get_page_indicator(d.page_source)[0] > current_page
        )
    except TimeoutException:
        print("  -> warning: page indicator didn't advance after clicking; "
              "content may not have changed.")
        return False

    return True
