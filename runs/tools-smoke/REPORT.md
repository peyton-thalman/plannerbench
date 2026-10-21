# PlannerBench results: tools-smoke

## Accuracy by task

Each cell: accuracy (right/asked, 95% interval). With repeated runs, every run counts in the cell.

| Task | claude-haiku-5-5 |
|---|---|
| bracket_room | 100% (1/1, 21–100) |
| breakpoint | 100% (1/1, 21–100) |
| comms_review | 100% (1/1, 21–100) |
| conversion_all_in | 0% (0/1, 0–79) |
| federal_tax | 100% (1/1, 21–100) |
| irmaa | 100% (1/1, 21–100) |
| rmd | 100% (1/1, 21–100) |
| rollover_flags | 100% (1/1, 21–100) |
| senior_phaseout | 0% (0/1, 0–79) |
| ss_claim | 100% (1/1, 21–100) |
| tax_torpedo | 100% (1/1, 21–100) |
| taxable_ss | 100% (1/1, 21–100) |
| widow_all_in | 100% (1/1, 21–100) |
| widow_penalty | 100% (1/1, 21–100) |
| **Overall** | **86% (12/14, 60–96)** |

## Where replies landed

| Model | correct | wrong | truncated | no_answer | refusal | error |
|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 12 | 2 | 0 | 0 | 0 | 0 |

## Review queue (different models agree with each other, not the key)

Needs two or more models to run.

## Mistakes by type

| Model | combined senior phase-out | pre-2022 RMD table | right IRMAA tier, wrong cents | left out Medicare | one-step shortcut | counted adult child | counted other fund family | missed a violation | flagged a compliant sentence | missed an issue | flagged a non-issue | unexplained |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Wrong answers

| Case | Model | Key | Got | Off by | Mistake |
|---|---|---|---|---|---|
| `conversion_all_in-000` | claude-haiku-5-5 | 16,601.00 | 17,422.00 | +821.00 | combined senior phase-out |
| `senior_phaseout-000` | claude-haiku-5-5 | 16,152.00 | 15,928.00 | -224.00 | combined senior phase-out |
