"""Read-only screen of candidate identification fixes (embeddings and the need-extraction model only; nothing written).
DATABASE_URL picks the database.

Every labelled English question in the fixtures (w11_eval.load_cases: answers, heldout, population, demo_services,
identification, the Stage 1 audit probe; plus multi_need's single-need messages, safety without follow-ups, generalisation and identification_failures)
is decided by a copy of routes.identify_procedure -> procedure_search.identify in which each candidate fix is a flag.
With every flag off the copy gives what the route gave before these fixes; with the flags the repository now
implements (REAL=<variant>) it must give exactly what the real route gives, which is asserted for every question, so a
flag's effect is the effect of that rule alone. Need extraction (the model) and query embeddings do not depend on the
database; they are cached in one file (CACHE, outside the repository), so every variant and both databases see the
same model output.

Flags (each a general rule, none naming a page):
  F1 abbreviation  a term written inside a longer procedure name ("PAN" in "Link PAN with Aadhaar") names that
                   procedure (the abbreviation override, the named flag) only if the question also uses another word
                   of the name; the name's initials ("DL", "EPF") and its bracketed short form ("(EPS)") still do
  F2 lower uk      "uk" in any case is the country (lower-case "us" stays a word)
  F3 unnamed doc   a question whose only specific word is a document noun ("a certificate in Tamil Nadu") is asked
                   which one; F3+ also treats a few general words (from, online, government...) as generic;
                   F3s is F3+ after the search, with rag._document_kinds deciding whether a kind is named
                   ("registration certificate" is), and a choice the search offers is kept
  F4 jurisdiction  India, Indian and the states and territories are not names a page must use (covers checks states)
  F5 citizen place where the citizen lives, works, studies or travels ("I work in Dubai") is not a name a page must use
  F6 message       when the phrase and a confident whole-message match disagree: "ask" between them, or "take" the
                   whole message's page
  F7 near miss     no match, but the best page scores 0.45-0.53, passes the checks and the question uses a word of its
                   name: offer it as the one choice
  F8 acronym home  when the question uses an acronym written in some stored procedure's name ("PAN": Link PAN with
                   Aadhaar), a matched page must be named by one of its acronyms (written or initials) or by its words;
                   F8p checks a need phrase with the acronyms and words of its standalone question too
  (27 Oct, brief "Autonomous final reliability"; on top of ALLask+F8p, the code of the remaining-failures brief)
  G1 residence     of two near sibling procedures (names share a word) one of which is for citizens abroad (its name
                   says overseas/NRI/non-resident), the message decides: abroad (explicit words, or any foreign country
                   in any case) -> that one; no residence clause -> the other; a clause with an unknown place -> as now;
                   G1a only the abroad direction
  G2 choice        the standalone question confidently matches another page that is plausible for the whole message too
  G3a acronyms     a lower-case word of 3+ letters that is a stored procedure's own abbreviation is read in capitals
  G3b spell out    RC and DL are written in full for the search (the embedding) only
  G5 specific doc  the matched page's headings name the asked document only with more qualifiers ("Inter Caste
                   Marriage Certificate" for "marriage certificate"): ask whether that is the one meant
    [LIST=<variant>] screen.py [variant ...]   (LIST also prints every question that variant still gets wrong)"""
import json, os, re, sys
from collections import Counter
from types import SimpleNamespace
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
sys.path.insert(0, "/Users/arunnm/Projects/SOP/PROCEDUREASSIST_HANDOFF/evidence/investigations/w11")
from backend import rag, routes, procedure_search as ps
from backend.config import IDENTIFY_MIN_SCORE
from backend.database import SessionLocal
from backend.models import Procedure
from backend.normalize import needs_normalizing
from backend.schemas import IdentifyRequest
from w11_eval import load_cases

ROOT = "/Users/arunnm/Projects/SOP/"
DB = os.environ.get("DATABASE_URL", "procedureassist").rsplit("/", 1)[-1]
CACHE_FILE = os.environ.get("CACHE", "/private/tmp/claude-501/-Users-arunnm-Projects-SOP/bebaf14e-7bdf-4da2-8b3f-9c2a6edb540d/scratchpad/p5_screen_cache.json")
cache = json.load(open(CACHE_FILE)) if os.path.exists(CACHE_FILE) else {"needs": {}, "vectors": {}}

real_extract, real_embed = ps.extract_needs, rag.embed_texts
def cached_extract(message):
    if message not in cache["needs"]:
        cache["needs"][message] = real_extract(message)
    found = cache["needs"][message]
    return (found[0], found[1]) if found else None
def cached_embed(texts, query=False):
    missing = [t for t in texts if f"{query}|{t}" not in cache["vectors"]]
    if missing:
        for t, v in zip(missing, real_embed(missing, query=query)):
            cache["vectors"][f"{query}|{t}"] = v
    return [cache["vectors"][f"{query}|{t}"] for t in texts]
ps.extract_needs, rag.embed_texts = cached_extract, cached_embed

# ---- the copy, with flags --------------------------------------------------------------------------------------
JURISDICTION = re.compile(rf"{ps.STATE.pattern}|\bIndia(?:n|ns)?\b", re.IGNORECASE)
CONTEXT = re.compile(
    r"\b(?i:live|lives|living|lived|work|works|working|worked|stay|stays|staying|stayed|study|studies|studying|studied"
    r"|settled|reside|resides|residing|based|moved|moving|shifted|shifting|relocated|relocating|going|travelling"
    r"|traveling|travel|visiting|visit|flying)\s+(?:in|to|at|from)\s+(?:the\s+)?((?:[A-Z][\w-]*|uk)(?:\s+[A-Z][\w-]*)*)")
DOCUMENT_NOUN = re.compile(r"\b(?:certificate|licence|license|permit|card)s?\b")
MORE_GENERIC = {"from", "online", "government", "govt", "state", "office", "new", "obtain", "india", "indian"}
COUNTRIES = (
    "afghanistan|albania|algeria|andorra|angola|antigua|argentina|armenia|australia|austria|azerbaijan|bahamas|bahrain|"
    "bangladesh|barbados|belarus|belgium|belize|benin|bhutan|bolivia|bosnia|botswana|brazil|brunei|bulgaria|burkina faso|"
    "burundi|cabo verde|cape verde|cambodia|cameroon|canada|central african republic|chad|chile|china|colombia|comoros|"
    "congo|costa rica|croatia|cuba|cyprus|czech republic|czechia|denmark|djibouti|dominica|dominican republic|ecuador|"
    "egypt|el salvador|equatorial guinea|eritrea|estonia|eswatini|swaziland|ethiopia|fiji|finland|france|gabon|gambia|"
    "georgia|germany|ghana|greece|grenada|guatemala|guinea|guyana|haiti|honduras|hungary|iceland|indonesia|iran|iraq|"
    "ireland|israel|italy|ivory coast|jamaica|japan|jordan|kazakhstan|kenya|kiribati|korea|kosovo|kuwait|kyrgyzstan|laos|"
    "latvia|lebanon|lesotho|liberia|libya|liechtenstein|lithuania|luxembourg|madagascar|malawi|malaysia|maldives|mali|"
    "malta|marshall islands|mauritania|mauritius|mexico|micronesia|moldova|monaco|mongolia|montenegro|morocco|mozambique|"
    "myanmar|burma|namibia|nauru|nepal|netherlands|holland|new zealand|nicaragua|niger|nigeria|macedonia|norway|oman|"
    "pakistan|palau|palestine|panama|papua new guinea|paraguay|peru|philippines|poland|portugal|qatar|romania|russia|"
    "rwanda|saint kitts|saint lucia|saint vincent|samoa|san marino|sao tome|saudi arabia|senegal|serbia|seychelles|"
    "sierra leone|singapore|slovakia|slovenia|solomon islands|somalia|south africa|south sudan|spain|sri lanka|sudan|"
    "suriname|sweden|switzerland|syria|taiwan|tajikistan|tanzania|thailand|timor-leste|east timor|togo|tonga|trinidad|"
    "tunisia|turkey|turkiye|turkmenistan|tuvalu|uganda|ukraine|united arab emirates|uae|united kingdom|uk|britain|"
    "england|scotland|wales|united states|usa|america|uruguay|uzbekistan|vanuatu|vatican|venezuela|vietnam|yemen|zambia|"
    "zimbabwe|hong kong|macau")
ABROAD_SAID = re.compile(rf"\b(?:abroad|overseas|outside (?:india|the country)|foreign countr(?:y|ies)|another country|nris?|"
                         rf"non[- ]?residents?|expat\w*|{COUNTRIES})\b|\bUS\b", re.IGNORECASE)
FOR_ABROAD = re.compile(r"\b(?:overseas|nri|non[- ]?resident|abroad)\b", re.IGNORECASE)
RESIDE_VERBS = (r"live|lives|living|lived|work|works|working|worked|stay|stays|staying|stayed|study|studies|studying|studied"
                r"|settled|reside|resides|residing|based|moved|moving|shifted|shifting|relocated|relocating|going|travelling"
                r"|traveling|travel|visiting|visit|flying")
# A place after "live in", "work in"...: capitalised, or any word when the message has no capitals at all.
RESIDENCE = re.compile(rf"\b(?i:{RESIDE_VERBS})\s+(?i:in|to|at|from)\s+(?i:the\s+)?([A-Z][\w-]*(?:\s+[A-Z][\w-]*)*)")
RESIDENCE_LOWER = re.compile(rf"\b(?:{RESIDE_VERBS})\s+(?:in|to|at|from)\s+(?:the\s+)?(\w+(?:\s+\w+)?)")
SPECIFIC_DOC = re.compile(r"((?:[A-Z][\w'’-]*\s+)*)(\w+)\s+(?i:certificate|licence|license|permit|card)s?\b")

def residence_of(message):
    """'abroad', 'india' (no clause saying where the citizen is) or None (a clause with a place not known as either)."""
    if ABROAD_SAID.search(message):
        return "abroad"
    clause = RESIDENCE_LOWER if message == message.lower() else RESIDENCE
    places = [m.group(1) for m in clause.finditer(message)]
    if any(not (ps.STATE.fullmatch(p.lower()) or ps.STATE.match(p.lower()) or p.lower().startswith("india")) for p in places):
        return None
    return "india"

def stems_shared(a, b):
    words = lambda name: [w for w in re.findall(r"\w+", name.lower()) if w not in rag.NAME_STOP_WORDS | ps.GENERIC_WORDS]
    return any(u.startswith(w[:5]) or len(u) >= 4 and w.startswith(u[:5]) for w in words(a) for u in words(b))

def own_abbreviations(names):
    """Each stored name's own abbreviations: the prefixes (3+ letters) of its words' initials, unless the name already
    holds an abbreviation ("Link PAN with Aadhaar" gives no "LPA"), and every abbreviation written in it ("PAN", "EPS")."""
    known = set()
    for name in names:
        plain = re.sub(r"\(.*?\)", " ", name)
        written = re.findall(r"\b[A-Z][A-Z0-9-]{2,}\b", name)
        known |= set(written)
        if not re.findall(r"\b[A-Z][A-Z0-9-]+\b", plain):
            initials = "".join(w[0] for w in re.findall(r"\b[A-Z][\w'’-]*", plain) if not re.search(r"\d", w))
            known |= {initials[:n] for n in range(3, len(initials) + 1)}
    return known

def read_abbreviations(question, names):
    known = own_abbreviations(names)
    return re.sub(r"\b[a-z][a-z0-9-]{2,}\b", lambda m: m.group().upper() if m.group().upper() in known else m.group(), question)

def more_specific_document(question, page):
    """The document a heading of the page names with more qualifiers than the question gives it, when every heading
    naming that kind of document does ("Inter Caste Marriage Certificate" for "a marriage certificate")."""
    kinds = rag._document_kinds(question)
    words = set(re.findall(r"\w+", question.lower()))
    if not kinds:
        return None
    named = [(m.group(1).split(), m.group(2), m.group(0)) for b in page.source_text.split("\n\n") if rag._is_heading(b)
             for m in SPECIFIC_DOC.finditer(b) if m.group(2).lower() in kinds]
    # the qualifier run starts at the first capitalised word that is not the heading's first word ("What are ...")
    named = [(quals, kind, text) for quals, kind, text in named]
    if named and all(any(q.lower() not in words for q in quals) for quals, _, _ in named):
        return " ".join(named[0][2].split())
    return None

def blank(text, pattern, group=0):
    return pattern.sub(lambda m: m.group()[:m.start(group) - m.start()] + "_" * len(m.group(group))
                       + m.group()[m.end(group) - m.start():], text)

def mentions_v(f, source_text, question, own=()):
    if f.F4:
        question = blank(question, JURISDICTION)
    if f.F5:
        question = blank(question, CONTEXT, 1)
    rests = [s.partition(" ")[2] for s in re.split(r"(?<=[.?!])\s+", question.strip())]
    code = re.compile(r"\b(?:US|[Uu][Kk])\b") if f.F2 else re.compile(r"\b(?:US|UK)\b")  # the code before F2
    codes = [] if question.isupper() else [c for r in rests for c in code.findall(r)]
    names = [n for r in rests for n in ps.NAMED_TERM.findall(r)] + codes
    text = source_text.lower()
    def found(name):
        if any(ps.abbreviates(name, o, own=True) for o in own if o):
            return True
        if name in codes:
            return bool(re.search(rf"\b{name.upper()}\b", source_text))
        return any(re.search(rf"\b{re.escape(form)}\b", text) for form in {name.lower(), name.lower().removesuffix("s")})
    missing = sum(not found(n) for n in names)
    return missing * 2 < len(names) or not names

def other_name_word(question, name, acronym):
    rest = re.sub(rf"\b{re.escape(acronym)}\b|\(.*?\)", " ", name).lower()
    words = [w for w in re.findall(r"\w+", rest) if w not in rag.NAME_STOP_WORDS]
    used = re.findall(r"\w+", question.lower())
    return any(u.startswith(w[:5]) or len(u) >= 4 and w.startswith(u.removesuffix("e")[:5]) for w in words for u in used)

def names_by(f, acronym, name, question, own):
    """F1: a term written inside a longer name names it only with another word of the name."""
    if f.F1 and re.search(rf"\b{re.escape(acronym)}\b", name) and not re.search(rf"\({re.escape(acronym)}\)", name):
        return other_name_word(question, name, acronym)
    return ps.abbreviates(acronym, name, own=own)

def names_procedure_v(f, question, procedure):
    return (any(names_by(f, a, procedure.name, question, own=True) for a in ps.ACRONYM.findall(question))
            or rag.uses_name(question, re.sub(r"\(.*?\)", " ", procedure.name)))

def decide_v(f, db, vector, text, asked=None, message=None):
    ranked = ps.rank_procedures(db, vector)
    status, ids = ps.classify(ranked)
    if acronyms := ps.ACRONYM.findall(text):
        near = [pid for pid, score in ranked if score >= ps.ACRONYM_MIN_SCORE]
        nearby = db.query(Procedure).filter(Procedure.id.in_(near)).all()
        named = [p.id for p in nearby if any(names_by(f, a, p.name, text, own=False) for a in acronyms)]
        if not named and status != "matched":
            uses = lambda p: any(re.search(rf"\b{re.escape(a)}\b", p.source_text) for a in acronyms)
            named = [p.id for p in db.query(Procedure) if uses(p)]
            named = named if len(named) == 1 and named[0] in near else []
        if len(named) == 1:
            status, ids = "matched", named
    if f.G1 and ranked and status != "no_match":  # the module's own helpers (pure functions); this copy places the rule
        residence = ps.residence(message or text)
        near = {p.id: p for p in db.query(Procedure).filter(Procedure.id.in_([i for i, s in ranked if s >= ps.ACRONYM_MIN_SCORE]))}
        abroad = [p for p in near.values() if ps.FOR_CITIZENS_ABROAD.search(p.name)]
        if len(abroad) == 1 and residence is not None and not (f.G1 == "a" and residence != "abroad"):
            general = next((near[i] for i, _ in ranked if i in near and i != abroad[0].id and ps._same_service(near[i].name, abroad[0].name)), None)
            if general and ranked[0][0] in (abroad[0].id, general.id):
                status, ids = "matched", [abroad[0].id if residence == "abroad" else general.id]
    found = {p.id: p for p in db.query(Procedure).filter(Procedure.id.in_(ids))}
    procedures = [found[i] for i in ids
                  if mentions_v(f, found[i].source_text, text, (found[i].name, found[i].jurisdiction)) and ps.covers(found[i].jurisdiction, text)]
    asked = asked or text  # F8p: a need phrase is checked with its standalone question's acronyms too
    if f.F8 and (acronyms := ps.ACRONYM.findall(asked)) and any(
            re.search(rf"\b{re.escape(a)}\b", name) for a in acronyms for (name,) in db.query(Procedure.name)):
        procedures = [p for p in procedures if any(ps.abbreviates(a, p.name) for a in acronyms) or names_procedure_v(f, asked, p)]
    if not procedures:
        return "no_match", [], ranked
    if status == "ambiguous" and len(procedures) == 1:
        return "ambiguous", [found[i] for i in ids], ranked
    if len(procedures) > 1 and (page := ps.named_by_the_others(text, procedures)):
        return "matched", [page], ranked
    return ("matched" if len(procedures) == 1 else "ambiguous"), procedures, ranked

def near_miss(f, db, question, ranked):
    if not ranked or not ps.ACRONYM_MIN_SCORE <= ranked[0][1] < IDENTIFY_MIN_SCORE:
        return None
    page = db.get(Procedure, ranked[0][0])
    if not (mentions_v(f, page.source_text, question, (page.name, page.jurisdiction)) and ps.covers(page.jurisdiction, question)):
        return None
    words = [w for w in re.findall(r"[\w']+", page.name.lower()) if w not in rag.NAME_STOP_WORDS
             and w not in ps.GENERIC_WORDS and not DOCUMENT_NOUN.fullmatch(w)]
    used = re.findall(r"\w+", question.lower())
    if any(u.startswith(w[:5]) for w in words for u in used) or any(ps.abbreviates(a, page.name) for a in ps.ACRONYM.findall(question)):
        return page

def identify_v(f, db, question, need=None):
    texts = [*(need or []), question]
    asked = [f"{need[0]} {need[1]}" if need and f.F8 == "p" else None, None, None][:len(texts)] if need else [None]
    searched = [rag._spell_out(t.lower()) for t in texts] if f.G3b else texts
    results = [decide_v(f, db, v, t, a, question) for t, v, a in zip(texts, rag.embed_texts(searched, query=True), asked)]
    if need:
        phrase_match, question_top, message_top = (r[1][0].id if r[1] else None for r in results)
        if results[0][0] == "matched" and question_top not in (None, phrase_match) and question_top == message_top:
            if f.F6 == "take" and results[-1][0] == "matched":
                return "matched", [results[-1][1][0]]
            return "ambiguous", [results[0][1][0], results[1][1][0]]
        if f.F6 and results[0][0] == "matched" and results[-1][0] == "matched" and message_top != phrase_match:
            return ("ambiguous", [results[0][1][0], results[-1][1][0]]) if f.F6 == "ask" else ("matched", [results[-1][1][0]])
        if f.G2 and results[0][0] == "matched" and results[1][0] == "matched" and question_top != phrase_match \
                and question_top in [p.id for p in results[-1][1]]:
            return "ambiguous", [results[0][1][0], results[1][1][0]]
    final = next((r for r in results if r[0] == "matched"), next((r for r in results if r[0] != "no_match"), results[-1]))
    if f.F7 and final[0] == "no_match" and (page := near_miss(f, db, question, results[-1][2])):
        return "ambiguous", [page]
    if f.G5 and final[0] == "matched" and ps.more_specific_document(question, final[1][0]):
        return "no_match", []
    return final[:2]

def unnamed_document(question):
    """F3s: the question names a document noun but not which document, and nothing else specific."""
    lowered = blank(question.lower(), ps.STATE)
    rest = [w for w in re.findall(r"\w+", lowered) if w not in ps.GENERIC_WORDS | MORE_GENERIC
            and not DOCUMENT_NOUN.fullmatch(w) and w.strip("_")]
    of_kinds = set(re.findall(rf"{DOCUMENT_NOUN.pattern}\s+of\s+(\w+)", lowered)) - rag.GENERIC_KINDS
    return bool(DOCUMENT_NOUN.search(lowered)) and not (rag._document_kinds(question) | of_kinds) and not rest

def route_v(f, db, question):
    """(status, ids, clarification, named) as routes.identify_procedure answers an English question."""
    if f.G3a:
        question = ps.read_abbreviations(question, [n for (n,) in db.query(Procedure.name)])
    if f.F3 in (True, "+"):
        lowered = blank(question.lower(), ps.STATE)
        generic = ps.GENERIC_WORDS | (MORE_GENERIC if f.F3 == "+" else set())
        rest = [w for w in re.findall(r"\w+", lowered) if w not in generic and not DOCUMENT_NOUN.fullmatch(w) and w.strip("_")]
        if DOCUMENT_NOUN.search(lowered) and not rest:
            return "no_match", [], "which document", False
    if not ps.names_something(question):
        return "no_match", [], "which service", False
    multiple = ps.identify_needs(db, question)
    if isinstance(multiple, tuple):
        return "multiple", [], None, False
    status, procedures = identify_v(f, db, question, need=multiple)
    if f.F3 == "s" and status != "ambiguous" and unnamed_document(question):
        return "no_match", [], "which document", False
    named = status == "matched" and names_procedure_v(f, question, procedures[0])
    return status, [p.id for p in procedures], None, named

def route_real(db, question):
    r = routes.identify_procedure(IdentifyRequest(question=question), db=db)
    return r.status, [c.id for c in r.candidates], ("which service" if r.clarification else None), r.named

OFF = dict(F1=False, F2=False, F3=False, F4=False, F5=False, F6=False, F7=False, F8=False, G1=False, G2=False, G3a=False,
           G3b=False, G5=False)
VARIANTS = {
    "V0": {}, "F1": dict(F1=True), "F2": dict(F2=True), "F3": dict(F3=True), "F3+": dict(F3="+"), "F3s": dict(F3="s"),
    "F4": dict(F4=True),
    "F5": dict(F5=True), "F4F5": dict(F4=True, F5=True), "F6ask": dict(F6="ask"), "F6take": dict(F6="take"),
    "F4F5F6take": dict(F4=True, F5=True, F6="take"), "F7": dict(F7=True),
    "ALLask": dict(F1=True, F2=True, F3="s", F4=True, F5=True, F6="ask"),
    "ALLtake": dict(F1=True, F2=True, F3="s", F4=True, F5=True, F6="take"),
    "ALL+F7": dict(F1=True, F2=True, F3="s", F4=True, F5=True, F6="ask", F7=True),
    "F8": dict(F8=True), "ALLask+F8": dict(F1=True, F2=True, F3="s", F4=True, F5=True, F6="ask", F8=True),
    "ALLask+F8p": dict(F1=True, F2=True, F3="s", F4=True, F5=True, F6="ask", F8="p"),
}
CURRENT = VARIANTS["ALLask+F8p"]
VARIANTS |= {
    "G1": {**CURRENT, "G1": True}, "G1a": {**CURRENT, "G1": "a"}, "G2": {**CURRENT, "G2": True},
    "G3a": {**CURRENT, "G3a": True}, "G3b": {**CURRENT, "G3b": True}, "G5": {**CURRENT, "G5": True},
    "G123": {**CURRENT, "G1": True, "G2": True, "G3a": True},
    "G1235": {**CURRENT, "G1": True, "G2": True, "G3a": True, "G5": True},
}

def verdict(kind, expected, status, ids, clarification):
    if kind == "clarify":
        return "correct" if clarification else "FALSE MATCH" if status == "matched" else "asks" if status == "ambiguous" else "no clarification"
    if clarification:
        return "clarified"
    if kind == "none":
        return "correct" if status == "no_match" else "FALSE MATCH" if status == "matched" else "asks" if status == "ambiguous" else "multiple"
    if kind == "ambiguous":
        return "correct" if status != "matched" else "FORCED MATCH"
    if status == "matched":
        return "correct" if ids[0] in expected else "WRONG PAGE"
    if status == "ambiguous":
        return "asks (among)" if any(i in expected for i in ids) else "asks (absent)"
    return "multiple" if status == "multiple" else "MISSED"

def labelled(pages):
    def page_ids(fragment):
        ids = [p.id for p in pages if fragment in p.source_url]
        exact = [p.id for p in pages if p.source_url.split("?")[0].endswith(fragment)]
        return exact if len(ids) > 1 and exact else ids
    cases = [(src, q, kind, ids) for src, q, kind, ids in load_cases(pages)]
    for i, c in enumerate(json.load(open(ROOT + "fixtures/evaluation/multi_need.json"))["cases"]):
        if len(c["expected"]) == 1 and not c.get("relation"):  # one need, often with background
            ids = page_ids(c["expected"][0]) if c["expected"][0] else []
            if c["expected"][0] is None or ids:
                cases.append((f"multi_need[{i}]", c["message"], "page" if ids else "none", ids))
    for name in ("safety", "generalisation", "identification_failures", "residence_and_documents"):
        for i, c in enumerate(json.load(open(ROOT + f"fixtures/evaluation/{name}.json"))["cases"]):
            if "context" in c or c.get("language") == "ta" or any(not page_ids(r) for r in c.get("requires", [])):
                continue
            e = c["expected"][0]
            kind = "clarify" if c.get("clarification") else "none" if e is None else "ambiguous" if e == "ambiguous" else "page"
            ids = page_ids(e) if kind == "page" else []
            if kind != "page" or ids:
                cases.append((f"{name}[{i}]", c["message"], kind, ids))
    seen, unique = set(), []
    for c in cases:
        if needs_normalizing(c[1], "en"):  # romanised Tamil: the model normaliser runs first (tamil.json covers it)
            skipped.append(c[1])
        elif c[1].lower() not in seen:
            seen.add(c[1].lower())
            unique.append(c)
    return unique

skipped = []
REAL = os.environ.get("REAL", "V0")  # the variant the code in the repository implements (checked on every question)
with SessionLocal() as db:
    pages = db.query(Procedure).all()
    cases = labelled(pages)
    chosen = sys.argv[1:] or list(VARIANTS)
    print(f"### {DB}: {len(cases)} distinct labelled questions: {dict(Counter(c[2] for c in cases))}; "
          f"{len(skipped)} romanised Tamil skipped")
    results = {}
    for src, q, kind, expected in cases:
        real = route_real(db, q)
        copy = route_v(SimpleNamespace(**{**OFF, **VARIANTS[REAL]}), db, q)
        assert (real[0], real[1], bool(real[2]), real[3]) == (copy[0], copy[1], bool(copy[2]), copy[3]), (q, real, copy)
        results[q] = {v: route_v(SimpleNamespace(**{**OFF, **VARIANTS[v]}), db, q) for v in chosen}
    json.dump(cache, open(CACHE_FILE, "w"))
    totals = {v: Counter() for v in chosen}
    base = chosen[0]
    print(f"\n## questions whose verdict changes ({base} -> each variant)")
    for src, q, kind, expected in cases:
        got = {v: verdict(kind, expected, *results[q][v][:3]) for v in chosen}
        for v in chosen:
            totals[v][(kind, got[v].split(" (")[0])] += 1
        if len(set(got.values())) > 1:
            print(f"  {src:28} {kind:9} | " + " | ".join(f"{v}:{got[v]}" for v in chosen if v == base or got[v] != got[base])
                  + f" | {q[:80]}")
    if listed := os.environ.get("LIST"):  # every question the chosen variant still gets wrong, with what it gave
        print(f"\n## not correct under {listed}")
        for src, q, kind, expected in cases:
            status, ids, clarification, named = results[q][listed]
            if (v := verdict(kind, expected, status, ids, clarification)) != "correct":
                print(f"  {v:18} {src:28} {kind:9} expected {expected} got {status} {ids} | {q[:85]}")
    print("\n## totals")
    for v in chosen:
        c = totals[v]
        print(f"  {v:11} in scope: correct {c[('page', 'correct')]}, wrong page {c[('page', 'WRONG PAGE')]}, missed {c[('page', 'MISSED')]}, "
              f"asks {c[('page', 'asks')]}, clarified {c[('page', 'clarified')]}, multiple {c[('page', 'multiple')]} | out of scope: "
              f"correct {c[('none', 'correct')]}, false match {c[('none', 'FALSE MATCH')]}, asks {c[('none', 'asks')]}, clarified "
              f"{c[('none', 'clarified')]} | unnamed: asked which {c[('clarify', 'correct')]}, false match {c[('clarify', 'FALSE MATCH')]}, "
              f"other {c[('clarify', 'no clarification')] + c[('clarify', 'asks')]} | ambiguous: ok {c[('ambiguous', 'correct')]}, "
              f"forced {c[('ambiguous', 'FORCED MATCH')]}")
