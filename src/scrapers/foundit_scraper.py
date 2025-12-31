from typing import List
from bs4 import BeautifulSoup
import asyncio
import random
from .job_board_base import GenericJobBoardScraper, JobData

class FoundItScraper(GenericJobBoardScraper):
    def __init__(self, browser_manager, search_terms: List[str]):
        super().__init__("FoundIt", browser_manager, search_terms)
        # Using foundit.in (common for this brand) or foundit.my depending on region
        # Defaulting to foundit.in for now as it's the biggest market for this brand
        self.base_url = "https://www.foundit.in/srp/results"

    async def scrape_search_term(self, page, search_term: str) -> List[JobData]:
        jobs = []
        # URL structure: https://www.foundit.in/srp/results?query=software+engineer
        url = f"{self.base_url}?query={search_term}"
        
        try:
            print(f"[{self.company_name}] Going to {url}")
            await page.goto(url, timeout=60000)
            await asyncio.sleep(random.uniform(2, 4))
            
            # Wait for results card
            try:
                await page.wait_for_selector('.srpResultCard', timeout=15000)
            except:
                print(f"[{self.company_name}] No results list found.")
                return []
                
            content = await page.content()
            self._extract_jobs(content, jobs)
            
        except Exception as e:
             print(f"[{self.company_name}] Error scraping term {search_term}: {e}")
             
        return jobs

    def _extract_jobs(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, 'html.parser')
        
        cards = soup.select('.srpResultCard')
        
        for card in cards:
            try:
                title_elem = card.select_one('.jobTitle')
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                
                company_elem = card.select_one('.companyName')
                company = company_elem.get_text(strip=True) if company_elem else "FoundIt Job"
                
                # Check link
                # FoundIt often opens in new tab or has onclick
                # Looking for an anchor in title
                if title_elem and title_elem.name == 'a':
                     href = title_elem.get('href')
                     url = "https://www.foundit.in" + href if href.startswith('/') else href
                else:
                    # Try finding any link
                    link_elem = card.select_one('a')
                    href = link_elem.get('href') if link_elem else ""
                    # Handle absolute URLs
                    if href.startswith('http'):
                        url = href
                    else:
                        url = "https://www.foundit.in" + href if href.startswith('/') else href

                loc_elem = card.select_one('.jobLocation')
                location = loc_elem.get_text(strip=True) if loc_elem else "Unknown Location"

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
