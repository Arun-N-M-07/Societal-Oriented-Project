"""Read-only P0-2 screen (embeddings only; nothing written). DATABASE_URL picks the database.
Every labelled English question (w11_eval.load_cases) plus the safety set's identification cases, decided on the
whole message as procedure_search._decide does today (V0), and with candidate scope checks:
  Vg  any two-letter capitals count as names matched as written, unless they abbreviate a stored procedure or
      jurisdiction ("DL", "RC", "TN"); a name the page's own name or jurisdiction abbreviates (own=True: "IDP") is found;
  Va  as Vg, but only the two-letter country abbreviations "US" and "UK" count (longer place names are already names);
  Vb1 Va + a document the question names ("marriage certificate": rag._document_kinds) must be named on the page;
  Vb2 Va + as Vb1, but an occurrence qualified by a capitalised word ("Inter Caste Marriage Certificate") names another
      document unless the question has that word too.
Prints every question whose verdict changes, and the totals per variant."""
import json, os, re, sys
from collections import Counter
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
sys.path.insert(0, "/Users/arunnm/Projects/SOP/PROCEDUREASSIST_HANDOFF/evidence/investigations/w11")
from backend import rag, procedure_search as ps
from backend.config import IDENTIFY_MIN_SCORE
from backend.database import SessionLocal
from backend.models import Procedure
from w11_eval import load_cases, verdict

DB = os.environ.get("DATABASE_URL", "procedureassist").rsplit("/", 1)[-1]
TWO = re.compile(r"\b[A-Z]{2}\b")
PLACES = re.compile(r"\b(?:US|UK)\b")
NOUN = r"(?:certificate|licence|license|permit|card)s?"

def mentions_a(text, question, own=(), known=frozenset(), generic=False):
    sentences = re.split(r"(?<=[.?!])\s+", question.strip())
    rests = [s.partition(" ")[2] for s in sentences]
    codes = (TWO if generic else PLACES) if not question.isupper() else re.compile("$^")
    names = [n for r in rests for n in ps.NAMED_TERM.findall(r)] + [c for r in rests for c in codes.findall(r) if c not in known]
    low = text.lower()
    def found(n):
        if any(ps.abbreviates(n, o, own=True) for o in own if o):
            return True
        if len(n) == 2:
            return bool(re.search(rf"\b{n}\b", text))
        return any(re.search(rf"\b{re.escape(f)}\b", low) for f in {n.lower(), n.lower().removesuffix("s")})
    missing = sum(not found(n) for n in names)
    return missing * 2 < len(names) or not names

def kinds_named(text, qualified_ok):
    """Document kinds a page names; with qualified_ok False, an occurrence whose kind word is capitalised and follows a
    capitalised word ("Caste Marriage Certificate") is recorded as (qualifier, kind) instead."""
    plain, qualified = set(), set()
    for m in re.finditer(rf"(?:(\S+)\s+)?(\w+)(?:'s)?\s+{NOUN}\b", text.replace("’", "'"), re.I):
        before, kind = m.group(1) or "", m.group(2)
        k = kind.lower()
        if k in rag.GENERIC_KINDS:
            continue
        if not qualified_ok and kind[:1].isupper() and before[:1].isupper() and not before.endswith((".", ":", "?")):
            qualified.add((before.lower(), k))
        else:
            plain.add(k)
    for m in re.finditer(rf"\b{NOUN}\s+of\s+(\w+)", text, re.I):
        plain.add(m.group(1).lower())
    return plain, qualified

def doc_ok(page_text, question, strict):
    asked = rag._document_kinds(question)
    if not asked:
        return True
    plain, qualified = kinds_named(page_text, qualified_ok=not strict)
    qwords = re.findall(r"\w+", question.lower())
    def named(k):
        return k in plain or any(q == k and f"{w} {k}" in " ".join(qwords) for w, q in qualified)
    return all(named(k) for k in asked)

def decide(db, vector, text, variant, pages):
    ranked = ps.rank_procedures(db, vector)
    status, ids = ps.classify(ranked, min_score=IDENTIFY_MIN_SCORE)
    if acronyms := ps.ACRONYM.findall(text):
        near = [i for i, s in ranked if s >= ps.ACRONYM_MIN_SCORE]
        named = [p.id for p in pages if p.id in near and any(ps.abbreviates(a, p.name) for a in acronyms)]
        if not named and status != "matched":
            uses = lambda p: any(re.search(rf"\b{re.escape(a)}\b", p.source_text) for a in acronyms)
            named = [p.id for p in pages if uses(p)]
            named = named if len(named) == 1 and named[0] in near else []
        if len(named) == 1:
            status, ids = "matched", named
    found = {p.id: p for p in pages if p.id in ids}
    known = {a for a in ps.ACRONYM.findall(text) if any(ps.abbreviates(a, p.name) or ps.abbreviates(a, p.jurisdiction or "") for p in pages)}
    def ok(p):
        if variant == "V0":
            return ps.mentions(p.source_text, text)
        good = mentions_a(p.source_text, text, own=(p.name, p.jurisdiction), known=known, generic=variant == "Vg")
        return good and (variant in ("Va", "Vg") or doc_ok(p.source_text, text, strict=variant == "Vb2"))
    procedures = [found[i] for i in ids if ok(found[i])]
    if not procedures:
        return "no_match", []
    if status == "ambiguous" and len(procedures) == 1:
        return "ambiguous", ids
    if len(procedures) > 1 and (page := ps.named_by_the_others(text, procedures)):
        return "matched", [page.id]
    return ("matched" if len(procedures) == 1 else "ambiguous"), [p.id for p in procedures]

with SessionLocal() as db:
    pages = db.query(Procedure).all()
    by_frag = lambda f: [p.id for p in pages if f in p.source_url]
    cases = load_cases(pages)
    for i, c in enumerate(json.load(open("/Users/arunnm/Projects/SOP/fixtures/evaluation/safety.json"))["cases"]):
        if "context" in c or any(not by_frag(r) for r in c.get("requires", [])):
            continue
        e = c["expected"][0]
        cases.append((f"safety[{i}]", c["message"], "none" if e is None else "page", by_frag(e) if e else []))
    # Synthetic probes (simulation only) with two-letter capitals that are not places: SC/ST certificates are TN
    # community certificates (page 17 FAQ 7); "IT return" is an income-tax return; "OK" is a word.
    ends = lambda f: [p.id for p in pages if p.source_url.endswith(f)]
    cases += [("probe", "How do I get an SC certificate in Tamil Nadu?", "page", by_frag("tnesevai")),
              ("probe", "Which documents do I need for an ST certificate in Tamil Nadu?", "page", by_frag("tnesevai")),
              ("probe", "Is it OK to renew my driving licence early?", "page", ends("content/renewal")),
              ("probe", "How do I file my IT return online with ITR-1?", "page", by_frag("itr1"))]
    seen, uniq = set(), []
    for c in cases:
        if c[1].lower() not in seen:
            seen.add(c[1].lower()); uniq.append(c)
    vectors = rag.embed_texts([c[1] for c in uniq], query=True)
    totals = {v: Counter() for v in ("V0", "Vg", "Va", "Vb1", "Vb2")}
    print(f"### {DB}: {len(uniq)} distinct labelled questions")
    for (src, q, kind, expected), vec in zip(uniq, vectors):
        got = {v: verdict(kind, expected, *decide(db, vec, q, v, pages)) for v in totals}
        for v in totals:
            totals[v][(kind, got[v].split(" (")[0])] += 1
        if len(set(got.values())) > 1:
            print(f"  {src:20} {kind:5} | " + " | ".join(f"{v} {got[v]:20}" for v in totals) + f" | {q[:80]}")
    print("\n## totals (kind, verdict)")
    for v, c in totals.items():
        print(f"  {v}: in-scope correct {c[('page','correct')]}, wrong page {c[('page','WRONG PAGE')]}, missed {c[('page','MISSED')]}, "
              f"asks {c[('page','asks')]} | out-of-scope false match {c[('none','FALSE MATCH')]}, correct {c[('none','correct')]} | "
              f"ambiguous forced {c[('ambiguous','FORCED MATCH')]}")
