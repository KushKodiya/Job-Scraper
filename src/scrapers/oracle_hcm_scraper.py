"""
Generic scraper for Oracle HCM Cloud (Fusion) career sites.

Oracle HCM exposes a REST API at:
  GET /hcmRestApi/resources/latest/recruitingCEJobRequisitions
    ?finder=findReqs;siteNumber={site},keyword={kw}
    &expand=requisitionList
    &onlyData=true
    &limit={n}&offset={o}

No browser required — pure aiohttp.
"""

from typing import List
import aiohttp
import logging
import ssl
import certifi
from ..scraper_engine import BaseScraper, JobData

logger = logging.getLogger("OracleHCMScraper")

PAGE_SIZE = 25


class OracleHCMScraper(BaseScraper):
    """
    Scraper for Oracle HCM Cloud career pages.

    Parameters
    ----------
    company_name : str
    browser_manager : BrowserManager
    host : str
        Oracle HCM hostname (e.g. "hdjq.fa.us2.oraclecloud.com").
    site_number : str
        Site identifier (e.g. "CX_1").
    portal_url : str
        Base URL for building job detail links.
        e.g. "https://hdjq.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1"
    """

    def __init__(
        self,
        company_name: str,
        browser_manager,
        host: str,
        site_number: str,
        portal_url: str,
    ):
        super().__init__(company_name, browser_manager)
        self.host = host
        self.site_number = site_number
        self.portal_url = portal_url.rstrip("/")
        self.api_base = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"

    async def scrape(self) -> List[JobData]:
        logger.info(f"[{self.company_name}] Starting Oracle HCM API scrape...")
        jobs: List[JobData] = []
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())

        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        async with aiohttp.ClientSession() as session:
            offset = 0
            total = None

            while total is None or offset < total:
                params = {
                    "finder": f"findReqs;siteNumber={self.site_number},keyword=intern",
                    "expand": "requisitionList",
                    "onlyData": "true",
                    "limit": PAGE_SIZE,
                    "offset": offset,
                }

                try:
                    async with session.get(
                        self.api_base,
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
                        items = data.get("items", [])
                        if not items:
                            break

                        search_meta = items[0]
                        if total is None:
                            total = search_meta.get("TotalJobsCount", 0)
                            logger.info(
                                f"[{self.company_name}] Total jobs found: {total}"
                            )

                        req_list = search_meta.get("requisitionList", [])
                        if not req_list:
                            break

                        for posting in req_list:
                            title = posting.get("Title", "")
                            if not self.is_relevant_role(title):
                                continue

                            # Filter to US jobs only
                            country = posting.get("PrimaryLocationCountry", "")
                            if country and country != "US":
                                continue

                            job_id = posting.get("Id", "")
                            url = f"{self.portal_url}/requisitions/{job_id}"
                            location = posting.get("PrimaryLocation")
                            date_posted = posting.get("PostedDate")

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

                        offset += PAGE_SIZE

                except Exception as e:
                    logger.error(
                        f"[{self.company_name}] Error at offset {offset}: {e}"
                    )
                    break

        logger.info(f"[{self.company_name}] Found {len(jobs)} intern jobs.")
        return jobs
