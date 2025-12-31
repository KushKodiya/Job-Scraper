from typing import List
from bs4 import BeautifulSoup
import asyncio
import random
from .job_board_base import GenericJobBoardScraper, JobData

class IndeedScraper(GenericJobBoardScraper):
    def __init__(self, browser_manager, search_terms: List[str]):
        super().__init__("Indeed", browser_manager, search_terms)
        self.base_url = "https://www.indeed.com/jobs"

    async def scrape_search_term(self, page, search_term: str) -> List[JobData]:
        jobs = []
        # Construct search URL
        url = f"{self.base_url}?q={search_term}&l="
        
        try:
            print(f"[{self.company_name}] Going to {url}")
            await page.goto(url, timeout=60000)
            
            # Anti-bot: Random sleep and mouse movements could be added here
            await asyncio.sleep(random.uniform(2, 4))
            
            # Check for Cloudflare/Shield
            title = await page.title()
            if "Cloudflare" in title or "Just a moment" in title:
                print(f"[{self.company_name}] Cloudflare detected! Skipping term.")
                return []

            # Wait for results
            try:
                await page.wait_for_selector('ul.jobsearch-ResultsList', timeout=15000)
            except:
                print(f"[{self.company_name}] No results list found.")
                return []
                
            # Scrape current page
            content = await page.content()
            self._extract_jobs(content, jobs)
            
            # Pagination (Simplification: just scrape first page for scale test)
            # In full version, we would find the 'Next' button and click it
            
        except Exception as e:
             print(f"[{self.company_name}] Error scraping term {search_term}: {e}")
             
        return jobs

    def _extract_jobs(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, 'html.parser')
        
        # Indeed structure changes often, looking for common classes
        # As of late 2024:
        cards = soup.select('.job_seen_beacon')
        
        for card in cards:
            try:
                title_elem = card.select_one('h2.jobTitle span')
                if not title_elem:
                   # Sometimes title is directly in h2 or a link
                   title_elem = card.select_one('h2.jobTitle')

                title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                
                company_elem = card.select_one('[data-testid="company-name"]')
                company = company_elem.get_text(strip=True) if company_elem else "Indeed Job"
                
                loc_elem = card.select_one('[data-testid="text-location"]')
                location = loc_elem.get_text(strip=True) if loc_elem else "Unknown Location"
                
                # Get Link
                link_elem = card.select_one('a.jcs-JobTitle')
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    url = "https://www.indeed.com" + href if href.startswith('/') else href
                else:
                    # Backup: sometimes the whole card is clickable or ID is elsewhere
                    url = "https://www.indeed.com/viewjob?jk=" + card.parent.get('data-jk', '')

                # Filter relevance
                if not self.is_relevant_role(title):
                    continue

                job = JobData(
                    title=title,
                    company=company, # Source company (e.g. "Boeing")
                    url=url,
                    location=location,
                    date_posted=None 
                )
                jobs_list.append(job)
                
            except Exception as e:
                # print(f"Error parsing indeed card: {e}")
                continue
