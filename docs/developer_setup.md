# Setup & Developer Guide

This guide explains how to set up, run, and customize the Job Scraper.

## 1. Setup

### Prerequisites
- Python 3.9+
- Chrome/Chromium (installed automatically by Playwright)

### Installation
1.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Install Browser Binaries**:
    ```bash
    playwright install chromium
    ```

3.  **Environment Variables**:
    Create a file named `.env` in `src/.env` (or root) with your Slack tokens:
    ```env
    SLACK_BOT_TOKEN=xoxb-your-bot-token...
    SLACK_APP_TOKEN=xapp-your-app-token...
    SLACK_CHANNEL=C12345678  # Channel ID to post jobs to
    ```

## 2. Running the Scraper

There are two modes to run the scraper:

### Manual Run (Immediate)
Runs one cycle immediately and exits. Use this to test or force an update.
```bash
python3 -m src.main --now
```

### Scheduled Mode (Daemon)
Runs continuously and triggers a scrape every 24 hours.
```bash
python3 -m src.main
```
*   **Logging**: The scraper logs to the console.
*   **Rate Limits**: The bot pauses for 1.2 seconds between messages to avoid Slack rate limits.
*   **Threading**: It creates a single "Cycle Started" thread and replies to it with all found jobs.

## 3. Slack Integration (Subscriptions)

To allow users to subscribe to specific job tags (e.g., `#software`, `#aerospace`), run the Slack Bolt server:

```bash
python3 -m src.server
```
*Note: This must be running for slash commands to work.*
