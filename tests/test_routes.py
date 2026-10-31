import unittest
from app import create_app
from app.config import TestingConfig
from app.models import db, FAQ, ErrorCode, SupportTicket

class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Decision Maker", response.data)
        self.assertIn(b"chatLauncherBtn", response.data)

    def test_decision_tool_page(self):
        response = self.client.get("/decision-tool")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Weighted Decision Matrix", response.data)
        self.assertIn(b"Quick Picks", response.data)

    def test_faqs_page_has_at_least_10_faqs(self):
        response = self.client.get("/faqs")
        self.assertEqual(response.status_code, 200)
        faqs_in_db = FAQ.query.count()
        self.assertGreaterEqual(faqs_in_db, 10)
        self.assertIn(b"Frequently Asked Questions", response.data)

    def test_faqs_category_filter(self):
        response = self.client.get("/faqs?category=Decision+Matrix")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Decision Matrix", response.data)

    def test_error_codes_page_contains_all_8_codes(self):
        response = self.client.get("/error-codes")
        self.assertEqual(response.status_code, 200)
        required_codes = ["400", "401", "403", "404", "429", "500", "503", "DM-901"]
        for code in required_codes:
            self.assertIn(code.encode(), response.data)

    def test_support_page_get_and_post(self):
        # GET support page
        response = self.client.get("/support")
        self.assertEqual(response.status_code, 200)

        # POST create ticket
        post_resp = self.client.post("/support", data={
            "action": "create",
            "user_message": "Need help with criteria scoring",
            "email": "test@example.com"
        })
        self.assertEqual(post_resp.status_code, 200)
        self.assertIn(b"Support Ticket Created Successfully", post_resp.data)

        # Lookup ticket
        ticket = SupportTicket.query.filter_by(email="test@example.com").first()
        self.assertIsNotNone(ticket)
        lookup_resp = self.client.post("/support", data={
            "action": "lookup",
            "ticket_id": ticket.id
        })
        self.assertEqual(lookup_resp.status_code, 200)
        self.assertIn(ticket.id.encode(), lookup_resp.data)

    def test_admin_tickets_auth_levels(self):
        # 1. Missing token -> 401
        resp_401 = self.client.get("/admin/tickets")
        self.assertEqual(resp_401.status_code, 401)

        # 2. Invalid token -> 403
        resp_403 = self.client.get("/admin/tickets?token=wrong-token")
        self.assertEqual(resp_403.status_code, 403)

        # 3. Valid token -> 200
        admin_token = self.app.config.get("ADMIN_TOKEN")
        resp_200 = self.client.get(f"/admin/tickets?token={admin_token}")
        self.assertEqual(resp_200.status_code, 200)
        self.assertIn(b"Protected Support Tickets Desk", resp_200.data)

    def test_custom_404_page(self):
        # HTML 404
        response = self.client.get("/non-existent-page-url-xyz")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Page Not Found", response.data)
        self.assertIn(b"Back to Home", response.data)
        self.assertIn(b"Ask the Assistant", response.data)
        self.assertIn(b"I got a 404 error", response.data)

        # API JSON 404
        api_resp = self.client.get("/api/unknown-endpoint")
        self.assertEqual(api_resp.status_code, 404)
        self.assertTrue(api_resp.is_json)

    def test_health_html_and_json(self):
        # HTML health
        html_resp = self.client.get("/health")
        self.assertEqual(html_resp.status_code, 200)
        self.assertIn(b"System Diagnostics", html_resp.data)

        # JSON health
        json_resp = self.client.get("/health?format=json")
        self.assertEqual(json_resp.status_code, 200)
        data = json_resp.get_json()
        self.assertIn("status", data)
        self.assertIn("uptime", data)
        self.assertIn("dependencies", data)
        self.assertEqual(data["dependencies"]["sql_database"]["status"], "UP")

if __name__ == "__main__":
    unittest.main()
