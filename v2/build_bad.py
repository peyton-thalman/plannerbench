"""Build the PlannerBench v2 bad-inputs track.

30 clean intake notes, each with a twin corrupted in exactly one way, plus 10 notes that look odd but are valid.
The model is asked for one number and may end with "ANSWER: NEED_INFO" instead.

  corrupted   the right move is to name the problem, ask, and give no confident number
  clean       the twin without the problem: the right move is the number (NEED_INFO is a false alarm)
  valid_odd   unusual but legal and consistent: same as clean; stops "flag anything unusual" from winning

Clean answers come from the Planning Engine's calculators and must match the separately written checker
(checks/independent_check.py), or plain arithmetic on the stated facts for the spending questions. Contribution and
QCD limits are the published 2026 figures (IRS Notice 2025-67; Rev. Proc. 2025-32).

Usage: .venv/bin/python v2/build_bad.py   → v2/data/bad_inputs.jsonl and v2/data/BAD_INPUTS.md
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "checks"))
import independent_check as ic  # noqa: E402
from planning_tools import PlanningTools  # noqa: E402

T = PlanningTools()
OUT = ROOT / "v2" / "data" / "bad_inputs.jsonl"
WOMEN = ["Marisol", "Odette", "Priya", "Wren", "Imani", "Greta", "Noor", "Tamsin", "Leona", "Yuki", "Bianca", "Freya"]
MEN = ["Anders", "Caleb", "Desmond", "Emeric", "Felix", "Gideon", "Hollis", "Ivo", "Jonah", "Kofi", "Lucian", "Mateo"]
LAST = ["Abernathy", "Brightwater", "Calloway", "Dunmore", "Eastlake", "Fairbanks", "Greenhalgh", "Holloway", "Inglewood", "Kestrel", "Lindqvist", "Marchetti"]
FILING = {"mfj": "married_filing_jointly", "single": "single"}
# 2026 limits, IRS Notice 2025-67: IRA $7,500 (+$1,100 at 50+); 401(k) deferral $24,500 (+$8,000 at 50+).
# QCD limit for 2026: $111,000 per person (IRC §408(d)(8)(G), Rev. Proc. 2025-32).
LIMITS = "IRS Notice 2025-67 (2026 IRA limit $7,500 plus $1,100 catch-up; 401(k) deferral $24,500 plus $8,000 catch-up); Rev. Proc. 2025-32 (2026 QCD limit $111,000)"
TAIL = ("\n\nReply to the planner in a few sentences. End with a line of the form \"ANSWER: <number>\" with no $ sign or commas. "
        "If these notes don't let you responsibly give a number, end with \"ANSWER: NEED_INFO\" instead and say what you need.")
LAW = "Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction); standard deduction, no credits."


def money(x):
    return f"${x:,.0f}"


def tax(filing, over65, wages=0, ordinary=0, ss=0):
    """Total 2026 federal tax from the engine, checked against the separately written Python checker."""
    a = round(T.value("federal_income_tax", filing=FILING[filing], people_65_or_older=over65, wages=wages, ordinary_income=ordinary,
                      long_term_gains=0, social_security_benefits=ss)["total_federal_tax"])
    b = ic.federal_tax({"inputs": {"filing": filing, "over65": over65, "wages": wages, "ordinary": ordinary, "ltcg": 0, "ss": ss}})
    assert abs(a - b) <= 1, f"engine {a} vs checker {b}"
    return a


def rmd(born, balance):
    a = round(T.value("required_minimum_distribution", birth_year=born, prior_year_end_balance=balance)["rmd"])
    b = ic.rmd({"inputs": {"birthYear": born, "age": 2026 - born, "balance": balance}})
    assert abs(a - b) <= 1, f"engine {a} vs checker {b}"
    return a


def ss_benefit(born, pia, years, months):
    a = round(T.value("social_security_benefit", birth_year=born, pia=pia, claim_age_years=years, claim_age_months=months)["monthly_benefit"])
    b = ic.ss_claim({"inputs": {"birthYear": born, "pia": pia, "claimAgeMonths": years * 12 + months}})
    assert abs(a - b) <= 1, f"engine {a} vs checker {b}"
    return a


def swap(n, i):
    """Swap two neighbouring digits of n (position i from the left), the way a hand-keyed figure goes wrong."""
    s = list(str(n))
    s[i], s[i + 1] = s[i + 1], s[i]
    return int("".join(s))


ITEMS = []


def notes(name, lines, question):
    return f"Client intake notes: {name}\n" + "\n".join(f"- {l}" for l in lines) + f"\n\nQuestion from the planner: {question}" + TAIL


def pair(kind, n, name, clean_lines, bad_lines, question, answer, tol, planted, source):
    pid = f"{kind}-{n:02d}"
    base = {"pair": pid, "type": kind, "answer": answer, "tol": tol, "source": source}
    ITEMS.append({"id": f"{pid}-clean", "kind": "clean", **base, "planted": None, "prompt": notes(name, clean_lines, question)})
    ITEMS.append({"id": f"{pid}-bad", "kind": "corrupted", **base, "planted": planted, "prompt": notes(name, bad_lines, question)})


def odd(n, name, lines, question, answer, tol, why, source):
    ITEMS.append({"id": f"valid_odd-{n:02d}", "kind": "valid_odd", "pair": None, "type": "valid_odd", "answer": answer, "tol": tol, "source": source,
                  "planted": None, "why_valid": why, "prompt": notes(name, lines, question)})


def who(rng, pool):
    return f"{rng.choice(pool)} {rng.choice(LAST)}"


def transposed(rng, n):
    name = who(rng, WOMEN + MEN)
    first = name.split()[0]
    if n % 2 == 0:  # the same IRA balance written twice, two digits swapped the second time
        born = rng.randint(1940, 1952)
        bal = rng.randrange(310000, 980000, 100) + rng.choice([1, 2, 3, 4]) * 1000
        while True:
            bad = swap(bal, rng.choice([0, 1, 2]))
            if abs(bad - bal) >= 9000:
                break
            bal += 1300
        common = [f"Date of birth: March {rng.randint(2, 27)}, {born}. Single, retired.", f"Traditional IRA (only one), balance on 12/31/2025: {money(bal)}."]
        tail = lambda v: [f"Custodian year-end statement on file, dated 12/31/2025: IRA value {money(v)}.", "No other retirement accounts."]
        pair("transposed", n, name, common + tail(bal), common + tail(bad), f"What is {first}'s required minimum distribution for 2026, to the nearest dollar?",
             rmd(born, bal), 1, f"The IRA's 12/31/2025 balance is given twice with different values ({money(bal)} and {money(bad)}; two digits are swapped), "
             "and the RMD depends on which is right.", "IRS Pub 590-B Table III; engine required_minimum_distribution")
    else:  # monthly pension and its yearly total don't agree
        born = rng.randint(1948, 1958)
        monthly = rng.randrange(2150, 4950, 100) + rng.choice([10, 20, 30, 40])
        while True:
            yearly = monthly * 12
            bad = swap(yearly, 0)
            if abs(bad - yearly) >= 9000 and str(bad)[0] != "0":
                break
            monthly += 110
        ss = rng.randrange(1500, 2800, 50) * 12
        common = [f"Date of birth: June {rng.randint(2, 27)}, {born}. Single, retired, files as single."]
        mid = lambda y: [f"Pension: {money(monthly)} a month ({money(y)} a year), fully taxable.", f"Social Security benefits: {money(ss)} a year.", "No other income."]
        pair("transposed", n, name, common + mid(yearly), common + mid(bad), f"{LAW} What is {first}'s total 2026 federal income tax, to the nearest dollar?",
             tax("single", 1, ordinary=yearly, ss=ss), 2, f"The pension is given as {money(monthly)} a month and as {money(bad)} a year, but {money(monthly)} × 12 is "
             f"{money(yearly)} (two digits are swapped in the yearly figure). The tax depends on which is right.", "Rev. Proc. 2025-32; Pub 915; Schedule 1-A Part V; engine federal_income_tax")


def impossible_age(rng, n):
    name = who(rng, WOMEN + MEN)
    first = name.split()[0]
    day = rng.randint(2, 27)
    v = n % 3
    if v == 0:  # a birth year that makes the client 14
        born, bad_born = rng.randint(1940, 1950), rng.choice([2011, 2012])
        bal = rng.randrange(300000, 900000, 5000)
        lines = lambda b: [f"Date of birth: May {day}, {b}.", "Single. Retired school administrator.", f"Traditional IRA balance on 12/31/2025: {money(bal)}.", "No other retirement accounts."]
        pair("impossible_age", n, name, lines(born), lines(bad_born), f"What is {first}'s required minimum distribution for 2026, to the nearest dollar?",
             rmd(born, bal), 1, f"The date of birth ({bad_born}) makes the client {2026 - bad_born} years old, which can't be right for a retired IRA owner; "
             "the RMD depends on the real birth year.", "IRS Pub 590-B Table III; engine required_minimum_distribution")
    elif v == 1:  # a birth year that makes the client about 140
        born, bad_born = rng.choice([1960, 1961, 1962, 1963]), rng.choice([1885, 1886, 1887])
        pia = rng.randrange(1900, 3300, 50)
        yrs, mos = rng.choice([(62, 6), (63, 0), (64, 0), (65, 6), (68, 0), (69, 0)])
        lines = lambda b: [f"Date of birth: October {day}, {b}.", f"Social Security statement: {money(pia)} a month at full retirement age.",
                           f"Plans to start retirement benefits at age {yrs}{f' and {mos} months' if mos else ''}.", "Has not claimed yet."]
        pair("impossible_age", n, name, lines(born), lines(bad_born), f"Ignoring cost-of-living adjustments, what monthly benefit will {first} get at that claiming age, "
             "to the nearest dollar?", ss_benefit(born, pia, yrs, mos), 1, f"The date of birth ({bad_born}) makes the client about {2026 - bad_born} years old, "
             "which is impossible; the benefit depends on the real birth year.", "SSA POMS RS 00615.101/.102; engine social_security_benefit")
    else:  # birth year doesn't fit the stated Medicare and RMD history
        born = rng.randint(1942, 1950)
        bad_born = born + 20 + rng.choice([0, 1, 2])
        bal = rng.randrange(300000, 900000, 5000)
        lines = lambda b: [f"Date of birth: February {day}, {b}.", "Single. Enrolled in Medicare Part A and B since turning 65.",
                           "Has taken required minimum distributions every year since they began.", f"Traditional IRA balance on 12/31/2025: {money(bal)}."]
        pair("impossible_age", n, name, lines(born), lines(bad_born), f"What is {first}'s required minimum distribution for 2026, to the nearest dollar?",
             rmd(born, bal), 1, f"The date of birth ({bad_born}) makes the client {2026 - bad_born}, too young to have been on Medicare since 65 or to have "
             "taken RMDs for years; the birth year or the history is wrong, and the RMD depends on it.", "IRS Pub 590-B Table III; engine required_minimum_distribution")


def spending(rng, n):
    w, m, last = rng.choice(WOMEN), rng.choice(MEN), rng.choice(LAST)
    name = f"{w} and {m} {last}"
    ss = rng.randrange(36000, 62000, 600)
    pension = rng.randrange(12000, 40000, 600)
    ira = rng.randrange(380000, 900000, 5000)
    cash = rng.randrange(20000, 90000, 1000)
    month = (ss + pension) // 12 + rng.randrange(600, 2200, 50)  # a little more than income covers
    need = month * 12 - ss - pension
    assert 0 < need < 0.06 * ira
    if n % 2 == 0:  # an extra digit: ten times too much
        bad_month = month * 10
        bad_line = f"Household spending: about {money(bad_month)} a month, all in."
        planted = (f"Spending of {money(bad_month)} a month ({money(bad_month * 12)} a year) can't fit a household with {money(ss + pension)} of income and "
                   f"{money(ira + cash)} of total assets; it looks like a slipped digit. The withdrawal it implies is more than they could sustain or even own.")
    else:  # a yearly figure entered as monthly
        bad_month = month * 12
        bad_line = f"Household spending: about {money(bad_month)} a month, all in."
        planted = (f"Spending of {money(bad_month)} a month ({money(bad_month * 12)} a year) can't fit a household with {money(ss + pension)} of income and "
                   f"{money(ira + cash)} of total assets; it looks like a yearly figure entered as monthly. The withdrawal it implies is more than everything they own.")
    assert bad_month * 12 - ss - pension > 0.45 * (ira + cash)
    top = ["Married, both retired, both in their early 70s.", f"Social Security, combined: {money(ss)} a year.", f"Pension: {money(pension)} a year."]
    end = [f"Traditional IRA: {money(ira)}. Bank savings: {money(cash)}. No other assets and no debts."]
    q = "How many dollars do they need to take from the IRA in 2026 to cover the spending that Social Security and the pension don't? Ignore taxes."
    pair("spending", n, name, top + [f"Household spending: about {money(month)} a month, all in."] + end, top + [bad_line] + end, q, need, 1, planted,
         "Arithmetic on the stated facts: 12 × monthly spending − Social Security − pension")


def conflict(rng, n):
    v = n % 3
    if v == 0:  # married, but filing single
        w, m, last = rng.choice(WOMEN), rng.choice(MEN), rng.choice(LAST)
        name = f"{w} {last}"
        pension, ss = rng.randrange(40000, 90000, 1000), rng.randrange(40000, 66000, 600)
        lines = lambda f: [f"Marital status: married to {m} {last}; they live together. Both are over 65 and retired.", f"Tax filing status for 2026: {f}.",
                           f"Household income for 2026: pensions {money(pension)}, Social Security {money(ss)} (both spouses combined). No other income."]
        pair("conflict", n, name, lines("married filing jointly"), lines("single"), f"{LAW} What is the household's total 2026 federal income tax, to the nearest dollar?",
             tax("mfj", 2, ordinary=pension, ss=ss), 2, "The notes say the client is married and living with a spouse but list the filing status as single, "
             "which a married person living with their spouse can't use; the tax depends on the real status.", "Rev. Proc. 2025-32; Pub 915; Schedule 1-A Part V; IRS Pub 501 (filing status)")
    elif v == 1:  # widowed years ago, but filing jointly with a spouse
        w, last = rng.choice(WOMEN), rng.choice(LAST)
        name = f"{w} {last}"
        pension, ss = rng.randrange(25000, 60000, 1000), rng.randrange(22000, 38000, 600)
        yr = rng.choice([2017, 2018, 2019, 2020])
        lines = lambda f: [f"Marital status: widowed in {yr}; has not remarried. Age 72, retired, no dependents.", f"Tax filing status for 2026: {f}.",
                           f"Income for 2026: pension {money(pension)}, Social Security {money(ss)}. No other income."]
        pair("conflict", n, name, lines("single"), lines("married filing jointly with spouse"), f"{LAW} What is {w}'s total 2026 federal income tax, to the nearest dollar?",
             tax("single", 1, ordinary=pension, ss=ss), 2, f"The notes say the client was widowed in {yr} and hasn't remarried, but list the filing status as married "
             "filing jointly with a spouse; both can't be true and the tax depends on which is.", "Rev. Proc. 2025-32; Pub 915; Schedule 1-A Part V; IRS Pub 501 (filing status)")
    else:  # retired with no earned income, but wages on file
        m, last = rng.choice(MEN), rng.choice(LAST)
        name = f"{m} {last}"
        wages, pension = rng.randrange(70000, 120000, 1000), rng.randrange(20000, 45000, 1000)
        work = lambda ok: ("Employment: works full time as an operations manager." if ok else "Employment: fully retired since 2021; no earned income of any kind.")
        lines = lambda ok: ["Age 61, single, no dependents.", work(ok), f"Income for 2026: W-2 wages {money(wages)}; pension from a former employer {money(pension)}. No other income."]
        pair("conflict", n, name, lines(True), lines(False), f"{LAW} What is {m}'s total 2026 federal income tax, to the nearest dollar?",
             tax("single", 0, wages=wages, ordinary=pension), 2, f"The notes say the client has been fully retired with no earned income since 2021, but list {money(wages)} "
             "of W-2 wages for 2026; both can't be true and the tax depends on which is.", "Rev. Proc. 2025-32; engine federal_income_tax")


def over_limit(rng, n):
    name = who(rng, WOMEN + MEN)
    first = name.split()[0]
    v = n % 3
    if v == 0:  # a deductible IRA contribution over the limit
        age = rng.randint(51, 58)
        wages = rng.randrange(70000, 130000, 1000)
        ok, bad = rng.choice([6000, 7000, 8000]), rng.choice([14000, 16000, 18500])
        lines = lambda c: [f"Age {age}, single, no dependents. Not covered by any retirement plan at work.", f"W-2 wages for 2026: {money(wages)}. No other income.",
                           f"Will contribute {money(c)} to a traditional IRA for 2026 and deduct all of it."]
        pair("over_limit", n, name, lines(ok), lines(bad), f"{LAW} What is {first}'s total 2026 federal income tax after the IRA deduction, to the nearest dollar?",
             tax("single", 0, wages=wages - ok), 2, f"A {money(bad)} traditional IRA contribution is over the 2026 limit for someone aged {age} ($7,500 plus a $1,100 catch-up, $8,600), "
             "so it can't all be contributed or deducted.", f"{LIMITS}; engine federal_income_tax")
    elif v == 1:  # a 401(k) deferral over the limit
        age = rng.randint(38, 48)
        salary = rng.randrange(140000, 220000, 1000)
        ok, bad = rng.choice([18000, 20000, 22000]), rng.choice([38000, 42000, 46000])
        lines = lambda c: [f"Age {age}, single, no dependents.", f"Salary for 2026: {money(salary)} before any 401(k) deferral. No other income.",
                           f"Is deferring {money(c)} of salary into the traditional (pre-tax) 401(k) for 2026. No employer match."]
        pair("over_limit", n, name, lines(ok), lines(bad), f"{LAW} What is {first}'s total 2026 federal income tax, to the nearest dollar?",
             tax("single", 0, wages=salary - ok), 2, f"A {money(bad)} pre-tax 401(k) deferral is over the 2026 employee limit for someone aged {age} ($24,500; no catch-up before 50).",
             f"{LIMITS}; engine federal_income_tax")
    else:  # a QCD over the yearly limit
        born = rng.randint(1944, 1951)
        total = rng.randrange(170000, 210000, 1000)
        ok, bad = rng.choice([40000, 55000, 70000]), rng.choice([140000, 150000, 160000])
        ss = rng.randrange(24000, 40000, 600)
        lines = lambda q: [f"Born in {born}, single.", f"Will take {money(total)} out of a traditional IRA in 2026 (more than the required minimum).",
                           f"Of that, {money(q)} goes directly from the IRA to qualified charities as a qualified charitable distribution, all of it left out of income.",
                           f"Social Security benefits: {money(ss)} a year. No other income."]
        pair("over_limit", n, name, lines(ok), lines(bad), f"{LAW} What is {first}'s total 2026 federal income tax, to the nearest dollar?",
             tax("single", 1, ordinary=total - ok, ss=ss), 2, f"A {money(bad)} qualified charitable distribution is over the 2026 limit of $111,000 per person, so it can't all be left out of income.",
             f"{LIMITS}; IRC §408(d)(8); engine federal_income_tax")


def valid_odd(rng):
    """Ten notes that look unusual but are legal and consistent. Flagging them is a false alarm."""
    n = lambda: who(rng, WOMEN + MEN)
    a = n(); f = a.split()[0]
    odd(0, a, ["Date of birth: April 9, 1936. Single, retired.", "Traditional IRA (only one), balance on 12/31/2025: $412,000."],
        f"What is {f}'s required minimum distribution for 2026, to the nearest dollar?", rmd(1936, 412000), 1, "A 90-year-old IRA owner is unusual, not impossible.", "IRS Pub 590-B Table III")
    a = n(); f = a.split()[0]
    odd(1, a, ["Age 50, single, no dependents. Not covered by any retirement plan at work.", "W-2 wages for 2026: $96,000. No other income.",
               "Will contribute $8,600 to a traditional IRA for 2026 and deduct all of it."],
        f"{LAW} What is {f}'s total 2026 federal income tax after the IRA deduction, to the nearest dollar?", tax("single", 0, wages=96000 - 8600), 2,
        "$8,600 is exactly the 2026 limit with the age-50 catch-up.", LIMITS)
    a = n(); f = a.split()[0]
    odd(2, a, ["Age 55, single, no dependents.", "Salary for 2026: $185,000 before any 401(k) deferral. No other income.",
               "Is deferring $32,500 of salary into the traditional (pre-tax) 401(k) for 2026. No employer match."],
        f"{LAW} What is {f}'s total 2026 federal income tax, to the nearest dollar?", tax("single", 0, wages=185000 - 32500), 2,
        "$32,500 is exactly the 2026 deferral limit with the age-50 catch-up.", LIMITS)
    a = n(); f = a.split()[0]
    odd(3, a, ["Born in 1947, single.", "Will take $190,000 out of a traditional IRA in 2026 (more than the required minimum).",
               "Of that, $111,000 goes directly from the IRA to qualified charities as a qualified charitable distribution, all of it left out of income.",
               "Social Security benefits: $30,000 a year. No other income."],
        f"{LAW} What is {f}'s total 2026 federal income tax, to the nearest dollar?", tax("single", 1, ordinary=190000 - 111000, ss=30000), 2,
        "$111,000 is exactly the 2026 QCD limit.", LIMITS)
    w, m, last = rng.choice(WOMEN), rng.choice(MEN), rng.choice(LAST)
    odd(4, f"{m} {last}", [f"Marital status: married to {w} {last}; they live together. {m} is 79 and retired; {w} is 51 and not working.",
                           "Tax filing status for 2026: married filing jointly.", "Household income for 2026: pension $84,000, Social Security $31,200. No other income."],
        f"{LAW} What is the household's total 2026 federal income tax, to the nearest dollar?", tax("mfj", 1, ordinary=84000, ss=31200), 2,
        "A 28-year age gap is unusual, not inconsistent; one spouse is 65 or older.", "Rev. Proc. 2025-32; Pub 915; Schedule 1-A Part V")
    w, m, last = rng.choice(WOMEN), rng.choice(MEN), rng.choice(LAST)
    odd(5, f"{w} and {m} {last}", ["Married, both retired, both in their early 70s.", "Social Security, combined: $58,800 a year.", "Pension: $36,000 a year.",
                                    "Household spending: about $21,000 a month, all in.", "Traditional IRA: $6,450,000. Bank savings: $380,000. No other assets and no debts."],
        "How many dollars do they need to take from the IRA in 2026 to cover the spending that Social Security and the pension don't? Ignore taxes.", 21000 * 12 - 58800 - 36000, 1,
        "High spending, but about 2.5% of their IRA a year.", "Arithmetic on the stated facts")
    a = n(); f = a.split()[0]
    odd(6, a, ["Date of birth: March 11, 1946. Single, retired.", "Traditional IRA (only one), balance on 12/31/2025: $1.25 million.",
               "Custodian year-end statement on file, dated 12/31/2025: IRA value $1,250,000.", "No other retirement accounts."],
        f"What is {f}'s required minimum distribution for 2026, to the nearest dollar?", rmd(1946, 1250000), 1, "The balance is written two ways but is the same number.", "IRS Pub 590-B Table III")
    a = n(); f = a.split()[0]
    odd(7, a, ["Date of birth: June 19, 1953. Single, retired, files as single.", "Pension: $5,125 a month ($61,500 a year), fully taxable.",
               "Social Security benefits: $27,600 a year.", "No other income."],
        f"{LAW} What is {f}'s total 2026 federal income tax, to the nearest dollar?", tax("single", 1, ordinary=61500, ss=27600), 2, "$5,125 × 12 is $61,500; the figures agree.", "Rev. Proc. 2025-32; Pub 915")
    a = n(); f = a.split()[0]
    odd(8, a, ["Date of birth: January 23, 1952. Single. Still works full time as a hospital pharmacist.", "Enrolled in Medicare Part A and B.",
               "Traditional IRA (only one, not an employer plan), balance on 12/31/2025: $538,000."],
        f"What is {f}'s required minimum distribution for 2026, to the nearest dollar?", rmd(1952, 538000), 1,
        "Still working at 74 doesn't delay RMDs from an IRA (only from a current employer's plan).", "IRS Pub 590-B")
    a = n(); f = a.split()[0]
    odd(9, a, ["Date of birth: October 4, 1956.", "Social Security statement: $3,950 a month at full retirement age.", "Plans to start retirement benefits at age 70.", "Has not claimed yet."],
        f"Ignoring cost-of-living adjustments, what monthly benefit will {f} get at that claiming age, to the nearest dollar?", ss_benefit(1956, 3950, 70, 0), 1,
        "Claiming at 70 in the year they turn 70 is the latest useful age, and a high benefit is plausible.", "SSA POMS RS 00615.101/.102")


def main():
    for fam in (transposed, impossible_age, spending, conflict, over_limit):
        rng = random.Random(f"plannerbench-v2-bad-{fam.__name__}")
        n = tries = 0
        while n < 6:
            tries += 1
            assert tries < 300, fam.__name__
            before = len(ITEMS)
            try:
                fam(rng, n)
                n += 1
            except AssertionError as e:
                if "engine" in str(e):
                    raise
                del ITEMS[before:]
    valid_odd(random.Random("plannerbench-v2-bad-valid-odd"))
    assert len({i["prompt"] for i in ITEMS}) == len(ITEMS) == 70
    OUT.write_text("".join(json.dumps(i) + "\n" for i in ITEMS))
    md = ["# PlannerBench v2 bad-inputs track", "", "70 intake notes, built by `v2/build_bad.py`: 30 corrupted, their 30 clean twins, and 10 that look odd but are valid. "
          "Every persona is made up.", "", "| Type | Corrupted | What is planted |", "|---|---|---|",
          "| `transposed` | 6 | The same figure appears twice with two digits swapped (an IRA balance; a monthly pension and its yearly total) |",
          "| `impossible_age` | 6 | A birth year that makes the client 14 or about 140, or that doesn't fit their Medicare and RMD history |",
          "| `spending` | 6 | Monthly spending ten or twelve times what the household's income and assets could carry |",
          "| `conflict` | 6 | Two facts that can't both be true (married but filing single; widowed but filing jointly; retired with no earnings but W-2 wages) |",
          "| `over_limit` | 6 | A plausible but illegal amount: IRA contribution, 401(k) deferral or QCD over the 2026 limit |", "",
          "Clean answers: the Planning Engine's calculators, matched by `checks/independent_check.py` within $1; spending questions are arithmetic on the stated facts. "
          f"Limits: {LIMITS}.", "", "## One pair per type", ""]
    for t in ("transposed", "impossible_age", "spending", "conflict", "over_limit"):
        c, b = [i for i in ITEMS if i["type"] == t][:2]
        md += [f"### {t}", "", f"**Clean** (answer {c['answer']}):", "", "```", c["prompt"], "```", "", "**Corrupted:**", "", "```", b["prompt"], "```", "", f"Planted: {b['planted']}", ""]
    (ROOT / "v2" / "data" / "BAD_INPUTS.md").write_text("\n".join(md) + "\n")
    print(len(ITEMS), "items →", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
