from typing import List
import aiohttp
import logging
import ssl
import certifi
from ..scraper_engine import BaseScraper, JobData

logger = logging.getLogger("GreenhouseScraper")

PER_PAGE = 100


class GreenhouseScraper(BaseScraper):
    """
    Scraper for Greenhouse-hosted career pages using the public Greenhouse
    Harvest / Job Board API.  No browser required — pure aiohttp.

    API docs: https://developers.greenhouse.io/job-board.html
    Endpoint : GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
    """

    def __init__(self, company_name: str, browser_manager, board_token: str):
        super().__init__(company_name, browser_manager)
        self.board_token = board_token
        self.api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

    async def scrape(self) -> List[JobData]:
        logger.info(f"[{self.company_name}] Starting Greenhouse API scrape...")
        jobs: List[JobData] = []
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())

        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        async with aiohttp.ClientSession() as session:
            page = 1
            while True:
                params = {"per_page": PER_PAGE, "page": page}
                try:
                    async with session.get(
                        self.api_url,
                        params=params,
                        headers=headers,
                        ssl=ssl_ctx,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status != 200:
                            logger.warning(
                                f"[{self.company_name}] API returned status {resp.status}"
                            )
                            break

                        data = await resp.json()
                        postings = data.get("jobs", [])

                        if not postings:
                            break

                        for posting in postings:
                            title = posting.get("title", "")
                            if not self.is_relevant_role(title):
                                continue

                            url = posting.get("absolute_url", "")
                            location_obj = posting.get("location") or {}
                            location = location_obj.get("name")
                            date_posted = posting.get("updated_at") or posting.get(
                                "first_published"
                            )

                            jobs.append(
                                JobData(
                                    title=title,
                                    company=self.company_name,
                                    url=url,
                                    location=location,
                                    date_posted=date_posted,
                                )
                            )

                        # If fewer results than per_page, we've hit the last page
                        if len(postings) < PER_PAGE:
                            break
                        page += 1

                except Exception as e:
                    logger.error(
                        f"[{self.company_name}] Error fetching page {page}: {e}"
                    )
                    break

        logger.info(f"[{self.company_name}] Found {len(jobs)} intern jobs.")
        return jobs


class SpaceXScraper(GreenhouseScraper):
    def __init__(self, browser_manager):
        super().__init__(
            company_name="SpaceX",
            browser_manager=browser_manager,
            board_token="spacex",
        )
