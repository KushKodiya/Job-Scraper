from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import hashlib

@dataclass
class JobData:
    title: str
    company: str
    url: str
    location: Optional[str] = None
    date_posted: Optional[str] = None

    @property
    def id(self) -> str:
        """Generate a unique ID for the job based on company and URL."""
        unique_str = f"{self.company}:{self.url}"
        return hashlib.md5(unique_str.encode()).hexdigest()

class BaseScraper(ABC):
    def __init__(self, company_name: str):
        self.company_name = company_name

    @abstractmethod
    def scrape(self) -> List[JobData]:
        """Scrape the carrier page and return a list of JobData objects."""
        pass
        
    def filter_interests(self, job: JobData) -> List[str]:
        """Return a list of interests (tags) based on the job title/description."""
        tags = []
        title_lower = job.title.lower()
        
        keywords = {
            'aerospace': ['aerospace', 'propulsion', 'flight', 'avionics', 'aircraft'],
            'software': ['software', 'developer', 'software engineer', 'data scientist', 'computer', 'full stack', 'backend', 'frontend'],
            'finance': ['finance', 'accounting', 'audit', 'tax', 'analyst'],
            'consulting': ['consultant', 'strategy', 'advisory'],
            'mechanical': ['mechanical', 'thermal', 'structural'],
            'electrical': ['electrical', 'electronics', 'circuit'],
        }
        
        for category, terms in keywords.items():
            if any(term in title_lower for term in terms):
                tags.append(category)
                
        # Heuristic: if company is Boeing, always add aerospace if not present? 
        # For now let's stick to keyword matching.
        
        return tags

    def is_relevant_role(self, title: str) -> bool:
        """Check if the job title matches Internship or New Grad keywords."""
        title_lower = title.lower()
        target_keywords = [
            'intern', 'internship', 'co-op', 
            'grad', 'graduate', 'entry level', 'entry-level', 
            'early career', 'junior', 'associate' 
        ]
        
        # Exclude senior roles explicitly to be safe
        exclude_keywords = ['senior', 'manager', 'lead', 'principal', 'director', 'expert', 'experienced']
        
        if any(ex in title_lower for ex in exclude_keywords):
            return False
            
        return any(term in title_lower for term in target_keywords)
