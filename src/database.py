import os
import logging
from supabase import create_client
from dotenv import load_dotenv
import pathlib

env_path = pathlib.Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("Database")


def init_db():
    """Initialize and return a Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        logger.warning("SUPABASE_URL or SUPABASE_KEY not set — database operations will fail")
    return create_client(url, key)


def job_exists(client, job_id: str) -> bool:
    """Check if a job with the given ID already exists."""
    result = client.table("jobs").select("id").eq("id", job_id).execute()
    return len(result.data) > 0


def insert_job(client, job_dict: dict):
    """Insert a new job into the database."""
    try:
        client.table("jobs").insert(job_dict).execute()
    except Exception as e:
        if "23505" in str(e):
            logger.info(f"Job already exists in database: {job_dict.get('url')}")
        else:
            raise


def add_subscription(client, sub_id: str, user_id: str, interest: str):
    """Add a subscription (idempotent via upsert)."""
    client.table("subscriptions").upsert({
        "id": sub_id,
        "user_id": user_id,
        "interest": interest
    }).execute()


def remove_subscription(client, sub_id: str):
    """Remove a subscription."""
    client.table("subscriptions").delete().eq("id", sub_id).execute()


def get_subscribers_for_interests(client, interests: list) -> list:
    """Return unique user IDs subscribed to any of the given interests."""
    if not interests:
        return []
    interests_lower = [i.lower() for i in interests]
    result = client.table("subscriptions").select("user_id").in_("interest", interests_lower).execute()
    return list({row["user_id"] for row in result.data})


def get_user_subscriptions(client, user_id: str) -> list:
    """Return all subscriptions for a user."""
    result = client.table("subscriptions").select("interest").eq("user_id", user_id).execute()
    return [row["interest"] for row in result.data]
