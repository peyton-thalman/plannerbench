# PlannerBench results: with-rule-10x1

## Accuracy by task

Each cell: accuracy (right/asked, 95% interval). With repeated runs, every run counts in the cell.

| Task | claude-haiku-5-5 | claude-sonnet-5-5 |
|---|---|---|
| senior_phaseout | 90% (9/10, 60–98) | 100% (10/10, 72–100) |
| widow_all_in | 60% (6/10, 31–83) | 100% (10/10, 72–100) |
| **Overall** | **75% (15/20, 53–89)** | **100% (20/20, 84–100)** |

## Where replies landed

| Model | correct | wrong | truncated | no_answer | refusal | error |
|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 15 | 5 | 0 | 0 | 0 | 0 |
| claude-sonnet-5-5 | 20 | 0 | 0 | 0 | 0 | 0 |

## Review queue (different models agree with each other, not the key)

None.

## Mistakes by type

| Model | combined senior phase-out | pre-2022 RMD table | right IRMAA tier, wrong cents | left out Medicare | one-step shortcut | counted adult child | counted other fund family | missed a violation | flagged a compliant sentence | missed an issue | flagged a non-issue | unexplained |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| claude-sonnet-5-5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Wrong answers

| Case | Model | Key | Got | Off by | Mistake |
|---|---|---|---|---|---|
| `senior_phaseout-008` | claude-haiku-5-5 | 29,935.00 | 28,973.00 | -962.00 | combined senior phase-out |
| `widow_all_in-001` | claude-haiku-5-5 | 31.00 | -105.00 | -136.00 |  |
| `widow_all_in-005` | claude-haiku-5-5 | 9,448.00 | 9,214.00 | -234.00 |  |
| `widow_all_in-008` | claude-haiku-5-5 | 6,561.00 | 6,486.00 | -75.00 |  |
| `widow_all_in-009` | claude-haiku-5-5 | 10,113.00 | 9,879.00 | -234.00 |  |
