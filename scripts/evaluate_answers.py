"""End-to-end answer quality on labelled questions, through the real API routes.

Read-only: uses the approved procedures in DATABASE_URL and the real Ollama
models. Each question follows the citizen page's own calls (identify, then
guidance, or relation for several needs; a follow-up goes to the open
procedure first and is searched again only if that page cannot answer, moving
to the page found only when that page answers). As on the citizen page, the card
of a procedure the citizen did not name is shown only with an answer from it.

A failed case is put down to the first stage that went wrong: normalize,
identify, follow-up routing, retrieval (stored but not retrieved), missed answer
(retrieved but no verified claim), incomplete (an answer without the expected
fact, or whose own text leaves out what "claim" requires), unsupported (answered
although the page does not state it), citation (a claim cites a passage of
another page), evidence not stored (the case cannot be judged), or a
clarification: asks to choose / asks which service. Clarifications are counted
as such, never as correct answers. A claim matching the case's "forbidden"
pattern, or a matched procedure whose card matches its "card" pattern, is
incorrect or misleading. A case is skipped when its "requires" pages are not stored, or an "unless" page is.
Identification is also counted on its own: a confident wrong page is reported
apart from a miss or a question back.

    .venv/bin/python scripts/evaluate_answers.py [fixture.json] [--claims]

--claims prints every final claim with its quote.
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

args = [arg for arg in sys.argv[1:] if arg != "--claims"]
fixture = args[0] if args else "fixtures/evaluation/answers.json"
cases = json.loads((Path(__file__).resolve().parents[1] / fixture).read_text())["cases"]
client = TestClient(app)


def post(path, body):
    response = client.post(path, json=body)
    response.raise_for_status()
    return response.json()


def at(fragment, url):
    """The page a case names: the fragment, not followed by a letter or digit ("psp/Apply" is not "psp/ApplyPCC")."""
    return bool(re.search(re.escape(fragment) + r"(?![A-Za-z0-9])", url))


def shown(status, candidates):
    return urls[candidates[0]["id"]] if status == "matched" else None if status == "no_match" else "ambiguous"


def guidance(procedure_id, question, language):
    """The reply and its claims; a claim from a related page carries that page's id."""
    reply = post("/api/guidance", {"procedure_id": procedure_id, "question": question, "language": language})
    return reply, [{**c, "procedure_id": c.get("procedure_id", procedure_id)} for c in reply["claims"]]


def evaluate(db, case):
    """(failed stage or None, printable detail, reply flagged partial)."""
    message, language = case["message"], case.get("language", "en")
    claims, partial, relation, body, shown_id = None, False, None, {}, None
    if "context" in case:  # as the citizen page does: a procedure the follow-up names, else the open page, then a match
        target = next(p for p in procedures if at(case["context"], p.source_url)).id
        body = post("/api/identify", {"question": message, "language": language})
        other = body["candidates"][0]["id"] if body["status"] == "matched" and body["candidates"][0]["id"] != target else None
        if other and body.get("named"):
            target = other
        reply, claims = guidance(target, message, language)
        if reply["insufficient_evidence"] and other and target != other:
            second, second_claims = guidance(other, message, language)
            if not second["insufficient_evidence"]:  # else the open page and its reply stay
                target, reply, claims = other, second, second_claims
        found, partial, shown_id = [urls[target]] + [urls[c["procedure_id"]] for c in claims], reply.get("partial", False), target
    else:
        body = post("/api/identify", {"question": message, "language": language})
        query = body.get("normalized_query", message)
        if bool(body.get("clarification")) != case.get("clarification", False):
            if case["expected"] == ["ambiguous"]:  # the citizen is asked which service
                return "asks which service", body["clarification"], False
            return "clarification", body.get("clarification"), False
        if not all(re.search(word, query, re.IGNORECASE) for word in case.get("keep", [])):
            return "normalize", query, False
        if body["status"] == "multiple":
            found = [shown(n["status"], n["candidates"]) for n in body["needs"]]
            relation = body.get("relation_question")
            if case.get("answer", True) is not None:
                claims = []
                for need in body["needs"]:
                    if need["status"] == "matched":
                        reply, need_claims = guidance(need["candidates"][0]["id"], need["question"], "en")
                        claims += need_claims
                        if not need_claims and not case.get("evidence"):
                            return "generation/verification", f"no answer for {need['phrase']!r}", False
        else:
            found = [shown(body["status"], body["candidates"])]
            shown_id = body["candidates"][0]["id"] if body["status"] == "matched" else None
            if body["status"] == "matched" and case.get("answer", True) is not None:
                reply, claims = guidance(body["candidates"][0]["id"], query, "en" if query != message else language)
                partial = reply.get("partial", False)
                # The answer may come from a related page that names this procedure (a fee table).
                found += [urls[c["procedure_id"]] for c in claims]
                if not claims and not body.get("named"):
                    shown_id = None  # no card: the citizen is told no approved procedure matches
    expected = case["expected"]
    matches = lambda e, f: e == f or bool(e and f and at(e, f))
    if len(expected) == 1 and ("context" in case or body.get("status") != "multiple"):  # the matched page or a related page answering
        ok = any(matches(expected[0], f) for f in found)
    else:
        ok = len(found) == len(expected) and all(map(matches, expected, found))
    case["_claims"] = claims
    if not ok:
        if found == ["ambiguous"] and expected[0] and any(at(expected[0], urls[c["id"]]) for c in body["candidates"]):
            return "asks to choose", [urls[c["id"]] for c in body["candidates"]], False
        return ("follow-up routing" if "context" in case else "identify"), found, False
    if bool(relation) != case.get("relation", False):
        return "identify", f"relation question {relation!r}", False
    # A misleading card is reported after the claims, so it never hides a wrong answer shown under it.
    card = bool(case.get("card") and shown_id and re.search(case["card"], cards[shown_id], re.IGNORECASE))
    if claims is None:
        return ("misleading card", cards[shown_id][:90], partial) if card else (None, found, False)
    if relation:
        claims += post("/api/relation", {"procedure_ids": [n["candidates"][0]["id"] for n in body["needs"]
                                                           if n["status"] == "matched"], "question": relation})["claims"]
    if any(owner[c["chunk_id"]] != c["procedure_id"] for c in claims):
        return "citation", "a claim cites a passage from a page other than its own", partial
    if case.get("forbidden") and (bad := [c["text"] for c in claims if re.search(case["forbidden"], c["text"], re.IGNORECASE)]):
        return "forbidden claim", bad + (["(and a misleading card)"] if card else []), partial
    if card:
        return "misleading card", cards[shown_id][:90], partial
    if not case.get("answer", True):
        return ("unsupported", [c["text"] for c in claims], partial) if claims else (None, "abstained", partial)
    evidence, claim = case.get("evidence"), case.get("claim")
    if claims and (not evidence or any(re.search(evidence, c["quote"], re.IGNORECASE) for c in claims)):
        if claim and not any(re.search(claim, c["text"], re.IGNORECASE) for c in claims):
            return "incomplete", [c["text"][:90] for c in claims], partial
        return None, f"{len(claims)} claims", partial
    # No verified claim cites the expected fact: find where it was lost.
    pages = {c["procedure_id"] for c in claims} or {next(p.id for p in procedures if at(expected[0], p.source_url))}
    if evidence and not any(re.search(evidence, sources[p], re.IGNORECASE) for p in pages):
        return "evidence not stored", f"the answering page never states /{evidence}/", partial
    question = case["message"] if "context" in case else body.get("normalized_query", case["message"])
    if evidence and not any(re.search(evidence, c.content, re.IGNORECASE) for p in pages for c in retrieve(db, p, question)):
        return "retrieval", f"/{evidence}/ is stored but not retrieved", partial
    return ("incomplete" if claims else "missed answer"), [c["text"][:70] for c in claims] or "no verified claim", partial


# Each failure stage, and each kind of success, as one of the reported outcomes.
OUTCOMES = {"asks which service": "clarification", "asks to choose": "clarification",
            "unsupported": "incorrect or misleading", "citation": "incorrect or misleading", "clarification": "incorrect or misleading",
            "forbidden claim": "incorrect or misleading", "misleading card": "incorrect or misleading",
            "normalize": "retrieval failure", "identify": "retrieval failure", "follow-up routing": "retrieval failure",
            "retrieval": "retrieval failure", "incomplete": "incomplete", "missed answer": "missed answer",
            "generation/verification": "missed answer", "evidence not stored": "cannot be judged (source incomplete)"}


def outcome(case, stage, partial):
    if stage:
        return OUTCOMES[stage]
    if case.get("clarification") or case["expected"] == ["ambiguous"]:
        return "clarification (expected)"
    if case.get("answer", True) is False or case["expected"] == [None]:
        return "appropriate abstention or no match"
    return "correct (partial, flagged)" if partial else "correct"


def identified(case, stage, detail):
    """Identification on its own: a confident wrong page (a false match) is worse than a miss or a question back."""
    if stage in ("identify", "follow-up routing") and isinstance(detail, list):
        wrong = any(f not in (None, "ambiguous") and not (e and at(e, f)) for e, f in zip(case["expected"], detail))
        return "confident wrong page" if wrong else "missed (no match)" if None in detail else "asked (expected page absent)"
    return {"asks which service": "asked", "asks to choose": "asked", "clarification": "unexpected clarification",
            "normalize": "normalization failure", "identify": "wrong relation question"}.get(stage, "correct")


with SessionLocal() as db:
    procedures = db.query(Procedure).all()
    urls = {p.id: p.source_url for p in procedures}
    sources = {p.id: p.source_text for p in procedures}
    cards = {p.id: " ".join([p.name, p.summary, json.dumps(p.structured_data, ensure_ascii=False)]) for p in procedures}
    owner = dict(db.query(ProcedureChunk.id, ProcedureChunk.procedure_id))
    # The fixture must only expect facts the approved pages actually contain.
    for case in cases:
        target = next((p for p in procedures if case["expected"][0] and at(case["expected"][0], p.source_url)), None)
        if case.get("evidence") and target and not re.search(case["evidence"], target.source_text, re.IGNORECASE):
            print(f"UNVERIFIABLE (source incomplete): {case['message']}")

    results, stages, outcomes, idents, took, skipped = Counter(), Counter(), Counter(), Counter(), [], 0
    for case in cases:
        stored = lambda fragment: any(at(fragment, url) for url in urls.values())
        if not all(map(stored, case.get("requires", []))) or any(map(stored, case.get("unless", []))):
            skipped += 1
            print(f"SKIP [{case['category']}] {case['message'][:60]:60} needs {case.get('requires', [])} stored, "
                  f"{case.get('unless', [])} not stored")
            continue
        start = time.time()
        stage, detail, partial = evaluate(db, case)
        took.append(time.time() - start)
        results[case["category"], stage is None] += 1
        stages[stage or "ok"] += 1
        outcomes[outcome(case, stage, partial)] += 1
        idents[identified(case, stage, detail)] += 1
        print(f"{'ok  ' if stage is None else 'FAIL'} [{case['category']}] {case['message'][:60]:60} "
              f"{'' if stage is None else stage + ': '}{detail}{' (partial)' if partial else ''} ({took[-1]:.0f}s)")
        if "--claims" in sys.argv:
            for claim in case.get("_claims") or []:
                print("       claim", json.dumps({k: claim[k] for k in ("procedure_id", "chunk_id", "text", "quote")}, ensure_ascii=False))

print(f"\n{stages['ok']}/{sum(stages.values())} as expected end to end{f' ({skipped} skipped)' if skipped else ''}")
for category in sorted({c for c, _ in results}):
    print(f"  {category}: {results[category, True]}/{results[category, True] + results[category, False]}")
print("outcomes:", dict(outcomes.most_common()))
print("failures by stage:", {stage: n for stage, n in stages.items() if stage != "ok"})
print("identification:", dict(idents.most_common()))
print(f"latency per question: median {sorted(took)[len(took) // 2]:.0f}s, max {max(took):.0f}s")
