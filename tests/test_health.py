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


class RequestLoggingTest(DatabaseTestCase):
    def test_each_request_gets_an_id_and_one_log_line_without_its_content(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        with self.assertLogs("procedureassist", "INFO") as logs:
            response = TestClient(app).post("/api/identify", json={"question": "PRIVATE QUESTION " * 100})
        self.assertEqual(response.status_code, 422)
        self.assertRegex(response.headers["X-Request-ID"], r"^[0-9a-f]{12}$")
        self.assertEqual(len(logs.output), 1)
        self.assertIn("POST /api/identify 422", logs.output[0])
        self.assertNotIn("PRIVATE", logs.output[0])

    def test_an_unreachable_database_gives_a_message_and_an_id_not_a_bare_500(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        down = OperationalError("SELECT 1", {}, Exception("connection refused"))
        with patch("backend.routes.identify_needs", side_effect=down), self.assertLogs("procedureassist", "INFO") as logs:
            response = TestClient(app).post("/api/identify", json={"question": "PRIVATE passport question"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "The procedure database is unavailable. Try again."})
        self.assertRegex(response.headers["X-Request-ID"], r"^[0-9a-f]{12}$")
        self.assertTrue(any("POST /api/identify 503" in line for line in logs.output))
        self.assertFalse(any("PRIVATE" in line for line in logs.output))


if __name__ == "__main__":
    unittest.main()
