import json
import uuid
from django.db import models
from django.utils import timezone

def generate_ticket_id():
    return f"TICK-{uuid.uuid4().hex[:8].upper()}"

class FAQ(models.Model):
    """FAQ model for storing frequently asked questions."""
    question = models.CharField(max_length=255, unique=True)
    answer = models.TextField()
    category = models.CharField(max_length=64, default="General")

    class Meta:
        db_table = "faqs"
        ordering = ["id"]

    def __str__(self):
        return self.question

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "category": self.category
        }

class ErrorCode(models.Model):
    """Error codes and troubleshooting guide model."""
    code = models.CharField(max_length=32, primary_key=True)
    title = models.CharField(max_length=128)
    description = models.TextField()
    suggested_fix = models.TextField()

    class Meta:
        db_table = "error_codes"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.title}"

    def to_dict(self):
        return {
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "suggested_fix": self.suggested_fix
        }

class SupportTicket(models.Model):
    """Support tickets created manually or via AI assistant fallback."""
    id = models.CharField(max_length=36, primary_key=True, default=generate_ticket_id, editable=False)
    user_message = models.TextField()
    email = models.CharField(max_length=128, blank=True, null=True)
    status = models.CharField(max_length=64, default="Open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tickets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.id} ({self.status})"

    def to_dict(self):
        return {
            "id": self.id,
            "user_message": self.user_message,
            "email": self.email,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

class Decision(models.Model):
    """Saved decisions evaluated through the Weighted Decision Matrix."""
    title = models.CharField(max_length=255, default="Decision Matrix Evaluation")
    options = models.TextField()   # JSON string
    criteria = models.TextField()  # JSON string
    scores = models.TextField()    # JSON string
    winner = models.CharField(max_length=128)
    total_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "decisions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} (Winner: {self.winner})"

    def to_dict(self):
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
