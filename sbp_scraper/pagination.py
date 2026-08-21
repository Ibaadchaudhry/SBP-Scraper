"""Working out where the next page of search results lives.

The results list is rendered client-side, but its pagination controls are
plain links carrying a `/P<offset>` suffix on the search URL, e.g.

    .../circular_end_date=        <- page 1
    .../circular_end_date=/P30    <- page 2 (offset 30 = 30 rows per page)

so we can fetch any page directly by URL. Clicking the on-page '>' control
is not an option: it sits under a sticky overlay (the click is intercepted)
and, more importantly, the site's CDN blocks every request after the first
one in a browser session, so the second page has to be fetched by a
freshly-started browser anyway. See scraper.fetch_page.
"""

import re

from .parser import find_next_page_href

PAGE_SUFFIX_RE = re.compile(r"/P\d+/?$")


def strip_page_suffix(url):
    """Drop a trailing '/P<offset>' so we're back to the page-1 URL."""
    return PAGE_SUFFIX_RE.sub("", url)


def build_page_url(url, page, page_size):
    """Construct the URL for `page` (1-based) of the results at `url`."""
    base = strip_page_suffix(url)
    offset = (page - 1) * page_size
    return base if offset <= 0 else f"{base}/P{offset}"


def next_page_url(html, current_url, current_page, total_pages=0, page_size=0):
    """Work out where the next page lives, or None if there isn't one.

    Prefers the link the site itself renders. If that's missing but the
    page indicator says there are more pages and we know how many rows
    fit on a page, fall back to computing the offset ourselves.
    """
    if total_pages and current_page >= total_pages:
        return None

    href = find_next_page_href(html, current_page)
    if not href and total_pages and page_size > 0:
        href = build_page_url(current_url, current_page + 1, page_size)
    if not href or href == current_url:
        return None
    return href
