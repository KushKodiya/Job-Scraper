from typing import List
import aiohttp
import logging
import ssl
import certifi
from ..scraper_engine import BaseScraper, JobData

logger = logging.getLogger("WorkdayScraper")

PAGE_SIZE = 20


class WorkdayScraper(BaseScraper):
    """
    Scraper for Workday-hosted career pages using the internal CXS JSON API.
    No browser required — uses aiohttp for direct API calls.
    """

    def __init__(self, company_name: str, browser_manager, host: str, tenant: str,
                 site: str, country_code: str = None):
        super().__init__(company_name, browser_manager)
        self.host = host
        self.tenant = tenant
        self.site = site
        self.country_code = country_code
        self.api_url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        self.job_base_url = f"https://{host}/en-US/{site}"

    async def scrape(self) -> List[JobData]:
        logger.info(f"[{self.company_name}] Starting Workday API scrape...")
        jobs = []
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())

        async with aiohttp.ClientSession() as session:
            offset = 0
            total = None

            while total is None or offset < total:
                facets = {}
                if self.country_code:
                    facets["locationCountry"] = [self.country_code]
                payload = {
                    "appliedFacets": facets,
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "searchText": "intern"
                }
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                }

                try:
                    async with session.post(
                        self.api_url,
                        json=payload,
                        headers=headers,
                        ssl=ssl_ctx,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status != 200:
                            logger.warning(f"[{self.company_name}] API returned status {resp.status}")
                            break

                        data = await resp.json()
                        postings = data.get("jobPostings", [])
                        if total is None:
                            total = data.get("total", 0)
                            logger.info(f"[{self.company_name}] Total jobs found: {total}")

                        if not postings:
                            break

                        for posting in postings:
                            title = posting.get("title", "Unknown Title")
                            if not self.is_relevant_role(title):
                                continue

                            external_path = posting.get("externalPath", "")
                            url = self.job_base_url + external_path if external_path else self.job_base_url
                            location = posting.get("locationsText", "Unknown Location")
                            date_posted = posting.get("postedOn")

                            jobs.append(JobData(
                                title=title,
                                company=self.company_name,
                                url=url,
                                location=location,
                                date_posted=date_posted
                            ))

                        offset += PAGE_SIZE

                except Exception as e:
                    logger.error(f"[{self.company_name}] Error fetching page at offset {offset}: {e}")
                    break

        logger.info(f"[{self.company_name}] Found {len(jobs)} intern jobs.")
        return jobs


class WorkdayPlaywrightScraper(BaseScraper):
    """
    Playwright-based fallback for Workday sites whose CXS API returns 422/403.
    Renders the Workday careers page and extracts job data from the DOM.
    """

    def __init__(self, company_name: str, browser_manager, careers_url: str):
        super().__init__(company_name, browser_manager)
        self.careers_url = careers_url
        # Extract base URL from careers_url for building full links
        from urllib.parse import urlparse
        parsed = urlparse(careers_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

    async def scrape(self) -> List[JobData]:
        import asyncio
        import random
        from bs4 import BeautifulSoup

        logger.info(f"[{self.company_name}] Starting Workday Playwright scrape...")
        jobs: List[JobData] = []
        context = await self.browser_manager.get_new_context()
        page = await context.new_page()

        try:
            await asyncio.sleep(random.uniform(2, 4))
            # Navigate to search URL with intern keyword
            url = self.careers_url
            if "?" in url:
                url += "&q=intern"
            else:
                url += "?q=intern"
            await page.goto(url, timeout=60000, wait_until="networkidle")
            await asyncio.sleep(random.uniform(3, 5))

            # Try to find and use search input if available
            for search_sel in [
                'input[data-automation-id="keywordSearchInput"]',
                'input[aria-label*="Search"]',
                'input[placeholder*="Search"]',
            ]:
                try:
                    search_input = await page.query_selector(search_sel)
                    if search_input:
                        await search_input.fill("intern")
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(random.uniform(3, 5))
                        break
                except Exception:
                    continue

            # Extract jobs from Workday's rendered DOM
            for page_num in range(1, 4):
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                # Workday rendered cards use various selectors
                cards = (
                    soup.select('[data-automation-id="jobResults"] li')
                    or soup.select('ul[role="list"] li[class*="css"]')
                    or soup.select('section[data-automation-id="jobResults"] li')
                )

                if not cards:
                    logger.warning(f"[{self.company_name}] No job cards found on page {page_num}")
                    break

                jobs_before = len(jobs)
                for card in cards:
                    try:
                        link = card.select_one("a[href]")
                        if not link:
                            continue
                        title = link.get_text(strip=True)
                        if not title or not self.is_relevant_role(title):
                            continue
                        href = link.get("href", "")
                        if href.startswith("/"):
                            job_url = self.base_url + href
                        elif href.startswith("http"):
                            job_url = href
                        else:
                            continue

                        # Location is usually in a dd or span after the title
                        loc_el = card.select_one(
                            '[data-automation-id="locations"]'
                        ) or card.select_one("dd")
                        location = loc_el.get_text(strip=True) if loc_el else None

                        date_el = card.select_one('[data-automation-id="postedOn"]')
                        date_posted = date_el.get_text(strip=True) if date_el else None

                        jobs.append(JobData(
                            title=title,
                            company=self.company_name,
                            url=job_url,
                            location=location,
                            date_posted=date_posted,
                        ))
                    except Exception:
                        continue

                if len(jobs) == jobs_before:
                    break

                # Try next page
                try:
                    next_btn = await page.query_selector(
                        'button[data-automation-id="next"], button[aria-label="next"]'
                    )
                    if next_btn:
                        await next_btn.click()
                        await asyncio.sleep(random.uniform(3, 5))
                    else:
                        break
                except Exception:
                    break

        except Exception as e:
            logger.error(f"[{self.company_name}] Scrape error: {e}")
        finally:
            await context.close()

        logger.info(f"[{self.company_name}] Found {len(jobs)} intern jobs.")
        return jobs


class NissanScraper(WorkdayScraper):
    def __init__(self, browser_manager):
        super().__init__(
            company_name="Nissan",
            browser_manager=browser_manager,
            host="alliance.wd3.myworkdayjobs.com",
            tenant="alliance",
            site="nissanjobs",
            country_code="bc33aa3152ec42d4995f4791a106ed09"
        )
