"""A persistent, append-only log of every scrape run -- separate from
the changelog JSON (which only ever holds the *latest* diff). This is
the actual audit trail: every run, every page fetched, every error,
with timestamps, kept forever (or until you delete the file).

Uses Python's standard `logging` module writing to a plain text file
next to the script, plus still printing to the console as before.
"""

import logging

LOG_FILENAME = "sbp_scraper.log"

_logger = None


def get_logger():
    """Returns a singleton logger that writes to sbp_scraper.log AND
    prints to the console, so behavior on the command line is
    unchanged but everything is now also durably recorded."""
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("sbp_scraper")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_FILENAME, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(console_handler)

    _logger = logger
    return logger


def tail(n=200):
    """Return the last n lines of the log file as a list of strings
    (oldest first). Used by the dashboard's 'Run log' panel."""
    try:
        with open(LOG_FILENAME, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [line.rstrip("\n") for line in lines[-n:]]
    except FileNotFoundError:
        return []
