"""Sends the change-alert email via plain SMTP -- works anywhere
(Windows, Linux, GitHub Actions), unlike the Outlook path which needs
a desktop Outlook install. This is what makes email alerts work from
the GitHub Actions scheduled runs.

Credentials are read from environment variables, never hardcoded or
committed to the repo:

    SBP_SMTP_HOST   e.g. smtp.office365.com  or  smtp.gmail.com
    SBP_SMTP_PORT   e.g. 587 (defaults to 587 if not set)
    SBP_SMTP_USER   the mailbox/account to send from
    SBP_SMTP_PASS   its password (or an app password -- see README)
    SBP_SMTP_FROM   optional; defaults to SBP_SMTP_USER if not set

Locally, set these in your terminal session before running scrape.py.
On GitHub Actions, set them as repository Secrets and pass them into
the workflow's env: block (already done in daily-scrape.yml).
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def smtp_configured():
    """True if enough SMTP settings are present in the environment to
    even attempt sending. Used to decide whether to try SMTP before
    falling back to Outlook."""
    return bool(
        os.environ.get("SBP_SMTP_HOST")
        and os.environ.get("SBP_SMTP_USER")
        and os.environ.get("SBP_SMTP_PASS")
    )


def send_alert_email_smtp(to_address, subject, body, body_html=None):
    """Send an email over SMTP. Returns True on success, False otherwise
    (missing config, auth failure, network error, etc.) -- callers should
    treat False as non-fatal.

    If body_html is given, the message is sent as multipart/alternative
    (plain-text `body` + `body_html`), so mail clients that render HTML
    show the styled version and everything else falls back to plain
    text. If body_html is omitted, a plain-text-only email is sent."""
    host = os.environ.get("SBP_SMTP_HOST")
    port = int(os.environ.get("SBP_SMTP_PORT", "587"))
    user = os.environ.get("SBP_SMTP_USER")
    password = os.environ.get("SBP_SMTP_PASS")
    from_addr = os.environ.get("SBP_SMTP_FROM", user)

    if not (host and user and password):
        print("  -> SMTP not configured (missing SBP_SMTP_HOST/USER/PASS); skipping.")
        return False

    if body_html:
        msg = MIMEMultipart("alternative")
        # Attach plain text first, HTML last -- clients use the LAST
        # part they understand, so HTML must come after plain text.
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(body_html, "html"))
    else:
        msg = MIMEText(body, "plain")

    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_address

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [to_address], msg.as_string())
        return True
    except Exception as e:
        print(f"  -> warning: failed to send alert email via SMTP ({e})")
        return False
