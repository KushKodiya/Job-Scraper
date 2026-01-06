# Job Scraper User Guide

Welcome! This tool automatically searches the web for new **Internship** and **Co-op** opportunities and posts them to our Slack channel.

## 🤖 What does it do?

Every 24 hours, the Internship Bot scans major job boards and company sites (like **Boeing**, **SimplyHired**, etc.) for fresh listings.

-   **Daily Summary**: The bot posts a single "Cycle Started" message each day.
-   **Threaded Alerts**: All new jobs found are posted as **replies** to that thread to keep the channel clean.
-   **Smart Tagging**: Use the subscription system to get notified only for the roles *you* care about.

## 🔔 How to Subscribe

You can subscribe to specific "Interest Tags." If a job matches your tag, the bot will **mention you** (`@You`) in the alert so you never miss it.

### Commands

| Command | Description |
| :--- | :--- |
| `/subscribe` | Shows a list of all available job categories/tags. |
| `/subscribe [tag]` | Subscribe to a tag (e.g., `/subscribe software`). |
| `/my-subs` | See a list of your current subscriptions. |
| `/unsubscribe [tag]` | Stop receiving notifications for a tag. |

### Available Categories

*   **`aerospace`**: Rockets, avionics, propulsion, and defense.
*   **`software`**: Development, data science, AI, and engineering.
*   **`automotive`**: Autonomous vehicles, ADAS, and EVs.
*   **`finance`**: Banking, trading, audit, and analysis.
*   **`manufacturing`**: Production, supply chain, and operations.
*   **`ece hardware`**: Circuits, FPGA, embedded systems, and electronics.
*   **`semiconductors`**: Chip design, lithography, FAB, and VLSI.
*   **`general`**: Business, marketing, HR, and sales.

## 🚀 Tips

*   **Check the Thread**: Always click into the "Cycle Started" thread to see the full list of jobs.
*   **Apply Fast**: These scrapers look for *fresh* postings, so apply as soon as you get the notification!
