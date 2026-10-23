import db_support  # noqa: F401  (must be first)

import unittest
from unittest.mock import patch

import httpx
from sqlalchemy.exc import OperationalError

from db_support import DatabaseTestCase


def tags(*names):
    return httpx.Response(
        200,
        json={"models": [{"name": name} for name in names]},
        request=httpx.Request("GET", "http://ollama.test/api/tags"),
    )


@patch("backend.routes.httpx.get")
class ReadinessTest(DatabaseTestCase):
    def test_ready_when_database_and_models_are_available(self, get):
        get.return_value = tags("qwen3:8b", "qwen3-embedding:0.6b", "other")

        response = self.client.get("/health/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok", "ollama": "ok"})

    def test_reports_each_failing_dependency_without_details(self, get):
        cases = (
            (tags("qwen3:8b"), {"ollama": "models missing"}),
            (httpx.ConnectError("connection refused to secret-host"), {"ollama": "unavailable"}),
        )
        for outcome, expected in cases:
            with self.subTest(expected=expected):
                get.side_effect = outcome if isinstance(outcome, Exception) else None
                get.return_value = None if isinstance(outcome, Exception) else outcome
                response = self.client.get("/health/ready")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["ollama"], expected["ollama"])
                self.assertNotIn("secret-host", response.text)

    def test_reports_database_failure(self, get):
        get.return_value = tags("qwen3:8b", "qwen3-embedding:0.6b")
        failure = OperationalError("SELECT", {}, Exception("password authentication failed"))
        with patch.object(self.session, "execute", side_effect=failure):
            response = self.client.get("/health/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["database"], "unavailable")
        self.assertNotIn("password", response.text)

    def test_liveness_needs_no_dependencies(self, get):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
