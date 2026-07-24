"""Sends the change-alert email through desktop Outlook, using pywin32
(the 'win32com' package). Windows-only, and requires Outlook to be
installed and configured on this machine.

This is intentionally isolated in its own module: if pywin32 isn't
installed, or Outlook isn't available, the rest of the scraper still
works fine -- you just don't get an email, and a warning is printed
instead.
"""


def send_alert_email(to_address, subject, body):
    """Send a plain-text email via Outlook. Returns True on success,
    False if it couldn't be sent (missing pywin32, Outlook not
    installed/running, etc.) -- callers should treat False as
    non-fatal."""
    try:
        import win32com.client as win32
    except ImportError:
        print("  -> pywin32 not installed; skipping email alert. "
              "Install with: pip install pywin32")
        return False

    try:
        outlook = win32.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        mail.To = to_address
        mail.Subject = subject
        mail.Body = body
        mail.Send()
        return True
    except Exception as e:
        print(f"  -> warning: failed to send alert email ({e})")
        return False
