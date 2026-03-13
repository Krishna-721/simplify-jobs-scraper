from typing import List, Dict, Any

from core.models import JobListing, ScraperState
from core.config import ScraperConfig
from core.constants import SimplifyConstants
from scraper.parser import SimplifyParser
from scraper.url_builder import URLBuilder
from scraper.browser_client import BrowserClient
from core.state_manager import StateManager
from exporter.data_exporter import DataExporter

import re
from bs4 import BeautifulSoup


class SimplifyScraper:
    """
    Main scraper class — orchestrates browser, API interception,
    pagination via infinite scroll, and data export.
    """

    SOURCE_NAME = SimplifyConstants.SOURCE_NAME

    def __init__(self):
        self.config        = ScraperConfig
        self.constants     = SimplifyConstants
        self.parser        = SimplifyParser()
        self.url_builder   = URLBuilder()
        self.browser       = BrowserClient()
        self.state_manager = StateManager()
        self.data_exporter = DataExporter()
        self._captured_docs: list[dict] = []

    # ── Network interceptor ──────────────────────────────────────────────

    async def _setup_interceptor(self) -> None:
        """Listen for Typesense multi_search responses and buffer documents."""
        async def on_response(response) -> None:
            if self.constants.SEARCH_ENDPOINT not in response.url:
                return
            if self.constants.API_HOST not in response.url:
                return
            try:
                body = await response.json()
                for result in body.get("results", []):
                    for hit in result.get("hits", []):
                        doc = hit.get("document", {})
                        if doc:
                            self._captured_docs.append(doc)
            except Exception as e:
                print(f"  [interceptor error] {e}")

        self.browser.page.on("response", on_response)

    # ── Scroll helper ────────────────────────────────────────────────────

    async def _scroll_and_wait(self) -> bool:
        """Scroll and listen for API response simultaneously."""
        page = self.browser.page

        try:
            container = page.locator('.gap-4.overflow-y-auto.flex-col').first
            await container.wait_for(timeout=15_000)
            box = await container.bounding_box()

            if not box:
                print("  [scroll] Container not found.")
                return False

            await page.mouse.move(
                box['x'] + box['width'] / 2,
                box['y'] + box['height'] / 2
            )

            async with page.expect_response(
                lambda r: self.constants.SEARCH_ENDPOINT in r.url
                and self.constants.API_HOST in r.url,
                timeout=12_000,
            ) as response_info:
                for _ in range(8):
                    await page.mouse.wheel(0, 500)
                    await page.wait_for_timeout(300)

            print("  [scroll] New batch received!")
            await page.wait_for_timeout(2_000)
            return True

        except Exception as e:
            print(f"  [scroll] No new batch: {e}")
            return False

    # ── Batch detail fetcher ─────────────────────────────────────────────

    async def _fetch_batch_details(self, jobs: List[JobListing], batch_num: int, total: int) -> None:
        print(f"  [Batch {batch_num}] Fetching details for {len(jobs)} jobs...")
        for job in jobs:
            try:
                job_id = job.link.split("/")[-1]
                url = f"{self.constants.API_DETAIL}/{job_id}/company"
                data = await self.browser.page.evaluate("""
                    async (url) => {
                        const res = await fetch(url, { credentials: 'include' });
                        return await res.json();
                    }
                """, url)

                # Description
                job.description = data.get("description") or ""
                soup = BeautifulSoup(job.description, "html.parser")
                job.description = soup.get_text(separator=" ").strip()
                job.description = " ".join(job.description.split())

                # Salary
                min_s    = data.get("min_salary")
                max_s    = data.get("max_salary")
                period   = data.get("salary_period")
                currency = data.get("currency_type", "USD")

                if min_s is not None and max_s is not None:
                    period_label = "/hr" if period == 1 else "/yr"
                    job.salary_range = f"{currency} {min_s} - {max_s} {period_label}"
                elif min_s is not None:
                    job.salary_range = f"{currency} {min_s}+"
                else:
                    job.salary_range = "Not Disclosed"

            except Exception:
                job.salary_range = "Not Disclosed"

        print(f"  [Batch {batch_num}] ✓ Done. Total so far: {total}")

    # ── Main scrape ──────────────────────────────────────────────────────

    async def scrape_jobs(
        self,
        filters: Dict[str, Any],
        output_dir: str = "output",
    ) -> List[JobListing]:

        keyword    = filters.get("keyword", "")
        max_jobs   = filters.get("max_jobs",   self.config.MAX_JOBS)
        batch_size = filters.get("batch_size", self.config.BATCH_SIZE)
        state      = self.state_manager.load_state()
        all_jobs:  List[JobListing] = []
        pending:   List[JobListing] = []
        seen_links: set = set()
        batch_num  = 0

        await self._setup_interceptor()

        url = self.url_builder.build_search_url(filters)
        print(f"[Scraper] Navigating: {url[:80]}...")

        async with self.browser.page.expect_response(
            lambda r: self.constants.SEARCH_ENDPOINT in r.url
            and self.constants.API_HOST in r.url,
            timeout=30_000,
        ) as _:
            await self.browser.page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        await self.browser.page.wait_for_timeout(6_000)

        # Helper to drain pending buffer in batch_size chunks
        async def drain_pending():
            nonlocal batch_num
            while len(pending) >= batch_size and len(all_jobs) < max_jobs:
                batch = pending[:batch_size]
                del pending[:batch_size]
                batch_num += 1
                await self._fetch_batch_details(batch, batch_num, len(all_jobs) + len(batch))
                all_jobs.extend(batch)

        # First batch
        new_jobs = self._flush_captured(keyword, seen_links)
        if not new_jobs:
            print("[WARNING] First load returned 0 jobs — API may have changed. Check endpoints.")
            return []
        pending.extend(new_jobs)
        print(f"  First load: +{len(new_jobs)} jobs (pending: {len(pending)})")
        await drain_pending()

        # Scroll for more
        scroll_num = 0
        while len(all_jobs) < max_jobs:
            scroll_num += 1
            print(f"  Scroll {scroll_num}... ({len(all_jobs) + len(pending)}/{max_jobs} jobs found)")
            self._captured_docs.clear()

            got_more = await self._scroll_and_wait()
            if not got_more:
                print("  Retrying, please wait...")
                got_more = await self._scroll_and_wait()
            if not got_more:
                print("  All available jobs loaded.")
                break

            await self.browser.page.wait_for_timeout(1_000)
            new_jobs = self._flush_captured(keyword, seen_links)
            if not new_jobs:
                print("  No unique jobs left — stopping.")
                break

            pending.extend(new_jobs)
            print(f"  +{len(new_jobs)} new jobs (pending: {len(pending)})")
            await drain_pending()

        # Process partial last batch
        if pending and len(all_jobs) < max_jobs:
            batch_num += 1
            remaining = pending[:max_jobs - len(all_jobs)]
            print(f"  Partial batch: {len(remaining)}/{batch_size} jobs — processing...")
            await self._fetch_batch_details(remaining, batch_num, len(all_jobs) + len(remaining))
            all_jobs.extend(remaining)

        if len(all_jobs) >= max_jobs:
            print(f"  Max jobs ({max_jobs}) reached.")
            all_jobs = all_jobs[:max_jobs]

        self.data_exporter.save_to_csv(all_jobs, output_dir=output_dir, keyword=keyword)
        print(f"[Scraper] Done. Total unique jobs: {len(all_jobs)}")
        return all_jobs

    # ── Deduplication helper ─────────────────────────────────────────────

    def _flush_captured(self, keyword: str, seen_links: set) -> List[JobListing]:
        """Parse buffered docs, deduplicate by link, return only new jobs."""
        jobs = []
        for doc in self._captured_docs:
            job = self.parser.parse_single_doc(doc, keyword)
            if job and job.is_valid() and job.link not in seen_links:
                seen_links.add(job.link)
                jobs.append(job)
        self._captured_docs.clear()
        return jobs