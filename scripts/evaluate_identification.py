"""Evaluate procedure identification and suggest thresholds.

Scrapes, chunks and embeds the labelled procedures with the real Ollama
model, then scores every question exactly like rank_procedures() (best chunk
cosine similarity per procedure) without writing to any database.

    .venv/bin/python scripts/evaluate_identification.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import IDENTIFY_MARGIN, IDENTIFY_MIN_SCORE  # noqa: E402
from backend.procedure_search import MAX_CANDIDATES, classify  # noqa: E402
from backend.rag import chunk_text, embed_texts  # noqa: E402
from backend.scraper import scrape_url  # noqa: E402

data = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures/evaluation/identification.json").read_text()
)
chunks = {
    name: embed_texts(chunk_text(scrape_url(url).source_text))
    for name, url in data["procedures"].items()
}
questions = data["questions"]
query_vectors = embed_texts([q["question"] for q in questions], query=True)


def ranked(vector):
    scores = {
        name: max(sum(a * b for a, b in zip(vector, chunk)) for chunk in vectors)
        for name, vectors in chunks.items()
    }
    return sorted(scores.items(), key=lambda item: -item[1])[:MAX_CANDIDATES]


rankings = [ranked(vector) for vector in query_vectors]


def evaluate(min_score, margin):
    result = {"found": 0, "matched": 0, "wrong_match": 0, "refused": 0}
    for question, ranking in zip(questions, rankings):
        status, candidates = classify(ranking, min_score, margin)
        expected = set(question["expected"])
        if not expected:
            result["refused"] += status == "no_match"
            result["wrong_match"] += status == "matched"
            continue
        result["found"] += bool(expected & set(candidates))
        result["matched"] += status == "matched" and candidates[0] in expected
        result["wrong_match"] += status == "matched" and candidates[0] not in expected
    return result


supported = sum(bool(q["expected"]) for q in questions)
unsupported = len(questions) - supported
print("Per-question top scores:")
for question, ranking in zip(questions, rankings):
    top = ", ".join(f"{name} {score:.3f}" for name, score in ranking[:2])
    print(f"  [{question['type'][:5]}] {question['question'][:55]:55} -> {top}")

print("\nmin_score margin | offered matched wrong refused")
for min_score in (IDENTIFY_MIN_SCORE - 0.03, IDENTIFY_MIN_SCORE, IDENTIFY_MIN_SCORE + 0.03):
    for margin in (0.0, IDENTIFY_MARGIN, IDENTIFY_MARGIN + 0.02):
        r = evaluate(min_score, margin)
        marker = "  <- configured" if (min_score, margin) == (IDENTIFY_MIN_SCORE, IDENTIFY_MARGIN) else ""
        print(
            f"  {min_score:.2f}      {margin:.2f}  | {r['found']:2}/{supported} "
            f"{r['matched']:2}/{supported} {r['wrong_match']:2} {r['refused']}/{unsupported}{marker}"
        )
