"""Read-only test of validate_migration.py without a migration: the staging records with the reviewer's corrections
applied in memory stand for a correctly migrated database and must pass every check; each deliberate fault must be
caught. The --embeddings path uses stand-in vectors (no Ollama). Nothing is written."""
import copy, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP/PROCEDUREASSIST_HANDOFF/evidence/other/scripts")
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import validate_migration as vm

engine = create_engine(vm.DATABASE_URL.rsplit("/", 1)[0] + "/" + vm.REFERENCE)
try:
    with Session(engine) as db:
        reference, orphans = vm.load(db)
        db.rollback()
finally:
    engine.dispose()

migrated = copy.deepcopy(reference)
for url, fields in vm.REVIEWED.items():
    migrated[url].update(copy.deepcopy(fields))
stored = lambda pages: {c: v for p in pages.values() for _, c, v in p["chunks"]}
same_vectors = lambda contents, pages=migrated: [stored(pages)[c] for c in contents]

results = []
def expect(name, pages, failures_expected, embed=None, orphan_count=0):
    print(f"\n######## {name}")
    failures = vm.validate(pages, orphan_count, reference, embed)
    ok = bool(failures) == failures_expected
    results.append((name, ok, len(failures)))

expect("correct migration (corrections applied)", migrated, False, embed=same_vectors)

faults = {}
p = copy.deepcopy(migrated); p["https://www.pfrda.org.in/schemes/atal-pension-yojana-apy"]["eligibility"] = reference["https://www.pfrda.org.in/schemes/atal-pension-yojana-apy"]["eligibility"]; faults["page 40 eligibility not corrected"] = p
p = copy.deepcopy(migrated); p["https://parivahan.gov.in/en/content/fees-and-user-charges"]["department"] = "MoRTH"; faults["page 39 department differs"] = p
p = copy.deepcopy(migrated); p["https://www.epfo.gov.in/epf-scheme"]["summary"] += " Extra."; faults["re-approved page summary changed"] = p
epf = "https://www.epfo.gov.in/epf-scheme"
p = copy.deepcopy(migrated); p["https://tnesevai.tn.gov.in/Citizen/FAQ.html"] = {**copy.deepcopy(p[epf]), "id": 17}; faults["page 17 not deleted"] = p
p = copy.deepcopy(migrated); p["https://parivahan.gov.in/en/content/fees-and-user-charges"]["steps"] = ["Find your service in the table and pay the amount listed against it."]; faults["page 39 step not as decided"] = p
p = copy.deepcopy(migrated); p[epf]["text"] = p[epf]["text"].replace("Can apprentices become EPF members?\n\n", ""); faults["an FAQ question lost (text and pairs)"] = p
p = copy.deepcopy(migrated); del p["https://www.pfrda.org.in/schemes/atal-pension-yojana-apy"]; faults["a page missing"] = p
p = copy.deepcopy(migrated); i, c, v = p[epf]["chunks"][0]; p[epf]["chunks"][0] = (i, c, [float("nan")] + v[1:]); faults["a stored vector not finite"] = p
p = copy.deepcopy(migrated); p[epf]["chunks"] = p[epf]["chunks"][1:]; faults["a chunk missing"] = p
for name, pages in faults.items():
    expect(f"fault: {name}", pages, True)
expect("fault: fresh embeddings one short", migrated, True, embed=lambda contents: same_vectors(contents)[:-1])
expect("fault: an orphan chunk", migrated, True, orphan_count=1)

print("\n######## summary")
for name, ok, n in results:
    print(f"{'PASS' if ok else 'WRONG'} {name}: {n} failed check(s)")
sys.exit(0 if all(ok for _, ok, _ in results) else 1)
