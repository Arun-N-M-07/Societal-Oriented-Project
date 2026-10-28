"""End-to-end ingestion check on previously unseen official URLs, through the real routes, scraper, model and
embeddings: Extract -> approval -> chunks and embeddings -> identify -> guidance, with no code specific to any page.

It runs only against a *_test database (TEST_DATABASE_URL), inside one transaction that is always rolled back, so
nothing is kept and the approved and staging databases are never touched. The approval here is a test step that
saves the model's draft as it is; it is not a content approval.

    .venv/bin/python scripts/evaluate_ingestion.py
"""

import os
import re
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg2://localhost:5432/procedureassist_test"
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from backend.auth import require_admin  # noqa: E402
from backend.config import EMBEDDING_DIMENSIONS  # noqa: E402
from backend.database import Base, engine, get_db, get_read_only_db  # noqa: E402
from backend.models import Procedure, ProcedureChunk  # noqa: E402
from backend.rag import chunk_text  # noqa: E402
from backend.routes import router  # noqa: E402

if not (engine.url.database or "").endswith("_test"):
    sys.exit("Runs only against a database whose name ends in _test.")

# (unseen official URL, a question that page answers, a pattern a cited quote must contain)
CASES = [
    ("https://www.indiapost.gov.in/insurance-services/pmsby", "Who can join PM Suraksha Bima Yojana?", r"18 to 70"),
    ("https://www.passportindia.gov.in/psp/ApplyPCC", "How do I apply for a police clearance certificate?", r"(?i)register"),
    ("https://krishnagiri.nic.in/scheme/civil-registration-system/", "Within how many days must a birth be registered in Tamil Nadu?", r"21 days"),
    ("https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/instant-e-pan?mobile-app=1",
     "Is there any fee for an instant e-PAN?", r"(?i)free of cost"),
    ("https://pfrda.org.in/web/pfrda/schemes/national-pension-system/nps-for-all-citizen-models",
     "What is the age limit to join the National Pension System?", r"18 to 85"),
    ("https://consumer.tn.gov.in/eligibility_ration.htm", "Where do I submit a new ration card application in Chennai?",
     r"Assistant Commissioner"),
]
UNRELATED = ["How do I book a train ticket?", "How do I renew my UK driving licence?"]
# Questions an ingested page does not answer (the PMSBY page links its premium only in PDFs): the answer must abstain.
NOT_STATED = [("https://www.indiapost.gov.in/insurance-services/pmsby", "What is the yearly premium for PM Suraksha Bima Yojana?")]

with engine.begin() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
Base.metadata.create_all(engine)

connection = engine.connect()
transaction = connection.begin()
session = Session(bind=connection, join_transaction_mode="create_savepoint")


def read_only_session():
    savepoint = session.begin_nested()
    session.execute(text("SET TRANSACTION READ ONLY"))
    try:
        yield session
    finally:
        savepoint.rollback()


app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_db] = lambda: session
app.dependency_overrides[get_read_only_db] = read_only_session
app.dependency_overrides[require_admin] = lambda: "ingestion-check"
client = TestClient(app)
failures = []


def check(ok, what):
    print(f"{'ok  ' if ok else 'FAIL'} {what}")
    if not ok:
        failures.append(what)


try:
    pages = {}
    for url, _, _ in CASES:
        extracted = client.post("/api/admin/extract", json={"source_url": url})
        check(extracted.status_code == 200, f"extract {url} ({extracted.status_code})")
        if extracted.status_code != 200:
            continue
        body = extracted.json()
        saved = client.post("/api/admin/procedures", json={
            "procedure": body["procedure"], "source_text": body["source_text"], "provenance_token": body["provenance_token"]})
        check(saved.status_code == 200, f"approve and save {body['procedure']['name']!r} ({saved.status_code})")
        if saved.status_code != 200:
            continue
        pid = saved.json()["id"]
        pages[url] = pid
        chunks = session.query(ProcedureChunk).filter_by(procedure_id=pid).order_by(ProcedureChunk.chunk_index).all()
        check([c.content for c in chunks] == chunk_text(body["source_text"])
              and all(len(c.embedding) == EMBEDDING_DIMENSIONS for c in chunks),
              f"indexed {len(chunks)} chunks with {EMBEDDING_DIMENSIONS}-value embeddings")

    owner = dict(session.query(ProcedureChunk.id, ProcedureChunk.procedure_id))
    for url, question, quote in CASES:
        if url not in pages:
            continue
        found = client.post("/api/identify", json={"question": question}).json()
        matched = found.get("status") == "matched" and found["candidates"][0]["id"] == pages[url]
        check(matched, f"identify {question!r} -> {found.get('status')} {[c['id'] for c in found.get('candidates', [])]}")
        reply = client.post("/api/guidance", json={"procedure_id": pages[url], "question": question}).json()
        claims = reply.get("claims", [])
        check(bool(claims) and all(owner[c["chunk_id"]] == pages[url] for c in claims), f"answer cites only its own page ({len(claims)} claims)")
        check(any(re.search(quote, c["quote"]) for c in claims), f"a cited quote contains /{quote}/")
        for claim in claims:
            print(f"       - {claim['text'][:110]}")
    for url, question in NOT_STATED:
        if url in pages:
            reply = client.post("/api/guidance", json={"procedure_id": pages[url], "question": question}).json()
            check(reply.get("insufficient_evidence") is True, f"not stated on the page, so no answer: {question!r}")
    for question in UNRELATED:
        status = client.post("/api/identify", json={"question": question}).json().get("status")
        check(status == "no_match", f"unrelated {question!r} -> {status}")
finally:
    transaction.rollback()
    session.close()
    connection.close()

with engine.connect() as connection:
    left = connection.execute(text("SELECT count(*) FROM procedures WHERE source_url = ANY(:urls)"),
                              {"urls": [url.rstrip("/") for url, _, _ in CASES]}).scalar()
check(left == 0, "nothing kept: the transaction was rolled back")
engine.dispose()
print(f"\n{len(failures)} failed check(s)")
sys.exit(1 if failures else 0)
