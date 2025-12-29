import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from .database import init_db, Job
from .scrapers.boeing_scraper import BoeingScraper
from .slack_bot import SlackBot

def run_scraper_cycle():
    print(f"Running scraper cycle at {datetime.now()}")
    
    # 1. Initialize DB
    Session = init_db()
    session = Session()
    
    # 2. Initialize Scrapers & Bot
    scrapers = [BoeingScraper()]
    bot = SlackBot() # Will use env vars or dry mode
    
    for scraper in scrapers:
        found_jobs = scraper.scrape()
        
        for job_data in found_jobs:
            # Check if exists
            existing = session.query(Job).filter_by(id=job_data.id).first()
            if existing:
                continue
            
            # New Job Found
            print(f"New job detected: {job_data.title}")
            
            # Save to DB
            new_job = Job(
                id=job_data.id,
                company=job_data.company,
                title=job_data.title,
                location=job_data.location,
                url=job_data.url,
                tags=scraper.filter_interests(job_data)
            )
            session.add(new_job)
            
            # Post to Slack
            bot.post_job(job_data, new_job.tags)
            
    session.commit()
    session.close()
    print("Cycle complete.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        run_scraper_cycle()
    else:
        # Schedule it
        scheduler = BlockingScheduler()
        scheduler.add_job(run_scraper_cycle, 'interval', hours=4)
        print("Scheduler started. Running every 4 hours.")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            pass
