"""Apply the proposed source remediation to procedureassist_staging ONLY (never the approved DB)."""
import json, os, sys
assert os.environ["DATABASE_URL"].endswith("/procedureassist_staging"), "staging only"
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend.database import SessionLocal
from backend.models import Procedure, ProcedureChunk
from backend.rag import build_chunks
from backend.extractor import extract_procedure
A = "/private/tmp/claude-501/-Users-arunnm-Projects-SOP/db3bcd4a-2175-4a9c-b255-6119f2c7a242/scratchpad/audit2/"
dry = json.load(open(A + "dry.json")); mobile = json.load(open(A + "mobile.json"))
RESCRAPE = (17, 18, 19, 20, 27, 35, 36, 37, 38)
NEW_URL = {16: None, 31: None, 32: None, 33: None}
drafts = {}
with SessionLocal() as db:
    with db.begin():
        def replace(p, url, text):
            db.query(ProcedureChunk).filter_by(procedure_id=p.id).delete()
            p.source_url, p.source_text = url, text
            for c in build_chunks(text):
                c.procedure_id = p.id; db.add(c)
        for pid in RESCRAPE:
            p = db.get(Procedure, pid); replace(p, p.source_url, dry[str(pid)]["text"])
        for pid in (31, 32, 33):
            p = db.get(Procedure, pid); replace(p, p.source_url + "?mobile-app=1", mobile[str(pid)])
        p = db.get(Procedure, 16); p.source_url = p.source_url.split("?")[0] + "?mobile-app=1"
        url = "https://parivahan.gov.in/en/content/fees-and-user-charges"
        draft = extract_procedure(dry[url]["text"], url); drafts["new"] = draft.model_dump()
        rec = Procedure(name=draft.name, department=draft.department, jurisdiction=draft.jurisdiction, summary=draft.summary,
                        source_url=url, source_text=dry[url]["text"], structured_data={"eligibility": draft.eligibility, "steps": draft.steps})
        db.add(rec); db.flush()
        for c in build_chunks(rec.source_text):
            c.procedure_id = rec.id; db.add(c)
    drafts["17"] = extract_procedure(dry["17"]["text"], dry["17"]["url"]).model_dump()
json.dump(drafts, open(A + "staging_drafts.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(drafts, indent=1, ensure_ascii=False)[:3000])
