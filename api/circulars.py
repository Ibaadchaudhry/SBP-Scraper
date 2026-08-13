"""Vercel serverless function: GET /api/circulars

Fetches the live sbp_circulars.csv straight from GitHub (raw content)
on every request -- no Vercel rebuild needed when GitHub Actions
commits a fresh scrape. Falls back to the bundled local copy only if
GitHub can't be reached.
"""

import csv
import io
import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler

COLUMNS = ["title", "circular_no", "date", "category", "circular_type", "url"]

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Ibaadchaudhry/SBP-Scraper/main"
REMOTE_URL = f"{GITHUB_RAW_BASE}/sbp_circulars.csv"
LOCAL_PATH = os.path.join(os.path.dirname(__file__), "..", "sbp_circulars.csv")


def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    return [{col: (row.get(col) or "") for col in COLUMNS} for row in reader]


def read_circulars():
    try:
        req = urllib.request.Request(REMOTE_URL, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            text = resp.read().decode("utf-8")
        return parse_csv(text), "github"
    except Exception:
        pass

    if os.path.exists(LOCAL_PATH):
        with open(LOCAL_PATH, "r", encoding="utf-8", newline="") as f:
            return parse_csv(f.read()), "local-fallback"

    return [], "empty"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            payload, source = read_circulars()
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Data-Source", source)
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            body = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
