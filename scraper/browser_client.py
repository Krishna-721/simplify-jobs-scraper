import os
from typing import Optional
from playwright.async_api import async_playwright, Page, BrowserContext

from core.config import ScraperConfig


class BrowserClient:
    """Manages Playwright browser lifecycle using real Edge profile."""

    def __init__(self):
        self.config      = ScraperConfig
        self._playwright = None
        self._context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()

        edge_profile = os.path.expandvars(
            r"%LOCALAPPDATA%\Microsoft\Edge\User Data"
        )

        # Launch using real Edge profile — already logged in!
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=edge_profile,
            channel="msedge",
            headless=False,
            args=[
                "--no-sandbox",
                "--profile-directory=Default",
            ],
        )

        self.page = await self._context.new_page()
        print("[Browser] Started with existing Edge profile.")

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        print("[Browser] Closed.")