# Tasks

- [x] Support scraping "intern" roles from Boeing <!-- id: 0 -->
    - [x] Analyze `src/scrapers/boeing_scraper.py` <!-- id: 1 -->
    - [x] Update scraper to target intern roles (URL or search query) <!-- id: 2 -->
    - [x] Verify scraper finds intern jobs <!-- id: 3 -->

- [ ] Create a pagination system <!-- id: 4 -->
    - [ ] Inspect pagination mechanism (confirm URL pattern `.../page/X`) <!-- id: 5 -->
    - [ ] Update `BoeingScraper` to loop through pages until no jobs found <!-- id: 6 -->
    - [ ] Verify scraper captures jobs from multiple pages <!-- id: 7 -->

- [ ] Set up Slack notifications <!-- id: 8 -->
    - [ ] Setup `.env` file with `SLACK_BOT_TOKEN` and `SLACK_CHANNEL` <!-- id: 11 -->
    - [ ] Remove "Dry Run" mode from `slack_bot.py` <!-- id: 12 -->
    - [ ] Send a test notification to Slack <!-- id: 13 -->

- [ ] Set up different notification roles on Slack <!-- id: 9 -->
    - [ ] Define mapping of Job Tags to Slack Users/Groups (e.g. `aerospace` -> `@engineers`, `finance` -> `@finance`) <!-- id: 14 -->
    - [ ] Update `SlackBot.post_job` to include mentions based on tags <!-- id: 15 -->
    - [ ] Verify correct users are mentioned for specific jobs <!-- id: 16 -->

- [ ] Scrape jobs for hundreds of thousands of companies <!-- id: 10 -->
    - [ ] Research/Design generic scraper architecture (Config-based vs Auto-detection) <!-- id: 17 -->
    - [ ] Implement a `GenericScraper` class for common ATS (Workday, Greenhouse, Lever) <!-- id: 18 -->
    - [ ] Create a system to manage/queue thousands of scraping tasks <!-- id: 19 -->
    - [ ] Optimize for rate limits and proxies <!-- id: 20 -->

