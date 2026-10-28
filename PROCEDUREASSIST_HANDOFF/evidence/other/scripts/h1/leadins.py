"""Read-only: blocks in stored chunks that look like list lead-ins but are not _is_heading."""
import re, subprocess, sys
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from backend.rag import _is_heading
for db in ("procedureassist", "procedureassist_staging"):
    out = subprocess.run(["psql", "-At", "-d", db, "-c", "select id, replace(source_text, E'\\n', '\\n') from procedures order by id"],
                         capture_output=True, text=True).stdout
    seen = set()
    for line in out.splitlines():
        pid, text = line.split("|", 1)
        for b in text.split("\\n\\n"):
            low = b.lower().rstrip(" .")
            if len(b) <= 120 and not _is_heading(b) and re.search(r"follow|as below|given below|listed below|are required$|include$", low):
                if (pid, b) not in seen:
                    seen.add((pid, b)); print(db[-7:], pid, repr(b))
