"""Harness check: does asking a model through OpenRouter change its score?

The same model (Claude Haiku 5.5) is asked the same questions two ways: directly through the Anthropic API and
through OpenRouter pinned to Anthropic. If the OpenRouter path changed scores (a different prompt wrapper, a
reasoning setting that didn't map, a parsing difference), the two would disagree more than run-to-run noise allows,
and no OpenRouter number should be published.

Pass: no significant difference on the shared questions (exact McNemar p > 0.05).
Usage: .venv/bin/python -I checks/harness_check.py <direct run> <openrouter run>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from stats import mcnemar, wilson  # noqa: E402

PAIRS = [("claude-haiku-5-5", "or:anthropic/claude-haiku-5.5@anthropic")]


def outcomes(run, model):
    rows = (json.loads(l) for l in (ROOT / "runs" / run / "graded.jsonl").read_text().splitlines() if l.strip())
    return {g["id"]: g["bucket"] == "correct" for g in rows if g["model"] == model and g["rep"] == 0 and g["bucket"] != "error"}


def main(direct_run, or_run):
    md = ["# Harness check: direct API vs. OpenRouter", "",
          "The same model asked the same questions both ways. Pass means no significant difference (exact McNemar p > 0.05).", "",
          "| Model | Shared questions | Direct | OpenRouter | Flipped (direct right only / OpenRouter right only) | p | Result |", "|---|---|---|---|---|---|---|"]
    ok = True
    rows = []
    for direct, routed in PAIRS:
        a, b = outcomes(direct_run, direct), outcomes(or_run, routed)
        shared = sorted(a.keys() & b.keys())
        if not shared:
            md.append(f"| {direct} | 0 | | | | | not run |")
            ok = False
            continue
        ka, kb = sum(a[i] for i in shared), sum(b[i] for i in shared)
        only_a = sum(a[i] and not b[i] for i in shared)
        only_b = sum(b[i] and not a[i] for i in shared)
        p = mcnemar([(a[i], b[i]) for i in shared])
        passed = p > 0.05
        ok &= passed
        fmt = lambda k: f"{k / len(shared):.0%} [{wilson(k, len(shared))[0]:.0%}–{wilson(k, len(shared))[1]:.0%}]"
        rows.append({"direct": direct, "openrouter": routed, "questions": len(shared), "direct_accuracy": round(ka / len(shared), 4),
                     "openrouter_accuracy": round(kb / len(shared), 4), "p_value": round(p, 4), "pass": passed})
        md.append(f"| {direct} | {len(shared)} | {fmt(ka)} | {fmt(kb)} | {only_a} / {only_b} | {p:.3f} | {'PASS' if passed else 'FAIL'} |")
    md += ["", f"Runs: `{direct_run}` (direct) and `{or_run}` (OpenRouter)."]
    (ROOT / "checks" / "HARNESS.md").write_text("\n".join(md) + "\n")
    (ROOT / "leaderboard" / "harness.json").write_text(json.dumps(rows, indent=1) + "\n")
    print("\n".join(md))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
