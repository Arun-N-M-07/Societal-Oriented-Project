"""Read-only: the H3 question matrix through the real API, 3 runs each. 'routed' = identify then guidance, as a
citizen gets it; 'page39' = guidance asked directly on the Rule 81 fee table (page 39). Prints every claim with its
quote so the fee/category association can be checked by hand. DATABASE_URL picks the database; writes nothing."""
import json, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend.main import app

c = TestClient(app)
RUNS = 3
QUESTIONS = [  # (question, expected answer, ask on page 39 directly too?)
    ("What is the fee to renew the registration certificate of my motorcycle?", "Rs 300, row 4(b)", True),
    ("What is the fee to renew the RC of a motorcycle?", "Rs 300, row 4(b); never the over-20-years Rs 2000 as ordinary", True),
    ("How much does a duplicate RC cost?", "item 5: half of item 4", True),
    ("RC renewal fee for a car", "row 4(c)i Rs 600 (non-transport LMV); never the fitness Rs 200", True),
    ("What is the fee to renew my vehicle RC?", "item 4 rows by class, or partial; never fitness Rs 200 as RC", True),
    ("What is the fitness test fee for a motorcycle?", "item 10(a): manual Rs 200 / automated Rs 400; labelled fitness", True),
    ("What is the RC renewal fee for an imported car older than 20 years?", "item 16(e)/(f) with 'older than 20 years'", True),
    ("What is the hypothecation endorsement fee for a car?", "item 9(b) Rs 1500; no item-10 rows", True),
    ("What is the fee for an International Driving Permit?", "Rs 1000 (page 27)", False),
    ("What is the fee for renewing a driving licence?", "Rs 200 (page 27)", False),
]
for question, expected, on_39 in QUESTIONS:
    ident = c.post("/api/identify", json={"question": question, "language": "en"}).json()
    routed = ident["candidates"][0]["id"] if ident.get("status") == "matched" else None
    targets = [("routed", routed)] + ([("page39", 39)] if on_39 and routed != 39 else [])
    for label, pid in targets:
        for run in range(1, RUNS + 1):
            if pid is None:
                print(json.dumps({"q": question, "expected": expected, "mode": label, "run": run,
                                  "identify": ident.get("status"), "outcome": "no page"}, ensure_ascii=False))
                break
            g = c.post("/api/guidance", json={"procedure_id": pid, "question": question, "language": "en"}).json()
            print(json.dumps({"q": question, "expected": expected, "mode": label, "page": pid, "run": run,
                              "identify": ident.get("status"), "partial": g.get("partial", False),
                              "outcome": "abstained" if g["insufficient_evidence"] else f"{len(g['claims'])} claims",
                              "claims": [{"page": cl.get("procedure_id", pid), "text": cl["text"], "quote": cl["quote"]} for cl in g["claims"]]},
                             ensure_ascii=False), flush=True)
