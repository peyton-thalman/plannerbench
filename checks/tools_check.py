"""Tools check: can a perfect tool user answer every numeric question from the MoneyGuide MCP tools alone?

For each case, src/planning_tools.oracle() composes the answer from MCP tool calls (no engine imports, no math of
its own beyond adding and subtracting tool results) and compares it with the answer key. Every case must match
within its tolerance, or the "Claude + planning tools" runs don't ship: a model's miss there must be the model's,
never a gap or a bug in the tools. Compliance tasks have no tools and are skipped.

Usage: .venv/bin/python -I checks/tools_check.py            (public set, plus the private set when it is on this machine)
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from planning_tools import PlanningTools, oracle  # noqa: E402


def check(tools, path):
    cases = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    passed, failed, skipped = Counter(), [], 0
    for c in cases:
        got = oracle(tools, c)
        if got is None:
            skipped += 1
        elif abs(got - c["answer"]) <= c["tol"]:
            passed[c["task"]] += 1
        else:
            failed.append((c["id"], got, c["answer"]))
    return cases, passed, failed, skipped


def main():
    tools = PlanningTools()
    print(f"MCP server {tools.server_info['name']} {tools.server_info['version']}: {', '.join(t['name'] for t in tools.tools)}")
    ok = True
    for split, path in (("public", ROOT / "data" / "cases.jsonl"), ("private", ROOT / "private" / "cases.jsonl")):
        if not path.exists():
            print(f"{split}: not on this machine, skipped")
            continue
        cases, passed, failed, skipped = check(tools, path)
        n = sum(passed.values()) + len(failed)
        print(f"{split}: {sum(passed.values())}/{n} numeric answers reproduced from tool calls alone ({skipped} compliance cases have no tools)")
        if split == "public":  # per-task counts are fine to print for the public set only
            print("  " + ", ".join(f"{k} {v}" for k, v in sorted(passed.items())))
        for cid, got, want in failed[:10]:
            print(f"  FAIL {cid if split == 'public' else '(private)'}: tools give {got}, key says {want}")
        ok &= not failed
    tools.close()
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
