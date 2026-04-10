import argparse
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .utils.date_utils import parse_job_date
from .database import init_db, job_exists, insert_job, get_subscribers_for_interests
from .browser_manager import BrowserManager
from .scraper_engine import filter_interests
from .scrapers.boeing_scraper import BoeingScraper
from .scrapers.simplyhired_scraper import SimplyHiredScraper
from .scrapers.workday_scraper import NissanScraper, WorkdayScraper, WorkdayPlaywrightScraper
from .scrapers.phenom_scraper import PhenomScraper
from .scrapers.automotive_scrapers import (
    TeslaScraper, StellantisScraper, VWGroupScraper,
    BMWScraper, MercedesScraper, VolvoScraper,
    HyundaiScraper, SubaruScraper,
)
from .scrapers.radancy_scraper import RadancyScraper
from .scrapers.greenhouse_scraper import SpaceXScraper
from .scrapers.eightfold_scraper import EightfoldScraper
from .scrapers.oracle_hcm_scraper import OracleHCMScraper
from .scrapers.tech_scrapers import AmazonScraper
from .scrapers.generic_playwright_scraper import GenericPlaywrightScraper


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

def build_scraper_registry(browser_manager):
    """Build a name -> scraper instance mapping for all available scrapers."""
    bm = browser_manager  # shorthand

    scrapers = [
        # ── Existing scrapers ─────────────────────────────────────────
        BoeingScraper(bm),
        SimplyHiredScraper(bm, search_terms=[
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
        NissanScraper(bm),
        PhenomScraper("Toyota", bm, "https://careers.toyota.com/us/en/search-results?keywords=intern", "https://careers.toyota.com"),
        PhenomScraper("Honda", bm, "https://careers.honda.com/us/en/search-results?keywords=intern", "https://careers.honda.com"),
        PhenomScraper("GM", bm, "https://search-careers.gm.com/en/?q=intern&location=United+States", "https://search-careers.gm.com"),
        PhenomScraper("Ford", bm, "https://www.careers.ford.com/en/home.html?SearchKeyword=intern", "https://www.careers.ford.com"),
        TeslaScraper(bm),
        StellantisScraper(bm),
        VWGroupScraper(bm),
        BMWScraper(bm),
        MercedesScraper(bm),
        VolvoScraper(bm),
        HyundaiScraper(bm),
        SubaruScraper(bm),

        # ── Greenhouse (API-based) ────────────────────────────────────
        SpaceXScraper(bm),

        # ── Workday API scrapers ──────────────────────────────────────
        WorkdayScraper("Airbus", bm, "ag.wd3.myworkdayjobs.com", "ag", "Airbus", "bc33aa3152ec42d4995f4791a106ed09"),
        WorkdayScraper("3M", bm, "3m.wd1.myworkdayjobs.com", "3m", "Search"),
        WorkdayScraper("NVIDIA", bm, "nvidia.wd5.myworkdayjobs.com", "nvidia", "NVIDIAExternalCareerSite"),
        WorkdayScraper("Coca-Cola", bm, "coke.wd1.myworkdayjobs.com", "coke", "coca-cola-careers", "bc33aa3152ec42d4995f4791a106ed09"),
        WorkdayScraper("Mondelez", bm, "wd3.myworkdaysite.com", "mdlz", "External"),
        WorkdayScraper("Enbridge", bm, "enbridge.wd3.myworkdayjobs.com", "enbridge", "Enbridge_Careers"),
        WorkdayScraper("Pentair", bm, "pentair.wd5.myworkdayjobs.com", "pentair", "Pentair_Careers"),
        WorkdayScraper("Stanley Black & Decker", bm, "sbdinc.wd1.myworkdayjobs.com", "sbdinc", "Stanley_Black_Decker_Career_Site", "bc33aa3152ec42d4995f4791a106ed09"),

        # ── Phenom People (new companies) ─────────────────────────────
        PhenomScraper("Continental", bm, "https://jobs.continental.com/en/search-results?keywords=intern", "https://jobs.continental.com"),
        PhenomScraper("Caterpillar", bm, "https://careers.caterpillar.com/en/search-results?keywords=intern", "https://careers.caterpillar.com"),
        PhenomScraper("Salesforce", bm, "https://careers.salesforce.com/en/search-results?keywords=intern", "https://careers.salesforce.com"),
        PhenomScraper("J&J", bm, "https://www.careers.jnj.com/en/search-results?keywords=intern", "https://www.careers.jnj.com"),
        PhenomScraper("RTX", bm, "https://careers.rtx.com/global/en/search-results?keywords=intern", "https://careers.rtx.com"),
        PhenomScraper("BAE Systems", bm, "https://jobs.baesystems.com/global/en/search-results?keywords=intern", "https://jobs.baesystems.com"),
        PhenomScraper("Honeywell", bm, "https://careers.honeywell.com/us/en/search-results?keywords=intern", "https://careers.honeywell.com"),
        PhenomScraper("ABB", bm, "https://careers.abb/global/en/search-results?keywords=intern", "https://careers.abb"),
        PhenomScraper("Adobe", bm, "https://careers.adobe.com/us/en/search-results?keywords=intern", "https://careers.adobe.com"),
        PhenomScraper("GE Aerospace", bm, "https://careers.geaerospace.com/global/en/search-results?keywords=intern", "https://careers.geaerospace.com"),
        PhenomScraper("TotalEnergies", bm, "https://careers.totalenergies.com/en/search-results?keywords=intern", "https://careers.totalenergies.com"),
        PhenomScraper("Mars", bm, "https://careers.mars.com/us/en/search-results?keywords=intern", "https://careers.mars.com"),
        PhenomScraper("Danone", bm, "https://careers.danone.com/en-global/search-results?keywords=intern", "https://careers.danone.com"),

        # ── Radancy / TalentBrew (Playwright) ─────────────────────────
        RadancyScraper("Lockheed Martin", bm, "https://www.lockheedmartinjobs.com"),
        RadancyScraper("L3Harris", bm, "https://careers.l3harris.com", search_path="/en/search-jobs/internship"),
        RadancyScraper("Johnson Controls", bm, "https://jobs.johnsoncontrols.com"),
        RadancyScraper("P&G", bm, "https://www.pgcareers.com"),
        RadancyScraper("Unilever", bm, "https://careers.unilever.com"),
        RadancyScraper("Kraft Heinz", bm, "https://careers.kraftheinzcompany.com"),
        RadancyScraper("General Mills", bm, "https://careers.generalmills.com"),
        RadancyScraper("Colgate-Palmolive", bm, "https://jobs.colgate.com"),
        RadancyScraper("Kimberly-Clark", bm, "https://careers.kimberly-clark.com", search_path="/en/search-jobs/internship"),
        RadancyScraper("Conagra", bm, "https://careers.conagrabrands.com"),
        RadancyScraper("Reckitt", bm, "https://careers.reckitt.com"),
        RadancyScraper("ExxonMobil", bm, "https://jobs.exxonmobil.com"),
        RadancyScraper("Chevron", bm, "https://careers.chevron.com"),
        WorkdayScraper("Shell", bm, "shell.wd3.myworkdayjobs.com", "shell", "shellcareers"),
        RadancyScraper("Halliburton", bm, "https://jobs.halliburton.com"),
        RadancyScraper("NextEra Energy", bm, "https://jobs.nexteraenergy.com"),
        RadancyScraper("ConocoPhillips", bm, "https://careers.conocophillips.com"),
        RadancyScraper("Dominion Energy", bm, "https://careers.dominionenergy.com"),
        RadancyScraper("Bank of America", bm, "https://careers.bankofamerica.com", search_path="/en-us/search-jobs/internship"),
        RadancyScraper("Citigroup", bm, "https://jobs.citi.com"),
        WorkdayScraper("Intel", bm, "intel.wd1.myworkdayjobs.com", "intel", "External"),

        # ── Eightfold.ai (Playwright) ─────────────────────────────────
        EightfoldScraper("Eaton", bm, "https://eaton.eightfold.ai/careers?query=intern&location=United%20States", "https://eaton.eightfold.ai"),
        # Siemens migrated to new portal — needs updated URL
        # EightfoldScraper("Siemens", bm, "https://jobs.siemens.com/careers?query=intern&location=United%20States", "https://jobs.siemens.com"),
        EightfoldScraper("PepsiCo", bm, "https://www.pepsicojobs.com/main/jobs?query=intern&location=United%20States", "https://www.pepsicojobs.com"),
        EightfoldScraper("Nestle", bm, "https://www.nestlejobs.com/nestle-usa/jobs?query=intern", "https://www.nestlejobs.com"),
        EightfoldScraper("Cisco", bm, "https://jobs.cisco.com/jobs/SearchJobs?query=intern&location=United%20States", "https://jobs.cisco.com"),
        EightfoldScraper("ServiceNow", bm, "https://careers.servicenow.com/careers/jobs?query=intern&location=United%20States", "https://careers.servicenow.com"),
        EightfoldScraper("Wells Fargo", bm, "https://www.wellsfargojobs.com/en/jobs?query=intern&location=United%20States", "https://www.wellsfargojobs.com"),

        # ── Oracle HCM (API-based) ────────────────────────────────────
        OracleHCMScraper("Emerson", bm, "hdjq.fa.us2.oraclecloud.com", "CX_1", "https://hdjq.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1"),
        OracleHCMScraper("Oracle", bm, "eeho.fa.us2.oraclecloud.com", "CX_1", "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1"),
        OracleHCMScraper("JPMorgan", bm, "jpmc.fa.oraclecloud.com", "CX_1001", "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001"),

        # ── Amazon (custom JSON API) ─────────────────────────────────
        AmazonScraper(bm),

        # ── Workday Playwright fallback (API returns 422) ────────────
        WorkdayScraper("Northrop Grumman", bm, "ngc.wd1.myworkdayjobs.com", "ngc", "Northrop_Grumman_External_Site"),
        WorkdayPlaywrightScraper("BP", bm, "https://bp.wd3.myworkdayjobs.com/en-US/BP_Careers"),
        WorkdayPlaywrightScraper("Clorox", bm, "https://clorox.wd5.myworkdayjobs.com/en-US/CloroxExternal"),
        WorkdayPlaywrightScraper("ITT", bm, "https://itt.wd5.myworkdayjobs.com/en-US/ITT_Careers"),
        WorkdayPlaywrightScraper("KPMG", bm, "https://kpmg.wd5.myworkdayjobs.com/en-US/KPMG_Careers"),
        WorkdayPlaywrightScraper("AEP", bm, "https://aep.wd5.myworkdayjobs.com/en-US/AEP_Careers"),
        WorkdayPlaywrightScraper("General Dynamics", bm, "https://generaldynamics.wd1.myworkdayjobs.com/en-US/GeneralDynamics"),
        WorkdayPlaywrightScraper("Rolls-Royce", bm, "https://rolls-royce.wd3.myworkdayjobs.com/en-US/Careers"),
        WorkdayPlaywrightScraper("Textron", bm, "https://textron.wd1.myworkdayjobs.com/en-US/Textron"),
        WorkdayPlaywrightScraper("IBM", bm, "https://ibm.wd1.myworkdayjobs.com/en-US/IBMExternalSite"),
        WorkdayPlaywrightScraper("Broadcom", bm, "https://broadcom.wd1.myworkdayjobs.com/en-US/BroadcomCareers"),
        WorkdayPlaywrightScraper("PwC", bm, "https://wd5.myworkdaysite.com/recruiting/pwc/Global_Experienced_Careers"),
        WorkdayPlaywrightScraper("Thales", bm, "https://thales.wd3.myworkdayjobs.com/en-US/ThalesExternalSite"),

        # ── Big Tech (custom Playwright) ─────────────────────────────
        GenericPlaywrightScraper("Google", bm,
            "https://www.google.com/about/careers/applications/jobs/results/?q=intern&target_level=INTERN_AND_APPRENTICE&location=United%20States",
            "https://www.google.com"),
        GenericPlaywrightScraper("Microsoft", bm,
            "https://jobs.careers.microsoft.com/global/en/search?q=intern&lc=United%20States&exp=Student%2FRecent%20Graduate&et=Internship",
            "https://jobs.careers.microsoft.com"),
        GenericPlaywrightScraper("Apple", bm,
            "https://jobs.apple.com/en-us/search?search=intern&sort=newest&team=internships-STDNT-INTRN",
            "https://jobs.apple.com"),
        GenericPlaywrightScraper("Meta", bm,
            "https://www.metacareers.com/jobs?q=intern&offices[0]=United%20States",
            "https://www.metacareers.com"),
        GenericPlaywrightScraper("Goldman Sachs", bm,
            "https://higher.gs.com/roles?query=intern&location=United+States",
            "https://higher.gs.com"),

        # ── iCIMS / custom career sites (Playwright) ─────────────────
        GenericPlaywrightScraper("SAIC", bm,
            "https://jobs.saic.com/search/jobsearchaction?q=intern&locname=United+States",
            "https://jobs.saic.com"),
        GenericPlaywrightScraper("Leidos", bm,
            "https://careers.leidos.com/search/jobs?q=intern&location=United+States",
            "https://careers.leidos.com"),
        GenericPlaywrightScraper("Southern Company", bm,
            "https://southerncompany.jobs/jobs/?q=intern",
            "https://southerncompany.jobs"),

        # ── Avature career sites (Playwright) ────────────────────────
        GenericPlaywrightScraper("Deloitte", bm,
            "https://apply.deloitte.com/careers/SearchJobs?q=intern&locname=United+States",
            "https://apply.deloitte.com"),
        GenericPlaywrightScraper("EY", bm,
            "https://careers.ey.com/ey/search?q=intern&location=United+States",
            "https://careers.ey.com"),
        GenericPlaywrightScraper("SLB", bm,
            "https://careers.slb.com/fojoblist/it-en/?q=intern",
            "https://careers.slb.com"),
        GenericPlaywrightScraper("Schneider Electric", bm,
            "https://www.se.com/us/en/about-us/careers/job-search.jsp?q=intern",
            "https://www.se.com"),
        GenericPlaywrightScraper("Accenture", bm,
            "https://www.accenture.com/us-en/careers/jobsearch?jk=intern&sb=0&vw=0&is_rj=0&ct=United+States",
            "https://www.accenture.com"),

        # ── SAP SuccessFactors / misc (Playwright) ───────────────────
        GenericPlaywrightScraper("Bosch", bm,
            "https://www.bosch.us/careers/job-offers/?keywords=intern",
            "https://www.bosch.us"),
        GenericPlaywrightScraper("Rheinmetall", bm,
            "https://www.rheinmetall.com/en/career?q=intern",
            "https://www.rheinmetall.com"),
        GenericPlaywrightScraper("SAP", bm,
            "https://jobs.sap.com/search?q=intern&locationsSearch=United+States",
            "https://jobs.sap.com"),
        GenericPlaywrightScraper("Parker-Hannifin", bm,
            "https://parkercareers.ttcportals.com/jobs/search?q=intern",
            "https://parkercareers.ttcportals.com"),
        GenericPlaywrightScraper("Morgan Stanley", bm,
            "https://morganstanley.tal.net/vx/lang-en-GB/mobile-0/brand-2/xf-53f9e5d0041a/candidate/jobboard/vacancy/1/adv/?q=intern",
            "https://morganstanley.tal.net"),
    ]
    # Key by lowercase company_name for easy lookup
    return {s.company_name.lower(): s for s in scrapers}


async def run_scraper_cycle(scraper_names=None):
    logger.info("Running scraper cycle...")

    # 1. Initialize DB
    db = init_db()

    # 2. Browser Manager
    browser_manager = BrowserManager(headless=True)
    await browser_manager.init()

    try:
        # 3. Initialize Scrapers & Bot
        registry = build_scraper_registry(browser_manager)

        if scraper_names:
            # Run only the requested scrapers
            scrapers = []
            for name in scraper_names:
                key = name.lower()
                if key not in registry:
                    logger.error(f"Unknown scraper: '{name}'. Use --list to see available scrapers.")
                    return
                scrapers.append(registry[key])
            logger.info(f"Running selected scrapers: {[s.company_name for s in scrapers]}")
        else:
            scrapers = list(registry.values())

        sub_manager = SubscriptionManager(db)
        bot = SlackBot(subscription_manager=sub_manager) # Will use env vars or dry mode

        # 4. Run Scrapers concurrently with bounded concurrency + per-scraper timeout
        # - Limits parallel browser contexts to prevent severe contention
        # - Enforces a hard timeout per scraper so one hung site can't block the whole run
        MAX_CONCURRENT_SCRAPERS = 8
        PER_SCRAPER_TIMEOUT = 300  # 5 minutes
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPERS)

        async def run_one(scraper):
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        scraper.scrape(), timeout=PER_SCRAPER_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        f"[{scraper.company_name}] Timed out after {PER_SCRAPER_TIMEOUT}s — skipping"
                    )
                    return []
                except Exception as e:
                    logger.error(f"[{scraper.company_name}] Scraper failed: {e}")
                    return []

        tasks = [run_one(scraper) for scraper in scrapers]
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
            if job_exists(db, job_data.id):
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

        # Second pass: commit new jobs to DB, then group by category and post
        committed_jobs = []  # track jobs that were saved to DB
        for job_data, tags in new_jobs:
            logger.info(f"New job detected: {job_data.title}")
            insert_job(db, {
                "id": job_data.id,
                "company": job_data.company,
                "title": job_data.title,
                "location": job_data.location,
                "url": job_data.url,
                "tags": tags
            })
            committed_jobs.append((job_data, tags))

        # Group jobs by category (a job appears under every matching category)
        category_jobs = defaultdict(list)
        for job_data, tags in committed_jobs:
            for tag in tags:
                category_jobs[tag].append((job_data, tags))

        # Post each category as its own thread
        for category, jobs in category_jobs.items():
            subscribers = get_subscribers_for_interests(db, [category])
            logger.info(f"Category '{category}': {len(jobs)} jobs, subscribers={subscribers}")
            thread_ts = await bot.post_category_header(category, subscribers, len(jobs))
            for job_data, tags in jobs:
                await bot.post_job(job_data, tags, thread_ts=thread_ts)

        logger.info(f"Cycle complete. Added {len(committed_jobs)} new jobs across {len(category_jobs)} categories.")

    finally:
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
    parser = argparse.ArgumentParser(description="Job Scraper — find internship & entry-level postings")
    parser.add_argument("--now", action="store_true", help="Run a single scraper cycle immediately")
    parser.add_argument("--scraper", nargs="+", metavar="NAME",
                        help="Run only the named scraper(s). Use --list to see available names.")
    parser.add_argument("--list", action="store_true", dest="list_scrapers",
                        help="List all available scraper names and exit")
    args = parser.parse_args()

    if args.list_scrapers:
        # Build registry without browser to just list names
        from .scraper_engine import BaseScraper
        # We need a browser_manager stub just to instantiate — use None and catch
        # Instead, just build and print names
        bm = type('FakeBM', (), {'get_new_context': None})()
        try:
            registry = build_scraper_registry(bm)
        except Exception:
            # Fallback: just print a static list
            print("Could not build registry. Check scraper constructors.")
            return
        print("Available scrapers:")
        for name in sorted(registry.keys()):
            print(f"  {name}")
        return

    if args.now or args.scraper:
        asyncio.run(run_scraper_cycle(scraper_names=args.scraper))
    else:
        print("Press Ctrl+C to exit")
        try:
            asyncio.run(run_scheduler())
        except (KeyboardInterrupt, SystemExit):
            pass

if __name__ == "__main__":
    main()
