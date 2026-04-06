"""
Generic Playwright-based scraper for career sites that have no accessible API.

Works by:
1. Navigating to a search URL with intern/internship keywords
2. Waiting for job cards to render
3. Extracting titles, URLs, locations from rendered DOM using multiple
   selector strategies

This is a fallback scraper for sites like Google, Microsoft, Apple, Meta,
Goldman Sachs, and other custom career platforms.
"""

from typing import List, Optional
from bs4 import BeautifulSoup
import asyncio
import random
import logging
from ..scraper_engine import BaseScraper, JobData

logger = logging.getLogger("GenericPlaywrightScraper")

MAX_PAGES = 3


class GenericPlaywrightScraper(BaseScraper):
    """
    Playwright-based scraper that works on most JS-rendered career pages.

    Parameters
    ----------
    company_name : str
    browser_manager : BrowserManager
    search_url : str
        Full URL with intern/internship search already applied.
    base_url : str
        Root domain for building absolute URLs from relative hrefs.
    card_selector : str | None
        Optional CSS selector for job card containers.
        If None, auto-detection is used.
    title_selector : str | None
        Optional CSS selector for the title element within a card.
    location_selector : str | None
        Optional CSS selector for the location element within a card.
    next_selector : str | None
        Optional CSS selector for the "next page" button.
    """

    def __init__(
        self,
        company_name: str,
        browser_manager,
        search_url: str,
        base_url: str,
        card_selector: Optional[str] = None,
        title_selector: Optional[str] = None,
        location_selector: Optional[str] = None,
        next_selector: Optional[str] = None,
    ):
        super().__init__(company_name, browser_manager)
        self.search_url = search_url
        self.base_url = base_url.rstrip("/")
        self.card_selector = card_selector
        self.title_selector = title_selector
        self.location_selector = location_selector
        self.next_selector = next_selector

    async def scrape(self) -> List[JobData]:
        logger.info(f"[{self.company_name}] Starting Playwright scrape...")
        jobs: List[JobData] = []

        context = await self.browser_manager.get_new_context()
        page = await context.new_page()

        try:
            await asyncio.sleep(random.uniform(2, 4))
            await page.goto(self.search_url, timeout=60000)
            await asyncio.sleep(random.uniform(4, 6))

            # Dismiss cookie/privacy banners
            for sel in [
                'button:has-text("Accept")',
                'button:has-text("Allow")',
                'button:has-text("Got it")',
                'button:has-text("I agree")',
                '[class*="cookie"] button',
                'button[id*="cookie"]',
            ]:
                try:
                    await page.click(sel, timeout=2000)
                    await asyncio.sleep(1)
                    break
                except Exception:
                    pass

            for page_num in range(1, MAX_PAGES + 1):
                logger.info(f"[{self.company_name}] Processing page {page_num}...")
                content = await page.content()
                jobs_before = len(jobs)
                self._extract_jobs(content, jobs)

                if len(jobs) == jobs_before:
                    logger.info(
                        f"[{self.company_name}] No new jobs on page {page_num} — stopping"
                    )
                    break

                if page_num < MAX_PAGES:
                    advanced = await self._go_next(page)
                    if not advanced:
                        break
                    await asyncio.sleep(random.uniform(3, 5))

        except Exception as e:
            logger.error(f"[{self.company_name}] Scrape error: {e}")
        finally:
            await context.close()

        logger.info(f"[{self.company_name}] Found {len(jobs)} intern jobs.")
        return jobs

    async def _go_next(self, page) -> bool:
        """Try to advance to the next page of results."""
        selectors = [self.next_selector] if self.next_selector else []
        selectors += [
            'button:has-text("Next")',
            'a:has-text("Next")',
            'button[aria-label="Next"]',
            'a[aria-label="Next"]',
            'button:has-text("Show more")',
            'button:has-text("Load more")',
            'button:has-text("View more")',
        ]

        for sel in selectors:
            if not sel:
                continue
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(random.uniform(3, 5))
                    return True
            except Exception:
                continue

        # Try infinite scroll
        try:
            prev_h = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(3)
            new_h = await page.evaluate("document.body.scrollHeight")
            if new_h > prev_h:
                return True
        except Exception:
            pass

        return False

    def _extract_jobs(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, "html.parser")
        seen_urls = {j.url for j in jobs_list}

        # Find job cards
        cards = []
        if self.card_selector:
            cards = soup.select(self.card_selector)

        if not cards:
            # Auto-detect: look for links containing job-related paths
            for pattern in [
                'a[href*="/job/"]',
                'a[href*="/jobs/"]',
                'a[href*="/role/"]',
                'a[href*="/roles/"]',
                'a[href*="/position/"]',
                'a[href*="/positions/"]',
                'a[href*="/requisition"]',
                'a[href*="/posting/"]',
                'a[href*="/opportunity/"]',
            ]:
                links = soup.select(pattern)
                if links:
                    for link in links:
                        self._parse_link(link, jobs_list, seen_urls)
                    return

        for card in cards:
            link = card.select_one("a[href]")
            if not link:
                # Maybe the card itself is a link
                if card.name == "a" and card.get("href"):
                    link = card
                else:
                    continue
            self._parse_link(link, jobs_list, seen_urls, card)

    def _parse_link(self, link, jobs_list, seen_urls, card=None):
        href = link.get("href", "")
        if href.startswith("/"):
            url = self.base_url + href
        elif href.startswith("http"):
            url = href
        else:
            return

        if url in seen_urls:
            return

        container = card if card else link

        # Title
        if self.title_selector:
            t_el = container.select_one(self.title_selector)
            title = t_el.get_text(strip=True) if t_el else ""
        else:
            t_el = container.select_one(
                "h2, h3, h4, [class*='title'], [class*='Title'], [data-testid*='title']"
            )
            title = t_el.get_text(strip=True) if t_el else link.get_text(strip=True)

        if not title or not self.is_relevant_role(title):
            return

        # Location
        if self.location_selector:
            l_el = container.select_one(self.location_selector)
            location = l_el.get_text(strip=True) if l_el else None
        else:
            l_el = container.select_one(
                "[class*='location'], [class*='Location'], [data-testid*='location']"
            )
            location = l_el.get_text(strip=True) if l_el else None

        seen_urls.add(url)
        jobs_list.append(
            JobData(
                title=title,
                company=self.company_name,
                url=url,
                location=location,
            )
        )
