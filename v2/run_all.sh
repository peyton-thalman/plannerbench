#!/bin/sh
# The v2 runs, in the order the $5 budget is spent: the headline track first. Each line resumes if rerun.
# --cap 4.45 leaves room under $4.80 for the judge.
cd "$(dirname "$0")/.." || exit 1
R=".venv/bin/python v2/run.py --cap 4.45"
MID3="or:openai/gpt-6.1-terra@openai/flex,or:google/gemini-3.8-flash@google-ai-studio/flex,or:anthropic/claude-haiku-5.5@anthropic"
$R --set bad --tier frontier --reps 1
$R --set bad --tier mid --reps 2
$R --set bad --tier cheap --reps 3
$R --set hard --tier frontier --reps 1
$R --set hard --models "or:openai/gpt-6.1-terra@openai/flex,or:anthropic/claude-haiku-5.5@anthropic" --reps 2
$R --set hard --models "or:google/gemini-3.8-flash@google-ai-studio/flex" --reps 1
$R --set hard --tier cheap --reps 2
$R --set hard --tools --models "$(python3 -c "import json;print(','.join(m['id'] for m in json.load(open('v2/lineup.json'))['models'] if m['tier']=='cheap' or 'haiku' in m['id']))")" --reps 1
$R --set hard --tools --models "or:openai/gpt-6.1-sol@openai/flex" --per-group 1 --reps 1
echo ALL-DONE
