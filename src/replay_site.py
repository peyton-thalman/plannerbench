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


FILING = {"married_filing_jointly": "Married, filing jointly", "single": "Single", "mfj": "Married, filing jointly"}


def raw(x, limit=4000):
    """The call or reply as sent, for the "show the raw call" fold; long ones (a whole household) are cut."""
    t = x if isinstance(x, str) else json.dumps(x, indent=1)
    return t if len(t) <= limit else t[:limit] + "\n… (cut; the full call is in the run's raw.jsonl)"


def summarize(call):
    """One engine call in plain words: a title, what the model sent, and what the engine said back (a headline, a
    few labeled numbers, or the options side by side), plus the raw call for anyone who wants it."""
    name, args, res = call["name"], call["input"], call["result"]
    step = {"tool": name, "raw_in": raw(args)}
    if call.get("malformed"):
        return {**step, "title": "Sent a call the engine couldn't read", "error": "The call wasn't valid JSON, so the engine asked for it again."}
    if call.get("is_error"):
        return {**step, "title": "Sent a call the engine turned back", "sent": sent(name, args), "error": res, "note": why_refused(args, res)}
    try:
        out = json.loads(res)
    except (json.JSONDecodeError, TypeError):
        return {**step, "title": f"Asked the engine ({name})", "sent": sent(name, args), "headline": str(res)[:300]}
    step["sent"] = sent(name, args)
    step["raw_out"] = raw(out) if len(res) < 6000 else None
    if name == "run_scenario":
        a = args.get("assumptions") or {}
        span = f"{a.get('first_year', 2026)}–{a.get('last_year', 2050)}"
        plans = out.get("plans", [])
        best = max((p["totals"]["after_tax_wealth_at_end_todays_dollars"] for p in plans), default=0)
        step["title"] = f"Ran {len(plans)} option{'s' * (len(plans) != 1)} year by year, {span}"
        step["options"] = [{"name": p["name"], "wealth": p["totals"]["after_tax_wealth_at_end_todays_dollars"],
                            "behind": p["totals"]["after_tax_wealth_at_end_todays_dollars"] - best} for p in plans]
        step["options"].sort(key=lambda o: -o["wealth"])
        step["note"] = f"After-tax wealth left in {a.get('last_year', 2050)}, in today's dollars. Higher is better."
    elif name == "solve_roth_conversion":
        step["title"] = "Searched for the best Roth conversion"
        step["headline"] = out.get("verdict", "")
        if out.get("engine_runs"):
            step["note"] = f"The engine tried {out['engine_runs']:,} plans to find it."
    elif name == "federal_income_tax":
        step["title"] = "Worked out one year's federal income tax"
        step["headline"] = f"Federal tax: {usd(out['total_federal_tax'])}"
        sd = out.get("senior_deduction") or {}
        step["facts"] = [["Taxable Social Security", usd(out["taxable_social_security"])], ["MAGI", usd(out["magi"])]] + (
            [["Senior deduction", usd(sd["total"])]] if isinstance(sd, dict) and "total" in sd else []) + [
            ["Top bracket reached", f"{round(out['marginal_ordinary_bracket'] * 100)}%"]]
    elif name == "required_minimum_distribution":
        step["title"] = "Worked out a required minimum distribution"
        step["headline"] = f"RMD: {usd(out['rmd'])}" if out.get("required") else "No RMD required that year"
        step["facts"] = [["Age that year", str(out.get("age_in_year"))], ["IRS divisor", str(out.get("uniform_lifetime_divisor"))]]
    elif name == "taxable_social_security":
        step["title"] = "Worked out how much Social Security is taxable"
        step["headline"] = f"Taxable: {usd(out['taxable_social_security'])}"
    elif name == "tax_tables":
        step["title"] = "Looked up the tax tables"
        step["headline"] = out.get("law", "2026 tax tables") + ": brackets, deductions, Medicare surcharge tiers"
    elif name == "social_security_benefit":
        step["title"] = "Worked out a Social Security benefit"
        step["headline"] = f"Monthly benefit: {usd(out['monthly_benefit'])}" if "monthly_benefit" in out else json.dumps(out)[:200]
    elif name == "medicare_part_b_premium":
        step["title"] = "Looked up a Medicare premium"
        step["headline"] = f"Part B: {usd(out['part_b_monthly_per_person'])} a month per person" if "part_b_monthly_per_person" in out else json.dumps(out)[:200]
    else:
        step["title"] = f"Asked the engine ({name})"
        step["headline"] = json.dumps(out)[:200]
    if out.get("next_question"):
        step["hint"] = out["next_question"]
    return step


def why_refused(args, res):
    """Engine versions before 2.2.0 crashed with a JavaScript message when ids didn't match; say what actually happened,
    read off the call itself."""
    if "Cannot read properties" not in str(res) or not isinstance(args, dict):
        return None
    h = args.get("household") or {}
    people = [p.get("id") for p in h.get("people") or []]
    owners = sorted({a.get("owner") for a in h.get("accounts") or []} - set(people) - {"joint"})
    if not owners:
        return None
    return (f"What went wrong: the people were named {' and '.join(f'“{x}”' for x in people)} but the accounts' owners "
            f"{' and '.join(f'“{x}”' for x in owners)}, and names must match exactly. This older engine said so badly; "
            "since version 2.2.0 it names the mismatch in plain words. The model fixed it on its next call.")


def sent(name, args):
    """What the model handed the engine, in a short list of labeled values."""
    if not isinstance(args, dict):
        return [["Input", str(args)[:200]]]
    if name in ("run_scenario", "solve_roth_conversion"):
        h = args.get("household") or {}
        people = ", ".join(str(p.get("id")) for p in h.get("people") or [])
        rows = [["Household", f"{people}: {len(h.get('accounts') or [])} accounts, {len(h.get('income') or [])} income sources"]]
        if name == "run_scenario":
            rows += [["Options to compare", str(len(args.get("plans") or []))]]
            if (args.get("assumptions") or {}).get("return") is not None:
                rows += [["Assumed return", f"{args['assumptions']['return'] * 100:g}% a year"]]
        else:
            rows += [["Convert from", str(args.get("from"))], ["Up to", f"{args.get('max_years')} years"]]
        return rows
    label = {"filing": "Filing", "people_65_or_older": "People 65+", "wages": "Wages", "ordinary_income": "Other taxable income",
             "long_term_gains": "Capital gains and qualified dividends", "social_security_benefits": "Social Security",
             "birth_year": "Born", "prior_year_end_balance": "Balance last Dec 31", "other_income": "Other income", "magi": "MAGI"}
    rows = []
    for k, v in args.items():
        if k == "wages" and not v:
            continue
        val = FILING.get(v, v) if k == "filing" else (usd(v) if isinstance(v, (int, float)) and k not in ("birth_year", "people_65_or_older") else v)
        rows.append([label.get(k, k.replace("_", " ").capitalize()), str(val)])
    return rows


def outcome(g, c):
    """The result in one plain sentence."""
    d = g["decision"]
    nums = list(g["numbers"].values())
    off = sum(not x["right"] for x in nums)
    if c["family"] == "trap":
        return "Correctly said the facts can't settle this." if d["right"] else "Answered a question the facts can't settle."
    if g["great"]:
        return "Right decision, and every number within 2% of the key."
    if d.get("why") == "no pick":
        return "It never gave a final answer."
    if d.get("why") == "declined an answerable question":
        return "It said it couldn't answer, though every fact needed was there."
    if d["right"]:
        return f"Right decision, but {off} of {len(nums)} number{'s' * (len(nums) != 1)} off by more than 2%."
    cost = f" That costs the household {usd(d['lost'])}." if d.get("lost") else ""
    return f"Wrong decision ({d.get('why')}).{cost}" + (f" {off} of {len(nums)} numbers off too." if off else "")


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
                    alone[(r["id"], r["model"], meta.get("set") == "gauntlet-ask")] = {
                        "great": g["great"], "answer": answer_lines(r["text"]), "lost": g["decision"].get("lost"), "why": g["decision"].get("why"),
                        "outcome": outcome(g, cases[r["id"]]), "numbers": {k: {"got": x["got"], "key": x["key"], "right": x["right"]} for k, x in g["numbers"].items()},
                        "decision_right": g["decision"]["right"], "asks": len(r.get("asks") or []), "revealed": bool(r.get("revealed"))}
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
                "great": g["great"], "decision_right": g["decision"]["right"], "why": g["decision"].get("why"), "outcome": outcome(g, c),
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
