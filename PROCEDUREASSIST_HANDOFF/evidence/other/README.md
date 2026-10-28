# evidence/ index

| Folder | Contents |
|---|---|
| `evaluations/eight_run_matrix/` | The 8 answer-evaluation runs (existing/updated code × approved/staging × main/held-out), the identification sets (`needs_main_*` = approved, `needs_stage_*` = staging), and the code/fixture hashes used (`frozen_inputs_eight_runs.txt`). |
| `evaluations/final_code/` | Final code (23:33) on **both** DBs: main and held-out (`final_approved*`, `final_staging*`), the identification sets (`needs_approved_*`, `needs_staging_*`), and the code hashes. |
| `evaluations/h1_fix/` | H1 (24 Oct), final code + H1, staging. **Raw outputs:** `h1_staging80.txt`, `h1_stagingheld.txt`, `needs_staging_{multi_need,population,demo_services,tamil}.txt`. **Frozen inputs** (`frozen_inputs_h1.txt`): start time; SHA-256 of the 13 `backend/*.py` files, `scripts/evaluate_answers.py`, `scripts/evaluate_needs.py` and the 7 `fixtures/evaluation/*.json` files; **pre-run** DB checksums of both databases; end time. It holds no post-run checksums and no hash of any test file. **Comparison:** `comparison_vs_final_code.txt` (per question, against `final_code/final_staging*`). **Scope:** `scope_old_vs_new_heading.txt` (old vs new `_section_heading` on every stored block, plus chunker invariance, both DBs). **Traces:** `trace_duplicate_staging_after.txt` (after the fix only; the pre-fix trace was not saved); `changed_staging.txt` and `changed_approved.txt` (claims for the two changed questions). **Tests:** `backend_tests.txt` (targeted tests and full suite, 207 OK). Scripts: `other/scripts/h1/`. |
| `source_audits/staging_inputs/` | The exact scrape outputs staging was built from (`dry.json`, `mobile.json`, `final_rescrape.json`, `apy_candidates.json`, `fees39.html`) and the drafts the model extracted (`staging_drafts.json`), with SHA-256 and original times. Copied on 24 Oct from the temporary folder below. Which file each staging page's text comes from: `07`. |
| `investigations/h4/` | H4 (transport-vehicle age) traces, the read-only blast-radius probe (rejected-claim logs), and the number-word experiments. |
| `investigations/number_words/` | The number-word fix: pre-change state, before/after simulation, staging probes with recorded exit codes, and claims newly rejected (none). |
| `investigations/rag_audit/` | Stage 1 RAG audit (`12`): probe and recall scripts with raw outputs, traces, chunk analysis, close-call scores; README with reproduction steps and transcribed inline commands. |
| `investigations/stage2/` | Stage 2 test plan (`15`): W1/W2/W3/W10/W11 explorations and simulations, with raw outputs. |
| `evaluations/rag_fixes/` | W3/W1/W10 implementation runs: staging and approved main and held-out, identification sets, follow-up scenarios, audit probe; exit codes and pre/post checksums; earlier runs kept as `_run1_before_rowfix` and `_run2_with_w2`; W2 effect check on approved data. |
| `evaluations/h3_fix/` | H3 (26 Oct): the H3 question matrix (3 runs each), the hypothecation comparison with and without continuation, the RC documents regression, continuation scope on both DBs, and the full staging/approved evaluation, identification sets, follow-up scenarios and audit probe. Exit codes and pre/post checksums; earlier versions kept as `_run1_spec_literal` and `_run2_B_always`. |
| `traces/` | Stage-by-stage traces of known cases (`attr_*`) and targeted final-code checks (`targeted_*`). |
| `source_audits/` | Live fetch vs stored text for all 24 URLs; dry-run re-scrape diff. |
| `audit_reports/` | The working source-audit notes and the other Claude session's final report and notes from 23 Oct. |
| `database/` | Checksum SQL, checksum outputs for both DBs, schema, per-page counts, backup verification. |
| `test_results/` | Backend, frontend, TypeScript/build logs, and the single-module import note. |
| `other/scripts/` | The read-only audit and evaluation helper scripts used (they contain absolute scratchpad paths; adapt before reuse). |

Raw working files of the 23 Oct sessions (larger, not copied): `/private/tmp/claude-501/-Users-arunnm-Projects-SOP/db3bcd4a-2175-4a9c-b255-6119f2c7a242/scratchpad/audit2/` and `/private/tmp/claude-501/-Users-arunnm-Projects-SOP/9057724f-75be-4f40-bd2b-13e80a579a34/scratchpad/final/`. These are temporary folders and may be gone after a reboot.

Not included on purpose: `.env`, credentials, database dumps. The backup dump is at `/Users/arunnm/Projects/SOP-backups/` (outside the repository).
