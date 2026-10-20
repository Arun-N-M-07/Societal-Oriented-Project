import db_support  # noqa: F401  (must be first)

import json
import math
import unittest
from unittest.mock import patch

from backend.extractor import ExtractionError
from backend.models import Procedure, ProcedureChunk
from backend.procedure_search import classify, extract_needs, mentions
from backend.rag import EmbeddingError
from db_support import DatabaseTestCase, make_client, unit_vector


class ClassifyTest(unittest.TestCase):
    def test_outcomes(self):
        cases = [
            ([], ("no_match", [])),
            ([(1, 0.40), (2, 0.39)], ("no_match", [])),
            ([(1, 0.80), (2, 0.60)], ("matched", [1])),
            ([(1, 0.70), (2, 0.69), (3, 0.40)], ("ambiguous", [1, 2])),
            ([(1, 0.70), (2, 0.70), (3, 0.70), (4, 0.70)], ("ambiguous", [1, 2, 3])),
        ]
        for ranked, expected in cases:
            with self.subTest(ranked=ranked):
                self.assertEqual(classify(ranked, min_score=0.53, margin=0.03), expected)


class MentionsTest(unittest.TestCase):
    def test_named_terms_must_mostly_appear_in_the_official_text(self):
        text = "Apply for a Community Certificate on the e-Sevai portal using your Citizen Number (CAN)."
        cases = [
            ("How do I get a certificate?", True),
            ("What documents does a Community Certificate need?", True),
            ("What is a Citizen Access Number (CAN)?", True),
            ("How can I update my address on my Aadhaar card?", False),
            ("How do I apply for a Caste Certificate in Gujarat?", False),
        ]
        for question, expected in cases:
            with self.subTest(question=question):
                self.assertEqual(mentions(text, question), expected)

    def test_ignores_sentence_initial_words(self):
        text = "Updating Data on Aadhaar: upload address proof."
        question = "I want to update my address on Aadhaar. What documents do I need, and how do I apply?"
        self.assertTrue(mentions(text, question))

    def test_matches_whole_words_only(self):
        self.assertFalse(mentions("Company registration and panchayat records.", "How do I update my PAN?"))

    def test_accepts_plural_names(self):
        self.assertTrue(mentions("Overseas Indian electors: an NRI can register online.", "Can NRIs vote in Indian elections?"))

    def test_rejects_a_page_for_another_country(self):
        self.assertFalse(mentions("Register to vote in the UK online.", "How do I register to vote in India?"))


MESSAGE = "I want to renew my passport and update my Aadhaar address. Which should I do first?"


def needs_output(*phrases, relation="Which should I do first?"):
    return json.dumps({
        "needs": [{"phrase": p, "question": f"How do I {p}?"} for p in phrases],
        "relation_question": relation,
    })


@patch("backend.procedure_search.call_qwen")
class ExtractNeedsTest(unittest.TestCase):
    def test_returns_needs_copied_from_the_message(self, llm):
        llm.return_value = needs_output("renew my passport", "update my Aadhaar address")
        needs, relation = extract_needs(MESSAGE)
        self.assertEqual([n["phrase"] for n in needs], ["renew my passport", "update my Aadhaar address"])
        self.assertEqual(relation, "Which should I do first?")

    def test_rejects_untrustworthy_output(self, llm):
        cases = {
            "invented phrase": needs_output("renew my passport", "apply for a gun licence"),
            "same phrase twice": needs_output("renew my passport", "renew my passport"),
            "extra field": json.dumps({"needs": [{"phrase": "renew my passport", "question": "q", "procedure_id": 1}]}),
            "empty question": json.dumps({"needs": [{"phrase": "renew my passport", "question": " "}]}),
            "not a list": json.dumps({"needs": "renew my passport"}),
            "not json": "renew my passport",
        }
        for name, output in cases.items():
            with self.subTest(name):
                llm.return_value = output
                self.assertIsNone(extract_needs(MESSAGE))
        llm.side_effect = ExtractionError("down")
        self.assertIsNone(extract_needs(MESSAGE))

    def test_accepts_a_verb_shared_by_listed_services_but_not_new_words(self, llm):
        message = "Explain EPF, EPS and EDLI and how they differ."
        llm.return_value = json.dumps({"needs": [{"phrase": f"Explain {s}", "question": f"What is {s}?"} for s in ("EPF", "EPS", "EDLI")],
                                       "relation_question": "how they differ"})
        needs, relation = extract_needs(message)
        self.assertEqual([n["phrase"] for n in needs], ["Explain EPF", "Explain EPS", "Explain EDLI"])
        self.assertEqual(relation, "how they differ")

        llm.return_value = json.dumps({"needs": [{"phrase": "Explain EPF", "question": "q"}, {"phrase": "Explain PAN", "question": "q"}]})
        self.assertIsNone(extract_needs(message))

    def test_drops_a_relation_question_not_in_the_message(self, llm):
        llm.return_value = needs_output("renew my passport", "update my Aadhaar address", relation="Can I reuse documents?")
        self.assertIsNone(extract_needs(MESSAGE)[1])


def between(first, second):
    vector = [a + b for a, b in zip(unit_vector(first), unit_vector(second))]
    return [value / math.sqrt(2) for value in vector]


class IdentifyApiTest(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.passport = self.add("Passport", [unit_vector(0), unit_vector(3)])
        self.aadhaar = self.add("Aadhaar update", [unit_vector(1)])
        self.tax = self.add("Income tax return", [unit_vector(2)])

    def add(self, name, vectors):
        procedure = Procedure(
            name=name,
            summary=f"{name} summary.",
            source_url=f"https://example.gov.in/{name.replace(' ', '-')}",
            source_text="PRIVATE SOURCE TEXT",
            structured_data={"eligibility": None, "steps": ["One"]},
        )
        self.session.add(procedure)
        self.session.flush()
        for index, vector in enumerate(vectors):
            self.session.add(
                ProcedureChunk(
                    procedure_id=procedure.id, chunk_index=index, content="x", embedding=vector
                )
            )
        self.session.flush()
        return procedure

    def ask(self, query_vector, question="How do I get a passport?"):
        self.embed.side_effect = lambda texts, query=False: [query_vector]
        return self.client.post("/api/identify", json={"question": question})

    def test_matches_on_the_best_chunk_of_each_procedure(self):
        response = self.ask(unit_vector(3))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "matched")
        self.assertEqual([c["id"] for c in body["candidates"]], [self.passport.id])
        self.assertEqual(set(body["candidates"][0]), {"id", "name", "department", "jurisdiction", "summary"})
        self.assertNotIn("PRIVATE SOURCE TEXT", response.text)
        self.assertTrue(self.embed.call_args.kwargs["query"])

    def test_asks_for_clarification_when_procedures_are_equally_plausible(self):
        body = self.ask(between(1, 2)).json()

        self.assertEqual(body["status"], "ambiguous")
        self.assertEqual({c["id"] for c in body["candidates"]}, {self.aadhaar.id, self.tax.id})

    def test_reports_no_match_for_unrelated_questions(self):
        body = self.ask(unit_vector(9), "What is the best biryani recipe?").json()

        self.assertEqual(body, {"status": "no_match", "candidates": []})

    def test_similar_procedure_without_the_named_service_is_not_a_match(self):
        body = self.ask(unit_vector(3), "How do I update my Aadhaar address?").json()

        self.assertEqual(body, {"status": "no_match", "candidates": []})

    def test_a_bare_acronym_in_a_procedure_name_rescues_a_near_miss(self):
        eps = self.add("Employees' Pension Scheme (EPS)", [unit_vector(4)])
        eps.source_text = "EPS pension rules"
        # cosine `score` with the EPS chunk: below IDENTIFY_MIN_SCORE (0.53), around ACRONYM_MIN_SCORE (0.45)
        near = lambda score: [score if i == 4 else (1 - score ** 2) ** 0.5 if i == 9 else 0.0 for i in range(len(unit_vector()))]
        self.assertEqual(self.ask(near(0.5), "What is EPS?").json()["candidates"][0]["id"], eps.id)
        self.assertEqual(self.ask(near(0.5), "What is the pension?").json()["status"], "no_match")
        self.assertEqual(self.ask(near(0.4), "What is EPS?").json()["status"], "no_match")

    def test_name_check_does_not_turn_a_close_call_into_a_match(self):
        self.aadhaar.source_text = "Aadhaar update in India"
        body = self.ask(between(1, 2), "How do I update my details in India?").json()

        self.assertEqual(body["status"], "ambiguous")
        self.assertEqual({c["id"] for c in body["candidates"]}, {self.aadhaar.id, self.tax.id})

    def test_deleted_procedures_are_never_returned(self):
        self.client = make_client(self.session)
        self.client.delete(f"/api/admin/procedures/{self.passport.id}")

        self.assertEqual(self.ask(unit_vector(0)).json()["status"], "no_match")

    def test_invalid_questions_are_rejected(self):
        for body in ({"question": ""}, {"question": "   "}, {"question": "x" * 1001}, {}):
            with self.subTest(body=str(body)[:30]):
                response = self.client.post("/api/identify", json=body)
                self.assertEqual(response.status_code, 422)

    def test_single_questions_never_call_the_extraction_model(self):
        with patch("backend.procedure_search.call_qwen") as llm:
            self.ask(unit_vector(3), "How do I get a passport?")
        llm.assert_not_called()

    def test_embedding_failure_returns_502(self):
        self.embed.side_effect = EmbeddingError("down")

        response = self.client.post("/api/identify", json={"question": "passport"})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "The search service is unavailable. Try again."})



@patch("backend.procedure_search.call_qwen")
class IdentifyNeedsApiTest(DatabaseTestCase):
    VECTORS = {"renew my passport": 0, "update my Aadhaar address": 1, "get a driving licence": 9,
               "check the documents for that update": 1, "file my tax return": 2, "get a voter ID": 8}

    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.passport = IdentifyApiTest.add(self, "Passport", [unit_vector(0)])
        self.aadhaar = IdentifyApiTest.add(self, "Aadhaar", [unit_vector(1)])
        self.aadhaar.source_text = "Updating Data on Aadhaar"
        self.tax = IdentifyApiTest.add(self, "Income tax", [unit_vector(2)])
        self.embed.side_effect = lambda texts, query=False: [unit_vector(self.VECTORS.get(t, 7)) for t in texts]

    def ask(self, llm, message, *phrases):
        llm.return_value = needs_output(*phrases)
        return self.client.post("/api/identify", json={"question": message}).json()

    def test_matches_each_need_independently(self, llm):
        body = self.ask(llm, "I want to renew my passport, update my Aadhaar address and get a driving licence. Which should I do first?",
                        "renew my passport", "update my Aadhaar address", "get a driving licence")

        self.assertEqual(body["status"], "multiple")
        self.assertEqual([(n["phrases"], n["status"]) for n in body["needs"]], [
            (["renew my passport"], "matched"), (["update my Aadhaar address"], "matched"),
            (["get a driving licence"], "no_match"),
        ])
        self.assertEqual(body["needs"][0]["candidates"][0]["id"], self.passport.id)
        self.assertEqual(body["needs"][1]["candidates"][0]["id"], self.aadhaar.id)
        self.assertEqual(body["relation_question"], "Which should I do first?")
        self.assertEqual(body["pending"], [])
        self.assertEqual(llm.call_count, 1)

    def test_needs_for_the_same_procedure_share_one_answer(self, llm):
        body = self.ask(llm, "I need to update my Aadhaar address and check the documents for that update, and renew my passport.",
                        "update my Aadhaar address", "check the documents for that update", "renew my passport")

        self.assertEqual(len(body["needs"]), 2)
        self.assertEqual(body["needs"][0]["phrases"], ["update my Aadhaar address", "check the documents for that update"])
        self.assertEqual(body["needs"][0]["question"],
                         "How do I update my Aadhaar address? How do I check the documents for that update?")

    def test_background_cannot_hide_the_one_real_need(self, llm):
        llm.return_value = needs_output("renew my passport", relation=None)
        message = "I updated my Aadhaar last week. Now I need to renew my passport."
        self.embed.side_effect = lambda texts, query=False: [unit_vector(self.VECTORS.get(t, 7)) for t in texts]
        body = self.client.post("/api/identify", json={"question": message}).json()

        self.assertEqual(body, {"status": "matched", "candidates": [body["candidates"][0]]})
        self.assertEqual(body["candidates"][0]["id"], self.passport.id)

    def test_background_that_matches_another_procedure_does_not_win(self, llm):
        llm.return_value = needs_output("renew my passport", relation=None)
        message = "I recently updated my Aadhaar. Now I want to renew my passport."
        self.embed.side_effect = lambda texts, query=False: [unit_vector(1 if "Aadhaar" in t else 0) for t in texts]
        body = self.client.post("/api/identify", json={"question": message}).json()

        self.assertEqual(body["candidates"][0]["id"], self.passport.id)

    def test_the_whole_message_is_used_when_the_need_alone_matches_nothing(self, llm):
        llm.return_value = needs_output("renew my passport", relation=None)
        self.embed.side_effect = lambda texts, query=False: [unit_vector(1 if "," in t else 9) for t in texts]
        body = self.client.post("/api/identify", json={"question": "I want to renew my passport, please."}).json()

        self.assertEqual(body["candidates"][0]["id"], self.aadhaar.id)

    def test_questions_about_one_procedure_keep_the_single_flow(self, llm):
        llm.return_value = needs_output("update my Aadhaar address", "check the documents for that update")
        self.embed.side_effect = lambda texts, query=False: [unit_vector(1) for _ in texts]
        body = self.client.post("/api/identify", json={
            "question": "I need to update my Aadhaar address and check the documents for that update."}).json()

        self.assertEqual(body, {"status": "matched", "candidates": [body["candidates"][0]]})
        self.assertEqual(body["candidates"][0]["id"], self.aadhaar.id)

    def test_needs_over_the_limit_are_listed_not_dropped(self, llm):
        phrases = ["renew my passport", "update my Aadhaar address", "file my tax return", "get a driving licence", "get a voter ID"]
        body = self.ask(llm, "I need to " + ", ".join(phrases) + ".", *phrases)

        self.assertEqual([n["phrases"][0] for n in body["needs"]], phrases[:3])
        self.assertEqual(body["pending"], [{"phrase": p, "question": f"How do I {p}?"} for p in phrases[3:]])

    def test_each_listed_service_is_matched_separately(self, llm):
        for procedure, name in ((self.passport, "EPF"), (self.aadhaar, "EPS"), (self.tax, "EDLI")):
            procedure.source_text = f"{name} scheme rules"
        llm.return_value = json.dumps({"needs": [{"phrase": f"Explain {s}", "question": f"What is {s}?"} for s in ("EPF", "EPS", "EDLI")],
                                       "relation_question": None})
        # Bare names can score too low on their own; each need's question is the fallback.
        vectors = {"Explain EPF": 0, "What is EPS?": 1, "What is EDLI?": 2}
        self.embed.side_effect = lambda texts, query=False: [unit_vector(vectors.get(t, 7)) for t in texts]
        body = self.client.post("/api/identify", json={"question": "Explain EPF, EPS and EDLI"}).json()

        self.assertEqual(body["status"], "multiple")
        self.assertEqual([(n["status"], n["candidates"][0]["id"]) for n in body["needs"]],
                         [("matched", self.passport.id), ("matched", self.aadhaar.id), ("matched", self.tax.id)])

    def test_a_comparison_reaches_extraction_and_keeps_unsupported_services_unmatched(self, llm):
        llm.return_value = json.dumps({"needs": [{"phrase": "passport renewal", "question": "How do I renew my passport?"},
                                                 {"phrase": "ration card application", "question": "How do I apply for a ration card?"}],
                                       "relation_question": None})
        self.embed.side_effect = lambda texts, query=False: [unit_vector(0 if "passport" in t else 9) for t in texts]
        body = self.client.post("/api/identify", json={"question": "Compare passport renewal versus a ration card application"}).json()

        self.assertEqual(llm.call_count, 1)
        self.assertEqual([(n["phrases"], n["status"]) for n in body["needs"]],
                         [(["passport renewal"], "matched"), (["ration card application"], "no_match")])

    def test_a_comparison_gets_one_need_per_side_and_sides_are_distinct(self, llm):
        self.passport.source_text, self.aadhaar.source_text = "EPF rules", "EPS rules"
        message = "What is the difference between EPF and EPS?"
        llm.return_value = json.dumps({"needs": [{"phrase": "difference between EPF and EPS", "question": message}],
                                       "relation_question": None})
        self.embed.side_effect = lambda texts, query=False: [
            between(0, 1) if t in ("EPF", "What is EPF?") else unit_vector(1 if t in ("EPS", "What is EPS?") else 7) for t in texts]
        body = self.client.post("/api/identify", json={"question": message}).json()

        self.assertEqual([(n["phrases"], n["status"], n["candidates"][0]["id"]) for n in body["needs"]],
                         [(["EPF"], "matched", self.passport.id), (["EPS"], "matched", self.aadhaar.id)])
        self.assertEqual(body["relation_question"], message)

    def test_untrustworthy_or_single_extraction_keeps_the_single_flow(self, llm):
        for output in (needs_output("renew my passport"), "not json"):
            with self.subTest(output=output[:20]):
                llm.return_value = output
                self.embed.side_effect = lambda texts, query=False: [unit_vector(0)]
                body = self.client.post("/api/identify", json={"question": "I want to renew my passport, please."}).json()
                self.assertEqual(body, {"status": "matched", "candidates": [body["candidates"][0]]})
                self.assertEqual(body["candidates"][0]["id"], self.passport.id)

if __name__ == "__main__":
    unittest.main()
