import asyncio
from playwright.async_api import async_playwright


async def save_login():
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=False,
        channel="msedge",
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",  # ← hides Playwright
        ]
    )
    context = await browser.new_context(
        # Pretend to be a real browser
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 720},
    )
    page = await context.new_page()

    # Hide automation flags
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    await page.goto("https://simplify.jobs/auth/login")
    print("\n✅ Browser opened!")
    print("👉 Log in manually in the browser...")
    print("👉 Once logged in, press Enter here.\n")
    input("Press Enter to save session...")

    await context.storage_state(path="session.json")
    print("✅ Session saved!")
    await browser.close()
    await p.stop()


if __name__ == "__main__":
    asyncio.run(save_login())