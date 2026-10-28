# Candidate review under the owner's delegation (27 Oct 2026): N1, N3, N4, N8, N10

**Status (28 Oct 2026, 09:34 IST): N3, N4 and N8 are APPROVED. N1 and N10 are DEFERRED.**
- **Where the approved three are stored:** the approved database (ids 39, 40, 41) and staging (ids 41, 42, 43), through the admin routes, after the tests below.
- **Section "Outcome after testing" (end of this file)** has the evidence. The review sections below are as written on 27 Oct.

*(27 Oct status, superseded: reviewed, not approved, not saved in any database.)*
- **Who reviewed:** Claude, under the owner's delegation in the brief "Final Autonomous Execution, Procedure Approval, Database Correction & Reliability Verification" (27 Oct 2026, §5). The delegation covers these five candidates only, through the existing admin workflow.
- **When:** 10:50–11:30 IST.
- **What was done:**
  - Each page was extracted through the admin route (`admin_workflow.py extract`, 10:50–10:51).
  - Every text is byte-identical to the 26 and 27 Oct copies (`p8_candidates/rescrape_candidates.json`):

    | Candidate | Characters | SHA-256 prefix | Chunks (`chunk_text`) |
    |---|---|---|---|
    | N1 | 8,245 | `18fce806…` | 11 |
    | N3 | 3,336 | `aa80aec7…` | 5 |
    | N4 | 3,747 | `811eee71…` | 5 |
    | N8 | 1,684 | `2c1763d2…` | 2 |
    | N10 | 10,548 | `fd27e624…` | 12 |

  - Each text was then read in full and the card corrected.
- **What was not done:** retrieval testing with realistic questions, approval, and verification of the stored record (§5.4 rules 9–12). The session ended for a fresh-account handoff before them.

**Card files** (`candidate_cards/N1.json`, `N3.json`, `N4.json`, `N8.json`):
- They are the reviewed values to enter at approval.
- Each one validates against the approval schema (`ProcedureDraft`).
- Each was word-checked against its page: every content word not found is a function word ("fill", "then", "shows") or an attribution ("this page states").

## Outcome per candidate

| Candidate | URL | Outcome | Main corrections to the model's draft |
|---|---|---|---|
| N1 Instant e-PAN | `https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/instant-e-pan?mobile-app=1` | **Ready to test, then approve** | "Representative Assessess" typo fixed; "minor *as on the date of the request*" and the sections (160 of the 1961 Act, 303 of the 2025 Act) restored; 18 draft steps merged into 8 (consent and Allow were two steps; three email steps; the post-login download repeated the status steps) |
| N3 Police Clearance Certificate | `https://www.passportindia.gov.in/psp/ApplyPCC` | **Ready to test, then approve** | Six form-section headings ("Step 01: Passport Type" …) were separate steps; now one step listing the sections. Jurisdiction null → India (national Passport Seva procedure). Name adds "(PCC)", which the page itself uses. The 90-day revisit rule and the SMS-as-proof note added |
| N4 Aadhaar Enrolment | `https://uidai.gov.in/en/aadhaar-enrolment` | **Ready to test, then approve** | The draft's eligibility presented the family-entitlement (head-of-family) route as *the* requirement; now the two routes are stated (one PoI + one PoA, or HoF with Proof of Relationship). "Enrol only once" and the 180-day waiting time added. Page dated "Last Updated: 03 Jul 2026" |
| N8 Registration of Births and Deaths | `https://krishnagiri.nic.in/scheme/civil-registration-system` | **Ready to test, then approve**, with the open point below | Draft step "RCH ID is mandatory" was stated as a universal rule; now attributed to the page and tied to pregnancy registration. Form 4 / 4A distinguished. Late registration reported without resolving the page's own conflict (below) |
| N10 New ration card | `https://consumer.tn.gov.in/eligibility_ration.htm` | **DEFERRED** (not approved) | See "N10" |

## Checks per candidate (brief §5.3)

### N1 — Instant e-PAN
- **Eligibility, Aadhaar and existing PAN:** FAQ 1 and 4.
- **Exclusions:** FAQ 3: a PAN already allotted; a minor as on the date of the request; a Representative Assessee under section 160 of the Income Tax Act, 1961, or section 303 of the Income Tax Act, 2025.
- **Steps:** FAQ 5–12.
- **Status:** FAQ 13–15.
- **Download:** FAQ 15, 17 and 19.
- **Fee:** "No. The service is free of cost." (FAQ 2).
- **No duplicate steps.**
- **Not in the card:** the DigiLocker troubleshooting (FAQ 20–25). The answer engine can still quote it.
- **Pre-approval check (found in the code review, not yet tested): the single letter "e" in "e-PAN".**
  - `procedure_search.acronym_names("PAN", "Instant e-PAN", question)` reads "PAN" as a term inside the name. It then needs "another word of the name" in the question.
  - The other words are `instant` and `e`. `_same_word` compares the first 5 letters, so any question word starting with "e" ("email", "education", "e-filing") counts.
  - So a PAN question with such a word can be treated as naming Instant e-PAN: the abbreviation override in `_decide`, and `named` in `/api/identify`.
  - **Test before approving.** Use "How do I update my email on my PAN card?" and "I lost my PAN card, how do I get it again for my education loan?", on the scratch copy with N1 added.
  - If they match N1, the generic fix belongs in `acronym_names`: ignore one-letter name words, with a unit test. Treat it as a code change, with regression evidence.

### N3 — Police Clearance Certificate
- **What the card covers:** registration, login, the application link, the form sections, submission and ARN, payment and appointment, rescheduling limits, the receipt, and the visit with original documents.
- **Eligibility:** the page states none, so it is left empty rather than invented.
- **Documents:** the page only links "Document Required for PCC". The card lists none, and a documents question should abstain.
- **Police verification:** not described on this page, so not in the card.
- **Not the passport procedure:** page 15 "Apply for Fresh / Re-issue Ordinary Passport" is a separate URL.
- **Evaluation label hazard, already fixed:** `.../psp/Apply` is a prefix of `.../psp/ApplyPCC`. See "Evaluation preparation".

### N4 — Aadhaar Enrolment
- **Covered:** both enrolment approaches, the common PoI/PoA documents, the centre process, biometrics, the acknowledgement slip with the Enrolment ID, free of cost, enrol once, and the 180-day wait.
- **Date of birth documents:** the page does not mention them, so they are not in the card.
- **Separate from page 18** (updating Aadhaar, UIDAI) **and page 35** (post-office channel, India Post). The shared Aadhaar-app FAQ paragraphs are not in the card.
- **Pre-approval check: "Aadhaar Enrolment" is inside page 35's name** ("Aadhaar Enrolment and Update at Post Offices").
  - In a close call, `named_by_the_others` picks the page every other candidate names, if the question uses its whole name.
  - So a post-office question ("Is Aadhaar enrolment free at the post office?", held-out case, expected page 35) could be matched to N4 instead.
  - Test it with N4 added. A wrong match here is a reason to hold N4 until it is understood. No page-specific rule.

### N8 — Registration of Births and Deaths
- **Statewide or district: statewide content.**
  - The page is on the Krishnagiri district site, but it cites the Tamil Nadu Registration of Birth and Death Rules, 2000 and section 30 of the Registration of Births and Deaths Act, 1969.
  - It names no district office and no district-only rule. The RDO and the village or urban health nurse are statewide roles.
  - So the jurisdiction is Tamil Nadu, and the department records the publisher.
  - The page text never says "Krishnagiri", so a question naming Krishnagiri fails the name check (`mentions`). Note this when testing.
- **What the card covers:** 21 days, the place of occurrence, the free certificate, Form 4 / 4A, the RCH ID (attributed), and the name change (gazette notification and birth certificate).
- **Name inclusion:** not on the page, so not in the card.
- **Open point: the page's late-registration text conflicts with itself.**
  - It says: "After 21 days but within one year, the events can be registered with a late fee. After that but within a period of one year, the events can be registered with a written permission of the prescribed authorities along with late fee."
  - The card reports both statements without choosing between them. No outside knowledge was used: no "30 days" was added, although the Act may say so.
  - A reviewer may instead leave the permission clause out of the card. Answers quote the page either way.
- **Currency:** the page is undated. It is consistent with the cited rules; this was not verified independently (**UNVERIFIED**).

### N10 — New ration card: DEFERRED
- **The page's own text shows that its submission instructions date from about 2008:**
  - "Civil Supplies and Consumer Protection department will be launching a full online application service by September 2008";
  - SMS status "(to be activated by end 2008)";
  - a Rs 5 fee;
  - filing at the AC/TSO office or by RPAD post.
- **Current route:** a web search of official domains (27 Oct, 11:10) found that the TN PDS portal (tnpds.gov.in) offers a "new electronic card application", and e-Sevai lists PDS-501 for a new ration card.
  - Neither page could be read here. The tnpds.gov.in home page has no static text (WebFetch). The project's scraper rejected it with "Only official government websites can be used as sources", presumably after a redirect to another host (**UNVERIFIED** cause).
  - The current route therefore cannot be stated from an official page.
- **Decision:** not approved. The brief says "Do not retain outdated submission instructions simply because they appear in an older official document". The page's eligibility rules may still be valid, but its steps and fee are not current.
- **To revisit:** find a readable official page for the current smart-card application (TNPDS or e-Sevai PDS-501) and review it as a new candidate. This needs the owner, because the delegation named this candidate and its packet URL.

## Deferred by the owner (not to be added in this execution)
- N2 e-Verify;
- N5 PM Jeevan Jyoti Bima Yojana;
- N6 PM Suraksha Bima Yojana;
- N7 National Pension System;
- N9 Old Age Pension;
- N11 Unemployment Allowance for Differently Abled Persons.

The owner's reasons: overlap, weak procedural detail, metadata problems or insufficiently verified conditions (brief §5.5).

## How to finish the approvals (next session)
1. **Evaluation preparation first.** See `10_PENDING_WORK.md`, P1: the page-17 `requires`/`unless` labels and the candidate relabels. Label before running.
2. **Test on the scratch copy of the approved database** (`procedureassist_scratch`, restored 27 Oct 10:47 from `procedureassist_2026-10-27_before_candidates.dump`; equal to approved). If approved has changed since, restore a fresh copy first. For each of N1, N3, N4, N8:
   1. extract;
   2. compare the text's SHA-256 with the table above, and re-review any difference;
   3. approve the card file.

   The DATABASE_URL is derived at run time and never written down:
   ```bash
   SCRATCH=$(.venv/bin/python -c "from backend.config import DATABASE_URL as u; print(u.rsplit('/',1)[0]+'/procedureassist_scratch')")
   DATABASE_URL="$SCRATCH" .venv/bin/python PROCEDUREASSIST_HANDOFF/evidence/investigations/p9_final/admin_workflow.py extract "<url>" <scratchpad>/N1.extract.json
   DATABASE_URL="$SCRATCH" .venv/bin/python PROCEDUREASSIST_HANDOFF/evidence/investigations/p9_final/admin_workflow.py approve <scratchpad>/N1.extract.json PROCEDUREASSIST_HANDOFF/evidence/investigations/p9_final/candidate_cards/N1.json
   ```
3. **Run the evaluation sets** on the scratch copy and compare them case by case with `evidence/evaluations/p7_final/approved_*`. Include the pre-approval checks above and the §7 card list in `10`.
4. **For each candidate whose tests show no harm**, approve it the same way into `procedureassist_staging`, then into `procedureassist`. Extract again if the 2-hour token has expired.
   - The production approval is the delegated one. `admin_workflow.py` allows only these five URLs there, and never a delete.
   - Then verify the stored record, its chunks (equal to `chunk_text`) and its embeddings (1024 finite, non-zero). The `approve` command prints this.
5. **Record each outcome here** and in `21`. A candidate that fails is not approved: record why, correct it if the page supports a correction, re-test, or defer.

## Evaluation preparation already done (27 Oct, before this review was interrupted)
- `scripts/evaluate_answers.py` and `scripts/evaluate_needs.py` now match a fixture's URL fragment only when no letter or digit follows it. So `psp/Apply` (passport, page 15) no longer matches `psp/ApplyPCC` (N3).
- Checked over every fragment in every fixture: no other fragment changes the pages it matches.
- Fixtures relabelled so the labels name the same page they always meant:
  - `"passportindia"` → `"psp/Apply"`;
  - `"uidai"` → `"updating-data-on-aadhaar"` (page 18; N4 is also on uidai.gov.in).
- `evaluate_answers.py` also accepts `"unless": [fragments]`, the opposite of `requires`: the case is skipped while such a page is stored.
- **Not verified by an evaluation run yet.**

## Outcome after testing (27 Oct 22:27 – 28 Oct 09:40)

### How they were tested
1. **Labels first.** The evaluation labels for the changed collection were written before any candidate was stored (`10` P1.1–P1.2). The baseline is `evidence/evaluations/p9_baseline/`.
2. **Production copy.** N1, N3, N4 and N8 were approved into the scratch copy of the approved database only (`candidates_scratch_approval.txt`). Each text's SHA-256 was equal to this review.
3. **Comparison.** The answer sets were run and compared case by case with the approved baseline (`evidence/evaluations/p9_scratch_candidates/`).
4. **Traces.**
   - Every changed case was traced (`p9_scratch_candidates/scratch_regressions_traced.txt`).
   - The answers behind every new choice were checked (`p9_scratch_candidates_fix/choice_answers.txt`).
   - 12 adversarial questions were asked (`p9_scratch_candidates_fix/adversarial_probes.txt`).
5. **Card safety** for the owner's topic list: `p9_scratch_candidates/scratch_card_safety.txt`.

### What the tests found

| Candidate | Effect on the production copy | Decision |
|---|---|---|
| **N4 Aadhaar Enrolment** | Enrolment questions are named and answered (4 claims). Post-office questions stay on page 35, and Aadhaar updates stay on page 18. **No regression** in any set | **APPROVED** |
| **N8 Registration of Births and Deaths** | Birth and death certificate questions now get this card with correct claims (21 days; late fee; the RDO order after a year). The approved database today answers "birth certificate in Tamil Nadu" with page 17's CAN steps. **Side effect:** 7 Tamil Nadu certificate or registration questions (marriage registration and fee, widow, nativity, property registration) are identified as N8. **All abstain and show no card**, so the citizen sees "No approved official information answers this question yet…". Re-checked with 5 adversarial phrasings: all abstain. A claim naming another document is also blocked by the document-kind rule. "Which form is needed to register a death that happened at home?" scores 0.518, below the threshold: no match | **APPROVED.** The false identifications are reported as such in the evaluations |
| **N3 Police Clearance Certificate** | PCC questions are answered (7 claims; "PCC for a job abroad" matches too). **Side effects:** "What is the fee for a passport?" and "…passport fee for 36 pages?" now ask passport vs PCC (scores tie at 0.582); both options abstain, since no fee is stored. "Do I need police verification for a passport?" matches PCC and abstains. **Lower-case "how do i get an idp" loses its match:** the PCC page moves the IDP page out of the top 3 pages that the abbreviation rule looks at. The result is a no match, which is safe; upper-case "IDP" still works | **APPROVED.** The top-3 limit is recorded in `10` (P3) as a general limitation |
| **N1 Instant e-PAN** | Its own questions are answered ("How can I get a PAN instantly using my Aadhaar?": 8 claims). **A misleading answer path:** "I lost my PAN card. How do I get a duplicate?" (and the standalone "…duplicate PAN card?") now asks Register on the e-Filing Portal vs Instant e-PAN. If the citizen picks Instant e-PAN, the verified answer says "To get a duplicate PAN card, you can apply for an Instant e-PAN if you do not already have a PAN…", but the page says a person who already has a PAN is **not eligible**. Verification and the meaning check both let it through | **DEFERRED** (below) |
| N10 New ration card | Not tested: deferred on 27 Oct (outdated 2008 submission route) | **DEFERRED** |

### A code bug found by N1 and fixed in general
- **The bug:** `procedure_search.acronym_names` counted the one-letter piece "e" of "e-PAN" as "another word of the name". So any question with an "e-…" word (for example "e-filing") named Instant e-PAN.
  - On the production copy, "How do I register on the income tax e-filing portal with my PAN?" was sent to Instant e-PAN with a card. It belongs to "Register on the e-Filing Portal".
- **The fix:** one line. One-letter pieces of a name are not words of it. A test asserts it, and it failed before the fix (mutation check).
- **Effect** (scratch re-run, `p9_scratch_candidates_fix/`): exactly that case changed back to correct, out of 300 labelled cases. Backend tests: 252 OK.
- **Kept although N1 is deferred:** it protects any future "e-…" page, and it changes nothing else.

### Why N1 is deferred, and what would let it be approved
- **The misleading answer is generated by the system, not by the card.**
  - Identification: a close call between two pages is cut by the name filter to one page, and the "a close call stays a choice" rule then offers both, including the page the filter rejected.
  - Then the answer model frames e-PAN as a duplicate route, and the meaning check accepts it.
- **No card correction can prevent this,** and adding N1 creates the path. The owner's rules forbid approving with an unsupported claim.
- **Before N1 can be approved,** one of the following needs a general change with its own measurement:
  - the close-call rule offers no page that the name filter rejected;
  - a claim saying it is for a "duplicate", "renewal" or "test" must come from a passage saying so. This extends the fee-service rule `_services` beyond fee claims.

  Either needs the full screen and the answer sets.
- **The card in `candidate_cards/N1.json` stays valid** for that time.
