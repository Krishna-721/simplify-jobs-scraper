import csv
import os
from datetime import datetime
from typing import List

from core.models import JobListing
from core.constants import SimplifyConstants


class DataExporter:
    # Handles the exports to csv
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
        if not jobs:
            print("[Exporter] No jobs to save.")
            return ""

        os.makedirs(output_dir, exist_ok=True)
        slug = keyword.replace(" ", "_").lower() if keyword else "all"
        
        # Find existing file for this keyword
        existing_file = None
        for f in os.listdir(output_dir):
            if f.startswith(f"{self.constants.OUTPUT_CSV_PREFIX}_{slug}_"):
                existing_file = os.path.join(output_dir, f)
                break

        # Load existing links for deduplication
        existing_links = set()
        existing_jobs = []
        if existing_file:
            with open(existing_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # fixes blank salary from old runs
                    if not row.get("salary_range"):
                        row["salary_range"] = "Not Disclosed"
                    existing_jobs.append(row)
                    existing_links.add(row.get("link", ""))

        # Filter out duplicates
        new_jobs = [j for j in jobs if j.link not in existing_links]
        print(f"[Exporter] {len(new_jobs)} new jobs, {len(jobs) - len(new_jobs)} duplicates skipped.")

        if not new_jobs and existing_file:
            print("[Exporter] No new jobs to add.")
            return existing_file

        # Merge new adn old then saving with updated timestamp
        now = datetime.now()
        filename = (
            f"{self.constants.OUTPUT_CSV_PREFIX}_{slug}"
            f"_{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}.csv"
        )
        filepath = os.path.join(output_dir, filename)

        # Delete old file
        if existing_file:
            os.remove(existing_file)

        # Write merged data
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=self.FIELD_NAMES, extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(existing_jobs)        # old jobs first
            for job in new_jobs:
                writer.writerow(job.to_dict())     # new jobs appended

        print(f"[Exporter] Saved {len(existing_jobs) + len(new_jobs)} total jobs → {filepath}")
        return filepath