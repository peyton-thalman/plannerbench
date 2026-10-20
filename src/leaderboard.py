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
from run_models import PRICES, cost_of  # noqa: E402
from stats import accuracy, mcnemar  # noqa: E402

# How many rules interact in one question: the leaderboard's main cut.
TIER = {**{t: "single-step" for t in ("federal_tax", "taxable_ss", "rmd", "ss_claim", "bracket_room", "irmaa")},
        **{t: "multi-step" for t in ("tax_torpedo", "widow_penalty")},
        **{t: "stacked" for t in ("senior_phaseout", "conversion_all_in", "widow_all_in")},
        **{t: "compliance" for t in ("rollover_flags", "breakpoint", "comms_review")}}
TIERS = ["single-step", "multi-step", "stacked", "compliance"]


def load(run):
    """Graded replies from one run, or several joined with "+" (each model's replies come from the runs that asked it)."""
    return [g for r in run.split("+") for g in (json.loads(l) for l in (ROOT / "runs" / r / "graded.jsonl").read_text().splitlines() if l.strip())
            if g["bucket"] != "error"]


# How the leaderboard names and describes each model. Unlisted models fall back to their id.
LABELS = {
    "claude-sonnet-5-5": ("Claude Sonnet 5.5", "Anthropic", "Anthropic API", False),
    "claude-haiku-5-5": ("Claude Haiku 5.5", "Anthropic", "Anthropic API", False),
    "or:anthropic/claude-haiku-5.5@anthropic": ("Claude Haiku 5.5", "Anthropic", "OpenRouter → Anthropic", False),
    "or:deepseek/deepseek-v4.1-flash@deepinfra/fp8": ("DeepSeek V4.1 Flash", "DeepSeek", "OpenRouter → DeepInfra (fp8)", True),
    "or:qwen/qwen3.8-flash@alibaba": ("Qwen3.8 Flash", "Alibaba", "OpenRouter → Alibaba", False),
    "or:z-ai/glm-5.3-flash@z-ai/fp8": ("GLM 5.3 Flash", "Z.ai", "OpenRouter → Z.ai (fp8)", True),
    "or:openai/gpt-oss-120b@deepinfra/bf16": ("gpt-oss-120b", "OpenAI", "OpenRouter → DeepInfra (bf16)", True),
}


def label(m):
    name, lab, access, open_weights = LABELS.get(m, (m.removeprefix("or:").split("@")[0], None, None, None))
    return {"name": name, "lab": lab, "access": access, "open_weights": open_weights}


def main(run, rule_run=None):
    rows = load(run)

    def scored(prefix, xs):
        """accuracy plus its 95% interval, under keys like stacked_accuracy, stacked_lo, stacked_hi."""
        a = accuracy(xs)
        return {f"{prefix}accuracy": a["accuracy"], f"{prefix}lo": a["lo"], f"{prefix}hi": a["hi"]}

    models = []
    for m in sorted({g["model"] for g in rows}):
        mine = [g for g in rows if g["model"] == m]
        correct = sum(g["bucket"] == "correct" for g in mine)
        cost = sum(cost_of(g) for g in mine)
        # An unpriced model would look free; leave its cost blank instead.
        priced = m in PRICES or any(g.get("billed_usd") is not None for g in mine)
        models.append({"model": m, **label(m), "questions": len({g["id"] for g in mine}), "replies": len(mine), "correct": correct, **scored("", mine),
                       **{k: v for t in TIERS for k, v in scored(f"{t.replace('-', '_')}_", [g for g in mine if TIER[g["task"]] == t]).items()},
                       # Ran out of tokens before answering: scored as not right, shown so it isn't mistaken for bad math.
                       "truncated_rate": round(sum(g["bucket"] == "truncated" for g in mine) / len(mine), 4),
                       "cost_usd": round(cost, 4) if priced else None,
                       # What a wealthtech team actually pays for: dollars per right answer, not per token.
                       "cost_per_correct": round(cost / correct, 5) if priced and correct else None,
                       "cost_per_1k_questions": round(1000 * cost / len(mine), 3) if priced and mine else None,
                       # Which deployment answered (OpenRouter): an unpinned open model can be served by several hosts.
                       **({"hosts": dict(Counter(g["host"] for g in mine if g.get("host")))} if any(g.get("host") for g in mine) else {})})

    cell = defaultdict(list)
    for g in rows:
        cell[(g["model"], g["task"])].append(g)
    tasks = [{"model": m, "task": t, "tier": TIER[t], "correct": sum(g["bucket"] == "correct" for g in gs), "answered": len(gs), **scored("", gs)}
             for (m, t), gs in sorted(cell.items(), key=lambda kv: (TIERS.index(TIER[kv[0][1]]), kv[0][1], kv[0][0]))]

    mistakes = Counter((g["model"], g.get("mistake") or "unexplained") for g in rows if g["bucket"] == "wrong")
    mistake_rows = [{"model": m, "mistake": k, "count": n} for (m, k), n in sorted(mistakes.items())]

    files = [("models", models), ("tasks", tasks), ("mistakes", mistake_rows)]
    if rule_run:
        with_rule = defaultdict(list)
        for g in load(rule_run):
            with_rule[(g["model"], g["task"])].append(g)
        effects = []
        for (m, t), gs in sorted(with_rule.items()):
            base = cell.get((m, t))
            if not base:
                continue
            # Paired on the same questions (first run of each), so the p-value counts only questions that flipped.
            b0 = {g["id"]: g["bucket"] == "correct" for g in base if g["rep"] == 0}
            b1 = {g["id"]: g["bucket"] == "correct" for g in gs if g["rep"] == 0}
            shared = sorted(b0.keys() & b1.keys())
            a0, a1 = accuracy([g for g in base if g["id"] in b1]), accuracy(gs)
            effects.append({"model": m, "task": t, "without_rule": a0["accuracy"], "without_lo": a0["lo"], "without_hi": a0["hi"],
                            "with_rule": a1["accuracy"], "with_lo": a1["lo"], "with_hi": a1["hi"], "questions": len(shared),
                            "p_value": round(mcnemar([(b1[i], b0[i]) for i in shared]), 5)})
        files.append(("rule_effect", effects))

    out = ROOT / "leaderboard"
    out.mkdir(exist_ok=True)
    for name, data in files:
        (out / f"{name}.json").write_text(json.dumps(data, indent=1) + "\n")
    print("Wrote " + ", ".join(f"leaderboard/{n}.json ({len(d)})" for n, d in files))
    for r in models:
        tiers = " | ".join(f"{t} {r[t.replace('-', '_') + '_accuracy']:.0%} [{r[t.replace('-', '_') + '_lo']:.0%}-{r[t.replace('-', '_') + '_hi']:.0%}]"
                           for t in TIERS if r[t.replace('-', '_') + '_accuracy'] is not None)
        print(f"  {r['model']}: {r['accuracy']:.0%} [{r['lo']:.0%}-{r['hi']:.0%}] overall | {tiers} | " + (f"${r['cost_usd']:.2f}" if r["cost_usd"] is not None else "unpriced")
              + (f", ${r['cost_per_correct'] * 1000:.2f} per 1,000 right answers" if r["cost_per_correct"] else ""))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "live-high-10x1", sys.argv[2] if len(sys.argv) > 2 else None)
