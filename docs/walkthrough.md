# Job Scraper Project Walkthrough

This document outlines the current state of the Job Scraper project, recent changes, and the upcoming roadmap.

## Current Capabilities

The system currently is capable of:
1. **Scraping Boeing Jobs**:
    - Visits multiple starting URLs (General Search + Specific Intern Search).
    - Extracts Job Title, Company, Location, URL, and Date.
    - Filters for relevant "Intern" or "Entry Level" roles.
2. **Data Persistence**:
    - Stores found jobs in a local SQLite database (`jobs.db`).
    - Prevents duplicate alerts for the same job ID.
3. **Notification System (Dry-Run)**:
    - The `SlackBot` class is implemented but currently runs in "Dry Run" mode, printing job alerts to the console instead of sending real messages.

## Recent Changes

### Multi-URL Support
I modified `src/scrapers/boeing_scraper.py` to support scanning multiple URLs. This allows us to target deep links like the "intern" search page directly.

```python
self.start_urls = [
    "https://jobs.boeing.com/search-jobs",
    "https://jobs.boeing.com/search-jobs/intern/185/1"
]
```

## Upcoming Roadmap

We have defined the following major tasks for the next phase:

1. **Pagination System**: Update scrapers to automatically traverse all pages of results.
2. **Slack Integration**: Enable real Slack notifications using the `slack_sdk`.
3. **Role-Based Notifications**: Tag specific Slack groups (e.g., `@engineers`, `@finance`) based on job categories.
4. **Massive Scale**: Architect the system to handle scraping hundreds of thousands of companies.

## Verification

The current system has been verified to run locally:
```bash
python -m src.main --now
```
Output:
> [Boeing] Found 4 jobs.
> New job detected: 2026 Summer Intern: Logistics
> --- [DRY RUN] SLACK POST ---
