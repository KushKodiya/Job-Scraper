from typing import List
from bs4 import BeautifulSoup
import asyncio
import random
import logging
from .job_board_base import GenericJobBoardScraper, JobData

logger = logging.getLogger("SimplyHiredScraper")

MAX_PAGES = 3

class SimplyHiredScraper(GenericJobBoardScraper):
    def __init__(self, browser_manager, search_terms: List[str]):
        super().__init__("SimplyHired", browser_manager, search_terms)
        self.base_url = "https://www.simplyhired.com/search"

    async def scrape_search_term(self, page, search_term: str) -> List[JobData]:
        jobs = []

        for page_num in range(1, MAX_PAGES + 1):
            url = f"{self.base_url}?q={search_term}&l=&p={page_num}"
            try:
                logger.info(f"[{self.company_name}] Fetching page {page_num} for '{search_term}'")
                await page.goto(url, timeout=60000)
                await asyncio.sleep(random.uniform(1, 3))

                try:
                    await page.wait_for_selector('#job-list', timeout=15000)
                except Exception:
                    logger.info(f"[{self.company_name}] No results on page {page_num} for '{search_term}' — stopping")
                    break

                content = await page.content()
                jobs_before = len(jobs)
                self._extract_jobs(content, jobs)

                if len(jobs) == jobs_before:
                    logger.info(f"[{self.company_name}] No new jobs on page {page_num} for '{search_term}' — stopping")
                    break

            except Exception as e:
                logger.warning(f"[{self.company_name}] Error on page {page_num} for '{search_term}': {e}")
                break

        return jobs

    def _extract_jobs(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, 'html.parser')
        
        # SimplyHired classes (often obfuscated but structured)
        # Look for the list items
        cards = soup.select('ul#job-list li article')
        if not cards:
             cards = soup.select('ul#job-list li') # Fallback

        for card in cards:
            try:
                title_elem = card.select_one('a.chakra-button') # Often the title is a link with chakra class
                if not title_elem:
                     title_elem = card.select_one('h3')

                title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                
                # Company
                company_elem = card.select_one('[data-testid="companyName"]')
                company = company_elem.get_text(strip=True) if company_elem else "SimplyHired Job"
                
                # Location
                loc_elem = card.select_one('[data-testid="searchSerpJobLocation"]')
                location = loc_elem.get_text(strip=True) if loc_elem else "Unknown Location"
                
                # URL
                if title_elem and title_elem.name == 'a':
                     href = title_elem.get('href')
                     url = "https://www.simplyhired.com" + href if href.startswith('/') else href
                else:
                    # Look for any link
                    link_elem = card.select_one('a')
                    href = link_elem.get('href') if link_elem else ""
                    url = "https://www.simplyhired.com" + href if href.startswith('/') else href

                if not self.is_relevant_role(title):
                    continue

                job = JobData(
                    title=title,
                    company=company,
                    url=url,
                    location=location,
                    date_posted=None
                )
                
                # Date
                date_elem = card.select_one('time')
                if not date_elem:
                     date_elem = card.select_one('[data-testid="searchSerpJobDate"]')
                
                if date_elem:
                    job.date_posted = date_elem.get_text(strip=True)

                jobs_list.append(job)
                
            except Exception as e:
                continue
