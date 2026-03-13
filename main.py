"""
main.py — Entry point for Simplify.jobs scraper.

Run:
    python main.py

Edit KEYWORDS and BASE_FILTERS below to customize each run.
Each keyword gets its own CSV in the output/ folder.
"""

import asyncio
from typing import Dict, Any, List

from scraper.scraper_manager import SimplifyScraper
from core.config import ScraperConfig
from core.models import JobListing


class ScraperManager:
    """Managing multiple keywords and browser stays open until all keywords are done"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self._scraper_classes = []

    def register(self, scraper_cls) -> None:
        self._scraper_classes.append(scraper_cls)
        print(f"[Manager] Registered: {scraper_cls.SOURCE_NAME}")

    async def run(self,input_data: Dict[str, Any]) -> List[JobListing]:
        validated = ScraperConfig.validate_input(input_data)
        keywords: List[str] = validated.pop("keywords")
        all_jobs: List[JobListing] = []

        for scraper_cls in self._scraper_classes:
            # Start browser ONCE for all keywords
            scraper = scraper_cls()
            await scraper.browser.start()
            print("[Manager] Browser started — will stay open for all keywords.")

            try:
                for keyword in keywords:
                    print(f"\n{'='*45}")
                    print(f"  Keyword : {keyword}")
                    print(f"  Scraper : {scraper_cls.SOURCE_NAME}")
                    print(f"{'='*45}")

                    filters = {**validated, "keyword": keyword}
                    jobs = await scraper.scrape_jobs(
                        filters, output_dir=self.output_dir
                    )
                    all_jobs.extend(jobs)

            finally:
                # Close browser ONCE after all keywords done
                await scraper.browser.close()
                print("[Manager] All keywords done — browser closed.")

        print("==========================================")
        print(f"\n All done! Total jobs: {len(all_jobs)}")
        print("==========================================")
        return all_jobs

def main():

    # Configuring the main working

    INPUT = {
        "keywords": [
            "Data Science",
            # "Data Analyst",
            "Machine Learning",
            "AI Engineer",
            #"Software Developer",
            # "Backend Developer"
        ],
        "location":         "North America",# "India","Canada","UK","Australia"],
        "employment_type":  ["Full-Time", "Internship"],
        "experience_level": ["Entry Level/New Grad", "Internship"],
        "remote_option":    ["Remote", "Hybrid", "In Person"],
        "category":         [],       # all categories
        "max_jobs":   400,
        "batch_size": 100,
    }
    output_dir="output"

    manager = ScraperManager(output_dir=output_dir)
    manager.register(SimplifyScraper)
    asyncio.run(manager.run(INPUT)) 

if __name__ == "__main__":
    main()
