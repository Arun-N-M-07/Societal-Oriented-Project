"""Read-only A/B of one added sentence in the answer prompt (rag.build_guidance_prompt), on the same questions and
pages: final claims with and without it. DATABASE_URL picks the database; nothing is written."""
import json, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from fastapi.testclient import TestClient
from backend import rag
from backend.main import app
ADDED = ("What the citizen says about themselves (where they live or work, what they do) tells you which passages apply "
         "to them; it need not appear in the passages.\n")
ANCHOR = "A link, button, heading or menu label is not a fact.\n"
CASES = [(21, q) for q in ["I work in Saudi Arabia. How do I register to vote?",
                           "I study in Canada. Can I still vote in Indian elections?",
                           "I am an NRI. How do I register as a voter?", "I live abroad. How do I register to vote?"]] + \
        [(int(p), q) for p, q in (line.split("|", 1) for line in sys.stdin.read().strip().splitlines())]
real = rag.build_guidance_prompt
client = TestClient(app)
def run():
    return [[c["text"] for c in client.post("/api/guidance", json={"procedure_id": p, "question": q}).json()["claims"]] for p, q in CASES]
base = run()
rag.build_guidance_prompt = lambda question, chunks, mode="answer": real(question, chunks, mode).replace(ANCHOR, ANCHOR + ADDED, 1)
assert ADDED in rag.build_guidance_prompt("q", [], "answer")
variant = run()
changed = 0
for (p, q), a, b in zip(CASES, base, variant):
    same = a == b
    changed += not same
    print(f"{'same   ' if same else 'CHANGED'} page {p}: {q[:70]!r}: {len(a)} -> {len(b)} claims")
    if not same:
        print("     without:", [x[:90] for x in a]); print("     with   :", [x[:90] for x in b])
print(f"{changed} of {len(CASES)} answers changed")
