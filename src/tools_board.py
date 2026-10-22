"""The "with planning tools" numbers for the site: same model and questions, without tools, with tools 1.0 (the
right number) and with tools 1.1 (the number, the rule and its citation).

Writes leaderboard/tools.json from public runs, which ./reproduce.sh rebuilds and compares. The held-out pair
goes to leaderboard/tools_private.json, aggregates only, and is rebuilt only where the private runs exist (the
maintainer's machine); elsewhere the committed copy is left as is.

Usage: .venv/bin/python src/tools_board.py
"""
import json
import re
import sys
from pathlib import Path

from dollars import summary
from leaderboard import TIER
from stats import accuracy, mcnemar
from tool_effect import graded

ROOT = Path(__file__).parent.parent
MODEL = "claude-haiku-5-5"
NONE, V1, V2 = "live-high-10x1", "tools-high-10x1", "tools-v2-high-10x1"
PRIVATE_NONE, PRIVATE_V2 = "live-high-10x1-private", "tools-v2-high-10x1-private"
# The reply the site quotes: Haiku given the right answer by tools 1.0, arguing with it.
QUOTE = (V1, "senior_phaseout-007", r"The calculation tool's figure[^.]*\.")
STAGES = [("none", "No tools"), ("v1", "Tools 1.0: the right number"), ("v2", "Tools 1.1: the number, the rule and its source")]


def stage(rows):
    acc = accuracy(rows)
    d = summary(rows)
    return {**acc, "right": sum(r["bucket"] == "correct" for r in rows), "dollars_off": d and d["dollars_off_per_question"]}


def paired(a, b, ids):
    pairs = [(a[i]["bucket"] == "correct", b[i]["bucket"] == "correct") for i in ids]
    return {"fixed": sum(1 for x, y in pairs if y and not x), "broken": sum(1 for x, y in pairs if x and not y), "p": mcnemar(pairs)}


def ladder(runs):
    g = {k: graded(r, MODEL) for k, r in runs.items()}
    ids = sorted(set.intersection(*(set(v) for v in g.values())))
    out = {"questions": len(ids), "tasks": sorted({g[next(iter(g))][i]["task"] for i in ids}),
           "stages": [{"key": k, "label": label, **stage([g[k][i] for i in ids])} for k, label in STAGES if k in g]}
    keys = [k for k, _ in STAGES if k in g]
    out["pairs"] = {f"{a}_to_{b}": paired(g[a], g[b], ids) for a, b in zip(keys, keys[1:])}
    if len(keys) > 2:
        out["pairs"][f"{keys[0]}_to_{keys[-1]}"] = paired(g[keys[0]], g[keys[-1]], ids)
    out["by_task"] = [{"task": t, **{k: sum(g[k][i]["bucket"] == "correct" for i in ids if g[k][i]["task"] == t) for k in keys},
                       "of": sum(1 for i in ids if g[keys[0]][i]["task"] == t)} for t in out["tasks"]]
    return out


def main():
    hard = ladder({"none": NONE, "v1": V1, "v2": V2})
    # Tools 1.0 was also asked every task, so the whole set shows what tools do on easy questions too.
    a, b = graded(NONE, MODEL), graded(V1, MODEL)
    ids = sorted(set(a) & set(b))
    whole = {"questions": len(ids), "without": stage([a[i] for i in ids]), "with": stage([b[i] for i in ids]), **paired(a, b, ids),
             "by_tier": {t: {"without": accuracy([a[i] for i in ids if TIER[a[i]["task"]] == t])["accuracy"],
                             "with": accuracy([b[i] for i in ids if TIER[b[i]["task"]] == t])["accuracy"]} for t in ("single-step", "multi-step", "stacked", "compliance")}}
    # Overruled misses, from tool_effect's report on the same pair (it sorts every miss by its tool calls).
    report = (ROOT / "runs" / V1 / f"TOOL_EFFECT_vs_{NONE}.md").read_text()
    whole["misses"] = int(re.search(r"\| overruled \| (\d+) \|", report).group(1)) + int(re.search(r"\| misused tools \| (\d+) \|", report).group(1)) \
        + int(re.search(r"\| no tool \| (\d+) \|", report).group(1))
    whole["overruled"] = int(re.search(r"\| overruled \| (\d+) \|", report).group(1))

    run, cid, pattern = QUOTE
    reply = next(json.loads(l) for l in (ROOT / "runs" / run / "raw.jsonl").read_text().splitlines() if l.strip() and json.loads(l)["id"] == cid)
    key = next(json.loads(l) for l in (ROOT / "data" / "cases.jsonl").read_text().splitlines() if json.loads(l)["id"] == cid)["answer"]
    after = graded(V2, MODEL)[cid]
    # What tools 1.1 said back on the same question: the senior-deduction block of its tax reply.
    v2 = next(json.loads(l) for l in (ROOT / "runs" / V2 / "raw.jsonl").read_text().splitlines() if l.strip() and json.loads(l)["id"] == cid)
    shown = next(json.loads(c["result"]) for c in v2["tool_calls"] if c["name"] == "federal_income_tax" and not c["is_error"])
    quote = {"id": cid, "run": run, "text": re.search(pattern, reply["text"]).group(0).replace("**", ""),
             "key": key, "answered": graded(run, MODEL)[cid]["got"], "answered_v2": after["got"], "v2_right": after["bucket"] == "correct",
             "v2_senior_deduction": shown["senior_deduction"]}

    meta = {r: json.loads((ROOT / "runs" / r / "meta.json").read_text()).get("tools") for r in (V1, V2)}
    out = {"model": MODEL, "runs": {"none": NONE, "v1": V1, "v2": V2},
           "server": {k: {"version": m["server"]["version"], "moneyguide_commit": m["moneyguide_commit"]} for k, m in (("v1", meta[V1]), ("v2", meta[V2]))},
           "tools": meta[V2]["names"], "hard": hard, "whole": whole, "quote": quote}
    (ROOT / "leaderboard" / "tools.json").write_text(json.dumps(out, indent=1) + "\n")

    if (ROOT / "runs" / PRIVATE_V2 / "graded.jsonl").exists() and (ROOT / "runs" / PRIVATE_NONE / "graded.jsonl").exists():
        private = ladder({"none": PRIVATE_NONE, "v2": PRIVATE_V2})
        private.pop("by_task")  # aggregates by tier and overall only; per-task rows add nothing the site needs
        (ROOT / "leaderboard" / "tools_private.json").write_text(json.dumps({"model": MODEL, "split": "private", **private}, indent=1) + "\n")
        print("wrote leaderboard/tools_private.json (aggregates only)")
    print(f"wrote leaderboard/tools.json: hard {[s['right'] for s in hard['stages']]} of {hard['questions']}, whole {whole['without']['right']} → {whole['with']['right']} of {whole['questions']}")


if __name__ == "__main__":
    sys.exit(main())
