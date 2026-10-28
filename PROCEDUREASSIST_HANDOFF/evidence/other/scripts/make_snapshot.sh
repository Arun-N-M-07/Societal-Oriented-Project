#!/bin/zsh
# Freeze the code an evaluation will measure: copies backend/, scripts/ and fixtures/ (no caches) to <dir>, adds the
# snapshot-only backend/__init__.py that snapshot_run.py needs, and writes MANIFEST.txt with every file's SHA-256.
#   make_snapshot.sh <dir>
set -eu
ROOT=/Users/arunnm/Projects/SOP
DIR=$1
[[ -e $DIR ]] && { echo "$DIR exists"; exit 1; }
mkdir -p "$DIR"
rsync -a --exclude __pycache__ "$ROOT/backend" "$ROOT/scripts" "$ROOT/fixtures" "$DIR/"
: > "$DIR/backend/__init__.py"
(cd "$DIR" && { date; shasum -a 256 backend/*.py scripts/*.py fixtures/evaluation/*.json; } > MANIFEST.txt)
echo "snapshot $DIR: $(grep -c . "$DIR/MANIFEST.txt") lines in MANIFEST.txt"
