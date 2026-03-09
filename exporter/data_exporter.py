import csv
import os
from datetime import datetime
from typing import List

from core.models import JobListing
from core.constants import SimplifyConstants


class DataExporter:
    """Handles exporting scraped job data to CSV."""

    FIELD_NAMES = [
        "title", "company", "location", "link", "source",
        "description", "salary_range", "employment_type", "search_keyword",
    ]

    def __init__(self):
        self.constants = SimplifyConstants

    def save_to_csv(
        self,
        jobs: List[JobListing],
        output_dir: str = "output",
        keyword: str = "",
    ) -> str:
        """Save job listings to a timestamped CSV file."""
        if not jobs:
            print("[Exporter] No jobs to save.")
            return ""

        os.makedirs(output_dir, exist_ok=True)
        now = datetime.now()
        slug = keyword.replace(" ", "_").lower() if keyword else "all"
        filename = (
            f"{self.constants.OUTPUT_CSV_PREFIX}_{slug}"
            f"_{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}.csv"
        )
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=self.FIELD_NAMES, extrasaction="ignore"
            )
            writer.writeheader()
            for job in jobs:
                writer.writerow(job.to_dict())

        print(f"[Exporter] Saved {len(jobs)} jobs → {filepath}")
        return filepath
