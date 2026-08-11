"""The actual 'do one full scrape run' job -- shared by the command
line (scrape.py) and the dashboard's 'Run scraper now' button
(dashboard_server.py), so there's exactly one place this logic lives.

Every run is written to the persistent log (run_log.py) as well as to
the console, and the return value is a small JSON-friendly summary the
dashboard can display without re-reading the CSV file itself.
"""

import pandas as pd

from .config import COLUMNS
from .emailer import send_alert_email
from .run_log import get_logger
from .scraper import scrape_all
from .storage import diff_snapshots, format_alert, load_existing, save_changelog, save_snapshot


def run_scrape_job(output="sbp_circulars.csv", search_doc="", department="",
                    category="Microfinance", circular_type="", start_date="",
                    end_date="", headless=True, delay=1.0, alert_email=""):
    """Run one full scrape: load the base file, scrape the site, diff,
    optionally email an alert, save the changelog + new snapshot.

    Returns a dict summary. On failure, returns {"error": "..."} rather
    than raising, so callers running this in a background thread (the
    dashboard) can surface the error without crashing the server.
    """
    logger = get_logger()
    logger.info("=" * 60)
    logger.info(f"Run started (output={output}, category={category!r}, department={department!r})")

    try:
        base_df = load_existing(output)
        logger.info(f"Base file has {len(base_df)} row(s) from the last run")

        rows = scrape_all(
            search_doc=search_doc,
            department=department,
            category=category,
            circular_type=circular_type,
            start_date=start_date,
            end_date=end_date,
            headless=headless,
            delay=delay,
        )
        logger.info(f"Scraped {len(rows)} circular row(s) from the site this run")

        new_df = pd.DataFrame(rows, columns=COLUMNS).drop_duplicates(subset=["url"], keep="first")
        diff = diff_snapshots(base_df, new_df)

        email_sent = False
        if diff["changed"]:
            alert_text = format_alert(diff)
            logger.info(alert_text)

            if alert_email:
                logger.info(f"Sending email alert to {alert_email} ...")
                email_sent = send_alert_email(
                    to_address=alert_email,
                    subject=f"SBP Circulars: change detected ({diff['old_count']} -> {diff['new_count']})",
                    body="The SBP circulars scraper detected a change since the last run.\n\n" + alert_text,
                )
                logger.info("  -> email sent." if email_sent else "  -> email not sent (see warning above).")
        else:
            logger.info("No change: counts and URLs match the previous run.")

        save_changelog(output, diff)
        save_snapshot(output, rows)
        logger.info(f"Base file updated to this run's {len(new_df)} row(s). Run finished OK.")

        return {
            "ok": True,
            "scraped": len(rows),
            "old_count": diff["old_count"],
            "new_count": diff["new_count"],
            "changed": diff["changed"],
            "added": diff["added"][["title", "url"]].to_dict("records") if len(diff["added"]) else [],
            "removed": diff["removed"][["title", "url"]].to_dict("records") if len(diff["removed"]) else [],
            "email_sent": email_sent,
        }

    except Exception as e:
        logger.exception(f"Run FAILED: {e}")
        return {"ok": False, "error": str(e)}
