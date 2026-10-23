"""End-to-end answer quality on labelled questions, through the real API routes.

Read-only: uses the approved procedures in DATABASE_URL and the real Ollama
models. Each question follows the citizen page's own calls (identify, then
guidance, or relation for several needs; follow-ups go straight to guidance),
and each failure is put down to the first stage that went wrong:
normalize, identify, clarification, evidence not stored (the matched page
never states it), retrieval (stored but not among the retrieved passages),
generation/verification (retrieved, but no verified claim cites it),
unsupported (answered although the page does not state it), citation (a
claim cites another procedure's passage) or asks to choose (not wrong: the
citizen is offered the expected procedure among close candidates) or asks which
service (not wrong: the question names none, so it is not searched).

    .venv/bin/python scripts/evaluate_answers.py [fixture.json]
"""

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from backend.database import SessionLocal  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models import Procedure, ProcedureChunk  # noqa: E402
from backend.rag import retrieve  # noqa: E402

fixture = sys.argv[1] if len(sys.argv) > 1 else "fixtures/evaluation/answers.json"
cases = json.loads((Path(__file__).resolve().parents[1] / fixture).read_text())["cases"]
client = TestClient(app)


def post(path, body):
    response = client.post(path, json=body)
    response.raise_for_status()
    return response.json()


def shown(status, candidates):
    return urls[candidates[0]["id"]] if status == "matched" else None if status == "no_match" else "ambiguous"


def evaluate(db, case):
    """(failed stage or None, printable detail)."""
    message, language = case["message"], case.get("language", "en")
    if "context" in case:
        target = next(p for p in procedures if case["context"] in p.source_url).id
        reply = post("/api/guidance", {"procedure_id": target, "question": message, "language": language})
        target = reply["procedure_id"]  # a page naming the open procedure may have answered
        if reply["insufficient_evidence"]:  # as the citizen page does: search the question again
            query = reply.get("normalized_query")
            body = post("/api/identify", {"question": query or message, "language": "en" if query else language})
            if body["status"] == "matched":
                target = body["candidates"][0]["id"]
        asked, relation, found = [(target, message, language)], None, [urls[target]]
    else:
        body = post("/api/identify", {"question": message, "language": language})
        query = body.get("normalized_query", message)
        if bool(body.get("clarification")) != case.get("clarification", False):
            if case["expected"] == ["ambiguous"]:  # not wrong: the citizen is asked which service
                return "asks which service", body["clarification"]
            return "clarification", body.get("clarification")
        if not all(re.search(word, query, re.IGNORECASE) for word in case.get("keep", [])):
            return "normalize", query
        if body["status"] == "multiple":
            found = [shown(n["status"], n["candidates"]) for n in body["needs"]]
            asked = [(n["candidates"][0]["id"], n["question"], "en") for n in body["needs"] if n["status"] == "matched"]
            relation = body.get("relation_question")
        else:
            found, relation = [shown(body["status"], body["candidates"])], None
            asked = [(body["candidates"][0]["id"], query, "en" if query != message else language)] if body["status"] == "matched" else []
            if asked:  # a page naming the matched procedure (a fee table) may answer instead
                reply = post("/api/guidance", {"procedure_id": asked[0][0], "question": query, "language": asked[0][2]})
                asked, found = [(reply["procedure_id"], query, asked[0][2])], [urls[reply["procedure_id"]]]
    expected = case["expected"]
    if len(found) != len(expected) or not all(e == f or (e and f and e in f) for e, f in zip(expected, found)):
        if found == ["ambiguous"] and expected[0] and any(expected[0] in urls[c["id"]] for c in body["candidates"]):
            return "asks to choose", [urls[c["id"]] for c in body["candidates"]]  # offered, not wrongly chosen
        return ("follow-up routing" if "context" in case else "identify"), found
    if bool(relation) != case.get("relation", False):
        return "identify", f"relation question {relation!r}"
    if case.get("answer", True) is None:
        return None, found

    claims = []
    for procedure_id, question, lang in asked:
        reply = post("/api/guidance", {"procedure_id": procedure_id, "question": question, "language": lang})
        claims += [{**c, "procedure_id": procedure_id} for c in reply["claims"]]
        if not reply["claims"] and case.get("answer", True) and not case.get("evidence") and len(asked) > 1:
            return "generation/verification", f"no answer for procedure {procedure_id}"
    if relation:
        reply = post("/api/relation", {"procedure_ids": [p for p, _, _ in asked], "question": relation})
        claims += reply["claims"]
    if any(owner[c["chunk_id"]] != c["procedure_id"] for c in claims):
        return "citation", "a claim cites another procedure's passage"
    if not case.get("answer", True):
        return ("unsupported", [c["text"] for c in claims]) if claims else (None, "abstained")
    evidence = case.get("evidence")
    if claims and (not evidence or any(re.search(evidence, c["quote"], re.IGNORECASE) for c in claims)):
        return None, f"{len(claims)} claims"
    # No verified claim cites the expected fact: find where it was lost.
    procedure_id, question, _ = asked[0]
    if evidence and not re.search(evidence, sources[procedure_id], re.IGNORECASE):
        return "evidence not stored", f"procedure {procedure_id} never states /{evidence}/"
    if evidence and not any(re.search(evidence, c.content, re.IGNORECASE) for c in retrieve(db, procedure_id, question)):
        return "retrieval", f"/{evidence}/ is stored but not retrieved"
    return "generation/verification", [c["text"][:70] for c in claims] or "no verified claim"


with SessionLocal() as db:
    procedures = db.query(Procedure).all()
    urls = {p.id: p.source_url for p in procedures}
    sources = {p.id: p.source_text for p in procedures}
    owner = dict(db.query(ProcedureChunk.id, ProcedureChunk.procedure_id))
    # The fixture must only expect facts the approved pages actually contain.
    for case in cases:
        target = next((p for p in procedures if case["expected"][0] and case["expected"][0] in p.source_url), None)
        if case.get("evidence") and target and not re.search(case["evidence"], target.source_text, re.IGNORECASE):
            print(f"UNVERIFIABLE (source incomplete): {case['message']}")

    results, stages, took = Counter(), Counter(), []
    for case in cases:
        start = time.time()
        stage, detail = evaluate(db, case)
        took.append(time.time() - start)
        results[case["category"], stage is None] += 1
        stages[stage or "ok"] += 1
        print(f"{'ok  ' if stage is None else 'FAIL'} [{case['category']}] {case['message'][:60]:60} "
              f"{'' if stage is None else stage + ': '}{detail} ({took[-1]:.0f}s)")

print(f"\n{stages['ok']}/{len(cases)} correct end to end")
for category in sorted({c for c, _ in results}):
    print(f"  {category}: {results[category, True]}/{results[category, True] + results[category, False]}")
print("failures by stage:", {stage: n for stage, n in stages.items() if stage != "ok"})
print(f"latency per question: median {sorted(took)[len(took) // 2]:.0f}s, max {max(took):.0f}s")
