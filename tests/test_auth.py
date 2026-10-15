import db_support  # noqa: F401  (must be first)

import unittest
from unittest.mock import patch

from backend.auth import (
    PROVENANCE_TTL_SECONDS,
    ProvenanceError,
    issue_provenance_token,
    verify_provenance_token,
)


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
        self.assertEqual(PROVENANCE_TTL_SECONDS, 7200)


if __name__ == "__main__":
    unittest.main()
