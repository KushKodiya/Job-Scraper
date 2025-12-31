from typing import List
from bs4 import BeautifulSoup
import asyncio
import random
from .job_board_base import GenericJobBoardScraper, JobData

class WellfoundScraper(GenericJobBoardScraper):
    def __init__(self, browser_manager, search_terms: List[str]):
        super().__init__("Wellfound", browser_manager, search_terms)
        self.base_url = "https://wellfound.com/jobs"

    async def scrape_search_term(self, page, search_term: str) -> List[JobData]:
        jobs = []
        # Wellfound url structure: https://wellfound.com/role/software-engineer?keywords=frontend
        # But generic search is harder. Let's try the jobs page query param if possible, 
        # or defaults. Wellfound often requires login for deep search, 
        # but public pages exist for roles.
        # Strategy: Use the 'keywords' param on the main jobs page.
        
        url = f"{self.base_url}?keywords={search_term}"
        
        try:
            print(f"[{self.company_name}] Going to {url}")
            await page.goto(url, timeout=60000)
            await asyncio.sleep(random.uniform(2, 4))
            
            # Check for login wall or public access
            # Wellfound is tricky without login. We might land on a landing page.
            # Selectors vary by auth state.
            
            try:
                # Wait for any job card
                await page.wait_for_selector('[class*="styles_jobListing"]', timeout=15000)
            except:
                print(f"[{self.company_name}] No job listings found (could be auth wall).")
                return []
                
            # Infinite scroll logic: Scroll 3 times
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
            content = await page.content()
            self._extract_jobs(content, jobs)
            
        except Exception as e:
             print(f"[{self.company_name}] Error scraping term {search_term}: {e}")
             
        return jobs

    def _extract_jobs(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, 'html.parser')
        
        # Wellfound classes use css modules often, e.g. styles_component__123
        # Use substring matching for classes
        
        cards = soup.select('[class*="styles_jobListing"]')
        
        for card in cards:
            try:
                # Title often in an h2 or similar
                title_elem = card.select_one('[class*="styles_title"]')
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                
                # Company
                company_elem = card.select_one('[class*="styles_header"] h2')
                company = company_elem.get_text(strip=True) if company_elem else "Wellfound Startup"
                
                # Link
                link_elem = card.select_one('a[href*="/jobs/"]')
                if link_elem:
                    href = link_elem.get('href')
                    url = "https://wellfound.com" + href if href.startswith('/') else href
                else:
                    url =  "https://wellfound.com/jobs" # Fallback

                # Location
                loc_elem = card.select_one('[class*="styles_location"]')
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote/Unknown"

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
