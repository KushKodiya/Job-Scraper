"""
Generic scraper for Eightfold.ai career sites.

Eightfold powers career pages for companies like Eaton, Siemens, PepsiCo,
Nestlé, Cisco, ServiceNow, and Wells Fargo.  The platform is a React SPA
that renders job cards dynamically — requires Playwright.

Common selectors (may vary slightly per tenant):
  - [data-test-id="position-card"]  or .position-card  -> job card
  - a with href containing /positions/ -> job detail link
  - Title in h3 or [data-test-id="position-title"]
  - Location in span or [data-test-id="position-location"]
"""

from typing import List, Optional
from bs4 import BeautifulSoup
import asyncio
import random
import logging
from ..scraper_engine import BaseScraper, JobData

logger = logging.getLogger("EightfoldScraper")

MAX_PAGES = 3


class EightfoldScraper(BaseScraper):
    """
    Playwright-based scraper for Eightfold.ai career sites.

    Parameters
    ----------
    company_name : str
    browser_manager : BrowserManager
    careers_url : str
        Full URL to the career search page with intern query.
        e.g. "https://eaton.eightfold.ai/careers?query=intern&location=United%20States"
    base_url : str
        Root domain for building absolute URLs.
        e.g. "https://eaton.eightfold.ai"
    """

    def __init__(
        self,
        company_name: str,
        browser_manager,
        careers_url: str,
        base_url: str,
    ):
        super().__init__(company_name, browser_manager)
        self.careers_url = careers_url
        self.base_url = base_url.rstrip("/")

    async def scrape(self) -> List[JobData]:
        logger.info(f"[{self.company_name}] Starting Eightfold scrape...")
        jobs: List[JobData] = []

        context = await self.browser_manager.get_new_context()
        page = await context.new_page()

        try:
            await asyncio.sleep(random.uniform(2, 4))
            await page.goto(self.careers_url, timeout=60000)

            # Wait for job cards to render — try multiple selectors
            card_selector = None
            for sel in [
                '[data-test-id="job-listing"]',
                'div[data-test-id="position-card"]',
                "div.position-card",
                'a[href*="/careers/job/"]',
                'a[href*="/position/"]',
                'a[href*="/positions/"]',
                '[class*="PositionCard"]',
                'div[role="listitem"]',
            ]:
                try:
                    await page.wait_for_selector(sel, timeout=10000)
                    card_selector = sel
                    logger.info(
                        f"[{self.company_name}] Found cards with selector: {sel}"
                    )
                    break
                except Exception:
                    continue

            if not card_selector:
                logger.warning(
                    f"[{self.company_name}] Could not find job cards on page"
                )
                return jobs

            # Allow full load
            await asyncio.sleep(random.uniform(2, 3))

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
                    advanced = await self._load_more(page)
                    if not advanced:
                        break
                    await asyncio.sleep(random.uniform(2, 3))

        except Exception as e:
            logger.error(f"[{self.company_name}] Scrape error: {e}")
        finally:
            await context.close()

        logger.info(f"[{self.company_name}] Found {len(jobs)} intern jobs.")
        return jobs

    async def _load_more(self, page) -> bool:
        """Try to click 'Load More' / 'Show More' or next page button."""
        for selector in [
            'button:has-text("Load more")',
            'button:has-text("Show more")',
            'button:has-text("View more")',
            'button[data-test-id="load-more"]',
            'a:has-text("Next")',
            'button:has-text("Next")',
        ]:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    visible = await btn.is_visible()
                    if visible:
                        await btn.click()
                        await asyncio.sleep(random.uniform(2, 3))
                        return True
            except Exception:
                continue

        # Try scrolling to bottom to trigger infinite scroll
        try:
            prev_height = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height > prev_height:
                return True
        except Exception:
            pass

        return False

    def _extract_jobs(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, "html.parser")
        seen_urls = {j.url for j in jobs_list}

        # Try multiple card selectors
        cards = (
            soup.select('[data-test-id="job-listing"]')
            or soup.select('div[data-test-id="position-card"]')
            or soup.select("div.position-card")
            or soup.select('[class*="PositionCard"]')
        )

        # Fallback: find all links to job/position pages
        if not cards:
            links = (
                soup.select('a[href*="/careers/job/"]')
                or soup.select('a[href*="/position/"]')
                or soup.select('a[href*="/positions/"]')
            )
            for link in links:
                self._parse_link_card(link, jobs_list, seen_urls)
            return

        for card in cards:
            try:
                # Find the job link
                link = (
                    card.select_one('a[href*="/careers/job/"]')
                    or card.select_one('a[href*="/position/"]')
                    or card.select_one('a[href*="/positions/"]')
                )

                if not link:
                    link = card.select_one("a[href]")

                if not link:
                    continue

                self._parse_link_card(link, jobs_list, seen_urls, card)

            except Exception as e:
                logger.debug(f"[{self.company_name}] Error parsing card: {e}")
                continue

    def _parse_link_card(
        self,
        link,
        jobs_list: List[JobData],
        seen_urls: set,
        card=None,
    ):
        """Extract job data from a link element, optionally within a card container."""
        href = link.get("href", "")
        if href.startswith("/"):
            url = self.base_url + href
        elif href.startswith("http"):
            url = href
        else:
            return

        if url in seen_urls:
            return

        # Title: try card heading, link text, or aria-label
        container = card if card else link
        title_elem = container.select_one(
            '[class*="title-"], h3, h4, [data-test-id="position-title"], [class*="title"]'
        )
        title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)

        if not title or not self.is_relevant_role(title):
            return

        # Location
        loc_elem = container.select_one(
            '[data-test-id="position-location"], [class*="location"], span.subtitle'
        )
        location = loc_elem.get_text(strip=True) if loc_elem else None

        seen_urls.add(url)
        jobs_list.append(
            JobData(
                title=title,
                company=self.company_name,
                url=url,
                location=location,
            )
        )
