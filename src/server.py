import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from .database import init_db
from .subscription_manager import SubscriptionManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SlackServer")

# Load environment variables
from dotenv import load_dotenv
import pathlib
# Path to .env file (current dir/src/.env or just .env if running from root)
# Let's try to load from where the file is found
env_path = pathlib.Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize App
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Initialize DB & Manager
Session = init_db()
sub_manager = SubscriptionManager(Session)

CATEGORIES = {
    'aerospace': 'Rockets, avionics, propulsion, and defense.',
    'software': 'Development, data science, AI, and engineering.',
    'automotive': 'Autonomous vehicles, ADAS, and EVs.',
    'finance': 'Banking, trading, audit, and analysis.',
    'manufacturing': 'Production, supply chain, and operations.',
    'ece hardware': 'Circuits, FPGA, embedded systems, and electronics.',
    'semiconductors': 'Chip design, lithography, FAB, and VLSI.',
    'general': 'Business, marketing, HR, and sales.',
    'other': 'Miscellaneous roles.'
}

@app.command("/subscribe")
def handle_subscribe(ack, respond, command):
    ack()
    user_id = command['user_id']
    text = command['text'].strip().lower()
    
    if not text:
        # Show help with categories
        msg = "*Available Job Categories:*\n"
        for cat, desc in CATEGORIES.items():
            msg += f"• *{cat}*: {desc}\n"
        
        msg += "\nUsage: `/subscribe <category>`"
        respond(msg)
        return
        
    sub_manager.add_subscription(user_id, text)
    respond(f"✅ Subscribed to `#{text}`. You will be notified when jobs match this tag.")

@app.command("/unsubscribe")
def handle_unsubscribe(ack, respond, command):
    ack()
    user_id = command['user_id']
    text = command['text'].strip().lower()
    
    if not text:
        respond("Please specify an interest to unsubscribe from. Usage: `/unsubscribe <interest>`")
        return
        
    sub_manager.remove_subscription(user_id, text)
    respond(f"❌ Unsubscribed from `#{text}`.")

@app.command("/my-subs")
def handle_list_subs(ack, respond, command):
    ack()
    user_id = command['user_id']
    
    # We need a method in manager to list subs for a user
    # Adding ad-hoc query here or updating manager (Updating manager is cleaner but let's do a quick query for now if needed, 
    # but Manager is better).
    # Since Manager doesn't have list_user_subs yet, let's just implement it here via session or update manager.
    # Let's update manager later, for now direct session usage to be quick
    
    from .database import Subscription
    session = Session()
    try:
        subs = session.query(Subscription).filter_by(user_id=user_id).all()
        if not subs:
            respond("You have no active subscriptions.")
        else:
            sub_list = ", ".join([f"`#{s.interest}`" for s in subs])
            respond(f"You are subscribed to: {sub_list}")
    finally:
        session.close()

if __name__ == "__main__":
    # Start Socket Mode
    # Requires SLACK_APP_TOKEN environment variable
    if not os.environ.get("SLACK_APP_TOKEN"):
        logger.error("SLACK_APP_TOKEN not found. Cannot start Socket Mode.")
    else:
        logger.info("Starting Slack Bolt Server (Socket Mode)...")
        handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
        handler.start()
