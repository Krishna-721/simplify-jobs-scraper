# Simplify.jobs Scraper

A Python-based job scraper built for Simplify.jobs using Playwright for browser automation. This was built as part of a take-home assignment where the goal was to scrape the listed jobs and export them as structured CSV data.

---

## What This Does

- Searches Simplify.jobs for jobs based on keywords like "Data Science", "Data Analyst", "Machine Learning" etc.
- Applies filters like employment type, experience level, remote options, and location
- Scrapes job listings and exports them to CSV files in the `output/` folder
- Each keyword gets its own CSV file with a timestamp in the name
- On subsequent runs, new jobs are **merged** with existing data — duplicates are skipped based on link URL, and the CSV is re-saved with an updated timestamp

---

## Project Structure

```
Simplify_Scraper/
├── core/                     # Core data models, config, constants
│   ├── __init__.py
│   ├── models.py             # JobListing and ScraperState dataclasses
│   ├── config.py             # All settings (timeouts, defaults, limits)
│   ├── constants.py          # URLs and API endpoint constants
│   └── state_manager.py      # Tracks scroll position and job counts
│
├── scraper/                  # All scraping logic
│   ├── __init__.py
│   ├── browser_client.py     # Playwright browser start/close (persistent Edge profile)
│   ├── url_builder.py        # Builds filtered search URLs
│   ├── parser.py             # Parses Typesense API JSON → JobListing
│   └── scraper.py            # Main orchestrator (scroll, intercept, fetch descriptions)
│
├── exporter/                 # CSV export
│   ├── __init__.py
│   └── data_exporter.py      # Saves/merges jobs to timestamped CSV with deduplication
│
├── auth/                     # Authentication helpers
│   ├── __init__.py
│   └── login.py              # Manual login flow — saves session for description fetching
│
├── output/                   # Generated CSV files go here
├── __init__.py
├── main.py                   # Entry point — configure keywords and filters here
├── requirements.txt
└── README.md
```

---

## How It Works

### Discovery Phase
The first step was opening Simplify.jobs in Chrome DevTools and observing the Network tab while browsing jobs. The site is a React/Next.js SPA and doesn't load jobs through normal HTML — instead it calls a **Typesense search API** in the background.

The API endpoint is:
```
https://js-ha.simplify.jobs/multi_search?x-typesense-api-key=...
```

This was a key observation because it meant there was no need to scrape HTML at all — instead the API responses could be intercepted directly using Playwright's `page.on("response", ...)` listener.

### How Scraping Works
1. Browser opens the filtered Simplify.jobs URL (filters are encoded in the URL params)
2. A network interceptor listens for any response from `js-ha.simplify.jobs/multi_search`
3. When the page loads, Simplify fires this API and returns ~40 job listings
4. We parse the JSON response and extract: title, company, location, link, employment type.
```
In scraper.py --> body = await response.json(). Here the interceptor caches the response which looks like this:
{
  "results": [
    {
      "hits": [
        {
          "document": {
            "title": "Data Scientist",
            "company_name": "Google",
            "locations": ["New York, NY, USA"],
            "slug": "abc123",
            "type": "Full-Time"
          }
        }
      ]
    }
  ]
}
Then we dig into this layer by layer -

        for result in body.get("results", []):    
            for hit in result.get("hits", []):       
                doc = hit.get("document", {})

After this step the parser.py maps each field to the jobs list.
```
5. Infinite scroll loads additional batches (~20 jobs each) via mouse wheel simulation
6. Descriptions and salary are fetched in batches via the detail API (requires login session)
7. All jobs are deduplicated and saved/merged to CSV

### URL Filter System
Simplify.jobs encodes all filters directly in the URL, for example:
```
https://simplify.jobs/jobs?query=Data+Science&state=North+America&jobType=Full-Time%3BInternship&experience=Entry+Level%2FNew+Grad
```
So there's no need to click UI buttons — just build the right URL and navigate to it.

---

### Why not use response headers?
Tried using response interception for descriptions but the `/company` endpoint only fires when a job card is clicked, which would require clicking 400 cards and waiting for each response — slower and more fragile. The authenticated `fetch()` approach from inside the browser context is faster and more reliable.

---

## Data Fields Collected

| Field | Status | Notes |
|---|---|---|
| `title` | ✅ Populated | Job title |
| `company` | ✅ Populated | Company name |
| `location` | ✅ Populated | City, State, Country |
| `link` | ✅ Populated | Direct link to job on Simplify |
| `source` | ✅ Populated | Always "Simplify.jobs" |
| `employment_type` | ✅ Populated | Full-Time / Internship / Part-Time |
| `search_keyword` | ✅ Populated | The keyword used to find this job |
| `description` | ✅ Populated | Fetched via detail API (requires login session) |
| `salary_range` | ✅ Populated | Populated when the employer provides salary info; empty otherwise since most postings don't list it |

---

## Infinite Scroll Pagination

Getting more than one batch of jobs (~40) was the hardest part of this project. Simplify uses **infinite scroll** (not page numbers), meaning to get more jobs you have to scroll down to trigger a new API call.

Here's the journey:

### Failed Attempts
1. **`window.scrollTo(0, document.body.scrollHeight)`** — Didn't work because Simplify uses a **virtualized list**; the page body height doesn't grow.
2. **Find scrollable container via `getComputedStyle`** — Found `.rfm-marquee-container` but that was just a banner.
3. **`End` key press** — Didn't trigger the scroll listener.
4. **`page.mouse.wheel()` on the page body** — Still didn't trigger new jobs.

### Working Solution
The key was identifying the **correct scrollable container**: `.gap-4.overflow-y-auto.flex-col`. Once the mouse is moved to the center of this container, `page.mouse.wheel()` successfully triggers the Typesense API call.

The scroll logic:
1. Locate the container and get its bounding box
2. Move the mouse to the center of the container
3. Fire 8 mouse wheel events (500px each, 300ms apart) while waiting for an API response (12s timeout)
4. If no response, retry once before stopping
5. Repeat until `max_jobs` (default: 400) is reached

Each scroll triggers one Typesense API call that returns a variable number of jobs (typically 20–40). Jobs are accumulated into a `pending` buffer; once it reaches `batch_size` (default: 100), the scraper pauses scrolling, fetches descriptions and salary for that batch via the detail API, then resumes. A full run collects up to `max_jobs` (default: 400) per keyword.

---

## Description & Salary Fetching

Simplify.jobs has a detail API:
```
https://api.simplify.jobs/v2/job-posting/{job_id}/company
```

The scraper fetches descriptions and salary **in batches of `batch_size` (default: 100) during the scroll phase** — not after all jobs are collected. This keeps the scraper efficient and avoids long waits at the end of a run.

However, this endpoint requires authentication — without a valid session it returns `{"detail": "Not Found"}`.

**To enable authenticated scraping:**
1. Run `python auth/login.py` — this opens Edge and lets you log in manually; after you press Enter it saves the session to `session.json`
2. Press Enter in the terminal after logging in
3. The scraper uses a persistent Edge profile (`BrowserClient` launches with your real Edge user data directory), so if you're already logged into Simplify in Edge, descriptions should populate automatically

> **Note:** Some postings don't display salary. They will show an empty salary field since most postings don't list compensation publicly.

---

## Setup and Running

### Requirements
- Python 3.11+
- Microsoft Edge browser installed

### Installation
```bash
# Clone or download the project
cd Simplify_Scraper

# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install msedge
```

### Running
```bash
python main.py
```

### Configuring Keywords and Filters
Edit the `INPUT` dictionary in `main.py`:

```python
INPUT = {
    "keywords": [
        "Data Science",
        "Data Analyst",
        "Machine Learning",
    ],
    "location":         "North America",
    "employment_type":  ["Full-Time", "Internship"],
    "experience_level": ["Entry Level/New Grad", "Internship"],
    "remote_option":    ["Remote", "Hybrid", "In Person"],
    "category":         [],       # empty = all categories
    "max_jobs":         400,      # stop after collecting this many jobs per keyword
    "batch_size":       100,      # fetch descriptions in chunks of this size
}
```

---

## Output

CSV files are saved in the `output/` folder:
```
output/
├── jobs_data_science_20260309_181543.csv
├── jobs_data_analyst_20260309_181632.csv
└── jobs_machine_learning_20260309_181720.csv
```

On each run, the exporter checks for an existing CSV for that keyword. If found, it loads the old jobs, deduplicates by link URL, merges new jobs at the end, and writes a single updated CSV with a fresh timestamp (the old file is deleted). This means you can run the scraper repeatedly and it will accumulate unique jobs over time.

---

## Tech Stack

- **Python 3.11 or greater**
- **Playwright** — browser automation and network interception
- **Microsoft Edge** — browser used for scraping
- **Typesense API** — Simplify's internal search API (intercepted via network listener)

---

## Known Limitations

**Single location per run** — scraping multiple locations requires multiple runs; using a list in the location input will break the URL builder

---

## References

- [Playwright Python Docs](https://playwright.dev/python/)
- [Simplify.jobs](https://simplify.jobs)