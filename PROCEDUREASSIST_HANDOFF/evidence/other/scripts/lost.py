"""Text in the live HTML that clean_html drops: which tags hold it."""
import sys, re
sys.path.insert(0, "/Users/arunnm/Projects/SOP")
from collections import Counter
from bs4 import BeautifulSoup
from backend import scraper
url = sys.argv[1]; rendered = len(sys.argv) > 2
final, html = (scraper.fetch_rendered_html if rendered else scraper.fetch_static_html)(url)
open(sys.argv[3] if len(sys.argv) > 3 else "/dev/null", "w").write(html)
text = scraper.clean_html(html)
soup = BeautifulSoup(html, "html.parser")
for t in soup(["script", "style", "noscript", "svg", "nav", "header", "footer"]): t.decompose()
main = soup.select_one("main, [role='main']") or soup
missing = Counter()
for el in main.find_all(string=True):
    s = " ".join(el.split())
    if len(s) > 12 and s not in text:
        chain = "/".join(p.name + ("." + ".".join(p.get("class", [])[:2]) if p.get("class") else "") + ("[hidden]" if p.has_attr("hidden") or p.get("aria-hidden") == "true" or "display:none" in p.get("style", "").replace(" ", "") else "") for p in list(el.parents)[:4])
        print(f"{chain[:110]:110} | {s[:120]}")
