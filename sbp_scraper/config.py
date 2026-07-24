"""Shared constants for the SBP circulars scraper."""

BASE = "https://www.sbp.org.pk"

# department / department_code / department_id dropped: not needed downstream
COLUMNS = [
    "title",
    "circular_no",
    "date",
    "category",
    "circular_type",
    "url",
]
