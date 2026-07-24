"""Builds the (page 1) search-result URL the same way the site's own
filter form does. Pagination from here on is done by clicking, not by
guessing further URLs."""

from urllib.parse import quote

from .config import BASE


def build_search_url(search_doc="", department="", category="", circular_type="",
                      start_date="", end_date=""):
    path = (
        f"circulars/search-result/search_doc={quote(search_doc)}"
        f"&department={quote(department)}"
        f"&category={quote(category)}"
        f"&circular-type={quote(circular_type)}"
        f"&circular_start_date={quote(start_date)}"
        f"&circular_end_date={quote(end_date)}"
    )
    return f"{BASE}/{path}"
