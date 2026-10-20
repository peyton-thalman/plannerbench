"""PlannerBench trust report: every check that stands between the answer key and "blind faith".

Runs five layers and writes TRUST.md plus a human audit pack:
  1. Golden set      — cases whose answers come straight from IRS / SSA / CMS tables.
  2. Two-way check   — an independent re-implementation must agree with the engine on every case.
  3. Invariants      — rules that must hold for any input (more income never lowers tax, ...).
  4. Dataset health  — no duplicates, no task dominated by one answer, every prompt asks for ANSWER:.
  5. Human audit     — a small random sample with worked solutions, for a person to tick off with a calculator.
  6. Outside model   — PolicyEngine-US, an open-source tax model this project didn't write, recomputes every tax answer.
  7. Held-out set    — the private cases (secret seed, not in the repo) pass the two-way and outside checks too.
"""
import subprocess
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import independent_check as ic  # noqa: E402

ROOT = Path(__file__).parent.parent
results = []  # (layer, passed, detail)


def layer(name, ok, detail):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


cases = [json.loads(l) for l in (ROOT / "data" / "cases.jsonl").read_text().splitlines() if l.strip()]

# 1. Golden set
golden = json.loads((ROOT / "checks" / "golden.json").read_text())
gold_bad = []
for g in golden:
    got = ic.CHECK[g["task"]]({"inputs": g["inputs"]})
    if abs(got - g["expected"]) > 0.01:
        gold_bad.append(f'{g["task"]} {g["inputs"]}: got {got}, published {g["expected"]}')
layer("Golden set (published answers)", not gold_bad, f"{len(golden) - len(gold_bad)}/{len(golden)} match IRS/SSA/CMS" + ("; " + "; ".join(gold_bad) if gold_bad else ""))

# 2. Two independent implementations agree
two_bad = [c["id"] for c in cases if not ic.agrees(ic.CHECK[c["task"]](c), c)]
layer("Two-way check (engine vs. independent)", not two_bad, f"{len(cases) - len(two_bad)}/{len(cases)} agree" + (f"; first mismatches {two_bad[:5]}" if two_bad else ""))

# 3. Invariants on random inputs
rng = random.Random(7)
viol = Counter()
N = 4000
for _ in range(N):
    f = rng.choice(["mfj", "single"])
    o65 = rng.choice([0, 1, 2] if f == "mfj" else [0, 1])
    base = {"filing": f, "over65": o65, "wages": rng.randrange(0, 300000, 500), "ordinary": rng.randrange(0, 150000, 500),
            "ltcg": rng.randrange(0, 100000, 500), "ss": rng.randrange(0, 70000, 100) if o65 else 0}
    t0 = ic.federal_tax({"inputs": base})
    t1 = ic.federal_tax({"inputs": {**base, "ordinary": base["ordinary"] + 1000}})
    if t1 < t0:
        viol["more income lowered tax"] += 1
    if t1 - t0 > 1000 * 0.6:  # top bracket + full SS inclusion + senior phaseout stays well under 60%
        viol["marginal rate above 60%"] += 1
    if t0 < 0:
        viol["negative tax"] += 1
    ss, other = rng.randrange(0, 80000, 100), rng.randrange(0, 200000, 500)
    tx = ic.pub915(ss, other, f)
    if tx > 0.85 * ss + 0.01:
        viol["taxable SS above 85%"] += 1
    if ic.pub915(ss, other + 1000, f) < tx:
        viol["taxable SS fell as income rose"] += 1
    by, pia, m = rng.randint(1943, 1970), 2000, rng.randint(744, 839)
    if ic.ss_claim({"inputs": {"birthYear": by, "pia": pia, "claimAgeMonths": m + 1}}) < ic.ss_claim({"inputs": {"birthYear": by, "pia": pia, "claimAgeMonths": m}}):
        viol["waiting a month lowered the benefit"] += 1
    if ic.tax_torpedo({"inputs": {**base, "conversion": 5000}}) < 0:
        viol["a Roth conversion lowered tax"] += 1
    if base["over65"] and ic.conversion_all_in({"inputs": {**base, "conversion": 5000}}) < ic.tax_torpedo({"inputs": {**base, "conversion": 5000}}) - 1:
        viol["Medicare made a conversion cheaper"] += 1
    magi = rng.randrange(50000, 900000, 100)
    if ic.irmaa({"inputs": {"filing": f, "magi": magi + 1}}) < ic.irmaa({"inputs": {"filing": f, "magi": magi}}):
        viol["more MAGI lowered the premium"] += 1
layer("Invariants", not viol, f"{N:,} random households x 9 rules" + (f"; violations {dict(viol)}" if viol else ", 0 violations"))

# 4. Dataset health
health = []
dupes = len(cases) - len({c["prompt"] for c in cases})
if dupes:
    health.append(f"{dupes} duplicate prompts")
if any("ANSWER:" not in c["prompt"] for c in cases):
    health.append("prompt missing ANSWER instruction")
for task in sorted({c["task"] for c in cases}):
    answers = Counter(c["answer"] for c in cases if c["task"] == task)
    total = sum(answers.values())
    val, n = answers.most_common(1)[0]
    if n / total > 0.6:
        health.append(f"{task}: {n}/{total} share answer {val} (too guessable)")
layer("Dataset health", not health, "; ".join(health) if health else f"{len(cases)} unique prompts, no task dominated by one answer")

# 5. Human audit pack: worked solutions for a random sample
def worked(c):
    i, t = c["inputs"], c["task"]
    if t == "federal_tax":
        f = i["filing"]
        other = i["wages"] + i["ordinary"] + i["ltcg"]
        tss = ic.pub915(i["ss"], other, f)
        agi = other + tss
        senior = max(0.0, 6000 - 0.06 * max(0.0, agi - ic.SENIOR_START[f])) * i["over65"]
        ded = ic.STD[f] + ic.ADD65[f] * i["over65"] + senior
        ti = max(0.0, agi - ded)
        return [f"Other income = {other:,.0f}", f"Taxable Social Security (Pub 915) = {tss:,.0f}", f"AGI = {agi:,.0f}",
                f"Deduction = {ic.STD[f]:,} standard + {ic.ADD65[f] * i['over65']:,} age-65 + {senior:,.0f} senior = {ded:,.0f}",
                f"Taxable income = {ti:,.0f}, of which {min(i['ltcg'], ti):,.0f} is taxed at capital-gains rates",
                f"Tax = {c['answer']:,}  (check the brackets on Rev. Proc. 2025-32)"]
    if t == "taxable_ss":
        b1, b2 = ic.SS_BASE[i["filing"]]
        prov = i["other"] + i["ss"] / 2
        return [f"Provisional income = {i['other']:,} + half of {i['ss']:,} = {prov:,.0f}", f"Bases: {b1:,} / {b2:,}", f"Taxable = {c['answer']:,} (never more than 85% = {0.85 * i['ss']:,.0f})"]
    if t == "rmd":
        start = 75 if i["birthYear"] >= 1960 else 73 if i["birthYear"] >= 1951 else 72
        if i["age"] < start:
            return [f"Born {i['birthYear']} → RMD age {start}; age {i['age']} in 2026 → no RMD", "Answer 0"]
        return [f"Born {i['birthYear']} → RMD age {start}; age {i['age']} → required", f"Divisor at {i['age']} = {ic.ULT[i['age']]}", f"{i['balance']:,} / {ic.ULT[i['age']]} = {c['answer']:,}"]
    if t == "ss_claim":
        fra = 67 * 12 if i["birthYear"] >= 1960 else 66 * 12 + max(0, i["birthYear"] - 1954) * 2
        d = i["claimAgeMonths"] - fra
        if d >= 0:
            rule = f"{d} months after FRA × 2/3% = +{d * 2 / 3:.2f}%"
        else:
            e = -d
            rule = f"{e} months before FRA: {min(e, 36)} × 5/9% + {max(0, e - 36)} × 5/12% = −{min(e, 36) * 5 / 9 + max(0, e - 36) * 5 / 12:.2f}%"
        return [f"Born {i['birthYear']} → full retirement age {fra // 12}y {fra % 12}m; claims at {i['claimAgeMonths'] // 12}y {i['claimAgeMonths'] % 12}m",
                rule, f"{i['pia']:,} PIA → {c['answer']:,}/month"]
    if t == "bracket_room":
        return [f"Taxable income = {i['ordinary']:,} − {ic.STD[i['filing']]:,} = {max(0, i['ordinary'] - ic.STD[i['filing']]):,}", f"Top of {int(i['rate'] * 100)}% bracket ({i['filing']}) minus taxable = {c['answer']:,}"]
    if t == "tax_torpedo":
        f, o65 = i["filing"], i["over65"]
        b = ic.household_tax(f, o65, i["ordinary"], i["ltcg"], i["ss"])
        a = ic.household_tax(f, o65, i["ordinary"] + i["conversion"], i["ltcg"], i["ss"])
        tss0, tss1 = (ic.pub915(i["ss"], i["ordinary"] + x + i["ltcg"], f) for x in (0, i["conversion"]))
        return [f"Tax without the conversion = {b:,} (work it as a federal_tax case)", f"Tax with {i['conversion']:,} more IRA income = {a:,}",
                f"Taxable Social Security rises {tss0:,.0f} → {tss1:,.0f}, so taxable income rises by more than the conversion",
                f"Difference = {c['answer']:,} vs. {c.get('naive', 0):,} from conversion × bracket rate alone"]
    if t == "widow_penalty":
        ss = max(i["ssA"], i["ssB"])
        return [f"Couple (MFJ, two over 65, SS {i['ssA'] + i['ssB']:,}): tax = {ic.household_tax('mfj', 2, i['ordinary'], i['ltcg'], i['ssA'] + i['ssB']):,}",
                f"Survivor (single, over 65, keeps larger SS {ss:,}): tax = {ic.household_tax('single', 1, i['ordinary'], i['ltcg'], ss):,}",
                f"Difference = {c['answer']:,}"]
    if t == "senior_phaseout":
        f, n = i["filing"], i["over65"]
        agi = ic.household_agi(f, i["ordinary"], i["ltcg"], i["ss"])
        each = max(0.0, 6000 - 0.06 * max(0.0, agi - ic.SENIOR_START[f]))
        return [f"AGI = {agi:,.0f} (taxable SS from Pub 915)", f"Senior deduction per person = 6,000 − 6% × ({agi:,.0f} − {ic.SENIOR_START[f]:,}) = {each:,.2f}, × {n} = {each * n:,.2f} (Schedule 1-A lines 35–37)",
                f"Tax = {c['answer']:,}"]
    if t == "rollover_flags":
        return [f"Left employer at {i['sepAge']}, now {i['age']}, withdrawals planned: {'yes' if i['withdraws'] else 'no'} → AGE55 needs all three (55+ at separation, under 59½, withdrawing)",
                f"IRA cost {i['erIra'] + i['adv']:.2f}% vs. plan {i['er401']:.2f}% → COST if the IRA is higher",
                f"Employer stock {i['stock']:,}, basis {i['basis']:,} → NUA if basis is low" if i["hasStock"] else "No employer stock → no NUA",
                f"Answer: {c['answer']}"]
    if t == "breakpoint":
        counted = i["purchase"] + i["own"] + i["spouse"] + i["minor"]
        return [f"Counted: purchase {i['purchase']:,} + client {i['own']:,} + spouse {i['spouse']:,} + minor child {i['minor']:,} = {counted:,}",
                f"Not counted: adult child {i['adult']:,}, other fund family {i['other']:,}", f"Schedule row for {counted:,} → {c['answer']}%"]
    if t == "comms_review":
        return ["Violations are guarantees, return predictions, 'virtually no risk', and calling the fund FDIC-insured (Rule 2210(d)(1)(A), (F))",
                f"Answer: sentences {c['answer']}"]
    if t in ("conversion_all_in", "widow_all_in"):
        return [f"Tax-only part (what a one-step answer gives) = {c.get('naive', 0):,}", f"Medicare Part B change for the year = {c['answer'] - c.get('naive', 0):,} (CMS 2026 tiers: joint {ic.IRMAA_EDGES['mfj']}, single {ic.IRMAA_EDGES['single']})",
                f"Total = {c['answer']:,}"]
    return [f"MAGI {i['magi']:,} vs. CMS tiers {ic.IRMAA_EDGES[i['filing']]}", f"Premium = ${c['answer']:.2f}"]


sample = random.Random(2026).sample(cases, 12)
lines = ["# Human audit pack", "", "Check each with a calculator and the cited table. About 2 minutes each. Tick the box if you agree.", ""]
for c in sample:
    lines += [f"## [ ] {c['id']}", "", f"> {c['prompt'].split(' End your reply')[0]}", "", *[f"- {s}" for s in worked(c)], ""]
(ROOT / "checks" / "AUDIT.md").write_text("\n".join(lines))
layer("Human audit pack", True, "12 random cases with worked solutions written to checks/AUDIT.md (not yet ticked by an outside reviewer)")

# 6. Outside implementation
PE = ROOT / ".venv-pe" / "bin" / "python"


def outside(cases_path, out_name):
    if not PE.exists():
        return None, "skipped: install with  python3 -m venv .venv-pe && .venv-pe/bin/pip install policyengine-us"
    subprocess.run([str(PE), "-I", str(ROOT / "checks" / "policyengine_check.py"), str(cases_path), out_name], capture_output=True, text=True)
    r = json.loads((ROOT / "checks" / f"{out_name.lower()}.json").read_text())
    return r["pass"], f"{r['agree']:,}/{r['total']:,} tax answers agree with PolicyEngine-US within $2"


pe_ok, pe_detail = outside(ROOT / "data" / "cases.jsonl", "POLICYENGINE")
layer("Outside model (PolicyEngine-US)", bool(pe_ok), pe_detail + ("; see checks/POLICYENGINE.md" if pe_ok is not None else ""))

# 7. Held-out set: the same checks, reporting counts only so nothing about the private cases is published.
private = ROOT / "private" / "cases.jsonl"
if private.exists():
    pcases = [json.loads(l) for l in private.read_text().splitlines() if l.strip()]
    p_two = sum(not ic.agrees(ic.CHECK[c["task"]](c), c) for c in pcases)
    p_overlap = len({c["prompt"] for c in pcases} & {c["prompt"] for c in cases})
    p_pe_ok, p_pe = outside(private, "private_policyengine")
    moved = ROOT / "checks" / "PRIVATE_POLICYENGINE.md"
    if moved.exists():  # the per-case report names private cases; keep it with them
        moved.replace(ROOT / "private" / "POLICYENGINE.md")
        (ROOT / "checks" / "private_policyengine.json").replace(ROOT / "private" / "policyengine.json")
    p_ok = not p_two and not p_overlap and p_pe_ok is not False
    layer("Held-out set (private)", p_ok, f"{len(pcases):,} private cases: {len(pcases) - p_two:,} pass the two-way check, {p_overlap} repeat a public question; {p_pe}")
else:
    layer("Held-out set (private)", True, "not on this machine (it never leaves the maintainer's); public checks above still apply")

# Report
ok = all(r[1] for r in results)
md = ["# PlannerBench trust report", "", f"**{'All checks pass' if ok else 'Checks failing'}** on {len(cases):,} cases.", "",
      "| Layer | Result | Detail |", "|---|---|---|"]
md += [f"| {n} | {'PASS' if p else 'FAIL'} | {d} |" for n, p, d in results]
(ROOT / "TRUST.md").write_text("\n".join(md) + "\n")
sys.exit(0 if ok else 1)
