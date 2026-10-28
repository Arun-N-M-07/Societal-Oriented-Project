#!/bin/zsh
# The full read-only evaluation suite, one Ollama workload at a time, as run for every phase of the
# master reliability work (19_). Writes only into <outdir>; never prints the database URL.
#   [CODE=<snapshot>] [ONLY="run names"] [CLAIMS=1] run_suite.sh <outdir> [extra answer fixtures run on both databases...]
# CODE: run every script against a frozen copy made by make_snapshot.sh (through snapshot_run.py), so the working tree
# can change meanwhile; the frozen inputs are then the snapshot's MANIFEST.txt. ONLY: run just these runs (names as in
# exit_codes.txt, e.g. "staging_safety approved_safety"). CLAIMS=1: answer runs also print every claim (--claims).
# Approved = DATABASE_URL from backend.config (.env); staging = the same server, procedureassist_staging.
set -u
ROOT=/Users/arunnm/Projects/SOP
OUT=$1; shift
mkdir -p "$OUT"
cd "$ROOT"
PY=$ROOT/.venv/bin/python
EV=$ROOT/PROCEDUREASSIST_HANDOFF/evidence
SQL=$EV/database/db_checksums.sql
CODE=${CODE:-}
ONLY=${ONLY:-}
SRC=${CODE:-$ROOT}
FLAGS=(); [[ -n ${CLAIMS:-} ]] && FLAGS=(--claims)
STAGING=$($PY -c "from backend.config import DATABASE_URL as u; print(u.rsplit('/',1)[0]+'/procedureassist_staging')")

checksums() {
  for db in procedureassist procedureassist_staging; do
    echo "$1 $db $(psql -At -d $db -f $SQL | head -4 | tr '\n' ' ')"
  done
}
py() { if [[ -n $CODE ]]; then $PY $EV/other/scripts/snapshot_run.py $CODE "$@"; else $PY "$@"; fi }
run() {
  local name=$1; shift
  [[ -n $ONLY && " $ONLY " != *" $name "* ]] && return
  "$@" > "$OUT/$name.txt" 2> "$OUT/$name.err"
  echo "$name exit $? ($(date +%T))" >> "$OUT/exit_codes.txt"
}

{ date
  if [[ -n $CODE ]]; then echo "code: snapshot $CODE"; cat $CODE/MANIFEST.txt
  else shasum -a 256 backend/*.py scripts/*.py fixtures/evaluation/*.json frontend/src/*.ts frontend/src/*.tsx; fi
  checksums PRE-RUN; } > "$OUT/frozen_inputs.txt"

export DATABASE_URL=$STAGING
run staging80 py $SRC/scripts/evaluate_answers.py fixtures/evaluation/answers.json $FLAGS
run stagingheld py $SRC/scripts/evaluate_answers.py fixtures/evaluation/heldout.json $FLAGS
for f in multi_need population demo_services tamil; do
  run needs_staging_$f py $SRC/scripts/evaluate_needs.py fixtures/evaluation/$f.json
done
run followup_scenarios_staging py $EV/evaluations/rag_fixes/followup_scenarios.py
run audit_probe_staging py $EV/investigations/rag_audit/scripts/probe.py
for x in "$@"; do run staging_${x:t:r} py $SRC/scripts/evaluate_answers.py $x $FLAGS; done
unset DATABASE_URL

run approved80 py $SRC/scripts/evaluate_answers.py fixtures/evaluation/answers.json $FLAGS
run approvedheld py $SRC/scripts/evaluate_answers.py fixtures/evaluation/heldout.json $FLAGS
for x in "$@"; do run approved_${x:t:r} py $SRC/scripts/evaluate_answers.py $x $FLAGS; done

{ checksums POST-RUN; date; } >> "$OUT/frozen_inputs.txt"
echo "suite done $(date +%T)" >> "$OUT/exit_codes.txt"
