"""
main.py — Entry point for Simplify.jobs scraper.

Run:
    python main.py

Edit KEYWORDS and BASE_FILTERS below to customise each run.
Each keyword gets its own CSV in the output/ folder.
"""

import asyncio
from typing import Dict, Any, List

from scraper.scraper import SimplifyScraper
from core.config import ScraperConfig
from core.models import JobListing


async def run_simplify_scraper(
    input_data: Dict[str, Any]
) -> List[JobListing]:
    """Run the Simplify scraper with given input data."""
    validated = ScraperConfig.validate_input(input_data)
    keywords: List[str] = validated.pop("keywords")
    output_dir: str = input_data.get("output_dir", "output")

    all_jobs: List[JobListing] = []

    for keyword in keywords:
        print(f"\n{'='*45}")
        print(f"  Scraping keyword: {keyword}")
        print(f"{'='*45}")

        filters = {**validated, "keyword": keyword}
        scraper = SimplifyScraper()
        jobs = await scraper.scrape_jobs(filters, output_dir=output_dir)
        all_jobs.extend(jobs)

    print("========================")
    print("\n All done! ")
    print(f"\n Total jobs across all keywords: {len(all_jobs)}")
    print("========================")

    return all_jobs


def main():

    # Configuring the main working

    INPUT = {
        "keywords": [
            "Data Science",
            "Data Analyst",
            # "Machine Learning",
            # "AI Engineer",
            # "Software Developer","Backend Developer"
        ],
        "locations":         "North America",# "India","Canada","UK","Australia"],
        "employment_type":  ["Full-Time", "Internship"],
        "experience_level": ["Entry Level/New Grad", "Internship"],
        "remote_option":    ["Remote", "Hybrid", "In Person"],
        "category":         [],       # all categories
        "max_scrolls":      5,        # 5 scrolls per keyword 
        "output_dir":       "output",
    }

    asyncio.run(run_simplify_scraper(INPUT))


if __name__ == "__main__":
    main()
