import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import check_password_hash, generate_password_hash

import backend.app as backend_app


class AppRouteTests(unittest.TestCase):
    def setUp(self):
        backend_app.app.testing = True
        self.client = backend_app.app.test_client()
        self.user_store_path = Path(__file__).resolve().parent / "_tmp_dashboard_users.json"
        self.user_store_path.write_text(
            json.dumps(
                [
                    {
                        "name": "Administrator",
                        "email": backend_app.DASHBOARD_ADMIN_EMAIL.strip().lower(),
                        "password_hash": generate_password_hash("Admin123!"),
                        "role": "admin",
                    },
                    {
                        "name": "Analyst",
                        "email": "analyst@example.com",
                        "password_hash": generate_password_hash("Analyst123!"),
                        "role": "analyst",
                    },
                    {
                        "name": "Other User",
                        "email": "other@example.com",
                        "password_hash": generate_password_hash("Other123!"),
                        "role": "analyst",
                    },
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
        self.user_store_patch = patch.object(backend_app, "USER_STORE_PATH", self.user_store_path)
        self.user_store_patch.start()
        self.addCleanup(self.user_store_patch.stop)
        self.addCleanup(lambda: self.user_store_path.unlink(missing_ok=True))

    def _set_session_user(self, email: str) -> None:
        with self.client.session_transaction() as session:
            session["user_email"] = email

    def test_require_auth_clears_stale_session_user(self):
        self._set_session_user("missing@example.com")

        response = self.client.get("/api/dashboard/summary")

        self.assertEqual(response.status_code, 401)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_email", session)

    def test_reset_password_requires_authenticated_session(self):
        response = self.client.post(
            "/api/auth/reset-password",
            json={"email": "analyst@example.com", "new_password": "NewPass123!"},
        )

        self.assertEqual(response.status_code, 401)

    def test_non_admin_can_only_reset_their_own_password(self):
        self._set_session_user("analyst@example.com")

        forbidden = self.client.post(
            "/api/auth/reset-password",
            json={"email": "other@example.com", "new_password": "NewPass123!"},
        )
        self.assertEqual(forbidden.status_code, 403)

        success = self.client.post(
            "/api/auth/reset-password",
            json={"new_password": "SelfReset123!"},
        )
        self.assertEqual(success.status_code, 200)

        users = json.loads(self.user_store_path.read_text(encoding="utf-8"))
        analyst_user = next(user for user in users if user["email"] == "analyst@example.com")
        self.assertTrue(check_password_hash(analyst_user["password_hash"], "SelfReset123!"))

    def test_unknown_brand_returns_404_for_insights_endpoint(self):
        self._set_session_user(backend_app.DASHBOARD_ADMIN_EMAIL.strip().lower())

        with patch.object(
            backend_app.dashboard_data,
            "dashboard_brand_payload",
            return_value={
                "brand_scores": [
                    {
                        "brand": "Known Brand",
                        "total_reviews": 10,
                        "positive_pct": 60.0,
                        "neutral_pct": 10.0,
                        "negative_pct": 30.0,
                        "brand_reputation_score": 30.0,
                    }
                ]
            },
        ):
            response = self.client.get("/api/dashboard/insights?brand=Missing Brand")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Unknown brand", response.get_json()["error"])

    def test_dashboard_summary_refresh_forces_live_recalculation(self):
        self._set_session_user("analyst@example.com")
        fresh_payload = {
            "total_reviews": 12,
            "positive_pct": 75.0,
            "neutral_pct": 8.0,
            "negative_pct": 17.0,
            "brand_reputation_score": 58.0,
            "brand_scores": [],
        }

        with patch.object(backend_app.dashboard_data, "calculate_brand_score", return_value=fresh_payload) as mocked:
            response = self.client.get("/api/dashboard/summary?refresh=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["brand_reputation_score"], 58.0)
        mocked.assert_called_once()

    def test_should_start_scheduler_only_in_active_debug_process(self):
        self.assertTrue(backend_app.should_start_scheduler(False))
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(backend_app.should_start_scheduler(True))
        with patch.dict(os.environ, {"WERKZEUG_RUN_MAIN": "true"}, clear=True):
            self.assertTrue(backend_app.should_start_scheduler(True))


if __name__ == "__main__":
    unittest.main()
