"""PolicyEngine-US, one tax year at a time: the outside check for the scenario engine's year-by-year tax.

The scenario engine runs a household forward many years. PolicyEngine-US (an open-source tax model this project
didn't write) only computes single years, so each year of the engine's ledger is handed to it as its own tax return:
the income items that year, the ages that year, the state. Where PolicyEngine and the engine disagree, the published
source decides.

Covers: federal income tax (brackets, capital gains stacking, standard and itemized deductions, the senior
deduction, the non-itemizer charitable deduction), taxable Social Security, NIIT, Arizona income tax.
Not covered here: RMDs, Medicare premiums, account balances, inherited IRAs (the clean-room engine checks those).

Run with PolicyEngine's own environment:
  .venv-pe/bin/python -I checks/pe_years.py in.jsonl out.jsonl
Each input line is one tax year:
  {"id": "...", "year": 2027, "filing": "mfj"|"single", "ages": [70, 68], "state": "AZ"|"none",
   "wages": 0, "ira": 0, "pension": 0, "taxable_interest": 0, "tax_exempt_interest": 0,
   "qualified_dividends": 0, "ordinary_dividends": 0, "ltcg": 0, "ss": [24000, 18000],
   "real_estate_tax": 0, "mortgage_interest": 0, "medical": 0, "charity_cash": 0}
Income items sit with the first person except Social Security, which is per person. "ira" is the taxable amount
(after the pro-rata rule; conversions included). "ordinary_dividends" are non-qualified only.
"""
import json
import sys
from collections import defaultdict

OUT_VARS = {
    "agi": "adjusted_gross_income",
    "taxable_ss": "tax_unit_taxable_social_security",
    "standard_deduction": "standard_deduction",
    "senior_deduction": "additional_senior_deduction",
    "itemizes": "tax_unit_itemizes",
    "taxable_income": "taxable_income",
    "income_tax_before_credits": "income_tax_before_credits",
    "niit": "net_investment_income_tax",
    "state_income_tax": "state_income_tax",
}

# Person-level inputs on the first person: our name -> PolicyEngine variable.
PERSON_INPUTS = {
    "wages": "employment_income",
    "ira": "taxable_ira_distributions",
    "pension": "taxable_pension_income",
    "taxable_interest": "taxable_interest_income",
    "tax_exempt_interest": "tax_exempt_interest_income",
    "qualified_dividends": "qualified_dividend_income",
    "ordinary_dividends": "non_qualified_dividend_income",
    "ltcg": "long_term_capital_gains",
    "real_estate_tax": "real_estate_taxes",
    "mortgage_interest": "deductible_mortgage_interest",
    "medical": "other_medical_expenses",
    "charity_cash": "charitable_cash_donations",
}


def situation(rows, year):
    """One PolicyEngine situation holding every household for this year (one simulation is far faster than many)."""
    y = str(year)
    sit = {k: {} for k in ("people", "tax_units", "families", "spm_units", "households", "marital_units")}
    for h, r in enumerate(rows):
        names = []
        ss = r.get("ss") or []
        for k, age in enumerate(r["ages"]):
            name = f"h{h}p{k}"
            names.append(name)
            p = {"age": {y: age}, "social_security_retirement": {y: ss[k] if k < len(ss) else 0}}
            for ours, theirs in PERSON_INPUTS.items():
                p[theirs] = {y: r.get(ours, 0) if k == 0 else 0}
            sit["people"][name] = p
        for g in ("tax_units", "families", "spm_units", "marital_units"):
            sit[g][f"h{h}"] = {"members": names}
        state = r.get("state", "none")
        # Texas has no income tax, so "none" means federal only.
        sit["households"][f"h{h}"] = {"members": names, "state_code": {y: "TX" if state == "none" else state}}
    return sit


def run(rows):
    from policyengine_us import Simulation

    by_year = defaultdict(list)
    for r in rows:
        by_year[r["year"]].append(r)
    results = {}
    for year, group in by_year.items():
        sim = Simulation(situation=situation(group, year))
        cols = {ours: sim.calculate(theirs, str(year)) for ours, theirs in OUT_VARS.items()}
        for h, r in enumerate(group):
            out = {k: round(float(v[h]), 2) for k, v in cols.items()}
            out["itemizes"] = bool(cols["itemizes"][h])
            # PolicyEngine keeps NIIT outside "income tax before credits"; the engine reports them together.
            out["federal_tax"] = round(out["income_tax_before_credits"] + out["niit"], 2)
            results[r["id"]] = out
    return [dict(id=r["id"], **results[r["id"]]) for r in rows]


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    rows = [json.loads(line) for line in open(src) if line.strip()]
    with open(dst, "w") as f:
        for out in run(rows):
            f.write(json.dumps(out) + "\n")
    print(f"{len(rows)} tax years computed by PolicyEngine-US -> {dst}")
