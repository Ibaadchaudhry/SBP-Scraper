"""Sends the change-alert email through desktop Outlook, using pywin32
(the 'win32com' package). Windows-only, and requires Outlook to be
installed and configured on this machine.

Used as a fallback when SMTP isn't configured (see emailer_smtp.py) --
handy if you're just running scrape.py by hand on your own Windows PC
and already have Outlook signed in there.
"""


def send_alert_email_outlook(to_address, subject, body):
    """Send a plain-text email via Outlook. Returns True on success,
    False if it couldn't be sent (missing pywin32, Outlook not
    installed/running, not on Windows, etc.) -- callers should treat
    False as non-fatal."""
    try:
        import win32com.client as win32
    except ImportError:
        print("  -> pywin32 not installed / not on Windows; can't use Outlook for email.")
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
        print(f"  -> warning: failed to send alert email via Outlook ({e})")
        return False
