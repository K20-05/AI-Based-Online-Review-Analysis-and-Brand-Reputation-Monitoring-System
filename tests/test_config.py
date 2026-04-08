import os
import unittest
from pathlib import Path
from unittest.mock import patch

import backend.config as backend_config


class ConfigTests(unittest.TestCase):
    def test_resolve_secret_key_reuses_generated_local_secret_for_placeholder_env(self):
        secret_path = Path(__file__).resolve().parent / "_tmp_flask_session_secret"
        secret_path.unlink(missing_ok=True)
        self.addCleanup(lambda: secret_path.unlink(missing_ok=True))

        with patch.dict(os.environ, {"SECRET_KEY": "replace-with-a-long-random-secret"}, clear=False):
            first_secret = backend_config.resolve_secret_key(secret_path)
            second_secret = backend_config.resolve_secret_key(secret_path)

        self.assertTrue(secret_path.exists())
        self.assertEqual(first_secret, second_secret)
        self.assertNotEqual(first_secret, "replace-with-a-long-random-secret")
        self.assertTrue(first_secret)

    def test_resolve_secret_key_prefers_explicit_env_secret(self):
        secret_path = Path(__file__).resolve().parent / "_tmp_flask_session_secret_explicit"
        secret_path.unlink(missing_ok=True)
        self.addCleanup(lambda: secret_path.unlink(missing_ok=True))

        with patch.dict(os.environ, {"SECRET_KEY": "unit-test-secret"}, clear=False):
            resolved_secret = backend_config.resolve_secret_key(secret_path)

        self.assertEqual(resolved_secret, "unit-test-secret")
        self.assertFalse(secret_path.exists())

    def test_runtime_server_settings_prefer_app_env_over_flask_env(self):
        env = {
            "APP_DEBUG": "true",
            "APP_HOST": "0.0.0.0",
            "APP_PORT": "8001",
            "PORT": "9000",
            "FLASK_DEBUG": "false",
            "FLASK_RUN_HOST": "127.0.0.1",
            "FLASK_RUN_PORT": "5000",
        }

        with patch.dict(os.environ, env, clear=False):
            settings = backend_config.resolve_runtime_server_settings()

        self.assertEqual(settings["host"], "0.0.0.0")
        self.assertEqual(settings["port"], 8001)
        self.assertTrue(settings["debug"])

    def test_runtime_server_settings_fall_back_to_flask_env(self):
        env = {
            "APP_DEBUG": "",
            "APP_HOST": "",
            "APP_PORT": "invalid",
            "FLASK_DEBUG": "true",
            "FLASK_RUN_HOST": "localhost",
            "FLASK_RUN_PORT": "7000",
        }

        with patch.dict(os.environ, env, clear=False):
            settings = backend_config.resolve_runtime_server_settings()

        self.assertEqual(settings["host"], "localhost")
        self.assertEqual(settings["port"], 7000)
        self.assertTrue(settings["debug"])

    def test_runtime_server_settings_support_port_env_and_default_host(self):
        env = {
            "APP_DEBUG": "",
            "APP_HOST": "",
            "APP_PORT": "",
            "PORT": "7100",
            "FLASK_DEBUG": "",
            "FLASK_RUN_HOST": "",
            "FLASK_RUN_PORT": "",
        }

        with patch.dict(os.environ, env, clear=False):
            settings = backend_config.resolve_runtime_server_settings()

        self.assertEqual(settings["host"], "0.0.0.0")
        self.assertEqual(settings["port"], 7100)
        self.assertFalse(settings["debug"])

    def test_resolve_allowed_cors_origins_falls_back_to_local_defaults(self):
        with patch.dict(os.environ, {"ALLOWED_CORS_ORIGINS": ""}, clear=False):
            origins = backend_config.resolve_allowed_cors_origins()

        self.assertIn("http://127.0.0.1:5000", origins)
        self.assertIn("http://localhost:5000", origins)
        self.assertIn("http://127.0.0.1:5500", origins)
        self.assertIn("http://localhost:5500", origins)


if __name__ == "__main__":
    unittest.main()
