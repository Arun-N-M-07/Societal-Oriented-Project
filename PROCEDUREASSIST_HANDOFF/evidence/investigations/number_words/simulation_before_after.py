"""Read-only: the H4 number-word simulation, old _numbers (copied) vs the implemented rag._numbers."""
import re, subprocess, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend import rag
NEW = rag._numbers
def OLD(text):
    values = set()
    for number in re.findall(r"\d+(?:[.,/]\d+)*", text):
        try: values.add(float(number.replace(",", "")))
        except ValueError: values.add(number)
    return values
print("== number-word + unit phrases in stored text that now give a value (both databases)")
for db in ("procedureassist_staging", "procedureassist"):
    out = subprocess.run(["psql", "-At", "-d", db, "-c", "select id, replace(source_text, E'\\n', ' ') from procedures order by id"], capture_output=True, text=True).stdout
    found = sorted({(int(l.split('|', 1)[0]), m.group(1).strip(), rag._amount(m.group(1).strip()))
                    for l in out.splitlines() for m in rag.COUNTED.finditer(l.split('|', 1)[1].lower().replace("-", " "))
                    if rag._amount(m.group(1).strip())})
    print(db, found)
print("\n== phrases: old vs new _numbers")
for t in ["completed twenty years of age", "Twenty Years", "within fourteen days", "twenty-five years", "one hundred and twenty years",
          "eighteen and forty years", "five years and three months", "two or three years", "a period of three months",
          "two copies of Form 6", "three times", "one month before", "one by one", "two options", "five pre-filed sections",
          "six fields", "Two separate OTPs", "penalty days", "and copies", "Twenty thousand rupees", "Rupees One Thousand Only for delay of each year",
          "Rs. 300.00/- each year", "30 days", "2 weeks"]:
    print(f"  {t!r:50} old {sorted(map(str, OLD(t)))!s:12} new {sorted(map(str, NEW(t)))}")
P20 = "An applicant who has completed twenty years of age will be eligible for applying for a licence to drive a transport vehicle"
P18 = "The applicant who has completed the age of eighteen years of age is eligible to apply for a driving licence to drive a motor vehicle other than a transport vehicle"
P14 = "in the case of a vehicle registered within the same State, within fourteen days of the transfer, application for the transfer of ownership of a motor vehicle shall be made by the transferee"
P3M = "the person succeeding to the possession of the vehicle may for a period of three months, use the vehicle"
CASES = [("20 digits vs twenty", "You can apply after completing 20 years of age.", P20, True),
         ("twenty vs twenty", "You can apply after completing twenty years of age.", P20, True),
         ("14 digits vs fourteen", "Apply within 14 days of the transfer.", P14, True),
         ("18 vs 20", "You can apply after completing eighteen years of age.", P20, False),
         ("20 vs 18", "You can apply for a non-transport licence after completing twenty years of age.", P18, False),
         ("thirty vs fourteen days", "Apply within thirty days of the transfer.", P14, False),
         ("six vs three months", "You may use the vehicle for six months.", P3M, False),
         ("three vs two copies", "Fill three copies of Form 6.", "Fill two copies of Form 6", False),
         ("two weeks vs fourteen days (units not converted)", "Apply within two weeks of the transfer.", P14, False),
         ("no number in claim", "Driving a transport vehicle needs a licence.", P20, True)]
print("\n== verify_claims: old vs new")
for name, text, quote, ok in CASES:
    res = []
    for impl in (OLD, NEW):
        rag._numbers = impl
        res.append("KEPT" if rag.verify_claims([{"text": text, "quote": quote, "chunk_id": 1}], {1: quote + "."}) else "REJECTED")
    rag._numbers = NEW
    print(f"  old {res[0]:8} new {res[1]:8} {'(as intended)' if (res[1] == 'KEPT') == ok else '<-- NOT AS INTENDED'}  {name}")
