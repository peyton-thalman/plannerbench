"""The Gauntlet's numbers for the site: site/data/gauntlet.json, from graded runs (src/gauntlet_grade.py first).

Usage: .venv/bin/python src/gauntlet_site.py gauntlet-small gauntlet-small-tools
The first run is the models alone, the second the same questions with the engine's MCP tools.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from run_models import cost_of  # noqa: E402
from stats import wilson  # noqa: E402

NAMES = {"claude-haiku-5-5": "Claude Haiku 5.5", "claude-sonnet-5-5": "Claude Sonnet 5.5", "claude-opus-5-5": "Claude Opus 5.5"}
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


def load(run):
    d = ROOT / "runs" / run
    graded = [json.loads(l) for l in (d / "gauntlet_graded.jsonl").read_text().splitlines()]
    raw = {(r["id"], r["model"]): r for r in map(json.loads, (d / "raw.jsonl").read_text().splitlines()) if "error" not in r}
    return [g for g in graded if g["bucket"] != "error"], raw


def rows(graded, raw, engine):
    out = []
    for m in sorted({g["model"] for g in graded}, key=list(NAMES).index):
        gs = [g for g in graded if g["model"] == m]
        real = [g for g in gs if g["family"] != "trap"]
        nums = [x for g in real for x in g["numbers"].values()]
        great = sum(g["great"] for g in gs)
        lo, hi = wilson(great, len(gs))
        cost = [cost_of(raw[(g["id"], m)]) for g in real]
        out.append({"model": m, "name": NAMES.get(m, m), "engine": engine, "questions": len(gs), "great": great, "lo": lo, "hi": hi,
                    "decisions": sum(g["decision"]["right"] for g in real), "decisions_of": len(real),
                    "numbers": sum(x["right"] for x in nums), "numbers_of": len(nums),
                    "out_of_room": sum(g["bucket"] == "truncated" for g in gs), "cost_per_question": sum(cost) / len(cost),
                    "output_tokens": round(sum(raw[(g["id"], m)].get("output_tokens", 0) for g in real) / len(real)),
                    "overrides": sum(v in ("override", "possible override") for g in gs for v in (g.get("why_wrong") or {}).values())})
    return out


def main(alone_run, tools_run):
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

    out = {"questions": len({g["id"] for g in alone}), "runs": [alone_run, tools_run],
           "rows": rows(alone, raw_alone, False) + rows(tools, raw_tools, True),
           "failures": failures[:3], "side_by_side": side, "families": len(WHAT)}
    (ROOT / "site" / "data" / "gauntlet.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("questions", "failures")}, indent=1)[:1500])


if __name__ == "__main__":
    main(*sys.argv[1:3])
