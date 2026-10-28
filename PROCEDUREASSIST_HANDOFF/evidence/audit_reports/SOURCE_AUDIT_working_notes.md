# ProcedureAssist source audit — 23 Oct 2026

Database `procedureassist`. There are 2 tables, `procedures` (24 rows) and `procedure_chunks` (122 rows). Each chunk belongs to a page through `procedure_chunks.procedure_id → procedures.id` with ON DELETE CASCADE. No other table, fixture or frontend storage refers to procedure IDs; the evaluation fixtures match pages by URL.

All 24 URLs were fetched live with the app's scraper on 23 Oct 2026. Every one returned HTTP 200. Four ECI and EPFO URLs redirect with a 301 to the same path with a trailing slash. Every chunk equals `chunk_text(source_text)`. Every embedding has cosine similarity 1.0000 with a freshly computed one, so nothing is stale. There are no orphan chunks. The only identical chunks are the incometax menu chunks 82, 91 and 96.

Classes: A = useful, informative · B = useful but incomplete · C = navigation · D = homepage · E = irrelevant/duplicate/broken · F = form/calculator.

| ID | URL | Live title / organisation | Class | Live vs stored | What it supports | Missing / defects | Recommendation |
|---|---|---|---|---|---|---|---|
| 15 | passportindia.gov.in/psp/Apply | Passport Seva (MEA), rendered by browser | B | identical | Registration, RPO choice, 9 form steps, payment and appointment, rescheduling limits, minors' photo, 90-day resubmission | No fee amounts: the page only links "Calculate the fee". Document lists are links only. | Retain. Fees are a gap (see the replacement table). |
| 16 | incometax.gov.in/…/itr-2-UM?mobile-app=1&utm_source=chatgpt.com | ITR-2 User Manual (CBDT) | A | identical | ITR-2 prerequisites, schedules, filing and e-verification steps | The URL carries a `utm_source=chatgpt.com` tracking parameter. | Replace the URL with `…/itr-2-UM?mobile-app=1`; the text is identical. |
| 17 | tnesevai.tn.gov.in/Citizen/FAQ.html | Tamil Nadu e-Sevai FAQ (TNeGA) | B, misleading record | identical, but extraction lost all 18 FAQ questions | CAN questions; document lists for 10 certificates; status checks | All questions were dropped, so the 10 document lists are unlabelled. The record is named "REV-101 Community Certificate", but its steps are the "edit your CAN details" FAQ answer. The page has no community-certificate application steps. | Re-scrape the same URL (questions restored). The reviewer must rename it and correct the steps. The community-certificate application procedure is a gap. |
| 18 | uidai.gov.in/en/updating-data-on-aadhaar | Updating Data on Aadhaar (UIDAI) | A | identical; extraction loss | Why and when to update, updatable fields, online and assisted modes, URN/EID | Assisted-mode labels (Update Client Standard/Lite) and FAQ answers are dropped; "In this section" nav and a repeated "Content Information" are kept. The accepted PoA/PoI list is a PDF (unsupported). | Re-scrape. The PoA list is a gap (PDF). |
| 19 | ecisveep.nic.in/voters/general-voters | General Voter (ECI SVEEP) | A | stored has 1 extra gallery block | Eligibility, qualifying dates, Forms 6/6A/7/8, offline enrolment, 1950 | Image-gallery text | Re-scrape (gallery removed). |
| 20 | ecisveep.nic.in/voters/how-to-vote | How to Vote (ECI SVEEP) | A | stored has 1 extra gallery block | Roll check, polling-booth steps in order, VVPAT 7 seconds, NOTA, 12 accepted IDs | Gallery text. One "Gallery …" block stays even after the fix. The 2024 poll dates are stale but are the official text. | Re-scrape. |
| 21 | ecisveep.nic.in/voters/overseas-voters | Overseas Voters (ECI SVEEP) | A | identical | NRI eligibility, Form 6A, documents, verification, Rs. 25 EPIC address change | — | Retain. |
| 22 | parivahan.gov.in/en/content/learners-license | Learner's License (MoRTH) | B | identical (+"View PDF" label) | Licensing authorities; age rules (under 18 gearless with consent, 18, 20 for transport) | No application steps or documents. The fee is on page 27. | Retain. The LL application steps are a gap; Sarathi is a transactional, state-specific site (F). |
| 23 | …/permanent-license | Permanent License (MoRTH) | A | identical | Test booking, Form 4, 30-day LL wait, test, vehicle, dispatch | Fee "as prescribed" (on 27) | Retain. |
| 24 | …/renewal | Renewal (MoRTH) | A | identical | Renewal window, 30-day/5-year rules, Rs. 30 late fee, forms | Fee "as prescribed" (on 27) | Retain. |
| 25 | …/duplicate-licence | Duplicate Licence (MoRTH) | A (short) | identical | When a duplicate is issued; Form 2; documents | No citizen duplicate fee on any approved page. Page 27 lists only the school/establishment duplicate fee. | Retain. The citizen fee is a gap, so abstaining is correct. |
| 26 | …/international-driving-permit | International Driving Permit (MoRTH) | A (short) | identical | Eligibility, Form 4A, documents | Fee on 27 (Rs. 1000) | Retain. |
| 27 | …/licensing-related-fees-charges | Licensing Related fees and Charges (MoRTH) | A | identical; rows split | 13 licence fees, including the school/establishment rows | Each table cell is a separate paragraph, so a fee is separated from its purpose and applicant (cells "10", label, amount). | Re-scrape: each row becomes one paragraph ("10 Issue or renewal of licence to a school … Rs. 10000.00/-"). |
| 28 | …/renewal-of-rc | Renewal of Registration Certificate (MoRTH) | B | identical | Form 25, 60-day window, documents | Fee "as specified in Rule 81", which no approved page contained | Retain and add the new fee page. |
| 29 | …/address-change | Change Of Address (MoRTH) | B | identical | Form 33, 14 days, documents | Rule 81 fee missing | Retain and add the new fee page. |
| 30 | …/ownership-transfer | Transfer Of Ownership (MoRTH) | B | identical | Forms 29–32, 14/45-day/3-month limits, documents | Rule 81 fee missing | Retain and add the new fee page. |
| 31 | incometax.gov.in/iec/foportal/help/how-to-link-aadhaar | Link Aadhaar User Manual (CBDT) | B | stored has 2 menu blocks | Who must link, fee payment steps (Other Receipts 500), pre/post-login linking | 2 large menu blocks plus the "Company" menu (chunk 82 is pure menu). The fee amount is not stated ("Applicable amount will be pre-filled"). | Replace the URL with `…?mobile-app=1`: the same page without site chrome, no paragraph lost. The fee amount is a gap. |
| 32 | …/how-to-register-e-filing | Register for e-Filing User Manual (CBDT) | A | stored has 2 menu blocks | Prerequisites, 8 steps, OTP and password rules | Menu pollution (chunk 91 is pure menu) | Replace the URL with `…?mobile-app=1`. |
| 33 | …/how-to-file-itr1-form-sahaj | File ITR-1 (Sahaj) User Manual (CBDT) | A | stored has 2 menu blocks | ITR-1 prerequisites and full filing steps | Menu pollution (chunk 96 is pure menu) | Replace the URL with `…?mobile-app=1`. |
| 34 | indiapost.gov.in/insurance-services/apy | Atal Pension Yojana (India Post) | B | identical | Eligibility (18–<40), where to open, debit frequency | Everything else is in 8 PDFs (contribution chart, pension amounts, exit). | Retain. The contribution and pension amounts are a gap. |
| 35 | indiapost.gov.in/otheronlineservices/aadhaar-updation | Aadhaar Updation (India Post), rendered by browser | A | identical; extraction defects | Enrolment free; 7-row Aadhaar service-charge table (₹125, ₹75, FREE) | Tab content is stored twice. "*Inclusive of GST" (the condition on every fee) is lost. Rows are split. | Re-scrape (rows joined, GST note kept). |
| 36 | epfo.gov.in/epf-scheme | EPF Scheme (EPFO) | A, extraction critically lossy | identical; extraction loss | Contribution 12%, UAN, withdrawals, FAQ answers | The "Who It Covers" cards (₹15,000, private sector, **age 18–54**, resident) and **all 10 FAQ questions** are dropped, leaving bare "Yes"/"No" answers. This produces a wrong answer today (apprentices). | Re-scrape. |
| 37 | epfo.gov.in/pension-scheme-eps | EPS (EPFO) | A, lossy | as 36 | 8.33% + 1.16%, 10-year rule, formula, life certificate | Coverage cards and all 10 FAQ questions are dropped. | Re-scrape. |
| 38 | epfo.gov.in/insurance-scheme-edli | EDLI (EPFO) | A, lossy | as 36 | 0.5% employer contribution, ₹2.5–7 lakh benefit, damages, 20-day claims | Coverage cards and 7 FAQ questions are dropped. The official page contradicts itself: ₹7 lakh maximum vs FAQ "Rs.600,000". | Re-scrape. Both statements stay quoted with their own source. |

**Counts.**

| Class | Pages |
|---|---|
| A, useful | 16 (16, 18–21, 23–27, 32, 33, 35–38) |
| B, useful but incomplete | 8 (15, 17, 22, 28–31, 34) |
| C, navigation | 0 |
| D, homepage | 0 |
| E, irrelevant, duplicate or broken | 0 |
| F, form or calculator | 0 (page 15 contains a calculator link but is mainly a procedure page) |

No page should be removed outright. Six pages need their stored extraction replaced: 17, 18, 35, 36, 37 and 38. Seven more have polluted text or a poor URL: 16, 19, 20, 27, 31, 32 and 33.

## Replacement and supplementary sources (verified by live fetch on 23 Oct 2026)

| For | URL | Verified content | Status |
|---|---|---|---|
| 16, 31, 32, 33 | same pages with `?mobile-app=1` | Identical manual text, no menus, nothing lost (paragraph diff) | verified, extractable statically |
| 28, 29, 30 | https://parivahan.gov.in/en/content/fees-and-user-charges | The Rule 81 fee table for all 16 registration-side entries: RC issue/renewal by vehicle class, duplicate RC, transfer, change of residence, hypothecation, fitness, delays, vehicles over 20 years | verified, extractable statically, 7 chunks |
| 15 fees | passportindia.gov.in/AppOnlineProject/onlineHtml/mobFeeDocument.html | HTTP 404. The portal1 mirror does not resolve. An Indian Embassy notice says fees were revised from 1 Jul 2026. | **gap**: keep abstaining |
| 31 fee amount | incometax.gov.in …/link-aadhaar-um (no amount); incometaxindia.gov.in/tax-services/link-aadhaar | The first does not state an amount; the second returns HTTP 403 to the scraper. | **gap** |
| 34 amounts | jansuraksha.gov.in | Unreachable from this machine. Search results were only from banks and third-party sites. | **gap** (no unofficial substitute) |
| 17 community-certificate procedure | official tn.gov.in pages | None found; search returned only third-party guides and a services.india.gov.in directory entry (C) | **gap** |
| 18 PoA list | uidai.gov.in supporting-documents PDF | PDF: the scraper supports HTML only | **gap** |

## Additional sources (staging only; verified on 23 Oct 2026)

| Staging ID | URL | Owner | Content | Class |
|---|---|---|---|---|
| 39 | https://parivahan.gov.in/en/content/fees-and-user-charges | MoRTH (Parivahan) | Rule 81 registration-side fee schedule, 16 items plus notes; sub-rows now carry their numbered parent row | A (fee schedule) |
| 40 | https://www.pfrda.org.in/schemes/atal-pension-yojana-apy | PFRDA (statutory regulator) | Eligibility 18–40; savings account; no income-tax payers from 1 Oct 2022; ₹1000–5000 pension slabs; spouse/nominee benefits; how to join | A, overlapping page 34 but adding new facts |
| — | https://www.passportindia.gov.in/psp/FeeCalculator | MEA | Interactive calculator only. The banner says fees were revised from 1 Jul 2026. It also states a 10% discount for minors up to 8 and seniors over 60 on fresh applications. | F: not added, so fees remain a gap |

## Remediation plan (awaiting approval; nothing has been executed on `procedureassist`)

Backup: /Users/arunnm/Projects/SOP-backups/procedureassist_2026-10-23_before_source_cleanup.dump (sha256 4e22ba1f…a42) contains the 2 tables only and no credentials.
Restore: `dropdb procedureassist && createdb procedureassist && pg_restore -d procedureassist <dump>`. The dump creates the extension it needs; confirm `CREATE EXTENSION vector` exists first.

| Step | Record (chunks) | Action | Replacement URL |
|---|---|---|---|
| 1 | new | Admin: extract, review and approve | https://parivahan.gov.in/en/content/fees-and-user-charges |
| 2 | new | Admin: extract, review and approve | https://www.pfrda.org.in/schemes/atal-pension-yojana-apy |
| 3 | 16 (chunks 15–32) | Approve the new URL, then delete 16 | …/itr-2-UM?mobile-app=1 |
| 4 | 31 (82–90), 32 (91–95), 33 (96–112) | Approve each new URL, then delete the old record | same paths + ?mobile-app=1 |
| 5 | 17 (33–36), 18 (37–46), 19 (47–50), 20 (51–56), 27 (69–70), 35 (115–117), 36 (118–122), 37 (123–126), 38 (127–129) | Same URL: delete the old record, then extract, review and approve immediately. The URL must be unique, so each page has a short gap. | same URL |
| — | 15, 21–26, 28–30, 34 | No change. Their stored text equals the live page and their chunks equal the final chunker's. | — |

Each delete cascades to that record's chunks and embeddings; no other table refers to them.
