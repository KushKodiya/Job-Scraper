import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from fake_useragent import UserAgent
import logging

class BrowserManager:
    def __init__(self, headless=True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.ua = UserAgent()
        self.logger = logging.getLogger("BrowserManager")

    async def init(self):
        """Initialize the Playwright browser instance."""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled'] # Stealth feature
            )
            self.logger.info("Browser initialized.")

    async def get_new_context(self) -> BrowserContext:
        """Create a new browser context with a random user agent."""
        if not self.browser:
            await self.init()
            
        user_agent = self.ua.random
        context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        
        # Add init scripts to evade detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return context

    async def close(self):
        """Close the browser and playwright."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.logger.info("Browser closed.")
