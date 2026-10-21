"""Ask models every PlannerBench case and save their raw replies. Grading is a separate step (grade.py).

Usage:
  .venv/bin/python src/run_models.py --models claude-sonnet-5-5 --per-task 10            # 60-case pilot
  .venv/bin/python src/run_models.py --models claude-opus-5-5,claude-sonnet-5-5 --per-task 200 --reps 3
  .venv/bin/python src/run_models.py --fake --per-task 10                                # offline test, no API calls
  .venv/bin/python src/run_models.py --models @lineups/cheap.txt --per-task 1 --run smoke  # check every pinned host answers

Replies are appended to runs/<run>/raw.jsonl as they arrive, so an interrupted run resumes where it stopped.
"""
import argparse
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent.parent
MAX_TOKENS = 16000  # per reply, thinking included; set per run with --max-tokens and recorded in meta.json


def load_env():
    """Read KEY=value lines from .env (git-ignored) so API keys never have to be typed into a shell or committed."""
    import os

    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#"):
                os.environ.setdefault(k.strip().removeprefix("export "), v.strip().strip("'\""))


load_env()

try:  # python.org builds ship without root certificates; use the operating system's store instead
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass
# $ per million tokens (input, output), Anthropic first-party rates as of 2026-10.
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50), "fake": (0, 0)}
# Other providers' models: add "oai:<id>": [input, output] to prices.json from the provider's pricing page.
# OpenRouter ("or:") replies carry their billed cost, so they need no entry.
_extra = ROOT / "prices.json"
if _extra.exists():
    PRICES.update({k: tuple(v) for k, v in json.loads(_extra.read_text()).items() if not k.startswith("_")})


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
            max_tokens=MAX_TOKENS,
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


MAX_TOOL_TURNS = 12  # a question needs at most ~4 tool calls; past this the reply is scored no_answer


def ask_claude_with_tools(client, model, effort, prompt, tools):
    """The same question with the MoneyGuide planning tools (MCP) available; Claude decides whether and how to use them.

    The prompt is unchanged and there is no system prompt, so the tools are the only difference from a plain run.
    Tokens are summed over every turn, and every call is saved so a miss can be traced to the inputs Claude chose.
    """
    import anthropic

    messages = [{"role": "user", "content": prompt}]
    rec = {"input_tokens": 0, "output_tokens": 0, "tool_calls": []}
    for _ in range(MAX_TOOL_TURNS):
        try:
            r = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                output_config={"effort": effort},
                tools=tools.list(),
                messages=messages,
            )
        except anthropic.NotFoundError as e:
            return {**rec, "error": f"404 not found: {e.message}"}
        except anthropic.AuthenticationError as e:
            raise SystemExit(f"Authentication failed: {e.message}. Set ANTHROPIC_API_KEY.")
        except anthropic.RateLimitError as e:
            return {**rec, "error": f"rate limited after retries: {e.message}"}
        except anthropic.APIStatusError as e:
            return {**rec, "error": f"{e.status_code} {e.type}: {e.message}"}
        except anthropic.APIConnectionError as e:
            return {**rec, "error": f"connection: {e}"}
        rec["input_tokens"] += r.usage.input_tokens
        rec["output_tokens"] += r.usage.output_tokens
        rec["text"] = "".join(b.text for b in r.content if b.type == "text")
        rec["stop_reason"] = r.stop_reason
        if r.stop_reason == "refusal" and r.stop_details:
            rec["refusal_category"] = r.stop_details.category
        if r.stop_reason != "tool_use":
            return rec
        # Thinking and tool_use blocks go back unchanged; all results return in one user message.
        messages.append({"role": "assistant", "content": r.content})
        results = []
        for b in r.content:
            if b.type == "tool_use":
                out, is_error = tools.call(b.name, b.input)
                rec["tool_calls"].append({"name": b.name, "input": b.input, "result": out, "is_error": is_error})
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out, "is_error": is_error})
        messages.append({"role": "user", "content": results})
    rec["stop_reason"] = "tool_turn_limit"
    return rec


def post_json(url, body, key, label):
    """POST with retries on rate limits and server errors; returns (json, None) or (None, error string)."""
    import time
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method="POST" if body is not None else "GET",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=1200) as resp:
                return json.loads(resp.read()), None
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise SystemExit(f"Authentication failed at {url}. Check {label}.")
            if e.code in (404, 429, 500, 502, 503, 529) and attempt < 4 and (e.code != 404 or body is None):
                time.sleep(2 ** attempt * 3)
                continue
            return None, f"{e.code}: {e.read()[:300].decode(errors='replace')}"
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 4:
                time.sleep(2 ** attempt * 3)
                continue
            return None, f"connection: {e}"


def from_chat_completion(r):
    """A reply record from an OpenAI-style response."""
    choice = r["choices"][0]
    usage = r.get("usage") or {}
    # Providers report a content-filter stop for declines; score it as a refusal like Claude's stop_reason.
    stop = "refusal" if choice.get("finish_reason") == "content_filter" else choice.get("finish_reason")
    rec = {"text": choice["message"].get("content") or "", "stop_reason": stop,
           "input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)}
    if isinstance(usage.get("cost"), (int, float)):  # billed cost, when the provider reports it
        rec["billed_usd"] = usage["cost"]
    reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
    if reasoning:
        rec["reasoning_tokens"] = reasoning
    return rec


def ask_openai_compatible(model, effort, prompt):
    """Any OpenAI-style /chat/completions endpoint (OpenAI, OpenCode Zen, DeepSeek, ...).

    Name the model "oai:<model id>"; OPENAI_BASE_URL (default https://api.openai.com/v1) and OPENAI_API_KEY pick the provider.
    """
    import os

    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    body = {"model": model.removeprefix("oai:"), "messages": [{"role": "user", "content": prompt}], "max_tokens": MAX_TOKENS}
    r, err = post_json(f"{base}/chat/completions", body, os.environ.get("OPENAI_API_KEY", ""), "OPENAI_API_KEY")
    return {"error": err} if err else from_chat_completion(r)


OPENROUTER = "https://openrouter.ai/api/v1"


def ask_openrouter(model, effort, prompt, private=False):
    """OpenRouter, with the routing pinned down so a score names what actually answered.

    Name the model "or:<vendor>/<model>" or "or:<vendor>/<model>@<host>" (e.g. or:deepseek/deepseek-v4.1-flash@deepinfra).
    With @host, only that host may answer and there is no fallback, so every reply comes from the same deployment.
    Hosts that keep prompts for training are always excluded; the private set also requires zero data retention.
    The host that served each reply is saved, since the same open model can score differently on different hosts.
    """
    import os

    name, _, host = model.removeprefix("or:").partition("@")
    provider = {"data_collection": "deny"}
    if host:
        provider.update({"only": [host], "allow_fallbacks": False})
    if private:
        provider["zdr"] = True
    body = {"model": name, "messages": [{"role": "user", "content": prompt}], "max_tokens": MAX_TOKENS,
            # Reasoning text isn't graded, so leave it out of the reply; it is still used and billed.
            "reasoning": {"effort": effort, "exclude": True}, "provider": provider}
    key = os.environ.get("OPENROUTER_API_KEY", "")
    r, err = post_json(f"{OPENROUTER}/chat/completions", body, key, "OPENROUTER_API_KEY")
    if err:
        return {"error": err}
    rec = {**from_chat_completion(r), "served_model": r.get("model"), "generation_id": r.get("id")}
    if r.get("provider"):
        rec["host"] = r["provider"]
    elif r.get("id"):
        # The host isn't always in the reply; the generation record has it (and the exact billed cost).
        g, _ = post_json(f"{OPENROUTER}/generation?id={r['id']}", None, key, "OPENROUTER_API_KEY")
        g = (g or {}).get("data") or {}
        if g.get("provider_name"):
            rec["host"] = g["provider_name"]
        if rec.get("billed_usd") is None and isinstance(g.get("total_cost"), (int, float)):
            rec["billed_usd"] = g["total_cost"]
    return rec


def subprocess_out(cmd):
    import subprocess

    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


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


def ask_fake_with_tools(tools, case, rep):
    """Stand-in for a tools run: answers numeric questions from real MCP tool calls, compliance like ask_fake."""
    from planning_tools import oracle

    ans = oracle(tools, case)
    if ans is None:
        return ask_fake(case, rep)
    return {"text": f"From the planning tools.\nANSWER: {ans}", "stop_reason": "end_turn", "input_tokens": 0, "output_tokens": 0, "tool_calls": []}


def main():
    global MAX_TOKENS
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
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS, help="per reply, thinking included; replies that hit it are graded 'truncated'")
    ap.add_argument("--max-usd", type=float, default=None, help="stop asking once this run has spent this much; rerun later to resume")
    ap.add_argument("--split", default="public", choices=list(SPLITS), help="private = the held-out set, never published")
    ap.add_argument("--tools", action="store_true", help="offer the MoneyGuide planning tools over MCP (Claude models only)")
    a = ap.parse_args()
    MAX_TOKENS = a.max_tokens

    if a.models.startswith("@"):  # a lineup file: one model per line, # comments allowed
        a.models = ",".join(l.split("#")[0].strip() for l in Path(a.models[1:]).read_text().splitlines() if l.split("#")[0].strip())
    models = ["fake"] if a.fake else a.models.split(",")
    # Free endpoints commonly keep prompts for training; a held-out question sent there is no longer held out.
    free = [m for m in models if m.endswith("-free") or m.split("@")[0].endswith(":free") or m == "oai:big-pickle"]
    if a.split == "private" and free:
        raise SystemExit(f"Not sending the private set to free endpoints that may train on it: {', '.join(free)}")
    if a.tools and not a.fake and not all(m.startswith("claude") for m in models):
        raise SystemExit("--tools runs Claude models only for now (the tool loop uses the Claude API's tool use).")
    tools = None
    if a.tools:
        from planning_tools import SERVER, PlanningTools

        tools = PlanningTools()
    cases = load_cases(a.per_task, a.split)
    if a.tasks:
        cases = [c for c in cases if c["task"] in a.tasks.split(",")]
    if a.context:
        # Same cases and answer key, so the gain from handing the model the rule is measured on identical questions.
        ctx = Path(a.context).read_text().strip()
        cases = [{**c, "prompt": f"{ctx}\n\n{c['prompt']}"} for c in cases]
    run = a.run or f"{'fake' if a.fake else 'live'}-{a.effort}-{a.per_task}x{a.reps}" + ("-tools" if a.tools else "") + ("-private" if a.split == "private" else "")
    out_dir = ROOT / "runs" / run
    out_dir.mkdir(parents=True, exist_ok=True)
    # What was asked and how, so anyone can rerun it exactly; grade.py reads the split from here.
    meta_path = out_dir / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    if meta and meta.get("split", "public") != a.split:  # runs from before meta.json existed were all public
        raise SystemExit(f"Run '{run}' was asked on the {meta.get('split', 'public')} split; pick another --run name.")
    if meta and bool(meta.get("tools")) != a.tools:
        raise SystemExit(f"Run '{run}' was asked {'with' if meta.get('tools') else 'without'} --tools; pick another --run name.")
    if tools:
        # Which tools, from which engine commit, so a tools score names exactly what the model could call.
        engine = subprocess_out(["git", "-C", str(SERVER.parents[2]), "rev-parse", "--short", "HEAD"])
        dirty = subprocess_out(["git", "-C", str(SERVER.parents[2]), "status", "--porcelain", "src/engine", "mcp"])
        if dirty and not a.fake:
            raise SystemExit("~/moneyguide has uncommitted engine or MCP changes; commit them so the score names a real commit.")
        meta["tools"] = {"server": tools.server_info, "names": [t["name"] for t in tools.tools], "moneyguide_commit": engine,
                         "moneyguide_dirty": bool(dirty), "max_tool_turns": MAX_TOOL_TURNS}
    meta.update({"split": a.split, "effort": a.effort, "per_task": a.per_task, "reps": a.reps, "context": a.context, "tasks": a.tasks,
                 "models": sorted(set(meta.get("models", [])) | set(models)), "max_tokens": MAX_TOKENS,
                 "openai_base_url": __import__("os").environ.get("OPENAI_BASE_URL") if any(m.startswith("oai:") for m in models) else meta.get("openai_base_url"),
                 "openrouter_routing": "data_collection=deny; @host pins only=[host], allow_fallbacks=false; private split adds zdr=true; reasoning effort = --effort"
                 if any(m.startswith("or:") for m in models) else meta.get("openrouter_routing")})
    meta_path.write_text(json.dumps(meta, indent=1) + "\n")
    raw = out_dir / "raw.jsonl"
    done = set()
    if raw.exists():
        for l in raw.read_text().splitlines():
            r = json.loads(l)
            if "error" not in r:
                done.add((r["model"], r["id"], r["rep"]))

    # Case by case across models, so a budget stop leaves every model with the same questions answered.
    jobs = [(m, c, rep) for rep in range(a.reps) for c in cases for m in models if (m, c["id"], rep) not in done]
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
    errors = skipped = 0
    with raw.open("a") as f, ThreadPoolExecutor(max_workers=1 if a.fake else a.workers) as pool:
        def ask(m, c, rep):
            if a.max_usd is not None and cost >= a.max_usd:
                return None  # over budget: not asked, not recorded, so a rerun picks it up
            if a.fake:
                return ask_fake_with_tools(tools, c, rep) if tools else ask_fake(c, rep)
            if tools:
                return ask_claude_with_tools(client, m, a.effort, c["prompt"], tools)
            if m.startswith("or:"):
                return ask_openrouter(m, a.effort, c["prompt"], private=a.split == "private")
            if m.startswith("oai:"):
                return ask_openai_compatible(m, a.effort, c["prompt"])
            return ask_claude(client, m, a.effort, c["prompt"])

        futs = {pool.submit(ask, m, c, rep): (m, c, rep) for m, c, rep in jobs}
        for n, fut in enumerate(as_completed(futs), 1):
            m, c, rep = futs[fut]
            if (res := fut.result()) is None:
                skipped += 1
                continue
            rec = {"model": m, "effort": a.effort, "id": c["id"], "task": c["task"], "rep": rep, **res}
            errors += "error" in rec
            cost += cost_of(rec)
            with lock:
                f.write(json.dumps(rec) + "\n")
                f.flush()
            if n % 10 == 0 or n == len(jobs):
                print(f"  {n}/{len(jobs)} answered, ${cost:.2f} so far")
    if skipped:
        print(f"BUDGET: stopped at ${cost:.2f} (--max-usd {a.max_usd}); {skipped} questions not asked. Rerun the same command to continue.")
    if errors:
        print(f"WARNING: {errors}/{len(jobs)} requests failed (see 'error' in raw.jsonl). Rerun the same command to retry them.")
    print(f"Saved to {raw.relative_to(ROOT)}. Next: .venv/bin/python src/grade.py {run}")


if __name__ == "__main__":
    main()
