import db_support  # noqa: F401  (must be first)

import importlib
import os
import unittest
from unittest.mock import patch

import backend.config


def load_config(environment):
    with patch.dict(os.environ, environment, clear=True), patch("dotenv.load_dotenv"):
        return importlib.reload(backend.config)


class ConfigTest(unittest.TestCase):
    def tearDown(self):
        importlib.reload(backend.config)

    def test_uses_defaults_for_unset_or_blank_settings(self):
        config = load_config(
            {"DATABASE_URL": "postgresql://db", "LLM_MODEL": "  ", "SECRET_KEY": "x" * 32, "ADMIN_PASSWORD_HASH": "scrypt$x"}
        )

        self.assertEqual(config.OLLAMA_BASE_URL, "http://localhost:11434")
        self.assertEqual(config.LLM_MODEL, "qwen3:8b")
        self.assertEqual(config.EMBEDDING_MODEL, "qwen3-embedding:0.6b")
        self.assertEqual(config.FRONTEND_ORIGIN, "http://localhost:5173")

    def test_environment_overrides_defaults(self):
        config = load_config(
            {
                "DATABASE_URL": " postgresql://db ",
                "OLLAMA_BASE_URL": "http://ollama:11434",
                "LLM_MODEL": "other-model",
                "FRONTEND_ORIGIN": "http://localhost:3000",
                "SECRET_KEY": "x" * 32,
                "ADMIN_PASSWORD_HASH": "scrypt$x",
            }
        )

        self.assertEqual(config.DATABASE_URL, "postgresql://db")
        self.assertEqual(config.OLLAMA_BASE_URL, "http://ollama:11434")
        self.assertEqual(config.LLM_MODEL, "other-model")
        self.assertEqual(config.FRONTEND_ORIGIN, "http://localhost:3000")

    def test_requires_database_url(self):
        with self.assertRaisesRegex(RuntimeError, "DATABASE_URL must be set"):
            load_config({"DATABASE_URL": " ", "SECRET_KEY": "x" * 32, "ADMIN_PASSWORD_HASH": "scrypt$x"})

    def test_requires_a_long_secret_key(self):
        with self.assertRaisesRegex(RuntimeError, "SECRET_KEY must be set"):
            load_config({"DATABASE_URL": "postgresql://db"})
        with self.assertRaisesRegex(RuntimeError, "at least 32 characters"):
            load_config({"DATABASE_URL": "postgresql://db", "SECRET_KEY": "short"})

    def test_requires_a_scrypt_admin_password_hash(self):
        base = {"DATABASE_URL": "postgresql://db", "SECRET_KEY": "x" * 32}
        with self.assertRaisesRegex(RuntimeError, "ADMIN_PASSWORD_HASH must be set"):
            load_config(base)
        with self.assertRaisesRegex(RuntimeError, "python -m backend.auth"):
            load_config({**base, "ADMIN_PASSWORD_HASH": "plain-password"})

    def test_cookie_secure_flag(self):
        base = {"DATABASE_URL": "postgresql://db", "SECRET_KEY": "x" * 32, "ADMIN_PASSWORD_HASH": "scrypt$x"}
        self.assertFalse(load_config(base).COOKIE_SECURE)
        self.assertTrue(load_config({**base, "COOKIE_SECURE": "TRUE"}).COOKIE_SECURE)


if __name__ == "__main__":
    unittest.main()
