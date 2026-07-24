"""Reading/writing the Excel output.

Semantics: the Excel file on disk is treated as a "base" snapshot from
the previous run. Each time the scraper runs, the freshly-scraped
results are compared against that base (by URL, which is unique per
circular). Any additions or removals are reported, and the base file
is then overwritten with the latest fetch -- it always reflects the
most recent run, it does not accumulate history.
"""

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from .config import COLUMNS


def load_existing(output_path):
    """Load the previous run's snapshot ("base"). Empty frame if none yet."""
    if Path(output_path).exists():
        try:
            return pd.read_excel(output_path)
        except Exception as e:
            print(f"Warning: couldn't read existing file ({e}); starting fresh.")
    return pd.DataFrame(columns=COLUMNS)


def diff_snapshots(old_df, new_df):
    """Compare the base snapshot against the freshly-scraped rows.

    Returns a dict describing what changed, keyed by URL (each
    circular's URL is treated as its unique identifier).
    """
    old_df = old_df if old_df is not None else pd.DataFrame(columns=COLUMNS)
    old_urls = set(old_df["url"]) if "url" in old_df.columns else set()
    new_urls = set(new_df["url"]) if "url" in new_df.columns else set()

    added_urls = new_urls - old_urls
    removed_urls = old_urls - new_urls

    added_rows = new_df[new_df["url"].isin(added_urls)] if added_urls else new_df.iloc[0:0]
    removed_rows = old_df[old_df["url"].isin(removed_urls)] if removed_urls else old_df.iloc[0:0]

    return {
        "old_count": len(old_df),
        "new_count": len(new_df),
        "added": added_rows,
        "removed": removed_rows,
        "changed": bool(added_urls) or bool(removed_urls) or len(old_df) != len(new_df),
    }


def format_alert(diff):
    """Render the diff as a human-readable alert block for the console."""
    lines = []
    lines.append("=" * 60)
    lines.append("CHANGE DETECTED since last run")
    lines.append("=" * 60)
    lines.append(f"Previous count: {diff['old_count']}   New count: {diff['new_count']}")

    if len(diff["added"]):
        lines.append(f"\n+ {len(diff['added'])} added:")
        for _, row in diff["added"].iterrows():
            lines.append(f"    + {row.get('title', '')}  ({row.get('url', '')})")

    if len(diff["removed"]):
        lines.append(f"\n- {len(diff['removed'])} removed:")
        for _, row in diff["removed"].iterrows():
            lines.append(f"    - {row.get('title', '')}  ({row.get('url', '')})")

    lines.append("=" * 60)
    return "\n".join(lines)


def save_snapshot(output_path, new_rows):
    """Overwrite the base file with the latest fetch (de-duplicated by
    URL within itself, in case the same circular appeared on two
    pages). This becomes the new base for the next run."""
    new_df = pd.DataFrame(new_rows, columns=COLUMNS)
    new_df = new_df.drop_duplicates(subset=["url"], keep="first")
    new_df.to_excel(output_path, index=False)
    return new_df


def changelog_path_for(output_path):
    """The changelog JSON lives next to the Excel file, same base name."""
    return str(Path(output_path).with_suffix("")) + "_changelog.json"


def save_changelog(output_path, diff):
    """Persist the latest diff as JSON, so a dashboard (or anything else)
    can show 'what changed on the last run' without re-scraping."""
    record = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "old_count": diff["old_count"],
        "new_count": diff["new_count"],
        "changed": diff["changed"],
        "added": diff["added"][["title", "url"]].to_dict("records") if len(diff["added"]) else [],
        "removed": diff["removed"][["title", "url"]].to_dict("records") if len(diff["removed"]) else [],
    }
    with open(changelog_path_for(output_path), "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    return record


def load_changelog(output_path):
    """Read back the last saved changelog, or a neutral default if none exists yet."""
    path = changelog_path_for(output_path)
    if Path(path).exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"checked_at": None, "old_count": 0, "new_count": 0, "changed": False, "added": [], "removed": []}
