"""Reading/writing the CSV output.

Semantics: the CSV file on disk is treated as a "base" snapshot from
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
            return pd.read_csv(output_path)
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


def _escape_html(value):
    """Minimal HTML-escaping for values dropped into the template below."""
    return (
        str(value if value is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _html_card(row, border_color):
    title = _escape_html(row.get("title", ""))
    url = _escape_html(row.get("url", ""))
    meta_bits = [
        _escape_html(row.get("circular_no", "")),
        _escape_html(row.get("date", "")),
        _escape_html(row.get("circular_type", "")),
    ]
    meta = " &nbsp;&middot;&nbsp; ".join(b for b in meta_bits if b)
    link_html = (
        f'<a href="{url}" style="color:#2563eb;text-decoration:none;font-weight:600;font-size:14px;">View circular &rarr;</a>'
        if url
        else ""
    )
    return f"""
    <tr>
      <td style="padding:16px 20px;border-left:3px solid {border_color};background:#ffffff;">
        <div style="font-size:15px;font-weight:700;color:#111827;margin-bottom:4px;">{title}</div>
        <div style="font-size:13px;color:#6b7280;margin-bottom:10px;">{meta}</div>
        {link_html}
      </td>
    </tr>
    <tr><td style="height:1px;background:#e5e7eb;line-height:1px;font-size:1px;">&nbsp;</td></tr>
    """


def format_alert_html(diff):
    """Render the diff as an HTML alert email matching the 'SBP Circulars
    Watch' card design (dark header, count summary, green 'added' /
    red 'removed' sections)."""
    old_count = diff["old_count"]
    new_count = diff["new_count"]
    delta = new_count - old_count
    delta_str = f"+{delta}" if delta > 0 else str(delta)
    delta_color = "#16a34a" if delta > 0 else ("#dc2626" if delta < 0 else "#6b7280")

    added_rows = diff["added"]
    removed_rows = diff["removed"]

    sections = ""

    if len(added_rows):
        cards = "".join(_html_card(row, "#16a34a") for _, row in added_rows.iterrows())
        sections += f"""
        <tr><td style="padding:24px 20px 8px 20px;">
          <span style="font-size:14px;font-weight:700;color:#111827;letter-spacing:0.02em;">NEW CIRCULARS</span>
          <span style="background:#dcfce7;color:#166534;font-size:12px;font-weight:700;padding:3px 8px;border-radius:10px;margin-left:8px;">{len(added_rows)} added</span>
        </td></tr>
        <tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{cards}</table></td></tr>
        """

    if len(removed_rows):
        cards = "".join(_html_card(row, "#dc2626") for _, row in removed_rows.iterrows())
        sections += f"""
        <tr><td style="padding:24px 20px 8px 20px;">
          <span style="font-size:14px;font-weight:700;color:#111827;letter-spacing:0.02em;">REMOVED</span>
          <span style="background:#fee2e2;color:#991b1b;font-size:12px;font-weight:700;padding:3px 8px;border-radius:10px;margin-left:8px;">{len(removed_rows)} removed</span>
        </td></tr>
        <tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{cards}</table></td></tr>
        """

    return f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:24px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:10px;overflow:hidden;border:1px solid #e5e7eb;">
          <tr>
            <td style="background:#0f2a4a;padding:28px 24px;">
              <div style="color:#ffffff;font-size:20px;font-weight:700;">SBP Circulars Watch</div>
              <div style="color:#c7d2e0;font-size:13px;margin-top:4px;">Change detected on the State Bank of Pakistan circulars page</div>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 20px 4px 20px;font-size:14px;color:#111827;">
              Previous count: <strong>{old_count}</strong> &rarr; New count: <strong>{new_count}</strong>
              &nbsp;<span style="color:{delta_color};font-weight:700;">({delta_str})</span>
            </td>
          </tr>
          {sections}
          <tr><td style="height:12px;"></td></tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def save_snapshot(output_path, new_rows):
    """Overwrite the base file with the latest fetch (de-duplicated by
    URL within itself, in case the same circular appeared on two
    pages). This becomes the new base for the next run."""
    new_df = pd.DataFrame(new_rows, columns=COLUMNS)
    new_df = new_df.drop_duplicates(subset=["url"], keep="first")
    new_df.to_csv(output_path, index=False)
    return new_df


def changelog_path_for(output_path):
    """The changelog JSON lives next to the CSV file, same base name."""
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
