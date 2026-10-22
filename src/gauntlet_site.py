"""The Gauntlet's numbers for the site: site/data/gauntlet.json, from graded runs (src/gauntlet_grade.py first).

Usage: .venv/bin/python src/gauntlet_site.py gauntlet-small,ds-smoke gauntlet-small-tools,ds-smoke-tools [ds-ask-smoke,ds-ask-smoke-tools]
First the runs with models alone, then the same questions with the engine's MCP tools (comma-separated, any number of
each), then optionally the ask-first runs (src/gauntlet_ask.py), alone and with the engine.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from run_models import cost_of  # noqa: E402
from stats import wilson  # noqa: E402

NAMES = {"claude-haiku-5-5": "Claude Haiku 5.5", "claude-sonnet-5-5": "Claude Sonnet 5.5", "claude-opus-5-5": "Claude Opus 5.5",
         "or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8": "DeepSeek V4.1 Flash"}
OPEN = {"or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8"}  # open-weight models, labeled as such on the site
# What each family's question is, in a few words, for the failure list.
WHAT = {"how_much": "How much to convert to Roth, and for how many years", "first_rmd": "A Roth conversion in the first-RMD year",
        "torpedo_irmaa": "A conversion that hits the tax torpedo and an IRMAA tier two years later",
        "senior_phaseout": "Converting inside the senior-deduction phase-out", "widow": "Converting before or after a spouse dies",
        "muni_stack": "A conversion when muni interest counts toward MAGI", "qcd_giving": "Giving by check or by QCD",
        "inherited_ira": "Emptying an inherited IRA under the 10-year rule", "gains_vs_conversion": "Harvesting 0% gains or converting",
        "claim_age": "Claiming Social Security at 70 and converting in the gap years"}
SHORTCUT = {"phaseout_once": "applied the senior-deduction phase-out once to the couple instead of to each spouse",
            "ignore_capital_gains_stacking": "left out how the extra income pushes dividends into the 15% capital-gains rate",
            "ignore_social_security_torpedo": "left out the extra Social Security that becomes taxable (the torpedo)",
            "ignore_senior_deduction": "left out the senior deduction it loses", "part_b_only": "counted Part B and forgot the Part D surcharge"}


def load(runs):
    graded, raw = [], {}
    for run in runs.split(","):
        d = ROOT / "runs" / run
        graded += [g for g in map(json.loads, (d / "gauntlet_graded.jsonl").read_text().splitlines()) if g["bucket"] != "error"]
        raw.update({(r["id"], r["model"]): r for r in map(json.loads, (d / "raw.jsonl").read_text().splitlines()) if "error" not in r})
    return graded, raw


def rows(graded, raw, engine):
    out = []
    for m in sorted({g["model"] for g in graded}, key=list(NAMES).index):
        gs = [g for g in graded if g["model"] == m]
        real = [g for g in gs if g["family"] != "trap"]
        nums = [x for g in real for x in g["numbers"].values()]
        great = sum(g["great"] for g in gs)
        lo, hi = wilson(great, len(gs))
        cost = [cost_of(raw[(g["id"], m)]) for g in real]
        out.append({"model": m, "name": NAMES.get(m, m), "open": m in OPEN, "engine": engine, "questions": len(gs), "great": great, "lo": lo, "hi": hi,
                    "decisions": sum(g["decision"]["right"] for g in real), "decisions_of": len(real),
                    "numbers": sum(x["right"] for x in nums), "numbers_of": len(nums),
                    "out_of_room": sum(g["bucket"] == "truncated" for g in gs), "cost_per_question": sum(cost) / len(cost),
                    "output_tokens": round(sum(raw[(g["id"], m)].get("output_tokens", 0) for g in real) / len(real)),
                    "overrides": sum(v in ("override", "possible override") for g in gs for v in (g.get("why_wrong") or {}).values())})
    return out


def ask_first(runs):
    """The ask-first runs: per model and engine, how often it asked, got the missing fact, and was fully right; a few of
    its real questions; and the proof each question is fair (every guess graded wrong; the stand-ins)."""
    if not runs:
        return None
    rows_ = []
    # Run by run: the same model answers the same ids alone and with the engine, so the runs can't share one lookup.
    for run in runs.split(","):
        graded, raw = load(run)
        for m in sorted({g["model"] for g in graded}):
            gs = [g for g in graded if g["model"] == m]
            engine = gs[0]["tools"]
            great = sum(g["great"] for g in gs)
            lo, hi = wilson(great, len(gs))
            quotes = [{"q": a["q"], "id": g["id"]} for g in gs for a in raw[(g["id"], m)].get("asks", []) if a["revealed"]][:3]
            rows_.append({"model": m, "name": NAMES.get(m, m), "open": m in OPEN, "engine": engine, "questions": len(gs), "great": great, "lo": lo, "hi": hi,
                          "asked": sum(g.get("asks", 0) > 0 for g in gs), "got_fact": sum(bool(g.get("revealed")) for g in gs),
                          "great_with_fact": sum(g["great"] for g in gs if g.get("revealed")), "quotes": quotes,
                          "cost_per_question": sum(cost_of(raw[(g["id"], m)]) for g in gs) / len(gs)})
    rows_.sort(key=lambda r: (r["engine"], r["name"]))
    built = [json.loads(l) for l in (ROOT / "data" / "gauntlet-ask.jsonl").read_text().splitlines()]
    stand = {}
    for style in ("asker", "guesser", "spammer"):
        f = ROOT / "runs" / f"ask-fake-{style}" / "gauntlet_graded.jsonl"
        if f.exists():
            gs = [json.loads(l) for l in f.read_text().splitlines()]
            stand[style] = {"great": sum(g["great"] for g in gs), "got_fact": sum(bool(g.get("revealed")) for g in gs), "of": len(gs)}
    return {"runs": runs.split(","), "rows": rows_, "built": len(built),
            "guesses": min(len(b["withheld"]["guesses"]) for b in built), "all_guesses_wrong": sum(all(not x["great"] for x in b["withheld"]["guesses"]) for b in built),
            "stand_ins": stand}


def main(alone_run, tools_run, ask_runs=None):
    alone, raw_alone = load(alone_run)
    tools, raw_tools = load(tools_run)
    with_engine = {(g["id"], g["model"]): g for g in tools}
    cases = {c["id"]: c for c in map(json.loads, (ROOT / "data" / "gauntlet.jsonl").read_text().splitlines())}

    failures = []
    for g in alone:
        if g["family"] == "trap" or g["great"] or g["bucket"] == "truncated":
            continue
        named = [SHORTCUT[x["shortcut"]] for x in g["numbers"].values() if x.get("shortcut") in SHORTCUT]
        failures.append({"id": g["id"], "model": NAMES[g["model"]], "what": WHAT[g["family"]], "why": g["decision"]["why"],
                         "lost": round(g["decision"]["lost"] or 0), "shortcut": named[0] if named else None,
                         "engine_great": bool(with_engine.get((g["id"], g["model"]), {}).get("great"))})
    failures.sort(key=lambda f: (-f["lost"], f["shortcut"] is None))

    # The side-by-side: the costliest "how much to convert" miss, alone vs. the same model with the engine.
    pick = next((f for f in failures if f["id"].startswith("g-how_much")), failures[0])
    c = cases[pick["id"]]
    model = next(k for k, v in NAMES.items() if v == pick["model"])
    plan = lambda text: (re.findall(r"(?m)PLAN\W*:\W*(.+)$", text or "") or ["—"])[-1].strip(" *")
    side = {"id": c["id"], "model": pick["model"], "intro": c["prompt"].split("\n")[0],
            "alone": plan(raw_alone[(c["id"], model)]["text"]), "alone_lost": pick["lost"],
            "engine": plan(raw_tools[(c["id"], model)]["text"]), "engine_calls": [t["name"] for t in raw_tools[(c["id"], model)].get("tool_calls", [])],
            "best": c["decision"]["best_any"]["label"], "best_gain": c["decision"]["best_flat"]["gain"]}

    out = {"questions": len({g["id"] for g in alone}), "runs": alone_run.split(",") + tools_run.split(","), "ask_first": ask_first(ask_runs),
           "rows": rows(alone, raw_alone, False) + rows(tools, raw_tools, True),
           "failures": failures[:3], "side_by_side": side, "families": len(WHAT)}
    (ROOT / "site" / "data" / "gauntlet.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("questions", "failures")}, indent=1)[:1500])


if __name__ == "__main__":
    main(*sys.argv[1:4])
