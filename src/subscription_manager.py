from sqlalchemy.orm import Session
from .database import Subscription
import logging

class SubscriptionManager:
    def __init__(self, session_factory):
        self.Session = session_factory
        self.logger = logging.getLogger("SubscriptionManager")

    def add_subscription(self, user_id: str, interest: str):
        """Subscribe a user to a specific interest/tag."""
        session = self.Session()
        try:
            # ID is composite of user_id + interest to enforce uniqueness
            sub_id = f"{user_id}:{interest}"
            existing = session.query(Subscription).filter_by(id=sub_id).first()
            if not existing:
                new_sub = Subscription(id=sub_id, user_id=user_id, interest=interest)
                session.add(new_sub)
                session.commit()
                self.logger.info(f"Subscribed {user_id} to {interest}")
            else:
                self.logger.info(f"User {user_id} already subscribed to {interest}")
        except Exception as e:
            self.logger.error(f"Error adding subscription: {e}")
            session.rollback()
        finally:
            session.close()

    def remove_subscription(self, user_id: str, interest: str):
        """Unsubscribe a user from an interest."""
        session = self.Session()
        try:
            sub_id = f"{user_id}:{interest}"
            session.query(Subscription).filter_by(id=sub_id).delete()
            session.commit()
            self.logger.info(f"Unsubscribed {user_id} from {interest}")
        except Exception as e:
             self.logger.error(f"Error removing subscription: {e}")
             session.rollback()
        finally:
            session.close()

    def get_subscribers_for_tags(self, tags: list) -> list:
        """
        Return a list of unique user_ids that are subscribed to ANY of the provided tags.
        """
        if not tags:
            return []
            
        session = self.Session()
        subscribers = set()
        try:
            # Find subscriptions where interest matches any of the tags
            # Note: tags in DB are lowercase usually, ensure matching logic
            tags_lower = [t.lower() for t in tags]
            
            subs = session.query(Subscription).filter(Subscription.interest.in_(tags_lower)).all()
            for sub in subs:
                subscribers.add(sub.user_id)
                
        except Exception as e:
            self.logger.error(f"Error getting subscribers: {e}")
        finally:
            session.close()
            
        return list(subscribers)
