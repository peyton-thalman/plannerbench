# Tool effect: claude-haiku-5-5

Before: `tools-high-10x1`. After, with the MoneyGuide planning tools (MCP): `tools-v2-high-10x1`. 50 questions asked both ways; p is a paired McNemar test on the questions that flipped.

| Questions | `tools-high-10x1` | `tools-v2-high-10x1` | Fixed | Broken | p |
|---|---|---|---|---|---|
| All (50) | 62% [48%–74%] | 100% [93%–100%] | 19 | 0 | 3.81e-06 |
| multi-step (20) | 85% [64%–95%] | 100% [84%–100%] | 3 | 0 | 0.25 |
| stacked (30) | 47% [30%–64%] | 100% [89%–100%] | 16 | 0 | 3.05e-05 |

| Task | Before | After |
|---|---|---|
| conversion_all_in | 8/10 | 10/10 |
| senior_phaseout | 0/10 | 10/10 |
| tax_torpedo | 10/10 | 10/10 |
| widow_all_in | 6/10 | 10/10 |
| widow_penalty | 7/10 | 10/10 |

## Dollars off a year, per numeric question

- `tools-high-10x1`: $229 [133–333], 19 misses, median miss $518, worst $1,277
- `tools-v2-high-10x1`: $0 [0–0], 0 misses

## Why the remaining misses happened

Tools were called on 50/50 questions (164 calls, at most 7 on one question, 0 returned an error).

| Kind | Misses |
|---|---|
| overruled | 0 |
| misused tools | 0 |
| no tool | 0 |

| Question | Kind | Key | Answer | Mistake named by the grader |
|---|---|---|---|---|
