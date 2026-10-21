# Tool effect: claude-haiku-5-5

Before: `live-high-10x1`. After, with the MoneyGuide planning tools (MCP): `tools-high-10x1`. 140 questions asked both ways; p is a paired McNemar test on the questions that flipped.

| Questions | `live-high-10x1` | `tools-high-10x1` | Fixed | Broken | p |
|---|---|---|---|---|---|
| All (140) | 77% [70%–83%] | 84% [77%–89%] | 13 | 3 | 0.0213 |
| single-step (60) | 97% [89%–99%] | 95% [86%–98%] | 2 | 3 | 1 |
| multi-step (20) | 75% [53%–89%] | 85% [64%–95%] | 2 | 0 | 0.5 |
| stacked (30) | 17% [7%–34%] | 47% [30%–64%] | 9 | 0 | 0.00391 |
| compliance (30) | 100% [89%–100%] | 100% [89%–100%] | 0 | 0 | 1 |

| Task | Before | After |
|---|---|---|
| bracket_room | 10/10 | 9/10 |
| breakpoint | 10/10 | 10/10 |
| comms_review | 10/10 | 10/10 |
| conversion_all_in | 3/10 | 8/10 |
| federal_tax | 10/10 | 10/10 |
| irmaa | 9/10 | 10/10 |
| rmd | 10/10 | 9/10 |
| rollover_flags | 10/10 | 10/10 |
| senior_phaseout | 0/10 | 0/10 |
| ss_claim | 9/10 | 10/10 |
| tax_torpedo | 9/10 | 10/10 |
| taxable_ss | 10/10 | 9/10 |
| widow_all_in | 2/10 | 6/10 |
| widow_penalty | 6/10 | 7/10 |

## Dollars off a year, per numeric question

- `live-high-10x1`: $171 [110–238], 32 misses, median miss $568, worst $1,512
- `tools-high-10x1`: $1,255 [103–3,443], 22 misses, median miss $719, worst $110,600

## Why the remaining misses happened

Tools were called on 96/140 questions (227 calls, at most 9 on one question, 0 returned an error).

| Kind | Misses |
|---|---|
| overruled | 18 |
| misused tools | 2 |
| no tool | 2 |

| Question | Kind | Key | Answer | Mistake named by the grader |
|---|---|---|---|---|
| bracket_room-007 | misused tools | 190100 | 79500.0 |  |
| conversion_all_in-000 | overruled | 16601 | 17422.0 | combined senior phase-out |
| conversion_all_in-007 | overruled | 13363 | 13604.0 | combined senior phase-out |
| rmd-009 | no tool | 44454 | 38415.0 |  |
| senior_phaseout-000 | overruled | 16152 | 15928.0 | combined senior phase-out |
| senior_phaseout-001 | overruled | 16074 | 15854.0 | combined senior phase-out |
| senior_phaseout-002 | overruled | 16628 | 16379.0 | combined senior phase-out |
| senior_phaseout-003 | overruled | 23555 | 22794.0 | combined senior phase-out |
| senior_phaseout-004 | overruled | 35336 | 34085.0 | combined senior phase-out |
| senior_phaseout-005 | overruled | 24620 | 23943.0 | combined senior phase-out |
| senior_phaseout-006 | overruled | 14368 | 14240.0 | combined senior phase-out |
| senior_phaseout-007 | overruled | 21639 | 21121.0 | combined senior phase-out |
| senior_phaseout-008 | overruled | 29935 | 28973.0 | combined senior phase-out |
| senior_phaseout-009 | overruled | 24917 | 24060.0 | combined senior phase-out |
| taxable_ss-005 | no tool | 5625 | 15563.0 |  |
| widow_all_in-000 | overruled | 8049 | 8458.0 | combined senior phase-out |
| widow_all_in-002 | misused tools | 9564 | 10841.0 | combined senior phase-out |
| widow_all_in-005 | overruled | 9448 | 9732.0 | combined senior phase-out |
| widow_all_in-007 | overruled | 9997 | 10810.0 | combined senior phase-out |
| widow_penalty-002 | overruled | 9422 | 9906.0 | combined senior phase-out |
| widow_penalty-004 | overruled | 5631 | 6013.0 | combined senior phase-out |
| widow_penalty-009 | overruled | 9139 | 10010.0 | combined senior phase-out |
