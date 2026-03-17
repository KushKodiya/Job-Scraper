import logging
from .database import add_subscription, remove_subscription, get_subscribers_for_interests, get_user_subscriptions


class SubscriptionManager:
    def __init__(self, db_client):
        self.db = db_client
        self.logger = logging.getLogger("SubscriptionManager")

    def add_subscription(self, user_id: str, interest: str):
        """Subscribe a user to a specific interest/tag."""
        sub_id = f"{user_id}:{interest}"
        try:
            add_subscription(self.db, sub_id, user_id, interest)
            self.logger.info(f"Subscribed {user_id} to {interest}")
        except Exception as e:
            self.logger.error(f"Error adding subscription: {e}")

    def remove_subscription(self, user_id: str, interest: str):
        """Unsubscribe a user from an interest."""
        sub_id = f"{user_id}:{interest}"
        try:
            remove_subscription(self.db, sub_id)
            self.logger.info(f"Unsubscribed {user_id} from {interest}")
        except Exception as e:
            self.logger.error(f"Error removing subscription: {e}")

    def get_subscribers_for_tags(self, tags: list) -> list:
        """Return a list of unique user_ids subscribed to ANY of the provided tags."""
        if not tags:
            return []
        try:
            return get_subscribers_for_interests(self.db, tags)
        except Exception as e:
            self.logger.error(f"Error getting subscribers: {e}")
            return []

    def get_user_subscriptions(self, user_id: str) -> list:
        """Return all interests a user is subscribed to."""
        try:
            return get_user_subscriptions(self.db, user_id)
        except Exception as e:
            self.logger.error(f"Error getting user subscriptions: {e}")
            return []
