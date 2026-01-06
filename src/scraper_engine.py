from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import hashlib
from .browser_manager import BrowserManager

@dataclass
class JobData:
    title: str
    company: str
    url: str
    location: Optional[str] = None
    date_posted: Optional[str] = None
    job_id: Optional[str] = None # Unique ID from the source (e.g. Indeed JK or Greenhouse ID)

    @property
    def id(self) -> str:
        """Generate a unique ID for the job based on company and ID/URL."""
        if self.job_id:
            # Use the explicit ID if provided (more stable)
            unique_str = f"{self.company}:{self.job_id}"
        else:
            # Fallback to URL (strip common tracking params if possible or use raw)
            # Simple strip of query params might be too aggressive if ID is in query
            unique_str = f"{self.company}:{self.url}"
            
        return hashlib.md5(unique_str.encode()).hexdigest()

class BaseScraper(ABC):
    def __init__(self, company_name: str, browser_manager: BrowserManager):
        self.company_name = company_name
        self.browser_manager = browser_manager

    @abstractmethod
    async def scrape(self) -> List[JobData]:
        """Scrape the carrier page/job board and return a list of JobData objects."""
        pass
        
    def filter_interests(self, job: JobData) -> List[str]:
        """Return a list of interests (tags) based on the job title/description."""
        tags = []
        title_lower = job.title.lower()
        
        keywords = {
            'aerospace': ['aerospace', 'propulsion', 'flight', 'avionics', 'aircraft', 'space', 'rocket', 'satellite', 'defen'], # 'defen' matches defense
            'software': ['software', 'developer', 'full stack', 'backend', 'frontend', 'computer science', 'machine learning', 'ai', 'cloud', 'cyber', 'data science', 'data engineer', 'firmware', 'sre', 'devops'],
            'automotive': ['automotive', 'vehicle', 'autonomous', 'driver', 'adas', 'car', 'ev', 'mobility'],
            'finance': ['finance', 'accounting', 'audit', 'tax', 'analyst', 'investment', 'trading', 'risk', 'capital'],
            'manufacturing': ['manufacturing', 'production', 'industrial', 'process', 'supply chain', 'logistics', 'quality', 'operations'],
            'ece hardware': ['hardware', 'electronics', 'circuit', 'fpga', 'asic', 'pcb', 'embedded', 'signal', 'rf', 'power'],
            'semiconductors': ['semiconductor', 'lithography', 'wafer', 'device physics', 'vlsi', 'silicon', 'chip', 'fab'],
            'general': ['business', 'marketing', 'hr', 'recruiter', 'project manager', 'program manager', 'sales', 'consultant', 'strategy', 'admin'],
        }
        
        for category, terms in keywords.items():
            if any(term in title_lower for term in terms):
                tags.append(category)
        
        # If no specific tag found, mark as 'other'
        if not tags:
            tags.append('other')
            
        return tags

    def is_relevant_role(self, title: str) -> bool:
        """Check if the job title matches Internship or New Grad keywords."""
        title_lower = title.lower()
        target_keywords = [
            'intern', 'internship', 'co-op'
        ]
        
        # Exclude senior roles explicitly to be safe
        exclude_keywords = ['senior', 'manager', 'lead', 'principal', 'director', 'expert', 'experienced']
        
        if any(ex in title_lower for ex in exclude_keywords):
            return False
            
        return any(term in title_lower for term in target_keywords)

class JobBoardScraper(BaseScraper):
    def __init__(self, company_name: str, browser_manager: BrowserManager, search_terms: List[str]):
        super().__init__(company_name, browser_manager)
        self.search_terms = search_terms

    @abstractmethod
    async def scrape(self) -> List[JobData]:
        pass
