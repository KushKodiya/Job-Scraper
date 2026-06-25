import os
from urllib.parse import urlparse
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import pathlib

env_path = pathlib.Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


def slack_escape(text) -> str:
    """Escape text that comes from untrusted scraped sources before putting it
    into Slack message text. Per Slack's API, only &, < and > are special, and
    escaping them prevents control sequences like <!channel>, <!everyone> or
    <@USERID> in a scraped job title from triggering broadcast pings or mentions.
    The order matters: & must be escaped first.
    """
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def is_safe_url(url) -> bool:
    """Only allow http(s) links to be rendered as clickable buttons, so a
    scraped href can't smuggle in a javascript:/data: or other scheme."""
    if not url:
        return False
    try:
        scheme = urlparse(str(url)).scheme.lower()
    except Exception:
        return False
    return scheme in ("http", "https")

class SlackBot:
    def __init__(self, token=None, channel=None, subscription_manager=None):
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        self.channel = channel or os.getenv("SLACK_CHANNEL")
        # If no token, we are in dry run mode
        if self.token:
            import ssl
            import certifi
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            self.client = AsyncWebClient(token=self.token, ssl=ssl_context)
        else:
            self.client = None
            
        self.sub_manager = subscription_manager

    async def post_message(self, text: str) -> str:
        """Post a simple message and return its timestamp (ts) for threading."""
        if self.client:
            try:
                response = await self.client.chat_postMessage(
                    channel=self.channel,
                    text=text
                )
                return response["ts"]
            except SlackApiError as e:
                print(f"Error posting parent message: {e.response['error']}")
                return None
        return None

    async def post_category_header(self, category: str, subscribers: list, job_count: int) -> str:
        """Post a category header message with subscriber pings. Returns thread timestamp."""
        mentions_str = ""
        if subscribers:
            mentions_str = "\n" + " ".join([f"<@{uid}>" for uid in subscribers])

        text = f"*{category.title()}* — {job_count} new job{'s' if job_count != 1 else ''}{mentions_str}"

        if self.client:
            try:
                import asyncio
                await asyncio.sleep(1.2)
                response = await self.client.chat_postMessage(
                    channel=self.channel,
                    text=text
                )
                return response["ts"]
            except SlackApiError as e:
                print(f"Error posting category header: {e.response['error']}")
                return None
        else:
            print(f"--- [DRY RUN] CATEGORY HEADER ---")
            print(f"Category: {category}")
            print(f"Job Count: {job_count}")
            print(f"Mentions: {mentions_str}")
            print(f"---------------------------------")
            return f"dry-run-{category}"

    async def post_job(self, job_data, tags: list, thread_ts: str = None):
        """
        Post a job to Slack as a thread reply.
        tags: list of strings (e.g. ['aerospace', 'finance'])
        thread_ts: Optional timestamp of parent message to thread this reply under.
        """
        tag_str = " ".join([f"#{slack_escape(tag)}" for tag in tags])

        # Escape all scraped fields — titles/company/location are untrusted and
        # could otherwise contain Slack control sequences (e.g. <!channel>).
        title = slack_escape(job_data.title)
        company = slack_escape(job_data.company)
        location = slack_escape(job_data.location)

        detail_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Type:* Internship/Entry-Level (Detected)\n{tag_str}"
            }
        }
        # Only render the Apply button for valid http(s) URLs; otherwise Slack
        # would reject the whole message (or we'd post an unsafe scheme).
        if is_safe_url(job_data.url):
            detail_block["accessory"] = {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Apply Now",
                    "emoji": True
                },
                "url": job_data.url,
                "action_id": "button-action"
            }

        message_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*\n{company} | {location}"
                }
            },
            detail_block,
            {
                "type": "divider"
            }
        ]

        if self.client:
            try:
                import asyncio
                await asyncio.sleep(1.2)

                await self.client.chat_postMessage(
                    channel=self.channel,
                    blocks=message_blocks,
                    text=f"New Job: {title}",
                    thread_ts=thread_ts
                )
            except SlackApiError as e:
                print(f"Error posting to Slack: {e.response['error']}")
        else:
            print("--- [DRY RUN] SLACK POST ---")
            print(f"Parent Thread: {thread_ts}")
            print(f"Title: {job_data.title}")
            print(f"Company: {job_data.company}")
            print(f"Tags: {tag_str}")
            print(f"URL: {job_data.url}")
            print("----------------------------")
