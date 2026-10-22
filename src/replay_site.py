"""Tool-call replays for the site: site/data/replays.json, from graded Gauntlet runs (src/gauntlet_grade.py first).

Each replay is one model answering one question with the engine: every tool call it made (what it asked the engine,
what came back, or the error), every question it put to the client (ask-first runs), its final answer against the
key, and the same model's answer alone when an alone run is given. The page is site/replay.html.

Usage: .venv/bin/python src/replay_site.py <run> [<run> ...]   (tools runs, alone runs and ask-first runs, any order)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from gauntlet_site import NAMES, WHAT  # noqa: E402
from run_models import cost_of  # noqa: E402

NAMES = {**NAMES, "or:deepseek/deepseek-v4.1-flash-1017@deepinfra/fp8": "DeepSeek V4.1 Flash (Oct 17)", "fake": "Stand-in (answer key)"}


def usd(x):
    return f"{'−' if x < 0 else ''}${abs(round(x)):,}"


def summarize(call):
    """(what the model asked for, what came back) in a line or two each, plus the full reply for the curious."""
    name, args, res = call["name"], call["input"], call["result"]
    if call.get("malformed"):
        return {"name": name, "asked": "A call whose arguments weren't valid JSON", "got": res, "error": True}
    if call.get("is_error"):
        return {"name": name, "asked": ask_line(name, args), "got": res, "error": True}
    try:
        out = json.loads(res)
    except (json.JSONDecodeError, TypeError):
        return {"name": name, "asked": ask_line(name, args), "got": str(res)[:300]}
    got = []
    if name == "run_scenario":
        for p in out.get("plans", []):
            got.append(f"{p['name']}: {usd(p['totals']['after_tax_wealth_at_end_todays_dollars'])} after-tax wealth at the end (today's dollars)")
        for cmp in out.get("comparisons", [])[:3]:
            got.append(f"{cmp['plan']} vs {cmp['versus']}: {'+' if cmp['after_tax_wealth_at_end_todays_dollars'] >= 0 else ''}{usd(cmp['after_tax_wealth_at_end_todays_dollars'])}")
    elif name == "solve_roth_conversion":
        got.append(out.get("verdict", ""))
        if out.get("close_call"):
            got.append(f"Close call: {out['close_call'] if isinstance(out['close_call'], str) else json.dumps(out['close_call'])[:200]}")
    else:
        got.append(json.dumps(out)[:300])
    if out.get("next_question"):
        got.append(f"The engine suggests asking: {out['next_question']}")
    return {"name": name, "asked": ask_line(name, args), "got": "\n".join(got)}


def ask_line(name, args):
    if not isinstance(args, dict):
        return str(args)[:200]
    if name == "run_scenario":
        plans = [p.get("name", "?") for p in args.get("plans") or []]
        return f"Run {len(plans)} plan{'s' * (len(plans) != 1)} for the household: " + "; ".join(plans)
    if name == "solve_roth_conversion":
        return f"Find the best Roth conversion from {args.get('from')}, up to {args.get('max_years')} years"
    return json.dumps(args)[:200]


def load(run):
    d = ROOT / "runs" / run
    meta = json.loads((d / "meta.json").read_text())
    cases = {c["id"]: c for c in map(json.loads, (ROOT / ("private" if meta.get("split") == "private" else "data") / "gauntlet.jsonl").read_text().splitlines())}
    if meta.get("split") == "private":
        raise SystemExit(f"{run} is a private-split run; replays are only built from public questions.")
    graded = {(g["id"], g["model"]): g for g in map(json.loads, (d / "gauntlet_graded.jsonl").read_text().splitlines())}
    raw = [r for r in map(json.loads, (d / "raw.jsonl").read_text().splitlines()) if "error" not in r]
    return meta, cases, graded, raw


def answer_lines(text):
    lines = (text or "").strip().splitlines()
    tail = [l for l in lines if l.split(":")[0].strip().strip("*").upper() in ("PICK", "PLAN") or l.strip().startswith(("N1", "N2", "N3", "N4"))]
    return tail


def main(runs):
    alone, replays = {}, []
    loaded = [load(r) + (r,) for r in runs]
    for meta, cases, graded, raw, run in loaded:
        if not meta.get("tools"):  # alone runs, regular or ask-first, to show beside the same question with the engine
            for r in raw:
                g = graded.get((r["id"], r["model"]))
                if g:
                    alone[(r["id"], r["model"], meta.get("set") == "gauntlet-ask")] = {"great": g["great"], "answer": answer_lines(r["text"]), "lost": g["decision"].get("lost"),
                                                    "why": g["decision"].get("why")}
    for meta, cases, graded, raw, run in loaded:
        ask = meta.get("set") == "gauntlet-ask"
        if not meta.get("tools") and not ask:
            continue
        for r in raw:
            g, c = graded.get((r["id"], r["model"])), cases.get(r["id"])
            if not g or not c:
                continue
            steps = [{"kind": "tool", **summarize(t)} for t in r.get("tool_calls") or []]
            # Ask-first turns aren't interleaved with tool calls in the record, so questions are listed first.
            steps = [{"kind": "ask", **a} for a in r.get("asks") or []] + steps
            key = []
            d = c["decision"]
            if c["family"] == "trap":
                key.append("PICK: CANT (the facts can't settle it)")
            elif c["how_much"]:
                key.append(f"PLAN: {d['best_flat']['amount']} x {d['best_flat']['years']}")
            else:
                key.append(f"PICK: {'CLOSE ' if d['close'] else ''}{','.join(d['pick'])}")
            key += [f"{k}: {n['value']}" for k, n in c["numbers"].items()]
            replays.append({
                "run": run, "id": r["id"], "family": c["family"], "what": WHAT.get(c["family"], "A question the facts can't settle"),
                "model": r["model"], "model_name": NAMES.get(r["model"], r["model"]), "engine": bool(meta.get("tools")), "ask_first": ask,
                "withheld": (c.get("withheld") or {}).get("fact") if ask else None,
                "options": c.get("options"), "asks": [n["ask"] for n in c["numbers"].values()],
                "steps": steps, "answer": answer_lines(r["text"]), "key": key,
                "great": g["great"], "decision_right": g["decision"]["right"], "why": g["decision"].get("why"),
                "numbers": {k: {"got": x["got"], "key": x["key"], "right": x["right"]} for k, x in g["numbers"].items()},
                "why_wrong": g.get("why_wrong"), "revealed": g.get("revealed"),
                "tokens": r.get("input_tokens", 0) + r.get("output_tokens", 0), "cost": round(cost_of(r), 4),
                "alone": alone.get((r["id"], r["model"], ask)) if meta.get("tools") else None,
            })
    replays.sort(key=lambda x: (x["ask_first"], x["model_name"], x["id"]))
    out = ROOT / "site" / "data" / "replays.json"
    out.write_text(json.dumps({"replays": replays}, indent=1) + "\n")
    print(f"{len(replays)} replays -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
