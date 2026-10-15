"""Test database setup. Import this before any backend module.

Points DATABASE_URL at a dedicated *_test database (TEST_DATABASE_URL) so tests
can never use the development database. Database tests are skipped when the
test database is unreachable, unless REQUIRE_DB_TESTS=1 (CI/release), in which
case they fail.
"""

import os
import sys
import unittest
from unittest.mock import patch

if "backend.config" in sys.modules:
    raise RuntimeError("Import db_support before any backend module.")

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg2://localhost:5432/procedureassist_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
# Unit tests must never reach a real model: fail fast if anything tries.
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:9"
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-that-is-long-enough")
os.environ["ADMIN_USERNAME"] = "admin"
# scrypt hash of TEST_PASSWORD (fixed salt, test use only)
TEST_PASSWORD = "test-password"
os.environ["ADMIN_PASSWORD_HASH"] = (
    "scrypt$16384$8$1$00000000000000000000000000000000$"
    "acec01ab38bb7a9f2d7fa343a6552b78cd0d74679e6c9c3771b2f7173b2ff558"
)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend.auth import require_admin  # noqa: E402
from backend.config import EMBEDDING_DIMENSIONS  # noqa: E402
from backend.database import Base, engine, get_db, get_read_only_db  # noqa: E402
from backend.routes import router  # noqa: E402

if not (engine.url.database or "").endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must name a database ending in _test.")


def _prepare_test_database():
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)


try:  # before any test imports backend.main, which also creates tables
    _prepare_test_database()
except OperationalError:
    pass  # reported by DatabaseTestCase.setUpClass


def unit_vector(position=0):
    """A deterministic embedding pointing along one axis."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[position] = 1.0
    return vector


def fake_embed(texts, *, query=False):
    return [unit_vector() for _ in texts]


def make_client(session=None, admin=True):
    """TestClient for the API; admin=True skips the session check."""
    app = FastAPI()
    app.include_router(router)
    if session is not None:
        app.dependency_overrides[get_db] = lambda: session

        # Requests share one test transaction, so keep each read-only request
        # in a savepoint; rolling it back ends read-only mode for later ones.
        def read_only_session():
            savepoint = session.begin_nested()
            session.execute(text("SET TRANSACTION READ ONLY"))
            try:
                yield session
            finally:
                savepoint.rollback()

        app.dependency_overrides[get_read_only_db] = read_only_session
    if admin:
        app.dependency_overrides[require_admin] = lambda: "admin"
    return TestClient(app)


class DatabaseTestCase(unittest.TestCase):
    """Runs each test inside a transaction that is always rolled back.

    Embeddings are faked so tests never call Ollama; self.embed is the mock.
    """

    @classmethod
    def setUpClass(cls):
        try:
            _prepare_test_database()
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
        self.client = make_client(self.session)
        embed_patch = patch("backend.rag.embed_texts", side_effect=fake_embed)
        self.embed = embed_patch.start()
        self.addCleanup(embed_patch.stop)

    def tearDown(self):
        self.session.close()
        self.transaction.rollback()
        self.connection.close()
