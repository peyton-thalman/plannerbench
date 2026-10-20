"""Independent answer check for PlannerBench.

Written separately from the TypeScript engine, straight from the published rules, so the benchmark's
answer key is never graded by the same code that produced it. Any disagreement fails the build.

Sources: IRS Rev. Proc. 2025-32 (2026 brackets, deductions), P.L. 119-21 sec. 70103 (senior deduction),
IRS Pub 915 worksheet, IRS Pub 590-B Table III, SSA POMS RS 00615.101/.102 (reduction and delayed credits),
CMS 2026 Part B premium fact sheet (IRMAA tiers; top tier is "greater than or equal to").
"""
import json
import sys
from pathlib import Path

ORD = {
    "mfj": [(24800, .10), (100800, .12), (211400, .22), (403550, .24), (512450, .32), (768700, .35), (float("inf"), .37)],
    "single": [(12400, .10), (50400, .12), (105700, .22), (201775, .24), (256225, .32), (640600, .35), (float("inf"), .37)],
}
CG = {"mfj": [(98900, 0), (613700, .15), (float("inf"), .20)], "single": [(49450, 0), (545500, .15), (float("inf"), .20)]}
STD = {"mfj": 32200, "single": 16100}
ADD65 = {"mfj": 1650, "single": 2050}
SENIOR_START = {"mfj": 150000, "single": 75000}
NIIT_START = {"mfj": 250000, "single": 200000}
SS_BASE = {"mfj": (32000, 44000), "single": (25000, 34000)}
# Pub 590-B Table III (Uniform Lifetime), ages 72..100.
ULT = {72: 27.4, 73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5,
       83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4, 88: 13.7, 89: 12.9, 90: 12.2}
# The Uniform Lifetime Table in force before 2022 (Treas. Reg. 1.401(a)(9)-9 before the 2020 final regulations),
# kept only to recognize answers that use it.
ULT_PRE2022 = {72: 25.6, 73: 24.7, 74: 23.8, 75: 22.9, 76: 22.0, 77: 21.2, 78: 20.3, 79: 19.5, 80: 18.7, 81: 17.9, 82: 17.1,
               83: 16.3, 84: 15.5, 85: 14.8, 86: 14.1, 87: 13.4, 88: 12.7, 89: 12.0, 90: 11.4}
IRMAA_EDGES = {"mfj": [218000, 274000, 342000, 410000, 750000], "single": [109000, 137000, 171000, 205000, 500000]}
PART_B = [202.90, 284.10, 405.80, 527.50, 649.20, 689.90]


# Known misreadings of the rules. The grader switches one on to recompute what a model that holds it would answer,
# so a wrong answer can be named ("took the senior phase-out once off $12,000") instead of just counted.
MISREAD = set()
MISREADINGS = {"combined_senior_phaseout": "senior deduction phase-out taken once off the couple's $12,000, not off each $6,000",
               "pre2022_rmd_table": "RMD divided by the Uniform Lifetime Table replaced in 2022"}


def answer_if_misread(name, c):
    MISREAD.add(name)
    try:
        return CHECK[c["task"]](c)
    finally:
        MISREAD.discard(name)


def layered(amount, table):
    """Tax on `amount` run through a bracket table."""
    owed, floor = 0.0, 0.0
    for top, rate in table:
        if amount > floor:
            owed += (min(amount, top) - floor) * rate
        floor = top
    return owed


def pub915(ss, other, filing):
    if ss <= 0:
        return 0.0
    line1, line2 = SS_BASE[filing]
    provisional = other + ss / 2
    if provisional <= line1:
        return 0.0
    tier1 = min(provisional - line1, line2 - line1) / 2
    tier1 = min(tier1, ss / 2)
    tier2 = max(0.0, provisional - line2) * 0.85
    return min(0.85 * ss, tier1 + tier2)


def federal_tax(c):
    i = c["inputs"]
    f = i["filing"]
    other = i["wages"] + i["ordinary"] + i["ltcg"]
    agi = other + pub915(i["ss"], other, f)
    excess = 0.06 * max(0.0, agi - SENIOR_START[f])
    if "combined_senior_phaseout" in MISREAD:
        senior = max(0.0, 6000 * i["over65"] - excess)
    else:
        # Schedule 1-A Part V: line 35 takes the 6% off $6,000, and lines 36a/36b give that amount to each qualifying spouse.
        senior = max(0.0, 6000 - excess) * i["over65"]
    deduction = STD[f] + ADD65[f] * i["over65"] + senior
    taxable = max(0.0, agi - deduction)
    ordinary_part = max(0.0, taxable - i["ltcg"])
    gains = taxable - ordinary_part
    tax = layered(ordinary_part, ORD[f])
    # Preferential gains fill the 0/15/20% bands on top of ordinary income.
    tax += layered(ordinary_part + gains, CG[f]) - layered(ordinary_part, CG[f])
    tax += 0.038 * max(0.0, min(i["ltcg"], agi - NIIT_START[f]))
    return round(tax)


def rmd(c):
    i = c["inputs"]
    by = i["birthYear"]
    start = 75 if by >= 1960 else 73 if by >= 1951 else 72
    table = ULT_PRE2022 if "pre2022_rmd_table" in MISREAD else ULT
    return 0 if i["age"] < start else round(i["balance"] / table[i["age"]])


def ss_claim(c):
    i = c["inputs"]
    by = i["birthYear"]
    fra_months = 67 * 12 if by >= 1960 else 66 * 12 + max(0, by - 1954) * 2
    diff = i["claimAgeMonths"] - fra_months
    if diff >= 0:
        factor = 1 + min(diff, 70 * 12 - fra_months) * (2 / 3) / 100
    else:
        early = -diff
        factor = 1 - min(early, 36) * (5 / 9) / 100 - max(0, early - 36) * (5 / 12) / 100
    return round(i["pia"] * factor)


def bracket_room(c):
    i = c["inputs"]
    f = i["filing"]
    taxable = max(0.0, i["ordinary"] - STD[f])
    top = next(t for t, r in ORD[f] if r == i["rate"])
    return round(max(0.0, top - taxable))


def irmaa(c):
    i = c["inputs"]
    edges = IRMAA_EDGES[i["filing"]]
    tier = sum(1 for e in edges[:-1] if i["magi"] > e) + (1 if i["magi"] >= edges[-1] else 0)
    return PART_B[tier]


def household_tax(filing, over65, ordinary, ltcg, ss):
    return federal_tax({"inputs": {"filing": filing, "over65": over65, "wages": 0, "ordinary": ordinary, "ltcg": ltcg, "ss": ss}})


def tax_torpedo(c):
    i = c["inputs"]
    base = (i["filing"], i["over65"])
    return household_tax(*base, i["ordinary"] + i["conversion"], i["ltcg"], i["ss"]) - household_tax(*base, i["ordinary"], i["ltcg"], i["ss"])


def widow_penalty(c):
    i = c["inputs"]
    # Survivor keeps the larger benefit (SSA survivor rules); the smaller one stops.
    return household_tax("single", 1, i["ordinary"], i["ltcg"], max(i["ssA"], i["ssB"])) - household_tax("mfj", 2, i["ordinary"], i["ltcg"], i["ssA"] + i["ssB"])


def household_agi(filing, ordinary, ltcg, ss):
    other = ordinary + ltcg
    return other + pub915(ss, other, filing)


def part_b(magi, filing):
    return irmaa({"inputs": {"filing": filing, "magi": magi}})


def conversion_all_in(c):
    i = c["inputs"]
    f, people = i["filing"], i["over65"]
    o0, o1 = i["ordinary"], i["ordinary"] + i["conversion"]
    tax_up = household_tax(f, people, o1, i["ltcg"], i["ss"]) - household_tax(f, people, o0, i["ltcg"], i["ss"])
    # 2026 MAGI sets 2028 premiums (the two-year lookback), one premium per enrolled spouse.
    medicare_up = 12 * people * (part_b(household_agi(f, o1, i["ltcg"], i["ss"]), f) - part_b(household_agi(f, o0, i["ltcg"], i["ss"]), f))
    return round(tax_up + medicare_up)


def widow_all_in(c):
    i = c["inputs"]
    ss_s, ss_c = max(i["ssA"], i["ssB"]), i["ssA"] + i["ssB"]
    survivor = household_tax("single", 1, i["ordinary"], i["ltcg"], ss_s) + 12 * part_b(household_agi("single", i["ordinary"], i["ltcg"], ss_s), "single")
    couple = household_tax("mfj", 2, i["ordinary"], i["ltcg"], ss_c) + 24 * part_b(household_agi("mfj", i["ordinary"], i["ltcg"], ss_c), "mfj")
    return round(survivor - couple)


# Compliance track. Thresholds are this file's own, chosen inside the generator's gaps, so a generator bug that
# puts a case near the line shows up as a disagreement.
def rollover_flags(c):
    i = c["inputs"]
    codes = []
    if i["sepAge"] >= 55 and i["age"] < 59.5 and i["withdraws"]:  # IRC 72(t)(2)(A)(v), plan-only exception
        codes.append("AGE55")
    if i["erIra"] + i["adv"] > i["er401"]:
        codes.append("COST")
    if i["hasStock"] and i["basis"] <= 0.5 * i["stock"]:
        codes.append("NUA")
    return ",".join(sorted(codes)) or "NONE"


def breakpoint(c):
    i = c["inputs"]
    total = i["purchase"] + i["own"] + i["spouse"] + i["minor"]  # rights of accumulation: client, spouse, children under 21
    for top, rate in [(50000, 5.75), (100000, 4.5), (250000, 3.5), (500000, 2.5), (1000000, 2.0)]:
        if total < top:
            return rate
    return 0.0


# Rule 2210(d)(1) violations, matched by the sentence's own text rather than the generator's labels.
VIOLATIONS = ("guaranteed to outperform", "at least 10% a year", "virtually no risk", "your investment in this fund is FDIC-insured",
              "project the fund will return", "can't-miss")


def comms_review(c):
    lines = [l for l in c["prompt"].split("\n") if l[:1].isdigit() and ". " in l]
    bad = [l.split(". ", 1)[0] for l in lines if any(v in l for v in VIOLATIONS)]
    return ",".join(bad) or "NONE"


def agrees(mine, c):
    """Exact match for code-set answers, within tolerance for numbers."""
    if isinstance(c["answer"], str):
        return mine == c["answer"]
    return abs(mine - c["answer"]) <= c["tol"]


CHECK = {
    "federal_tax": federal_tax,
    "taxable_ss": lambda c: round(pub915(c["inputs"]["ss"], c["inputs"]["other"], c["inputs"]["filing"])),
    "rmd": rmd,
    "ss_claim": ss_claim,
    "bracket_room": bracket_room,
    "irmaa": irmaa,
    "tax_torpedo": tax_torpedo,
    "widow_penalty": widow_penalty,
    "senior_phaseout": lambda c: household_tax(*(c["inputs"][k] for k in ("filing", "over65", "ordinary", "ltcg", "ss"))),
    "conversion_all_in": conversion_all_in,
    "widow_all_in": widow_all_in,
    "rollover_flags": rollover_flags,
    "breakpoint": breakpoint,
    "comms_review": comms_review,
}

if __name__ == "__main__":
    path = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent / "data" / "cases.jsonl")
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    bad = []
    for c in cases:
        mine = CHECK[c["task"]](c)
        if not agrees(mine, c):
            bad.append((c["id"], c["answer"], mine, c["inputs"]))
    by_task = {}
    for c in cases:
        by_task[c["task"]] = by_task.get(c["task"], 0) + 1
    print(f"Checked {len(cases)} cases: {dict(by_task)}")
    for b in bad:
        print(f"  MISMATCH {b[0]}: engine={b[1]} independent={b[2]} inputs={b[3]}")
    print("PASS" if not bad else f"FAIL: {len(bad)} disagreement(s)")
    sys.exit(1 if bad else 0)
