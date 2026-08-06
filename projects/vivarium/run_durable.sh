#!/bin/bash
# Append-only run wrapper. The previous batch wrote only to /tmp, which was cleared overnight and
# took ~7 completed runs with it. Every run now lands in the repo: a per-run log AND one appended
# line in results.tsv, written the moment the run finishes.
set -u
D=/home/rbao/quorum-thermolife/projects/vivarium/docs/runs
TARGET=$1; TAG=$2; ARGS=$3
mkdir -p "$D"
bazel run --ui_event_filters=-info,-stdout --noshow_progress "//projects/vivarium:$TARGET" -- "$TAG" "$ARGS" > "$D/$TAG.log" 2>&1
grep -h "RESULT" "$D/$TAG.log" >> "$D/results.tsv"
