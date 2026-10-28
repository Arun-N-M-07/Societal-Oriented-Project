"""Read-only: the owner's card-safety topics (brief of 27 Oct, section 7) through the real API, with the citizen page's
card rule (CitizenPage.showAndAnswer): a matched procedure's card is shown when the question names it, or when its page
answers with verified claims. Prints what the citizen would see, and flags any claim that is a CAN-editing step.
DATABASE_URL picks the database.   card_safety.py [question ...]  (questions given replace the topic list)"""
import re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.procedure_search import rank_procedures
from backend.rag import embed_texts

c = TestClient(app)
CAN_STEP = re.compile(r"Citizen Login|Captcha|Generate OTP|Confirm OTP|Edit CAN|DEPARTMENT WISE|REV-101", re.I)
TOPICS = [
    ("birth certificate", "How do I get a birth certificate in Tamil Nadu?"),
    ("death certificate", "How do I get a death certificate?"),
    ("income certificate", "How do I apply for an income certificate in Tamil Nadu?"),
    ("income certificate documents", "What documents are needed for an income certificate in Tamil Nadu?"),
    ("community certificate", "How do I apply for a community certificate in Tamil Nadu?"),
    ("nativity certificate", "How do I get a nativity certificate?"),
    ("marriage certificate", "How do I get a marriage certificate?"),
    ("CAN editing", "How do I edit my CAN details on e-Sevai?"),
    ("new PAN", "How do I apply for a new PAN card?"),
    ("PAN-Aadhaar linking", "How do I link my PAN with Aadhaar?"),
    ("overseas voter", "I live abroad. How do I register to vote?"),
    ("ordinary voter", "How do I register to vote?"),
    ("electoral-roll address", "How do I change my address in the electoral roll?"),
    ("Aadhaar enrolment", "How do I enrol for Aadhaar?"),
    ("Aadhaar update", "How do I update my address in Aadhaar?"),
    ("PCC", "How do I get a police clearance certificate?"),
    ("new ration card", "How do I apply for a new ration card in Tamil Nadu?"),
]
TOPICS = [("asked", q) for q in sys.argv[1:]] or TOPICS
names = {p["id"]: p["name"] for p in c.get("/api/procedures").json()}
for topic, q in TOPICS:
    ident = c.post("/api/identify", json={"question": q}).json()
    status, found = ident["status"], [x["id"] for x in ident.get("candidates", [])]
    shown, claims = "no card", []
    if status == "matched":
        reply = c.post("/api/guidance", json={"procedure_id": found[0], "question": q}).json()
        claims = reply["claims"]
        if ident.get("named") or claims:
            shown = f"card: {names[found[0]]}"
    elif status == "ambiguous":
        shown = "choice: " + " / ".join(names[i] for i in found)
    note = ident.get("clarification") or ("" if status != "no_match" else "no approved procedure (NO_MATCH)")
    can = sum(bool(CAN_STEP.search(x["quote"])) for x in claims)
    print(f"[{topic}] {q}\n   identify: {status} {[names[i] for i in found]} named={ident.get('named', False)} -> {shown}"
          f"{'; ' + note if note else ''}; {len(claims)} claims{f', {can} CAN-editing STEP(S)' if can else ''}")
    with SessionLocal() as db:
        top = rank_procedures(db, embed_texts([q], query=True)[0])
    print("   top 3 by score: " + "; ".join(f"{names[i][:40]} {s:.3f}" for i, s in top))
    for x in claims[:3]:
        print(f"     - {x['text'][:140]}")
