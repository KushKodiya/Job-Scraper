from typing import List
from bs4 import BeautifulSoup
import asyncio
import random
from .job_board_base import GenericJobBoardScraper, JobData

class DribbbleScraper(GenericJobBoardScraper):
    def __init__(self, browser_manager, search_terms: List[str]):
        super().__init__("Dribbble", browser_manager, search_terms)
        self.base_url = "https://dribbble.com/jobs"

    async def scrape_search_term(self, page, search_term: str) -> List[JobData]:
        jobs = []
        # URL structure: https://dribbble.com/jobs?keyword=designer
        url = f"{self.base_url}?keyword={search_term}"
        
        try:
            print(f"[{self.company_name}] Going to {url}")
            await page.goto(url, timeout=60000)
            await asyncio.sleep(random.uniform(2, 4))
            
            # Wait for job list
            try:
                # Select cards container
                await page.wait_for_selector('.jobs-list', timeout=15000)
            except:
                print(f"[{self.company_name}] No results found (or selector changed).")
                return []
                
            content = await page.content()
            self._extract_jobs(content, jobs)
            
        except Exception as e:
             print(f"[{self.company_name}] Error scraping term {search_term}: {e}")
             
        return jobs

    def _extract_jobs(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, 'html.parser')
        
        # Dribbble usually has a list of <a> tags that are the job cards
        cards = soup.select('.jobs-list a.job-list-item')
        
        for card in cards:
            try:
                title_elem = card.select_one('.job-title')
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                
                company_elem = card.select_one('.company-name')
                company = company_elem.get_text(strip=True) if company_elem else "Dribbble Job"
                
                href = card.get('href')
                url = "https://dribbble.com" + href if href.startswith('/') else href

                loc_elem = card.select_one('.job-location')
                location = loc_elem.get_text(strip=True) if loc_elem else "Remote/Unknown"

                if not self.is_relevant_role(title):
                    continue

                # Extract ID from URL
                # Formats: /jobs/123456-Title
                job_id = None
                if url:
                    clean_url = url.split('?')[0]
                    parts = clean_url.rstrip('/').split('/')
                    for part in reversed(parts):
                        if part.replace('-','').isdigit(): # Check if it's the ID
                            job_id = part
                            break
                        # Heuristic: Dribbble IDs are usually the second to last or last part
                        # e.g. /jobs/181818-Title -> 181818 is usually mixed with title or separate
                        # Actually dribbble is usually /jobs/12345-title.
                        # Let's simple use the segment with digits that comes after 'jobs'
                    
                    # Simpler approach for Dribbble:
                    # /jobs/123-title -> split by - take first
                    if "/jobs/" in url:
                        try:
                            slug = url.split("/jobs/")[1]
                            job_id = slug.split("-")[0]
                        except:
                            pass

                job = JobData(
                    title=title,
                    company=company,
                    url=url,
                    location=location,
                    date_posted=None,
                    job_id=job_id
                )
                jobs_list.append(job)
                
            except Exception as e:
                continue
