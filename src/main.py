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
from .scrapers.simplyhired_scraper import SimplyHiredScraper


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
    # Switch to headless=False to bypass basic Cloudflare/CAPTCHA detection for debugging
    browser_manager = BrowserManager(headless=False)
    await browser_manager.init()
    
    try:
        # 3. Initialize Scrapers & Bot
        scrapers = [
            BoeingScraper(browser_manager),
            SimplyHiredScraper(browser_manager, search_terms=[
                "software engineer intern",
                "aerospace engineering intern",
                "automotive engineering intern",
                "finance intern",
                "manufacturing intern", 
                "supply chain intern",
                "hardware engineering intern",
                "embedded systems intern",
                "semiconductor intern", 
                "VLSI intern"
            ]),

            # Note: Greenhouse/Lever scrapers would be triggered 
            # if we had a list of board URLs to feed them.
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
        parent_thread_ts = None
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
            # Create a thread for this batch if it's the first job of the batch, or reuse existing?
            # Ideally we want ONE parent message for the whole cycle. 
            # But the cycle logic is streaming jobs one by one.
            # Let's start the thread BEFORE the loop if we found jobs? 
            # Actually, we are iterating `all_found_jobs`. We can check if `new_jobs_count == 0` to start it.
            
            if new_jobs_count == 0 and not parent_thread_ts:
                 # This is the first new job we are about to save. Start the thread.
                 parent_thread_ts = await bot.post_message(f"🚀 *Scraper Cycle Started*: Finding new jobs...")
            
            await bot.post_job(job_data, tags, thread_ts=parent_thread_ts)
            
        session.commit()
        session.commit()
        logger.info(f"Cycle complete. Added {new_jobs_count} new jobs.")
        
        if parent_thread_ts and bot.client:
             # Update the parent message to show final count
             await bot.client.chat_update(
                 channel=bot.channel,
                 ts=parent_thread_ts,
                 text=f"✅ *Scraper Cycle Complete*: Found {new_jobs_count} new jobs today."
             )
        
    finally:
        session.close()
        await browser_manager.close()

async def run_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_scraper_cycle, 'interval', hours=24)
    logger.info("Scheduler started. Running every 24 hours.")
    scheduler.start()
    
    # Log next run time
    jobs = scheduler.get_jobs()
    if jobs:
        next_run = jobs[0].next_run_time
        logger.info(f"Next scraper cycle scheduled for: {next_run}")

    # Keep the task alive
    while True:
        await asyncio.sleep(3600)

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--now":
            asyncio.run(run_scraper_cycle())
    else:
        print("Press Ctrl+C to exit")
        try:
            asyncio.run(run_scheduler())
        except (KeyboardInterrupt, SystemExit):
            pass

if __name__ == "__main__":
    main()
