# SBP Circulars Scraper (Selenium version)

Automatically visits the State Bank of Pakistan (SBP) [circulars search
page](https://www.sbp.org.pk/circulars/search-result), pages through
every result, and saves the list into an Excel file.

Each time you run it, it also tells you **what changed** since the last
run (circulars added or removed) and updates the Excel file to reflect
the current state of the site.

---

## Why Selenium (a real browser) instead of a simple request?

The SBP results list is drawn by JavaScript after the page loads, and the
site is behind Cloudflare, which turns away plain HTTP clients outright.
A simple `requests` call gets either an empty shell of a page or a "Sorry,
you have been blocked" notice. So this scraper drives an actual (headless,
i.e. invisible) Chrome browser: it opens the page, waits for the results
to render, and reads them.

### How it gets past page 1

Each results page does have its own web address — page 2 is the page-1
address with `/P30` on the end (30 = rows per page), page 3 is `/P60`, and
so on. The scraper reads the address off the site's own ">" link and goes
straight there.

It also **starts a brand-new browser for every page**. That sounds
wasteful, but Cloudflare blocks every request after the first one in a
given browser session — no matter which address you ask for, how long you
wait, or whether cookies are cleared in between. A fresh browser per page
is what actually works, and a search only has a handful of pages.

---

## Automated daily scrape (GitHub Actions)

The scraper now runs automatically every day at **8:00 AM Pakistan
Time**, on GitHub's own servers — you don't need to keep your computer
on or remember to run it yourself. This is set up in
`.github/workflows/daily-scrape.yml`.

Every day it:
1. Checks out the repo on a fresh GitHub-hosted Linux machine.
2. Installs Python, Chrome, and the required packages.
3. Runs `python scrape.py` exactly like you would locally.
4. Commits the updated `sbp_circulars.xlsx`, `sbp_circulars_changelog.json`,
   and `sbp_scraper.log` straight back into the repo.

**To get it running on your own GitHub repo:**

```bash
git remote add origin https://github.com/<your-username>/<your-repo>.git
git branch -M main
git push -u origin main
```

That's it — no extra setup, secrets, or tokens needed. GitHub Actions
picks the workflow up automatically once it's in the repo.

You can also trigger a run manually any time, without waiting for
9 AM: go to your repo on GitHub → the **Actions** tab → **Daily SBP
circulars scrape** → **Run workflow**.

**A few things worth knowing:**
- GitHub Actions schedules run in UTC. `0 3 * * *` in the workflow
  file is 3:00 AM UTC, which is 8:00 AM PKT. If you ever move time
  zones or want a different time, edit that one line.
- GitHub doesn't guarantee the *exact* minute for scheduled runs —
  during busy periods it can start a few minutes late. This is normal
  and not something to worry about for a daily check.

---

## Email alerts (via Gmail, working from GitHub Actions too)

Email alerts are sent over plain SMTP using a Gmail account as the
sender — this works anywhere, including on GitHub's servers, unlike
the Outlook option (which only works locally on Windows and is kept
purely as a fallback if SMTP isn't configured).

### Step 1 — create a Gmail "App Password"

Gmail won't accept your normal login password for this — you need a
special 16-character **App Password** instead. To generate one:

1. Go to **https://myaccount.google.com/security**
2. Turn on **2-Step Verification** if it isn't already on (this is
   required before Google will let you create an App Password).
3. Go to **https://myaccount.google.com/apppasswords**
4. Under "App name," type something like `SBP Scraper` and click
   **Create**.
5. Google shows you a 16-character password (e.g. `abcd efgh ijkl
   mnop`). Copy it — you can enter it with or without the spaces. This
   is what you'll use below, **not** your regular Gmail password.

### Step 2 — add it to GitHub as repo Secrets

Go to your repo on GitHub → **Settings** → **Secrets and variables** →
**Actions** → **New repository secret**, and add:

| Secret name | Value |
|---|---|
| `SBP_SMTP_HOST` | `smtp.gmail.com` |
| `SBP_SMTP_PORT` | `587` |
| `SBP_SMTP_USER` | your full Gmail address, e.g. `yourname@gmail.com` |
| `SBP_SMTP_PASS` | the 16-character App Password from Step 1 |

**Who the alert gets sent to** is set directly in the workflow file
(`.github/workflows/daily-scrape.yml`), in the `--alert-email` flag —
edit that line to change the recipient (it doesn't need to be a Gmail
address; it can be sent *from* Gmail *to* any inbox, including your
work email).

### Step 3 — test it locally first (recommended)

Before relying on the daily GitHub Actions run, confirm it actually
works from your own machine:

```powershell
# PowerShell
$env:SBP_SMTP_HOST = "smtp.gmail.com"
$env:SBP_SMTP_PORT = "587"
$env:SBP_SMTP_USER = "yourname@gmail.com"
$env:SBP_SMTP_PASS = "your-16-char-app-password"
python scrape.py --alert-email "yourname@gmail.com"
```

If `SBP_SMTP_HOST`/`USER`/`PASS` aren't set at all (neither locally
nor as GitHub Secrets), the scraper falls back to trying Outlook, and
if that's not available either, it just logs a warning and continues
— a missing email never stops the scrape itself from completing.

---

## Dashboard (live view in your browser)

There's a local web dashboard that shows your circulars in a
searchable, sortable table, a "recent activity" panel showing what was
added or removed on the last run, and a "View log" panel showing the
persistent run log. It re-reads `sbp_circulars.xlsx` fresh every time
you load the page or click "Reload data" — no re-uploading or
exporting needed.

Start it with:

```bash
python -m sbp_scraper.dashboard_server
```

Then open **http://localhost:8000** in your browser.

Since scraping now happens automatically on GitHub's schedule (see
above) rather than on your own machine, the usual flow is:

1. `git pull` to fetch whatever the scheduled run committed overnight.
2. Click **"Reload data"** on the dashboard (or just reload the page)
   to see it.

There's also an "Auto-refresh (30s)" checkbox if you want the table to
keep polling for changes on its own while it's open on a screen (this
still only re-reads whatever's on disk locally — remember to `git
pull` first).

Options:

```bash
python -m sbp_scraper.dashboard_server --file my_circulars.xlsx --port 8080
```

---

## The run log (backend audit trail)

Every time the scraper runs — whether triggered by GitHub Actions on
its schedule, or by you running `scrape.py` locally — it appends a
timestamped entry to **`sbp_scraper.log`**, a plain text file kept
right in the repo. Unlike the changelog JSON (which only ever holds
the *latest* diff), this log keeps the full history of every run: when
it started, how many rows were found on each page, what changed,
whether an email alert was sent, and the full error text if something
failed.

You can:
- Open `sbp_scraper.log` directly in any text editor (or on GitHub,
  just view the file in the repo).
- Or click **"View log"** in the dashboard to see the last 200 lines
  without leaving the browser.

---

## Setup

**Requirements:** Python 3, Google Chrome installed on your machine.

Install the Python packages:

```bash
pip install selenium webdriver-manager beautifulsoup4 pandas openpyxl
```

You do **not** need to separately download a chromedriver —
`webdriver-manager` fetches the correct one automatically the first
time you run the script.

**Optional — email alerts:** if you want an email sent automatically
when a change is detected, also install `pywin32`:

```bash
pip install pywin32
```

This only works on **Windows**, with **desktop Outlook installed and
signed in** on the same machine (it sends the email through Outlook
itself, the same as if you clicked "New Email" and hit Send). If you
skip this step or aren't on Windows, the scraper still runs completely
normally — you just won't get an email, and it'll print a note instead.

---

## Usage

Run the scraper from the project folder:

```bash
python scrape.py
```

By default this searches the "Microfinance" category and saves results
to `sbp_circulars.xlsx` in the same folder.

### Common options

```bash
# Filter by a different category
python scrape.py --category ""

# Filter by department (used only to narrow the search on the site —
# not stored as a column in the output)
python scrape.py --department "BPRD"

# Save to a different file
python scrape.py --output my_circulars.xlsx

# Watch the browser work instead of running invisibly (useful for debugging)
python scrape.py --show-browser

# Slow down a bit between pages (default is 1 second)
python scrape.py --delay 2.0

# Email someone when a change is detected (Windows + Outlook only, see Setup)
python scrape.py --alert-email "you@example.com"
```

Run `python scrape.py --help` to see all available filters (search
text, circular type, start/end date, etc).

---

## What you get in the Excel file

Each row is one circular, with these columns:

| Column | Meaning |
|---|---|
| `title` | The circular's title |
| `circular_no` | Its reference number |
| `date` | Date it was issued |
| `category` | e.g. "Microfinance" |
| `circular_type` | e.g. "Circular Letter" |
| `url` | Direct link to the circular on SBP's site |

(Department name/code/id are intentionally **not** included — they were
dropped as irrelevant.)

---

## "What changed since last time?" (change detection)

The Excel file is treated as a **base snapshot** — it represents what
the scraper found the *last* time it ran. Every time you run the
script again:

1. It loads the existing Excel file (the base).
2. It re-scrapes the site to get the current list.
3. It compares the two lists by each circular's link (its unique
   fingerprint) — not just by counting rows, so it also catches cases
   where one circular was swapped for another and the total count
   happens to stay the same.
4. If anything is different, it prints an alert to the console listing
   exactly what was **added** and what was **removed**, e.g.:

   ```
   ============================================================
   CHANGE DETECTED since last run
   ============================================================
   Previous count: 42   New count: 43

   + 1 added:
       + Some New Circular Title  (https://www.sbp.org.pk/circulars/...)

   - 0 removed:
   ============================================================
   ```

   If nothing changed, it simply prints `No change: counts and URLs
   match the previous run.`

   If you passed `--alert-email you@example.com` and a change *was*
   detected, this same alert text is also emailed to that address via
   desktop Outlook.

5. It then **overwrites** the Excel file with the latest results. The
   file does not pile up history — it always reflects the most recent
   run, ready to be compared against the next time you run the script.

---

## Project structure

```
.github/workflows/daily-scrape.yml   ← runs the scraper daily at 9 AM PKT, commits results
requirements.txt                     ← Python packages needed (local + GitHub Actions)
.gitignore                           ← repo hygiene (data files ARE tracked, see above)

scrape.py                    ← run this file (locally, or it's what GitHub Actions runs)
sbp_scraper/
    config.py                ← site URL + Excel column names
    url_builder.py            ← builds the search-page web address from your filters
    browser.py                ← sets up the invisible Chrome browser
    parser.py                 ← reads a loaded page: extracts circular rows + page number
    pagination.py             ← works out the web address of the next page of results
    scraper.py                ← ties browser + parser + pagination together, page by page
    storage.py                ← loads the old Excel file, compares it to the new results,
                                  prints the change alert, saves the new snapshot + changelog
    emailer.py                ← picks SMTP or Outlook automatically (see below)
    emailer_smtp.py           ← cross-platform email (works on GitHub Actions too)
    emailer_outlook.py        ← Windows + Outlook fallback for local runs
    run_log.py                ← persistent run log (sbp_scraper.log)
    job.py                    ← run_scrape_job(): the one place the full scrape logic lives
    dashboard_server.py       ← local, read-only server: shows the live xlsx + log in a browser
    dashboard.html            ← the dashboard page itself (table, filters, recent activity, log)
```

### How it all fits together

```
GitHub Actions (daily at 9 AM PKT, or triggered manually anytime)
   │
   └─→ scrape.py
          │
          ├─→ url_builder.py   → builds the correct search URL from your filters
          │
          └─→ job.py            → run_scrape_job(): the actual work for one run
                 │
                 ├─→ scraper.py        → opens the browser (browser.py), reads each page
                 │                        (parser.py), works out the next page's address
                 │                        (pagination.py), repeats until every page is read
                 ├─→ storage.py        → loads last run's Excel file, compares it to
                 │                        this run's results, saves the changelog + snapshot
                 ├─→ emailer.py        → tries SMTP first (emailer_smtp.py, works
                 │                        everywhere); falls back to Outlook
                 │                        (emailer_outlook.py, Windows-only)
                 └─→ run_log.py        → appends this run to the persistent log file
                        │
                        └─→ GitHub Actions commits the updated files back to the repo

dashboard_server.py  → separate and read-only: after a `git pull`, shows whatever's
                        currently on disk in your browser. It does not run the scraper.
```

Each file has one clear job, so if something on the site changes (say,
the page-indicator text format changes, or the "next" button's label
changes), you only need to fix the one relevant file instead of
digging through one giant script.

---

## Notes / limitations

- The site occasionally fails to advance to the next page (e.g. slow
  load). The scraper detects this (the page number doesn't change) and
  stops gracefully with a warning rather than looping forever.
- Change detection matches circulars by their `url`. If SBP ever
  changes a circular's URL without actually changing its content, that
  would show up as one "removed" + one "added" rather than "no
  change."
