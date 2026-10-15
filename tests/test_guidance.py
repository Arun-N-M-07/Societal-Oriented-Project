import db_support  # noqa: F401  (must be first)

import json
import unittest
from unittest.mock import patch

from sqlalchemy import func

from backend.extractor import ExtractionError
from backend.models import Procedure, ProcedureChunk
from backend.rag import EmbeddingError, build_guidance_prompt, verify_claims
from db_support import DatabaseTestCase, make_client, unit_vector


FEE = "The application fee for a fresh passport of 36 pages is Rs 1,500 payable online."
DOCS = "Applicants must carry proof of address and proof of date of birth to the appointment."
OLD_FEE = "Older guidance: the application fee for a fresh passport was Rs 1,000."


class VerifyClaimsTest(unittest.TestCase):
    passages = {1: FEE, 2: DOCS}

    def claim(self, text, quote, chunk_id=1):
        return {"text": text, "quote": quote, "chunk_id": chunk_id}

    def test_keeps_claims_quoted_verbatim_from_the_cited_passage(self):
        claims = [
            self.claim("Pay Rs 1,500 online.", "fee for a fresh passport of 36 pages is Rs 1,500"),
            self.claim("Bring address proof.", "  Applicants MUST carry proof\nof address ", 2),
        ]
        self.assertEqual(len(verify_claims(claims, self.passages)), 2)

    def test_drops_unsupported_claims(self):
        cases = {
            "fabricated quote": self.claim("Pay online.", "the fee can be paid at any bank branch"),
            "wrong passage": self.claim("Bring address proof.", "Applicants must carry proof of address", 1),
            "unknown passage": self.claim("Pay online.", "payable online at the portal", 99),
            "invented number": self.claim("Pay Rs 2,000 online.", "fee for a fresh passport of 36 pages"),
            "too short quote": self.claim("Pay online.", "payable online"),
            "missing text": {"quote": "fee for a fresh passport of 36 pages", "chunk_id": 1},
            "string id": self.claim("Pay.", "fee for a fresh passport of 36 pages", "1"),
            "not an object": "Pay Rs 1,500",
        }
        for name, claim in cases.items():
            with self.subTest(name):
                self.assertEqual(verify_claims([claim], self.passages), [])
        self.assertEqual(verify_claims("not a list", self.passages), [])


class GuidanceApiTest(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.procedure = self.add("Passport", [FEE, DOCS, OLD_FEE])
        self.other = self.add("Aadhaar", ["Aadhaar address can be updated online for Rs 50."])
        llm = patch("backend.rag.call_qwen")
        self.llm = llm.start()
        self.addCleanup(llm.stop)

    def add(self, name, passages):
        procedure = Procedure(
            name=name,
            summary=f"{name} summary.",
            source_url=f"https://example.gov.in/{name}",
            source_text="\n\n".join(passages),
            structured_data={"eligibility": None, "steps": ["One"]},
        )
        self.session.add(procedure)
        self.session.flush()
        for index, passage in enumerate(passages):
            self.session.add(
                ProcedureChunk(
                    procedure_id=procedure.id, chunk_index=index, content=passage, embedding=unit_vector(index)
                )
            )
        self.session.flush()
        return procedure

    def chunk_ids(self):
        rows = self.session.query(ProcedureChunk).filter_by(procedure_id=self.procedure.id)
        return {row.content: row.id for row in rows}

    def ask(self, model_output, question="How much does a passport cost?"):
        self.llm.return_value = json.dumps(model_output) if not isinstance(model_output, str) else model_output
        return self.client.post(
            "/api/guidance", json={"procedure_id": self.procedure.id, "question": question}
        )

    def test_returns_verified_steps_with_citations_and_official_link(self):
        ids = self.chunk_ids()
        response = self.ask({
            "insufficient_evidence": False,
            "claims": [
                {"text": "Pay Rs 1,500 online.", "chunk_id": ids[FEE], "quote": "is Rs 1,500 payable online"},
                {"text": "Bring proof of address.", "chunk_id": ids[DOCS], "quote": "carry proof of address and proof"},
            ],
        })

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["insufficient_evidence"])
        self.assertEqual([c["chunk_id"] for c in body["claims"]], [ids[FEE], ids[DOCS]])
        self.assertEqual(body["source_url"], "https://example.gov.in/Passport")
        self.assertEqual(body["omitted_claims"], 0)

    def test_removes_fabricated_claims_and_counts_them(self):
        ids = self.chunk_ids()
        body = self.ask({
            "insufficient_evidence": False,
            "claims": [
                {"text": "Pay Rs 1,500 online.", "chunk_id": ids[FEE], "quote": "is Rs 1,500 payable online"},
                {"text": "Applications close on 31 March.", "chunk_id": ids[FEE], "quote": "applications close on 31 March each year"},
            ],
        }).json()

        self.assertEqual(len(body["claims"]), 1)
        self.assertEqual(body["omitted_claims"], 1)

    def test_refuses_when_no_claim_survives_or_model_finds_no_answer(self):
        for output in (
            {"insufficient_evidence": False, "claims": [{"text": "Fee is Rs 900.", "chunk_id": 1, "quote": "fee is Rs 900 for everyone"}]},
            {"insufficient_evidence": True, "claims": []},
            {"insufficient_evidence": True, "claims": [{"text": "x", "chunk_id": 1, "quote": "y"}]},
        ):
            with self.subTest(output=output):
                body = self.ask(output, "Can I get a passport delivered by drone?").json()
                self.assertTrue(body["insufficient_evidence"])
                self.assertEqual(body["claims"], [])

    def test_keeps_both_sides_of_conflicting_evidence(self):
        ids = self.chunk_ids()
        body = self.ask({
            "insufficient_evidence": False,
            "claims": [
                {"text": "The fee is Rs 1,500.", "chunk_id": ids[FEE], "quote": "is Rs 1,500 payable online"},
                {"text": "Older guidance listed Rs 1,000.", "chunk_id": ids[OLD_FEE], "quote": "fresh passport was Rs 1,000"},
            ],
        }).json()

        self.assertEqual(len(body["claims"]), 2)

    def test_prompt_contains_only_this_procedures_evidence_and_question(self):
        self.ask({"insufficient_evidence": True, "claims": []}, "What documents do I need?")
        prompt = self.llm.call_args.args[0]

        self.assertIn("What documents do I need?", prompt)
        self.assertIn(DOCS, prompt)
        self.assertNotIn("Aadhaar address", prompt)
        self.assertIn("untrusted data", prompt)
        self.assertTrue(self.embed.call_args.kwargs["query"])

    def test_procedure_without_evidence_is_refused_without_calling_the_model(self):
        empty = Procedure(
            name="Empty", summary="s", source_url="https://example.gov.in/e",
            source_text="t", structured_data={"eligibility": None, "steps": ["s"]},
        )
        self.session.add(empty)
        self.session.flush()

        response = self.client.post("/api/guidance", json={"procedure_id": empty.id, "question": "fee?"})

        self.assertTrue(response.json()["insufficient_evidence"])
        self.llm.assert_not_called()

    def test_errors(self):
        self.assertEqual(
            self.client.post("/api/guidance", json={"procedure_id": 999999, "question": "fee?"}).status_code, 404
        )
        for body in ({"procedure_id": "x", "question": "fee?"}, {"procedure_id": 1, "question": " "}):
            self.assertEqual(self.client.post("/api/guidance", json=body).status_code, 422)
        for failure in ("not json", json.dumps([1, 2]), json.dumps({"claims": []})):
            with self.subTest(failure=failure):
                self.assertEqual(self.ask(failure).status_code, 502)
        self.llm.side_effect = ExtractionError("Qwen extraction timed out.")
        response = self.ask({"insufficient_evidence": True})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "The answer service is unavailable. Try again."})
        self.llm.side_effect = None
        self.embed.side_effect = EmbeddingError("down")
        self.assertEqual(self.ask({"insufficient_evidence": True}).status_code, 502)

    def test_writes_nothing(self):
        before = self.session.query(func.count(ProcedureChunk.id)).scalar()
        self.ask({"insufficient_evidence": True, "claims": []})
        self.assertEqual(self.session.query(func.count(ProcedureChunk.id)).scalar(), before)


class GuidancePromptTest(unittest.TestCase):
    def test_marks_passages_and_requires_quotes(self):
        chunk = ProcedureChunk(id=7, content="Official text.")
        prompt = build_guidance_prompt("Question?", [chunk])

        self.assertIn("--- PASSAGE 7 ---\nOfficial text.\n--- END PASSAGE 7 ---", prompt)
        self.assertIn("quote copied word for word", prompt)
        self.assertIn("insufficient_evidence", prompt)


if __name__ == "__main__":
    unittest.main()
