"""Test database setup. Import this before any backend module.

Points DATABASE_URL at a dedicated *_test database (TEST_DATABASE_URL) so tests
can never use the development database. Database tests are skipped when the
test database is unreachable, unless REQUIRE_DB_TESTS=1 (CI/release), in which
case they fail.
"""

import os
import sys
import unittest

if "backend.config" in sys.modules:
    raise RuntimeError("Import db_support before any backend module.")

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg2://localhost:5432/procedureassist_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-that-is-long-enough")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend.database import Base, engine, get_db  # noqa: E402
from backend.routes import router  # noqa: E402

if not (engine.url.database or "").endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must name a database ending in _test.")


class DatabaseTestCase(unittest.TestCase):
    """Runs each test inside a transaction that is always rolled back."""

    @classmethod
    def setUpClass(cls):
        try:
            Base.metadata.create_all(engine)
        except OperationalError as error:
            if os.environ.get("REQUIRE_DB_TESTS") == "1":
                raise
            raise unittest.SkipTest(f"Test database unavailable: {error.orig}")

    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.session = Session(
            bind=self.connection, join_transaction_mode="create_savepoint"
        )
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: self.session
        self.client = TestClient(app)

    def tearDown(self):
        self.session.close()
        self.transaction.rollback()
        self.connection.close()
