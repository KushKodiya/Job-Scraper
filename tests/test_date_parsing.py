import unittest
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.date_utils import parse_job_date

class TestDateParsing(unittest.TestCase):
    def test_relative_days(self):
        # "3 days ago"
        dt = parse_job_date("3 days ago")
        self.assertIsNotNone(dt)
        expected = datetime.utcnow() - timedelta(days=3)
        self.assertEqual(dt.date(), expected.date())
        
        # "posted 14 days ago"
        dt = parse_job_date("posted 14 days ago")
        self.assertIsNotNone(dt)
        expected = datetime.utcnow() - timedelta(days=14)
        self.assertEqual(dt.date(), expected.date())
        
    def test_special_terms(self):
        # "Just posted"
        dt = parse_job_date("Just posted")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.date(), datetime.utcnow().date())
        
        # "Today"
        dt = parse_job_date("Today")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.date(), datetime.utcnow().date())
        
        # "Yesterday"
        dt = parse_job_date("Yesterday")
        self.assertIsNotNone(dt)
        expected = datetime.utcnow() - timedelta(days=1)
        self.assertEqual(dt.date(), expected.date())
        
    def test_absolute_dates(self):
        # Assumes current year if missing
        current_year = datetime.utcnow().year
        
        # "Jan 05, 2025"
        dt = parse_job_date("Jan 05, 2025")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 5)
        
        # "2025-01-05"
        dt = parse_job_date("2025-01-05")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2025)
        
    def test_30_plus(self):
        dt = parse_job_date("30+ days ago")
        self.assertIsNotNone(dt)
        # Should be at least 31 days ago
        self.assertTrue(dt < datetime.utcnow() - timedelta(days=30))
        
    def test_none(self):
        self.assertIsNone(parse_job_date(None))
        self.assertIsNone(parse_job_date(""))

if __name__ == '__main__':
    unittest.main()
