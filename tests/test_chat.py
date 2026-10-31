import unittest
from app import create_app
from app.config import TestingConfig
from app.models import db, SupportTicket

class TestAIChat(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_chat_error_code_lookup(self):
        # Querying an error code such as DM-901 or 404
        response = self.client.post("/api/chat", json={
            "message": "What is error DM-901?",
            "session_id": "test_sess_1"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("DM-901", data["reply"])
        self.assertEqual(data["source"], "ErrorCode:DM-901")

    def test_chat_faq_grounding(self):
        # Querying something in the FAQs (e.g. Weighted Decision Matrix)
        response = self.client.post("/api/chat", json={
            "message": "How does the Weighted Decision Matrix work?",
            "session_id": "test_sess_2"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["source"].startswith("FAQ:"))
        self.assertIn("Weighted Decision Matrix", data["reply"])

    def test_chat_unanswered_fallback_creates_support_ticket(self):
        # Querying an unsupported topic that cannot be answered from FAQs
        unanswerable_query = "What is the quantum orbital radius of ruthenium in high pressure nitrogen?"
        initial_ticket_count = SupportTicket.query.count()

        response = self.client.post("/api/chat", json={
            "message": unanswerable_query,
            "session_id": "test_sess_3"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        # Must indicate cannot confidently answer and provide ticket ID
        self.assertIn("cannot confidently answer", data["reply"])
        self.assertIsNotNone(data["ticket_id"])
        self.assertTrue(data["source"].startswith("AutoTicket:"))

        # Check ticket was persisted in SQL database
        new_ticket_count = SupportTicket.query.count()
        self.assertEqual(new_ticket_count, initial_ticket_count + 1)
        created_ticket = SupportTicket.query.filter_by(id=data["ticket_id"]).first()
        self.assertIsNotNone(created_ticket)
        self.assertEqual(created_ticket.user_message, unanswerable_query)

    def test_feedback_endpoint(self):
        response = self.client.post("/api/feedback", json={
            "session_id": "test_sess_4",
            "message_id": "msg_12345",
            "rating": 1,
            "comment": "Very helpful explanation!"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")

if __name__ == "__main__":
    unittest.main()
