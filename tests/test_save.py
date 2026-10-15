import db_support  # noqa: F401  (must be first)

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from backend.database import engine
from backend.models import Procedure
from db_support import DatabaseTestCase


APPROVAL = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "sample_procedure.json").read_text()
)


class SaveProcedureTest(DatabaseTestCase):
    def count(self):
        return self.session.query(Procedure).count()

    def test_uses_the_test_database(self):
        self.assertTrue(engine.url.database.endswith("_test"))

    def test_saves_reviewed_procedure(self):
        response = self.client.post("/api/admin/procedures", json=APPROVAL)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["name"], "Fresh Passport Application")
        self.assertEqual(body["status"], "saved")
        saved = self.session.get(Procedure, body["id"])
        self.assertEqual(saved.source_text, APPROVAL["source_text"])
        self.assertEqual(saved.structured_data["steps"], APPROVAL["procedure"]["steps"])
        self.assertIsNone(saved.structured_data["eligibility"])

    def test_rejects_duplicate_source_url(self):
        self.client.post("/api/admin/procedures", json=APPROVAL)
        response = self.client.post("/api/admin/procedures", json=APPROVAL)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "A procedure using this source URL already exists.",
        )
        self.assertEqual(self.count(), 1)

    def test_database_failure_returns_500_and_saves_nothing(self):
        failure = OperationalError("INSERT", {}, Exception("database down"))
        with patch.object(self.session, "commit", side_effect=failure):
            response = self.client.post("/api/admin/procedures", json=APPROVAL)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Unable to save the procedure.")
        self.assertEqual(self.count(), 0)

    def test_invalid_procedure_is_rejected_before_saving(self):
        invalid = {**APPROVAL, "procedure": {**APPROVAL["procedure"], "steps": [" "]}}
        response = self.client.post("/api/admin/procedures", json=invalid)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.count(), 0)


if __name__ == "__main__":
    unittest.main()
