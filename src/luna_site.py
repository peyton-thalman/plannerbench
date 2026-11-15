"""GPT-6 Luna (ChatGPT subscription, via Codex) results for the site: web/data/luna.json.

  .venv/bin/python src/grade.py luna-codex-10x1 && .venv/bin/python src/gauntlet_grade.py luna-gauntlet \
    && .venv/bin/python v2/luna_grade.py && .venv/bin/python src/luna_site.py

Combines the first-test grades (runs/luna-codex-10x1/graded.jsonl), the whole-household grades
(runs/luna-gauntlet/graded.jsonl) and v2/results/luna.json. Free; reads saved files only.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from stats import wilson  # noqa: E402

TIERS = {"single_step": ["federal_tax", "taxable_ss", "rmd", "ss_claim", "bracket_room", "irmaa"],
         "multi_step": ["tax_torpedo", "widow_penalty"],
         "stacked": ["conversion_all_in", "senior_phaseout", "widow_all_in"],  # same tiers as leaderboard/tasks.json
         "compliance": ["rollover_flags", "breakpoint", "comms_review"]}


def load(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def r_(k, n):
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "lo": round(lo, 4) if n else None, "hi": round(hi, 4) if n else None}


def main():
    v1 = load(ROOT / "runs/luna-codex-10x1/graded.jsonl")
    first = {t: r_(sum(g["bucket"] == "correct" for g in v1 if g["task"] in ts), sum(g["task"] in ts for g in v1)) for t, ts in TIERS.items()}
    first["overall"] = r_(sum(g["bucket"] == "correct" for g in v1), len(v1))
    first["asked_of"] = 140
    gp = ROOT / "runs/luna-gauntlet/gauntlet_graded.jsonl"
    ga = load(gp) if gp.exists() else []
    great = sum(bool(g.get("great")) for g in ga)
    declined = sum(g["decision"]["why"] == "declined an answerable question" for g in ga)
    trap_ok = sum(g["family"] == "trap" and g["great"] for g in ga)
    v2 = json.loads((ROOT / "v2/results/luna.json").read_text())
    out = {"model": "GPT-6 Luna", "via": "ChatGPT subscription (through Codex)", "effort": "medium", "date": "2026-11-15",
           "first_test": first,
           "household": {"great": great, "n": len(ga), "declined_answerable": declined, "trap_declined": trap_ok},
           "hard": v2["hard"], "bad": v2["bad"], "setup_note": v2["setup_note"],
           "source": "runs/luna-codex-10x1, runs/luna-gauntlet, v2/results/luna.json (src/luna_import.py, v2/runs/luna-map/)"}
    (ROOT / "web/data/luna.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: (v["rate"] if isinstance(v, dict) and "rate" in v else v) for k, v in first.items()}), out["household"], "hard", v2["hard"]["rate"])


if __name__ == "__main__":
    main()
