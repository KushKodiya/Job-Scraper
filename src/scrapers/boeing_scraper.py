from typing import List
from bs4 import BeautifulSoup
import logging
from ..scraper_engine import BaseScraper, JobData

logger = logging.getLogger("BoeingScraper")

MAX_PAGES = 3

class BoeingScraper(BaseScraper):
    def __init__(self, browser_manager):
        super().__init__("Boeing", browser_manager)

    async def scrape(self) -> List[JobData]:
        logger.info(f"[{self.company_name}] Starting scrape...")
        jobs = []

        context = await self.browser_manager.get_new_context()
        page = await context.new_page()

        try:
            # General search (page 1 only — no paginated URL pattern for this endpoint)
            try:
                logger.info(f"[{self.company_name}] Scraping general search page")
                await page.goto("https://jobs.boeing.com/search-jobs", timeout=60000)
                await page.wait_for_selector('#search-results-list', timeout=30000)
                content = await page.content()
                self._extract_jobs_from_page(content, jobs)
            except Exception as e:
                logger.warning(f"[{self.company_name}] Error on general search: {e}")

            # Intern search — paginate using the /intern/185/N URL pattern
            for page_num in range(1, MAX_PAGES + 1):
                url = f"https://jobs.boeing.com/search-jobs/intern/185/{page_num}"
                try:
                    logger.info(f"[{self.company_name}] Scraping intern page {page_num}")
                    await page.goto(url, timeout=60000)
                    await page.wait_for_selector('#search-results-list', timeout=30000)
                    content = await page.content()
                    jobs_before = len(jobs)
                    self._extract_jobs_from_page(content, jobs)
                    if len(jobs) == jobs_before:
                        logger.info(f"[{self.company_name}] No new jobs on page {page_num} — stopping")
                        break
                except Exception as e:
                    logger.warning(f"[{self.company_name}] Error on intern page {page_num}: {e}")
                    break

        finally:
            await context.close()

        logger.info(f"[{self.company_name}] Found {len(jobs)} jobs.")
        return jobs

    def _extract_jobs_from_page(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, 'html.parser')
        results_list = soup.select('#search-results-list ul li')
        
        for li in results_list:
            try:
                link_elem = li.select_one('a.search-results__job-link')
                if not link_elem:
                    continue
                
                title_elem = link_elem.select_one('.search-results__job-title')
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                
                href = link_elem.get('href')
                url = "https://jobs.boeing.com" + href if href.startswith('/') else href
                
                loc_elem = li.select_one('.search-results__job-info.location')
                location = loc_elem.get_text(strip=True) if loc_elem else "Unknown Location"
                
                date_elem = li.select_one('.search-results__job-info.date')
                date_posted = date_elem.get_text(strip=True) if date_elem else None
                
                # Filter for Intern only
                if not self.is_relevant_role(title):
                    continue

                job = JobData(
                    title=title,
                    company=self.company_name,
                    url=url,
                    location=location,
                    date_posted=date_posted
                )
                jobs_list.append(job)
                
            except Exception as e:
                print(f"Error parsing job card: {e}")
                continue
