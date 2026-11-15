"""Grade GPT-6 Luna (through Codex on a ChatGPT subscription) on the newer set and the wrong-facts notes, with the same
rules as v2/grade.py, and write v2/results/luna.json. Free: reads saved replies and judge labels only.

  .venv/bin/python v2/luna_grade.py

Inputs: v2/runs/luna-codex/raw.jsonl (src/luna_import.py), v2/runs/luna-codex/judge.jsonl (same rubric as the main
judge, judged by Claude Haiku 5.5), v2/runs/luna-codex/adjudication.jsonl (optional; same rule as ADJUDICATION.md).
Luna's setup differs from the API runs (agent session, batches, medium effort, no token limit), so it is reported
next to them, not merged into v2/results/summary.json.
"""
import json
import sys
from collections import Counter
from pathlib import Path

V2 = Path(__file__).parent
sys.path.insert(0, str(V2))
import grade as g  # noqa: E402

RUN = V2 / "runs" / "luna-codex"


def main():
    raw = g.load(RUN / "raw.jsonl")
    hard_items = {i["id"]: i for i in g.load(V2 / "data" / "hard.jsonl")}
    bad_items = {i["id"]: i for i in g.load(V2 / "data" / "bad_inputs.jsonl")}
    judged = {j["id"]: j for j in g.load(RUN / "judge.jsonl")}
    adj = {a["id"]: a for a in g.load(RUN / "adjudication.jsonl")}

    hard = []
    for r in (r for r in raw if r["set"] == "hard"):
        it = hard_items[r["id"]]
        kind, x = g.answer(r["text"])
        b = "correct" if kind == "number" and abs(x - it["answer"]) <= it["tol"] else "wrong" if kind == "number" else "no_answer"
        hard.append({"id": r["id"], "family": it["family"], "bucket": b, "got": x, "key": it["answer"]})

    cor, ctl = [], []
    for r in (r for r in raw if r["set"] == "bad"):
        it = bad_items[r["id"]]
        kind, x = g.answer(r["text"])
        if it["kind"] == "corrupted":
            j = judged.get(r["id"])
            flag_j = bool(j and j.get("flagged"))
            flag = adj[r["id"]]["adjudicated_flagged"] if r["id"] in adj else flag_j
            out = lambda f: "caught" if f and kind != "number" else "flagged_but_answered" if f else "silent_number" if kind == "number" else "declined_other_reason"
            cor.append({"id": r["id"], "type": it["type"], "outcome": out(flag), "outcome_judge": out(flag_j), "judged": j is not None,
                        "asked": bool(j and j.get("asked")), "flagged": flag})
        else:
            j = judged.get(r["id"])
            ctl.append({"id": r["id"], "kind": it["kind"], "correct": kind == "number" and abs(x - it["answer"]) <= it["tol"],
                        "false_alarm": kind == "need_info", "decline_reason": (j or {}).get("reason") if kind == "need_info" else None})

    def r_(k, n):
        lo, hi = g.wilson(k, n)
        return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "lo": round(lo, 4), "hi": round(hi, 4)}

    oc = Counter(c["outcome"] for c in cor)
    ocj = Counter(c["outcome_judge"] for c in cor)
    clean = [c for c in ctl if c["kind"] == "clean"]
    by_type = {t: r_(sum(c["outcome"] == "caught" for c in cor if c["type"] == t), sum(c["type"] == t for c in cor)) for t in g.TYPES}
    fam = sorted({h["family"] for h in hard})
    out = {
        "model": "GPT-6 Luna", "via": "Codex agent, ChatGPT subscription", "effort": "medium", "date": "2026-11-15",
        "setup_note": "Answered in agent sessions of 11-35 prompts each, told to treat each as its own chat, no code, web or files; no token limit. The 11 API models got one message per question at low effort with a 4,000-token limit.",
        "hard": {**r_(sum(h["bucket"] == "correct" for h in hard), len(hard)), "no_answer": sum(h["bucket"] == "no_answer" for h in hard),
                 "by_family": {f: r_(sum(h["bucket"] == "correct" for h in hard if h["family"] == f), sum(h["family"] == f for h in hard)) for f in fam}},
        "bad": {"corrupted": len(cor), "judged": sum(c["judged"] for c in cor),
                **{o: r_(oc[o], len(cor)) for o in ("caught", "flagged_but_answered", "silent_number", "declined_other_reason")},
                "named": r_(sum(c["flagged"] for c in cor), len(cor)),
                "judge_only_caught": r_(ocj["caught"], len(cor)), "labels_changed": len(adj),
                "false_alarm": r_(sum(c["false_alarm"] for c in ctl), len(ctl)),
                "clean_correct": r_(sum(c["correct"] for c in clean), len(clean)),
                "decline_reasons": dict(Counter(c["decline_reason"] for c in ctl if c["false_alarm"])),
                "by_type": by_type},
    }
    (V2 / "results" / "luna.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"hard": out["hard"]["rate"], "caught": out["bad"]["caught"]["rate"], "noticed_answered": out["bad"]["flagged_but_answered"]["rate"],
                      "silent": out["bad"]["silent_number"]["rate"], "false_alarm": out["bad"]["false_alarm"]["rate"], "clean": out["bad"]["clean_correct"]["rate"]}))


if __name__ == "__main__":
    main()
