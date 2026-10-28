"""Compare the single-question flow with multi-need handling on labelled messages.

Read-only: uses the approved procedures in DATABASE_URL and the real Ollama
models (so it is not part of the unit tests).

    .venv/bin/python scripts/evaluate_needs.py [fixture.json] [--answers]

--answers also generates every matched answer (and the relationship check when
asked) and verifies that each cited chunk belongs to the answering procedure.

Tamil or Tamil-English messages are first normalized as /api/identify does; a case
can also require a clarification ("clarification"), words the normalized query must
keep ("keep", regexes) or that normalization is skipped ("bypass").
"""

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal  # noqa: E402
from backend.models import ProcedureChunk  # noqa: E402
from backend.normalize import needs_normalizing, normalize_query  # noqa: E402
from backend.procedure_search import identify, identify_needs  # noqa: E402
from backend.rag import answer_question, relate  # noqa: E402

answers = "--answers" in sys.argv
args = [arg for arg in sys.argv[1:] if arg != "--answers"]
fixture = args[0] if args else "fixtures/evaluation/multi_need.json"
cases = json.loads((Path(__file__).resolve().parents[1] / fixture).read_text())["cases"]


def label(status, procedures):
    """What a citizen is shown for one need: a source key, None, or 'ambiguous'."""
    return procedures[0].source_url if status == "matched" else None if status == "no_match" else "ambiguous"


def correct(expected, shown):
    return expected is None and shown is None or bool(
        expected and shown and re.search(re.escape(expected) + r"(?![A-Za-z0-9])", shown))  # "psp/Apply" is not "psp/ApplyPCC"


def check_answers(db, owner, asked, relation, case):
    """Generate each matched answer; returns printable facts and updates totals."""
    notes = []
    for procedure_id, question in asked:
        start = time.time()
        claims, _, _ = answer_question(db, procedure_id, question)
        stats["latency"].append(time.time() - start)
        stats["answered" if claims else "abstained"] += 1
        stats["leaked"] += sum(owner[c["chunk_id"]] != procedure_id for c in claims)
        notes.append(f"{procedure_id}:{len(claims)}c/{time.time() - start:.0f}s")
    if relation and len(asked) > 1:
        claims, _ = relate(db, [p for p, _ in asked], relation)
        stats["leaked"] += sum(c["procedure_id"] not in [p for p, _ in asked] for c in claims)
        found = bool(claims)
        if case.get("relation_evidence") is not None:
            stats["relation as labelled"] += found == case["relation_evidence"]
            stats["relation labelled"] += 1
        notes.append(f"relation:{'kept ' + str(len(claims)) if found else 'abstained'}")
    return " ".join(notes)


totals = {"single flow": 0, "multi-need": 0}
categories = Counter()
stats = Counter(latency=[], **{"normalize latency": []})
with SessionLocal() as db:
    owner = dict(db.query(ProcedureChunk.id, ProcedureChunk.procedure_id))
    for case in cases:
        expected, message = case["expected"], case["message"]
        old = [label(*identify(db, message))]
        query, clarified = message, False
        if needs_normalizing(message, "en"):
            start = time.time()
            normalized = normalize_query(message)
            stats["normalize latency"].append(time.time() - start)
            if normalized:
                query, clarified = normalized["normalized_query"], normalized["needs_clarification"]
        multiple = () if clarified else identify_needs(db, query)
        if clarified:
            new, pending, relation, asked = [None], [], None, []
        elif isinstance(multiple, tuple):
            needs, pending, relation = multiple
            new = [label(n["status"], n["candidates"]) for n in needs]
            asked = [(n["candidates"][0].id, n["question"]) for n in needs if n["status"] == "matched"]
        else:
            status, procedures = identify(db, query, need=multiple)
            new, pending, relation = [label(status, procedures)], [], None
            asked = [(procedures[0].id, query)] if status == "matched" else []
        understood = (clarified == case.get("clarification", False)
                      and all(re.search(word, query, re.IGNORECASE) for word in case.get("keep", []))
                      and (query == message or not case.get("bypass")))
        results = {
            "single flow": len(old) == len(expected) and all(map(correct, expected, old)),
            "multi-need": len(new) == len(expected) and all(map(correct, expected, new))
            and len(pending) == case.get("pending", 0) and bool(relation) == case["relation"] and understood,
        }
        for name, ok in results.items():
            totals[name] += ok
        category = case.get("category", "uncategorised")
        categories[category, results["multi-need"]] += 1
        notes = check_answers(db, owner, asked, relation, case) if answers else ""
        searched = " (clarification)" if clarified else f" as {query!r}" if query != message else ""
        print(f"{'ok ' if results['multi-need'] else 'MISS'} [{category}] {message[:66]:66}{searched} -> {new} "
              f"pending={len(pending)} relation={bool(relation)} {notes}")

if stats["normalize latency"]:
    took = sorted(stats["normalize latency"])
    print(f"normalized {len(took)} messages; latency median {took[len(took) // 2]:.1f}s, max {took[-1]:.1f}s")
for name, score in totals.items():
    print(f"{name}: {score}/{len(cases)} messages fully correct")
for category in sorted({c for c, _ in categories}):
    print(f"  {category}: {categories[category, True]}/{categories[category, True] + categories[category, False]}")
if answers:
    latency = sorted(stats.pop("latency")) or [0]
    stats.pop("normalize latency")
    print(f"answers: {stats['answered']} with verified claims, {stats['abstained']} abstained, "
          f"{stats['leaked']} cited another procedure's chunk; latency median {latency[len(latency) // 2]:.0f}s, max {latency[-1]:.0f}s")
    if stats["relation labelled"]:
        print(f"relationships as labelled: {stats['relation as labelled']}/{stats['relation labelled']}")
