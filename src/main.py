import sys
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .utils.date_utils import parse_job_date
from .database import init_db, Job
from .browser_manager import BrowserManager
from .scraper_engine import filter_interests
from .scrapers.boeing_scraper import BoeingScraper
from .scrapers.simplyhired_scraper import SimplyHiredScraper
from .scrapers.workday_scraper import NissanScraper
from .scrapers.phenom_scraper import PhenomScraper
from .scrapers.automotive_scrapers import (
    TeslaScraper, StellantisScraper, VWGroupScraper,
    BMWScraper, MercedesScraper, VolvoScraper,
    HyundaiScraper, SubaruScraper,
)


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
            # Workday API scraper
            NissanScraper(browser_manager),
            # Phenom People platform
            PhenomScraper("Toyota", browser_manager, "https://careers.toyota.com/us/en/search-results?keywords=intern", "https://careers.toyota.com"),
            PhenomScraper("Honda", browser_manager, "https://careers.honda.com/us/en/search-results?keywords=intern", "https://careers.honda.com"),
            PhenomScraper("GM", browser_manager, "https://search-careers.gm.com/en/?q=intern&location=United+States", "https://search-careers.gm.com"),
            PhenomScraper("Ford", browser_manager, "https://www.careers.ford.com/en/home.html?SearchKeyword=intern", "https://www.careers.ford.com"),
            # Tesla REST API
            TeslaScraper(browser_manager),
            # Playwright-based automotive scrapers
            StellantisScraper(browser_manager),
            VWGroupScraper(browser_manager),
            BMWScraper(browser_manager),
            MercedesScraper(browser_manager),
            VolvoScraper(browser_manager),
            HyundaiScraper(browser_manager),
            SubaruScraper(browser_manager),
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
        
        # 5. Process Results — first pass: identify genuinely new, recent jobs
        new_jobs = []  # list of (job_data, tags) tuples
        seen_ids = set()  # deduplicate within this run (before DB commit)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for job_data in all_found_jobs:
            if job_data.id in seen_ids:
                continue
            existing = session.query(Job).filter_by(id=job_data.id).first()
            if existing:
                continue

            # Date filtering
            job_date = parse_job_date(job_data.date_posted)
            if job_date:
                days_old = (now - job_date).days
                if days_old > 7:
                    logger.info(f"Skipping old job: {job_data.title} (Posted {days_old} days ago)")
                    continue
            elif job_data.date_posted is not None:
                # date_posted text exists but couldn't be parsed — log a warning and include
                logger.warning(f"Could not parse date '{job_data.date_posted}' for: {job_data.title} — including anyway")

            seen_ids.add(job_data.id)
            tags = filter_interests(job_data)
            new_jobs.append((job_data, tags))

        # Second pass: create Slack thread (only if there are new jobs), then save and post
        parent_thread_ts = None
        if new_jobs:
            parent_thread_ts = await bot.post_message("🚀 *Scraper Cycle Started*: Finding new jobs...")

        for job_data, tags in new_jobs:
            logger.info(f"New job detected: {job_data.title}")
            new_job = Job(
                id=job_data.id,
                company=job_data.company,
                title=job_data.title,
                location=job_data.location,
                url=job_data.url,
                tags=tags
            )
            session.add(new_job)
            session.commit()
            await bot.post_job(job_data, tags, thread_ts=parent_thread_ts)
        logger.info(f"Cycle complete. Added {len(new_jobs)} new jobs.")
        
        if parent_thread_ts and bot.client:
            await bot.client.chat_update(
                channel=bot.channel,
                ts=parent_thread_ts,
                text=f"✅ *Scraper Cycle Complete*: Found {len(new_jobs)} new jobs today."
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
