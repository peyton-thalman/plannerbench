"""Copy the leaderboard data and a few real example questions into site/data/ for the public site.

Usage: .venv/bin/python src/build_site.py live-high-10x1 [with-rule-10x1]
Run src/leaderboard.py first; the site reads only what this writes.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from leaderboard import TIER  # noqa: E402

sys.path.insert(0, str(ROOT / "checks"))
import independent_check as ic  # noqa: E402

# One question per tier, chosen to show the kind of reasoning each tier asks for.
EXAMPLES = [
    ("federal_tax-000", "A full 2026 federal return, in one step"),
    ("tax_torpedo-005", "A Roth conversion that also makes Social Security taxable"),
    ("senior_phaseout-000", "Retirees inside the new senior-deduction phase-out"),
    ("comms_review-000", "Spotting Rule 2210 violations in a client email"),
]
# The one case the site walks through line by line.
FEATURED = "senior_phaseout-000"


def short_prompt(p):
    # The rules preamble and the answer-format line are the same on every question; the site states them once.
    p = p.split(" End your reply")[0]
    for pre in ("Use 2026 federal tax law (IRS Rev. Proc. 2025-32 and the One Big Beautiful Bill Act, including the $6,000 senior deduction). ",
                "Use the 2026 CMS Part B premiums and IRMAA tiers. There is no tax-exempt interest, so MAGI for IRMAA equals AGI. "):
        p = p.replace(pre, "")
    return p.strip()


def steps(c):
    """The featured case worked both ways: the Schedule 1-A reading the key uses, and the reading the models used."""
    i = c["inputs"]
    f, n = i["filing"], i["over65"]
    agi = ic.household_agi(f, i["ordinary"], i["ltcg"], i["ss"])
    cut = 0.06 * max(0.0, agi - ic.SENIOR_START[f])
    return {"agi": round(agi, 2), "threshold": ic.SENIOR_START[f], "cut": round(cut, 2),
            "per_spouse": round(max(0.0, 6000 - cut) * n, 2), "combined": round(max(0.0, 6000 * n - cut), 2),
            "tax_key": c["answer"], "tax_combined": ic.answer_if_misread("combined_senior_phaseout", c)}


def replies(run):
    """First-run replies by (model, case), from one run or several joined with "+"."""
    out = {}
    for r in run.split("+"):
        path = ROOT / "runs" / r / "graded.jsonl"
        if path.exists():
            out.update({(g["model"], g["id"]): g for g in (json.loads(l) for l in path.read_text().splitlines() if l.strip()) if g["rep"] == 0})
    return out


def main(run, rule_run=None):
    out = ROOT / "site" / "data"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("models", "tasks", "mistakes", "dollars_by_mistake", "rule_effect", "harness"):
        src = ROOT / "leaderboard" / f"{name}.json"
        if src.exists():
            shutil.copy(src, out / f"{name}.json")

    cases = {c["id"]: c for c in (json.loads(l) for l in (ROOT / "data" / "cases.jsonl").read_text().splitlines() if l.strip())}
    base, ruled = replies(run), replies(rule_run) if rule_run else {}
    models = sorted({m for m, _ in base})

    def answers(cid, src):
        return {m: {"got": src[(m, cid)]["got"], "bucket": src[(m, cid)]["bucket"], "mistake": src[(m, cid)].get("mistake")}
                for m in models if (m, cid) in src}

    examples = [{"id": cid, "task": cases[cid]["task"], "tier": TIER[cases[cid]["task"]], "title": title,
                 "prompt": short_prompt(cases[cid]["prompt"]), "answer": cases[cid]["answer"], "replies": answers(cid, base)}
                for cid, title in EXAMPLES]
    c = cases[FEATURED]
    featured = {"id": FEATURED, "prompt": short_prompt(c["prompt"]), "inputs": c["inputs"], "answer": c["answer"],
                "replies": answers(FEATURED, base), "with_rule": answers(FEATURED, ruled), "steps": steps(c)}

    by_tier = {}
    for cid, case in cases.items():
        by_tier.setdefault(TIER[case["task"]], set()).add(case["task"])
    meta = {"questions": len(cases), "tasks": len({c["task"] for c in cases.values()}), "run": run, "rule_run": rule_run,
            "tiers": {t: sorted(ts) for t, ts in by_tier.items()}}

    for name, data in (("examples", examples), ("featured", featured), ("meta", meta)):
        (out / f"{name}.json").write_text(json.dumps(data, indent=1) + "\n")
    print(f"Wrote site/data/ from runs {run}" + (f" and {rule_run}" if rule_run else "") + f": {meta['questions']} questions, {meta['tasks']} tasks")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "live-high-10x1", sys.argv[2] if len(sys.argv) > 2 else None)
