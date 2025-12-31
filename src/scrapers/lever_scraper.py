from typing import List
from bs4 import BeautifulSoup
import asyncio
from .job_board_base import GenericJobBoardScraper, JobData

class LeverScraper(GenericJobBoardScraper):
    def __init__(self, browser_manager, search_terms: List[str]):
        super().__init__("Lever", browser_manager, search_terms)
        # Similar to Greenhouse, search_terms here are expected to be Board URLs 
        pass

    async def scrape_board(self, page, board_url: str) -> List[JobData]:
        jobs = []
        try:
            print(f"[{self.company_name}] Scraping board: {board_url}")
            await page.goto(board_url, timeout=60000)
            await page.wait_for_selector('.postings-group', timeout=15000)
            
            content = await page.content()
            self._extract_jobs(content, jobs)
            
        except Exception as e:
            print(f"[{self.company_name}] Error scraping board {board_url}: {e}")
            
        return jobs
        
    async def scrape(self) -> List[JobData]:
        all_jobs = []
        context = await self.browser_manager.get_new_context()
        page = await context.new_page()
        
        try:
            for url in self.search_terms:
                if "lever.co" not in url:
                    continue 
                jobs = await self.scrape_board(page, url)
                all_jobs.extend(jobs)
                
        except Exception as e:
            print(f"[{self.company_name}] Error: {e}")
        finally:
            await context.close()
            
        return all_jobs

    def _extract_jobs(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, 'html.parser')
        
        # Lever structure: .posting
        postings = soup.select('.posting')
        
        for posting in postings:
            try:
                title_elem = posting.select_one('h5[data-qa="posting-name"]')
                if not title_elem:
                     continue
                     
                title = title_elem.get_text(strip=True)
                
                link_elem = posting.select_one('a.posting-title')
                href = link_elem.get('href') if link_elem else ""
                url = href # Lever links are usually absolute
                
                loc_elem = posting.select_one('.sort-by-location')
                location = loc_elem.get_text(strip=True) if loc_elem else "Unknown"

                # Filter
                if not self.is_relevant_role(title):
                    continue

                job = JobData(
                    title=title,
                    company="Lever Job", 
                    url=url,
                    location=location,
                    date_posted=None
                )
                jobs_list.append(job)
                
            except:
                continue
