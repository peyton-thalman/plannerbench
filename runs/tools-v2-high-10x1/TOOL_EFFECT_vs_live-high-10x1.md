# Tool effect: claude-haiku-5-5

Before: `live-high-10x1`. After, with the MoneyGuide planning tools (MCP): `tools-v2-high-10x1`. 50 questions asked both ways; p is a paired McNemar test on the questions that flipped.

| Questions | `live-high-10x1` | `tools-v2-high-10x1` | Fixed | Broken | p |
|---|---|---|---|---|---|
| All (50) | 40% [28%–54%] | 100% [93%–100%] | 30 | 0 | 1.86e-09 |
| multi-step (20) | 75% [53%–89%] | 100% [84%–100%] | 5 | 0 | 0.0625 |
| stacked (30) | 17% [7%–34%] | 100% [89%–100%] | 25 | 0 | 5.96e-08 |

| Task | Before | After |
|---|---|---|
| conversion_all_in | 3/10 | 10/10 |
| senior_phaseout | 0/10 | 10/10 |
| tax_torpedo | 9/10 | 10/10 |
| widow_all_in | 2/10 | 10/10 |
| widow_penalty | 6/10 | 10/10 |

## Dollars off a year, per numeric question

- `live-high-10x1`: $318 [210–428], 30 misses, median miss $501, worst $1,358
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
