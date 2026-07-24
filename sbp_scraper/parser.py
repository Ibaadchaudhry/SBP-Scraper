"""Parsing of the search-result HTML: the 'Showing page X of Y' indicator
and the individual circular rows."""

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
