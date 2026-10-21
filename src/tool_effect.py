"""Same model, same questions, without and with the planning tools: what the tools change, and why misses remain.

Pairs each question across the two runs, reports accuracy by tier with 95% intervals and a paired McNemar test,
dollars off a year, and sorts every miss in the tools run by its tool calls:

  overruled     the tools, used as called, give the key (src/planning_tools.oracle on the same results), but
                the final answer is different: the model replaced a right tool result with its own math
  no tool       the model answered without calling any tool
  misused tools the model called tools but didn't get to the key: wrong inputs, a missed step, or a misread result

"overruled" is decided by recomputing the oracle from the case and checking that every call it needs appears in
the model's own calls with the same inputs and result, so it never credits a model with calls it didn't make.

Usage: .venv/bin/python src/tool_effect.py live-high-10x1 tools-high-10x1 claude-haiku-5-5   → runs/<tools run>/TOOL_EFFECT_vs_<base run>.md
"""
import json
import sys
from pathlib import Path

from dollars import summary
from leaderboard import TIER, TIERS
from planning_tools import PlanningTools, oracle
from stats import accuracy, mcnemar

ROOT = Path(__file__).parent.parent


def graded(run, model):
    return {g["id"]: g for g in (json.loads(l) for l in (ROOT / "runs" / run / "graded.jsonl").read_text().splitlines() if l.strip())
            if g["model"] == model and g["bucket"] != "error"}


class Recorder:
    """Wraps PlanningTools to record the calls the oracle needs for one case."""

    def __init__(self, tools):
        self.tools, self.calls = tools, []

    def value(self, name, **args):
        out = self.tools.value(name, **args)
        self.calls.append((name, args))
        return out


def same_call(need, made):
    name, args = need
    return any(m["name"] == name and not m["is_error"] and all(abs(float(m["input"].get(k, -1)) - v) < 0.005 if isinstance(v, (int, float)) else m["input"].get(k) == v
                                                                 for k, v in args.items()) for m in made)


def miss_kind(tools, case, raw):
    made = raw.get("tool_calls") or []
    if not made:
        return "no tool"
    rec = Recorder(tools)
    if oracle(rec, case) is None:
        return "no tool"
    return "overruled" if all(same_call(c, made) for c in rec.calls) else "misused tools"


def split_of(run):
    meta = ROOT / "runs" / run / "meta.json"
    return json.loads(meta.read_text()).get("split", "public") if meta.exists() else "public"


def main(base_run, tools_run, model):
    # Private runs pair by id within the private set; the report lands in the (git-ignored) private run folder.
    split = split_of(tools_run)
    if split_of(base_run) != split:
        raise SystemExit(f"{base_run} and {tools_run} were asked on different splits; ids don't pair across them.")
    path = ROOT / ("private" if split == "private" else "data") / "cases.jsonl"
    cases = {c["id"]: c for c in (json.loads(l) for l in path.read_text().splitlines() if l.strip())}
    raw = {r["id"]: r for r in (json.loads(l) for l in (ROOT / "runs" / tools_run / "raw.jsonl").read_text().splitlines() if l.strip()) if r["model"] == model}
    a, b = graded(base_run, model), graded(tools_run, model)
    ids = sorted(set(a) & set(b))
    A, B = [a[i] for i in ids], [b[i] for i in ids]

    md = [f"# Tool effect: {model}", "", f"Before: `{base_run}`. After, with the MoneyGuide planning tools (MCP): `{tools_run}`. "
          f"{len(ids)} questions asked both ways; p is a paired McNemar test on the questions that flipped.", "",
          f"| Questions | `{base_run}` | `{tools_run}` | Fixed | Broken | p |", "|---|---|---|---|---|---|"]

    def row(label, keep):
        q = [i for i in ids if keep(i)]
        if not q:
            return
        x, y = accuracy([a[i] for i in q]), accuracy([b[i] for i in q])
        fixed = sum(1 for i in q if b[i]["bucket"] == "correct" and a[i]["bucket"] != "correct")
        broken = sum(1 for i in q if a[i]["bucket"] == "correct" and b[i]["bucket"] != "correct")
        p = mcnemar([(a[i]["bucket"] == "correct", b[i]["bucket"] == "correct") for i in q])
        pct = lambda s: f"{s['accuracy']:.0%} [{s['lo']:.0%}–{s['hi']:.0%}]"
        md.append(f"| {label} ({len(q)}) | {pct(x)} | {pct(y)} | {fixed} | {broken} | {p:.3g} |")

    row("All", lambda i: True)
    for tier in TIERS:
        row(tier, lambda i, t=tier: TIER[cases[i]["task"]] == t)
    md += ["", "| Task | Before | After |", "|---|---|---|"]
    for task in sorted({cases[i]["task"] for i in ids}):
        q = [i for i in ids if cases[i]["task"] == task]
        md.append(f"| {task} | {sum(a[i]['bucket'] == 'correct' for i in q)}/{len(q)} | {sum(b[i]['bucket'] == 'correct' for i in q)}/{len(q)} |")

    def dollars(label, s):
        line = f"- {label}: ${s['dollars_off_per_question']:,.0f} [{s['dollars_lo']:,.0f}–{s['dollars_hi']:,.0f}], {s['misses']} misses"
        return line + (f", median miss ${s['median_miss']:,.0f}, worst ${s['worst_miss']:,.0f}" if s["misses"] else "")

    md += ["", "## Dollars off a year, per numeric question", "", dollars(f"`{base_run}`", summary(A)), dollars(f"`{tools_run}`", summary(B))]

    tools = PlanningTools()
    misses = [i for i in ids if b[i]["bucket"] != "correct"]
    kinds = {i: miss_kind(tools, cases[i], raw[i]) for i in misses}
    tools.close()
    calls = [len(raw[i].get("tool_calls") or []) for i in ids]
    used = sum(1 for i in ids if raw[i].get("tool_calls"))
    md += ["", "## Why the remaining misses happened", "",
           f"Tools were called on {used}/{len(ids)} questions ({sum(calls)} calls, at most {max(calls)} on one question, "
           f"{sum(1 for i in ids for c in raw[i].get('tool_calls') or [] if c['is_error'])} returned an error).", "",
           "| Kind | Misses |", "|---|---|"]
    for k in ("overruled", "misused tools", "no tool"):
        md.append(f"| {k} | {sum(1 for v in kinds.values() if v == k)} |")
    md += ["", "| Question | Kind | Key | Answer | Mistake named by the grader |", "|---|---|---|---|---|"]
    for i in misses:
        md.append(f"| {i} | {kinds[i]} | {b[i].get('key')} | {b[i].get('got')} | {b[i].get('mistake') or ''} |")

    out = ROOT / "runs" / tools_run / f"TOOL_EFFECT_vs_{base_run}.md"
    out.write_text("\n".join(md) + "\n")
    print("\n".join(md[:12]))
    print(f"\nFull report: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
