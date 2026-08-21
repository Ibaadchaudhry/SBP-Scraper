"""Parsing of the search-result HTML: the 'Showing page X of Y' indicator,
the pagination links, and the individual circular rows."""

import re

from bs4 import BeautifulSoup

from .config import BASE


def get_page_indicator(html):
    """Extract (current_page, total_pages) from 'Showing page X of Y' text."""
    soup = BeautifulSoup(html, "html.parser")
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    m = re.search(r"Showing page\s+(\d+)\s+of\s+(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 1, 1


BLOCK_MARKERS = (
    "Attention Required! | Cloudflare",
    "Sorry, you have been blocked",
    "cf-error-details",
)


def looks_blocked(html):
    """True if we got Cloudflare's block page instead of the site.

    Worth distinguishing: a block page parses as zero circulars and no
    page indicator, which is indistinguishable from "the site changed"
    unless we look for it explicitly.
    """
    head = html[:8000]
    return any(marker in head for marker in BLOCK_MARKERS)


def _absolute(href):
    return href if href.startswith("http") else BASE + "/" + href.lstrip("/")


def _pagination_links(soup):
    """Yield (label, absolute_href) for every link inside a pagination bar.

    The site renders the same bar twice (above and below the results),
    so labels repeat; callers should take the first match.
    """
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        in_pagination = any(
            "pagination" in cls
            for parent in a.parents
            for cls in (parent.get("class") or [])
        )
        if not in_pagination:
            continue
        yield a.get_text(strip=True), _absolute(href)


def find_next_page_href(html, current_page=None):
    """Return the absolute URL of the next results page, or None.

    Prefers the '>' control; falls back to the numbered link for
    `current_page + 1` in case the site ever drops the arrow. Returns
    None on the last page, where the site renders no forward link at all.
    """
    soup = BeautifulSoup(html, "html.parser")
    wanted_number = str(current_page + 1) if current_page else None
    numbered_href = None

    for label, href in _pagination_links(soup):
        if label == ">":
            return href
        if wanted_number and label == wanted_number and numbered_href is None:
            numbered_href = href

    return numbered_href


def parse_listing_page(html):
    """Parse one circulars search-result page and return a list of dict rows.

    Note: the site's metadata line looks like
        "<department stuff> | <category> | <circular type>"
    We still split on '|' to reach category/circular_type, but we no
    longer keep the department segment itself.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    circular_links = soup.find_all(
        "a", href=re.compile(r"/circulars/[a-z0-9\-]+$", re.IGNORECASE)
    )

    for a in circular_links:
        title = a.get_text(strip=True)
        href = a.get("href")
        if not title or not href:
            continue
        url = href if href.startswith("http") else BASE + href

        heading = a.find_parent(["h1", "h2", "h3", "h4", "h5"]) or a.parent

        circ_no, date_txt, meta_txt = "", "", ""
        node = heading
        collected_text = []
        steps = 0
        while node is not None and steps < 6:
            node = node.find_next_sibling()
            steps += 1
            if node is None:
                break
            txt = node.get_text(" ", strip=True)
            if not txt:
                continue
            collected_text.append(txt)
            if "|" in txt:
                meta_txt = txt
                break

        if collected_text:
            circ_no = collected_text[0]

        date_match = None
        for t in collected_text:
            m = re.search(
                r"(January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+\d{1,2}\s+\d{4}",
                t,
            )
            if m:
                date_match = m.group(0)
                break
        if date_match:
            date_txt = date_match

        category, circular_type = "", ""
        if meta_txt:
            parts = [p.strip() for p in meta_txt.split("|")]
            if len(parts) >= 2:
                category = parts[1].strip()
            if len(parts) >= 3:
                circular_type = parts[2].strip()

        rows.append(
            {
                "title": title,
                "circular_no": circ_no,
                "date": date_txt,
                "category": category,
                "circular_type": circular_type,
                "url": url,
            }
        )

    return rows
