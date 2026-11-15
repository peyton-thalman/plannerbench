"""Rule-based pre-filter for adjudicating the judge's "named the planted problem" labels (see v2/results/ADJUDICATION.md).

  .venv/bin/python v2/adjudicate.py           # list candidates in both directions and check v2/runs/bad/adjudication.jsonl
  .venv/bin/python v2/adjudicate.py --show    # also print the matching sentences of each candidate, for reading

Free: reads saved replies and judge labels only. The pre-filter only picks which replies to read; every override in
adjudication.jsonl was decided by reading the reply, and carries the exact sentence that justifies it.

False-negative candidates (judge said flagged:false on a corrupted note with a non-empty reply) are replies with any of:
  1. a number from the planted fact that is not in the prompt (a legal limit, a yearly total, the impossible age);
  2. for a swapped-digit balance, both conflicting balances;
  3. the type's keyword pattern (grade.KEYWORDS);
  4. a verification or shortfall phrase (confirm, verify, clarify, typo, date of birth, cannot cover/fund, "only $X").
False-positive check (judge said flagged:true): the "caught" replies of the five models with the best net score and of
both Gemini models; a reply is printed with its sentence that best matches the planted problem, for reading.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import grade  # noqa: E402

V2 = Path(__file__).parent
NUMS = re.compile(r"\d[\d,]*")
ASK = r"confirm|verif|clarif|double-check|typo|date of birth|cannot (fully )?(cover|fund)|only \$[\d,]+"
TOP = ("claude-sonnet", "gpt-6.1-sol", "claude-haiku", "deepseek", "gpt-6.1-terra", "gemini")


def key_numbers(it):
    planted = {n.replace(",", "") for n in NUMS.findall(it["planted"])}
    prompt = {n.replace(",", "") for n in NUMS.findall(it["prompt"])}
    return {n for n in planted - prompt if (len(n) >= 3 or it["type"] == "impossible_age") and n not in ("2025", "2026", "12", "65")}


def hits(it, text):
    flat = text.replace(",", "")
    found = [n for n in key_numbers(it) if re.search(r"(?<!\d)" + n + r"(?!\d)", flat)]
    if it["type"] == "transposed" and "balance" in it["planted"]:
        both = {n.replace(",", "") for n in NUMS.findall(it["planted"]) if len(n.replace(",", "")) >= 5}
        if all(n in flat for n in both):
            found.append("both balances")
    found += [m.group(0) for m in re.finditer(grade.KEYWORDS[it["type"]], text, re.I)]
    found += [m.group(0) for m in re.finditer(ASK, text, re.I)]
    return found


def main():
    show = "--show" in sys.argv
    items = {i["id"]: i for i in grade.load(V2 / "data" / "bad_inputs.jsonl")}
    raw = grade.load(V2 / "runs" / "bad" / "raw.jsonl")
    judged = {(j["model"], j["id"], j["rep"]): j for j in grade.load(V2 / "runs" / "bad" / "judge.jsonl")}
    adj = {(a["model"], a["id"], a["rep"]): a for a in grade.load(V2 / "runs" / "bad" / "adjudication.jsonl")}
    neg, pos = [], []
    for n, r in enumerate(raw, 1):
        it = items[r["id"]]
        text = r.get("text") or ""
        if it["kind"] != "corrupted" or not text.strip():
            continue
        j = judged[(r["model"], r["id"], r["rep"])]
        if not j["flagged"]:
            h = hits(it, text)
            if h:
                neg.append((n, r, h))
        elif grade.answer(text)[0] != "number" and any(t in r["model"] for t in TOP):
            pos.append((n, r))
    print(f"false-negative candidates: {len(neg)} of {sum(1 for j in judged.values() if j.get('flagged') is False)} judged not flagged")
    print("  by model:", dict(Counter(r["model"].split("/")[1].split("@")[0] for _, r, _ in neg)))
    print(f"false-positive check: {len(pos)} caught replies read")
    if show:
        for n, r, h in neg:
            sents = [s for s in re.split(r"(?<=[.!?])\s+|\n+", r["text"]) if any(x.lower() in s.lower().replace(",", "") or x.lower() in s.lower() for x in h if x != "both balances")]
            print(f"\n### raw line {n} {r['model']} {r['id']} rep {r['rep']} {'OVERRIDDEN' if (r['model'], r['id'], r['rep']) in adj else ''}")
            for s in sents[:6]:
                print("  -", s[:350])
    # every override must point at a real reply, quote it exactly, and contradict the judge's label
    for (m, i, rep), a in adj.items():
        r = raw[a["raw_line"] - 1]
        assert (r["model"], r["id"], r["rep"]) == (m, i, rep), a
        assert a["quote"] in r["text"], a
        assert judged[(m, i, rep)]["flagged"] == a["judge_flagged"] != a["adjudicated_flagged"], a
    print(f"adjudication.jsonl: {len(adj)} overrides, all quotes found in the replies; directions:",
          dict(Counter(f"{a['judge_flagged']}->{a['adjudicated_flagged']}" for a in adj.values())))


if __name__ == "__main__":
    main()
