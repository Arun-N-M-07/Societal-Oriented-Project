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
    passages = {1: FEE, 2: DOCS, 3: "Applicants without a registered mobile number cannot use online services."}

    def claim(self, text, quote, chunk_id=1):
        return {"text": text, "quote": quote, "chunk_id": chunk_id}

    def test_keeps_claims_quoted_verbatim_from_the_cited_passage(self):
        claims = [
            self.claim("Pay Rs 1,500 online.", "fee for a fresh passport of 36 pages is Rs 1,500"),
            self.claim("Bring address proof.", "  Applicants MUST carry proof\nof address ", 2),
        ]
        self.assertEqual(len(verify_claims(claims, self.passages)), 2)

    def test_keeps_negated_claims_backed_by_negated_quotes(self):
        claim = self.claim(
            "You cannot use online services without a registered mobile.",
            "without a registered mobile number cannot use online services", 3,
        )
        self.assertEqual(len(verify_claims([claim], self.passages)), 1)

    def test_quotes_joining_table_cells_or_list_items_differ_only_in_punctuation(self):
        # Scraped tables and lists store each cell or item as its own paragraph.
        passages = {7: "Purpose\n\nFor test of competence to drive\n\nRs. 300.00/-\n\n4",
                    8: "Documents required\n\nApplication in Form 25\n\nInsurance certificate*"}
        kept = [
            self.claim("The driving test fee is Rs. 300.00/-.", "For test of competence to drive Rs. 300.00/-.", 7),
            self.claim("Apply in Form 25.", "Documents required: Application in Form 25", 8),
        ]
        self.assertEqual(len(verify_claims(kept, passages)), 2)
        dropped = [
            self.claim("The fee is Rs. 300.", "test of competence to drive Rs. 300.00/- extra", 7),
            self.claim("Apply in Form 2.", "required: Application in Form 2", 8),  # "Form 2" is not "Form 25"
            self.claim("Test fee.", "For test of competence to dri", 7),  # stops mid-word
        ]
        self.assertEqual(verify_claims(dropped, passages), [])

    def test_a_short_quote_must_be_a_whole_list_item_without_numbers(self):
        passages = {9: "Documents required\n\nInsurance certificate*\n\nIssue of learner licence\n\nRs. 150.00/-"}
        self.assertEqual(len(verify_claims([self.claim("Bring the insurance certificate.", "Insurance certificate*", 9)], passages)), 1)
        for text, quote in [("Bring the insurance.", "Insurance"),  # part of an item
                            ("The fee is Rs. 150.", "Rs. 150.00/-")]:  # a bare amount needs its label
            with self.subTest(quote):
                self.assertEqual(verify_claims([self.claim(text, quote, 9)], passages), [])

    def test_numbers_must_equal_the_quoted_numbers(self):
        quote = "fee for a fresh passport of 36 pages is Rs 1,500"
        for text in ["Pay Rs 1500.", "Pay Rs. 1,500.00 online.", "A 36-page passport costs Rs 1,500."]:
            with self.subTest(text):
                self.assertEqual(len(verify_claims([self.claim(text, quote)], self.passages)), 1)
        # Digits of the quoted amount are not the amount ("Rs 150" is not "Rs 1,500").
        for text in ["Pay Rs 150.", "Pay Rs 1,50.", "A 3-page passport costs Rs 1,500.", "Pay Rs 1.5 online."]:
            with self.subTest(text):
                self.assertEqual(verify_claims([self.claim(text, quote)], self.passages), [])

    def test_drops_repeated_claims(self):
        claim = self.claim("Pay Rs 1,500 online.", "fee for a fresh passport of 36 pages is Rs 1,500")
        self.assertEqual(len(verify_claims([claim, dict(claim)], self.passages)), 1)

    def test_drops_unsupported_claims(self):
        cases = {
            "fabricated quote": self.claim("Pay online.", "the fee can be paid at any bank branch"),
            "wrong passage": self.claim("Bring address proof.", "Applicants must carry proof of address", 1),
            "unknown passage": self.claim("Pay online.", "payable online at the portal", 99),
            "invented number": self.claim("Pay Rs 2,000 online.", "fee for a fresh passport of 36 pages"),
            "too short quote": self.claim("Pay online.", "payable online"),
            "negation added": self.claim("You cannot pay online.", "is Rs 1,500 payable online"),
            "negation dropped": self.claim(
                "You can use online services.", "registered mobile number cannot use online services", 3
            ),
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

    def test_a_page_naming_the_procedure_answers_when_its_own_page_cannot(self):
        table = self.add("Fee table", ["Issue of a Passport of 36 pages costs Rs 1,500 at the counter."])
        chunk = self.session.query(ProcedureChunk).filter_by(procedure_id=table.id).one()
        self.llm.side_effect = [
            json.dumps({"insufficient_evidence": True, "claims": []}),
            json.dumps({"insufficient_evidence": False, "claims": [
                {"text": "It costs Rs 1,500.", "chunk_id": chunk.id, "quote": "Passport of 36 pages costs Rs 1,500"}]}),
        ]
        body = self.client.post("/api/guidance", json={"procedure_id": self.procedure.id, "question": "Fee?"}).json()

        self.assertEqual((body["procedure_id"], body["source_url"]), (table.id, "https://example.gov.in/Fee table"))
        self.assertEqual([c["chunk_id"] for c in body["claims"]], [chunk.id])
        # The Aadhaar page does not name the passport procedure, so it was never asked.
        self.assertEqual(self.llm.call_count, 2)
        self.assertNotIn("Aadhaar", self.llm.call_args.args[0])

    def test_only_the_related_page_s_passages_naming_the_procedure_are_used(self):
        table = self.add("Fee table", ["Issue of a Passport of 36 pages costs Rs 1,500 at the counter.",
                                       "Duplicate licence to a driving school costs Rs 5,000."])
        self.llm.return_value = json.dumps({"insufficient_evidence": True, "claims": []})
        self.client.post("/api/guidance", json={"procedure_id": self.procedure.id, "question": "Duplicate fee?"})

        related_prompt = self.llm.call_args_list[1].args[0]
        self.assertIn("Issue of a Passport", related_prompt)
        self.assertNotIn("driving school", related_prompt)

    def test_related_pages_are_not_asked_when_the_page_answers_or_nothing_names_it(self):
        self.add("Fee table", ["Issue of a Passport of 36 pages costs Rs 1,500 at the counter."])
        ids = self.chunk_ids()
        self.ask({"insufficient_evidence": False, "claims": [
            {"text": "Pay Rs 1,500 online.", "chunk_id": ids[FEE], "quote": "is Rs 1,500 payable online"}]})
        self.assertEqual(self.llm.call_count, 1)

        self.llm.reset_mock()
        body = self.client.post("/api/guidance", json={"procedure_id": self.other.id, "question": "Fee?"}).json()
        self.assertEqual((body["procedure_id"], body["insufficient_evidence"]), (self.other.id, True))
        self.assertEqual(self.llm.call_count, 1)

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

    def test_counts_distinct_unsupported_claims_and_survives_malformed_ones(self):
        ids = self.chunk_ids()
        good = {"text": "Pay Rs 1,500 online.", "chunk_id": ids[FEE], "quote": "is Rs 1,500 payable online"}
        body = self.ask({"insufficient_evidence": False, "claims": [good, good, ["odd"], {"text": ["other"]}, {"text": None}]}).json()

        self.assertEqual([c["text"] for c in body["claims"]], ["Pay Rs 1,500 online."])
        self.assertEqual(body["omitted_claims"], 3)

    def test_writes_nothing(self):
        before = self.session.query(func.count(ProcedureChunk.id)).scalar()
        self.ask({"insufficient_evidence": True, "claims": []})
        self.assertEqual(self.session.query(func.count(ProcedureChunk.id)).scalar(), before)


LINK = "Existing PAN holders must link PAN with Aadhaar before filing the return."
BOTH_NAMES = "Enter your PAN and Aadhaar number on the portal."
ADDRESS = "Address update requests are verified at an Aadhaar Enrolment Centre."
STEP = "Upload the address proof after you sign in to the portal."
TAX_ORDER = "File the income tax return only after your PAN is linked with Aadhaar."


class RelationApiTest(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.pan = GuidanceApiTest.add(self, "PAN", [LINK, BOTH_NAMES])
        self.aadhaar = GuidanceApiTest.add(self, "Aadhaar", [ADDRESS, STEP])
        self.tax = GuidanceApiTest.add(self, "Income tax", [TAX_ORDER])
        self.unrelated = GuidanceApiTest.add(self, "Passport", [FEE])
        llm = patch("backend.rag.call_qwen")
        self.llm = llm.start()
        self.addCleanup(llm.stop)

    def chunk(self, content):
        return self.session.query(ProcedureChunk).filter_by(content=content).one().id

    def claim(self, text, content, quote=None):
        return {"text": text, "chunk_id": self.chunk(content), "quote": quote or content.rstrip(".")}

    def ask(self, claims, ids=None, question="Which should I do first?"):
        self.llm.return_value = json.dumps({"insufficient_evidence": not claims, "claims": claims})
        ids = ids or [self.pan.id, self.aadhaar.id]
        return self.client.post("/api/relation", json={"procedure_ids": ids, "question": question})

    def test_keeps_an_explicitly_stated_relationship_as_official_text_with_its_source(self):
        body = self.ask([self.claim("You can reuse your Aadhaar address proof for PAN too.", LINK)]).json()

        self.assertFalse(body["insufficient_evidence"])
        self.assertEqual(body["claims"][0]["text"], LINK.rstrip("."))
        self.assertEqual(body["claims"][0]["procedure_id"], self.pan.id)
        self.assertEqual(body["claims"][0]["source_url"], self.pan.source_url)

    def test_rejects_relationships_the_quote_does_not_state(self):
        cases = {
            "order from an unrelated fact": self.claim("Update your Aadhaar address first, then link PAN.", ADDRESS),
            "reuse from an unrelated fact": self.claim("You can reuse the same address proof for PAN.", ADDRESS),
            "step inside one procedure": self.claim("Upload the address proof after you sign in.", STEP),
            "names both but states nothing": self.claim("Link PAN and Aadhaar first.", BOTH_NAMES),
            "inference with no relation words": self.claim("Your Aadhaar proof also works for PAN.", BOTH_NAMES),
        }
        for name, claim in cases.items():
            with self.subTest(name):
                self.assertEqual(self.ask([claim]).json(),
                                 {"insufficient_evidence": True, "claims": [], "omitted_claims": 1})

    def test_relates_three_procedures_with_each_quote_attributed_to_its_own_page(self):
        body = self.ask(
            [self.claim("Link PAN before filing.", LINK), self.claim("File after linking.", TAX_ORDER),
             self.claim("Verify at a centre first.", ADDRESS)],
            ids=[self.pan.id, self.aadhaar.id, self.tax.id],
        ).json()

        self.assertEqual([(c["text"], c["procedure_id"]) for c in body["claims"]],
                         [(LINK.rstrip("."), self.pan.id), (TAX_ORDER.rstrip("."), self.tax.id)])
        self.assertEqual(body["omitted_claims"], 1)

    def test_uses_only_the_requested_procedures_evidence(self):
        self.ask([])
        prompt = self.llm.call_args.args[0]
        self.assertIn(LINK, prompt)
        self.assertIn(ADDRESS, prompt)
        self.assertNotIn(FEE, prompt)
        self.assertIn("never combine separate facts", prompt)

        body = self.ask([self.claim("The passport fee is Rs 1,500.", FEE, "fee for a fresh passport of 36 pages is Rs 1,500")]).json()
        self.assertTrue(body["insufficient_evidence"])

    def test_rejects_bad_requests_and_reports_failures(self):
        self.assertEqual(self.ask([], ids=[self.pan.id]).status_code, 422)
        self.assertEqual(self.ask([], ids=[self.pan.id, 999999]).status_code, 404)
        self.llm.side_effect = ExtractionError("down")
        self.assertEqual(self.ask([]).status_code, 502)


EPF = "EPF members can withdraw the full balance at retirement after 58 years."
EPS = "EPS pays a monthly pension to members after 58 years of service."
EDLI = "EDLI pays an assurance benefit to the nominee if a member dies in service."


class ComparisonApiTest(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.epf = GuidanceApiTest.add(self, "Employees' Provident Fund Scheme", [EPF])
        self.eps = GuidanceApiTest.add(self, "Employees' Pension Scheme (EPS)", [EPS])
        self.edli = GuidanceApiTest.add(self, "Employees' Deposit Linked Insurance (EDLI)", [EDLI])
        llm = patch("backend.rag.call_qwen")
        self.llm = llm.start()
        self.addCleanup(llm.stop)

    def chunk(self, content):
        return self.session.query(ProcedureChunk).filter_by(content=content).one().id

    def ask(self, claims, procedures, question="What is the difference between EPF and EPS?"):
        self.llm.return_value = json.dumps({"insufficient_evidence": not claims, "claims": claims})
        return self.client.post("/api/relation", json={"procedure_ids": [p.id for p in procedures], "question": question}).json()

    def test_each_point_is_verified_against_its_own_procedure(self):
        body = self.ask([
            {"text": "EPF allows full withdrawal at retirement.", "chunk_id": self.chunk(EPF), "quote": "can withdraw the full balance at retirement"},
            {"text": "EPS pays a monthly pension.", "chunk_id": self.chunk(EPS), "quote": "EPS pays a monthly pension to members"},
            {"text": "Unlike the pension scheme, EPF pays a lump sum.", "chunk_id": self.chunk(EPF), "quote": "can withdraw the full balance at retirement"},
            {"text": "EPS pays a pension of Rs 7,500.", "chunk_id": self.chunk(EPS), "quote": "EPS pays a monthly pension to members"},
        ], [self.epf, self.eps])

        self.assertTrue(body["comparison"])
        self.assertEqual([(c["text"], c["procedure_id"], c["source_url"]) for c in body["claims"]], [
            ("EPF allows full withdrawal at retirement.", self.epf.id, self.epf.source_url),
            ("EPS pays a monthly pension.", self.eps.id, self.eps.source_url),
        ])
        self.assertEqual(body["omitted_claims"], 2)

    def test_compares_three_procedures_from_their_own_passages_only(self):
        body = self.ask([{"text": "EDLI pays the nominee if a member dies in service.", "chunk_id": self.chunk(EDLI),
                          "quote": "pays an assurance benefit to the nominee"}],
                        [self.epf, self.eps, self.edli], "Explain EPF, EPS and EDLI and how they differ")
        prompt = self.llm.call_args.args[0]

        self.assertEqual([c["procedure_id"] for c in body["claims"]], [self.edli.id])
        self.assertIn("how several government schemes or procedures compare", prompt)
        for passage in (EPF, EPS, EDLI):
            self.assertIn(passage, prompt)

    def test_says_so_when_the_pages_do_not_support_a_comparison(self):
        self.assertEqual(self.ask([], [self.epf, self.eps]),
                         {"insufficient_evidence": True, "claims": [], "omitted_claims": 0, "comparison": True})

    def test_dependency_questions_keep_the_strict_relationship_rules(self):
        body = self.ask([{"text": "EPS pays a monthly pension.", "chunk_id": self.chunk(EPS), "quote": "EPS pays a monthly pension to members"}],
                        [self.epf, self.eps], "Must I join EPF before EPS?")

        self.assertEqual(body, {"insufficient_evidence": True, "claims": [], "omitted_claims": 1})


class GuidancePromptTest(unittest.TestCase):
    def test_marks_passages_and_requires_quotes(self):
        chunk = ProcedureChunk(id=7, content="Official text.")
        prompt = build_guidance_prompt("Question?", [chunk])

        self.assertIn("--- PASSAGE 7 ---\nOfficial text.\n--- END PASSAGE 7 ---", prompt)
        self.assertIn("quote copied word for word", prompt)
        self.assertIn("insufficient_evidence", prompt)


if __name__ == "__main__":
    unittest.main()
