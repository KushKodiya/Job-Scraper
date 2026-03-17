from typing import List, Optional
from bs4 import BeautifulSoup
import asyncio
import logging
from ..scraper_engine import BaseScraper, JobData

logger = logging.getLogger("PhenomScraper")

MAX_PAGES = 3
CARD_SELECTOR = '[data-ph-at-id="jobs-list-item"]'
LINK_SELECTOR = '[data-ph-at-id="job-link"]'


class PhenomScraper(BaseScraper):
    """
    Scraper for Phenom People career platform (Toyota, Honda, Ford).
    Uses Playwright since the page is JavaScript-rendered.

    Data is extracted from data-ph-at-* HTML attributes on the job link element,
    which Phenom People populates with clean structured data.
    """

    def __init__(self, company_name: str, browser_manager, search_url: str,
                 base_url: Optional[str] = None):
        super().__init__(company_name, browser_manager)
        self.search_url = search_url
        self.base_url = base_url or ""

    async def scrape(self) -> List[JobData]:
        logger.info(f"[{self.company_name}] Starting Phenom People scrape...")
        jobs = []

        context = await self.browser_manager.get_new_context()
        page = await context.new_page()

        try:
            await page.goto(self.search_url, timeout=60000)
            await asyncio.sleep(3)

            # Dismiss cookie banner if present
            for cookie_sel in [
                '[data-ph-at-id="cookie-close-link"]',
                'button:has-text("Accept")',
                'button:has-text("Allow")',
                '[class*="cookie"] button',
            ]:
                try:
                    await page.click(cookie_sel, timeout=2000)
                    await asyncio.sleep(1)
                    break
                except Exception:
                    pass

            for page_num in range(1, MAX_PAGES + 1):
                logger.info(f"[{self.company_name}] Scraping page {page_num}...")

                try:
                    await page.wait_for_selector(CARD_SELECTOR, timeout=15000)
                except Exception:
                    logger.warning(f"[{self.company_name}] No job cards found on page {page_num}")
                    break

                content = await page.content()
                jobs_before = len(jobs)
                self._extract_jobs(content, jobs)

                if len(jobs) == jobs_before:
                    logger.info(f"[{self.company_name}] No new jobs on page {page_num} — stopping")
                    break

                if page_num < MAX_PAGES:
                    advanced = await self._go_to_next_page(page)
                    if not advanced:
                        break
                    await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"[{self.company_name}] Scrape error: {e}")
        finally:
            await context.close()

        logger.info(f"[{self.company_name}] Found {len(jobs)} intern jobs.")
        return jobs

    async def _go_to_next_page(self, page) -> bool:
        for selector in [
            '[data-ph-at-id="pagination-next-link"]',
            'button[aria-label="Next page"]',
            'a[aria-label="Next"]',
            '.pagination-next',
        ]:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    disabled = await btn.get_attribute("disabled")
                    aria_disabled = await btn.get_attribute("aria-disabled")
                    if disabled or aria_disabled == "true":
                        return False
                    await btn.click()
                    return True
            except Exception:
                continue
        return False

    def _extract_jobs(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select(CARD_SELECTOR)

        if not cards:
            logger.warning(f"[{self.company_name}] Could not find job cards in HTML")
            return

        for card in cards:
            try:
                # All structured data lives on the job-link anchor as data-ph-at-* attributes
                link_el = card.select_one(LINK_SELECTOR)
                if not link_el:
                    continue

                title = link_el.get("data-ph-at-job-title-text") or link_el.get_text(strip=True)
                if not title or not self.is_relevant_role(title):
                    continue

                href = link_el.get("href", "")
                if href.startswith("http"):
                    url = href
                elif href.startswith("/"):
                    url = self.base_url + href
                else:
                    url = self.search_url

                location = (
                    link_el.get("data-ph-at-job-location-area-text") or
                    link_el.get("data-ph-at-job-location-text") or
                    "Unknown Location"
                )

                date_posted = link_el.get("data-ph-at-job-post-date-text")

                jobs_list.append(JobData(
                    title=title,
                    company=self.company_name,
                    url=url,
                    location=location,
                    date_posted=date_posted
                ))

            except Exception as e:
                logger.debug(f"[{self.company_name}] Error parsing card: {e}")
                continue
