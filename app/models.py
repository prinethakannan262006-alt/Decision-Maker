import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

class FAQ(db.Model):
    """FAQ table for storing frequently asked questions."""
    __tablename__ = "faqs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(64), nullable=False, default="General")

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "category": self.category
        }

class ErrorCode(db.Model):
    """Error codes and troubleshooting guide."""
    __tablename__ = "error_codes"

    code = db.Column(db.String(32), primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=False)
    suggested_fix = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "suggested_fix": self.suggested_fix
        }

class SupportTicket(db.Model):
    """User support tickets created manually or via AI assistant fallback."""
    __tablename__ = "tickets"

    id = db.Column(db.String(36), primary_key=True, default=lambda: f"TICK-{uuid.uuid4().hex[:8].upper()}")
    user_message = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(32), default="Open", nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_message": self.user_message,
            "email": self.email,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

class Decision(db.Model):
    """Saved decisions evaluated through the Weighted Decision Matrix."""
    __tablename__ = "decisions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False, default="Decision Matrix Evaluation")
    options = db.Column(db.Text, nullable=False)  # JSON string of options list
    criteria = db.Column(db.Text, nullable=False) # JSON string of criteria + weights
    scores = db.Column(db.Text, nullable=False)   # JSON string of matrix scores
    winner = db.Column(db.String(128), nullable=False)
    total_score = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "title": self.title,
            "options": json.loads(self.options) if self.options else [],
            "criteria": json.loads(self.criteria) if self.criteria else [],
            "scores": json.loads(self.scores) if self.scores else {},
            "winner": self.winner,
            "total_score": self.total_score,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
