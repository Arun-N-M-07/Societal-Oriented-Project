import db_support  # noqa: F401  (must be first)

import re
import unittest
from unittest.mock import patch

from backend.auth import (
    SESSION_COOKIE,
    ProvenanceError,
    create_session_token,
    hash_password,
    issue_provenance_token,
    verify_password,
    verify_provenance_token,
)
from backend.main import app
from db_support import TEST_PASSWORD, make_client
from fastapi.testclient import TestClient


URL = "https://example.gov.in/passport"
TEXT = "Official passport instructions."


class ProvenanceTokenTest(unittest.TestCase):
    def test_accepts_unchanged_source(self):
        verify_provenance_token(issue_provenance_token(URL, TEXT), URL, TEXT)

    def test_rejects_changed_source_or_forged_token(self):
        token = issue_provenance_token(URL, TEXT)
        payload, _, signature = token.rpartition(":")
        for args in (
            (token, URL, TEXT + " "),
            (token, URL + "/other", TEXT),
            (f"{payload}:{'0' * len(signature)}", URL, TEXT),
            ("not-a-token", URL, TEXT),
            ("", URL, TEXT),
        ):
            with self.subTest(args=args[0][:30]):
                with self.assertRaisesRegex(ProvenanceError, "does not match"):
                    verify_provenance_token(*args)

    def test_rejects_expired_token(self):
        token = issue_provenance_token(URL, TEXT)
        with patch("backend.auth.time.time", return_value=10**10):
            with self.assertRaisesRegex(ProvenanceError, "expired"):
                verify_provenance_token(token, URL, TEXT)


class PasswordHashTest(unittest.TestCase):
    def test_hashes_are_salted_and_verifiable(self):
        first, second = hash_password("correct horse"), hash_password("correct horse")

        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("scrypt$"))
        self.assertTrue(verify_password("correct horse", first))
        self.assertFalse(verify_password("wrong", first))
        self.assertFalse(verify_password("correct horse", "not-a-hash"))


class AdminSessionTest(unittest.TestCase):
    def setUp(self):
        self.client = make_client(admin=False)

    def login(self, password=TEST_PASSWORD, username="admin"):
        return self.client.post(
            "/api/admin/login", json={"username": username, "password": password}
        )

    def test_login_sets_secure_session_cookie(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"username": "admin"})
        cookie = response.headers["set-cookie"]
        for attribute in ("admin_session=", "HttpOnly", "SameSite=strict", "Max-Age=43200"):
            self.assertIn(attribute, cookie)
        self.assertEqual(self.client.get("/api/admin/session").json(), {"username": "admin"})

    def test_rejects_wrong_credentials_with_same_message(self):
        for response in (self.login(password="wrong"), self.login(username="root"), self.login(username="admïn")):
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {"detail": "Invalid username or password."})
            self.assertNotIn("set-cookie", response.headers)

    def test_rejects_missing_forged_and_expired_sessions(self):
        valid = create_session_token("admin")
        with patch("backend.auth.time.time", return_value=0):
            expired = create_session_token("admin")
        forged = valid[:-1] + ("1" if valid.endswith("0") else "0")  # always a different signature
        for cookie in (None, "garbage", forged, expired, create_session_token("other")):
            with self.subTest(cookie=str(cookie)[:20]):
                self.client.cookies.clear()
                if cookie:
                    self.client.cookies.set(SESSION_COOKIE, cookie)
                response = self.client.get("/api/admin/session")
                self.assertEqual(response.status_code, 401)

    def test_logout_clears_the_cookie(self):
        self.login()
        response = self.client.post("/api/admin/logout")

        self.assertEqual(response.status_code, 204)
        self.assertIn('admin_session=""', response.headers["set-cookie"])
        self.assertEqual(self.client.get("/api/admin/session").status_code, 401)

    def test_every_admin_route_requires_a_session(self):
        public = {"/api/admin/login", "/api/admin/logout"}
        admin_routes = [
            (path, method.upper())
            for path, methods in app.openapi()["paths"].items()
            if path.startswith("/api/admin") and path not in public
            for method in methods
        ]
        self.assertGreaterEqual(len(admin_routes), 6)
        for path, method in admin_routes:
            with self.subTest(path=path, method=method):
                response = self.client.request(method, re.sub(r"{\w+}", "1", path), json={})
                self.assertEqual(response.status_code, 401)


class CorsTest(unittest.TestCase):
    def test_allows_only_the_frontend_origin_with_credentials(self):
        client = TestClient(app)
        allowed = client.options(
            "/api/admin/login",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
        )
        other = client.options(
            "/api/admin/login",
            headers={"Origin": "http://evil.test", "Access-Control-Request-Method": "POST"},
        )

        self.assertEqual(allowed.headers["access-control-allow-origin"], "http://localhost:5173")
        self.assertEqual(allowed.headers["access-control-allow-credentials"], "true")
        self.assertNotIn("access-control-allow-origin", other.headers)


if __name__ == "__main__":
    unittest.main()
