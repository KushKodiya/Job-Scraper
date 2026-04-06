"""
Generic scraper for Radancy (TalentBrew) career sites.

Radancy powers career pages for ~20+ major companies with a consistent
HTML structure:
  - #search-results-list ul li          -> job cards
  - a.search-results__job-link          -> link to job detail
  - .search-results__job-title          -> title text
  - .search-results__job-info.location  -> location text
  - .search-results__job-info.date      -> posted date

Pagination URL pattern: {base_url}/search-jobs/{keyword}/{site_id}/{page_num}
Some sites omit site_id or use query params instead.
"""

from typing import List, Optional
from bs4 import BeautifulSoup
import asyncio
import random
import logging
from ..scraper_engine import BaseScraper, JobData

logger = logging.getLogger("RadancyScraper")

MAX_PAGES = 5


class RadancyScraper(BaseScraper):
    """
    Generic scraper for Radancy/TalentBrew career pages.

    Parameters
    ----------
    company_name : str
        Display name (e.g. "Lockheed Martin").
    browser_manager : BrowserManager
        Shared Playwright browser manager.
    base_url : str
        Root URL of the career site (e.g. "https://www.lockheedmartinjobs.com").
    search_path : str
        Path appended after base_url for intern search.
        Default: "/search-jobs/internship"
    site_id : str | None
        Optional Radancy site ID injected into the pagination URL.
        Pattern: /search-jobs/{keyword}/{site_id}/{page}
    """

    def __init__(
        self,
        company_name: str,
        browser_manager,
        base_url: str,
        search_path: str = "/search-jobs/internship",
        site_id: Optional[str] = None,
    ):
        super().__init__(company_name, browser_manager)
        self.base_url = base_url.rstrip("/")
        self.search_path = search_path
        self.site_id = site_id

    def _build_page_url(self, page_num: int) -> str:
        # Page 1 = no suffix (avoids the number being misinterpreted as a site filter)
        if page_num == 1:
            if self.site_id:
                return f"{self.base_url}{self.search_path}/{self.site_id}"
            return f"{self.base_url}{self.search_path}"
        if self.site_id:
            return f"{self.base_url}{self.search_path}/{self.site_id}/{page_num}"
        return f"{self.base_url}{self.search_path}/{page_num}"

    async def scrape(self) -> List[JobData]:
        logger.info(f"[{self.company_name}] Starting Radancy scrape...")
        jobs: List[JobData] = []

        context = await self.browser_manager.get_new_context()
        page = await context.new_page()

        try:
            for page_num in range(1, MAX_PAGES + 1):
                url = self._build_page_url(page_num)
                logger.info(f"[{self.company_name}] Scraping page {page_num}: {url}")

                await asyncio.sleep(random.uniform(2, 4))
                await page.goto(url, timeout=60000)
                await asyncio.sleep(2)

                # Dismiss cookie/privacy banners that block content
                if page_num == 1:
                    for cookie_sel in [
                        'button:has-text("Accept all")',
                        'button:has-text("Accept All")',
                        'button:has-text("Accept")',
                        'button:has-text("Allow")',
                        'button:has-text("I agree")',
                        'button:has-text("Got it")',
                        '[id*="cookie"] button',
                        '[class*="cookie"] button',
                        '[id*="consent"] button',
                        'button[id*="accept"]',
                    ]:
                        try:
                            await page.click(cookie_sel, timeout=2000)
                            await asyncio.sleep(1)
                            break
                        except Exception:
                            pass

                try:
                    await page.wait_for_selector(
                        "#search-results-list, a[href*='/job/']", timeout=20000
                    )
                except Exception:
                    logger.warning(
                        f"[{self.company_name}] No results container on page {page_num}"
                    )
                    break

                content = await page.content()
                jobs_before = len(jobs)
                self._extract_jobs(content, jobs)

                if len(jobs) == jobs_before:
                    logger.info(
                        f"[{self.company_name}] No new jobs on page {page_num} — stopping"
                    )
                    break

        except Exception as e:
            logger.error(f"[{self.company_name}] Scrape error: {e}")
        finally:
            await context.close()

        logger.info(f"[{self.company_name}] Found {len(jobs)} intern jobs.")
        return jobs

    def _extract_jobs(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, "html.parser")
        results = soup.select("#search-results-list ul li")

        # Fallback: if no standard Radancy container, find job links directly
        if not results:
            seen_urls = {j.url for j in jobs_list}
            links = soup.select('a[href*="/job/"]')
            for link in links:
                try:
                    href = link.get("href", "")
                    if href.startswith("/"):
                        url = self.base_url + href
                    elif href.startswith("http"):
                        url = href
                    else:
                        continue
                    if url in seen_urls:
                        continue
                    title = link.get_text(strip=True)
                    if not title or not self.is_relevant_role(title):
                        continue
                    # Look for location in sibling/parent elements
                    parent = link.find_parent("tr") or link.find_parent("li") or link.find_parent("div")
                    location = None
                    if parent:
                        loc_el = (
                            parent.select_one("[class*='location'], [class*='Location']")
                            or parent.select_one("td:nth-of-type(2)")
                        )
                        if loc_el:
                            location = loc_el.get_text(strip=True)
                    seen_urls.add(url)
                    jobs_list.append(
                        JobData(
                            title=title,
                            company=self.company_name,
                            url=url,
                            location=location,
                        )
                    )
                except Exception:
                    continue
            return

        for li in results:
            try:
                # Radancy has two template variants:
                # Variant A (Boeing-style):  a.search-results__job-link > .search-results__job-title
                # Variant B (Lockheed-style): a[data-job-id] > .job-title
                link_elem = (
                    li.select_one("a.search-results__job-link")
                    or li.select_one("a[data-job-id]")
                    or li.select_one("a[href*='/job/']")
                )
                if not link_elem:
                    continue

                title_elem = (
                    link_elem.select_one(".search-results__job-title")
                    or link_elem.select_one(".job-title")
                )
                title = (
                    title_elem.get_text(strip=True) if title_elem else link_elem.get_text(strip=True)
                )

                if not title or not self.is_relevant_role(title):
                    continue

                href = link_elem.get("href", "")
                if href.startswith("/"):
                    url = self.base_url + href
                elif href.startswith("http"):
                    url = href
                else:
                    continue

                loc_elem = (
                    li.select_one(".search-results__job-info.location")
                    or li.select_one(".job-location")
                )
                location = (
                    loc_elem.get_text(strip=True) if loc_elem else None
                )

                date_elem = (
                    li.select_one(".search-results__job-info.date")
                    or li.select_one(".job-date-posted")
                )
                date_posted = (
                    date_elem.get_text(strip=True) if date_elem else None
                )
                # Strip common prefix like "Date Posted: "
                if date_posted and ":" in date_posted:
                    date_posted = date_posted.split(":", 1)[1].strip()

                jobs_list.append(
                    JobData(
                        title=title,
                        company=self.company_name,
                        url=url,
                        location=location,
                        date_posted=date_posted,
                    )
                )
            except Exception as e:
                logger.debug(f"[{self.company_name}] Error parsing card: {e}")
                continue
