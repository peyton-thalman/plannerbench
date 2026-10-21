# PlannerBench results: tools-high-10x1

## Accuracy by task

Each cell: accuracy (right/asked, 95% interval). With repeated runs, every run counts in the cell.

| Task | claude-haiku-5-5 |
|---|---|
| bracket_room | 90% (9/10, 60–98) |
| breakpoint | 100% (10/10, 72–100) |
| comms_review | 100% (10/10, 72–100) |
| conversion_all_in | 80% (8/10, 49–94) |
| federal_tax | 100% (10/10, 72–100) |
| irmaa | 100% (10/10, 72–100) |
| rmd | 90% (9/10, 60–98) |
| rollover_flags | 100% (10/10, 72–100) |
| senior_phaseout | 0% (0/10, 0–28) |
| ss_claim | 100% (10/10, 72–100) |
| tax_torpedo | 100% (10/10, 72–100) |
| taxable_ss | 90% (9/10, 60–98) |
| widow_all_in | 60% (6/10, 31–83) |
| widow_penalty | 70% (7/10, 40–89) |
| **Overall** | **84% (118/140, 77–89)** |

## Where replies landed

| Model | correct | wrong | truncated | no_answer | refusal | error |
|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 118 | 22 | 0 | 0 | 0 | 0 |

## Review queue (different models agree with each other, not the key)

Needs two or more models to run.

## Mistakes by type

| Model | combined senior phase-out | pre-2022 RMD table | right IRMAA tier, wrong cents | left out Medicare | one-step shortcut | counted adult child | counted other fund family | missed a violation | flagged a compliant sentence | missed an issue | flagged a non-issue | unexplained |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 19 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |

## Wrong answers

| Case | Model | Key | Got | Off by | Mistake |
|---|---|---|---|---|---|
| `bracket_room-007` | claude-haiku-5-5 | 190,100.00 | 79,500.00 | -110,600.00 |  |
| `conversion_all_in-000` | claude-haiku-5-5 | 16,601.00 | 17,422.00 | +821.00 | combined senior phase-out |
| `conversion_all_in-007` | claude-haiku-5-5 | 13,363.00 | 13,604.00 | +241.00 | combined senior phase-out |
| `rmd-009` | claude-haiku-5-5 | 44,454.00 | 38,415.00 | -6,039.00 |  |
| `senior_phaseout-000` | claude-haiku-5-5 | 16,152.00 | 15,928.00 | -224.00 | combined senior phase-out |
| `senior_phaseout-001` | claude-haiku-5-5 | 16,074.00 | 15,854.00 | -220.00 | combined senior phase-out |
| `senior_phaseout-002` | claude-haiku-5-5 | 16,628.00 | 16,379.00 | -249.00 | combined senior phase-out |
| `senior_phaseout-003` | claude-haiku-5-5 | 23,555.00 | 22,794.00 | -761.00 | combined senior phase-out |
| `senior_phaseout-004` | claude-haiku-5-5 | 35,336.00 | 34,085.00 | -1,251.00 | combined senior phase-out |
| `senior_phaseout-005` | claude-haiku-5-5 | 24,620.00 | 23,943.00 | -677.00 | combined senior phase-out |
| `senior_phaseout-006` | claude-haiku-5-5 | 14,368.00 | 14,240.00 | -128.00 | combined senior phase-out |
| `senior_phaseout-007` | claude-haiku-5-5 | 21,639.00 | 21,121.00 | -518.00 | combined senior phase-out |
| `senior_phaseout-008` | claude-haiku-5-5 | 29,935.00 | 28,973.00 | -962.00 | combined senior phase-out |
| `senior_phaseout-009` | claude-haiku-5-5 | 24,917.00 | 24,060.00 | -857.00 | combined senior phase-out |
| `taxable_ss-005` | claude-haiku-5-5 | 5,625.00 | 15,563.00 | +9,938.00 |  |
| `widow_all_in-000` | claude-haiku-5-5 | 8,049.00 | 8,458.00 | +409.00 | combined senior phase-out |
| `widow_all_in-002` | claude-haiku-5-5 | 9,564.00 | 10,841.00 | +1,277.00 | combined senior phase-out |
| `widow_all_in-005` | claude-haiku-5-5 | 9,448.00 | 9,732.00 | +284.00 | combined senior phase-out |
| `widow_all_in-007` | claude-haiku-5-5 | 9,997.00 | 10,810.00 | +813.00 | combined senior phase-out |
| `widow_penalty-002` | claude-haiku-5-5 | 9,422.00 | 9,906.00 | +484.00 | combined senior phase-out |
| `widow_penalty-004` | claude-haiku-5-5 | 5,631.00 | 6,013.00 | +382.00 | combined senior phase-out |
| `widow_penalty-009` | claude-haiku-5-5 | 9,139.00 | 10,010.00 | +871.00 | combined senior phase-out |
