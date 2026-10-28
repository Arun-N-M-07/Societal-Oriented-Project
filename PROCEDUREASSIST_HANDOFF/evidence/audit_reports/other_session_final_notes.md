# Final report notes (session db3bcd4a), 23 Oct 2026 ~22:55 IST

## Runs: frozen code hashes in frozen_inputs.txt; approved DB 24/122; staging 26/140 (procs 6154bf02…, chunks 93000b69…)

| Code | Data | 80-question file | 80 score | held-out file | held-out score |
|---|---|---|---|---|---|
| existing (session-start verify_claims) | approved | base80.txt | 73/80 | baseheld.txt | 23/27 |
| updated | approved | code80.txt | 73/80 (same failures) | codeheld.txt | 23/27 |
| existing (run_eval.py old) | staging | oldstage80.txt | 71/80 | oldstageheld.txt | 22/27 |
| updated | staging | stage80.txt | 71/80 | stageheld.txt | 23/27 |

- Incorrect or misleading = 0 in every run.
- 80-question outcomes, approved: 48 correct, 15 partial, 8 abstain, 2 expected clarification, 4 unnecessary clarification, 2 missed, 1 retrieval failure.
- 80-question outcomes, staging: 51 correct, 10 partial, 8 abstain, 2 expected clarification, 7 unnecessary clarification, 1 missed, 1 retrieval failure.
- Staging fixed: Aadhaar mixed-language address proof; EPS central-government contribution; held-out appeal fee (row-joined fee table).
- Staging new clarifications:
  - IDP fee: 26 vs 27 (0.686 vs 0.674)
  - APY eligibility: 40 vs 34
  - Romanized renewal fee
  - "I just turned 18": 19 vs 20
- Held-out new miss: Tamil voter helpline. The 1950 chunk is retrieved but the model abstains (generation).
- Identification sets, approved → staging: multi_need 11→11, population 34→32, demo_services 30→29, tamil 29→30.

## Traces: attr_main_final.txt / attr_staging_final.txt

- Wrong answers on the approved DB, all caused by scraping and all fixed or made safe on staging:
  - EPF apprentices: "can become members" (official answer is No).
  - Tamil Nadu income-certificate documents: an item from another certificate's list.
  - Tamil Nadu community-certificate documents: Salary Certificate, PAN, Encumbrance Certificate and others from other lists.
- Staging abstentions that are generation failures:
  - Tamil Nadu community documents (the correct chunk 509 is ranked top).
  - Transport-vehicle age ("The applicant" vs "An applicant"; verbatim check correctly rejects it).
  - Voter helpline.
- EDLI: the official page contradicts itself (₹7 lakh vs FAQ Rs. 6,00,000).

## Live checks on the restarted backend (:8000, final code, approved DB)

- 24 procedures. Authentication 401 for no session, forged cookie and wrong password; empty question 422.
- School duplicate fee: Rs. 5,000. Citizen duplicate fee: abstains.
- Grace period: Rs. 300 plus Rs. 1,000 a year. Passport fee: abstains. VVPAT: 7 seconds.
- Apprentice: still wrong on approved data; only the re-scrape fixes it.
- Browser: the grace-period question gave a clarification, then an abstention after choosing the fee page (generation variance).

## Tests

- Backend: 199 OK (`discover -s tests`).
- Frontend: 61 OK; tsc with unused checks OK; build OK.
- The `tests.test_rag` direct-import failure predates this session (HEAD).

## Not built (proposed)

- When an identification tie is between a service page and a fee page that names that service, prefer the service page; the existing naming-page completion supplies the fee.
- Remediation plan, backup and restore steps: end of SOURCE_AUDIT.md.
