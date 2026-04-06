"""
Scrapers for major tech companies with proprietary/custom career platforms.
"""

from typing import List
import aiohttp
import logging
import ssl
import certifi
from ..scraper_engine import BaseScraper, JobData

logger = logging.getLogger("TechScrapers")


class AmazonScraper(BaseScraper):
    """
    Amazon Jobs uses a JSON API at amazon.jobs/en/search.json.
    No browser required.
    """

    def __init__(self, browser_manager):
        super().__init__("Amazon", browser_manager)
        self.api_url = "https://www.amazon.jobs/en/search.json"

    async def scrape(self) -> List[JobData]:
        logger.info(f"[{self.company_name}] Starting Amazon API scrape...")
        jobs: List[JobData] = []
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())

        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        async with aiohttp.ClientSession() as session:
            offset = 0
            page_size = 100

            while True:
                params = {
                    "base_query": "intern",
                    "loc_query": "United States",
                    "result_limit": page_size,
                    "offset": offset,
                    "country": "USA",
                }

                try:
                    async with session.get(
                        self.api_url,
                        params=params,
                        headers=headers,
                        ssl=ssl_ctx,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status != 200:
                            logger.warning(f"[{self.company_name}] API returned {resp.status}")
                            break

                        data = await resp.json()
                        postings = data.get("jobs", [])

                        if not postings:
                            break

                        for posting in postings:
                            title = posting.get("title", "")
                            if not self.is_relevant_role(title):
                                continue

                            # Filter to US only
                            country = posting.get("country_code", "")
                            if country and country != "USA":
                                continue

                            job_id = posting.get("id_icims", "") or posting.get("id", "")
                            url = f"https://www.amazon.jobs/en/jobs/{job_id}"
                            city = posting.get("city", "")
                            state = posting.get("state", "")
                            location = f"{city}, {state}" if city else state or None
                            date_posted = posting.get("posted_date")

                            jobs.append(
                                JobData(
                                    title=title,
                                    company=self.company_name,
                                    url=url,
                                    location=location,
                                    date_posted=date_posted,
                                    job_id=str(job_id),
                                )
                            )

                        total = data.get("hits", 0)
                        offset += page_size
                        if offset >= total:
                            break

                except Exception as e:
                    logger.error(f"[{self.company_name}] Error at offset {offset}: {e}")
                    break

        logger.info(f"[{self.company_name}] Found {len(jobs)} intern jobs.")
        return jobs
