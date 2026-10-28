# 06 — Source URL audit (every source, approved and staging)

## How the audit was done (23 Oct 2026)
- **Live fetch.** Every stored URL was fetched live with the app's own scraper. The result was compared paragraph by paragraph with the stored `source_text`.
- **Lost text.** For each page, the live HTML was searched for text the scraper dropped, and the HTML tags holding it were recorded (`evidence/other/scripts/lost.py`).
- **Chunks and embeddings.** Each page's stored chunks were checked against `chunk_text(source_text)`, and every stored embedding against a fresh one: all cosines were 1.0000.
- **Dry-run re-scrape.** Every URL was re-scraped with the fixed scraper, without writing (`evidence/source_audits/rescrape_dry_run_diff.json`).
- **Gap filling.** Replacement or supplementary official pages were searched for where coverage was missing. Each was verified by fetching it, not from search snippets.

Raw evidence:
- `evidence/source_audits/live_fetch_vs_stored_2026-10-23.json`: status, redirects, title, paragraphs only in the stored text, paragraphs only live, chunk IDs, embedding check;
- `evidence/source_audits/rescrape_dry_run_diff.json`;
- `evidence/audit_reports/SOURCE_AUDIT_working_notes.md`: the working table;
- `evidence/traces/`: how each page's content behaves in answers.

**Accessibility is not usefulness.** All 24 URLs return HTTP 200. Four redirect with 301 to the same path with a trailing slash: ECI 19–21 and EPFO 36–38. Nine pages nonetheless had stored text missing or polluting meaningful content.

## Summary
| Classification | Count | Pages |
|---|---|---|
| **KEEP** (no change) | 11 | 15, 21, 22, 23, 24, 25, 26, 28, 29, 30, 34 |
| **RESCRAPE** (same URL, fixed scraper, human review) | 9 | 17, 18, 19, 20, 27, 35, 36, 37, 38 |
| **REPLACE** (same official page at a cleaner URL) | 4 | 16, 31, 32, 33 → `?mobile-app=1` |
| **REMOVE** | 0 | — |
| **ADD** (new verified official source) | 2 | Parivahan fees-and-user-charges; PFRDA APY |

**"Matches live" in the table below** means that the stored text equals the live page *as the original scraper reads it*. Today's fixed scraper adds only noise to some KEEP pages:
- one "View PDF" button label on pages 22–26 and 28–30;
- the labels "Atal Pension Yojana" and "Jansuraksha Scheme" on page 34.

That is why KEEP pages are not re-scraped (`evidence/source_audits/staging_inputs/final_rescrape.json`; see `07`).

There are no homepages, navigation-only pages, menu pages or broken pages among the stored sources. Content type:
- 16 useful, informative pages;
- 8 useful but incomplete pages: 15, 17, 22, 28, 29, 30, 31, 34;
- 0 pure forms or calculators. Page 15 contains a calculator link but is a procedure page.

No page duplicates another. 18 (UIDAI) and 35 (India Post) both cover Aadhaar updates but with different content: update modes vs the fee table at post offices.

## Page by page

Columns: authority / category · scraped-content quality · chunk quality · missing information → **decision** and why.

| ID | URL | Procedure (stored name) | Authority, category | Scraped content | Chunks | Missing / known issues | Decision |
|---|---|---|---|---|---|---|---|
| 15 | https://www.passportindia.gov.in/psp/Apply | Apply for Fresh / Re-issue Ordinary Passport | MEA Passport Seva; procedure page (needs a browser render) | Matches live | 7, fine | **No fee amounts.** "Calculate the fee" opens `psp/FeeCalculator`, an interactive form with no amounts in its page text. Its banner says fees were revised from 1 Jul 2026; its only stated rule is a 10% discount on fresh applications for children up to 8 and people over 60. Document lists are only links. | **KEEP.** Fees stay a gap; abstaining is correct. |
| 16 | https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/file-itr-2-online/itr-2-UM?mobile-app=1&utm_source=chatgpt.com | Filing of ITR-2 | CBDT e-filing manual | Matches live | 18 | URL carries a `utm_source=chatgpt.com` tracking parameter | **REPLACE** with `…/itr-2-UM?mobile-app=1`: text identical |
| 17 | https://tnesevai.tn.gov.in/Citizen/FAQ.html | REV-101 Community Certificate (**misnamed**) | Tamil Nadu e-Governance Agency; FAQ page | **Lost all 18 FAQ questions** (accordion `<a>` headers in `<div>`), so 10 document lists for different certificates are unlabelled | 4 | Caused **wrong answers**: income-certificate and community-certificate questions got documents from other certificates' lists. The record's "steps" are the *edit your CAN details* answer, not how to apply for a community certificate; the page has no such procedure. | **RESCRAPE** (questions restored). The reviewer must rename it to "e-Sevai FAQ: CAN and certificate documents" (final reviewed value, `07` "Reviewed card values") and correct the steps. The community-certificate application procedure is a **gap**. |
| 18 | https://uidai.gov.in/en/updating-data-on-aadhaar | Updating Data on Aadhaar | UIDAI; informative | Assisted-update labels and FAQ answers lost; an "In this section" nav list is kept | 10 | The accepted PoA/PoI document list is a **PDF** (not supported) | **RESCRAPE.** The address-proof list is a gap. |
| 19 | https://ecisveep.nic.in/voters/general-voters | Register to Vote | ECI SVEEP; informative | Image-gallery text stored | 4 | — | **RESCRAPE** (gallery removed) |
| 20 | https://ecisveep.nic.in/voters/how-to-vote | How to Vote | ECI SVEEP; informative | Gallery text stored | 6 | One "Gallery …" block stays even after the fix. The 2024 poll dates are stale but are the official text. | **RESCRAPE** |
| 21 | https://ecisveep.nic.in/voters/overseas-voters | Overseas (NRI) Voter Registration | ECI SVEEP; informative | Matches | 5 | — | **KEEP** |
| 22 | https://parivahan.gov.in/en/content/learners-license | Learner's Licence | MoRTH Parivahan; informative but incomplete | Matches | 2 | Only licensing authorities and age rules; **no application steps or documents**. The fee is on 27. Sarathi is a transactional, state-specific portal, not a source. | **KEEP**; gap recorded |
| 23 | https://parivahan.gov.in/en/content/permanent-license | Permanent Driving Licence | MoRTH; informative | Matches | 2 | Fee "as prescribed" (on 27) | **KEEP** |
| 24 | https://parivahan.gov.in/en/content/renewal | Renewal of Driving Licence | MoRTH; informative | Matches | 1 | Rs. 30 fee for applying more than 30 days late; base fee on 27 | **KEEP** |
| 25 | https://parivahan.gov.in/en/content/duplicate-licence | Duplicate Driving Licence | MoRTH; informative (short) | Matches | 1 | **No citizen duplicate fee on any official page.** Page 27 lists only the school/establishment duplicate fee. | **KEEP**; abstaining on the citizen fee is correct |
| 26 | https://parivahan.gov.in/en/content/international-driving-permit | International Driving Permit | MoRTH; informative (short) | Matches | 1 | Fee on 27 (Rs. 1000) | **KEEP** |
| 27 | https://parivahan.gov.in/en/content/licensing-related-fees-charges | Driving Licence Fees and Charges | MoRTH; **fee schedule** | Each table cell stored as its own paragraph ("10", label, amount) | 2 | A fee was cut off from its purpose and applicant | **RESCRAPE**: one paragraph per row |
| 28 | https://parivahan.gov.in/en/content/renewal-of-rc | Renewal of Vehicle Registration Certificate | MoRTH; incomplete | Matches | 2 | Fee "as specified in Rule 81" was on no approved page | **KEEP** + supplement with the new fee page |
| 29 | https://parivahan.gov.in/en/content/address-change | Change of Address in Vehicle Registration | MoRTH; incomplete | Matches | 2 | Same Rule 81 gap | **KEEP** + supplement |
| 30 | https://parivahan.gov.in/en/content/ownership-transfer | Transfer of Vehicle Ownership | MoRTH; incomplete | Matches | 7 | Same Rule 81 gap | **KEEP** + supplement |
| 31 | https://www.incometax.gov.in/iec/foportal/help/how-to-link-aadhaar | Link PAN with Aadhaar | CBDT manual; incomplete | Two large menu blocks plus a "Company" menu; chunk 82 is pure menu (identical to 91 and 96) | 9 | **Fee amount not stated** ("Applicable amount will be pre-filled"). `incometaxindia.gov.in/tax-services/link-aadhaar` returned HTTP 403 to the scraper; the `link-aadhaar-um` manual also states no amount. | **REPLACE** with `…/how-to-link-aadhaar?mobile-app=1` (same text, no menus). The fee amount is a gap. |
| 32 | https://www.incometax.gov.in/iec/foportal/help/how-to-register-e-filing | Register on the e-Filing Portal | CBDT manual | Menu pollution (chunk 91) | 5 | — | **REPLACE** with `?mobile-app=1` |
| 33 | https://www.incometax.gov.in/iec/foportal/help/how-to-file-itr1-form-sahaj | File ITR-1 (Sahaj) Online | CBDT manual | Menu pollution (chunk 96) | 17 | — | **REPLACE** with `?mobile-app=1` |
| 34 | https://www.indiapost.gov.in/insurance-services/apy | Atal Pension Yojana | India Post; incomplete | Matches | 2 | Eligibility, where to open the account, debit frequency only; contribution chart, pension amounts and exit rules are in 8 PDFs | **KEEP** + supplement with PFRDA |
| 35 | https://www.indiapost.gov.in/otheronlineservices/aadhaar-updation | Aadhaar Enrolment and Update at Post Offices | India Post; **fee schedule** (needs a browser render) | Tab content stored twice; "*Inclusive of GST" (the condition on every fee) lost; rows split | 3 | — | **RESCRAPE** (rows joined, GST note kept) |
| 36 | https://www.epfo.gov.in/epf-scheme | Employees' Provident Fund Scheme | EPFO; informative | **"Who it covers" cards and all 10 FAQ questions lost**; bare "Yes"/"No" answers | 5 | Caused a **wrong answer** ("Apprentices can become EPF members"; the official answer is No) and an abstention on the 18–54 age rule | **RESCRAPE** |
| 37 | https://www.epfo.gov.in/pension-scheme-eps | Employees' Pension Scheme (EPS) | EPFO; informative | Coverage cards and 10 FAQ questions lost | 4 | — | **RESCRAPE** |
| 38 | https://www.epfo.gov.in/insurance-scheme-edli | Employees' Deposit Linked Insurance (EDLI) | EPFO; informative | Coverage cards and 7 FAQ questions lost | 3 | **The official page contradicts itself:** maximum ₹7 lakh vs FAQ "Rs.600,000". Both are quoted with their own source. | **RESCRAPE** |

### Added in staging (verified first-party sources)
| Staging ID | URL | Authority | What it adds | Decision |
|---|---|---|---|---|
| 39 | https://parivahan.gov.in/en/content/fees-and-user-charges | MoRTH Parivahan; **fee schedule** (Rule 81) | All registration-side fees: RC issue/renewal by vehicle class, duplicate RC, transfer, change of residence, hypothecation, fitness, delays, vehicles older than 20 years, GST note. Sub-rows carry their numbered parent row. | **ADD** as "Vehicle Registration Fees and User Charges" |
| 40 | https://www.pfrda.org.in/schemes/atal-pension-yojana-apy | PFRDA (statutory pension regulator; page title verified) | Income-tax payers are not eligible from 1 Oct 2022; ₹1,000–5,000 guaranteed pension slabs; spouse and nominee benefits; how to join (forms at banks and post offices, eAPY). India Post says "below 40", PFRDA says "maximum age is 40"; both are kept with attribution. | **ADD** alongside 34 |

Verified but **not added**:
- `npstrust.org.in/apy-eligibility` and `charges-under-apy`: NPS Trust; account opening ₹15 and annual maintenance ₹15, excluding taxes. Optional.
- `passportindia.gov.in/psp/FeeCalculator`: an interactive form with no amounts.

## Remaining source gaps (no verified first-party HTML source)
| Gap | What was tried |
|---|---|
| Passport fee amounts | Fee calculator is interactive; old `mobFeeDocument.html` returns HTTP 404; a mirror host does not resolve; fees revised 1 Jul 2026 |
| PAN–Aadhaar linking fee amount | The manual says "pre-filled"; incometaxindia.gov.in returns 403 |
| APY contribution chart | Only in PDFs; jansuraksha.gov.in unreachable (scraper and browser) |
| UIDAI accepted documents (proof of address) | PDF only |
| Citizen duplicate driving-licence fee | Not on any Parivahan page found |
| Community-certificate application steps (TN) | Only third-party guides found |
| Learner's licence application steps | Only Sarathi (transactional, state-specific) |

Never fill these gaps from bank, aggregator or news sites. If an official HTML page appears later, add it through the admin review workflow.
