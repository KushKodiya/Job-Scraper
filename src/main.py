import sys
import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from .utils.date_utils import parse_job_date
from .database import init_db, Job
from .browser_manager import BrowserManager
from .scrapers.boeing_scraper import BoeingScraper
from .scrapers.indeed_scraper import IndeedScraper
from .scrapers.simplyhired_scraper import SimplyHiredScraper
from .scrapers.wellfound_scraper import WellfoundScraper
from .scrapers.foundit_scraper import FoundItScraper
from .scrapers.dribbble_scraper import DribbbleScraper
from .scrapers.google_search_scraper import GoogleSearchScraper
from .scrapers.greenhouse_scraper import GreenhouseScraper
from .scrapers.lever_scraper import LeverScraper
from .slack_bot import SlackBot
from .subscription_manager import SubscriptionManager
from dotenv import load_dotenv
import pathlib

# Load env variables from src/.env
env_path = pathlib.Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Main")

async def run_scraper_cycle():
    logger.info("Running scraper cycle...")
    
    # 1. Initialize DB (Sync for now, safe enough for low volume)
    Session = init_db()
    session = Session()
    
    # 2. Browser Manager
    browser_manager = BrowserManager(headless=True)
    await browser_manager.init()
    
    try:
        # 3. Initialize Scrapers & Bot
        scrapers = [
            BoeingScraper(browser_manager),
            IndeedScraper(browser_manager, search_terms=[
                "software engineer intern",
                "aerospace engineering intern",
                "finance intern"
            ]),
            SimplyHiredScraper(browser_manager, search_terms=[
                "software engineer intern",
                "aerospace engineering intern"
            ]),
            WellfoundScraper(browser_manager, search_terms=[
                "intern" # Broader term for startups
            ]),
            FoundItScraper(browser_manager, search_terms=[
                "software intern",
                "developer intern"
            ]),
            DribbbleScraper(browser_manager, search_terms=[
                "product design intern",
                "frontend intern"
            ]),
            GoogleSearchScraper(browser_manager, search_queries=[
                'site:boards.greenhouse.io "software engineer intern"',
                'site:jobs.lever.co "software engineer intern"'
            ])
            # Note: Greenhouse/Lever scrapers would be triggered 
            # if we had a list of board URLs to feed them. 
            # For now, GoogleSearchScraper will find the links.
        ]
        
        sub_manager = SubscriptionManager(Session)
        bot = SlackBot(subscription_manager=sub_manager) # Will use env vars or dry mode
        
        # 4. Run Scrapers concurrently
        tasks = [scraper.scrape() for scraper in scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_found_jobs = []
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Scraper failed: {res}")
            else:
                all_found_jobs.extend(res)
        
        # 5. Process Results
        new_jobs_count = 0
        for job_data in all_found_jobs:
            # Check if exists
            existing = session.query(Job).filter_by(id=job_data.id).first()
            if existing:
                continue
            
            # New Job Found
            
            # Date Filtering
            job_date = parse_job_date(job_data.date_posted)
            if job_date:
                days_old = (datetime.utcnow() - job_date).days
                if days_old > 7:
                    logger.info(f"Skipping old job: {job_data.title} (Posted {days_old} days ago)")
                    continue
            
            logger.info(f"New job detected: {job_data.title}")
            
            # Simple tag filtering
            # Note: We need to access the scraper that found it to use filter_interests? 
            # Or just move filter_interests to a utility or static method.
            # For now, just instantiating a helper or using one of the instances
            # Hack: use first scraper instance for filtering logic as it is shared
            tags = scrapers[0].filter_interests(job_data)
            
            # Save to DB
            new_job = Job(
                id=job_data.id,
                company=job_data.company,
                title=job_data.title,
                location=job_data.location,
                url=job_data.url,
                tags=tags
            )
            session.add(new_job)
            new_jobs_count += 1
            
            # Post to Slack
            await bot.post_job(job_data, tags)
            
        session.commit()
        logger.info(f"Cycle complete. Added {new_jobs_count} new jobs.")
        
    finally:
        session.close()
        await browser_manager.close()

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--now":
            asyncio.run(run_scraper_cycle())
        elif sys.argv[1] == "--seed":
            # Seed test subscriptions
            Session = init_db()
            manager = SubscriptionManager(Session)
            manager.add_subscription("U_TEST_USER", "software")
            manager.add_subscription("U_TEST_USER", "aerospace")
            print("Seeded test subscriptions for U_TEST_USER.")
    else:
        # Schedule it
        scheduler = AsyncIOScheduler()
        scheduler.add_job(run_scraper_cycle, 'interval', hours=4)
        logger.info("Scheduler started. Running every 4 hours.")
        print("Press Ctrl+C to exit")
        
        try:
            scheduler.start()
            # AsyncIOScheduler is non-blocking, so we need to keep the event loop running
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            pass

if __name__ == "__main__":
    main()
