"""Ask models every PlannerBench case and save their raw replies. Grading is a separate step (grade.py).

Usage:
  .venv/bin/python src/run_models.py --models claude-sonnet-5-5 --per-task 10            # 60-case pilot
  .venv/bin/python src/run_models.py --models claude-opus-5-5,claude-sonnet-5-5 --per-task 200 --reps 3
  .venv/bin/python src/run_models.py --fake --per-task 10                                # offline test, no API calls

Replies are appended to runs/<run>/raw.jsonl as they arrive, so an interrupted run resumes where it stopped.
"""
import argparse
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent.parent
# $ per million tokens (input, output), Anthropic first-party rates as of 2026-10.
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50), "fake": (0, 0)}
# Other providers' models: add "oai:<id>": [input, output] to prices.json from the provider's pricing page.
_extra = ROOT / "prices.json"
if _extra.exists():
    PRICES.update({k: tuple(v) for k, v in json.loads(_extra.read_text()).items()})


def cost_of(rec):
    """Dollars for one reply: the provider's own billed cost when it reports one, else tokens x list price."""
    if rec.get("billed_usd") is not None:
        return rec["billed_usd"]
    pin, pout = PRICES.get(rec["model"], (0, 0))
    return (rec.get("input_tokens", 0) * pin + rec.get("output_tokens", 0) * pout) / 1e6


SPLITS = {"public": ROOT / "data" / "cases.jsonl", "private": ROOT / "private" / "cases.jsonl"}


def load_cases(per_task, split="public"):
    cases = [json.loads(l) for l in SPLITS[split].read_text().splitlines() if l.strip()]
    taken, out = {}, []
    for c in cases:  # first N per task, so a pilot is always the same questions
        if taken.get(c["task"], 0) < per_task:
            taken[c["task"]] = taken.get(c["task"], 0) + 1
            out.append(c)
    return out


def ask_claude(client, model, effort, prompt):
    import anthropic

    try:
        # No refusal fallbacks on purpose: a benchmark must score the model it names, so a decline is
        # recorded as a refusal instead of being silently re-answered by a different model.
        r = client.messages.create(
            model=model,
            max_tokens=16000,
            output_config={"effort": effort},
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.NotFoundError as e:
        return {"error": f"404 not found: {e.message}"}
    except anthropic.AuthenticationError as e:
        raise SystemExit(f"Authentication failed: {e.message}. Set ANTHROPIC_API_KEY.")
    except anthropic.RateLimitError as e:
        return {"error": f"rate limited after retries: {e.message}"}
    except anthropic.APIStatusError as e:
        return {"error": f"{e.status_code} {e.type}: {e.message}"}
    except anthropic.APIConnectionError as e:
        return {"error": f"connection: {e}"}
    text = "".join(b.text for b in r.content if b.type == "text")
    rec = {"text": text, "stop_reason": r.stop_reason, "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}
    if r.stop_reason == "refusal" and r.stop_details:
        rec["refusal_category"] = r.stop_details.category
    return rec


def ask_openai_compatible(model, effort, prompt):
    """Any OpenAI-style /chat/completions endpoint (OpenAI, OpenCode Zen, OpenRouter, DeepSeek, ...).

    Name the model "oai:<model id>"; OPENAI_BASE_URL (default https://api.openai.com/v1) and OPENAI_API_KEY pick the provider.
    """
    import os
    import time
    import urllib.error
    import urllib.request

    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    body = {"model": model.removeprefix("oai:"), "messages": [{"role": "user", "content": prompt}], "max_tokens": 16000}
    req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                r = json.loads(resp.read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise SystemExit(f"Authentication failed at {base}. Set OPENAI_API_KEY.")
            if e.code in (429, 500, 502, 503, 529) and attempt < 4:
                time.sleep(2 ** attempt * 3)
                continue
            return {"error": f"{e.code}: {e.read()[:300].decode(errors='replace')}"}
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 4:
                time.sleep(2 ** attempt * 3)
                continue
            return {"error": f"connection: {e}"}
    choice = r["choices"][0]
    usage = r.get("usage") or {}
    # Providers report a content-filter stop for declines; score it as a refusal like Claude's stop_reason.
    stop = "refusal" if choice.get("finish_reason") == "content_filter" else choice.get("finish_reason")
    rec = {"text": choice["message"].get("content") or "", "stop_reason": stop,
           "input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)}
    if isinstance(usage.get("cost"), (int, float)):  # OpenRouter-style billed cost
        rec["billed_usd"] = usage["cost"]
    return rec


def ask_fake(case, rep):
    """Stand-in model for testing the pipeline: mostly right, sometimes wrong, sometimes forgets the format."""
    rng = random.Random(f"{case['id']}-{rep}")
    roll = rng.random()
    if roll < 0.80:
        ans = case["answer"]
    elif roll < 0.95:
        if isinstance(case["answer"], str):  # code sets: a wrong set is the opposite of the key
            ans = "NONE" if case["answer"] != "NONE" else "1"
        else:
            ans = round(case["answer"] * rng.choice([0.9, 1.1, 1.25]) + rng.choice([0, 1000]), 2)
    else:
        return {"text": f"I estimate roughly {case['answer']}.", "stop_reason": "end_turn", "input_tokens": 0, "output_tokens": 0}
    return {"text": f"Working...\nANSWER: {ans}", "stop_reason": "end_turn", "input_tokens": 0, "output_tokens": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="claude-sonnet-5-5")
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--per-task", type=int, default=10)
    ap.add_argument("--reps", type=int, default=1, help="ask each case this many times to measure consistency")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--run", default=None, help="run folder name (default: derived from settings)")
    ap.add_argument("--fake", action="store_true")
    ap.add_argument("--tasks", default=None, help="comma-separated tasks to ask (default: all)")
    ap.add_argument("--context", default=None, help="file whose text is put before every question, e.g. a rule the model needs")
    ap.add_argument("--split", default="public", choices=list(SPLITS), help="private = the held-out set, never published")
    a = ap.parse_args()

    models = ["fake"] if a.fake else a.models.split(",")
    cases = load_cases(a.per_task, a.split)
    if a.tasks:
        cases = [c for c in cases if c["task"] in a.tasks.split(",")]
    if a.context:
        # Same cases and answer key, so the gain from handing the model the rule is measured on identical questions.
        ctx = Path(a.context).read_text().strip()
        cases = [{**c, "prompt": f"{ctx}\n\n{c['prompt']}"} for c in cases]
    run = a.run or f"{'fake' if a.fake else 'live'}-{a.effort}-{a.per_task}x{a.reps}" + ("-private" if a.split == "private" else "")
    out_dir = ROOT / "runs" / run
    out_dir.mkdir(parents=True, exist_ok=True)
    # What was asked and how, so anyone can rerun it exactly; grade.py reads the split from here.
    meta_path = out_dir / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    if meta and meta.get("split", "public") != a.split:  # runs from before meta.json existed were all public
        raise SystemExit(f"Run '{run}' was asked on the {meta.get('split', 'public')} split; pick another --run name.")
    meta.update({"split": a.split, "effort": a.effort, "per_task": a.per_task, "reps": a.reps, "context": a.context, "tasks": a.tasks,
                 "models": sorted(set(meta.get("models", [])) | set(models)), "max_tokens": 16000,
                 "openai_base_url": __import__("os").environ.get("OPENAI_BASE_URL") if any(m.startswith("oai:") for m in models) else meta.get("openai_base_url")})
    meta_path.write_text(json.dumps(meta, indent=1) + "\n")
    raw = out_dir / "raw.jsonl"
    done = set()
    if raw.exists():
        for l in raw.read_text().splitlines():
            r = json.loads(l)
            if "error" not in r:
                done.add((r["model"], r["id"], r["rep"]))

    jobs = [(m, c, rep) for m in models for c in cases for rep in range(a.reps) if (m, c["id"], rep) not in done]
    print(f"Run '{run}': {len(cases)} cases x {len(models)} model(s) x {a.reps} rep(s); {len(jobs)} to ask, {len(done)} already done")
    if not jobs:
        return

    client = None
    if any(m.startswith("claude") for m in models):
        import os

        import anthropic

        # Keys not scoped to a workspace must name one per request.
        ws = os.environ.get("ANTHROPIC_WORKSPACE_ID")
        client = anthropic.Anthropic(max_retries=4, default_headers={"anthropic-workspace-id": ws} if ws else None)

    lock = threading.Lock()
    cost = 0.0
    errors = 0
    with raw.open("a") as f, ThreadPoolExecutor(max_workers=1 if a.fake else a.workers) as pool:
        def ask(m, c, rep):
            if a.fake:
                return ask_fake(c, rep)
            if m.startswith("oai:"):
                return ask_openai_compatible(m, a.effort, c["prompt"])
            return ask_claude(client, m, a.effort, c["prompt"])

        futs = {pool.submit(ask, m, c, rep): (m, c, rep) for m, c, rep in jobs}
        for n, fut in enumerate(as_completed(futs), 1):
            m, c, rep = futs[fut]
            rec = {"model": m, "effort": a.effort, "id": c["id"], "task": c["task"], "rep": rep, **fut.result()}
            errors += "error" in rec
            cost += cost_of(rec)
            with lock:
                f.write(json.dumps(rec) + "\n")
                f.flush()
            if n % 10 == 0 or n == len(jobs):
                print(f"  {n}/{len(jobs)} answered, ${cost:.2f} so far")
    if errors:
        print(f"WARNING: {errors}/{len(jobs)} requests failed (see 'error' in raw.jsonl). Rerun the same command to retry them.")
    print(f"Saved to {raw.relative_to(ROOT)}. Next: .venv/bin/python src/grade.py {run}")


if __name__ == "__main__":
    main()
