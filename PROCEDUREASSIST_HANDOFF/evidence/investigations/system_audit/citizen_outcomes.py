"""Read-only: what a citizen receives (identify -> procedure card -> guidance) for known risk cases.
DATABASE_URL picks the database; writes nothing."""
import json, os, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend.main import app
c = TestClient(app)
print("DB:", os.environ.get("DATABASE_URL", "procedureassist").rsplit("/", 1)[-1])
for q in sys.argv[1:]:
    ident = c.post("/api/identify", json={"question": q, "language": "en"}).json()
    print(f"\n## {q}\n   identify: {ident.get('status')} {[(x['id'], x['name']) for x in ident.get('candidates', [])]} named={ident.get('named', False)}")
    if ident.get("status") != "matched":
        continue
    pid = ident["candidates"][0]["id"]
    card = c.get(f"/api/procedures/{pid}").json()
    print(f"   card shown: {card['name']!r} | steps: {[s[:70] for s in card['steps'][:3]]}{' ...' if len(card['steps']) > 3 else ''}")
    g = c.post("/api/guidance", json={"procedure_id": pid, "question": q, "language": "en"}).json()
    print(f"   answer: {'insufficient evidence' if g['insufficient_evidence'] else str(len(g['claims'])) + ' claims'}{' (partial)' if g.get('partial') else ''}")
    for cl in g["claims"][:5]:
        print(f"     - [{cl.get('procedure_id', pid)}] {cl['text'][:140]}")
