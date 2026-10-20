# PlannerBench methodology

How every published number is made, and how to check it without trusting the maintainer.

## What is measured

Each question describes one household's numbers and asks for one exact answer under 2026 US federal rules (or, for the
compliance tasks, a set of codes). A reply is right when its final `ANSWER:` line is within the case's tolerance:
$1–2 on dollar answers, one cent on Medicare premiums, an exact match on codes. Replies with no parsable answer,
refusals and API errors are counted separately, and errors are excluded and retried instead of being scored.

It measures rule knowledge and arithmetic. It doesn't measure advice quality, judgment or client communication.

## How models are asked

- One user message per question: no system prompt, no tools, no examples. The prompt text is in `data/cases.jsonl`.
- Claude models: `effort` as recorded in each run's `meta.json` (default `high`), `max_tokens` 16,000.
- Other labs' models: the same prompt through OpenRouter, `max_tokens` 16,000, reasoning effort set to the run's
  effort. Each model is pinned to one host (`only: [host]`, no fallbacks), chosen as the model maker's own endpoint or
  else a full-precision one, never 4-bit; the lineup and the reason for each host are in `lineups/`. Every reply
  records the host that actually served it. Hosts that train on prompts are excluded (`data_collection: deny`).
- Other OpenAI-compatible endpoints (`oai:`) are supported for exploration. Their serving host and precision aren't
  visible, so their scores aren't published.
- No refusal fallbacks: a decline is scored as a refusal, never re-answered by a different model.
- Every raw reply is saved in `runs/<run>/raw.jsonl`, so anyone can regrade without asking a model again.

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
providers whose terms exclude API traffic from training.

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
