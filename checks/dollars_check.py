"""Dollars check: recompute every model's dollars-off score from the raw replies, without src/dollars.py or graded.jsonl.

Reads each run's raw.jsonl and the public answer key, pulls the number after "ANSWER:" with its own pattern, and
rebuilds total dollars off (per year) and the count of material misses ($1,000 a year or more) per model. Both
must match leaderboard/models.json, or the dollar scores don't ship.

Usage: .venv/bin/python -I checks/dollars_check.py live-high-10x1+or-5models-15x1
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
NUMBER = re.compile(r"answer[\s*]*:[\s*]*\$?\s*(-?[0-9][0-9,]*(?:\.[0-9]+)?|-?\.[0-9]+)", re.I)
MONTHLY = ("ss_claim", "irmaa")
TEXT_ANSWERS = ("rollover_flags", "breakpoint", "comms_review")


def main(runs):
    key = {c["id"]: c for c in (json.loads(l) for l in (ROOT / "data" / "cases.jsonl").read_text().splitlines() if l.strip())}
    per_q = defaultdict(lambda: defaultdict(list))  # model -> question -> [(dollars off, material)]
    for run in runs.split("+"):
        last = {}
        for l in (ROOT / "runs" / run / "raw.jsonl").read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                last[(r["model"], r["id"], r["rep"])] = r
        for (model, cid, _), r in last.items():
            c = key[cid]
            if "error" in r or r.get("stop_reason") == "refusal" or c["task"] in TEXT_ANSWERS:
                continue
            hits = NUMBER.findall(r.get("text") or "")
            if not hits:
                continue
            diff = abs(float(hits[-1].replace(",", "")) - c["answer"])
            dollars = 0.0 if diff <= c["tol"] else diff * (12 if c["task"] in MONTHLY else 1)
            per_q[model][cid].append((dollars, dollars >= 1000))
    board = {m["model"]: m["dollars"] for m in json.loads((ROOT / "leaderboard" / "models.json").read_text())}
    ok = True
    for model, qs in sorted(per_q.items()):
        mean = sum(sum(d for d, _ in v) / len(v) for v in qs.values()) / len(qs)
        material = sum(sum(m for _, m in v) / len(v) for v in qs.values()) / len(qs)
        pub = board.get(model) or {}
        same = (len(qs) == pub.get("questions") and abs(round(mean, 2) - pub.get("dollars_off_per_question", -1)) < 0.006
                and abs(round(material, 4) - pub.get("material_rate", -1)) < 0.00006)
        ok &= same
        print(f"{'ok  ' if same else 'DIFF'} {model}: {len(qs)} questions, ${mean:,.2f}/yr off per question, {material:.2%} material"
              + ("" if same else f"  (leaderboard: {pub})"))
    print("PASS: dollar scores match the raw replies." if ok and per_q else "FAIL: dollar scores differ from the raw replies.")
    sys.exit(0 if ok and per_q else 1)


if __name__ == "__main__":
    main(sys.argv[1])
