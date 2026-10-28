"""Automated browser walkthrough of the citizen page (headless Chromium through Playwright; not a manual session).
It types questions as a citizen would, waits for each answer and records what the page shows, with a screenshot of
each scenario. Read-only: the page only searches and asks for answers.
    browser_walkthrough.py <frontend url> <screenshot folder>"""
import re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL, SHOTS = sys.argv[1], Path(sys.argv[2])
SHOTS.mkdir(parents=True, exist_ok=True)
failures = []

def check(ok, what):
    print(f"{'ok  ' if ok else 'FAIL'} {what}", flush=True)
    if not ok:
        failures.append(what)

def ask(page, text, label="Your situation or question"):
    page.get_by_label(label).fill(text)
    page.get_by_role("button", name="Send").click()
    # Wait until the page is idle again: no "Searching…/Loading…/Checking…" status and Send enabled.
    page.wait_for_function("""() => !document.querySelector('.thinking') &&
        !document.querySelector('button.send-button[disabled]')""", timeout=240_000)

def last_exchange(page):
    return page.locator("section.exchange").last.inner_text()

def new_chat(page):
    if page.get_by_role("button", name="New chat").count():
        page.get_by_role("button", name="New chat").click()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1100, "height": 1400})
    page.goto(URL)
    check("Find the right government procedure" in page.inner_text("body"), "the citizen page loads")

    ask(page, "How do I renew my passport?")
    text = last_exchange(page)
    check("Apply for Fresh / Re-issue Ordinary Passport" in text, "1. passport question: the procedure card is shown")
    check(page.locator("ol.citizen-steps li").count() > 0, f"1. answered with {page.locator('ol.citizen-steps li').count()} verified claims")
    page.screenshot(path=SHOTS / "1_passport.png", full_page=True)

    new_chat(page)
    ask(page, "I live abroad. How do I register to vote?")
    text = last_exchange(page)
    check("Overseas (NRI) Voter Registration" in text and page.locator("ol.citizen-steps li").count() > 0,
          f"2a. citizen abroad: the overseas card with {page.locator('ol.citizen-steps li').count()} verified claims")
    page.screenshot(path=SHOTS / "2a_overseas.png", full_page=True)

    new_chat(page)
    ask(page, "I work in Saudi Arabia. How do I register to vote?")
    text = last_exchange(page)
    heading = page.locator(".procedure-intro h2").all_inner_texts()
    print(f"     2b shows: card {heading or 'none'}; {text.splitlines()[-1][:120]!r}")
    check("Register to Vote" not in heading, "2b. citizen in a foreign country: never the general Register to Vote card")
    page.screenshot(path=SHOTS / "2b_saudi.png", full_page=True)

    new_chat(page)
    ask(page, "How do I apply for a certificate in Tamil Nadu?")
    check("Which certificate is your question about?" in page.inner_text("body"), "3. unnamed certificate: asked which one")
    page.screenshot(path=SHOTS / "3_which_certificate.png", full_page=True)

    new_chat(page)
    ask(page, "How do I get a marriage certificate?")
    text = last_exchange(page)
    check(("No approved official information answers this question" in text or "don't have an approved procedure" in text)
          and not page.locator(".procedure-intro").count(), "4. marriage certificate: no procedure card, an honest note")
    page.screenshot(path=SHOTS / "4_marriage.png", full_page=True)

    new_chat(page)
    ask(page, "How do I renew my driving licence?")
    check(page.locator(".procedure-intro").count() == 1, "5. driving licence renewal: card shown (the question names it)")
    ask(page, "What is the fee?", label="Ask about this procedure")
    text = last_exchange(page)
    check(bool(re.search(r"Rs\.?\s*200|200", text)) or "does not answer" in text, "5. follow-up on the fee: answered on the open procedure")
    page.screenshot(path=SHOTS / "5_followup_fee.png", full_page=True)

    new_chat(page)
    page.get_by_label("Language").select_option("ta")
    ask(page, "Passport renew panna enna documents venum?")
    check("Searched as:" in page.inner_text("body"), "6. Tamil-English question: searched as an English query")
    page.screenshot(path=SHOTS / "6_tamil.png", full_page=True)
    browser.close()

print(f"\n{len(failures)} failed check(s)")
sys.exit(1 if failures else 0)
