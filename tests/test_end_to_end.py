import db_support  # noqa: F401  (must be first)

import json
import re
import unittest
from unittest.mock import patch

from backend.schemas import ScrapeResult
from db_support import TEST_PASSWORD, DatabaseTestCase, make_client


URL = "https://uidai.gov.in/en/updating-data-on-aadhaar"
SOURCE_TEXT = (
    "Updating Data on Aadhaar\n\n"
    "Residents can update their address online on the myAadhaar portal.\n\n"
    "Upload a scanned proof of address document to complete the request."
)
EXTRACTION = {
    "name": "Updating Data on Aadhaar",
    "department": "UIDAI",
    "jurisdiction": None,
    "summary": "Update Aadhaar details online or at an enrolment centre.",
    "eligibility": None,
    "steps": ["Sign in to myAadhaar.", "Upload proof of address."],
}


def fake_qwen(prompt):
    """Stands in for qwen3:8b: extraction JSON, or a guidance answer quoting
    the first passage it was given."""
    if "--- BEGIN SOURCE TEXT ---" in prompt:
        return json.dumps(EXTRACTION)
    if "fishing" in prompt:
        return json.dumps({"insufficient_evidence": True, "claims": []})
    passage = int(re.search(r"--- PASSAGE (\d+) ---", prompt).group(1))
    return json.dumps({
        "insufficient_evidence": False,
        "claims": [{"text": "You can update your address online.", "chunk_id": passage,
                    "quote": "update their address online on the myAadhaar portal"}],
    })


@patch("backend.rag.call_qwen", side_effect=fake_qwen)
@patch("backend.extractor.call_qwen", side_effect=fake_qwen)
@patch("backend.routes.scrape_url", return_value=ScrapeResult(source_url=URL, source_text=SOURCE_TEXT))
class EndToEndTest(DatabaseTestCase):
    def test_admin_approval_to_citizen_guidance(self, *_mocks):
        admin = make_client(self.session, admin=False)
        citizen = make_client(self.session, admin=False)

        self.assertEqual(admin.post("/api/admin/extract", json={"source_url": URL}).status_code, 401)
        login = admin.post("/api/admin/login", json={"username": "admin", "password": TEST_PASSWORD})
        self.assertEqual(login.status_code, 200)

        extraction = admin.post("/api/admin/extract", json={"source_url": URL}).json()
        reviewed = {**extraction["procedure"], "summary": "Reviewed summary."}
        saved = admin.post("/api/admin/procedures", json={
            "procedure": reviewed,
            "source_text": extraction["source_text"],
            "provenance_token": extraction["provenance_token"],
        })
        self.assertEqual(saved.status_code, 200)
        procedure_id = saved.json()["id"]

        match = citizen.post("/api/identify", json={"question": "I moved house"}).json()
        self.assertEqual(match["status"], "matched")
        self.assertEqual(match["candidates"][0]["id"], procedure_id)

        detail = citizen.get(f"/api/procedures/{procedure_id}").json()
        self.assertEqual(detail["summary"], "Reviewed summary.")
        self.assertEqual(detail["source_url"], URL)
        self.assertNotIn("source_text", detail)

        answer = citizen.post("/api/guidance", json={
            "procedure_id": procedure_id, "question": "Can I update my address online?",
        }).json()
        self.assertFalse(answer["insufficient_evidence"])
        self.assertIn("update their address online", answer["claims"][0]["quote"])
        refusal = citizen.post("/api/guidance", json={
            "procedure_id": procedure_id, "question": "How do I get a fishing licence?",
        }).json()
        self.assertTrue(refusal["insufficient_evidence"])

        self.assertEqual(citizen.delete(f"/api/admin/procedures/{procedure_id}").status_code, 401)
        self.assertEqual(admin.delete(f"/api/admin/procedures/{procedure_id}").status_code, 204)
        gone = citizen.post("/api/identify", json={"question": "I moved house"}).json()
        self.assertEqual(gone["status"], "no_match")


if __name__ == "__main__":
    unittest.main()
