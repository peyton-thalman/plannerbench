# Tool effect: claude-haiku-5-5

Without tools: `live-high-10x1`. With the MoneyGuide planning tools (MCP): `tools-smoke`. 14 questions asked both ways; p is a paired McNemar test on the questions that flipped.

| Questions | Without tools | With tools | Fixed | Broken | p |
|---|---|---|---|---|---|
| All (14) | 71% [45%–88%] | 86% [60%–96%] | 2 | 0 | 0.5 |
| single-step (6) | 100% [61%–100%] | 100% [61%–100%] | 0 | 0 | 1 |
| multi-step (2) | 50% [9%–91%] | 100% [34%–100%] | 1 | 0 | 1 |
| stacked (3) | 0% [0%–56%] | 33% [6%–79%] | 1 | 0 | 1 |
| compliance (3) | 100% [44%–100%] | 100% [44%–100%] | 0 | 0 | 1 |

| Task | Without | With |
|---|---|---|
| bracket_room | 1/1 | 1/1 |
| breakpoint | 1/1 | 1/1 |
| comms_review | 1/1 | 1/1 |
| conversion_all_in | 0/1 | 0/1 |
| federal_tax | 1/1 | 1/1 |
| irmaa | 1/1 | 1/1 |
| rmd | 1/1 | 1/1 |
| rollover_flags | 1/1 | 1/1 |
| senior_phaseout | 0/1 | 0/1 |
| ss_claim | 1/1 | 1/1 |
| tax_torpedo | 1/1 | 1/1 |
| taxable_ss | 1/1 | 1/1 |
| widow_all_in | 0/1 | 1/1 |
| widow_penalty | 0/1 | 1/1 |

## Dollars off a year, per numeric question

- Without tools: $133 [1–298], 4 misses, median miss $316, worst $821
- With tools: $95 [0–244], 2 misses, median miss $522, worst $821

## Why the remaining misses happened

Tools were called on 10/14 questions (23 calls, at most 7 on one question, 0 returned an error).

| Kind | Misses |
|---|---|
| overruled | 2 |
| misused tools | 0 |
| no tool | 0 |

| Question | Kind | Key | Answer | Mistake named by the grader |
|---|---|---|---|---|
| conversion_all_in-000 | overruled | 16601 | 17422.0 | combined senior phase-out |
| senior_phaseout-000 | overruled | 16152 | 15928.0 | combined senior phase-out |
