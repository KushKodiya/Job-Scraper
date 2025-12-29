from typing import List
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
from ..scraper_engine import BaseScraper, JobData

class BoeingScraper(BaseScraper):
    def __init__(self):
        super().__init__("Boeing")
        self.start_urls = [
            "https://jobs.boeing.com/search-jobs",
            "https://jobs.boeing.com/search-jobs/intern/185/1"
        ]

    def scrape(self) -> List[JobData]:
        print(f"[{self.company_name}] Starting scrape...")
        jobs = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                for url in self.start_urls:
                    print(f"[{self.company_name}] Scraping URL: {url}")
                    try:
                        page.goto(url, timeout=60000)
                        # Wait for the list to load
                        page.wait_for_selector('#search-results-list', timeout=30000)
                        
                        # Scrape the jobs from the current page
                        self._extract_jobs_from_page(page.content(), jobs)
                    except Exception as e:
                         print(f"[{self.company_name}] Error scraping URL {url}: {e}")
                
            except Exception as e:
                print(f"[{self.company_name}] Error during scraping: {e}")
            finally:
                browser.close()
                
        print(f"[{self.company_name}] Found {len(jobs)} jobs.")
        return jobs

    def _extract_jobs_from_page(self, html: str, jobs_list: List[JobData]):
        soup = BeautifulSoup(html, 'html.parser')
        results_list = soup.select('#search-results-list ul li')
        
        for li in results_list:
            try:
                link_elem = li.select_one('a.search-results__job-link')
                if not link_elem:
                    continue
                
                title_elem = link_elem.select_one('.search-results__job-title')
                title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                
                url = "https://jobs.boeing.com" + link_elem.get('href') if link_elem.get('href').startswith('/') else link_elem.get('href')
                
                # Location and Date are often in spans with specific classes
                # Inspection said: .search-results__job-info.location / .date
                
                loc_elem = li.select_one('.search-results__job-info.location')
                location = loc_elem.get_text(strip=True) if loc_elem else "Unknown Location"
                
                date_elem = li.select_one('.search-results__job-info.date')
                date_posted = date_elem.get_text(strip=True) if date_elem else None
                
                # Filter for Intern/New Grad only
                if not self.is_relevant_role(title):
                    continue

                job = JobData(
                    title=title,
                    company=self.company_name,
                    url=url,
                    location=location,
                    date_posted=date_posted
                )
                jobs_list.append(job)
                
            except Exception as e:
                print(f"Error parsing job card: {e}")
                continue
