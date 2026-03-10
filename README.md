# Simplify.jobs Scraper

A Python-based job scraper built for Simplify.jobs using Playwright for browser automation. This was built as part of a take-home assignment where the goal was to scrape the listed jobs and export them as structured CSV data.

---

## What This Does

- Searches Simplify.jobs for jobs based on keywords like "Data Science", "Data Analyst", "Machine Learning" etc.
- Applies filters like employment type, experience level, remote options, and location
- Scrapes job listings and exports them to CSV files in the `output/` folder
- Each keyword gets its own CSV file with a timestamp in the name
- On every new run, a new csv is created with a new timestamp which acts as the serial number.

---

## Project Structure

```
Simplify_Scraper/
├── core/                # Core data models, config, constants
│   ├── __init__.py
│   ├── models.py        # JobListing and ScraperState dataclasses
│   ├── config.py        # All settings (timeouts, defaults, limits)
│   ├── constants.py          # URLs and API endpoint constants
│   └── state_manager.py      # Tracks scroll position and job counts
│
├── scraper/                  # All scraping logic
│   ├── __init__.py
│   ├── browser_client.py     # Playwright browser start/close
│   ├── url_builder.py        # Builds filtered search URLs
│   ├── parser.py        # Parses Typesense API JSON → JobListing
│   └── scraper.py       # Main orchestrator 
├── exporter/            # CSV export
│   ├── __init__.py
│   └── data_exporter.py      # Saves jobs to timestamped CSV
│
├── output/                   # Generated CSV files go here
├── __init__.py
├── main.py          # Entry point — configure keywords and filters here
├── requirements.txt
└── README.md
```

---

## How It Works

### Discovery Phase
The first step I did was open Simplify.jobs in Chrome DevTools and observed the Network tab while browsing jobs. I noticed the site is a React/Next.js SPA and doesn't load jobs through normal HTML — instead it calls a **Typesense search API** in the background.

The API endpoint is:
```
https://js-ha.simplify.jobs/multi_search?x-typesense-api-key=...
```

This was a huge observation because it meant I didn't need to scrape HTML at all rather I could just intercept the API responses directly using Playwright's `page.on("response", ...)` listener.

### How Scraping Works
1. Browser opens the filtered Simplify.jobs URL (filters are encoded in the URL params)
2. A network interceptor listens for any response from `js-ha.simplify.jobs/multi_search`
3. When the page loads, Simplify fires this API and returns ~40 job listings
4. We parse the JSON response and extract: title, company, location, link, employment type.
```
In scraper.py --> body = await response.json(). Here the interceptor caches the response which looks like this :
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
            "type": "Full-Time",
            "salary_min": "",
            "salary_max": ""
          }
        }
      ]
    }
  ]
}
Then we dig in to this layer by layer - 

        for result in body.get("results", []):    
            for hit in result.get("hits", []):       
                doc = hit.get("document", {})

After this step the parser.py maps each filed to the jobs list.
```
5. An infinite scroll attempt is made to load more jobs (more on this below)
6. All jobs are saved to CSV

### URL Filter System
Simplify.jobs encodes all filters directly in the URL, for example:
```
https://simplify.jobs/jobs?query=Data+Science&state=North+America&jobType=Full-Time%3BInternship&experience=Entry+Level%2FNew+Grad
```
So there's no need to click UI buttons- just build the right URL and navigate to it.

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
| `description` | ⚠️ Empty | Requires login (see below) |
| `salary_range` | ⚠️ Empty | Requires login (see below) |

---

## What I Tried — Infinite Scroll Pagination

Getting more than one batch of jobs (~40) was the hardest part of this project. Simplify uses **infinite scroll** (not page numbers), meaning to get more jobs you have to scroll down to trigger a new API call.

Here's everything I tried:

### Attempt 1 — `window.scrollTo(0, document.body.scrollHeight)`
The most common scroll approach. Didn't work because Simplify uses a **virtualized list** — the page body height doesn't grow when new jobs load, it just swaps DOM elements in and out.

### Attempt 2 — Find the scrollable container
Tried to find the actual scrollable element using `getComputedStyle` to check for `overflow: auto/scroll`. Found a `.rfm-marquee-container` element but that was just a banner, not the job list.

### Attempt 3 — `End` key press
Simulated keyboard `End` key to scroll to the bottom of the page. Didn't trigger the Simplify scroll listener.

### Attempt 4 — `page.mouse.wheel()`
Simulated physical mouse wheel scrolling. Still didn't trigger more jobs loading.

### Current Status
The first batch loads perfectly (~40 jobs per keyword). Infinite scroll pagination is not yet working due to Simplify's virtualized list implementation. This is a known limitation and can be fixed in a future update once the exact scrollable container is identified via browser DevTools.

---

## Why Description and Salary Are Empty

During development I discovered that Simplify.jobs has a detail API:
```
https://api.simplify.jobs/v2/job-posting/{job_id}
```

However, this endpoint returns `{"detail": "Not Found"}` without authentication. Both description and salary are behind login.

**To enable descriptions in the future:**
1. Run `login.py` (to be implemented) to log in manually and save the browser session to `session.json`
2. Load `session.json` in `BrowserClient` on startup
3. Re-enable `await self._fetch_descriptions(all_jobs)` in `scraper.py`

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
    "location":         "North America", # can be anything
    "employment_type":  ["Full-Time", "Internship"],
    "experience_level": ["Entry Level/New Grad", "Internship"],
    "remote_option":    ["Remote", "Hybrid", "In Person"],
    "category":         [],   # empty = all categories
    "max_scrolls":      5,    # can be increased
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

Each run creates a new csv file with all the current jobs listed on the portal. This helps in identifying how many and what kind of jobs have been posted at each timestamp.

---

## Tech Stack

- **Python 3.11 or greater**
- **Playwright** — browser automation and network interception
- **Microsoft Edge** — browser used for scraping
- **Typesense API** — Simplify's internal search API (intercepted via network listener)

---

## Known Limitations

1. **~40 jobs per keyword** — infinite scroll not working yet due to virtualized list
2. **No description/salary** — protected behind Simplify's login barrier
3. **Single location per run** — scraping multiple locations requires multiple runs. Using list in the location input will break the url_builder.  
---

## References

- [Playwright Python Docs](https://playwright.dev/python/)
- [Simplify.jobs](https://simplify.jobs)
- Claude.ai as a paired partner.