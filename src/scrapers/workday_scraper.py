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
                 site: str, country_code: str):
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
                payload = {
                    "appliedFacets": {
                        "locationCountry": [self.country_code]
                    },
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
