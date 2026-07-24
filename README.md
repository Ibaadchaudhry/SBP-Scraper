# SBP Circulars Scraper (Selenium version)

Automatically visits the State Bank of Pakistan (SBP) [circulars search
page](https://www.sbp.org.pk/circulars/search-result), pages through
every result, and saves the list into an Excel file.

Each time you run it, it also tells you **what changed** since the last
run (circulars added or removed) and updates the Excel file to reflect
the current state of the site.

---

## Why Selenium (a real browser) instead of a simple request?

SBP's site loads page 1 normally, but pages 2, 3, 4... are loaded by
JavaScript when you click the ">" (next page) arrow — not by visiting a
different web address. A simple HTTP request can't run that JavaScript,
so it can never actually reach page 2.

This scraper instead drives an actual (headless, i.e. invisible)
Chrome browser: it opens the page, reads how many total pages there
are, clicks ">" the same way a person would, waits for the page to
confirm it advanced, and reads the new content. It repeats until every
page has been read.

---

## Dashboard (live view in your browser)

There's a local web dashboard that shows your circulars in a searchable,
sortable table, a "recent activity" panel showing what was added or
removed on the last run, and — new — a button that actually **triggers
a real scrape** from the browser, plus a persistent **run log**.

Start it with:

```bash
python -m sbp_scraper.dashboard_server
```

Then open **http://localhost:8000** in your browser.

There are two different buttons, and they do different things:

- **"Reload data"** — just re-reads whatever's currently in
  `sbp_circulars.xlsx` right now. Instant. Useful if something else
  (Task Scheduler, a cron job, you running `scrape.py` manually)
  already updated the file and you want the dashboard to catch up.
- **"Run scraper now"** — actually kicks off a real scrape: opens
  headless Chrome, pages through the live SBP site, saves the results,
  and updates the changelog — the same thing `scrape.py` does from the
  command line. This can take anywhere from several seconds to a
  couple of minutes (it's a real browser paging through a real
  website), so the button shows "Scraping…" while it works, and the
  table refreshes automatically the moment it's done. You can keep
  using the rest of the dashboard while it runs.
- **"View log"** — opens a "Logbook" panel showing the persistent run
  log (see below) right in the dashboard, so you don't need to go dig
  up the log file yourself.

There's also an "Auto-refresh (30s)" checkbox if you want the table to
keep polling for changes on its own while it's open on a screen (this
only reloads data — it does not trigger a scrape by itself).

**Options for what the "Run scraper now" button actually searches
for** (department, category, etc.) are set when you *start* the
server, the same way as `scrape.py`'s flags:

```bash
python -m sbp_scraper.dashboard_server --category "Microfinance" --department "BPRD" --alert-email "you@example.com"
python -m sbp_scraper.dashboard_server --file my_circulars.xlsx --port 8080
```

---

## The run log (backend audit trail)

Every time the scraper runs — whether from the command line
(`scrape.py`) or triggered from the dashboard — it appends a
timestamped entry to **`sbp_scraper.log`**, a plain text file next to
your Excel file. Unlike the changelog JSON (which only ever holds the
*latest* diff), this log keeps the full history of every run: when it
started, how many rows were found on each page, what changed, whether
an email alert was sent, and the full error text if something failed.

You can:
- Open `sbp_scraper.log` directly in any text editor.
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

# Slow down a bit between page clicks (default is 1 second)
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
scrape.py                    ← run this file
sbp_scraper/
    config.py                ← site URL + Excel column names
    url_builder.py            ← builds the search-page web address from your filters
    browser.py                ← sets up the invisible Chrome browser
    parser.py                 ← reads a loaded page: extracts circular rows + page number
    pagination.py             ← clicks the ">" next-page link and waits for it to load
    scraper.py                ← ties browser + parser + pagination together, page by page
    storage.py                ← loads the old Excel file, compares it to the new results,
                                  prints the change alert, saves the new snapshot + changelog
    emailer.py                ← (optional) emails the change alert via desktop Outlook
    run_log.py                ← persistent run log (sbp_scraper.log)
    job.py                    ← run_scrape_job(): one full scrape run, shared by
                                  scrape.py (CLI) and the dashboard's "Run" button
    dashboard_server.py       ← local server: re-reads the xlsx live, can trigger a
                                  real scrape, serves the dashboard + log
    dashboard.html            ← the dashboard page itself (table, filters, recent
                                  activity, run button, logbook panel)
```

### How it all fits together

```
scrape.py
   │
   ├─→ url_builder.py   → builds the correct search URL from your filters
   │
   └─→ job.py            → run_scrape_job(): the actual work for one run
          │
          ├─→ scraper.py        → opens the browser (browser.py), reads each page
          │                        (parser.py), clicks "next" (pagination.py),
          │                        repeats until every page is read
          ├─→ storage.py        → loads last run's Excel file, compares it to
          │                        this run's results, saves the changelog + snapshot
          ├─→ emailer.py        → (optional) emails the alert via Outlook
          └─→ run_log.py        → appends this run to the persistent log file

dashboard_server.py  → calls the SAME job.py when you click "Run scraper now",
                        so the dashboard and the command line always behave
                        identically — there's only one place the scrape logic lives.
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
