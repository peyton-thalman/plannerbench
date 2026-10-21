# PlannerBench methodology

How every published number is made, and how to check it without trusting the maintainer.

## What is measured

Each question describes one household's numbers and asks for one exact answer under 2026 US federal rules (or, for the
compliance tasks, a set of codes). A reply is right when its final `ANSWER:` line is within the case's tolerance:
$1–2 on dollar answers, one cent on Medicare premiums, an exact match on codes. Replies with no parsable answer,
refusals and API errors are counted separately, and errors are excluded and retried instead of being scored.

A reply that hits the token limit before answering is graded **truncated**. It counts as not right, and its rate is
published for each model. Some low-cost reasoning models spend their whole budget thinking. A firm pays for those
tokens and gets no answer, so that rate is part of the result, not noise. The limit is recorded per run in
`meta.json`. It was 16,000 tokens for the Claude pilot runs and 32,000 for the OpenRouter runs, after a smoke test
showed 16,000 cut off two models on most questions.

It measures rule knowledge and arithmetic. It doesn't measure advice quality, judgment or client communication.

## How models are asked

- One user message per question: no system prompt, no tools (except tools runs, below), no examples. The prompt text is in `data/cases.jsonl`.
- Claude models: `effort` as recorded in each run's `meta.json` (default `high`), `max_tokens` 16,000.
- Other labs' models: the same prompt through OpenRouter, `max_tokens` 16,000, reasoning effort set to the run's
  effort. Each model is pinned to one host (`only: [host]`, no fallbacks), chosen as the model maker's own endpoint or
  else a full-precision one, never 4-bit; the lineup and the reason for each host are in `lineups/`. Every reply
  records the host that actually served it. Hosts that train on prompts are excluded (`data_collection: deny`).
- Other OpenAI-compatible endpoints (`oai:`) are supported for exploration. Their serving host and precision aren't
  visible, so their scores aren't published.
- No refusal fallbacks: a decline is scored as a refusal, never re-answered by a different model.
- Every raw reply is saved in `runs/<run>/raw.jsonl`, so anyone can regrade without asking a model again.

### With planning tools (`--tools`)

The same questions, word for word, with one difference: the model may call the MoneyGuide planning tools over MCP
(`~/moneyguide/mcp/server.ts`). There are six general calculators: federal income tax, taxable Social Security,
RMD, Social Security claiming benefit, Medicare Part B premium, and the 2026 tax tables. There is no tool per question
type. A stacked question still needs the model to pick the inputs (the survivor files single and keeps the larger
check; 2026 income sets 2028 premiums), call several tools and combine the results.

- **The tools are enough, and right.** `checks/tools_check.py` answers every numeric question from tool calls alone
  and must match the key on all of them (2,200/2,200 public, 550/550 private). So a miss in a tools run is the
  model's: wrong inputs, a missed step, or not calling a tool at all.
- **This is not circular, though the tools and the key share an engine.** The key's correctness is established
  separately (golden set, independent checker, PolicyEngine-US). A tools run measures whether a model can use a
  verified calculator correctly, the way an advisor would use planning software.
- Each reply saves every tool call with its inputs and result. Tokens are summed over all turns; a question gets up
  to 12 turns, after which it is scored `no_answer`. `meta.json` records the tool names, the MCP server version and
  the MoneyGuide commit, and the runner refuses a live run while that repo has uncommitted engine or tool changes.
- Claude models only for now.

## How the answer key is checked

No case ships unless all seven layers in [TRUST.md](TRUST.md) pass:

1. **Golden set.** 16 cases whose answers are printed in IRS, SSA and CMS publications.
2. **Two-way check.** The case generator's engine (TypeScript) and a separately written Python checker
   (`checks/independent_check.py`) must agree on every case.
3. **Invariants.** 4,000 random households × 9 rules that must always hold (more income never lowers tax, …).
4. **Dataset health.** No duplicate prompts, no task where one answer is common enough to guess.
5. **Human audit pack.** 12 random cases with worked solutions in `checks/AUDIT.md`. *Not yet signed off by an
   outside CPA; that's an open item.*
6. **Outside model.** [PolicyEngine-US](https://github.com/PolicyEngine/policyengine-us) (pinned in
   `requirements-policyengine.txt`), an open-source tax model this project didn't write, recomputes every tax
   answer. Layers 2–3 can't catch a rule both implementations misread the same way, and this layer can.
   Results: [checks/POLICYENGINE.md](checks/POLICYENGINE.md).
7. **Held-out set.** See below.

When models agree with each other against the key, the grader puts the case in a review queue. The published
source decides, not the models. The senior-deduction phase-out is the standing example: both Claude models took 6%
off the couple's combined $12,000. Schedule 1-A Part V (lines 35–36b) and PolicyEngine both take it off each spouse's
$6,000, as the key does.

What the outside model doesn't cover: `rmd`, `ss_claim`, `irmaa` and the compliance tasks, which PolicyEngine doesn't
model. Those rest on layers 1–4.

## Held-out set

The public set comes from a fixed seed in `src/generate.ts`. A private set of 700 cases (50 per task) comes from a
secret seed kept in `private/`, which is git-ignored and never published. It excludes every public prompt. A model
trained on the public set still meets new questions there. A large gap between a model's public and private scores
is evidence of contamination, and the leaderboard will report both once private runs exist. The runner refuses to send
the private set to free endpoints, which commonly keep prompts for training. Paid endpoints get it only through
providers whose terms exclude API traffic from training. Replies to private questions restate their numbers, so
private runs (`runs/*-private/`) stay on the maintainer's machine; only aggregate scores are published.

## Checks on the harness and the site

- **Harness check** (`checks/harness_check.py`). Claude Haiku 5.5 is asked the same questions directly and through
  OpenRouter. If routing changed scores, no OpenRouter number would be publishable. Pass means no significant
  difference (exact McNemar p > 0.05). The comparison isn't perfectly clean: the direct pilot ran with a
  16,000-token limit and the prompt wording from before the single-filer fix.
- **Site check** (`checks/site_check.py`). Fetches the data files the deployed site serves and requires them to equal
  `leaderboard/` field for field, so the page can't drift from the graded runs.

## Statistics

- Accuracy is per question. With repeated runs, a question's score is the share of its runs that were right, so
  three runs of one question never count as three questions.
- Every accuracy carries a 95% Wilson score interval (`src/stats.py`).
- Comparisons on the same questions (with vs. without the rule) use an exact McNemar test on the questions whose
  outcome flipped. The p-value is in `leaderboard/rule_effect.json`.
- Cost is tokens × the provider's list price on the run date, or the provider's billed cost when its API reports
  one. The headline cost figure is **dollars per right answer**, since that is what a firm pays for.

## Reproduce

```bash
./reproduce.sh
```

This re-verifies the key (layers 1–6, plus 7 on the maintainer's machine), regrades every saved reply and rebuilds
`leaderboard/` from the runs listed in `leaderboard/RUNS`. It fails if any number differs from the committed one.
Regenerating the cases themselves needs the MoneyGuide engine, which isn't in this repo. The checks above verify
every answer without it.

## Disputing an answer

If you think a key is wrong, open an issue with the case id and the rule citation. If the citation holds, the case is
fixed, the change is logged in the README, and every affected score is regraded from the saved replies.

## Known limits

- One fixed wording per task. Paraphrased prompts aren't tested yet, so part of a score may reflect the wording.
- Compliance tasks define each issue in the question. Both models tested scored 100%, so this track currently
  measures reading, not knowledge.
- Federal rules only. No state tax, no AMT cases (PolicyEngine found none in the set), no credits.
- Pilot runs (`live-high-10x1`, `with-rule-10x1`) were asked before a 2026-10-20 wording fix. That fix changed how
  the age line reads for single filers ("age 65 or older" instead of "1 spouse age 65 or older"); inputs and answers
  are unchanged.
