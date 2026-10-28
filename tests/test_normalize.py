import json
import unittest
from unittest.mock import patch

from db_support import DatabaseTestCase, make_client, unit_vector

from backend.extractor import ExtractionError
from backend.models import Procedure, ProcedureChunk
from backend.normalize import needs_normalizing, normalize_query


def normalized(query, clarify=False, reason=None):
    return json.dumps({"normalized_query": query, "needs_clarification": clarify, "clarification_reason": reason})


class NeedsNormalizingTest(unittest.TestCase):
    def test_english_questions_bypass_normalization(self):
        for question in ["How do I renew my passport?", "What is the difference between EPF and EPS?",
                         "Can I apply for PAN online in Chennai?", "I need a learner's licence and a voter ID."]:
            with self.subTest(question):
                self.assertFalse(needs_normalizing(question, "en"))

    def test_tamil_script_romanized_tamil_or_a_tamil_selection_are_normalized(self):
        for question in ["எனக்கு பாஸ்போர்ட் வேண்டும்", "PAN card epdi apply panradhu?", "Voter ID illama vote poda mudiyuma?",
                         "EPF EPS rendukum enna vithiyasam?", "Passport renew pannanum"]:
            with self.subTest(question):
                self.assertTrue(needs_normalizing(question, "en"))
        self.assertTrue(needs_normalizing("Passport", "ta"))


@patch("backend.normalize.call_qwen")
class NormalizeQueryTest(unittest.TestCase):
    def test_returns_the_query_and_sends_the_question_as_data(self, llm):
        llm.return_value = normalized(" How do I renew my passport? ")
        self.assertEqual(normalize_query("Passport renew pannanum"), {
            "normalized_query": "How do I renew my passport?", "needs_clarification": False, "clarification_reason": None,
        })
        self.assertTrue(llm.call_args.args[0].endswith("Citizen question: Passport renew pannanum"))

    def test_keeps_the_reason_only_when_clarification_is_needed(self, llm):
        llm.return_value = normalized("Apply", True, " No service named. ")
        self.assertEqual(normalize_query("Apply pannanum")["clarification_reason"], "No service named.")
        llm.return_value = normalized("How do I apply for a PAN card?", False, "Clear.")
        self.assertIsNone(normalize_query("PAN apply pannanum")["clarification_reason"])

    def test_rejects_failed_or_malformed_model_output(self, llm):
        for output in [ExtractionError("down"), "not json", "[]", normalized(""), normalized("x" * 301),
                       json.dumps({"normalized_query": "Passport", "needs_clarification": "no"}),
                       normalized("Passport", True, 5)]:
            with self.subTest(output=str(output)[:40]):
                llm.side_effect = output if isinstance(output, Exception) else None
                llm.return_value = output
                self.assertIsNone(normalize_query("Passport pannanum"))


@patch("backend.normalize.call_qwen")
class NormalizedApiTest(DatabaseTestCase):
    """Identify and guidance search with the English query but keep the contract."""

    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.passport = Procedure(
            name="Passport renewal", summary="Renew a passport.", source_url="https://example.gov.in/passport",
            source_text="Passport renewal", structured_data={"eligibility": None, "steps": ["One"]},
        )
        self.session.add(self.passport)
        self.session.flush()
        self.session.add(ProcedureChunk(procedure_id=self.passport.id, chunk_index=0,
                                        content="Apply for passport renewal online.", embedding=unit_vector(0)))
        self.session.flush()
        self.embedded = []
        self.embed.side_effect = lambda texts, query=False: self.embedded.extend(texts) or [unit_vector(0) for _ in texts]

    def identify(self, question, **extra):
        return self.client.post("/api/identify", json={"question": question, **extra}).json()

    def test_tamil_question_is_searched_as_the_english_query(self, llm):
        llm.return_value = normalized("How do I renew my passport?")
        body = self.identify("Enakku passport renew pannanum")

        self.assertEqual(body["status"], "matched")
        self.assertEqual(body["normalized_query"], "How do I renew my passport?")
        self.assertEqual([c["id"] for c in body["candidates"]], [self.passport.id])
        self.assertTrue(all("pannanum" not in text for text in self.embedded))

    def test_english_questions_never_call_the_model_and_keep_the_old_response(self, llm):
        body = self.identify("How do I renew my passport?")

        llm.assert_not_called()
        self.assertEqual(set(body), {"status", "candidates", "named"})  # "passport" names the Passport page
        self.assertEqual(body, self.identify("How do I renew my passport?", language="en"))

    def test_vague_question_asks_for_clarification_without_searching(self, llm):
        llm.return_value = normalized("Update details", True, "No service named.")
        body = self.identify("Update pannanum", language="ta")

        self.assertEqual(body["status"], "no_match")
        self.assertEqual(body["candidates"], [])
        self.assertIn("Which service or document", body["clarification"])
        self.assertNotIn("normalized_query", body)
        self.assertEqual(self.embedded, [])

    def test_failed_normalization_searches_the_original_question(self, llm):
        llm.side_effect = ExtractionError("model unavailable")
        body = self.identify("Passport renew pannanum")

        self.assertEqual(body["status"], "matched")
        self.assertNotIn("normalized_query", body)
        self.assertIn("Passport renew pannanum", self.embedded)

    def test_rejects_unknown_languages(self, llm):
        response = self.client.post("/api/identify", json={"question": "Passport", "language": "hi"})
        self.assertEqual(response.status_code, 422)

    def test_guidance_answers_the_english_query(self, llm):
        with patch("backend.rag.call_qwen", return_value=json.dumps({"insufficient_evidence": True, "claims": []})) as answer:
            llm.return_value = normalized("How do I renew my passport?")
            body = self.client.post("/api/guidance", json={
                "procedure_id": self.passport.id, "question": "Passport renew panna enna venum?", "language": "ta",
            }).json()
            self.assertEqual(body["normalized_query"], "How do I renew my passport?")
            self.assertIn("How do I renew my passport?", answer.call_args.args[0])
            self.assertNotIn("enna venum", answer.call_args.args[0])

            llm.reset_mock()
            english = self.client.post("/api/guidance", json={"procedure_id": self.passport.id, "question": "Fee?"}).json()
            llm.assert_not_called()
            self.assertNotIn("normalized_query", english)


if __name__ == "__main__":
    unittest.main()
