"""Build the PlannerBench v2 hard tier: 42 questions where retirement rules interact.

Every answer key is read from the Planning Engine (run_scenario over MCP) and must match the clean-room engine
(checks/cleanroom, written from the rules spec alone) to the dollar, or the build fails. Each item carries the
published source of the rules it leans on.

Usage: .venv/bin/python v2/build_hard.py        → v2/data/hard.jsonl and v2/data/HARD.md
"""
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from planning_tools import PlanningTools  # noqa: E402

OUT = ROOT / "v2" / "data" / "hard.jsonl"
TOOLS = PlanningTools()
END = 'End your reply with a line of the form "ANSWER: <number>" with no $ sign or commas.'
LAW = ("Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior "
       "deduction). Standard deduction, no credits.")
# Made-up first names. No persona is a real client.
WOMEN = ["Marisol", "Odette", "Priya", "Wren", "Imani", "Greta", "Noor", "Tamsin", "Leona", "Yuki", "Bianca", "Freya"]
MEN = ["Anders", "Caleb", "Desmond", "Emeric", "Felix", "Gideon", "Hollis", "Ivo", "Jonah", "Kofi", "Lucian", "Mateo"]
IRMAA = {"mfj": [218000, 274000, 342000, 410000, 750000], "single": [109000, 137000, 171000, 205000, 500000]}  # CMS 2026


def money(x):
    return f"${x:,.0f}"


def person(pid, born, ss_monthly=0):
    p = {"id": pid, "born": born, "born_month": 1, "medicare": True}
    if ss_monthly:
        p["social_security"] = {"monthly_at_fra": ss_monthly, "claim_age": 67, "already_claimed_monthly": ss_monthly, "claimed_at_months": 804}
    return p


def scenario(filing, state, people, accounts, income, plans):
    return {"household": {"filing": filing, "state": state, "people": people, "accounts": accounts, "income": income, "spending_need": 1000},
            "plans": plans, "assumptions": {"first_year": 2026, "last_year": 2026}}


def run_both(sc):
    """Year-2026 rows from the Planning Engine and the clean-room engine, one per plan, checked against each other."""
    out, err = TOOLS.call("run_scenario", sc)
    if err:
        raise SystemExit(f"engine rejected the scenario: {out[:400]}")
    ours = [p["years"][0] for p in json.loads(out)["plans"]]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(sc, f)
    r = subprocess.run(["python3", "-I", str(ROOT / "checks/cleanroom/engine.py"), f.name], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"clean-room engine failed: {r.stderr[-400:]}")
    theirs_by_name = json.loads(r.stdout)["plans"]
    theirs = [theirs_by_name[p["name"]]["years"][0] for p in sc["plans"]]
    for a, b in zip(ours, theirs):
        pairs = [(a["federal_tax"], b["federal_tax"]), (a["state_tax"], b["state_tax"]), (a["agi"], b["agi"]),
                 (a["magi_for_irmaa"], b["magi_irmaa"]), (a["taxable_social_security"], b["taxable_ss"]),
                 (a["senior_deduction"], b["senior_deduction"]), (a["rmd"], sum(b["rmd"].values()))]
        for x, y in pairs:
            if abs(x - y) > 1:
                raise SystemExit(f"engines disagree: {x} vs {y}\n{json.dumps(sc)[:600]}")
        for k, v in a.get("rmd_by_account", {}).items():
            if abs(v - b["rmd"].get(k, 0)) > 1:
                raise SystemExit(f"engines disagree on RMD {k}: {v} vs {b['rmd'].get(k)}")
    return ours


ITEMS = []


def add(family, n, prompt, answer, tol, source, sc, note):
    ITEMS.append({"id": f"{family}-{n:02d}", "family": family, "prompt": prompt, "answer": answer, "tol": tol, "source": source,
                  "key_from": "Planning Engine run_scenario, 2026 row; matched by the clean-room engine within $1", "scenario": sc, "note": note})


def couple_text(a, b, ya, yb):
    return f"{a} (born January {ya}) and {b} (born January {yb}) are married, file jointly and are both enrolled in Medicare Part B"


def irmaa_headroom(rng, n):
    """Largest Roth conversion that leaves 2028 Part B premiums alone. MAGI for IRMAA adds back tax-exempt interest and
    includes only the taxable part of Social Security."""
    filing = "mfj" if n % 2 == 0 else "single"
    k = 2 if filing == "mfj" else 1
    w, m = rng.choice(WOMEN), rng.choice(MEN)
    ya, yb = rng.randint(1956, 1960), rng.randint(1955, 1960)
    ss_a, ss_b = rng.randrange(1800, 3400, 50), rng.randrange(1500, 3000, 50)
    muni = rng.randrange(4000, 26000, 500)
    tier = n % 3  # which threshold they sit under
    edge = IRMAA[filing][tier]
    pension = rng.randrange(20000, 40000, 500) * k
    people = [person("a", ya, ss_a)] + ([person("b", yb, ss_b)] if k == 2 else [])
    income = [{"type": "pension", "owner": "a", "annual": pension}, {"type": "interest_tax_exempt", "owner": "a", "annual": muni}]
    accounts = [{"id": "a_ira", "owner": "a", "type": "traditional_ira", "balance": 900000}]
    # Pick the IRA withdrawal so the household sits $8,000–$40,000 under the threshold before converting.
    gap = rng.randrange(8000, 40000, 250)
    base = run_both(scenario(filing, "none", people, accounts, income, [{"name": "A", "actions": []}]))[0]["magi_for_irmaa"]
    wd = round(edge - gap - base, -2)
    assert wd >= 5000, "draw again: already too close to the threshold"
    plan = lambda conv: [{"name": "A", "actions": [{"type": "withdrawal", "from": "a_ira", "amount": wd, "years": [2026]}]
                          + ([{"type": "roth_conversion", "from": "a_ira", "amount": conv, "years": [2026]}] if conv else [])}]
    magi = run_both(scenario(filing, "none", people, accounts, income, plan(0)))[0]["magi_for_irmaa"]
    room = round(edge - magi)
    at = run_both(scenario(filing, "none", people, accounts, income, plan(room)))[0]["magi_for_irmaa"]
    over = run_both(scenario(filing, "none", people, accounts, income, plan(room + 100)))[0]["magi_for_irmaa"]
    assert abs(at - edge) <= 1 and over > edge, (at, over, edge)
    who = couple_text(w, m, ya, yb) if k == 2 else f"{w} (born January {ya}) is single and enrolled in Medicare Part B"
    ss = f"Social Security of {money(ss_a * 12)} ({w}) and {money(ss_b * 12)} ({m})" if k == 2 else f"Social Security of {money(ss_a * 12)}"
    prompt = (f"{LAW} Use the 2026 CMS Part B premiums and IRMAA tiers. {who}. For 2026 they expect a pension of {money(pension)}, "
              f"traditional IRA withdrawals of {money(wd)}, {ss}, and {money(muni)} of tax-exempt municipal bond interest. No other income. "
              f"Medicare sets Part B premiums from the return two years earlier, so 2026 income sets 2028 premiums; assume the 2026 tiers still "
              f"apply in 2028. What is the largest Roth conversion, in whole dollars, they can add in 2026 without raising their 2028 Part B "
              f"premium above what it would be with no conversion? {END}")
    add("irmaa_headroom", n, prompt, room, 2, "CMS 2026 Part B/IRMAA fact sheet (MAGI = AGI + tax-exempt interest; a tier starts above its threshold); IRS Pub 915",
        scenario(filing, "none", people, accounts, income, plan(room)), "IRMAA two years out; muni interest counts, only taxable Social Security counts")


def conv_cost_az(rng, n):
    """Added 2026 federal plus Arizona tax from a Roth conversion that also makes more Social Security taxable."""
    w, m = rng.choice(WOMEN), rng.choice(MEN)
    ya, yb = rng.randint(1955, 1960), rng.randint(1955, 1960)
    ss_a, ss_b = rng.randrange(1700, 2900, 50), rng.randrange(1200, 2400, 50)
    pension = rng.randrange(18000, 60000, 500)
    conv = rng.randrange(30000, 110000, 5000)
    people = [person("a", ya, ss_a), person("b", yb, ss_b)]
    income = [{"type": "pension", "owner": "a", "annual": pension}]
    accounts = [{"id": "a_ira", "owner": "a", "type": "traditional_ira", "balance": 800000}]
    sc = scenario("mfj", "AZ", people, accounts, income, [{"name": "A", "actions": []},
                  {"name": "B", "actions": [{"type": "roth_conversion", "from": "a_ira", "amount": conv, "years": [2026]}]}])
    a, b = run_both(sc)
    ans = round(b["federal_tax"] + b["state_tax"] - a["federal_tax"] - a["state_tax"])
    prompt = (f"{LAW} They live in Arizona; use Arizona income tax law for 2026 as amended by Laws 2026, chapter 140 (which lets Arizona "
              f"filers subtract the federal senior deduction). {couple_text(w, m, ya, yb)}. In 2026 they have a pension of {money(pension)} and "
              f"Social Security of {money(ss_a * 12)} ({w}) and {money(ss_b * 12)} ({m}), and no other income. They are considering converting "
              f"{money(conv)} from a traditional IRA to a Roth IRA in 2026. How much more total income tax, federal plus Arizona, would they owe "
              f"for 2026 with the conversion than without it? Round to the nearest dollar. {END}")
    add("conv_cost_az", n, prompt, ans, 5, "Rev. Proc. 2025-32; Schedule 1-A Part V; IRS Pub 915; A.R.S. §§43-1011, 43-1022(10) and (35), 43-1023, 43-1041 (Laws 2026 ch. 140)",
        sc, "conversion + Social Security torpedo + senior phase-out + Arizona")


def ss_muni_qcd(rng, n):
    """Taxable Social Security when muni interest counts toward provisional income and a QCD doesn't."""
    filing = "single" if n % 2 == 0 else "mfj"
    w, m = rng.choice(WOMEN), rng.choice(MEN)
    ya, yb = rng.randint(1950, 1955), rng.randint(1950, 1955)  # 71+ in 2026, so QCDs are allowed; under 73 or not, no RMD is asked
    ss_a, ss_b = rng.randrange(1600, 3000, 50), rng.randrange(1200, 2200, 50)
    muni = rng.randrange(3000, 15000, 500)
    qcd = rng.randrange(4000, 16000, 500)
    target = rng.randrange(6000, 30000, 500) * (2 if filing == "mfj" else 1)
    people = [person("a", ya, ss_a)] + ([person("b", yb, ss_b)] if filing == "mfj" else [])
    income = [{"type": "interest_tax_exempt", "owner": "a", "annual": muni}]
    accounts = [{"id": "a_ira", "owner": "a", "type": "traditional_ira", "balance": 500000}]
    probe = run_both(scenario(filing, "none", people, accounts, income, [{"name": "A", "actions": []}]))[0]
    rmd = probe["rmd"]
    extra = max(0, round(target - rmd, -2))
    acts = [{"type": "qcd", "from": "a_ira", "amount": qcd, "years": [2026]}] + ([{"type": "withdrawal", "from": "a_ira", "amount": extra, "years": [2026]}] if extra else [])
    sc = scenario(filing, "none", people, accounts, income, [{"name": "A", "actions": acts}])
    row = run_both(sc)[0]
    total_out = round(max(rmd, qcd) + extra) if rmd else qcd + extra  # a QCD counts toward the RMD first
    kept = total_out - qcd
    ss_total = (ss_a + (ss_b if filing == "mfj" else 0)) * 12
    assert row["qcd"] == qcd and abs(row["agi"] - kept - row["taxable_social_security"]) <= 1, (row["agi"], kept, row["taxable_social_security"], rmd, extra)
    assert 0 < row["taxable_social_security"] < 0.85 * ss_total - 5, "want a case inside the phase-in, not at the 85% cap"
    who = (f"{w} (born January {ya}) and {m} (born January {yb}) are married and file jointly" if filing == "mfj" else f"{w} (born January {ya}) is single")
    prompt = (f"{LAW} {who}. In 2026 total Social Security benefits are {money(ss_total)}. {w} takes {money(total_out)} out of a traditional IRA "
              f"during the year; {money(qcd)} of that goes straight from the IRA custodian to a qualified charity as a qualified charitable "
              f"distribution and the rest comes to the household. They also receive {money(muni)} of tax-exempt municipal bond interest. No other income. "
              f"How many dollars of their 2026 Social Security benefits are taxable? Round to the nearest dollar. {END}")
    add("ss_muni_qcd", n, prompt, round(row["taxable_social_security"]), 2, "IRS Pub 915 Worksheet 1 (tax-exempt interest is added on line 3); IRC §408(d)(8) (a QCD is not in income)",
        sc, "taxable Social Security inside the phase-in; muni interest counts, the QCD doesn't")


def inherited_rmd(rng, n):
    """2026 RMD from an inherited IRA under the 10-year rule: annual RMDs only if the owner had reached the required
    beginning date, with the divisor the longer of the beneficiary's and the owner's (minus one each year)."""
    w = rng.choice(WOMEN + MEN)
    parent = rng.choice(["mother", "father"])
    before_rbd = n in (2, 5)
    died = rng.randint(2021, 2024)
    owner_born = rng.randint(1953, 1958) if before_rbd else rng.randint(1936, 1946)
    ben_born = rng.randint(1962, 1975)
    bal = rng.randrange(180000, 900000, 1000)
    people = [person("a", ben_born)]
    people[0]["medicare"] = False
    accounts = [{"id": "a_inh", "owner": "a", "type": "inherited_ira", "balance": bal,
                 "inherited": {"from_born": owner_born, "died": died, "owner_had_reached_rbd": not before_rbd, "beneficiary_class": "designated"}}]
    wages = rng.randrange(60000, 140000, 1000)
    sc = scenario("single", "none", people, accounts, [{"type": "wages", "owner": "a", "annual": wages}], [{"name": "A", "actions": []}])
    row = run_both(sc)[0]
    ans = round(row["rmd_by_account"].get("a_inh", 0))
    assert (ans == 0) == before_rbd, (ans, before_rbd)
    age_at_death = died - owner_born
    prompt = (f"{w}, born in January {ben_born}, is the sole beneficiary of a traditional IRA inherited from their {parent}, who was born in "
              f"January {owner_born} and died in {died} at age {age_at_death}"
              f"{', before starting required minimum distributions' if before_rbd else ', after starting required minimum distributions'}. "
              f"{w} is an ordinary adult-child beneficiary (not disabled or chronically ill) and has taken every distribution required so far. "
              f"The inherited IRA was worth {money(bal)} on December 31, 2025. Under the SECURE Act and the final IRS regulations (and IRS Pub 590-B), "
              f"what is the minimum {w} must withdraw from the inherited IRA for 2026? Give 0 if no withdrawal is required for 2026. "
              f"Round to the nearest dollar. {END}")
    add("inherited_rmd", n, prompt, ans, 2, "IRC §401(a)(9)(B), (H); Treas. Reg. §1.401(a)(9)-5(d); IRS Pub 590-B Table I (Single Life)", sc,
        "no annual RMD if the owner died before the required beginning date" if before_rbd else "annual RMD inside the 10-year window; longer of beneficiary's and owner's remaining life expectancy")


def qcd_rmd_tax(rng, n):
    """Federal tax when part of the RMD goes out as a QCD: the model has to work out the RMD, take the QCD off income,
    then run Social Security taxation and the senior deduction."""
    w = rng.choice(WOMEN + MEN)
    born = rng.randint(1941, 1952)
    bal = rng.randrange(450000, 1600000, 5000)
    ss = rng.randrange(1800, 3300, 50)
    pension = rng.randrange(0, 30000, 500)
    people = [person("a", born, ss)]
    accounts = [{"id": "a_ira", "owner": "a", "type": "traditional_ira", "balance": bal}]
    income = [{"type": "pension", "owner": "a", "annual": pension}] if pension else []
    rmd = run_both(scenario("single", "none", people, accounts, income, [{"name": "A", "actions": []}]))[0]["rmd"]
    qcd = int(rmd * rng.choice([0.25, 0.4, 0.5, 0.6]) // 500 * 500)
    assert 1000 <= qcd <= 111000, "draw again: QCD must be under the 2026 limit"
    sc = scenario("single", "none", people, accounts, income, [{"name": "A", "actions": [{"type": "qcd", "from": "a_ira", "amount": qcd, "years": [2026]}]}])
    row = run_both(sc)[0]
    assert row["qcd"] == qcd and abs(row["agi"] - (rmd - qcd) - pension - row["taxable_social_security"]) <= 1
    prompt = (f"{LAW} {w}, born in January {born}, is single. {w}'s only traditional IRA was worth {money(bal)} on December 31, 2025. In 2026 "
              f"{w} takes exactly the required minimum distribution from it and no more, sending {money(qcd)} of that directly from the IRA to a "
              f"qualified charity as a qualified charitable distribution. {w} also has Social Security benefits of {money(ss * 12)}"
              f"{f' and a pension of {money(pension)}' if pension else ''}. No other income. What is {w}'s total 2026 federal income tax? "
              f"Round to the nearest dollar. {END}")
    add("qcd_rmd_tax", n, prompt, round(row["federal_tax"]), 5, "IRS Pub 590-B Table III (Uniform Lifetime) and QCD rules; IRC §408(d)(8); Pub 915; Rev. Proc. 2025-32; Schedule 1-A Part V",
        sc, "RMD from the table, QCD counts toward it and stays out of income, then the usual tax stack")


def widow_first_year(rng, n):
    """How much more federal tax the survivor owes than the couple would have: single brackets, one Social Security
    check, one senior deduction with the single threshold, and the whole IRA on one person's RMD divisor."""
    w, m = rng.choice(WOMEN), rng.choice(MEN)
    ya, yb = rng.randint(1944, 1952), rng.randint(1940, 1950)
    ss_a, ss_b = rng.randrange(1300, 2400, 50), rng.randrange(2400, 3600, 50)
    assert 0 <= ya - yb <= 9, "draw again: keeps the Uniform Lifetime Table right for both (spouse not more than 10 years younger)"
    bal_a, bal_b = rng.randrange(150000, 600000, 5000), rng.randrange(400000, 1400000, 5000)
    pension = rng.randrange(0, 24000, 500)
    inc = [{"type": "interest_taxable", "owner": "a", "annual": pension}] if pension else []
    couple = scenario("mfj", "none", [person("a", ya, ss_a), person("b", yb, ss_b)],
                      [{"id": "a_ira", "owner": "a", "type": "traditional_ira", "balance": bal_a}, {"id": "b_ira", "owner": "b", "type": "traditional_ira", "balance": bal_b}],
                      inc, [{"name": "A", "actions": []}])
    widow = scenario("single", "none", [person("a", ya, ss_b)], [{"id": "a_ira", "owner": "a", "type": "traditional_ira", "balance": bal_a + bal_b}],
                     inc, [{"name": "A", "actions": []}])
    c, s = run_both(couple)[0], run_both(widow)[0]
    ans = round(s["federal_tax"] - c["federal_tax"])
    prompt = (f"{LAW} Compare two versions of 2026 for the same household, using 2026 law for both. Version 1: {w} (born January {ya}) and {m} "
              f"(born January {yb}) are married and file jointly. {w}'s traditional IRA was worth {money(bal_a)} and {m}'s {money(bal_b)} on December 31, "
              f"2025; each takes exactly their own required minimum distribution. Social Security is {money(ss_a * 12)} ({w}) and {money(ss_b * 12)} ({m})"
              f"{f', and they have {money(pension)} of taxable interest' if pension else ''}. Version 2: {m} died in 2025. {w} files as single for 2026, "
              f"rolled {m}'s IRA into her own before December 31, 2025 (so her IRA held {money(bal_a + bal_b)} on that date) and takes exactly her required "
              f"minimum distribution, and receives the larger of the two Social Security benefits instead of her own"
              f"{', with the same taxable interest' if pension else ''}. No other income in either version. How many dollars more federal income tax "
              f"does {w} owe in version 2 than the couple owes in version 1? Give a negative number if she owes less. Round to the nearest dollar. {END}")
    add("widow_first_year", n, prompt, ans, 5, "IRS Pub 590-B Table III and spousal rollover; Pub 915; Rev. Proc. 2025-32; Schedule 1-A Part V",
        {"couple": couple, "widow": widow}, "single brackets + lost Social Security check + one senior deduction + RMD on the survivor's age")


def az_tax(rng, n):
    """Arizona income tax for retirees: Social Security and the federal senior deduction come off, plus $2,100 per person 65+."""
    filing = "mfj" if n % 2 == 0 else "single"
    w, m = rng.choice(WOMEN), rng.choice(MEN)
    ya, yb = rng.randint(1952, 1960), rng.randint(1952, 1960)
    ss_a, ss_b = rng.randrange(1700, 3000, 50), rng.randrange(1300, 2500, 50)
    k = 2 if filing == "mfj" else 1
    pension = rng.randrange(25000, 70000, 500) * k
    interest = rng.randrange(2000, 12000, 500)
    people = [person("a", ya, ss_a)] + ([person("b", yb, ss_b)] if k == 2 else [])
    income = [{"type": "pension", "owner": "a", "annual": pension}, {"type": "interest_taxable", "owner": "a", "annual": interest}]
    sc = scenario(filing, "AZ", people, [{"id": "a_roth", "owner": "a", "type": "roth_ira", "balance": 100000, "first_roth_year": 2010}], income, [{"name": "A", "actions": []}])
    row = run_both(sc)[0]
    ss_total = (ss_a + (ss_b if k == 2 else 0)) * 12
    who = (f"{w} (born January {ya}) and {m} (born January {yb}) are married Arizona residents who file jointly" if k == 2
           else f"{w} (born January {ya}) is a single Arizona resident")
    prompt = (f"Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction) and "
              f"Arizona income tax law for 2026 as amended by Laws 2026, chapter 140 (which lets Arizona filers subtract the federal senior deduction, "
              f"and sets the Arizona standard deduction equal to the federal basic standard deduction). {who}. In 2026 they have pension income of "
              f"{money(pension)} (from a private employer), {money(interest)} of taxable interest and Social Security benefits of {money(ss_total)}. "
              f"No other income; they take the standard deduction on both returns and have no credits. What is their 2026 Arizona income tax? "
              f"Round to the nearest dollar. {END}")
    add("az_tax", n, prompt, round(row["state_tax"]), 5, "A.R.S. §43-1011 (2.5% flat rate), §43-1022(10) and (35), §43-1023 ($2,100 age-65 exemption), §43-1041 (Laws 2026 ch. 140); Pub 915; Schedule 1-A Part V",
        sc, "Arizona: Social Security out, senior deduction out, age-65 exemption, federal basic standard deduction, 2.5%")


FAMILIES = [irmaa_headroom, conv_cost_az, ss_muni_qcd, inherited_rmd, qcd_rmd_tax, widow_first_year, az_tax]


def main():
    for fam in FAMILIES:
        rng = random.Random(f"plannerbench-v2-{fam.__name__}")
        n = tries = 0
        while n < 6:
            tries += 1
            if tries > 200:
                raise SystemExit(f"{fam.__name__}: could not make 6 items")
            try:
                fam(rng, n)
                n += 1
            except AssertionError:
                continue  # this draw didn't land where the question needs it; draw again
    assert len({i["prompt"] for i in ITEMS}) == len(ITEMS)
    OUT.write_text("".join(json.dumps(i) + "\n" for i in ITEMS))
    md = ["# PlannerBench v2 hard tier", "", f"{len(ITEMS)} questions, 6 per family. Built by `v2/build_hard.py`. Every key is the Planning Engine's 2026 row "
          "and matched the clean-room engine within $1 on tax, AGI, MAGI, taxable Social Security, the senior deduction and every RMD.", "",
          "| Family | What interacts | Published source | Tolerance |", "|---|---|---|---|"]
    seen = set()
    for i in ITEMS:
        if i["family"] not in seen:
            seen.add(i["family"])
            fam_items = [x for x in ITEMS if x["family"] == i["family"]]
            notes = "; ".join(sorted({x["note"] for x in fam_items}))
            md.append(f"| `{i['family']}` | {notes} | {i['source']} | ±${i['tol']} |")
    md += ["", "## One example per family", ""]
    for fam in seen and [f.__name__ for f in FAMILIES]:
        i = next(x for x in ITEMS if x["family"] == fam)
        md += [f"**{i['id']}** (answer {i['answer']})", "", "> " + i["prompt"], ""]
    (ROOT / "v2" / "data" / "HARD.md").write_text("\n".join(md) + "\n")
    print(f"{len(ITEMS)} items → {OUT.relative_to(ROOT)}")
    for i in ITEMS:
        print(i["id"], i["answer"])


if __name__ == "__main__":
    main()
