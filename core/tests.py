import json
from django.test import TestCase, Client
from django.conf import settings
from core.models import FAQ, ErrorCode, SupportTicket, Decision
from core.services.db_service import seed_database_safely

class DecisionMakerDjangoTests(TestCase):
    def setUp(self):
        self.client = Client()
        seed_database_safely()

    # ==========================================
    # PAGE ROUTE TESTS
    # ==========================================

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Decision Maker")
        self.assertContains(response, "chatLauncherBtn")

    def test_decision_tool_page(self):
        response = self.client.get("/decision-tool")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Weighted Decision Matrix")
        self.assertContains(response, "Quick Picks")

    def test_faqs_page_has_at_least_10_faqs(self):
        response = self.client.get("/faqs")
        self.assertEqual(response.status_code, 200)
        faqs_count = FAQ.objects.count()
        self.assertGreaterEqual(faqs_count, 10)
        self.assertContains(response, "Frequently Asked Questions")

    def test_faqs_category_filter(self):
        response = self.client.get("/faqs?category=Decision+Matrix")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Decision Matrix")

    def test_error_codes_page_contains_all_8_codes(self):
        response = self.client.get("/error-codes")
        self.assertEqual(response.status_code, 200)
        required_codes = ["400", "401", "403", "404", "429", "500", "503", "DM-901"]
        for code in required_codes:
            self.assertContains(response, code)

    def test_support_page_get_and_post(self):
        response = self.client.get("/support")
        self.assertEqual(response.status_code, 200)

        # POST create ticket
        post_resp = self.client.post("/support", {
            "action": "create",
            "user_message": "Need help with criteria scoring",
            "email": "test@example.com"
        })
        self.assertEqual(post_resp.status_code, 200)
        self.assertContains(post_resp, "Support Ticket Created Successfully")

        # Lookup ticket
        ticket = SupportTicket.objects.filter(email="test@example.com").first()
        self.assertIsNotNone(ticket)
        lookup_resp = self.client.post("/support", {
            "action": "lookup",
            "ticket_id": ticket.id
        })
        self.assertEqual(lookup_resp.status_code, 200)
        self.assertContains(lookup_resp, ticket.id)

    def test_admin_tickets_auth_levels(self):
        # 1. Missing token -> 401
        resp_401 = self.client.get("/admin/tickets")
        self.assertEqual(resp_401.status_code, 401)

        # 2. Invalid token -> 403
        resp_403 = self.client.get("/admin/tickets?token=wrong-token")
        self.assertEqual(resp_403.status_code, 403)

        # 3. Valid token -> 200
        admin_token = getattr(settings, "ADMIN_TOKEN", "dm-admin-secret-token")
        resp_200 = self.client.get(f"/admin/tickets?token={admin_token}")
        self.assertEqual(resp_200.status_code, 200)
        self.assertContains(resp_200, "Protected Support Tickets Desk")

    def test_custom_404_page(self):
        # HTML 404
        response = self.client.get("/non-existent-page-url-xyz")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page Not Found", status_code=404)
        self.assertContains(response, "Back to Home", status_code=404)
        self.assertContains(response, "Ask the Assistant", status_code=404)
        self.assertContains(response, "I got a 404 error", status_code=404)

        # API JSON 404
        api_resp = self.client.get("/api/unknown-endpoint")
        self.assertEqual(api_resp.status_code, 404)
        self.assertEqual(api_resp["Content-Type"], "application/json")

    def test_health_html_and_json(self):
        # HTML health
        html_resp = self.client.get("/health")
        self.assertEqual(html_resp.status_code, 200)
        self.assertContains(html_resp, "System Status")

        # JSON health
        json_resp = self.client.get("/health?format=json")
        self.assertEqual(json_resp.status_code, 200)
        data = json_resp.json()
        self.assertIn("status", data)
        self.assertIn("uptime", data)
        self.assertIn("dependencies", data)
        self.assertEqual(data["dependencies"]["sql_database"]["status"], "UP")

    # ==========================================
    # REST API TESTS
    # ==========================================

    def test_matrix_calculation_valid(self):
        payload = {
            "options": ["Laptop Pro", "Laptop Air"],
            "criteria": [
                {"name": "Performance", "weight": 5},
                {"name": "Price", "weight": 3}
            ],
            "scores": {
                "Laptop Pro": {"Performance": 9, "Price": 4},   # 9*5 + 4*3 = 45 + 12 = 57
                "Laptop Air": {"Performance": 7, "Price": 8}    # 7*5 + 8*3 = 35 + 24 = 59
            }
        }
        response = self.client.post(
            "/api/matrix/calculate",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["winner"], "Laptop Air")
        self.assertEqual(data["winner_score"], 59.0)

    def test_matrix_dm901_insufficient_options(self):
        payload = {
            "options": ["Single Option"],
            "criteria": [{"name": "Cost", "weight": 3}],
            "scores": {}
        }
        response = self.client.post(
            "/api/matrix/calculate",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data.get("error_code"), "DM-901")

    def test_matrix_dm901_missing_criteria(self):
        payload = {
            "options": ["Option 1", "Option 2"],
            "criteria": [],
            "scores": {}
        }
        response = self.client.post(
            "/api/matrix/calculate",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data.get("error_code"), "DM-901")

    def test_save_decision_in_sql(self):
        payload = {
            "title": "Choose Framework",
            "options": ["Django", "FastAPI"],
            "criteria": [{"name": "Ecosystem", "weight": 5}],
            "scores": {"Django": {"Ecosystem": 9}, "FastAPI": {"Ecosystem": 7}},
            "winner": "Django",
            "total_score": 45.0
        }
        response = self.client.post(
            "/api/matrix/save",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)

        saved = Decision.objects.filter(title="Choose Framework").first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.winner, "Django")

        list_resp = self.client.get("/api/decisions")
        self.assertEqual(list_resp.status_code, 200)
        self.assertGreaterEqual(list_resp.json()["count"], 1)

    def test_quick_picks(self):
        # Coin flip
        coin_resp = self.client.get("/api/quick-picks/coin-flip")
        self.assertEqual(coin_resp.status_code, 200)
        self.assertIn(coin_resp.json()["result"], ["Heads", "Tails"])

        # Dice roll
        dice_resp = self.client.get("/api/quick-picks/dice-roll?sides=6")
        self.assertEqual(dice_resp.status_code, 200)
        self.assertTrue(1 <= dice_resp.json()["result"] <= 6)

        # Random choice
        rand_resp = self.client.post(
            "/api/quick-picks/random-choice",
            data=json.dumps({"items": ["One", "Two", "Three"]}),
            content_type="application/json"
        )
        self.assertEqual(rand_resp.status_code, 200)
        self.assertIn(rand_resp.json()["result"], ["One", "Two", "Three"])

    def test_chat_error_code_lookup(self):
        response = self.client.post(
            "/api/chat",
            data=json.dumps({"message": "What is error DM-901?", "session_id": "test_1"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("DM-901", data["reply"])
        self.assertEqual(data["source"], "ErrorCode:DM-901")

    def test_chat_faq_grounding(self):
        response = self.client.post(
            "/api/chat",
            data=json.dumps({"message": "How does the Weighted Decision Matrix work?", "session_id": "test_2"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["source"].startswith("FAQ:"))
        self.assertIn("Weighted Decision Matrix", data["reply"])

    def test_chat_unanswered_fallback_creates_support_ticket(self):
        unanswerable = "What is the orbital speed of Triton around Neptune?"
        initial_count = SupportTicket.objects.count()

        response = self.client.post(
            "/api/chat",
            data=json.dumps({"message": unanswerable, "session_id": "test_3"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("cannot confidently answer", data["reply"])
        self.assertIsNotNone(data["ticket_id"])
        self.assertTrue(data["source"].startswith("AutoTicket:"))

        self.assertEqual(SupportTicket.objects.count(), initial_count + 1)
        created = SupportTicket.objects.filter(id=data["ticket_id"]).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.user_message, unanswerable)

    def test_feedback_endpoint(self):
        response = self.client.post(
            "/api/feedback",
            data=json.dumps({
                "session_id": "test_fb",
                "message_id": "msg_01",
                "rating": 1,
                "comment": "Great!"
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_faqs_api_endpoint(self):
        response = self.client.get("/api/faqs")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["count"], 10)

    def test_ticket_full_crud(self):
        # 1. CREATE
        c_resp = self.client.post(
            "/api/support/ticket",
            data=json.dumps({"user_message": "CRUD ticket test", "email": "crud@example.com"}),
            content_type="application/json"
        )
        self.assertEqual(c_resp.status_code, 201)
        t_id = c_resp.json()["ticket"]["id"]

        # 2. READ
        r_resp = self.client.get(f"/api/support/ticket/{t_id}")
        self.assertEqual(r_resp.status_code, 200)
        self.assertEqual(r_resp.json()["user_message"], "CRUD ticket test")

        # 3. UPDATE
        u_resp = self.client.put(
            f"/api/support/ticket/{t_id}",
            data=json.dumps({"status": "Resolved"}),
            content_type="application/json"
        )
        self.assertEqual(u_resp.status_code, 200)
        self.assertEqual(u_resp.json()["ticket"]["status"], "Resolved")

        # 4. DELETE
        d_resp = self.client.delete(f"/api/support/ticket/{t_id}")
        self.assertEqual(d_resp.status_code, 200)

        # Verify 404
        nf_resp = self.client.get(f"/api/support/ticket/{t_id}")
        self.assertEqual(nf_resp.status_code, 404)
