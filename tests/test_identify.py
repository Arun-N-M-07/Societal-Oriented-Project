import db_support  # noqa: F401  (must be first)

import math
import unittest

from backend.models import Procedure, ProcedureChunk
from backend.procedure_search import classify
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

    def test_deleted_procedures_are_never_returned(self):
        self.client = make_client(self.session)
        self.client.delete(f"/api/admin/procedures/{self.passport.id}")

        self.assertEqual(self.ask(unit_vector(0)).json()["status"], "no_match")

    def test_invalid_questions_are_rejected(self):
        for body in ({"question": ""}, {"question": "   "}, {"question": "x" * 1001}, {}):
            with self.subTest(body=str(body)[:30]):
                response = self.client.post("/api/identify", json=body)
                self.assertEqual(response.status_code, 422)

    def test_embedding_failure_returns_502(self):
        self.embed.side_effect = EmbeddingError("down")

        response = self.client.post("/api/identify", json={"question": "passport"})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "The search service is unavailable. Try again."})


if __name__ == "__main__":
    unittest.main()
