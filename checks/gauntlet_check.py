"""The Gauntlet grader's own test: stand-in "models" whose mistakes are known in advance must land in exactly the
right buckets. Free (no API calls); the tools stand-ins use the real MCP server.

  key            the answer key                                         → 100% great
  tool user      answers read only off real engine tool replies         → 100% great (the tools are enough)
  blank          says nothing                                           → 0% great, no answers
  liar           worst option, every number 10% off                     → 0% great, 0 numbers right
  refuser        declines everything                                    → traps 7/7, every other question a false decline
  lazy           biggest move; tax = income x 22%; Medicare = Part B only → decisions right only where the build said
                                                                          "biggest move" wins; every number named as its shortcut
  overrider      real engine replies in hand, then the worst option and numbers 20% off → every wrong item an override
  mistranslator  calls a tool that can't answer, then the liar's answers → no overrides

Usage: .venv/bin/python -I checks/gauntlet_check.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
import gauntlet_grade as gg  # noqa: E402
from planning_tools import PlanningTools, gauntlet_oracle  # noqa: E402

cases = gg.load_cases("public")
gg.CASES.update(cases)


def text(pick=None, plan=None, numbers=None):
    lines = ["Stand-in."] + ([f"PICK: {pick}"] if pick else []) + ([f"PLAN: {plan[0]} x {plan[1]}"] if plan else [])
    return "\n".join(lines + [f"{k}: {round(v)}" for k, v in (numbers or {}).items()])


def moved(sc):
    return sum(a.get("amount", 0) * len(a.get("years", [])) for a in sc["plans"][0]["actions"])


def worst(c):
    g = c["decision"]["gains"]
    return min(g, key=g.get)


def liar(c, factor=1.1):
    nums = {k: n["value"] * factor for k, n in c["numbers"].items()}
    if c["family"] == "trap":
        return text("A", numbers={"N1": 12345})
    if c["how_much"]:
        return text(plan=(0, 0), numbers=nums)
    return text(worst(c), numbers=nums)


def lazy(c):
    if c["family"] == "trap":
        return text("A", numbers={"N1": 12345})
    nums = {}
    for k, n in c["numbers"].items():
        s = n["shortcuts"]
        nums[k] = s.get("flat_22pct", s.get("part_b_only", n["value"] * 1.5))
    if c["how_much"]:
        return text(plan=(0, 0), numbers=nums)
    most = max(moved(sc) for sc in c["scenarios"].values())
    return text(next(l for l in sorted(c["scenarios"]) if moved(c["scenarios"][l]) == most), numbers=nums)


tools = PlanningTools()
real_calls = {cid: gauntlet_oracle(tools, c) for cid, c in cases.items()}


def wrong_inputs(c):
    """Real engine runs on the wrong facts, what a model that mistranslates sees: IRA balances 50% too high,
    Social Security 30% too high and other income 40% too high (so this year's numbers change, not just the end)."""
    bad = json.loads(json.dumps(c))
    for sc in (bad["scenarios"] or {}).values():
        h = sc["household"]
        for a in h["accounts"]:
            if "ira" in a["type"] or a["type"] == "401k":
                a["balance"] = round(a["balance"] * 1.5)
        for p in h["people"]:
            for k in ("monthly_at_fra", "already_claimed_monthly"):
                if k in (p.get("social_security") or {}):
                    p["social_security"][k] = round(p["social_security"][k] * 1.3)
        for i in h.get("income") or []:
            i["annual"] = round(i["annual"] * 1.4)
    return gauntlet_oracle(tools, bad)


wrong_calls = {cid: wrong_inputs(c) for cid, c in cases.items()}
stand_ins = {
    "key": lambda c: (gg_key(c), None),
    "tool user": lambda c: real_calls[c["id"]],
    "blank": lambda c: ("", None),
    "liar": lambda c: (liar(c), None),
    "refuser": lambda c: ("PICK: CANT", None),
    "lazy": lambda c: (lazy(c), None),
    "overrider": lambda c: (liar(c, 1.2), real_calls[c["id"]][1]),
    "wrong facts": lambda c: (liar(c), wrong_calls[c["id"]][1]),
    "mistranslator": lambda c: (liar(c), [{"name": "tax_tables", "input": {}, "result": tools.call("tax_tables", {"filing": "married_filing_jointly"})[0], "is_error": False}]),
}


def gg_key(c):
    from run_models import ask_fake_gauntlet

    return ask_fake_gauntlet(c)["text"]


results = {}
for name, make in stand_ins.items():
    graded = []
    for c in cases.values():
        t, calls = make(c)
        rec = {"model": name, "id": c["id"], "text": t, "stop_reason": "end_turn"}
        if calls is not None:
            rec["tool_calls"] = calls
        graded.append(gg.grade_rec(rec, c))
    results[name] = graded

fails, log = [], []
def check(ok, msg):
    log.append(("PASS " if ok else "FAIL ") + msg)
    print(log[-1])
    if not ok:
        fails.append(msg)

real = lambda gs: [g for g in gs if g["family"] != "trap"]
n_all, n_real = len(cases), len(real(results["key"]))
check(all(g["great"] for g in results["key"]), f"key: {sum(g['great'] for g in results['key'])}/{n_all} great")
check(all(g["great"] for g in results["tool user"]), f"tool user (real engine replies only): {sum(g['great'] for g in results['tool user'])}/{n_all} great")
check(not any(g["great"] for g in results["blank"]) and all(g["bucket"] == "no_answer" for g in real(results["blank"])), "blank: 0 great, every answerable question no_answer")
liars = results["liar"]
check(not any(g["great"] for g in liars) and not any(x["right"] for g in liars for x in g["numbers"].values()), "liar: 0 great, 0 numbers right")
ref = results["refuser"]
check(sum(g["great"] for g in ref) == n_all - n_real and all(g["decision"]["why"] == "declined an answerable question" for g in real(ref)),
      f"refuser: traps {sum(g['great'] for g in ref)}/{n_all - n_real}, {n_real} false declines")
# The build's own count of how often "biggest move" is right (ties count only if every tied option is right).
expect_lazy = 0
for c in cases.values():
    if c["family"] in ("trap",) or c["how_much"]:
        continue
    most = max(moved(sc) for sc in c["scenarios"].values())
    expect_lazy += all(l in c["decision"]["pick"] for l, sc in c["scenarios"].items() if moved(sc) == most)
lz = [g for g in real(results["lazy"]) if not cases[g["id"]]["how_much"]]
got_lazy = sum(g["decision"]["right"] for g in lz)
# The lazy stand-in breaks ties by letter, so it can do at most as well as "every tied option is right" undercounts.
check(got_lazy >= expect_lazy, f"lazy: decisions right {got_lazy}/{len(lz)} (build's strict count {expect_lazy})")
named = [(x["shortcut"], cases[g["id"]]["numbers"][k]) for g in real(results["lazy"]) for k, x in g["numbers"].items()]
check(all(not x["right"] for g in real(results["lazy"]) for x in g["numbers"].values()), "lazy: every number wrong")
check(all(s in ("flat_22pct", "part_b_only") for s, n in named if "flat_22pct" in n["shortcuts"] or "part_b_only" in n["shortcuts"]),
      f"lazy: every shortcut number named ({sum(s is not None for s, _ in named)}/{len(named)} named)")
ov = [g for g in real(results["overrider"])]
wrong_items = [(g, k) for g in ov for k in g["why_wrong"]]
# Questions that name options get exact overrides; how_much numbers ("if they converted $X") name none, so the best
# the grader can say is "possible override".
lettered = [(g, k) for g, k in wrong_items if k == "decision" or "option" in cases[g["id"]]["numbers"][k]["ask"]]
check(wrong_items and all(g["why_wrong"][k] in ("override", "possible override") for g, k in wrong_items)
      and all(g["why_wrong"][k] == "override" for g, k in lettered),
      f"overrider: {sum(g['why_wrong'][k] in ('override', 'possible override') for g, k in wrong_items)}/{len(wrong_items)} wrong items caught "
      f"({sum(g['why_wrong'][k] == 'override' for g, k in lettered)}/{len(lettered)} exact where the question names options)")
check(all("decision" in g["why_wrong"] for g in ov if len(set(cases[g["id"]]["decision"].get("pick", []))) < len(cases[g["id"]]["scenarios"])),
      "overrider: every wrong pick is in the list")
mt = [v for g in real(results["mistranslator"]) for v in g["why_wrong"].values()]
check(mt and all(v == "mistranslated" for v in mt), f"mistranslator: {mt.count('override')} overrides, {mt.count('mistranslated')} mistranslated")
# Only items where the wrong-facts runs really did give a wrong answer (read the way a perfect tool user reads them)
# can be false alarms; where the wrong facts happen not to change the answer, the engine did show the right one.
false_alarm = []
for g in real(results["wrong facts"]):
    c = cases[g["id"]]
    shown = gg.grade_rec({"model": "x", "id": c["id"], "text": wrong_calls[c["id"]][0], "stop_reason": "end_turn"}, c)
    for k, v in g["why_wrong"].items():
        really_wrong = not shown["decision"]["right"] if k == "decision" else not shown["numbers"][k]["right"]
        if really_wrong:
            false_alarm.append(v == "override")
check(sum(false_alarm) <= 0.05 * len(false_alarm),
      f"wrong facts (real engine runs on wrong inputs): {sum(false_alarm)}/{len(false_alarm)} items the engine got wrong were called overrides (allowed: 5%)")
tools.close()

out = ["# Gauntlet grader check", "", f"{n_all} public questions; stand-ins with known mistakes must land in the right buckets.", ""]
out += [f"- {line}" for line in log] + [""]
(ROOT / "checks" / "GAUNTLET-GRADER.md").write_text("\n".join(out + [("**All checks pass.**" if not fails else f"**{len(fails)} failed:** " + "; ".join(fails))]) + "\n")
sys.exit(1 if fails else 0)
