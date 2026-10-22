"""Grade a Gauntlet run: every reply against the engine's key, with overrides tracked case by case.

Each reply gets four checks (PLAN-gauntlet.md, G3) and is "great" only if all pass:
  decision  PICK is the best option or within $1,000 of it (PICK: CLOSE x,y is right if every letter named is);
            for how_much, the proposed plan is run through the clean-room engine and must be within $1,000 of the best
  numbers   every N line within the key's tolerance (2%, at least $50, at most $1,000)
  scope     PICK: CANT on trap questions, and only on trap questions
  format    a PICK (or PLAN) line and every N line were given; otherwise the reply is "no_answer"
"Invents nothing" isn't auto-graded: replies that state assumptions with dollar amounts not in the question are
listed for a human look.

Every wrong answer is priced and named: a wrong pick costs the household the engine's after-tax wealth difference;
a wrong number that matches a known shortcut ("ignored the torpedo", "used one flat rate", "Part B only") is named.

With tools, each wrong item is also classed by what the engine had shown the model:
  override        a tool reply contained the right answer and the final answer went against it
  mistranslated   the model called the tools but no reply contained the right answer (wrong inputs)
  no_tools        it never called them
Overrides are the finding that matters most, so every one is listed with the tool reply and the model's words.

Usage: .venv/bin/python src/gauntlet_grade.py <run> [<run with tools> ...]
"""
import itertools
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from stats import wilson  # noqa: E402

CLOSE = 1000
SETS = {"public": ROOT / "data" / "gauntlet.jsonl", "private": ROOT / "private" / "gauntlet.jsonl"}

# Tolerates markdown bold, a leading $, thousands commas and a typographic minus; the last line of each kind wins.
NUM = r"([-−–]?\s*\$?\s*[\d,]*\.?\d+)"
LINE = lambda label: re.compile(rf"^[\s*_`>#-]*{label}[\s*_`]*:[\s*_`]*(.+?)[\s*_`]*$", re.IGNORECASE | re.MULTILINE)
PICK, PLAN = LINE("PICK"), LINE("PLAN")


def number(s):
    m = re.search(NUM, s or "")
    if not m:
        return None
    t = re.sub(r"[\s$,]", "", m.group(1)).replace("−", "-").replace("–", "-")
    try:
        return float(t)
    except ValueError:
        return None


def parse(text):
    """{'pick': ('CANT'|'CLOSE'|'ONE', letters) or None, 'plan': (amount, years) or None, 'N1': x, ...}"""
    text = text or ""
    out = {}
    picks = PICK.findall(text)
    if picks:
        p = picks[-1].upper()
        if "CANT" in p or "CAN'T" in p or "CANNOT" in p:
            out["pick"] = ("CANT", ())
        else:
            letters = tuple(dict.fromkeys(re.findall(r"\b([A-D])\b", p.replace("CLOSE", ""))))
            out["pick"] = ("CLOSE" if "CLOSE" in p else "ONE", letters) if letters else None
    plans = PLAN.findall(text)
    if plans:
        m = re.search(r"\$?\s*([\d,]+)\s*(?:a year|per year|/yr)?\s*[x×*]\s*(\d+)", plans[-1], re.IGNORECASE)
        out["plan"] = (float(m.group(1).replace(",", "")), int(m.group(2))) if m else None
        if "CANT" in plans[-1].upper():
            out["pick"] = ("CANT", ())
    for k in ("N1", "N2"):
        hits = LINE(k).findall(text)
        if hits:
            out[k] = number(hits[-1])
    return out


@lru_cache(maxsize=None)
def plan_gain(case_id, amount, years):
    """After-tax wealth gain (today's dollars) of a flat conversion plan vs none, by the clean-room engine."""
    c = CASES[case_id]
    sc = json.loads(json.dumps(c["scenarios"]["A"]))
    acts = [{"type": "roth_conversion", "from": c["how_much"]["from"], "amount": amount, "years": list(range(2026, 2026 + years))}] if amount > 0 and years > 0 else []
    sc["plans"] = [{"name": "none", "actions": []}, {"name": "plan", "actions": acts}]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(sc, f)
    out = json.loads(subprocess.run([sys.executable, "-I", str(ROOT / "checks/cleanroom/engine.py"), f.name], capture_output=True, text=True, check=True).stdout)
    end = lambda p: out["plans"][p]["totals"]["end_wealth_real"]
    return end("plan") - end("none")


def grade_decision(c, got):
    """(right, dollars the household gives up, label). Traps want CANT; everything else wants the engine's pick."""
    d = c["decision"]
    if c["family"] == "trap":
        return (got.get("pick") or ("",))[0] == "CANT", 0, "declined" if (got.get("pick") or ("",))[0] == "CANT" else "answered a trap"
    pick = got.get("pick")
    if pick and pick[0] == "CANT":
        return False, None, "declined an answerable question"
    if c["how_much"]:
        plan = got.get("plan")
        if plan is None:
            return False, None, "no plan"
        amount, years = plan
        years = min(years, 25)
        gain = plan_gain(c["id"], amount, years)
        lost = d["best_flat"]["gain"] - gain
        return lost <= CLOSE, max(0, lost), "within $1,000 of the best plan" if lost <= CLOSE else f"plan gives up {money(lost)}"
    if not pick:
        return False, None, "no pick"
    gains = d["gains"]
    named = [l for l in pick[1] if l in gains]
    if not named:
        return False, None, "picked an option that doesn't exist"
    best = max(gains.values())
    lost = max(best - gains[l] for l in named)
    right = all(l in d["pick"] for l in named)
    return right, lost, ("right" if right else f"picked {','.join(named)}; best was {d['pick'][0]}")


def money(x):
    return f"{'−' if x < 0 else ''}${abs(round(x)):,}"


def shortcut_name(got, n):
    """The known shortcut this wrong answer matches (the nearest, when two shortcuts land close together)."""
    near = [(abs(got - v), name) for name, v in n["shortcuts"].items() if abs(got - v) <= n["tol"]]
    return min(near)[1] if near else None


# ---- What the engine showed the model (tools runs) ------------------------------------------------------------

def tool_views(rec):
    """Every number the tool replies put in front of the model that a Gauntlet answer could be read from. Replies are
    pooled: models often run one option per call, so the right difference only appears across calls."""
    plans, rows, totals, named = [], [], [], {}
    for call in rec.get("tool_calls") or []:
        try:
            out = json.loads(call["result"]) if isinstance(call["result"], str) else call["result"]
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(out, list):  # MCP content blocks
            out = next((json.loads(b["text"]) for b in out if isinstance(b, dict) and b.get("type") == "text" and b["text"].lstrip().startswith("{")), None)
        if not isinstance(out, dict):
            continue
        for p in out.get("plans") or [] if isinstance(out.get("plans"), list) else []:
            rows.append({y["year"]: y for y in p.get("years", [])})
            if m := re.match(r"\s*(?:option\s*)?([A-D])\b", str(p.get("name", "")), re.IGNORECASE):
                named[m[1].upper()] = rows[-1]
            totals.append(p.get("totals", {}).get("after_tax_wealth_at_end_todays_dollars"))
        if "strategies" in out:
            plans += [(s.get("amounts", [0])[0], len(s.get("years", []))) for s in out["strategies"] if s.get("amounts")]
            for s in out["strategies"]:
                if m := re.match(r"\$([\d,]+) a year for (\d+) year", s.get("label", "")):
                    plans.append((float(m[1].replace(",", "")), int(m[2])))
    # By year, so a 2026 answer can only be matched by something the engine said about 2026.
    nums = defaultdict(list)
    for yr in {y for r in rows for y in r}:
        fed = [r[yr]["federal_tax"] for r in rows if yr in r and isinstance(r[yr].get("federal_tax"), (int, float))]
        med = [sum(m.get("premium", 0) for m in (r[yr].get("medicare") or {}).values()) for r in rows if yr in r]
        nums[("tax", yr)] += [a - b for a, b in itertools.permutations(fed, 2)]
        nums[("medicare", yr)] += [a - b for a, b in itertools.permutations(med, 2)]
        for r in rows:
            if yr in r:
                y = r[yr]
                nums[("value", yr)] += [y[k] for k in ("senior_deduction", "taxable_social_security", "rmd", "social_security") if isinstance(y.get(k), (int, float))]
                nums[("value", yr)] += list((y.get("rmd_by_account") or {}).values()) + list((y.get("social_security_by_person") or {}).values())
    nums["named"] = named
    return nums, [totals], plans


def engine_showed_decision(c, decisions):
    """True if the run_scenario replies ranked every option the way the key does (matched by wealth differences)."""
    gains = c["decision"].get("gains")
    if not gains:
        return False
    letters = list(gains)
    for vals in decisions:
        vals = [v for v in vals if isinstance(v, (int, float))]
        # Every option must line up (pairs alone match by chance too often).
        for k in (len(letters),):
            for subset in itertools.permutations(range(len(vals)), k):
                for ls in itertools.combinations(letters, k):
                    if all(abs((vals[subset[i]] - vals[subset[0]]) - (gains[ls[i]] - gains[ls[0]])) <= 500 for i in range(k)):
                        if c["decision"]["pick"][0] in ls and max(ls, key=lambda l: gains[l]) in c["decision"]["pick"]:
                            return True
    return False


def classify(rec, c, item, n=None):
    """For a wrong item in a tools run: override, mistranslated or no_tools."""
    if not rec.get("tool_calls"):
        return "no_tools"
    nums, decisions, plans = tool_views(rec)
    if item == "decision":
        if c["how_much"]:
            b = c["decision"]["best_flat"]
            shown = any(abs(a - b["amount"]) <= 5000 and y == b["years"] for a, y in plans)
        else:
            shown = engine_showed_decision(c, decisions)
    else:
        exact = named_reading(n, nums["named"], c)
        if exact is not None:
            shown = abs(exact - n["value"]) <= n["tol"]
        elif any(isinstance(v, (int, float)) and abs(v - n["value"]) <= n["tol"] for v in nums[number_kind(n)]):
            # Plans weren't named by option letter, so the match is on some pair of plans: usually the right one, but a
            # coincidence is possible (about 6% on wrong-input runs, checks/gauntlet_check.py). Listed apart.
            return "possible override"
        else:
            shown = False
    return "override" if shown else "mistranslated"


def named_reading(n, named, c):
    """When the model named its plans by option letter, read the asked number off exactly those plans (else None)."""
    kind, year = number_kind(n)
    rows = lambda l: named.get(l, {}).get(year)
    if m := re.search(r"under option (\w) than under option (\w)", n["ask"]):
        b, a = rows(m[1]), rows(m[2])
        if b and a:
            if kind == "tax":
                return b["federal_tax"] - a["federal_tax"]
            if kind == "medicare":
                prem = lambda y: sum(x.get("premium", 0) for x in (y.get("medicare") or {}).values())
                return prem(b) - prem(a)
    if m := re.search(r"Under option (\w),", n["ask"]):
        y = rows(m[1])
        if y:
            ids = {name: pid for pid, name in c["names"].items()}
            if "senior deduction" in n["ask"]:
                return y.get("senior_deduction")
            if "Social Security is taxable" in n["ask"]:
                return y.get("taxable_social_security")
            if who := re.search(r"Social Security will (\w+) receive", n["ask"]):
                return (y.get("social_security_by_person") or {}).get(ids.get(who[1]))
    return None


def number_kind(n):
    """Which engine figure a question's number is read from: ("tax" | "medicare" | "value", year asked about)."""
    year = int(re.findall(r"\b(20\d\d)\b", n["ask"])[-1])
    kind = "medicare" if "Medicare premiums" in n["ask"] else "tax" if "federal income tax" in n["ask"] else "value"
    return kind, year


ASSUME = re.compile(r"assum[a-z]*[^.\n]{0,120}?\$\s?([\d,]{4,})", re.IGNORECASE)


def invented(text, prompt):
    """Dollar amounts the reply says it assumed that appear nowhere in the question (for a human look)."""
    have = set(re.findall(r"[\d,]{4,}", prompt))
    return [a for a in ASSUME.findall(text or "") if a not in have and a.replace(",", "") not in {h.replace(",", "") for h in have}]


def grade_rec(rec, c):
    got = parse(rec.get("text"))
    g = {"id": c["id"], "family": c["family"], "model": rec["model"], "tools": bool(rec.get("tool_calls") is not None), "rep": rec.get("rep", 0)}
    if rec.get("error"):
        g["bucket"] = "error"
        return g
    if rec.get("stop_reason") == "refusal":
        g["bucket"] = "refusal"
    elif rec.get("stop_reason") in ("max_tokens", "length", "tool_turn_limit") and not got.get("pick") and not got.get("plan"):
        g["bucket"] = "truncated"
    elif not got.get("pick") and not got.get("plan") and c["family"] != "trap":
        g["bucket"] = "no_answer"
    right, lost, why = grade_decision(c, got)
    g["decision"] = {"right": right, "lost": lost, "why": why}
    g["numbers"] = {}
    for k, n in c["numbers"].items():
        v = got.get(k)
        ok = v is not None and abs(v - n["value"]) <= n["tol"]
        g["numbers"][k] = {"got": v, "key": n["value"], "right": ok, "shortcut": None if ok or v is None else shortcut_name(v, n)}
    if c["family"] == "trap":
        g["great"] = right
    else:
        g["great"] = right and all(x["right"] for x in g["numbers"].values())
    g.setdefault("bucket", "great" if g["great"] else "wrong")
    if g["tools"]:
        g["why_wrong"] = {}
        if not right and c["family"] != "trap":
            g["why_wrong"]["decision"] = classify(rec, c, "decision")
        for k, x in g["numbers"].items():
            if not x["right"]:
                g["why_wrong"][k] = classify(rec, c, k, c["numbers"][k])
    g["invented"] = invented(rec.get("text"), c["prompt"])
    return g


# ---- Report ---------------------------------------------------------------------------------------------------

def pct(k, n):
    if not n:
        return "–"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.0f}% ({100 * lo:.0f}–{100 * hi:.0f})"


def report(run, graded, recs):
    lines = [f"# Gauntlet: {run}", ""]
    by_model = defaultdict(list)
    for g in graded:
        if g["bucket"] != "error":
            by_model[(g["model"], g["tools"])].append(g)
    lines += ["| Model | Engine | Asked | Great | Decision right | Numbers right | Traps declined | False declines | Median $ lost on wrong picks |",
              "|---|---|---|---|---|---|---|---|---|"]
    for (m, tools), gs in sorted(by_model.items()):
        real = [g for g in gs if g["family"] != "trap"]
        traps = [g for g in gs if g["family"] == "trap"]
        nums = [x for g in real for x in g["numbers"].values()]
        losses = sorted(g["decision"]["lost"] for g in real if not g["decision"]["right"] and g["decision"]["lost"])
        lines.append(f"| {m} | {'with' if tools else 'alone'} | {len(gs)} | {pct(sum(g['great'] for g in gs), len(gs))} | "
                     f"{pct(sum(g['decision']['right'] for g in real), len(real))} | {pct(sum(x['right'] for x in nums), len(nums))} | "
                     f"{sum(g['decision']['right'] for g in traps)}/{len(traps)} | {sum(g['decision']['why'] == 'declined an answerable question' for g in real)} | "
                     f"{money(losses[len(losses) // 2]) if losses else '–'} |")
    lines += ["", "Great = right decision and every number within tolerance (traps: declined). Intervals are 95% Wilson.", ""]

    shortcuts = Counter(x["shortcut"] for g in graded for x in g.get("numbers", {}).values() if x.get("shortcut"))
    if shortcuts:
        lines += ["## Wrong numbers that match a known shortcut", "", "| Shortcut | Times |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in shortcuts.most_common()] + [""]

    tooled = [g for g in graded if g.get("why_wrong")]
    if any(g["tools"] for g in graded):
        kinds = Counter(v for g in tooled for v in g["why_wrong"].values())
        lines += ["## With the engine: why wrong answers were wrong", "",
                  f"Override (the engine showed the right answer and the model went against it): **{kinds['override']}**; "
                  f"possible override (matched on unnamed plans, may be a coincidence): {kinds['possible override']}; "
                  f"mistranslated (wrong inputs to the tools): {kinds['mistranslated']}; never called the tools: {kinds['no_tools']}.", ""]
        overrides = [(g, k) for g in tooled for k, v in g["why_wrong"].items() if v in ("override", "possible override")]
        if overrides:
            lines += ["### Every override", ""]
            for g, k in overrides:
                if k == "decision":
                    lines.append(f"- **{g['id']}** ({g['model']}) decision: {g['decision']['why']}; costs the household {money(g['decision']['lost'] or 0)}")
                else:
                    x = g["numbers"][k]
                    tag = "" if g["why_wrong"][k] == "override" else " (possible: plans not named by letter)"
                    lines.append(f"- **{g['id']}** ({g['model']}) {k}: said {money(x['got'] or 0)}, the engine had shown {money(x['key'])}{tag}")
            lines.append("")

    alone = [g for g in graded if not g["tools"] and g["family"] != "trap" and not g["decision"]["right"] and g["decision"]["lost"]]
    if alone:
        lines += ["## Costliest wrong decisions by a model alone (video candidates)", ""]
        for g in sorted(alone, key=lambda g: -g["decision"]["lost"])[:10]:
            named = ", ".join(f"{k}: {x['shortcut']}" for k, x in g["numbers"].items() if x.get("shortcut"))
            lines.append(f"- **{g['id']}** ({g['model']}): {g['decision']['why']}; costs {money(g['decision']['lost'])}" + (f"; numbers via {named}" if named else ""))
        lines.append("")

    flagged = [g for g in graded if g.get("invented")]
    if flagged:
        lines += ["## For a human look: assumed amounts not in the question", ""] + [f"- {g['id']} ({g['model']}): {', '.join(g['invented'][:5])}" for g in flagged[:30]] + [""]
    return "\n".join(lines) + "\n"


def load_cases(split):
    return {c["id"]: c for c in (json.loads(l) for l in SETS[split].read_text().splitlines() if l.strip())}


CASES = {}


def grade_run(run):
    d = ROOT / "runs" / run
    meta = json.loads((d / "meta.json").read_text()) if (d / "meta.json").exists() else {}
    CASES.update(load_cases(meta.get("split", "public")))
    recs = [json.loads(l) for l in (d / "raw.jsonl").read_text().splitlines() if l.strip()]
    graded = [grade_rec(r, CASES[r["id"]]) for r in recs if r["id"] in CASES]
    (d / "gauntlet_graded.jsonl").write_text("".join(json.dumps(g) + "\n" for g in graded))
    (d / "GAUNTLET.md").write_text(report(run, graded, recs))
    return graded


if __name__ == "__main__":
    for run in sys.argv[1:]:
        graded = grade_run(run)
        print((ROOT / "runs" / run / "GAUNTLET.md").read_text().split("\n## ")[0])
