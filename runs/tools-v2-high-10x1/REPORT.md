# PlannerBench results: tools-v2-high-10x1

## Accuracy by task

Each cell: accuracy (right/asked, 95% interval). With repeated runs, every run counts in the cell.

| Task | claude-haiku-5-5 |
|---|---|
| conversion_all_in | 100% (10/10, 72–100) |
| senior_phaseout | 100% (10/10, 72–100) |
| tax_torpedo | 100% (10/10, 72–100) |
| widow_all_in | 100% (10/10, 72–100) |
| widow_penalty | 100% (10/10, 72–100) |
| **Overall** | **100% (50/50, 93–100)** |

## Where replies landed

| Model | correct | wrong | truncated | no_answer | refusal | error |
|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 50 | 0 | 0 | 0 | 0 | 0 |

## Review queue (different models agree with each other, not the key)

Needs two or more models to run.

## Mistakes by type

| Model | combined senior phase-out | pre-2022 RMD table | right IRMAA tier, wrong cents | left out Medicare | one-step shortcut | counted adult child | counted other fund family | missed a violation | flagged a compliant sentence | missed an issue | flagged a non-issue | unexplained |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Wrong answers

| Case | Model | Key | Got | Off by | Mistake |
|---|---|---|---|---|---|
