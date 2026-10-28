# Field review of the migration's replaced, moved and added cards (27 Oct 2026, 21:30–21:45 IST)

- **Scope:** the owner's brief "Final Autonomous Execution…" §4.
- **What was checked:** every card field of the 8 replacements (18, 19, 20, 27, 35, 36, 37, 38), ID 33's assessment-year freshness, and IDs 39 and 40.
- **Against what:** the staging text. That text equals the 27 Oct re-scrape (`p7_migration/rescrape_27oct.txt`); page 33 was also re-scraped live at 21:35 and was identical (`page33_freshness_27oct.txt`).
- **Status:** these are **proposals.** Nothing is written to any database. The cards are entered by the human reviewers during the migration, which needs the owner's approval (`19`, item 7). Each correction is also in `evidence/other/scripts/validate_migration.py` `REVIEWED`, marked as proposed.
- **Rule used:** keep a field unless it is unsupported, inaccurate, ambiguous or missing a condition the page states. No outside knowledge.

## Verdicts
| Id | Page | Verdict | Change proposed |
|---|---|---|---|
| 18 | Updating Data on Aadhaar | Accurate, but steps 3–8 read as one sequence mixing two routes | Steps 3 and 5 say which route they belong to. **Online, the page offers only the address update** (myAadhaar); demographic and biometric updates are made at an Aadhaar Enrolment Centre. Its Aadhaar-app FAQ also lists Mobile Number and Address Update, so the card does not say "only" |
| 19 | Register to Vote | Accurate. Form 6 for general voters and Form 6A for NRI voters are kept distinct; the four eligibility conditions and the qualifying dates match | None. *Optional:* step 5 could add "or hand them to the Booth Level Officer of your polling area" (on the page) |
| 20 | How to Vote | The voting sequence (steps 5–10) matches the page exactly. Step 1's SMS instruction is garbled, and step 4 names 3 of the 12 accepted IDs | Step 1: the page's own example "sms ECI 12345678 to 1950" and the STD-code note. Step 4: all 12 recognised IDs, plus "Photo Voter Slip shall not be accepted as a stand-alone identification document" |
| 27 | Driving Licence Fees and Charges | Accurate: the 13 steps are the fee table's row labels word for word (no amounts) | None. *Optional:* the same single fee-table step as page 39, for consistency |
| 35 | Aadhaar Enrolment and Update at Post Offices | Accurate; states no amount; "enrolment is free" matches | None |
| 36 | Employees' Provident Fund Scheme | Thresholds (₹15,000; the para 26(6) option within 6 months), the 12% contribution and the withdrawal conditions (58 years, disability, 2 months' unemployment) match. **The summary says EPF "provides … pension, and insurance"**: the page says only that part of the employer's share goes to EPS and EDLI. **Step 4 lists "nominations" as an online service**: the page calls it a separate facility | Summary and step 4 corrected |
| 37 | Employees' Pension Scheme (EPS) | ₹15,000, 10 years, membership until 58, family pension and the life certificate all match. **Missing condition:** the FAQ says disablement pension is available without 10 years of service | Eligibility adds that sentence |
| 38 | Employees' Deposit Linked Insurance (EDLI) | **The maximum benefit conflicts on the page itself:** "Maximum benefit: ₹7 lakh (including 20% enhancement)" vs the FAQ's "Currently, the maximum assurance benefit is Rs.600,000/-". The card states ₹7 lakh as fact. Coverage is missing | Summary and step 4 state both figures as the page does; eligibility adds the coverage (automatic for EPF employees; not tea factories in Assam) |
| 33 | File ITR-1 (Sahaj) Online (move) | **The live page (21:35) still gives AY 2025–26 instructions** ("Select Assessment Year as 2025–26", "For AY 2025-26 New Tax Regime is the default"). The current year is not stated anywhere on the page, so the card must not update it silently | Summary, step 3 and step 9 attribute "2025–26" to the official guide |
| 39 | Vehicle Registration Fees and User Charges (add) | A fee table, not a payment workflow | Step decided by the owner: "Refer to the fee table to identify the applicable fee for the relevant vehicle-related service." |
| 40 | Atal Pension Yojana (PFRDA scheme details) (add) | Matches the page:<br>• age 18–40 (minimum and maximum age of joining);<br>• Indian citizens with a savings account in a bank or the Department of Posts;<br>• joining by the registration form at the bank or post office, or online through eAPY.<br>The staging card's "who are not income-tax payers" reduces the rule | Keep the existing correction: "…any citizen who is or has been an income-tax payer is not eligible to join APY" (already in `REVIEWED`) |

## Exact proposed values

### 18, steps (only 3 and 5 change)
3. Online, the myAadhaar portal offers address update: log in with your Aadhaar number and the OTP sent to your registered mobile number to place the address update request.
5. For demographic or biometric updates at an Aadhaar Enrolment Centre, place the update request with the help of an operator.

### 20, steps (only 1 and 4 change)
1. Verify your name on the Voter List by logging on to https://electoralsearch.eci.gov.in, calling the Voter Helpline 1950 (add your STD code before dialling), sending an SMS to 1950 (for example, if your EPIC is 12345678, sms ECI 12345678 to 1950), or using the Voter Helpline App.
4. Bring any one of the recognised ID cards:
   - EPIC (Voter ID card), Passport, Driving License;
   - Service Identity Cards with photograph issued to employees by Central/State Govt./PSUs/Public Limited Companies;
   - Passbooks with photograph issued by Bank/Post Office;
   - PAN Card, Smart Card issued by RGI under NPR, MNREGA Job Card;
   - Health Insurance Smart Card issued under the scheme of Ministry of Labour;
   - Pension document with photograph;
   - Official identity cards issued to MPs/MLAs/MLCs;
   - Aadhaar Card.

   The Photo Voter Slip is not accepted as a stand-alone identification document.

### 36
- **summary:** The Employees' Provident Funds Scheme, 1952, is a social security initiative in India administered by the Employees' Provident Fund Organisation (EPFO) under the Ministry of Labour and Employment, as part of the Employees' Provident Funds and Miscellaneous Provisions Act, 1952. Employees and employers each contribute 12% of basic wages plus dearness allowance to build retirement savings; part of the employer's share goes to the Employees' Pension Scheme (EPS) and the Employees' Deposit Linked Insurance (EDLI).
- **step 4:** Online services include balance checks, passbook download and account transfer between employers; a nomination facility ensures smooth fund settlement in case of death.

### 37
- **eligibility:** Employees earning up to ₹15,000/month and contributing under EPF for a minimum period are eligible. Members with minimum 10 years of eligible service are entitled to pension; others may opt for withdrawal benefits or scheme certificate. Disablement pension is available without 10 years of service.

### 38
- **summary:** The Employees' Deposit Linked Insurance (EDLI) Scheme provides life insurance benefits to EPF members in case of death during service, with a minimum benefit of ₹2.5 lakh. The page states a maximum of ₹7 lakh (including a 20% enhancement), but its FAQ says the current maximum assurance benefit is Rs. 6,00,000.
- **eligibility:** Benefits are admissible only in case of death while in service. The EDLI benefit is payable to the persons eligible to receive the EPF dues. It covers all employees of factories and establishments, with automatic membership for EPF employees; it is not applicable to tea factories (Assam).
- **step 4:** In case of death during service, the nominee receives a minimum of ₹2.5 lakh and up to ₹7 lakh, based on the employee's salary and EPF balance (the page's FAQ gives the current maximum as Rs. 6,00,000).

### 33 (summary; steps 3 and 9)
- **summary:** This procedure outlines the steps for filing ITR-1 (Sahaj) online through the e-Filing portal for eligible resident individuals. The official guide's steps are written for Assessment Year 2025–26 (unchanged on the page on 27 Oct 2026).
- **step 3:** Select the Assessment Year (the official guide shows 2025–26) and Mode of filling as Online, then click Continue.
- **step 9:** The guide states that for AY 2025-26 the New Tax Regime is the default tax regime: option 'No' is auto-selected for 'If you want to opt out of New Tax Regime'; select 'Yes' in the Personal Information section if you wish to file under the Old Tax Regime.

## What this does not change
- **Text and chunks:** no page's text or chunks change. Answers still quote the pages as published, including EDLI's two maximums (known item H7) and page 33's AY 2025–26 wording.
- **Untouched pages:** the 11 untouched pages are not reviewed or changed.
