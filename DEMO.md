# ProcedureAssist demo runbook

## 1. Start

```bash
./start.sh
```

Starts PostgreSQL and Ollama, checks both models, then the backend (http://localhost:8000) and
frontend. Citizens: http://localhost:5173 · Admin: http://localhost:5173/admin.
Check readiness first: http://localhost:8000/health/ready must show `"status":"ok"`.
Stop with Ctrl+C (PostgreSQL and Ollama keep running).

## 2. Review batch (not yet approved)

Saved today: Passport (Apply/Re-issue), ITR-2, Aadhaar data update, and the eSevai FAQ
(procedure 17). Each page below was scraped and extracted by the app itself on 2026-10-20 and
nothing was saved. Three more Parivahan pages are also ready: International Driving Permit,
Change of Address in Vehicle Registration and Transfer of Vehicle Ownership.

**Fastest way to approve all 20** (with the app running; you type your admin username and password,
see each draft, and answer `y` per procedure; already-saved pages are skipped):

```bash
.venv/bin/python scripts/approve_batch.py fixtures/ingestion/demo_batch.json
```

The reviewed names and departments come from `fixtures/ingestion/demo_batch.json`. Or approve one at a
time in the admin screen: **Extract → review and correct → Approve and save**, fixing the
name/department where noted below.

| # | Official URL | Proposed name / department | Example question | Notes |
|---|---|---|---|---|
| 1 | https://ecisveep.nic.in/voters/general-voters/ | Register to Vote / Election Commission of India | I turned 18, how do I get on the voter list? | |
| 2 | https://ecisveep.nic.in/voters/how-to-vote/ | How to Vote / Election Commission of India | How do I check my name in the electoral roll? | Draft says "Electoral Commission" – correct it |
| 3 | https://ecisveep.nic.in/voters/overseas-voters/ | Overseas (NRI) Voter Registration / Election Commission of India | I live abroad, can I register as a voter? | Same correction |
| 4 | https://parivahan.gov.in/en/content/learners-license | Learner's Licence / Ministry of Road Transport and Highways (Parivahan) | How do I get a learner's licence? | Close to #5: some questions offer both |
| 5 | https://parivahan.gov.in/en/content/permanent-license | Permanent Driving Licence / MoRTH (Parivahan) | How do I get a permanent licence? | |
| 6 | https://parivahan.gov.in/en/content/renewal | Renewal of Driving Licence / MoRTH (Parivahan) | My licence expires next month, how do I renew it? | Draft name is just "Renewal"; department empty |
| 7 | https://parivahan.gov.in/en/content/duplicate-licence | Duplicate Driving Licence / MoRTH (Parivahan) | I lost my licence, how do I get a duplicate? | Department empty |
| 8 | https://parivahan.gov.in/en/content/renewal-of-rc | Renewal of Vehicle Registration Certificate / MoRTH (Parivahan) | How do I renew my RC? | |
| 9 | https://parivahan.gov.in/en/content/licensing-related-fees-charges | Driving Licence Fees and Charges / MoRTH (Parivahan) | What is the learner's licence test fee? | Fee table, not steps |
| 10 | https://www.incometax.gov.in/iec/foportal/help/how-to-link-aadhaar | Link PAN with Aadhaar / Income Tax Department | How do I link my PAN with Aadhaar? | Linking only – not PAN corrections |
| 11 | https://www.incometax.gov.in/iec/foportal/help/how-to-register-e-filing | Register on the e-Filing Portal / Income Tax Department | How do I register on the e-filing portal? | |
| 12 | https://www.incometax.gov.in/iec/foportal/help/how-to-file-itr1-form-sahaj | File ITR-1 (Sahaj) Online / Income Tax Department | How do I file ITR-1? | |
| 13 | https://www.indiapost.gov.in/insurance-services/apy | Atal Pension Yojana / India Post | Who can join Atal Pension Yojana? | |
| 14 | https://www.indiapost.gov.in/otheronlineservices/aadhaar-updation | Aadhaar Enrolment and Update at Post Offices / India Post | Can I update Aadhaar at a post office? | Overlaps with UIDAI page; tested separable |
| 15 | https://www.epfo.gov.in/epf-scheme/ | Employees' Provident Fund Scheme / EPFO | What are the EPF scheme benefits? | Scheme information, not an application |
| 16 | https://www.epfo.gov.in/pension-scheme-eps/ | Employees' Pension Scheme (EPS) / EPFO | How is my EPS pension worked out? | Close to #15 |
| 17 | https://www.epfo.gov.in/insurance-scheme-edli/ | Employees' Deposit Linked Insurance (EDLI) / EPFO | What does EDLI pay my family? | Draft name is a slogan – correct it |

Reviewer checklist for every draft: the name says what the citizen does; steps come from the
page (no invented steps); eligibility only if the page states it; source URL is the official page.

Pages checked and **not** proposed: NSP scholarship pages (forms, announcements and scheme lists, no
procedure text), NFSA ration card (state list), India Post savings schemes (multi-scheme hub), UIDAI
forms page (PDF links only), Income Tax "how to file" landing pages (mostly menu), PMAY (no readable
content), TN e-Sevai Service List (all-services hub). No scrapeable official single-service page was
found for the Community Certificate, PAN corrections or scholarships.

## 3. After approving

```bash
.venv/bin/python scripts/evaluate_needs.py fixtures/evaluation/population.json --answers
.venv/bin/python scripts/evaluate_needs.py fixtures/evaluation/demo_services.json
.venv/bin/python scripts/evaluate_needs.py
```

`population.json` has 42 labelled questions in categories A–G (single, phrasings, multiple,
background, ambiguous, relationship, unsupported); `--answers` also generates every answer and
checks each citation belongs to its own procedure. Before approval (4 procedures): 14/42.

The first runs 37 labelled demo questions; the second is the original multi-need set. Both are
read-only and need Ollama.

Measured on 2026-10-20 by ingesting all 21 pages (the 4 current + these 17, with the corrections
above) through the real Extract → Approve endpoints into the isolated test database, then rolling
back: 21 procedures, 112 chunks, no orphans or duplicates, all embeddings 1024-d; duplicate save → 409,
tampered URL or edited source text → 422. Demo set **30/37** (current database: 10/37); original set
12/14 – its "get a driving licence" case expects no match, which is only true before the Parivahan
pages exist (with them, the citizen is offered the learner's and permanent licence pages).

## 4. Demo script

| Show | Type | Expected |
|---|---|---|
| Single | My passport has expired. How do I get a new one? | Passport procedure, cited steps, official link |
| Two needs | Update my Aadhaar address and renew my passport. | One reply, two sections with their own sources |
| Two needs (after approval) | Help me file my ITR-2 and check whether I need to link PAN with Aadhaar. | ITR-2 and Link PAN sections |
| Three needs (after approval) | I need a learner's licence, an overseas voter registration, to join Atal Pension Yojana and to link PAN with Aadhaar. | Three sections, PAN link listed as "Not answered yet" with a button |
| Relationship with evidence | I want to update my Aadhaar address and file my ITR-2. Do I need Aadhaar to get my ITR-2 refund? | "How these relate" quotes the ITR-2 page's PAN–Aadhaar refund sentence |
| Relationship without evidence (after approval) | Renew my driving licence and register as a voter. Which should I do first, and can I reuse documents? | Abstains: sources do not confirm an order or reuse |
| Background context | I registered as a voter last year. Now I need a duplicate driving licence. | Duplicate licence only |
| Unsupported | How do I apply for a ration card? | "We don't have an approved procedure…" |
| Admin | /admin → Extract a page from section 2 → edit → Approve | Shows human review before anything is saved |

Each answer takes roughly 8–20 s; three needs take about 35–45 s in total.

## 5. Recovery

| Symptom | Fix |
|---|---|
| `Port 5173/8000 is already in use` | The app is already running; open http://localhost:5173, or stop the other run first |
| `/health/ready` shows `ollama: unavailable` | `ollama serve` (or open the Ollama app), then `ollama list` should show `qwen3:8b` and `qwen3-embedding:0.6b` |
| `database: unavailable` | `brew services start postgresql@16` |
| Answers say "service is unavailable" | Ollama stopped or a model is missing; restart it and press Try again on the section |
| Browser shows CORS/network errors | Use `localhost`, not `127.0.0.1` |
| First answer very slow | The model is loading; later answers take 8–20 s |

## 6. Known limitations

- Procedure 17 (eSevai FAQ) still attracts unrelated document questions (e.g. "documents to file my
  income tax return", "marriage certificate", "updating my voter details"). Retiring it is pending approval.
- "How do I change the name on my PAN card?" matches e-filing registration: no PAN-correction page is saved.
- Two-letter places such as "UK" are not checked by the name filter, so "driving licence in the UK"
  offers the Indian pages. Checking 2-letter capitals was tested and rejected: it also broke "DL renewal".
- Close pages (learner's vs permanent licence, EPF vs EPS) sometimes ask the citizen to choose.
- Relationships are shown only when one official sentence states them; most combinations abstain.
- Answers are generated one at a time (Ollama runs one generation at a time on this machine).
