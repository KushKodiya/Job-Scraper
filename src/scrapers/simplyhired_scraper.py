from typing import List
from bs4 import BeautifulSoup
import asyncio
import random
from .job_board_base import GenericJobBoardScraper, JobData

class SimplyHiredScraper(GenericJobBoardScraper):
    def __init__(self, browser_manager, search_terms: List[str]):
        super().__init__("SimplyHired", browser_manager, search_terms)
        self.base_url = "https://www.simplyhired.com/search"

    async def scrape_search_term(self, page, search_term: str) -> List[JobData]:
        jobs = []
        # Construct search URL (SimpyHired uses q for query, l for location)
        url = f"{self.base_url}?q={search_term}&l="
        
        try:
            print(f"[{self.company_name}] Going to {url}")
            await page.goto(url, timeout=60000)
            await asyncio.sleep(random.uniform(1, 3))
            
            # Wait for list
            try:
                await page.wait_for_selector('#job-list', timeout=15000)
            except:
                print(f"[{self.company_name}] No results list found.")
                # Maybe try valid selector for empty state or error
                return []
                
            content = await page.content()
            self._extract_jobs(content, jobs)
            
        except Exception as e:
             print(f"[{self.company_name}] Error scraping term {search_term}: {e}")
             
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
                jobs_list.append(job)
                
            except Exception as e:
                continue
