"""Export a graded run as the leaderboard's data files (models, tasks, mistakes) in leaderboard/.

With a second run that asked the same questions with a rule supplied (run_models.py --context), also writes
rule_effect.json: accuracy on those tasks without and with the rule.

Usage: .venv/bin/python src/leaderboard.py live-high-10x1 [with-rule-10x1]
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from run_models import PRICES  # noqa: E402

# How many rules interact in one question: the leaderboard's main cut.
TIER = {**{t: "single-step" for t in ("federal_tax", "taxable_ss", "rmd", "ss_claim", "bracket_room", "irmaa")},
        **{t: "multi-step" for t in ("tax_torpedo", "widow_penalty")},
        **{t: "stacked" for t in ("senior_phaseout", "conversion_all_in", "widow_all_in")},
        **{t: "compliance" for t in ("rollover_flags", "breakpoint", "comms_review")}}
TIERS = ["single-step", "multi-step", "stacked", "compliance"]


def load(run):
    return [g for g in (json.loads(l) for l in (ROOT / "runs" / run / "graded.jsonl").read_text().splitlines() if l.strip()) if g["bucket"] != "error"]


def main(run, rule_run=None):
    rows = load(run)
    pct = lambda xs: round(sum(x["bucket"] == "correct" for x in xs) / len(xs), 4) if xs else None

    models = []
    for m in sorted({g["model"] for g in rows}):
        mine = [g for g in rows if g["model"] == m]
        pin, pout = PRICES.get(m, (0, 0))
        cost = sum(g.get("input_tokens", 0) * pin + g.get("output_tokens", 0) * pout for g in mine) / 1e6
        models.append({"model": m, "questions": len(mine), "correct": sum(g["bucket"] == "correct" for g in mine), "accuracy": pct(mine),
                       **{f"{t.replace('-', '_')}_accuracy": pct([g for g in mine if TIER[g["task"]] == t]) for t in TIERS},
                       "cost_usd": round(cost, 2)})

    cell = defaultdict(list)
    for g in rows:
        cell[(g["model"], g["task"])].append(g)
    tasks = [{"model": m, "task": t, "tier": TIER[t], "correct": sum(g["bucket"] == "correct" for g in gs), "answered": len(gs), "accuracy": pct(gs)}
             for (m, t), gs in sorted(cell.items(), key=lambda kv: (TIERS.index(TIER[kv[0][1]]), kv[0][1], kv[0][0]))]

    mistakes = Counter((g["model"], g.get("mistake") or "unexplained") for g in rows if g["bucket"] == "wrong")
    mistake_rows = [{"model": m, "mistake": k, "count": n} for (m, k), n in sorted(mistakes.items())]

    files = [("models", models), ("tasks", tasks), ("mistakes", mistake_rows)]
    if rule_run:
        with_rule = defaultdict(list)
        for g in load(rule_run):
            with_rule[(g["model"], g["task"])].append(g)
        files.append(("rule_effect", [{"model": m, "task": t, "without_rule": pct(cell[(m, t)]), "with_rule": pct(gs), "questions": len(gs)}
                                      for (m, t), gs in sorted(with_rule.items()) if cell.get((m, t))]))

    out = ROOT / "leaderboard"
    out.mkdir(exist_ok=True)
    for name, data in files:
        (out / f"{name}.json").write_text(json.dumps(data, indent=1) + "\n")
    print("Wrote " + ", ".join(f"leaderboard/{n}.json ({len(d)})" for n, d in files))
    for r in models:
        print(f"  {r['model']}: {r['accuracy']:.0%} overall | single {r['single_step_accuracy']:.0%} | multi {r['multi_step_accuracy']:.0%} | stacked {r['stacked_accuracy']:.0%} | compliance {r['compliance_accuracy']:.0%} | ${r['cost_usd']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "live-high-10x1", sys.argv[2] if len(sys.argv) > 2 else None)
