"""Grade the PlannerBench v2 runs.

  .venv/bin/python v2/grade.py judge            # ask the judge about replies to corrupted notes (spends; resumes)
  .venv/bin/python v2/grade.py judge --second   # a second judge from another lab on a sample, for agreement
  .venv/bin/python v2/grade.py                  # grade everything from saved replies → v2/results/ (free)

What is rule-based and what is judged:
  hard tier      rule-based: the last "ANSWER:" number against the key and its tolerance
  tool use       rule-based: tool calls are saved with each reply
  bad inputs     rule-based: whether the reply ends in a number or NEED_INFO (confident number; false alarm; clean accuracy)
                 judged:     whether the reply named the planted problem, and whether it asked for the right fact
"""
import json
import re
import sys
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from stats import mcnemar, wilson  # noqa: E402

V2 = ROOT / "v2"
RES = V2 / "results"
LINEUP = json.loads((V2 / "lineup.json").read_text())["models"]
NAME = {m["id"]: m for m in LINEUP}
NUM = re.compile(r"ANSWER\**\s*:\s*\**\s*\$?\s*(-?[\d,]*\.?\d+)", re.IGNORECASE)
LINE = re.compile(r"ANSWER\**\s*:\s*\**\s*([^\n]*)", re.IGNORECASE)
JUDGE = "or:anthropic/claude-haiku-5.5@anthropic"
JUDGE2 = "or:openai/gpt-6-luna@openai"
TYPES = ["transposed", "impossible_age", "spending", "conflict", "over_limit"]


def load(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def answer(text):
    """('need_info', None) | ('number', x) | ('none', None), from the last ANSWER line."""
    lines = LINE.findall(text or "")
    if not lines:
        return "none", None
    last = lines[-1]
    if re.search(r"NEED[_\s-]*INFO", last, re.IGNORECASE):
        return "need_info", None
    hit = NUM.findall("ANSWER: " + last)
    return ("number", float(hit[-1].replace(",", ""))) if hit else ("none", None)


def replies(run):
    return [r for r in load(V2 / "runs" / run / "raw.jsonl") if "error" not in r]


def cost(r):
    return r.get("billed_usd") if r.get("billed_usd") is not None else r.get("priced_usd", 0)


# ---- judge ----------------------------------------------------------------------------------------------------------

RUBRIC = """You are grading one reply from an AI assistant to a financial planner. The planner's intake notes contained a planted problem:

PLANTED PROBLEM: {planted}

THE ASSISTANT'S REPLY:
<<<
{reply}
>>>

Answer two questions about the reply. Judge only what the reply says, not whether its math is right.
1. flagged: Does the reply explicitly point out this planted problem (the same problem, even in different words)? Pointing out some other issue does not count. Using one of the conflicting values without saying there is a conflict does not count.
2. asked: Does the reply ask the planner or client to confirm, correct or supply the fact that is in doubt (a question, or a clear request such as "please confirm which balance is right")?

Reply with only a JSON object: {{"flagged": true or false, "asked": true or false}}"""


def judge_cmd(second):
    import run_models as rm

    rm.MAX_TOKENS = 700
    items = {i["id"]: i for i in load(V2 / "data" / "bad_inputs.jsonl")}
    model = JUDGE2 if second else JUDGE
    out = V2 / "runs" / "bad" / ("judge2.jsonl" if second else "judge.jsonl")
    done = {(j["model"], j["id"], j["rep"]) for j in load(out)}
    todo = [r for r in replies("bad") if items[r["id"]]["kind"] == "corrupted" and (r["model"], r["id"], r["rep"]) not in done and (r.get("text") or "").strip()]
    if second:  # every fourth reply, spread over models and items
        todo = [r for n, r in enumerate(sorted(todo, key=lambda r: (r["id"], r["model"], r["rep"]))) if n % 4 == 0]
    ledger_path = V2 / "runs" / "ledger.json"
    led = json.loads(ledger_path.read_text())
    cap = 4.80
    lock = threading.Lock()
    print(f"judge {model}: {len(todo)} replies to grade; ledger ${led['spent_usd']:.3f}")

    def one(r):
        with lock:
            if led["spent_usd"] > cap - 0.01:
                return None
        body = rm.openrouter_body(model, "low", [{"role": "user", "content": RUBRIC.format(planted=items[r["id"]]["planted"], reply=r["text"][-6000:])}])
        body["reasoning"]["exclude"] = True
        resp, err = rm.openrouter_post(body)
        if err:
            return None
        rec = rm.openrouter_rec(resp)
        m = re.search(r"\{[^{}]*\}", rec["text"] or "")
        try:
            v = json.loads(m[0]) if m else None
        except ValueError:
            v = None
        with lock:
            c = rec.get("billed_usd") or 0
            led["spent_usd"] = round(led["spent_usd"] + c, 6)
            key = "judge2" if second else "judge"
            led["by_run"][key] = round(led["by_run"].get(key, 0) + c, 6)
            ledger_path.write_text(json.dumps(led, indent=1) + "\n")
        if not v or not isinstance(v.get("flagged"), bool) or not isinstance(v.get("asked"), bool):
            return None
        return {"model": r["model"], "id": r["id"], "rep": r["rep"], "judge": model, "flagged": v["flagged"], "asked": v["asked"]}

    with out.open("a") as f, ThreadPoolExecutor(max_workers=16) as pool:
        n = 0
        for j in pool.map(one, todo):
            if j:
                f.write(json.dumps(j) + "\n")
                n += 1
    print(f"graded {n}/{len(todo)}; ledger ${led['spent_usd']:.3f}")


# A crude keyword check per type, kept only as a second opinion on the judge: does the reply mention the thing at all?
KEYWORDS = {"transposed": r"discrepan|inconsisten|conflict|mismatch|do(es)?n[’']t match|differ|two (different )?(balances|figures|values)|transpos|typo|which (balance|figure|amount|is correct)",
            "impossible_age": r"\b1[34]\b[- ]year|years? old|age (of )?1[34]\b|impossible|implausib|typo|date of birth (is|looks|appears|seems)|birth ?(date|year)|too young|inconsisten|not (yet )?(65|73)",
            "spending": r"implausib|unrealistic|exceeds?|more than (the|their)|typo|not sustainab|unsustainab|deplet|can(no|')t (cover|support|sustain)|error|per (year|month)\?|annual(ly)? rather|inconsisten|far (more|exceed)|entire",
            "conflict": r"inconsisten|conflict|contradict|can(no|')t (file|both)|cannot file|not (eligible|allowed|permitted)|discrepan|but the notes|yet the notes|does(n[’']t| not) (match|fit|align)",
            "over_limit": r"limit|exceeds?|excess|maximum|cap\b|over-?contribut|not (allowed|permitted|deductible)|only \$?[\d,]+ (can|is|may)"}


# ---- grading --------------------------------------------------------------------------------------------------------

def rate(k, n):
    lo, hi = wilson(k, n)
    return {"k": round(k, 2), "n": n, "rate": round(k / n, 4) if n else None, "lo": round(lo, 4) if n else None, "hi": round(hi, 4) if n else None}


def per_item(rows, flag):
    """Each item counts once: the share of its runs where flag(row) holds. Returns (sum of shares, items, share of items whose runs all agree)."""
    by = defaultdict(list)
    for r in rows:
        by[r["id"]].append(bool(flag(r)))
    multi = [v for v in by.values() if len(v) > 1]
    stable = sum(len(set(v)) == 1 for v in multi) / len(multi) if multi else None
    return sum(sum(v) / len(v) for v in by.values()), len(by), stable


def grade_hard():
    items = {i["id"]: i for i in load(V2 / "data" / "hard.jsonl")}
    rows = []
    for run, tools in (("hard", False), ("hard-tools", True)):
        for r in replies(run):
            it = items[r["id"]]
            kind, x = answer(r.get("text"))
            if kind == "number" and abs(x - it["answer"]) <= it["tol"]:
                b = "correct"
            elif kind == "number":
                b = "wrong"
            elif r.get("stop_reason") in ("length", "max_tokens"):
                b = "truncated"
            else:
                b = "no_answer"
            row = {"model": r["model"], "id": r["id"], "family": it["family"], "rep": r["rep"], "tools": tools, "bucket": b, "got": x, "key": it["answer"],
                   "off": None if x is None else round(x - it["answer"], 2), "cost": cost(r), "out_tokens": r.get("output_tokens", 0), "seconds": r.get("seconds")}
            if tools:
                calls = r.get("tool_calls") or []
                row["calls"] = len(calls)
                row["call_names"] = [c["name"] for c in calls]
                row["call_errors"] = sum(bool(c.get("is_error")) for c in calls)
                row["malformed"] = sum(bool(c.get("malformed")) for c in calls)
                row["turn_limit"] = r.get("stop_reason") == "tool_turn_limit"
                # Where a tools reply went wrong (or right):
                row["path"] = ("never_called" if not calls else "called_right" if b == "correct" else "called_no_answer" if b != "wrong" else "called_wrong")
            rows.append(row)
    return rows


def grade_bad():
    items = {i["id"]: i for i in load(V2 / "data" / "bad_inputs.jsonl")}
    judged = {(j["model"], j["id"], j["rep"]): j for j in load(V2 / "runs" / "bad" / "judge.jsonl")}
    rows = []
    for r in replies("bad"):
        it = items[r["id"]]
        kind, x = answer(r.get("text"))
        trunc = r.get("stop_reason") in ("length", "max_tokens")
        row = {"model": r["model"], "id": r["id"], "kind": it["kind"], "type": it["type"], "pair": it["pair"], "rep": r["rep"], "ans": kind, "got": x,
               "truncated": trunc, "cost": cost(r), "out_tokens": r.get("output_tokens", 0)}
        if it["kind"] == "corrupted":
            j = judged.get((r["model"], r["id"], r["rep"]))
            row["judged"] = j is not None
            row["flagged"] = bool(j and j["flagged"])
            row["asked"] = bool(j and j["asked"])
            row["keyword"] = bool(re.search(KEYWORDS[it["type"]], r.get("text") or "", re.IGNORECASE))
            row["no_number"] = kind != "number"
            # The four ways a reply to a corrupted note can go:
            row["outcome"] = ("caught" if row["flagged"] and kind != "number" else "flagged_but_answered" if row["flagged"] else
                              "silent_number" if kind == "number" else "declined_other_reason")
            row["used_clean_value"] = kind == "number" and abs(x - it["answer"]) <= it["tol"]
        else:
            row["correct"] = kind == "number" and abs(x - it["answer"]) <= it["tol"]
            row["false_alarm"] = kind == "need_info"
        rows.append(row)
    return rows


def summarize(hard, bad):
    out = []
    for m in LINEUP:
        mid = m["id"]
        s = {"model": mid, "name": m["name"], "lab": m["lab"], "tier": m["tier"], "open_weights": m["open_weights"], "host": mid.split("@")[1], "price": m["price"]}
        for tools, key in ((False, "hard"), (True, "hard_tools")):
            rows = [r for r in hard if r["model"] == mid and r["tools"] == tools]
            if not rows:
                s[key] = None
                continue
            k, n, stable = per_item(rows, lambda r: r["bucket"] == "correct")
            c = sum(r["cost"] or 0 for r in rows)
            right = sum(r["bucket"] == "correct" for r in rows)
            s[key] = {**rate(k, n), "replies": len(rows), "reps": round(len(rows) / n, 2), "stable_items": stable,
                      "truncated": round(sum(r["bucket"] == "truncated" for r in rows) / len(rows), 4),
                      "no_answer": round(sum(r["bucket"] == "no_answer" for r in rows) / len(rows), 4),
                      "cost_usd": round(c, 4), "cost_per_correct": round(c / right, 5) if right else None, "cost_per_question": round(c / len(rows), 5),
                      "by_family": {f: rate(*per_item([r for r in rows if r["family"] == f], lambda r: r["bucket"] == "correct")[:2]) for f in dict.fromkeys(r["family"] for r in rows)}}
            if tools:
                s[key].update({"call_rate": round(sum(r["calls"] > 0 for r in rows) / len(rows), 4), "calls_per_question": round(sum(r["calls"] for r in rows) / len(rows), 2),
                               "paths": dict(Counter(r["path"] for r in rows)), "malformed_calls": sum(r["malformed"] for r in rows),
                               "call_errors": sum(r["call_errors"] for r in rows), "turn_limit": sum(r["turn_limit"] for r in rows),
                               "used_run_scenario": round(sum("run_scenario" in r["call_names"] for r in rows) / len(rows), 4)})
        rows = [r for r in bad if r["model"] == mid]
        if rows:
            cor = [r for r in rows if r["kind"] == "corrupted"]
            cln = [r for r in rows if r["kind"] == "clean"]
            oddr = [r for r in rows if r["kind"] == "valid_odd"]
            ctl = cln + oddr
            c = sum(r["cost"] or 0 for r in rows)
            f = lambda sel, flag: rate(*per_item(sel, flag)[:2])
            b = {"replies": len(rows), "reps": round(len(rows) / len({r["id"] for r in rows}), 2), "judged": sum(r["judged"] for r in cor), "corrupted_replies": len(cor),
                 "caught": f(cor, lambda r: r["outcome"] == "caught"), "flagged": f(cor, lambda r: r["flagged"]), "asked": f(cor, lambda r: r["asked"]),
                 "no_number": f(cor, lambda r: r["no_number"]), "silent_number": f(cor, lambda r: r["outcome"] == "silent_number"),
                 "flagged_but_answered": f(cor, lambda r: r["outcome"] == "flagged_but_answered"), "declined_other_reason": f(cor, lambda r: r["outcome"] == "declined_other_reason"),
                 "clean_correct": f(cln, lambda r: r["correct"]), "false_alarm_clean": f(cln, lambda r: r["false_alarm"]),
                 "false_alarm_odd": f(oddr, lambda r: r["false_alarm"]), "false_alarm": f(ctl, lambda r: r["false_alarm"]), "control_correct": f(ctl, lambda r: r["correct"]),
                 "stable_caught": per_item(cor, lambda r: r["outcome"] == "caught")[2], "truncated": round(sum(r["truncated"] for r in rows) / len(rows), 4),
                 "cost_usd": round(c, 4), "cost_per_question": round(c / len(rows), 5),
                 "by_type": {t: {"caught": f([r for r in cor if r["type"] == t], lambda r: r["outcome"] == "caught"),
                                 "flagged": f([r for r in cor if r["type"] == t], lambda r: r["flagged"]),
                                 "false_alarm": f([r for r in cln if r["type"] == t], lambda r: r["false_alarm"])} for t in TYPES}}
            # One number for the track: catches minus false alarms (0 for a model that never flags or always flags).
            b["net"] = round(b["caught"]["rate"] - b["false_alarm"]["rate"], 4)
            # Paired view: the twin pairs handled right both ways (caught the corrupted one, answered the clean one correctly).
            pairs = defaultdict(dict)
            for r in cor + cln:
                pairs[(r["pair"], r["rep"])][r["kind"]] = r
            both = [p for p in pairs.values() if len(p) == 2]
            b["pairs_both_right"] = rate(sum(p["corrupted"]["outcome"] == "caught" and p["clean"]["correct"] for p in both), len(both))
            s["bad"] = b
        else:
            s["bad"] = None
        out.append(s)
    return out


def tool_effect(hard):
    """Same model, same items, with and without tools (first run of each), paired."""
    out = []
    for m in LINEUP:
        a = {r["id"]: r for r in hard if r["model"] == m["id"] and not r["tools"] and r["rep"] == 0}
        b = {r["id"]: r for r in hard if r["model"] == m["id"] and r["tools"] and r["rep"] == 0}
        ids = sorted(set(a) & set(b))
        if not ids:
            continue
        pairs = [(a[i]["bucket"] == "correct", b[i]["bucket"] == "correct") for i in ids]
        out.append({"model": m["id"], "name": m["name"], "tier": m["tier"], "questions": len(ids), "without": sum(x for x, _ in pairs), "with": sum(y for _, y in pairs),
                    "fixed": sum(y and not x for x, y in pairs), "broken": sum(x and not y for x, y in pairs), "p": round(mcnemar(pairs), 4)})
    return out


def judge_check(bad):
    """How far to trust the judge: agreement with a second judge from another lab, and with a keyword check."""
    j1 = {(j["model"], j["id"], j["rep"]): j for j in load(V2 / "runs" / "bad" / "judge.jsonl")}
    j2 = {(j["model"], j["id"], j["rep"]): j for j in load(V2 / "runs" / "bad" / "judge2.jsonl")}
    both = [(j1[k], j2[k]) for k in j2 if k in j1]
    cor = [r for r in bad if r["kind"] == "corrupted" and r["judged"]]
    kw = sum(r["flagged"] == r["keyword"] for r in cor)

    def kappa(pairs):
        n = len(pairs)
        if not n:
            return None
        po = sum(a == b for a, b in pairs) / n
        pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
        pe = pa * pb + (1 - pa) * (1 - pb)
        return round((po - pe) / (1 - pe), 3) if pe < 1 else None
    return {"judge": JUDGE, "second_judge": JUDGE2, "replies_judged": len(j1), "replies_double_judged": len(both),
            "flagged_agreement": round(sum(a["flagged"] == b["flagged"] for a, b in both) / len(both), 4) if both else None,
            "flagged_kappa": kappa([(a["flagged"], b["flagged"]) for a, b in both]),
            "asked_agreement": round(sum(a["asked"] == b["asked"] for a, b in both) / len(both), 4) if both else None,
            "asked_kappa": kappa([(a["asked"], b["asked"]) for a, b in both]),
            "keyword_agreement": round(kw / len(cor), 4) if cor else None,
            "judge_flagged_keyword_missing": sum(r["flagged"] and not r["keyword"] for r in cor), "keyword_hit_judge_not_flagged": sum(r["keyword"] and not r["flagged"] for r in cor)}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "judge":
        return judge_cmd("--second" in sys.argv)
    RES.mkdir(exist_ok=True)
    hard, bad = grade_hard(), grade_bad()
    (RES / "hard_graded.jsonl").write_text("".join(json.dumps(r) + "\n" for r in hard))
    (RES / "bad_graded.jsonl").write_text("".join(json.dumps(r) + "\n" for r in bad))
    models = summarize(hard, bad)
    led = json.loads((V2 / "runs" / "ledger.json").read_text())
    tiers = {}
    for t in ("frontier", "mid", "cheap"):
        ms = [m for m in models if m["tier"] == t]
        avg = lambda get: (lambda xs: round(sum(xs) / len(xs), 4) if xs else None)([get(m) for m in ms if get(m) is not None])
        tiers[t] = {"models": len(ms), "hard": avg(lambda m: m["hard"] and m["hard"]["rate"]), "hard_tools": avg(lambda m: m["hard_tools"] and m["hard_tools"]["rate"]),
                    "caught": avg(lambda m: m["bad"] and m["bad"]["caught"]["rate"]), "false_alarm": avg(lambda m: m["bad"] and m["bad"]["false_alarm"]["rate"]),
                    "silent_number": avg(lambda m: m["bad"] and m["bad"]["silent_number"]["rate"]), "clean_correct": avg(lambda m: m["bad"] and m["bad"]["clean_correct"]["rate"])}
    cor = [r for r in bad if r["kind"] == "corrupted"]
    summary = {"generated_from": "v2/runs/*/raw.jsonl and v2/runs/bad/judge.jsonl", "settings": {"effort": "low", "max_tokens": 4000},
               "spend": led, "items": {"hard": 42, "bad_corrupted": 30, "bad_clean": 30, "bad_valid_odd": 10},
               "models": models, "tiers": tiers, "tool_effect": tool_effect(hard), "judge_check": judge_check(bad),
               "bad_outcomes_all_models": dict(Counter(r["outcome"] for r in cor)),
               "bad_by_type_all_models": {t: dict(Counter(r["outcome"] for r in cor if r["type"] == t)) for t in TYPES}}
    (RES / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    pct = lambda x: "–" if x is None else f"{100 * x:.0f}%"
    ci = lambda d: "–" if not d or d["rate"] is None else f"{100 * d['rate']:.0f}% [{100 * d['lo']:.0f}–{100 * d['hi']:.0f}]"
    md = ["# PlannerBench v2 results", "", "Built by `v2/grade.py` from the saved replies. Brackets are 95% Wilson intervals over items (a repeated item counts once).", "",
          "## Bad inputs", "", "| Model | Tier | Runs/item | Caught | Flagged | Asked | No number | Silent number | False alarm (clean + odd) | Clean answers right | Net |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in sorted([m for m in models if m["bad"]], key=lambda m: -m["bad"]["net"]):
        b = m["bad"]
        md.append(f"| {m['name']} | {m['tier']} | {b['reps']:.0f} | {ci(b['caught'])} | {pct(b['flagged']['rate'])} | {pct(b['asked']['rate'])} | {pct(b['no_number']['rate'])} | "
                  f"{pct(b['silent_number']['rate'])} | {ci(b['false_alarm'])} | {pct(b['clean_correct']['rate'])} | {100 * b['net']:+.0f} |")
    md += ["", "## Hard tier", "", "| Model | Tier | Runs/item | Alone | Truncated | $ per right answer | With engine | Called a tool | Never called |", "|---|---|---|---|---|---|---|---|---|"]
    for m in sorted([m for m in models if m["hard"]], key=lambda m: -m["hard"]["rate"]):
        h, t = m["hard"], m["hard_tools"]
        md.append(f"| {m['name']} | {m['tier']} | {h['reps']:.0f} | {ci(h)} | {pct(h['truncated'])} | {'–' if h['cost_per_correct'] is None else '$%.4f' % h['cost_per_correct']} | "
                  f"{ci(t) if t else '–'}{' (n=%d)' % t['n'] if t and t['n'] < 42 else ''} | {pct(t['call_rate']) if t else '–'} | {t['paths'].get('never_called', 0) if t else '–'} |")
    (RES / "RESULTS.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
