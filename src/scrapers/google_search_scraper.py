from typing import List
from bs4 import BeautifulSoup
import asyncio
import random
import urllib.parse
from .job_board_base import GenericJobBoardScraper, JobData

class GoogleSearchScraper(GenericJobBoardScraper):
    def __init__(self, browser_manager, search_queries: List[str]):
        """
        search_queries: List of Google queries e.g. ['site:boards.greenhouse.io "software engineer"']
        """
        super().__init__("GoogleSearch", browser_manager, search_queries)
        self.base_url = "https://www.google.com/search"

    async def scrape_search_term(self, page, query: str) -> List[JobData]:
        # Google search scraping
        jobs = [] # We will return "JobData" objects where the URL is the ATS link
        
        url = f"{self.base_url}?q={urllib.parse.quote(query)}"
        
        try:
            print(f"[{self.company_name}] Dorking: {query}")
            await page.goto(url, timeout=60000)
            await asyncio.sleep(random.uniform(2, 5))
            
            # Check for captcha
            if "sorry/index" in page.url or await page.query_selector('iframe[src*="recaptcha"]'):
                print(f"[{self.company_name}] Google CAPTCHA detected. Aborting this query.")
                return []

            content = await page.content()
            links = self._extract_links(content)
            
            # For each link found, we creating a placeholder JobData
            # The actual metadata (title, location) might be sparse from Google results
            # We will rely on the specific ATS scraper to refine this later or just post the link
            
            for link in links:
                # Basic parsing from Google Snippet if possible, else defaults
                job = JobData(
                    title=link['title'],
                    company="Unknown (ATS Discovery)",
                    url=link['url'],
                    location="Unknown",
                    date_posted=None
                )
                jobs.append(job)
                
        except Exception as e:
             print(f"[{self.company_name}] Error scraping query {query}: {e}")
             
        return jobs

    def _extract_links(self, html: str) -> List[dict]:
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Google search results usually in div.g
        for g in soup.select('div.g'):
            try:
                link_elem = g.select_one('a')
                if not link_elem:
                     continue
                     
                href = link_elem.get('href')
                if not href or href.startswith('/search'):
                    continue
                    
                title_elem = g.select_one('h3')
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                
                # Filter out garbage
                if "google.com" in href:
                    continue
                    
                results.append({'url': href, 'title': title})
            except:
                continue
                
        return results
