"""Sends the change-alert email, picking whichever method is actually
usable in the current environment:

  1. SMTP (emailer_smtp.py) -- if SBP_SMTP_HOST/USER/PASS are set as
     environment variables, use this. Works everywhere, including
     GitHub Actions, since it's just Python's standard library talking
     to a mail server.
  2. Outlook (emailer_outlook.py) -- fallback for running scrape.py by
     hand on a Windows PC with Outlook already signed in, and no SMTP
     configured.

If neither is available/configured, this prints a warning and returns
False rather than failing the whole scrape run.
"""

from .emailer_outlook import send_alert_email_outlook
from .emailer_smtp import send_alert_email_smtp, smtp_configured


def send_alert_email(to_address, subject, body):
    if smtp_configured():
        return send_alert_email_smtp(to_address, subject, body)
    return send_alert_email_outlook(to_address, subject, body)
