# Audit of PlannerBench v1

Written 2026-11-14 from the repo and the two leaderboard runs (`live-high-10x1`, `or-5models-15x1`). Every number
below is recomputed from `runs/*/graded.jsonl`; nothing was rerun.

## The short version

- v1 is saturated on three of its four groups: single-step math, multi-step math for the best model, and compliance.
- It is **not** saturated on the "stacked" tasks. Claude Sonnet 5.5 scores 37% there. But 99 of the 139 wrong
  answers with a named cause are one misreading (the senior-deduction phase-out), so the stacked group mostly
  measures one rule.
- "Top models ace it" rests on one frontier model, asked 10 questions per task, once. No GPT or Gemini frontier
  model has been run.
- Nothing in v1 or the Gauntlet tests wrong inputs. Ask-first tests a *missing* fact. A fact that is present and
  wrong is untested.

## What v1 tests

14 tasks, 200 public cases each, plus 700 held-out cases. One user message, no system prompt, one exact answer.

| Group | Tasks | What a right answer needs |
|---|---|---|
| Single-step | federal_tax, taxable_ss, rmd, ss_claim, bracket_room, irmaa | One published rule and arithmetic |
| Multi-step | tax_torpedo, widow_penalty | Two tax returns and a subtraction |
| Stacked | senior_phaseout, conversion_all_in, widow_all_in | Tax plus the senior-deduction phase-out, plus Medicare tiers |
| Compliance | rollover_flags, breakpoint, comms_review | Pick codes; each issue is defined in the prompt |

Separately, the Gauntlet (77 public whole-household decisions) and Ask-first (69 of them with one fact removed) exist
but have only been run on 5–11 questions per model.

## Where it is saturated

Right answers out of questions asked, by task (errors excluded):

| Task | Sonnet 5.5 | Haiku 5.5 | Haiku via OpenRouter | DeepSeek V4.1 Flash | GLM 5.3 Flash | Qwen3.8 Flash | gpt-oss-120b |
|---|---|---|---|---|---|---|---|
| federal_tax | 10/10 | 10/10 | 15/15 | 10/15 | 9/15 | 0/15 | 0/15 |
| taxable_ss | 10/10 | 10/10 | 14/15 | 15/15 | 11/15 | 12/15 | 7/15 |
| rmd | 10/10 | 10/10 | 15/15 | 15/15 | 11/15 | 6/15 | 5/15 |
| ss_claim | 8/10 | 9/10 | 12/15 | 15/15 | 14/15 | 14/15 | 14/15 |
| bracket_room | 10/10 | 10/10 | 14/15 | 11/15 | 13/15 | 7/15 | 6/15 |
| irmaa | 10/10 | 9/10 | 13/15 | 11/15 | 3/15 | 0/15 | 0/15 |
| tax_torpedo | 10/10 | 9/10 | 12/15 | 14/15 | 11/15 | 1/15 | 3/15 |
| widow_penalty | 8/10 | 6/10 | 7/15 | 7/15 | 4/15 | 0/15 | 0/15 |
| senior_phaseout | 1/10 | 0/10 | 0/15 | 3/15 | 4/15 | 0/1 | 1/15 |
| conversion_all_in | 8/10 | 3/10 | 6/15 | 8/15 | 5/15 | 0/5 | 1/15 |
| widow_all_in | 2/10 | 2/10 | 3/15 | 5/15 | 3/15 | 0/11 | 0/7 |
| rollover_flags | 10/10 | 10/10 | 12/15 | 13/15 | 12/15 | 11/15 | 11/15 |
| breakpoint | 10/10 | 10/10 | 15/15 | 15/15 | 15/15 | 15/15 | 15/15 |
| comms_review | 10/10 | 10/10 | 15/15 | 15/15 | 15/15 | 15/15 | 15/15 |

- **Sonnet 5.5:** 58/60 single-step (97%), 18/20 multi-step, 30/30 compliance. Only the stacked group has room (11/30).
- **breakpoint and comms_review:** every model, every question. They separate nothing.
- **Cheap models still spread out** on single-step tasks (gpt-oss 0/15 on federal_tax and irmaa), so v1 still ranks
  the low end. It no longer ranks the top.

## Items every model gets right

Of the 199 questions that at least five models answered, **66 were right for every model** and 18 wrong for every
model.

| | Count by task |
|---|---|
| Right for everyone (66) | breakpoint 15, comms_review 15, rollover_flags 11, ss_claim 8, bracket_room 6, taxable_ss 5, rmd 5, tax_torpedo 1 |
| Wrong for everyone (18) | senior_phaseout 5, widow_all_in 4, widow_penalty 3, conversion_all_in 2, rollover_flags 2, bracket_room 1, tax_torpedo 1 |

A third of the benchmark carries no information about which model is better. The all-wrong items are nearly all the
senior-deduction rule again.

## How scoring works

- The grader takes the last `ANSWER:` line and compares it to the key: within $1–2 on dollars, one cent on Medicare
  premiums, exact on code sets (`src/grade.py`).
- Each reply lands in one bucket: correct, wrong, no_answer, truncated, refusal, error. Errors are left out and
  retried; truncated counts as not right and is published.
- Wrong answers that match a known misreading get its name (11 named mistakes). Dollar answers are also scored by
  how far off they are (`src/dollars.py`).
- Accuracy is per question with a 95% Wilson interval; paired comparisons use exact McNemar (`src/stats.py`).
- The key is checked seven ways (`TRUST.md`), including PolicyEngine-US. This is the strongest part of v1.

## Weak spots in the scoring and design

1. **No variance.** Every leaderboard run asked each question once. A model that is right two times in three looks
   the same as one that is always right or always wrong.
2. **Small samples at the top.** Sonnet's headline numbers are 10 questions per task. 10/10 has a 95% interval of
   72–100%.
3. **One frontier model, one lab.** Saturation at the top is shown for Claude Sonnet only.
4. **Right or wrong, nothing between.** A reply that is $3 off and one that is $30,000 off are both "wrong" on the
   leaderboard (the dollars-off score exists but isn't the headline).
5. **The stacked group measures one rule.** 99 of 139 wrong answers with a named cause are the combined
   senior-deduction phase-out. Fix that rule (the `with-rule` run did) and the group saturates too.
6. **Compliance defines its own answers.** Each issue is explained in the prompt, so it tests reading.
7. **One wording per task.** Every question in a task is the same template with different numbers.
8. **Format decides some grades.** A right number without the `ANSWER:` line is `no_answer`. Rare (2 replies), but
   it is a format test mixed into a math score.
9. **Clean inputs only.** Every prompt is internally consistent and every fact is true. The grader has no way to
   give credit for refusing to compute, so a model that noticed a problem would be marked wrong.
10. **Federal only.** No state tax, no QCDs, no inherited IRAs in the scored tasks (the Gauntlet has them, on a few
    questions).
11. **Effort and token limits differ between runs** (16k direct, 32k OpenRouter), and the pilot ran before a wording
    fix. The harness check found no difference for Haiku, but it is a known mismatch.

## What v2 should do about it

| Weak spot | v2 answer |
|---|---|
| 1, 2 | Up to three runs per item; report the spread |
| 3 | Frontier models from three labs |
| 5, 10 | A hard tier where different rules interact: IRMAA two years out, QCDs with RMDs, inherited IRAs, Arizona, a widow's first year |
| 9 | A bad-inputs track with clean twins, scored on catching the problem and on false alarms |
| 4 | Report dollars and failure types next to accuracy |
| 6, 7 | Not addressed in v2 (compliance v2 is a separate open item) |
