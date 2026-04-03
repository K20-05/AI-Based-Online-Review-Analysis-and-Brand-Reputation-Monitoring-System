import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import joblib
import pandas as pd
from werkzeug.security import check_password_hash, generate_password_hash

import backend.app as backend_app
import backend.dashboard_data as dashboard_data
import backend.model_artifacts as model_artifacts
import backend.realtime_reviews as realtime_reviews


class StubProbabilityModel:
    classes_ = ["Negative", "Neutral", "Positive"]

    def __init__(self, probabilities):
        self._probabilities = probabilities

    def predict_proba(self, text_matrix):
        return self._probabilities

    def predict(self, text_matrix):
        predictions = []
        for row in self._probabilities:
            best_index = max(range(len(row)), key=row.__getitem__)
            predictions.append(self.classes_[best_index])
        return predictions


class StubVectorizer:
    def transform(self, rows):
        return list(rows)


class AppRouteTests(unittest.TestCase):
    def setUp(self):
        backend_app.app.testing = True
        self.client = backend_app.app.test_client()
        backend_app._USER_STORE_CACHE.update({"signature": None, "users": [], "index": {}})
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

    def _login(self, email: str, password: str):
        return self.client.post("/api/auth/login", json={"email": email, "password": password})

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

    def test_missing_route_preserves_404_json_status(self):
        response = self.client.get("/definitely-missing-route")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.")

    def test_index_response_disables_html_caching(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        cache_control = response.headers.get("Cache-Control", "")
        self.assertIn("no-store", cache_control)
        self.assertIn("max-age=0", cache_control)
        response.close()

    def test_index_html_response_disables_html_caching(self):
        response = self.client.get("/index.html")

        self.assertEqual(response.status_code, 200)
        cache_control = response.headers.get("Cache-Control", "")
        self.assertIn("no-store", cache_control)
        self.assertIn("max-age=0", cache_control)
        response.close()

    def test_unknown_origin_does_not_receive_cors_headers(self):
        response = self.client.get("/api/health", headers={"Origin": "https://evil.example"})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))
        self.assertTrue(backend_app.app.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(backend_app.app.config["SESSION_COOKIE_SAMESITE"], "Lax")
        self.assertFalse(backend_app.app.config["SESSION_COOKIE_SECURE"])

    def test_login_sets_hardened_session_cookie_defaults(self):
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": backend_app.DASHBOARD_ADMIN_EMAIL.strip().lower(),
                "password": "Admin123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        cookie_header = response.headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", cookie_header)
        self.assertIn("SameSite=Lax", cookie_header)

    def test_load_user_store_skips_auto_seed_without_configured_admin_password(self):
        empty_user_store_path = Path(__file__).resolve().parent / "_tmp_dashboard_users_empty.json"
        empty_user_store_path.write_text("[]", encoding="utf-8")
        self.addCleanup(lambda: empty_user_store_path.unlink(missing_ok=True))

        with (
            patch.object(backend_app, "USER_STORE_PATH", empty_user_store_path),
            patch.object(backend_app, "DASHBOARD_ADMIN_EMAIL", "admin@brandpulse.ai"),
            patch.object(backend_app, "DASHBOARD_ADMIN_PASSWORD", ""),
        ):
            users = backend_app.load_user_store()

        self.assertEqual(users, [])

    def test_admin_users_preserves_admin_role_label(self):
        self._set_session_user(backend_app.DASHBOARD_ADMIN_EMAIL.strip().lower())

        response = self.client.get("/api/admin/users")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        admin_row = next(row for row in payload["users"] if row["email"] == backend_app.DASHBOARD_ADMIN_EMAIL.strip().lower())
        self.assertEqual(admin_row["role"], "admin")
        self.assertTrue(admin_row["is_protected"])

    def test_save_user_store_refreshes_find_user_lookup(self):
        initial = backend_app.find_user("analyst@example.com")
        self.assertIsNotNone(initial)
        self.assertEqual(initial["role"], "analyst")

        users = backend_app.load_user_store()
        analyst = next(user for user in users if user["email"] == "analyst@example.com")
        analyst["role"] = "marketing_staff"
        backend_app.save_user_store(users)

        updated = backend_app.find_user("analyst@example.com")
        self.assertIsNotNone(updated)
        self.assertEqual(updated["role"], "marketing_staff")

    def test_login_session_and_dashboard_summary_flow(self):
        brand_score_path = Path(__file__).resolve().parent / "_tmp_dashboard_brand_score.json"
        missing_predictions_path = Path(__file__).resolve().parent / "_tmp_missing_predictions.csv"
        missing_realtime_path = Path(__file__).resolve().parent / "_tmp_missing_realtime.csv"
        brand_score_path.write_text(
            json.dumps(
                {
                    "total_reviews": 42,
                    "positive_pct": 66.5,
                    "neutral_pct": 11.9,
                    "negative_pct": 21.6,
                    "brand_reputation_score": 44.9,
                    "brand_scores": [],
                }
            ),
            encoding="utf-8",
        )
        self.addCleanup(lambda: brand_score_path.unlink(missing_ok=True))

        with (
            patch.object(dashboard_data, "BRAND_SCORE_PATH", brand_score_path),
            patch.object(dashboard_data, "PREDICTIONS_PATH", missing_predictions_path),
            patch.object(dashboard_data, "REALTIME_REVIEWS_PATH", missing_realtime_path),
        ):
            login_response = self._login("analyst@example.com", "Analyst123!")
            with self.client.session_transaction() as session:
                self.assertEqual(session.get("user_email"), "analyst@example.com")
            summary_response = self.client.get("/api/dashboard/summary")

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.get_json()["user"]["email"], "analyst@example.com")
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.get_json()["brand_reputation_score"], 44.9)

    def test_dashboard_keywords_grouped_by_sentiment(self):
        self._set_session_user("analyst@example.com")

        predictions_path = Path(__file__).resolve().parent / "_tmp_keywords_predictions.csv"
        realtime_path = Path(__file__).resolve().parent / "_tmp_keywords_realtime.csv"
        keyword_cache_path = Path(__file__).resolve().parent / "_tmp_keywords_grouped_cache.json"
        predictions_path.write_text("review_id,predicted_sentiment\n1,Positive\n", encoding="utf-8")
        realtime_path.write_text("", encoding="utf-8")
        keyword_cache_path.write_text(
            json.dumps(
                {
                    "Positive": [{"word": "easy", "count": 12}],
                    "Neutral": [{"word": "okay", "count": 8}],
                    "Negative": [{"word": "refund", "count": 15}],
                }
            ),
            encoding="utf-8",
        )
        self.addCleanup(lambda: predictions_path.unlink(missing_ok=True))
        self.addCleanup(lambda: realtime_path.unlink(missing_ok=True))
        self.addCleanup(lambda: keyword_cache_path.unlink(missing_ok=True))

        with (
            patch.object(dashboard_data, "PREDICTIONS_PATH", predictions_path),
            patch.object(dashboard_data, "REALTIME_REVIEWS_PATH", realtime_path),
            patch.object(dashboard_data, "KEYWORD_GROUPS_CACHE_PATH", keyword_cache_path),
        ):
            response = self.client.get("/api/dashboard/keywords?group_by=sentiment")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["keywords_by_sentiment"]["Positive"][0]["word"], "easy")
        self.assertEqual(payload["keywords_by_sentiment"]["Neutral"][0]["word"], "okay")
        self.assertEqual(payload["keywords_by_sentiment"]["Negative"][0]["word"], "refund")

    def test_dashboard_realtime_reviews_serializes_missing_values_as_null(self):
        self._set_session_user("analyst@example.com")

        realtime_path = Path(__file__).resolve().parent / "_tmp_realtime_reviews.csv"
        pd.DataFrame(
            [
                {
                    "review_id": "rt-1",
                    "review_text": "Helpful experience overall.",
                    "cleaned_review": "helpful experience overall",
                    "normalized_review": "helpful experience overall",
                    "platform": "Amazon",
                    "brand": "Amazon",
                    "rating": 5,
                    "source_language": "en",
                    "source_language_label": "English",
                    "language_confidence": 0.82,
                    "translation_applied": True,
                    "multilingual_strategy": "lexicon_bridge",
                    "predicted_sentiment": "Positive",
                    "prediction_confidence": 0.91,
                    "primary_aspect": float("nan"),
                    "primary_aspect_sentiment": float("nan"),
                    "aspect_summary": float("nan"),
                    "ingested_at": "2026-04-02T06:42:24.898815+00:00",
                    "review_date": "2024-08-09",
                    "source_type": "connector:dataset_csv:Amazon.csv",
                }
            ]
        ).to_csv(realtime_path, index=False)
        self.addCleanup(lambda: realtime_path.unlink(missing_ok=True))

        with patch.object(realtime_reviews, "REALTIME_REVIEWS_PATH", realtime_path):
            response = self.client.get("/api/dashboard/realtime-reviews?limit=1")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("NaN", response.get_data(as_text=True))
        payload = response.get_json()
        self.assertEqual(payload["source_mode"], "live")
        self.assertEqual(len(payload["reviews"]), 1)
        self.assertIsNone(payload["reviews"][0]["primary_aspect"])
        self.assertIsNone(payload["reviews"][0]["primary_aspect_sentiment"])
        self.assertIsNone(payload["reviews"][0]["aspect_summary"])

    def test_predict_endpoint_uses_stubbed_model_artifacts(self):
        model_path = Path(__file__).resolve().parent / "_tmp_sentiment_model.pkl"
        vectorizer_path = Path(__file__).resolve().parent / "_tmp_tfidf_vectorizer.pkl"
        joblib.dump(StubProbabilityModel([[0.20, 0.10, 0.70]]), model_path)
        joblib.dump(StubVectorizer(), vectorizer_path)
        self.addCleanup(lambda: model_path.unlink(missing_ok=True))
        self.addCleanup(lambda: vectorizer_path.unlink(missing_ok=True))

        with (
            patch.object(model_artifacts, "MODEL_PATH", model_path),
            patch.object(model_artifacts, "VECTORIZER_PATH", vectorizer_path),
        ):
            model_artifacts._ARTIFACT_CACHE.update({"signature": None, "model": None, "vectorizer": None})
            self._set_session_user("analyst@example.com")
            predict_response = self.client.post(
                "/api/predict",
                json={
                    "review_text": "okish",
                    "platform": "Nykaa",
                },
            )
            model_artifacts._ARTIFACT_CACHE.update({"signature": None, "model": None, "vectorizer": None})

        self.assertEqual(predict_response.status_code, 200)
        payload = predict_response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["brand"], "Nykaa")
        self.assertEqual(payload["platform"], "Nykaa")
        self.assertEqual(payload["normalized_review"], "okay")
        self.assertEqual(payload["predicted_sentiment"], "Neutral")
        self.assertEqual(payload["sentiment_adjustment_reason"], "multilingual_neutral_guard")

    def test_should_start_scheduler_only_in_active_debug_process(self):
        self.assertTrue(backend_app.should_start_scheduler(False))
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(backend_app.should_start_scheduler(True))
        with patch.dict(os.environ, {"WERKZEUG_RUN_MAIN": "true"}, clear=True):
            self.assertTrue(backend_app.should_start_scheduler(True))


if __name__ == "__main__":
    unittest.main()
