import logging
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

class MongoService:
    """Manages connection and persistence to MongoDB Atlas with graceful offline fallback."""
    def __init__(self, uri=None, db_name="decision_maker"):
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self._connected = False
        if uri:
            self.init_connection()

    def init_connection(self):
        if not self.uri:
            self._connected = False
            return
        try:
            self.client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
                socketTimeoutMS=2000
            )
            # Trigger quick ping
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self._connected = True
            logger.info("MongoDB Atlas connected successfully.")
        except (PyMongoError, ServerSelectionTimeoutError, Exception) as e:
            self._connected = False
            self.client = None
            self.db = None
            # Log failure without leaking connection strings or credentials
            logger.warning("MongoDB Atlas is unreachable. Operating gracefully in offline fallback mode.")

    def is_connected(self):
        if not self.client:
            return False
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False

    def log_chat(self, session_id, user_message, bot_reply, matched_source):
        """Save chat exchange to chat_logs collection in MongoDB."""
        if not self.is_connected() or self.db is None:
            logger.info(f"[Offline Log] Chat logged in-memory (session: {session_id[:8]}...)")
            return False
        try:
            self.db.chat_logs.insert_one({
                "session_id": session_id,
                "user_message": user_message,
                "bot_reply": bot_reply,
                "matched_source": matched_source,
                "timestamp": datetime.now(timezone.utc)
            })
            return True
        except Exception as e:
            logger.warning(f"Failed to write chat log to MongoDB: {type(e).__name__}")
            return False

    def log_feedback(self, session_id, message_id, rating, comment=""):
        """Save thumbs-up/down feedback to feedback collection in MongoDB."""
        if not self.is_connected() or self.db is None:
            logger.info(f"[Offline Log] Feedback logged in-memory (rating: {rating})")
            return False
        try:
            self.db.feedback.insert_one({
                "session_id": session_id,
                "message_id": message_id,
                "rating": rating,
                "comment": comment or "",
                "timestamp": datetime.now(timezone.utc)
            })
            return True
        except Exception as e:
            logger.warning(f"Failed to write feedback to MongoDB: {type(e).__name__}")
            return False
