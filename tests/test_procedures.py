import db_support  # noqa: F401  (must be first)

import unittest

from sqlalchemy import text
from sqlalchemy.exc import InternalError

from backend.database import get_read_only_db
from backend.models import Procedure
from db_support import DatabaseTestCase, make_client


def add_procedure(session, name="Fresh Passport", url="https://example.gov.in/a"):
    procedure = Procedure(
        name=name,
        department="Ministry of External Affairs",
        jurisdiction=None,
        summary="Apply for a passport.",
        source_url=url,
        source_text="PRIVATE SOURCE TEXT",
        structured_data={"eligibility": "Indian citizens.", "steps": ["One", "Two"]},
    )
    session.add(procedure)
    session.flush()
    return procedure


class PublicProcedureTest(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = make_client(self.session, admin=False)
        self.procedure = add_procedure(self.session)

    def test_lists_procedure_summaries_without_private_fields(self):
        response = self.client.get("/api/procedures")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": self.procedure.id,
                    "name": "Fresh Passport",
                    "department": "Ministry of External Affairs",
                    "jurisdiction": None,
                    "summary": "Apply for a passport.",
                }
            ],
        )

    def test_returns_procedure_detail_with_official_link(self):
        response = self.client.get(f"/api/procedures/{self.procedure.id}")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["steps"], ["One", "Two"])
        self.assertEqual(body["eligibility"], "Indian citizens.")
        self.assertEqual(body["source_url"], "https://example.gov.in/a")
        self.assertNotIn("PRIVATE SOURCE TEXT", response.text)
        self.assertNotIn("source_text", body)

    def test_unknown_and_invalid_ids(self):
        self.assertEqual(self.client.get("/api/procedures/999999").status_code, 404)
        self.assertEqual(self.client.get("/api/procedures/abc").status_code, 422)

    def test_public_reads_run_in_a_read_only_transaction(self):
        session = get_read_only_db(self.session)
        with self.assertRaises(InternalError):
            session.execute(text("DELETE FROM procedures"))


class AdminProcedureListTest(DatabaseTestCase):
    def test_lists_saved_procedures_newest_first(self):
        first = add_procedure(self.session)
        second = add_procedure(self.session, "Aadhaar Update", "https://uidai.gov.in/u")

        body = self.client.get("/api/admin/procedures").json()

        self.assertEqual([item["id"] for item in body], [second.id, first.id])
        self.assertEqual(set(body[0]), {"id", "name", "department", "jurisdiction", "source_url"})


if __name__ == "__main__":
    unittest.main()
