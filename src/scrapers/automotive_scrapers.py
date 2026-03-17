"""
Automotive company scrapers for:
  - Tesla         (internal REST API via aiohttp)
  - VW Group      (Playwright)
  - Stellantis    (Playwright — Phenom People platform)
  - BMW Group     (Playwright)
  - Mercedes-Benz (Playwright)
  - Volvo Group   (Playwright)
  - Hyundai USA   (Playwright — follows redirect to ATS)
  - Subaru        (Playwright — follows redirect to ATS)
"""

from typing import List
from bs4 import BeautifulSoup
import aiohttp
import asyncio
import ssl
import certifi
import logging
from ..scraper_engine import BaseScraper, JobData

logger = logging.getLogger("AutomotiveScrapers")

MAX_PAGES = 3


# ---------------------------------------------------------------------------
# Tesla — REST API
# ---------------------------------------------------------------------------

class TeslaScraper(BaseScraper):
    """Tesla careers via their internal CUA API. No browser required."""

    API_URL = "https://www.tesla.com/cua-api/tesla-jobs"
    PAGE_SIZE = 20

    def __init__(self, browser_manager):
        super().__init__("Tesla", browser_manager)

    async def scrape(self) -> List[JobData]:
        logger.info("[Tesla] Starting API scrape...")
        jobs = []
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())

        async with aiohttp.ClientSession() as session:
            offset = 0
            total = None

            while total is None or offset < total:
                params = {
                    "query": "intern",
                    "site": "US",
                    "lng": "en_US",
                    "offset": offset,
                    "count": self.PAGE_SIZE,
                }
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "application/json",
                }

                try:
                    async with session.get(
                        self.API_URL,
                        params=params,
                        headers=headers,
                        ssl=ssl_ctx,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status != 200:
                            logger.warning(f"[Tesla] API returned status {resp.status}")
                            break

                        data = await resp.json(content_type=None)

                        # Response shape: {"results": [...], "totalCount": N}
                        result_list = data.get("results", [])
                        if total is None:
                            total = data.get("totalCount", 0)
                            logger.info(f"[Tesla] Total jobs: {total}")

                        if not result_list:
                            break

                        for job in result_list:
                            title = job.get("title", "Unknown Title")
                            if not self.is_relevant_role(title):
                                continue

                            job_id = job.get("id", "")
                            url = f"https://www.tesla.com/careers/search/job/{job_id}" if job_id else "https://www.tesla.com/careers/search"

                            city = job.get("city", "")
                            state = job.get("state", "")
                            location = f"{city}, {state}".strip(", ") if city or state else "Unknown Location"

                            # date_posted may be ISO 8601 string
                            date_posted = job.get("date_posted") or job.get("postedDate") or job.get("updated_at")

                            jobs.append(JobData(
                                title=title,
                                company=self.company_name,
                                url=url,
                                location=location,
                                date_posted=str(date_posted) if date_posted else None
                            ))

                        offset += self.PAGE_SIZE

                except Exception as e:
                    logger.error(f"[Tesla] Error at offset {offset}: {e}")
                    break

        logger.info(f"[Tesla] Found {len(jobs)} intern jobs.")
        return jobs


# ---------------------------------------------------------------------------
# Generic Playwright helper — reused by VW, BMW, Mercedes, Volvo, Hyundai, Subaru
# ---------------------------------------------------------------------------

class _PlaywrightScraper(BaseScraper):
    """
    Base Playwright scraper for company career pages that don't have a known API.
    Subclasses define search_url, base_url, and card/title/location/date selectors.
    """

    search_url: str = ""
    base_url: str = ""
    card_selectors: List[str] = []
    title_selectors: List[str] = []
    location_selectors: List[str] = []
    date_selectors: List[str] = []
    next_page_selectors: List[str] = []

    async def scrape(self) -> List[JobData]:
        logger.info(f"[{self.company_name}] Starting Playwright scrape...")
        jobs = []

        context = await self.browser_manager.get_new_context()
        page = await context.new_page()

        try:
            await page.goto(self.search_url, timeout=60000, wait_until="networkidle")
            await asyncio.sleep(3)

            for page_num in range(1, MAX_PAGES + 1):
                logger.info(f"[{self.company_name}] Scraping page {page_num}...")

                # Wait for job cards
                loaded = False
                for selector in self.card_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=10000)
                        loaded = True
                        break
                    except Exception:
                        continue

                if not loaded:
                    logger.warning(f"[{self.company_name}] No job cards on page {page_num}")
                    break

                content = await page.content()
                jobs_before = len(jobs)
                self._extract_jobs(content, jobs)

                if len(jobs) == jobs_before:
                    logger.info(f"[{self.company_name}] No new jobs on page {page_num} — stopping")
                    break

                if page_num < MAX_PAGES:
                    advanced = await self._next_page(page)
                    if not advanced:
                        break
                    await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"[{self.company_name}] Scrape error: {e}")
        finally:
            await context.close()

        logger.info(f"[{self.company_name}] Found {len(jobs)} intern jobs.")
        return jobs

    async def _next_page(self, page) -> bool:
        for selector in self.next_page_selectors:
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

        cards = []
        for sel in self.card_selectors:
            cards = soup.select(sel)
            if cards:
                break

        if not cards:
            logger.warning(f"[{self.company_name}] No cards found in HTML")
            return

        for card in cards:
            try:
                title_elem = None
                for sel in self.title_selectors:
                    title_elem = card.select_one(sel)
                    if title_elem:
                        break

                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                if not title or not self.is_relevant_role(title):
                    continue

                # URL: prefer the title link, otherwise first <a> in card
                link_elem = title_elem if title_elem.name == 'a' else card.select_one('a')
                href = link_elem.get('href', '') if link_elem else ''
                if href.startswith('/'):
                    url = self.base_url + href
                elif href.startswith('http'):
                    url = href
                else:
                    url = self.search_url

                loc_elem = None
                for sel in self.location_selectors:
                    loc_elem = card.select_one(sel)
                    if loc_elem:
                        break
                location = loc_elem.get_text(strip=True) if loc_elem else "Unknown Location"

                date_elem = None
                for sel in self.date_selectors:
                    date_elem = card.select_one(sel)
                    if date_elem:
                        break
                date_posted = date_elem.get_text(strip=True) if date_elem else None

                jobs_list.append(JobData(
                    title=title,
                    company=self.company_name,
                    url=url,
                    location=location,
                    date_posted=date_posted
                ))

            except Exception as e:
                logger.debug(f"[{self.company_name}] Card parse error: {e}")
                continue


# ---------------------------------------------------------------------------
# Stellantis — no working search URL found; returns 0 gracefully
# ---------------------------------------------------------------------------

class StellantisScraper(BaseScraper):
    def __init__(self, browser_manager):
        super().__init__("Stellantis", browser_manager)

    async def scrape(self):
        logger.info("[Stellantis] No working search URL found — skipping")
        return []


# ---------------------------------------------------------------------------
# VG Job Board base — used by VW Group, Volvo Group, Hyundai
# These portals all use the same table-based job listing format (tr.data-row).
# ---------------------------------------------------------------------------

class _VGJobBoardScraper(BaseScraper):
    """
    Scraper for VG-style job portals (jobs.volkswagen-group.com,
    jobs.volvogroup.com, careers-americas.hyundai.com).
    All use the same table-row layout: tr.data-row with a.jobTitle-link.
    """

    search_url: str = ""
    base_url: str = ""
    us_only: bool = True  # filter results to US locations only

    async def scrape(self) -> List[JobData]:
        logger.info(f"[{self.company_name}] Starting VG board scrape...")
        jobs = []

        context = await self.browser_manager.get_new_context()
        page = await context.new_page()

        try:
            for page_num in range(1, MAX_PAGES + 1):
                url = self.search_url if page_num == 1 else f"{self.search_url}&pg={page_num}"
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(4)

                try:
                    await page.wait_for_selector('tr.data-row', timeout=15000)
                except Exception:
                    logger.warning(f"[{self.company_name}] No job rows on page {page_num}")
                    break

                content = await page.content()
                jobs_before = len(jobs)
                self._extract_jobs(content, jobs)

                if len(jobs) == jobs_before:
                    logger.info(f"[{self.company_name}] No new jobs on page {page_num} — stopping")
                    break

        except Exception as e:
            logger.error(f"[{self.company_name}] Scrape error: {e}")
        finally:
            await context.close()

        logger.info(f"[{self.company_name}] Found {len(jobs)} intern jobs.")
        return jobs

    def _extract_jobs(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.select('tr.data-row')

        for row in rows:
            try:
                title_el = row.select_one('a.jobTitle-link')
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                if not title or not self.is_relevant_role(title):
                    continue

                href = title_el.get('href', '')
                url = self.base_url + href if href.startswith('/') else href

                # Location lives in a span or td with class containing "jobLocation"
                loc_el = row.select_one('.jobLocation, .colLocation, [class*="jobLocation"]')
                location = loc_el.get_text(strip=True) if loc_el else "Unknown Location"

                # Filter to US jobs only (location format: "City, ST, US, PostalCode")
                if self.us_only and ', US,' not in location and not location.strip().endswith(', US'):
                    continue

                date_el = row.select_one('.jobDate, .colDate, [class*="jobDate"]')
                date_posted = date_el.get_text(strip=True) if date_el else None

                jobs_list.append(JobData(
                    title=title,
                    company=self.company_name,
                    url=url,
                    location=location,
                    date_posted=date_posted
                ))

            except Exception as e:
                logger.debug(f"[{self.company_name}] Row parse error: {e}")
                continue


# ---------------------------------------------------------------------------
# VW Group
# ---------------------------------------------------------------------------

class VWGroupScraper(_VGJobBoardScraper):
    search_url = "https://jobs.volkswagen-group.com/search/?searchby=location&q=intern&locationsearch=United+States"
    base_url = "https://jobs.volkswagen-group.com"
    us_only = True

    def __init__(self, browser_manager):
        super().__init__("VW Group", browser_manager)


# ---------------------------------------------------------------------------
# BMW Group — no working US search URL found; returns 0 gracefully
# ---------------------------------------------------------------------------

class BMWScraper(BaseScraper):
    def __init__(self, browser_manager):
        super().__init__("BMW Group", browser_manager)

    async def scrape(self):
        logger.info("[BMW Group] No working US search URL found — skipping")
        return []


# ---------------------------------------------------------------------------
# Mercedes-Benz — site returns 403; returns 0 gracefully
# ---------------------------------------------------------------------------

class MercedesScraper(BaseScraper):
    def __init__(self, browser_manager):
        super().__init__("Mercedes-Benz", browser_manager)

    async def scrape(self):
        logger.info("[Mercedes-Benz] Site blocked (403) — skipping")
        return []


# ---------------------------------------------------------------------------
# Volvo Group — uses jobs.volvogroup.com (VG job board format)
# ---------------------------------------------------------------------------

class VolvoScraper(_VGJobBoardScraper):
    search_url = "https://jobs.volvogroup.com/search/?searchby=location&q=intern&locationsearch=United+States"
    base_url = "https://jobs.volvogroup.com"
    us_only = False  # locationsearch parameter already scopes to US

    def __init__(self, browser_manager):
        super().__init__("Volvo Group", browser_manager)


# ---------------------------------------------------------------------------
# Hyundai Motor America — uses careers-americas.hyundai.com (VG job board format)
# ---------------------------------------------------------------------------

class HyundaiScraper(_VGJobBoardScraper):
    search_url = "https://careers-americas.hyundai.com/hma/search?q=intern"
    base_url = "https://careers-americas.hyundai.com"
    us_only = False  # This portal is already US-specific

    def __init__(self, browser_manager):
        super().__init__("Hyundai", browser_manager)


# ---------------------------------------------------------------------------
# Subaru — no ATS link found on careers page; returns 0 gracefully
# ---------------------------------------------------------------------------

class SubaruScraper(BaseScraper):
    def __init__(self, browser_manager):
        super().__init__("Subaru", browser_manager)

    async def scrape(self):
        logger.info("[Subaru] No accessible ATS URL found — skipping")
        return []
