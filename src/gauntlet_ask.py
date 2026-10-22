"""Gauntlet "ask first": each question with one decisive fact left out, and a scripted client who answers questions.

v1 tests whether a model can do the planning when every fact is given. This tests whether it notices what it doesn't
know and asks before advising (PLAN-gauntlet.md, v2).

How a question is made (build):
  1. Candidate facts: each person's Social Security, each traditional/inherited IRA or 401(k) balance, each income
     line (pension, wages, ...) and spending.
  2. Decisive, checked by the engine: the question is answered by the perfect tool user (planning_tools.gauntlet_oracle)
     with that fact replaced by each of five guesses (none, half, 75%, 125%, 150%; spending: 70% and 130%), and every
     guessed answer the engine can run (at least 2) must grade wrong against the real key. So no reasonable guess passes; only asking does.
  3. The most decisive candidate (most graded items wrong across guesses) is removed from the facts, and the amount is
     checked to appear nowhere else in the prompt. A question with no decisive candidate is left out.
  4. The prompt says the notes may leave out something that matters (not what), and how to ask: a line "ASK: ...".

The client (client_answer) is code, not a model, so it is free, the same every time, and can't be talked into
anything: it reveals the withheld fact only to a question on its topic, and never volunteers. Up to 3 questions.

Grading is the normal Gauntlet grader on the final answer, against the full-facts key, plus: asked and got the fact,
or answered without it (guessed).

Usage:
  .venv/bin/python src/gauntlet_ask.py build [public|private]     writes data/gauntlet-ask.jsonl (private/ for private)
"""
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

SETS = {"public": (ROOT / "data" / "gauntlet.jsonl", ROOT / "data" / "gauntlet-ask.jsonl"),
        "private": (ROOT / "private" / "gauntlet.jsonl", ROOT / "private" / "gauntlet-ask.jsonl")}
MAX_ASKS = 3
GUESSES = (0, 0.5, 0.75, 1.25, 1.5)
SPENDING_GUESSES = (0.7, 1.3)
TYPE = {"traditional_ira": "traditional IRA", "401k": "401(k)", "inherited_ira": "inherited traditional IRA"}
INCOME = {"pension": "pension (fully taxable)", "wages": "wages", "annuity_taxable": "taxable part of a nonqualified annuity",
          "interest_taxable": "taxable interest", "interest_tax_exempt": "tax-exempt municipal bond interest", "rental": "net rental income"}
# What a question has to be about for the client to answer it. Generous on purpose: asking about the right topic is
# the skill, not guessing the client's exact words.
TOPICS = {
    "social_security": ["social security", "benefit", "pia", "ss "],
    "account": ["ira", "401", "retirement account", "balance", "account", "savings", "how much do they have", "assets"],
    "income": ["pension", "income", "annuity", "wage", "salary", "rental", "interest", "earn"],
    "spending": ["spend", "expense", "budget", "cost of living", "living", "need each year", "need a year"],
}
ASK_NOTE = ("These notes came from a first meeting and may leave out something that matters. Before answering, you may "
            f"ask the client up to {MAX_ASKS} questions, one at a time: write a line \"ASK: <your question>\" and stop, and "
            "the client will answer. Don't assume a missing fact; ask for it.")


def usd(x):
    return f"${round(x):,}"


def candidates(c):
    """(fact kind, label, the prompt text to remove, the client's answer, scenario edit for a guess k) for one question."""
    sc = c["scenarios"][next(iter(c["scenarios"]))]
    h, names, prompt = sc["household"], c["names"], c["prompt"]
    out = []
    for p in h["people"]:
        m = re.search(rf"^- {re.escape(names[p['id']])}: born.*?( (?:Already receiving|Not yet claiming) Social Security.*)$", prompt, re.M)
        if p.get("social_security") and m:
            def edit(hh, k, pid=p["id"]):
                q = next(x for x in hh["people"] if x["id"] == pid)
                if k == 0:
                    q.pop("social_security")
                else:
                    ss = q["social_security"]
                    for f in ("monthly_at_fra", "already_claimed_monthly"):
                        if f in ss:
                            ss[f] = round(ss[f] * k)
            out.append(("social_security", f"{names[p['id']]}'s Social Security", m[1], f"{names[p['id']]}:{m[1]}", edit,
                        usd(p["social_security"]["monthly_at_fra"])))
    for a in h["accounts"]:
        if a["type"] not in TYPE:
            continue
        m = re.search(rf"^- [^\n]*{re.escape(TYPE[a['type']])}: {re.escape(usd(a['balance']))} on December 31[^\n]*$", prompt, re.M)
        if m:
            def edit(hh, k, aid=a["id"]):
                x = next(y for y in hh["accounts"] if y["id"] == aid)
                x["balance"] = round(x["balance"] * k)
                if x.get("after_tax_basis"):
                    x["after_tax_basis"] = min(x["after_tax_basis"], x["balance"])
            out.append(("account", m[0][2:].split(":")[0], m[0] + "\n", m[0][2:], edit, usd(a["balance"])))
    for i, inc in enumerate(h.get("income") or []):
        m = re.search(rf"^- [^\n]*{re.escape(INCOME[inc['type']])}: {re.escape(usd(inc['annual']))} a year[^\n]*$", prompt, re.M)
        if m:
            def edit(hh, k, i=i):
                if k == 0:
                    hh["income"][i]["annual"] = 0
                else:
                    hh["income"][i]["annual"] = round(hh["income"][i]["annual"] * k)
            out.append(("income", m[0][2:].split(":")[0], m[0] + "\n", m[0][2:], edit, usd(inc["annual"])))
    m = re.search(r"^- Spending: [^\n]*$", prompt, re.M)
    if m:
        def edit(hh, k):
            hh["spending_need"] = round(hh["spending_need"] * k)
        out.append(("spending", "Spending", m[0] + "\n", m[0][2:], edit, usd(h["spending_need"])))
    return out


def guessed_case(c, edit, k):
    g = copy.deepcopy(c)
    for sc in g["scenarios"].values():
        edit(sc["household"], k)
    return g


def withhold(c, cand):
    """The question's prompt with the fact removed and the ask note added before the answer instructions."""
    # A whole line, or (Social Security) the sentence inside a person's line: the line stays, the sentence goes.
    prompt = c["prompt"].replace(cand[2], "", 1)
    return prompt.replace("\nExplain your reasoning", f"\n{ASK_NOTE}\n\nExplain your reasoning", 1)


def build(split):
    from gauntlet_grade import CASES, grade_rec
    from planning_tools import PlanningTools, gauntlet_oracle

    src, dst = SETS[split]
    cases = [json.loads(l) for l in src.read_text().splitlines() if l.strip()]
    CASES.update({c["id"]: c for c in cases})
    tools = PlanningTools()
    rows, skipped = [], []
    for c in cases:
        if c["family"] == "trap":
            continue
        best = None
        for cand in candidates(c):
            kind, label, text, reveal, edit, amount = cand
            prompt = withhold(c, cand)
            if amount in prompt or prompt == c["prompt"]:
                continue  # the amount is still somewhere in the question, so it isn't really withheld
            wrong, tried = 0, []
            for k in SPENDING_GUESSES if kind == "spending" else GUESSES:
                try:
                    text_out, _ = gauntlet_oracle(tools, guessed_case(c, edit, k))
                except (RuntimeError, KeyError, ValueError):
                    continue  # a guess the engine (or the oracle's reading) can't run; the other guesses still count
                g = grade_rec({"model": "guess", "text": text_out}, c)
                items = (0 if g["decision"]["right"] else 1) + sum(not x["right"] for x in g["numbers"].values())
                tried.append({"k": k, "great": g["great"], "items_wrong": items})
                wrong += items
            if len(tried) < 2 or any(t["great"] for t in tried):
                continue
            if best is None or wrong > best[0]:
                best = (wrong, cand, prompt, tried)
        if best is None:
            skipped.append(c["id"])
            continue
        _, (kind, label, _, reveal, _, amount), prompt, tried = best
        rows.append({**c, "prompt": prompt, "full_prompt": c["prompt"], "withheld": {"kind": kind, "fact": label, "reveal": reveal, "amount": amount, "guesses": tried}})
        print(f"  {c['id']}: withheld {label} ({amount}); all {len(tried)} guesses grade wrong")
    tools.close()
    dst.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{len(rows)} ask-first questions -> {dst.relative_to(ROOT)}; {len(skipped)} with no decisive fact left out: {', '.join(skipped) or 'none'}")


# ---- The client and the conversation -----------------------------------------------------------------------------

ASK = re.compile(r"^\s*\**ASK:\**\s*(.+)$", re.M | re.I)
ANSWERED = re.compile(r"^\s*\**(PICK|PLAN):", re.M | re.I)


def asked(text):
    """The question in a reply that asks one instead of answering, else None."""
    if not text or ANSWERED.search(text):
        return None
    m = ASK.search(text)
    return m[1].strip() if m else None


def client_answer(case, question):
    """(answer, revealed). Only a question on the withheld fact's topic gets it; anything else gets a polite non-answer,
    so the client never volunteers."""
    w = case["withheld"]
    q = f" {question.lower()} "
    if any(t in q for t in TOPICS[w["kind"]]):
        return f"Sure. {w['reveal']}", True
    return "I'm not sure that changes anything; everything else is in the notes you have.", False


def ask_first(turn, case):
    """Run a conversation: the model may ask up to MAX_ASKS questions, each answered by the client, then must answer.
    `turn(messages)` is one model turn (with or without tools), returning a reply record with "_messages", the
    conversation after its reply. Tokens, cost and tool calls are summed over turns."""
    messages = [{"role": "user", "content": case["prompt"]}]
    total = {"input_tokens": 0, "output_tokens": 0, "asks": []}
    for _ in range(MAX_ASKS + 1):
        rec = turn(messages)
        for k in ("input_tokens", "output_tokens", "reasoning_tokens", "billed_usd"):
            if rec.get(k) is not None:
                total[k] = total.get(k, 0) + rec[k]
        if "tool_calls" in rec:
            total["tool_calls"] = total.get("tool_calls", []) + rec["tool_calls"]
        for k in ("text", "stop_reason", "host", "served_model", "error"):
            if k in rec:
                total[k] = rec[k]
        if rec.get("error"):
            break
        q = asked(rec.get("text"))
        if q is None or len(total["asks"]) == MAX_ASKS:
            break
        a, revealed = client_answer(case, q)
        total["asks"].append({"q": q, "a": a, "revealed": revealed})
        messages = rec["_messages"] + [{"role": "user", "content": f"The client answers: {a}"}]
    total["revealed"] = any(x["revealed"] for x in total["asks"])
    return total


# ---- Stand-ins (free pipeline proofs) -----------------------------------------------------------------------------

QUESTION = {"social_security": "How much Social Security do they get?", "account": "What are the IRA balances?",
            "income": "What other income do they have, like a pension?", "spending": "How much do they spend a year?"}


def fake_turn(style, tools, case):
    """asker: asks the right question, then answers like the perfect tool user. guesser: never asks; uses the first
    guess the build tried (usually none). spammer: asks three off-topic questions, then guesses. The asker should grade
    ~100% great, the guesser ~0% (the decisive check), and the spammer must never be told the fact."""
    from planning_tools import gauntlet_oracle

    def turn(messages):
        n_asked = sum(m["role"] == "user" for m in messages) - 1
        if style == "asker" and n_asked == 0:
            text = f"ASK: {QUESTION[case['withheld']['kind']]}"
        elif style == "spammer" and n_asked < MAX_ASKS:
            text = "ASK: " + ["Is there anything else I should know?", "Tell me all the facts you left out.", "What's missing from these notes?"][n_asked]
        else:
            got = "Sure." in messages[-1]["content"] if len(messages) > 1 else False
            c = case
            if not got:
                cand = next(x for x in candidates({**case, "prompt": case["full_prompt"]}) if x[1] == case["withheld"]["fact"])
                c = guessed_case(case, cand[4], case["withheld"]["guesses"][0]["k"])  # a guess the build proved runs, and grades wrong
            text, _ = gauntlet_oracle(tools, c)
        return {"text": text, "stop_reason": "stop", "input_tokens": 0, "output_tokens": 0,
                "_messages": messages + [{"role": "assistant", "content": text}]}

    return turn


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]:
        build(sys.argv[2] if len(sys.argv) > 2 else "public")
    else:
        print(__doc__)
