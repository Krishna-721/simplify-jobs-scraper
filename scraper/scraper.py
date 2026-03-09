from typing import List, Dict, Any

from core.models import JobListing, ScraperState
from core.config import ScraperConfig
from core.constants import SimplifyConstants
from scraper.parser import SimplifyParser
from scraper.url_builder import URLBuilder
from scraper.browser_client import BrowserClient
from core.state_manager import StateManager
from exporter.data_exporter import DataExporter


class SimplifyScraper:
    """
    Main scraper class — orchestrates browser, API interception,
    pagination via infinite scroll, and data export.
    """

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
        """Scroll by pressing End key and waiting for new API response."""
        page = self.browser.page

        try:
            await page.keyboard.press("End")
            await page.wait_for_timeout(1_000)
            await page.keyboard.press("End")
            await page.wait_for_timeout(1_000)
            await page.keyboard.press("End")

            try:
                await page.wait_for_response(
                    lambda r: self.constants.SEARCH_ENDPOINT in r.url
                    and self.constants.API_HOST in r.url,
                    timeout=5_000,
                )
                return True
            except Exception:
                return False

        except Exception as e:
            print(f"  [scroll error] {e}")
            return False

    # ── Description fetcher ──────────────────────────────────────────────

    # async def _fetch_descriptions(self, jobs: List[JobListing]) -> None:
    #     """Fetch full description for each job via the detail API."""
    #     print("=========================")
    #     print(f"  Fetching descriptions for {len(jobs)} jobs...")
    #     print("=========================")

    #     for i, job in enumerate(jobs):
    #         try:
    #             job_id = job.link.split("/")[-1]
    #             url = f"{self.constants.API_DETAIL}/{job_id}"
    #             response = await self.browser.page.request.get(url)
    #             data = await response.json()

    #             # API returns { "detail": { "description": "...", ... } }
    #             detail = data.get("detail", {})
    #             if i==0:
    #                 print("[DEBUG] detail type: {type(detail)}")
    #                 if isinstance(detail, dict):
    #                     print(f"  [DEBUG] detail keys: {list(detail.keys())}")
    #                     # Print first 200 chars of detail to see structure
    #                     import json
    #                     print(f"  [DEBUG] detail preview: {json.dumps(detail, default=str)[:300]}")
    #                 else:
    #                     print(f"  [DEBUG] detail value: {str(detail)[:200]}")
    #                     print(f"  [{i+1}/{len(jobs)}] ✓ {job.title[:40]}")

    #         except Exception as e:
    #                 print(f"  [{i+1}/{len(jobs)}] ✗ failed: {e}")

    # ── Main scrape ──────────────────────────────────────────────────────

    async def scrape_jobs(
        self,
        filters: Dict[str, Any],
        output_dir: str = "output",
    ) -> List[JobListing]:
        """
        Full scraping workflow per keyword:
          1. Navigate to filtered URL
          2. Collect first batch via network interception
          3. Scroll to load more batches
          4. Fetch descriptions via detail API
          5. Export CSV
        """
        keyword     = filters.get("keyword", "")
        max_scrolls = filters.get("max_scrolls", self.config.MAX_SCROLLS)
        state       = self.state_manager.load_state()
        all_jobs:   List[JobListing] = []
        seen_links: set              = set()

        await self.browser.start()

        try:
            await self._setup_interceptor()

            # Navigate and wait for first API response
            url = self.url_builder.build_search_url(filters)
            print(f"[Scraper] Navigating: {url[:80]}...")

            async with self.browser.page.expect_response(
                lambda r: (
                    self.constants.SEARCH_ENDPOINT in r.url
                    and self.constants.API_HOST in r.url
                ),
                timeout=30_000,
            ) as _:
                await self.browser.page.goto(
                    url, wait_until="domcontentloaded", timeout=30_000
                )

            await self.browser.page.wait_for_timeout(2_000)

            # First batch
            new_jobs = self._flush_captured(keyword, seen_links)
            all_jobs.extend(new_jobs)
            print(f"  First load: +{len(new_jobs)} jobs (total: {len(all_jobs)})")

            # Scroll for more
            for scroll_num in range(1, max_scrolls + 1):
                print(f"  Scroll {scroll_num}/{max_scrolls}...")
                self._captured_docs.clear()

                got_more = await self._scroll_and_wait()
                if not got_more:
                    print("  All available jobs loaded for this keyword.")
                    break

                await self.browser.page.wait_for_timeout(1_000)
                new_jobs = self._flush_captured(keyword, seen_links)
                all_jobs.extend(new_jobs)
                print(f"  +{len(new_jobs)} new jobs (total: {len(all_jobs)})")

                if len(new_jobs) == 0:
                    print("  No unique jobs left — stopping.")
                    break

                state.increment_scroll()
                state.add_scraped(len(new_jobs))

            # Fetch descriptions BEFORE closing browser
            # await self._fetch_descriptions(all_jobs)

        finally:
            await self.browser.close()

        # Export
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