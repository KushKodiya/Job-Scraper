import os
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import pathlib

env_path = pathlib.Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class SlackBot:
    def __init__(self, token=None, channel=None, subscription_manager=None):
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        self.channel = channel or os.getenv("SLACK_CHANNEL")
        # If no token, we are in dry run mode
        if self.token:
            # Fix for SSL Cert Error on some Macs/Environments
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
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

    async def post_job(self, job_data, tags: list, thread_ts: str = None):
        """
        Post a job to Slack.
        tags: list of strings (e.g. ['aerospace', 'finance'])
        thread_ts: Optional timestamp of parent message to thread this reply under.
        """
        tag_str = " ".join([f"#{tag}" for tag in tags])
        
        # Calculate Mentions
        mentions_str = ""
        if self.sub_manager:
            subscribers = self.sub_manager.get_subscribers_for_tags(tags)
            if subscribers:
                mentions_str = " ".join([f"<@{uid}>" for uid in subscribers])
                mentions_str = f"\n*Heads up:* {mentions_str}"
        
        message_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{job_data.title}*\n{job_data.company} | {job_data.location}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Type:* Internship/Entry-Level (Detected)\n{tag_str}{mentions_str}"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Apply Now",
                        "emoji": True
                    },
                    "url": job_data.url,
                    "action_id": "button-action"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        if self.client:
            try:
                # Rate limit protection: 1 msg/sec limit usually
                import asyncio
                await asyncio.sleep(1.2)
                
                await self.client.chat_postMessage(
                    channel=self.channel,
                    blocks=message_blocks,
                    text=f"New Job: {job_data.title}", # Fallback text
                    thread_ts=thread_ts # Post in thread if provided
                )
            except SlackApiError as e:
                print(f"Error posting to Slack: {e.response['error']}")
        else:
            print("--- [DRY RUN] SLACK POST ---")
            print(f"Parent Thread: {thread_ts}")
            print(f"Title: {job_data.title}")
            print(f"Company: {job_data.company}")
            print(f"Tags: {tag_str}")
            print(f"Mentions: {mentions_str}")
            print(f"URL: {job_data.url}")
            print("----------------------------")
