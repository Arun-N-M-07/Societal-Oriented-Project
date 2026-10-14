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
        config = load_config({"DATABASE_URL": "postgresql://db", "LLM_MODEL": "  "})

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
            }
        )

        self.assertEqual(config.DATABASE_URL, "postgresql://db")
        self.assertEqual(config.OLLAMA_BASE_URL, "http://ollama:11434")
        self.assertEqual(config.LLM_MODEL, "other-model")
        self.assertEqual(config.FRONTEND_ORIGIN, "http://localhost:3000")

    def test_requires_database_url(self):
        with self.assertRaisesRegex(RuntimeError, "DATABASE_URL must be set"):
            load_config({"DATABASE_URL": " "})


if __name__ == "__main__":
    unittest.main()
