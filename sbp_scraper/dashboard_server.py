"""A local, read-only web server for the circulars dashboard.

Re-reads sbp_circulars.xlsx fresh on every request and hands it to the
dashboard page as JSON (browsers can't read local files by themselves,
so this small server is what makes the dashboard "live"). It also
serves the persistent run log for the "View log" panel.

Note: this server does NOT trigger scrapes. Scraping now happens on a
schedule via GitHub Actions (see .github/workflows/daily-scrape.yml),
which commits the updated sbp_circulars.xlsx, changelog, and log back
to the repo. Run `git pull` to get the latest, then hit "Reload data"
on the dashboard.

Uses only Python's built-in http.server, so no extra packages are
needed beyond what the scraper already requires (pandas, openpyxl).

USAGE
-----
    python -m sbp_scraper.dashboard_server
    python -m sbp_scraper.dashboard_server --file my_circulars.xlsx --port 8000

Then open http://localhost:8000 in a browser.
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pandas as pd

from .config import COLUMNS
from .run_log import tail as log_tail
from .storage import changelog_path_for, load_changelog

DASHBOARD_HTML_PATH = Path(__file__).parent / "dashboard.html"


def _read_circulars_json(xlsx_path):
    """Re-read the CSV file from disk right now and return it as a
    list of plain dicts, ready to serialize as JSON. This is what
    makes the dashboard 'live' -- every request re-reads the file."""
    if not Path(xlsx_path).exists():
        return []
    df = pd.read_csv(xlsx_path)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS].fillna("")
    return df.to_dict("records")


def make_handler(xlsx_path):
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload, status=200):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/api/circulars"):
                try:
                    self._send_json(_read_circulars_json(xlsx_path))
                except Exception as e:
                    self._send_json({"error": str(e)}, status=500)
                return

            if self.path.startswith("/api/changes"):
                try:
                    self._send_json(load_changelog(xlsx_path))
                except Exception as e:
                    self._send_json({"error": str(e)}, status=500)
                return

            if self.path.startswith("/api/log"):
                try:
                    n = 200
                    if "lines=" in self.path:
                        n = int(self.path.split("lines=")[1].split("&")[0])
                    self._send_json({"lines": log_tail(n)})
                except Exception as e:
                    self._send_json({"error": str(e)}, status=500)
                return

            if self.path in ("/", "/index.html"):
                try:
                    html = DASHBOARD_HTML_PATH.read_text(encoding="utf-8")
                    body = html.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(str(e).encode("utf-8"))
                return

            self.send_response(404)
            self.end_headers()

        def log_message(self, fmt, *args):
            # keep the console quiet; comment this out for verbose request logs
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Serve the SBP circulars dashboard.")
    parser.add_argument("--file", default="sbp_circulars.csv",
                         help="Path to the CSV file (kept up to date by GitHub Actions)")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on")
    args = parser.parse_args()

    handler = make_handler(args.file)
    server = HTTPServer(("localhost", args.port), handler)
    print(f"Dashboard running at http://localhost:{args.port}")
    print(f"Reading live data from: {Path(args.file).resolve()}")
    print(f"Reading changelog from: {changelog_path_for(args.file)}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
