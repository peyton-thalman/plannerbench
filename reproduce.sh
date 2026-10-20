#!/usr/bin/env bash
# Rebuild every published number from what's in this repo, with no API keys and no trust in the maintainer:
#   1. re-verify the answer key (golden set, independent checker, invariants, PolicyEngine-US)
#   2. regrade every saved model reply from runs/*/raw.jsonl
#   3. rebuild the leaderboard and compare it with the committed copy
# Usage: ./reproduce.sh            (about 3 minutes; the first run installs PolicyEngine, about 1 GB)
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
[ -x .venv-pe/bin/python ] || { python3 -m venv .venv-pe && .venv-pe/bin/pip install -q -r requirements-policyengine.txt; }

echo "== 1. Answer key"
.venv/bin/python -I checks/trust.py

echo "== 2. Regrade saved replies"
for run in runs/*/; do
  run=$(basename "$run")
  [ -f "runs/$run/raw.jsonl" ] && .venv/bin/python src/grade.py "$run" > /dev/null && echo "  graded $run"
done

echo "== 3. Leaderboard"
cp -r leaderboard /tmp/plannerbench-committed-leaderboard.$$
.venv/bin/python src/leaderboard.py $(cat leaderboard/RUNS)
if diff -rq leaderboard /tmp/plannerbench-committed-leaderboard.$$ > /dev/null; then
  echo "REPRODUCED: leaderboard/ matches the committed numbers exactly."
else
  echo "DIFFERS from the committed leaderboard:"; diff -r /tmp/plannerbench-committed-leaderboard.$$ leaderboard || true; exit 1
fi
