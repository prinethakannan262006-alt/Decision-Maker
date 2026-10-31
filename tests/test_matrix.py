import unittest
import json
from app import create_app
from app.config import TestingConfig
from app.models import db, Decision

class TestMatrixAndQuickPicks(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

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
        response = self.client.post("/api/matrix/calculate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["winner"], "Laptop Air")
        self.assertEqual(data["winner_score"], 59.0)

    def test_matrix_dm901_insufficient_options(self):
        # Fewer than 2 options triggers DM-901
        payload = {
            "options": ["Single Option"],
            "criteria": [{"name": "Cost", "weight": 3}],
            "scores": {}
        }
        response = self.client.post("/api/matrix/calculate", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data.get("error_code"), "DM-901")

    def test_matrix_dm901_missing_criteria(self):
        payload = {
            "options": ["Option 1", "Option 2"],
            "criteria": [],
            "scores": {}
        }
        response = self.client.post("/api/matrix/calculate", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data.get("error_code"), "DM-901")

    def test_save_decision_in_sql(self):
        payload = {
            "title": "Choose Tech Stack",
            "options": ["Flask", "FastAPI"],
            "criteria": [{"name": "Simplicity", "weight": 4}],
            "scores": {"Flask": {"Simplicity": 9}, "FastAPI": {"Simplicity": 8}},
            "winner": "Flask",
            "total_score": 36.0
        }
        response = self.client.post("/api/matrix/save", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["status"], "success")

        # Verify saved in database
        saved = Decision.query.filter_by(title="Choose Tech Stack").first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.winner, "Flask")

        # Verify /api/decisions returns it
        list_resp = self.client.get("/api/decisions")
        self.assertEqual(list_resp.status_code, 200)
        list_data = list_resp.get_json()
        self.assertGreaterEqual(list_data["count"], 1)

    def test_quick_picks_coin_flip(self):
        response = self.client.get("/api/quick-picks/coin-flip")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn(data["result"], ["Heads", "Tails"])

    def test_quick_picks_dice_roll(self):
        response = self.client.get("/api/quick-picks/dice-roll?sides=6")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(1 <= data["result"] <= 6)

    def test_quick_picks_random_choice(self):
        items = ["Alpha", "Beta", "Gamma"]
        response = self.client.post("/api/quick-picks/random-choice", json={"items": items})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn(data["result"], items)

if __name__ == "__main__":
    unittest.main()
