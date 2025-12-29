import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class SlackBot:
    def __init__(self, token=None, channel=None):
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        self.channel = channel or os.getenv("SLACK_CHANNEL")
        # If no token, we are in dry run mode
        self.client = WebClient(token=self.token) if self.token else None

    def post_job(self, job_data, tags: list):
        """
        Post a job to Slack.
        tags: list of strings (e.g. ['aerospace', 'finance'])
        """
        tag_str = " ".join([f"#{tag}" for tag in tags])  # Simple hashtags for now, mentions need IDs
        
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
                    "text": f"*Type:* Internship/Entry-Level (Detected)\n{tag_str}"
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
                self.client.chat_postMessage(
                    channel=self.channel,
                    blocks=message_blocks,
                    text=f"New Job: {job_data.title}" # Fallback text
                )
            except SlackApiError as e:
                print(f"Error posting to Slack: {e.response['error']}")
        else:
            print("--- [DRY RUN] SLACK POST ---")
            print(f"Title: {job_data.title}")
            print(f"Company: {job_data.company}")
            print(f"Tags: {tag_str}")
            print(f"URL: {job_data.url}")
            print("----------------------------")
