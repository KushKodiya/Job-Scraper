import unittest
import sys
import os
from dataclasses import dataclass

# Mock JobData to avoid importing whole engine if it has complex dependencies
@dataclass
class JobData:
    title: str
    company: str = "Test Co"
    url: str = "http://test.com"
    location: str = "Remote"
    date_posted: str = None
    job_id: str = None
    
# Mock browser_manager and playwright to avoid install requirement for logic test
from unittest.mock import MagicMock
sys.modules['src.browser_manager'] = MagicMock()
sys.modules['playwright'] = MagicMock()
sys.modules['playwright.async_api'] = MagicMock()

# Import the actual filter_interests method or class
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.scraper_engine import BaseScraper

# Concrete class for testing
class TestScraper(BaseScraper):
    async def scrape(self):
        return []

class TestCategories(unittest.TestCase):
    def setUp(self):
        # Pass None for browser_manager as it's not needed for filter_interests
        self.scraper = TestScraper("Test", None)
        
    def test_aerospace(self):
        job = JobData(title="Raptor Propulsion Intern")
        tags = self.scraper.filter_interests(job)
        self.assertIn("aerospace", tags)
        
        job = JobData(title="Avionics Engineer")
        tags = self.scraper.filter_interests(job)
        self.assertIn("aerospace", tags)

    def test_software(self):
        job = JobData(title="Senior Backend Developer")
        tags = self.scraper.filter_interests(job)
        self.assertIn("software", tags)
        
        job = JobData(title="Data Scientist")
        tags = self.scraper.filter_interests(job)
        self.assertIn("software", tags)

    def test_automotive(self):
        job = JobData(title="Autonomous Vehicle Test Engineer")
        tags = self.scraper.filter_interests(job)
        self.assertIn("automotive", tags)
        
        job = JobData(title="ADAS Perception Intern")
        tags = self.scraper.filter_interests(job)
        self.assertIn("automotive", tags)

    def test_finance(self):
        job = JobData(title="Investment Banking Analyst")
        tags = self.scraper.filter_interests(job)
        self.assertIn("finance", tags)
        
    def test_manufacturing(self):
        job = JobData(title="Supply Chain Manager")
        tags = self.scraper.filter_interests(job)
        self.assertIn("manufacturing", tags)
        
    def test_ece_hardware(self):
        job = JobData(title="FPGA Engineer")
        tags = self.scraper.filter_interests(job)
        self.assertIn("ece hardware", tags)
        # Should also match software via 'engineer'? Or kept separate?
        # 'Engineer' is in software keywords, so it might match software too.
        # Let's check if it matches at least ece hardware
        
    def test_semiconductors(self):
        job = JobData(title="Lithography Process Engineer")
        tags = self.scraper.filter_interests(job)
        self.assertIn("semiconductors", tags)
        self.assertIn("manufacturing", tags) # 'process' is in mfg
        
    def test_general(self):
        job = JobData(title="Marketing Intern")
        tags = self.scraper.filter_interests(job)
        self.assertIn("general", tags)
        
    def test_other(self):
        job = JobData(title="Head Chef")
        tags = self.scraper.filter_interests(job)
        self.assertEqual(tags, ["other"])
        
    def test_multi_tag(self):
        # A job could match multiple
        job = JobData(title="Embedded Software Engineer for Autonomous Vehicles")
        tags = self.scraper.filter_interests(job)
        self.assertIn("software", tags)
        self.assertIn("ece hardware", tags) # embedded
        self.assertIn("automotive", tags) # autonomous + vehicle

if __name__ == '__main__':
    unittest.main()
