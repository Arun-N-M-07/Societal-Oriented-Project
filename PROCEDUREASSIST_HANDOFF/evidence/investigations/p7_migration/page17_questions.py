"""Read-only: certificate questions against page 17 through the real API: what /api/identify does, and what
/api/guidance answers on page 17 itself, with every claim that is a CAN-editing step flagged. Run on approved
(page 17 as stored today) and on staging (page 17's planned replacement text). DATABASE_URL picks the database."""
import re, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend.main import app
c = TestClient(app)
CAN_STEP = re.compile(r"Citizen Login|Captcha|Generate OTP|Confirm OTP|Edit CAN|DEPARTMENT WISE|Revenue Department|REV-101|"
                      r"Proceed|Search section|login credentials|tnesevai\.tn\.gov\.in", re.I)
QUESTIONS = ["How do I get a birth certificate in Tamil Nadu?", "How do I get a death certificate in Tamil Nadu?",
             "How do I get a legal heir certificate in Tamil Nadu?", "How do I apply for a community certificate in Tamil Nadu?",
             "How do I apply for an income certificate online in Tamil Nadu?", "How do I get a nativity certificate?",
             "What documents are needed for an income certificate in Tamil Nadu?",
             "What documents do I need for a nativity certificate in Tamil Nadu?", "How do I apply for an OBC certificate?",
             "How do I get a marriage certificate?", "How do I edit my CAN details on e-Sevai?"]
for q in QUESTIONS:
    ident = c.post("/api/identify", json={"question": q}).json()
    found = [x["id"] for x in ident.get("candidates", [])]
    reply = c.post("/api/guidance", json={"procedure_id": 17, "question": q}).json()
    claims = reply["claims"]
    can = [cl for cl in claims if CAN_STEP.search(cl["quote"])]
    print(f"\n## {q}\n   identify: {ident['status']} {found}{' clarification' if ident.get('clarification') else ''}"
          f" | guidance on 17: {'abstained' if reply['insufficient_evidence'] else f'{len(claims)} claims'}"
          f"{f', {len(can)} CAN-editing' if can else ''}{' (partial)' if reply.get('partial') else ''}")
    for cl in claims:
        print(f"   {'CAN ' if cl in can else '    '}{cl['text'][:150]}")
