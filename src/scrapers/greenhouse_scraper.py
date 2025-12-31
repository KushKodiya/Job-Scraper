from typing import List
from bs4 import BeautifulSoup
import asyncio
from .job_board_base import GenericJobBoardScraper, JobData

class GreenhouseScraper(GenericJobBoardScraper):
    def __init__(self, browser_manager, search_terms: List[str]):
        super().__init__("Greenhouse", browser_manager, search_terms)
        # Note: Greenhouse doesn't have a central search. 
        # This scraper mimics the JobBoardScraper interface but expects 
        # the 'search_terms' to be Full URLs to company boards if used directly,
        # OR it can be used to parse pages found by GoogleSearchScraper.
        # For this implementation, we will treat it as a "Direct Board Scraper" 
        # where we assume we are given board URLs, NOT search terms.
        pass

    async def scrape_board(self, page, board_url: str) -> List[JobData]:
        jobs = []
        try:
            print(f"[{self.company_name}] Scraping board: {board_url}")
            await page.goto(board_url, timeout=60000)
            await page.wait_for_selector('div#main', timeout=15000)
            
            content = await page.content()
            self._extract_jobs(content, jobs, board_url)
            
        except Exception as e:
            print(f"[{self.company_name}] Error scraping board {board_url}: {e}")
            
        return jobs
        
    async def scrape(self) -> List[JobData]:
        # Overriding base scrape to treat search_terms as URLs
        all_jobs = []
        context = await self.browser_manager.get_new_context()
        page = await context.new_page()
        
        try:
            for url in self.search_terms:
                if "boards.greenhouse.io" not in url:
                    continue 
                jobs = await self.scrape_board(page, url)
                all_jobs.extend(jobs)
                
        except Exception as e:
            print(f"[{self.company_name}] Error: {e}")
        finally:
            await context.close()
            
        return all_jobs

    def _extract_jobs(self, html: str, jobs_list: List[JobData], base_url: str):
        soup = BeautifulSoup(html, 'html.parser')
        
        # Standard Greenhouse structure
        # usually div.opening
        openings = soup.select('div.opening')
        
        for opening in openings:
            try:
                link_elem = opening.select_one('a')
                if not link_elem:
                    continue
                    
                title = link_elem.get_text(strip=True)
                href = link_elem.get('href')
                url = "https://boards.greenhouse.io" + href if href.startswith('/') else href
                
                loc_elem = opening.select_one('span.location')
                location = loc_elem.get_text(strip=True) if loc_elem else "Unknown"

                # No direct company name on the board usually, it's the board's owner
                # We can extract it from the page title or meta, but for now use "Greenhouse Job"
                
                # Filter
                if not self.is_relevant_role(title):
                    continue

                job = JobData(
                    title=title,
                    company="Greenhouse Job", # Placeholder, ideally passed in
                    url=url,
                    location=location,
                    date_posted=None
                )
                jobs_list.append(job)
                
            except:
                continue
