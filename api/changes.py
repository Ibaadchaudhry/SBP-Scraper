"""Vercel serverless function: GET /api/changes

Fetches the live changelog JSON straight from GitHub (raw content) on
every request. Falls back to the bundled local copy only if GitHub
can't be reached.
"""

import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/salmanadnan2006-hue/SBP-Scraper/main"
REMOTE_URL = f"{GITHUB_RAW_BASE}/sbp_circulars_changelog.json"
LOCAL_PATH = os.path.join(os.path.dirname(__file__), "..", "sbp_circulars_changelog.json")

DEFAULT = {"checked_at": None, "old_count": 0, "new_count": 0, "changed": False, "added": [], "removed": []}


def read_changelog():
    try:
        req = urllib.request.Request(REMOTE_URL, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8")), "github"
    except Exception:
        pass

    if os.path.exists(LOCAL_PATH):
        try:
            with open(LOCAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f), "local-fallback"
        except Exception:
            pass

    return DEFAULT, "empty"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            payload, source = read_changelog()
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
