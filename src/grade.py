"""Grade a run: compare each model's ANSWER line to the key, then write runs/<run>/REPORT.md.

Every reply lands in exactly one bucket:
  correct    within the case's tolerance
  wrong      a number, but not the right one
  no_answer  no parsable "ANSWER:" line (kept apart so format slips don't look like math errors)
  refusal    the model declined
  error      the API call failed (excluded from accuracy; rerun to fill in)

Usage: .venv/bin/python src/grade.py <run>
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
# Tolerates markdown bold around the label ("**ANSWER:** 42,268") and a leading $; the last match wins.
ANSWER = re.compile(r"ANSWER\**\s*:\s*\**\s*\$?\s*(-?[\d,]*\.?\d+)", re.IGNORECASE)


ANSWER_LINE = re.compile(r"ANSWER\**\s*:\s*\**\s*([^\n]*)", re.IGNORECASE)


def parse(text):
    hits = ANSWER.findall(text or "")
    return float(hits[-1].replace(",", "")) if hits else None


def parse_set(text):
    """Compliance answers: codes or sentence numbers, in any order and case, written back as the key writes them."""
    hits = ANSWER_LINE.findall(text or "")
    if not hits:
        return None
    items = {t.strip("*.`\"' ").upper() for t in re.split(r"[,;\s]+|\band\b", hits[-1])} - {""}
    if items <= {"NONE"}:
        return "NONE" if items else None
    items.discard("NONE")
    return ",".join(sorted(items, key=lambda t: (not t.isdigit(), int(t) if t.isdigit() else 0, t)))


sys.path.insert(0, str(ROOT / "checks"))
import independent_check as ic  # noqa: E402

# Named mistakes, checked in order: a wrong answer matching what a known misreading produces gets that label.
MISTAKES = ["combined senior phase-out", "left out Medicare", "one-step shortcut", "counted adult child", "counted other fund family",
            "missed a violation", "flagged a compliant sentence", "missed an issue", "flagged a non-issue"]


def mistake(got, case):
    if isinstance(case["answer"], str):
        # Code sets: say which way the answer is off (an answer can be off both ways; missing one is the costlier miss).
        key, mine = set(case["answer"].split(",")) - {"NONE"}, set(got.split(",")) - {"NONE"}
        missed = "missed a violation" if case["task"] == "comms_review" else "missed an issue"
        extra = "flagged a compliant sentence" if case["task"] == "comms_review" else "flagged a non-issue"
        return missed if key - mine else extra
    near = lambda x: abs(got - x) <= case["tol"]
    if near(ic.answer_if_misread("combined_senior_phaseout", case)) and not near(case["answer"]):
        return "combined senior phase-out"
    for name, value in case.get("misreadings", {}).items():
        if near(value):
            return name
    if "naive" in case and near(case["naive"]):
        return "left out Medicare" if case["task"].endswith("_all_in") else "one-step shortcut"
    return None


def fmt(x):
    return f"{x:,.2f}" if isinstance(x, (int, float)) else str(x)


def bucket(rec, case):
    if "error" in rec:
        return "error", None
    if rec.get("stop_reason") == "refusal":
        return "refusal", None
    got = parse_set(rec.get("text")) if isinstance(case["answer"], str) else parse(rec.get("text"))
    if got is None:
        return "no_answer", None
    return ("correct" if ic.agrees(got, case) else "wrong"), got


def main(run):
    run_dir = ROOT / "runs" / run
    cases = {c["id"]: c for c in (json.loads(l) for l in (ROOT / "data" / "cases.jsonl").read_text().splitlines() if l.strip())}
    recs = [json.loads(l) for l in (run_dir / "raw.jsonl").read_text().splitlines() if l.strip()]
    # Keep the last attempt per (model, case, rep): a resumed run may have retried an error.
    latest = {(r["model"], r["id"], r["rep"]): r for r in recs}

    graded = []
    for r in latest.values():
        b, got = bucket(r, cases[r["id"]])
        graded.append({**r, "bucket": b, "got": got, "key": cases[r["id"]]["answer"], "mistake": mistake(got, cases[r["id"]]) if b == "wrong" else None})
    (run_dir / "graded.jsonl").write_text("".join(json.dumps(g) + "\n" for g in graded))

    models = sorted({g["model"] for g in graded})
    tasks = sorted({g["task"] for g in graded})
    acc = lambda rows: (sum(r["bucket"] == "correct" for r in rows), sum(r["bucket"] != "error" for r in rows))
    pct = lambda k, n: f"{100 * k / n:.0f}% ({k}/{n})" if n else "n/a"

    md = [f"# PlannerBench results: {run}", ""]
    md += ["## Accuracy by task", "", "| Task | " + " | ".join(models) + " |", "|---|" + "---|" * len(models)]
    for t in tasks:
        md.append(f"| {t} | " + " | ".join(pct(*acc([g for g in graded if g["model"] == m and g["task"] == t])) for m in models) + " |")
    md.append("| **Overall** | " + " | ".join(f"**{pct(*acc([g for g in graded if g['model'] == m]))}**" for m in models) + " |")

    md += ["", "## Where replies landed", "", "| Model | correct | wrong | no_answer | refusal | error |", "|---|---|---|---|---|---|"]
    for m in models:
        c = Counter(g["bucket"] for g in graded if g["model"] == m)
        md.append(f"| {m} | {c['correct']} | {c['wrong']} | {c['no_answer']} | {c['refusal']} | {c['error']} |")

    # Consistency: with reps > 1, how often does a model give the same answer to the same question?
    by_case = defaultdict(list)
    for g in graded:
        if g["bucket"] in ("correct", "wrong"):
            by_case[(g["model"], g["id"])].append(g["got"])
    multi = {k: v for k, v in by_case.items() if len(v) > 1}
    if multi:
        md += ["", "## Consistency (same question, repeated)", ""]
        for m in models:
            rows = [v for (mm, _), v in multi.items() if mm == m]
            if rows:
                md.append(f"- {m}: same answer every time on {sum(len(set(v)) == 1 for v in rows)}/{len(rows)} questions")

    # Trust layer 6: when different models land on the same wrong number, suspect the key or the wording first.
    wrong_votes = defaultdict(lambda: defaultdict(set))
    for g in graded:
        if g["bucket"] == "wrong":
            wrong_votes[g["id"]][g["got"]].add(g["model"])
    review = [(cid, val, sorted(ms)) for cid, vals in wrong_votes.items() for val, ms in vals.items() if len(ms) >= 2]
    md += ["", "## Review queue (different models agree with each other, not the key)", ""]
    md += [f"- `{cid}`: {', '.join(ms)} all said {fmt(val)}; key says {fmt(cases[cid]['answer'])}" for cid, val, ms in sorted(review)] or [
        "None." if len(models) > 1 else "Needs two or more models to run."]

    md += ["", "## Mistakes by type", "", "| Model | " + " | ".join(MISTAKES) + " | unexplained |", "|---|" + "---|" * (len(MISTAKES) + 1)]
    for m in models:
        c = Counter(g["mistake"] or "unexplained" for g in graded if g["model"] == m and g["bucket"] == "wrong")
        md.append(f"| {m} | " + " | ".join(str(c[k]) for k in [*MISTAKES, "unexplained"]) + " |")

    md += ["", "## Wrong answers", "", "| Case | Model | Key | Got | Off by | Mistake |", "|---|---|---|---|---|---|"]
    for g in sorted((g for g in graded if g["bucket"] == "wrong"), key=lambda g: (g["task"], g["id"]))[:80]:
        md.append(f"| `{g['id']}` | {g['model']} | {fmt(g['key'])} | {fmt(g['got'])} | {f"{g['got'] - g['key']:+,.2f}" if isinstance(g['key'], (int, float)) else ''} | {g['mistake'] or ''} |")

    (run_dir / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:4 + len(tasks) + 2]))
    print(f"\nFull report: runs/{run}/REPORT.md")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fake-high-10x1")
