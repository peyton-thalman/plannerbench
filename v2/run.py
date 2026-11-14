"""Ask models the PlannerBench v2 questions through OpenRouter and save every raw reply.

  .venv/bin/python v2/run.py --set bad --tier cheap --reps 3
  .venv/bin/python v2/run.py --set hard --models or:anthropic/claude-haiku-5.5@anthropic --reps 2
  .venv/bin/python v2/run.py --set hard --tools --tier cheap --reps 2          # same hard items, engine offered as tools
  .venv/bin/python v2/run.py --set bad --tier frontier --per-group 2           # first 2 items of each family/type

Replies go to v2/runs/<set>[-tools]/raw.jsonl as they arrive; rerunning the same command resumes.
Every dollar OpenRouter bills is added to v2/runs/ledger.json, and no request starts if it could carry the total
past the cap (default $4.80, under the owner's $5).
"""
import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
import run_models as rm  # noqa: E402  (reuses v1's OpenRouter calls, host pinning and tool loop unchanged)

V2 = ROOT / "v2"
LEDGER = V2 / "runs" / "ledger.json"
LINEUP = json.loads((V2 / "lineup.json").read_text())["models"]
SETS = {"hard": V2 / "data" / "hard.jsonl", "bad": V2 / "data" / "bad_inputs.jsonl"}
# The engine tools a hard item can need. plan_check and solve_roth_conversion are left out: 4.5k tokens of schema
# re-sent every turn, for a conversational front door and a solver no hard item uses.
TOOL_NAMES = ["federal_income_tax", "taxable_social_security", "required_minimum_distribution", "social_security_benefit",
              "medicare_part_b_premium", "tax_tables", "run_scenario"]


class ToolSubset:
    def __init__(self):
        from planning_tools import PlanningTools

        self.inner = PlanningTools()
        self.tools = [t for t in self.inner.tools if t["name"] in TOOL_NAMES]
        self.server_info = self.inner.server_info

    def call(self, name, args):
        if name not in TOOL_NAMES:
            return f"No such tool: {name}", True
        return self.inner.call(name, args)


def ledger():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {"spent_usd": 0.0, "by_run": {}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=list(SETS))
    ap.add_argument("--tools", action="store_true")
    ap.add_argument("--models", default=None, help="comma-separated or: ids (default: by --tier)")
    ap.add_argument("--tier", default=None, help="frontier, mid, cheap (comma-separated)")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--per-group", type=int, default=None, help="first N items of each family/type (and kind)")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--cap", type=float, default=4.80)
    ap.add_argument("--run", default=None)
    a = ap.parse_args()
    rm.MAX_TOKENS = a.max_tokens
    rm.MAX_TOOL_TURNS = 8
    known = {m["id"]: m for m in LINEUP}
    models = a.models.split(",") if a.models else [m["id"] for m in LINEUP if m["tier"] in (a.tier or "").split(",")]
    if not models:
        raise SystemExit("Name --models or --tier.")
    items = [json.loads(l) for l in SETS[a.set].read_text().splitlines()]
    if a.per_group:
        seen, keep = {}, []
        for i in items:
            g = (i.get("family") or i["type"], i.get("kind"))
            if seen.get(g, 0) < a.per_group:
                seen[g] = seen.get(g, 0) + 1
                keep.append(i)
        items = keep
    run = a.run or a.set + ("-tools" if a.tools else "")
    out = V2 / "runs" / run
    out.mkdir(parents=True, exist_ok=True)
    tools = ToolSubset() if a.tools else None
    meta_path = out / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.update({"set": a.set, "tools": TOOL_NAMES if a.tools else None, "effort": a.effort, "max_tokens": a.max_tokens,
                 "models": sorted(set(meta.get("models", [])) | set(models)),
                 "routing": "data_collection=deny; @host pins only=[host], allow_fallbacks=false; one user message, no system prompt"})
    if tools:
        meta["engine"] = {"server": tools.server_info, "commit": rm.subprocess_out(["git", "-C", str(Path.home() / "moneyguide"), "rev-parse", "--short", "HEAD"]), "max_tool_turns": rm.MAX_TOOL_TURNS}
    meta_path.write_text(json.dumps(meta, indent=1) + "\n")
    raw = out / "raw.jsonl"
    done = set()
    if raw.exists():
        for l in raw.read_text().splitlines():
            r = json.loads(l)
            if "error" not in r:
                done.add((r["model"], r["id"], r["rep"]))
    jobs = [(m, i, rep) for rep in range(a.reps) for i in items for m in models if (m, i["id"], rep) not in done]
    print(f"{run}: {len(items)} items x {len(models)} models x {a.reps} reps; {len(jobs)} to ask, {len(done)} done; ledger ${ledger()['spent_usd']:.3f} of ${a.cap}")
    if not jobs:
        return
    price = {m: tuple(known[m]["price"]) if m in known else rm.openrouter_prices(m) for m in models}
    lock = threading.Condition()
    led = ledger()
    reserved = [0.0]

    def worst(m, i):
        pin, pout = price[m]
        turns = 4 if tools else 1
        tokens_in = len(i["prompt"]) / 3 + (6000 if tools else 0)
        return turns * (tokens_in * pin + a.max_tokens * pout) / 1e6

    def ask(m, i, rep):
        w = worst(m, i)
        with lock:
            while led["spent_usd"] + reserved[0] + w > a.cap:
                if reserved[0] == 0:
                    return None
                lock.wait()
            reserved[0] += w
        res, t0 = None, time.monotonic()
        try:
            msgs = [{"role": "user", "content": i["prompt"]}]
            body = rm.openrouter_body(m, a.effort, msgs)
            if known.get(m, {}).get("reasoning") == "off":  # see lineup.json: these spent the whole reply limit thinking at effort low
                body["reasoning"] = {"enabled": False}
            try:
                if tools:
                    res = rm.ask_chat_with_tools(rm.openrouter_post, body, tools)
                    res.pop("_messages", None)
                else:
                    body["reasoning"]["exclude"] = True  # reasoning text isn't graded; it is still used and billed
                    r, err = rm.openrouter_post(body)
                    res = {"error": err} if err else rm.openrouter_rec(r)
            except (KeyError, IndexError, TypeError) as e:  # a 200 reply with no choices (the host returned an error body)
                res = {"error": f"malformed reply from host: {type(e).__name__} {e}"}
            res["seconds"] = round(time.monotonic() - t0, 1)
            return res
        finally:
            with lock:
                if res is not None:
                    cost = res.get("billed_usd")
                    if cost is None:  # the host didn't report a cost: tokens x list price
                        cost = (res.get("input_tokens", 0) * price[m][0] + res.get("output_tokens", 0) * price[m][1]) / 1e6
                        res["priced_usd"] = cost
                    led["spent_usd"] = round(led["spent_usd"] + cost, 6)
                    led["by_run"][run] = round(led["by_run"].get(run, 0) + cost, 6)
                    LEDGER.write_text(json.dumps(led, indent=1) + "\n")
                reserved[0] -= w
                lock.notify_all()

    skipped = errors = 0
    with raw.open("a") as f, ThreadPoolExecutor(max_workers=a.workers) as pool:
        futs = {pool.submit(ask, m, i, rep): (m, i, rep) for m, i, rep in jobs}
        for n, fut in enumerate(as_completed(futs), 1):
            m, i, rep = futs[fut]
            res = fut.result()
            if res is None:
                skipped += 1
                continue
            errors += "error" in res
            f.write(json.dumps({"model": m, "set": run, "id": i["id"], "rep": rep, "effort": a.effort, **res}) + "\n")
            f.flush()
            if n % 25 == 0 or n == len(jobs):
                print(f"  {n}/{len(jobs)}  ledger ${led['spent_usd']:.3f}", flush=True)
    if skipped:
        print(f"CAP: {skipped} requests not sent; the ledger is at ${led['spent_usd']:.3f} of ${a.cap}.")
    if errors:
        print(f"{errors} requests failed (see 'error' in raw.jsonl); rerun to retry.")


if __name__ == "__main__":
    main()
