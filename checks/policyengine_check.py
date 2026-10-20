"""Outside check: recompute every tax answer with PolicyEngine-US, an open-source tax model nobody on this project wrote.

The two-way check proves the engine and the independent checker agree, but both were written from one reading of
the rules, so they could share a misreading. PolicyEngine is a third implementation maintained by other people, used
in published policy analysis, so where it agrees the key does not rest on this project's own reading.

Covers every task whose answer is federal income tax or taxable Social Security (the Medicare part of the *_all_in
tasks is checked against the CMS table by the other layers; PolicyEngine is used for their tax part and AGI).
Not covered: rmd, ss_claim, irmaa and the compliance tasks, which PolicyEngine doesn't model.

Run with its own environment (PolicyEngine pins its own numpy):
  .venv-pe/bin/python -I checks/policyengine_check.py [cases.jsonl]
Writes checks/POLICYENGINE.md and checks/policyengine.json. Fails below 99% agreement or on any unexplained miss.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
YEAR = "2026"
OLD, YOUNG = 70, 50  # ages used for "65 or older" and "under 65"
TOL = 2  # dollars, the key's own tolerance on tax answers


def household(filing, over65, ordinary, ltcg, ss, wages=0):
    """A PolicyEngine household. Income sits with the first person; with one spouse over 65, that is the older one."""
    n = 2 if filing == "mfj" else 1
    ages = [OLD if k < over65 else YOUNG for k in range(n)]
    people = {}
    for k in range(n):
        first = k == 0
        people[k] = {"age": {YEAR: ages[k]}, "taxable_ira_distributions": {YEAR: ordinary if first else 0},
                     "long_term_capital_gains": {YEAR: ltcg if first else 0}, "social_security_retirement": {YEAR: ss if first else 0},
                     "employment_income": {YEAR: wages if first else 0}}
    return people


class Batch:
    """Many households in one PolicyEngine simulation; one run takes about a minute instead of one per case."""

    def __init__(self):
        self.homes = []

    def add(self, **kw):
        self.homes.append(household(**kw))
        return len(self.homes) - 1

    def run(self):
        from policyengine_us import Simulation

        sit = {k: {} for k in ("people", "tax_units", "families", "spm_units", "households", "marital_units")}
        for h, people in enumerate(self.homes):
            names = [f"h{h}p{k}" for k in people]
            for k, p in people.items():
                sit["people"][f"h{h}p{k}"] = p
            for g in ("tax_units", "families", "spm_units"):
                sit[g][f"h{h}"] = {"members": names}
            sit["households"][f"h{h}"] = {"members": names, "state_code": {YEAR: "TX"}}  # no state income tax
            sit["marital_units"][f"h{h}"] = {"members": names}
        sim = Simulation(situation=sit)
        # Prompts say "no credits" and "including any Net Investment Income Tax". PolicyEngine's tax before credits is
        # main rates + capital gains rates + AMT, with NIIT computed separately, so add it back.
        self.niit = sim.calculate("net_investment_income_tax", int(YEAR)).tolist()
        self.tax = [t + n for t, n in zip(sim.calculate("income_tax_before_credits", int(YEAR)).tolist(), self.niit)]
        self.amt = sim.calculate("alternative_minimum_tax", int(YEAR)).tolist()
        self.agi = sim.calculate("adjusted_gross_income", int(YEAR)).tolist()
        self.taxable = sim.calculate("taxable_income", int(YEAR)).tolist()
        self.tss = sim.calculate("tax_unit_taxable_social_security", int(YEAR)).tolist()  # the person-level one is per spouse


TOPS = {"mfj": {0.12: 100800, 0.22: 211400, 0.24: 403550}, "single": {0.12: 50400, 0.22: 105700, 0.24: 201775}}


def plan(c, b):
    """Queue the households a case needs; returns a function that turns PolicyEngine's results into the answer."""
    i, t = c["inputs"], c["task"]
    if t in ("federal_tax", "senior_phaseout"):
        h = b.add(filing=i["filing"], over65=i["over65"], ordinary=i["ordinary"], ltcg=i["ltcg"], ss=i["ss"], wages=i.get("wages", 0))
        return lambda: b.tax[h], c["answer"]
    if t == "taxable_ss":
        h = b.add(filing=i["filing"], over65=0, ordinary=i["other"], ltcg=0, ss=i["ss"])
        return lambda: b.tss[h], c["answer"]
    if t == "bracket_room":
        h = b.add(filing=i["filing"], over65=0, ordinary=i["ordinary"], ltcg=0, ss=0)
        return lambda: max(0.0, TOPS[i["filing"]][i["rate"]] - b.taxable[h]), c["answer"]
    if t in ("tax_torpedo", "conversion_all_in"):
        base = dict(filing=i["filing"], over65=i["over65"], ltcg=i["ltcg"], ss=i["ss"])
        h0, h1 = b.add(ordinary=i["ordinary"], **base), b.add(ordinary=i["ordinary"] + i["conversion"], **base)
        # conversion_all_in: its tax part is the case's "naive" answer (the Medicare part is checked elsewhere).
        return lambda: b.tax[h1] - b.tax[h0], c["answer"] if t == "tax_torpedo" else c["naive"]
    if t in ("widow_penalty", "widow_all_in"):
        h0 = b.add(filing="mfj", over65=2, ordinary=i["ordinary"], ltcg=i["ltcg"], ss=i["ssA"] + i["ssB"])
        h1 = b.add(filing="single", over65=1, ordinary=i["ordinary"], ltcg=i["ltcg"], ss=max(i["ssA"], i["ssB"]))
        return lambda: b.tax[h1] - b.tax[h0], c["answer"] if t == "widow_penalty" else c["naive"]
    return None


def main(path, out_name="POLICYENGINE"):
    cases = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    b = Batch()
    planned = [(c, plan(c, b)) for c in cases]
    planned = [(c, p) for c, p in planned if p]
    b.run()

    by_task = defaultdict(lambda: [0, 0])
    misses = []
    for c, (get, key) in planned:
        pe = get()
        ok = abs(round(pe) - key) <= TOL
        by_task[c["task"]][0] += ok
        by_task[c["task"]][1] += 1
        if not ok:
            misses.append({"id": c["id"], "task": c["task"], "key": key, "policyengine": round(pe, 2), "off_by": round(pe - key, 2), "inputs": c["inputs"]})
    agree = sum(v[0] for v in by_task.values())
    total = sum(v[1] for v in by_task.values())
    amt_cases = sum(1 for x in b.amt if x > 0.5)
    rate = agree / total if total else 0
    ok = rate >= 0.99 and not misses

    md = ["# PolicyEngine-US check", "",
          "Every tax answer recomputed by [PolicyEngine-US](https://github.com/PolicyEngine/policyengine-us), an open-source tax model "
          "this project didn't write. It's an outside reading of the same IRS rules.", "",
          f"**{'PASS' if ok else 'FAIL'}: {agree:,}/{total:,} agree within ${TOL}** ({rate:.2%}). Households where PolicyEngine "
          f"found alternative minimum tax: {amt_cases}.", "",
          "| Task | Agree | What PolicyEngine computes |", "|---|---|---|"]
    what = {"federal_tax": "income tax before credits", "senior_phaseout": "income tax before credits", "taxable_ss": "taxable Social Security",
            "bracket_room": "taxable income → room to the bracket top", "tax_torpedo": "tax with − without the conversion",
            "conversion_all_in": "tax part (Medicare part checked against CMS elsewhere)", "widow_penalty": "survivor's tax − couple's tax",
            "widow_all_in": "tax part (Medicare part checked against CMS elsewhere)"}
    md += [f"| {t} | {a}/{n} | {what[t]} |" for t, (a, n) in sorted(by_task.items())]
    md += ["", "Not covered: rmd, ss_claim, irmaa and the compliance tasks (PolicyEngine doesn't model them). Those rest on the golden set and the two-way check.", ""]
    if misses:
        md += ["## Disagreements", "", "| Case | Key | PolicyEngine | Off by |", "|---|---|---|---|"]
        md += [f"| `{m['id']}` | {m['key']:,} | {m['policyengine']:,} | {m['off_by']:+,} |" for m in misses[:100]]
        md += ["", "Off-by patterns: " + ", ".join(f"{k}: {v}" for k, v in Counter(m["task"] for m in misses).most_common())]
    (ROOT / "checks" / f"{out_name}.md").write_text("\n".join(md) + "\n")
    (ROOT / "checks" / f"{out_name.lower()}.json").write_text(json.dumps({"pass": ok, "agree": agree, "total": total, "by_task": by_task, "misses": misses}, indent=1) + "\n")
    print("\n".join(md[4:5] + md[8:8 + len(by_task)]))
    for m in misses[:15]:
        print(f"  MISS {m['id']}: key {m['key']} vs PolicyEngine {m['policyengine']} {m['inputs']}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "data" / "cases.jsonl", *sys.argv[2:3])
