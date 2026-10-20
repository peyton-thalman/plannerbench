"""Site check: does the page people see show exactly the graded numbers?

Fetches the data files a deployed site serves and compares them field for field with leaderboard/, which
src/leaderboard.py builds from the graded runs. Any difference (a stale deploy, a hand edit, a build that skipped
a run) fails.

Usage: .venv/bin/python -I checks/site_check.py [https://plannerbench.vercel.app]
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

ROOT = Path(__file__).parent.parent
FILES = ["models", "tasks", "mistakes", "rule_effect", "harness"]


def main(base):
    bad = []
    for name in FILES:
        local = ROOT / "leaderboard" / f"{name}.json"
        if not local.exists():
            continue
        try:
            with urllib.request.urlopen(f"{base.rstrip('/')}/data/{name}.json?nocache", timeout=30) as r:
                live = json.loads(r.read())
        except urllib.error.HTTPError as e:
            live = f"HTTP {e.code}"
        if live != json.loads(local.read_text()):
            bad.append(name)
        print(f"[{'FAIL' if name in bad else 'PASS'}] {name}.json")
    print("PASS: the site serves exactly the graded numbers" if not bad else f"FAIL: {', '.join(bad)} differ from leaderboard/")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "https://plannerbench.vercel.app")
