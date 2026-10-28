"""The admin page's own routes (Extract, Approve, Delete), run in this process against the database DATABASE_URL names.
Only the sign-in check is replaced, because the admin password is not available to Claude; extraction, the provenance
token, chunking, embedding and saving are the application's code, unchanged (21, current brief).
    admin_workflow.py extract <url> <out.json>            source text, the model's draft and the provenance token
    admin_workflow.py approve <extract.json> <card.json>  saves the reviewed card with exactly the extracted text
    admin_workflow.py delete <id> [--rollback]            deletes one procedure; --rollback undoes it after the checks
It refuses any delete in procedureassist, and any approval there except the five candidates the owner delegated."""
import json, math, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.auth import require_admin
from backend.database import engine, get_db
from backend.rag import chunk_text
from backend.routes import router

APPROVED = "procedureassist"
DELEGATED = {  # N1, N3, N4, N8, N10 (owner's brief of 27 Oct, section 5)
    "https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/instant-e-pan?mobile-app=1",
    "https://www.passportindia.gov.in/psp/ApplyPCC",
    "https://uidai.gov.in/en/aadhaar-enrolment",
    "https://krishnagiri.nic.in/scheme/civil-registration-system",
    "https://consumer.tn.gov.in/eligibility_ration.htm",
}
CHECKS = """select (select count(*) from procedures), (select count(*) from procedure_chunks),
  (select count(*) from procedure_chunks c left join procedures p on p.id = c.procedure_id where p.id is null),
  (select md5(string_agg(id||name||coalesce(department,'')||coalesce(jurisdiction,'')||summary||source_url||source_text
     ||structured_data::text, '|' order by id)) from procedures where id <> :id),
  (select md5(string_agg(id||'/'||procedure_id||'/'||chunk_index||content||embedding::text, '|' order by id))
     from procedure_chunks where procedure_id <> :id)"""

command, database = sys.argv[1], engine.url.database
connection = engine.connect()
outer = connection.begin() if "--rollback" in sys.argv else None
session = Session(bind=connection, join_transaction_mode="create_savepoint") if outer else Session(engine)
app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_db] = lambda: session
app.dependency_overrides[require_admin] = lambda: "claude-delegated"
client = TestClient(app)
print(f"database: {database}")

if command == "extract":
    response = client.post("/api/admin/extract", json={"source_url": sys.argv[2]})
    print(response.status_code, response.json().get("detail", ""))
    response.raise_for_status()
    json.dump(response.json(), open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
    print(f"{len(response.json()['source_text'])} characters, {len(chunk_text(response.json()['source_text']))} chunks")
elif command == "approve":
    extracted, card = json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))
    url = extracted["procedure"]["source_url"]
    if database == APPROVED and url not in DELEGATED:
        sys.exit(f"Refusing: {url} is not one of the five delegated candidates.")
    response = client.post("/api/admin/procedures", json={"procedure": {**card, "source_url": url},
                           "source_text": extracted["source_text"], "provenance_token": extracted["provenance_token"]})
    print(response.status_code, response.json())
    response.raise_for_status()
    pid = response.json()["id"]
    chunks = session.execute(text("select content, embedding from procedure_chunks where procedure_id = :id "
                                  "order by chunk_index"), {"id": pid}).all()
    vectors = [json.loads(v) if isinstance(v, str) else list(v) for _, v in chunks]
    print(f"id {pid}: {len(chunks)} chunks, equal to chunk_text(source_text): "
          f"{[c for c, _ in chunks] == chunk_text(extracted['source_text'])}; vectors 1024 finite non-zero: "
          f"{all(len(v) == 1024 and all(map(math.isfinite, v)) and any(v) for v in vectors)}")
elif command == "delete":
    if database == APPROVED:
        sys.exit("Refusing: deleting from the approved database needs the owner's approval and the admin page.")
    pid = int(sys.argv[2])
    before = session.execute(text(CHECKS), {"id": pid}).one()
    response = client.delete(f"/api/admin/procedures/{pid}")
    print("DELETE", response.status_code)
    after = session.execute(text(CHECKS), {"id": pid}).one()
    print(f"pages {before[0]} -> {after[0]}; chunks {before[1]} -> {after[1]}; orphan chunks {after[2]}; every other "
          f"procedure unchanged: {before[3] == after[3]}; every other chunk unchanged: {before[4] == after[4]}")
    if outer:
        outer.rollback()
        print("rolled back; pages now", connection.execute(text("select count(*) from procedures")).scalar())
session.close()
connection.close()
