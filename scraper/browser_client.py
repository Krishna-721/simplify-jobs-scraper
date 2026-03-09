from typing import Optional
from playwright.async_api import async_playwright, Browser, Page

from core.config import ScraperConfig


class BrowserClient:
    """Manages Playwright browser lifecycle."""

    def __init__(self):
        self.config = ScraperConfig
        self._playwright = None
        self._browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.HEADLESS,
            channel="msedge",
            args=["--no-sandbox"],
        )
        self.page = await self._browser.new_page()
        print("[Browser] Started.")

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        print("[Browser] Closed.")
