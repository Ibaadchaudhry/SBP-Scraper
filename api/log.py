"""Vercel serverless function: GET /api/log?lines=200

Fetches the live sbp_scraper.log straight from GitHub (raw content) on
every request. Falls back to the bundled local copy only if GitHub
can't be reached.
"""

import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Ibaadchaudhry/SBP-Scraper/main"
REMOTE_URL = f"{GITHUB_RAW_BASE}/sbp_scraper.log"
LOCAL_PATH = os.path.join(os.path.dirname(__file__), "..", "sbp_scraper.log")


def read_log_text():
    try:
        req = urllib.request.Request(REMOTE_URL, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.read().decode("utf-8"), "github"
    except Exception:
        pass

    if os.path.exists(LOCAL_PATH):
        with open(LOCAL_PATH, "r", encoding="utf-8") as f:
            return f.read(), "local-fallback"

    return "", "empty"


def tail(n=200):
    text, source = read_log_text()
    lines = text.splitlines()
    return lines[-n:], source


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            query = parse_qs(urlparse(self.path).query)
            n = int(query.get("lines", ["200"])[0])
            lines, source = tail(n)
            body = json.dumps({"lines": lines}).encode("utf-8")
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
