import asyncio
from typing import List
from ..scraper_engine import JobBoardScraper, JobData
import random

class GenericJobBoardScraper(JobBoardScraper):
    """
    A generic base for job boards that use search parameters.
    This class handles the common pattern of:
    1. Go to search URL with params
    2. Extract jobs
    3. Click 'Next' or go to next page
    """
    
    async def scrape_search_term(self, context, search_term: str) -> List[JobData]:
        # To be implemented by subclasses like IndeedScraper
        return []

    async def scrape(self) -> List[JobData]:
        all_jobs = []
        context = await self.browser_manager.get_new_context()
        page = await context.new_page()
        
        try:
            for term in self.search_terms:
                print(f"[{self.company_name}] Searching for: {term}")
                jobs = await self.scrape_search_term(page, term)
                all_jobs.extend(jobs)
                # Random sleep between terms
                await asyncio.sleep(random.uniform(2, 5))
                
        except Exception as e:
            print(f"[{self.company_name}] Error: {e}")
        finally:
            await context.close()
            
        return all_jobs
