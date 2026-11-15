"""Import GPT-6 Luna's answers (taken through Codex on a ChatGPT subscription, 2026-11-15) into the run formats the
graders already read, so the same graders and answer keys score it.

How the answers were collected: Codex agents (model gpt-6-luna, reasoning effort medium) each got one batch of
prompts with opaque ids (q001...) and no answer fields, and were told to answer each as its own chat, one at a time,
showing their reasoning, with no code, no calculator, no web and no other files. Sets: the 140 first-test questions the
Claude runs used, the 42 hard questions, the 70 wrong-facts notes (each planted-mistake note in a different batch from
its clean twin) and the 11 whole-household questions of the first Gauntlet run.
Attempt 1 (batches of 11-35) was discarded: most replies were a bare "ANSWER: n" with no reasoning, which is not how
the model answers a person in a chat. Its outputs are kept in v2/runs/luna-map/attempt1/. Attempt 2: 27 batches of
5-11, plus one fill-in batch (fill-01) for questions an agent skipped, declined as a whole batch, or wrote malformed. The opaque-id map is
v2/runs/luna-map/map.json; the raw agent outputs are copied to v2/runs/luna-map/out/.

  .venv/bin/python src/luna_import.py <dir with out/*.jsonl>

Writes runs/luna-codex-10x1/ (first test), runs/luna-gauntlet/ (whole-household), v2/runs/luna-codex/raw.jsonl
(hard + wrong facts) and v2/runs/luna-codex/judge_todo.jsonl (the judge prompts, same rubric as v2/grade.py).
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "v2"))
import grade as v2grade  # noqa: E402  (RUBRIC, RUBRIC_CONTROL, answer)

MODEL = "codex:gpt-6-luna"
EFFORT = "medium"


def load(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def main(src):
    src = Path(src)
    mp = json.loads((ROOT / "v2/runs/luna-map/map.json").read_text())
    keep = ROOT / "v2/runs/luna-map/out"
    keep.mkdir(parents=True, exist_ok=True)
    got = {}
    broken = 0
    for p in sorted((src / "out").glob("*.jsonl")):  # first valid answer per question wins; fill-01 only holds questions that had none
        shutil.copy(p, keep / p.name)
        for l in p.read_text().splitlines():
            try:
                r = json.loads(l)
            except ValueError:
                broken += 1  # a malformed line the agent wrote; its question was re-asked in a fill-in batch
                continue
            if (r.get("text") or "").strip():
                got.setdefault(r["qid"], r["text"])
    print(f"skipped {broken} malformed lines")
    missing = sorted(set(mp) - set(got))
    print(f"{len(got)} answers for {len(mp)} questions; missing: {missing or 'none'}")

    cases = {c["id"]: c for c in load(ROOT / "data/cases.jsonl")}
    bad = {i["id"]: i for i in load(ROOT / "v2/data/bad_inputs.jsonl")}
    rows = {"v1": [], "hard": [], "bad": [], "gauntlet": []}
    for qid, m in mp.items():
        if qid not in got:
            continue
        base = {"model": MODEL, "effort": EFFORT, "id": m["id"], "rep": 0, "text": got[qid], "stop_reason": "stop", "via": "codex (ChatGPT subscription)", "qid": qid}
        if m["set"] == "v1":
            rows["v1"].append({**base, "task": cases[m["id"]]["task"]})
        elif m["set"] == "gauntlet":
            rows["gauntlet"].append({**base, "task": "gauntlet"})
        else:
            rows[m["set"]].append({**base, "set": m["set"]})

    meta = {"model": MODEL, "effort": EFFORT, "via": "Codex agent on a ChatGPT subscription, batches of 11-35 prompts per agent session, no code/web/files, no token limit set",
            "date": "2026-11-15", "note": "Not the same setup as the API runs (one message per question, fixed token limits). Reported separately."}
    for name, key in (("runs/luna-codex-10x1", "v1"), ("runs/luna-gauntlet", "gauntlet")):
        d = ROOT / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "raw.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows[key]))
        (d / "meta.json").write_text(json.dumps({**meta, "max_tokens": None}, indent=1) + "\n")
    d = ROOT / "v2/runs/luna-codex"
    d.mkdir(parents=True, exist_ok=True)
    (d / "raw.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows["hard"] + rows["bad"]))
    (d / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    todo = []
    for r in rows["bad"]:
        it = bad[r["id"]]
        if it["kind"] == "corrupted":
            todo.append({"id": r["id"], "kind": "corrupted", "prompt": v2grade.RUBRIC.format(planted=it["planted"], reply=r["text"][-6000:])})
        elif v2grade.answer(r["text"])[0] == "need_info":
            todo.append({"id": r["id"], "kind": "control", "prompt": v2grade.RUBRIC_CONTROL.format(reply=r["text"][-6000:])})
    (d / "judge_todo.jsonl").write_text("".join(json.dumps(t) + "\n" for t in todo))
    print({k: len(v) for k, v in rows.items()}, f"judge prompts: {len(todo)}")


if __name__ == "__main__":
    main(sys.argv[1])
