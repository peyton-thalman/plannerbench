# PlannerBench results: luna-codex-10x1

## Accuracy by task

Each cell: accuracy (right/asked, 95% interval). With repeated runs, every run counts in the cell.

| Task | codex:gpt-6-luna |
|---|---|
| bracket_room | 80% (8/10, 49–94) |
| breakpoint | 100% (10/10, 72–100) |
| comms_review | 100% (10/10, 72–100) |
| conversion_all_in | 0% (0/10, 0–28) |
| federal_tax | 50% (5/10, 24–76) |
| irmaa | 33% (3/9, 12–65) |
| rmd | 90% (9/10, 60–98) |
| rollover_flags | 80% (8/10, 49–94) |
| senior_phaseout | 0% (0/10, 0–28) |
| ss_claim | 80% (8/10, 49–94) |
| tax_torpedo | 10% (1/10, 2–40) |
| taxable_ss | 90% (9/10, 60–98) |
| widow_all_in | 0% (0/10, 0–28) |
| widow_penalty | 0% (0/10, 0–28) |
| **Overall** | **51% (71/139, 43–59)** |

## Where replies landed

| Model | correct | wrong | truncated | no_answer | refusal | error |
|---|---|---|---|---|---|---|
| codex:gpt-6-luna | 71 | 68 | 0 | 0 | 0 | 0 |

## Review queue (different models agree with each other, not the key)

Needs two or more models to run.

## Mistakes by type

| Model | combined senior phase-out | pre-2022 RMD table | right IRMAA tier, wrong cents | left out Medicare | one-step shortcut | counted adult child | counted other fund family | missed a violation | flagged a compliant sentence | missed an issue | flagged a non-issue | unexplained |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codex:gpt-6-luna | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 63 |

## Wrong answers

| Case | Model | Key | Got | Off by | Mistake |
|---|---|---|---|---|---|
| `bracket_room-001` | codex:gpt-6-luna | 15,600.00 | 0.00 | -15,600.00 |  |
| `bracket_room-006` | codex:gpt-6-luna | 49,300.00 | 46,950.00 | -2,350.00 |  |
| `conversion_all_in-000` | codex:gpt-6-luna | 16,601.00 | 14,489.00 | -2,112.00 |  |
| `conversion_all_in-001` | codex:gpt-6-luna | 17,437.00 | 0.00 | -17,437.00 |  |
| `conversion_all_in-002` | codex:gpt-6-luna | 11,043.00 | 10,000.00 | -1,043.00 |  |
| `conversion_all_in-003` | codex:gpt-6-luna | 9,600.00 | 0.00 | -9,600.00 |  |
| `conversion_all_in-004` | codex:gpt-6-luna | 4,515.00 | 0.00 | -4,515.00 |  |
| `conversion_all_in-005` | codex:gpt-6-luna | 21,014.00 | 22,400.00 | +1,386.00 |  |
| `conversion_all_in-006` | codex:gpt-6-luna | 20,155.00 | 21,024.00 | +869.00 |  |
| `conversion_all_in-007` | codex:gpt-6-luna | 13,363.00 | 10,468.00 | -2,895.00 |  |
| `conversion_all_in-008` | codex:gpt-6-luna | 21,299.00 | 20,369.00 | -930.00 |  |
| `conversion_all_in-009` | codex:gpt-6-luna | 14,019.00 | 16,624.00 | +2,605.00 |  |
| `federal_tax-003` | codex:gpt-6-luna | 53,909.00 | 51,400.00 | -2,509.00 |  |
| `federal_tax-005` | codex:gpt-6-luna | 12,956.00 | 0.00 | -12,956.00 |  |
| `federal_tax-006` | codex:gpt-6-luna | 4,449.00 | 0.00 | -4,449.00 |  |
| `federal_tax-007` | codex:gpt-6-luna | 52,104.00 | 49,334.00 | -2,770.00 |  |
| `federal_tax-009` | codex:gpt-6-luna | 13,228.00 | 12,699.00 | -529.00 |  |
| `irmaa-001` | codex:gpt-6-luna | 527.50 | 608.70 | +81.20 |  |
| `irmaa-002` | codex:gpt-6-luna | 649.20 | 608.90 | -40.30 |  |
| `irmaa-003` | codex:gpt-6-luna | 527.50 | 608.90 | +81.40 |  |
| `irmaa-005` | codex:gpt-6-luna | 405.80 | 527.50 | +121.70 |  |
| `irmaa-006` | codex:gpt-6-luna | 527.50 | 608.70 | +81.20 |  |
| `irmaa-007` | codex:gpt-6-luna | 527.50 | 649.20 | +121.70 |  |
| `rmd-000` | codex:gpt-6-luna | 59,455.00 | 64,434.00 | +4,979.00 | pre-2022 RMD table |
| `rollover_flags-000` | codex:gpt-6-luna | COST,NUA | AGE55,COST,NUA |  | flagged a non-issue |
| `rollover_flags-003` | codex:gpt-6-luna | COST,NUA | AGE55,COST,NUA |  | flagged a non-issue |
| `senior_phaseout-000` | codex:gpt-6-luna | 16,152.00 | 15,726.00 | -426.00 |  |
| `senior_phaseout-001` | codex:gpt-6-luna | 16,074.00 | 12,775.00 | -3,299.00 |  |
| `senior_phaseout-002` | codex:gpt-6-luna | 16,628.00 | 11,500.00 | -5,128.00 |  |
| `senior_phaseout-003` | codex:gpt-6-luna | 23,555.00 | 15,600.00 | -7,955.00 |  |
| `senior_phaseout-004` | codex:gpt-6-luna | 35,336.00 | 33,085.00 | -2,251.00 |  |
| `senior_phaseout-005` | codex:gpt-6-luna | 24,620.00 | 23,943.00 | -677.00 | combined senior phase-out |
| `senior_phaseout-006` | codex:gpt-6-luna | 14,368.00 | 13,451.00 | -917.00 |  |
| `senior_phaseout-007` | codex:gpt-6-luna | 21,639.00 | 22,725.00 | +1,086.00 |  |
| `senior_phaseout-008` | codex:gpt-6-luna | 29,935.00 | 17,393.00 | -12,542.00 |  |
| `senior_phaseout-009` | codex:gpt-6-luna | 24,917.00 | 25,500.00 | +583.00 |  |
| `ss_claim-005` | codex:gpt-6-luna | 2,307.00 | 2,305.00 | -2.00 |  |
| `ss_claim-006` | codex:gpt-6-luna | 3,267.00 | 3,742.00 | +475.00 |  |
| `tax_torpedo-000` | codex:gpt-6-luna | 0.00 | 600.00 | +600.00 |  |
| `tax_torpedo-001` | codex:gpt-6-luna | 4,680.00 | 8,580.00 | +3,900.00 |  |
| `tax_torpedo-002` | codex:gpt-6-luna | 2,220.00 | 1,200.00 | -1,020.00 | one-step shortcut |
| `tax_torpedo-003` | codex:gpt-6-luna | 2,853.00 | 1,620.00 | -1,233.00 |  |
| `tax_torpedo-004` | codex:gpt-6-luna | 2,112.00 | 3,740.00 | +1,628.00 |  |
| `tax_torpedo-005` | codex:gpt-6-luna | 8,915.00 | 0.00 | -8,915.00 |  |
| `tax_torpedo-007` | codex:gpt-6-luna | 1,978.00 | 2,099.00 | +121.00 |  |
| `tax_torpedo-008` | codex:gpt-6-luna | 0.00 | 2,400.00 | +2,400.00 |  |
| `tax_torpedo-009` | codex:gpt-6-luna | 4,200.00 | 4,648.00 | +448.00 |  |
| `taxable_ss-005` | codex:gpt-6-luna | 5,625.00 | 19,750.00 | +14,125.00 |  |
| `widow_all_in-000` | codex:gpt-6-luna | 8,049.00 | 19,000.00 | +10,951.00 |  |
| `widow_all_in-001` | codex:gpt-6-luna | 31.00 | 0.00 | -31.00 |  |
| `widow_all_in-002` | codex:gpt-6-luna | 9,564.00 | 14,000.00 | +4,436.00 |  |
| `widow_all_in-003` | codex:gpt-6-luna | 10,768.00 | 8,350.00 | -2,418.00 |  |
| `widow_all_in-004` | codex:gpt-6-luna | 11,272.00 | 3,220.00 | -8,052.00 |  |
| `widow_all_in-005` | codex:gpt-6-luna | 9,448.00 | 13,000.00 | +3,552.00 |  |
| `widow_all_in-006` | codex:gpt-6-luna | 9,155.00 | 12,904.00 | +3,749.00 |  |
| `widow_all_in-007` | codex:gpt-6-luna | 9,997.00 | 13,702.00 | +3,705.00 |  |
| `widow_all_in-008` | codex:gpt-6-luna | 6,561.00 | 17,713.00 | +11,152.00 |  |
| `widow_all_in-009` | codex:gpt-6-luna | 10,113.00 | 7,136.00 | -2,977.00 |  |
| `widow_penalty-000` | codex:gpt-6-luna | 1,540.00 | 0.00 | -1,540.00 |  |
| `widow_penalty-001` | codex:gpt-6-luna | 1,052.00 | 1,760.00 | +708.00 |  |
| `widow_penalty-002` | codex:gpt-6-luna | 9,422.00 | 0.00 | -9,422.00 |  |
| `widow_penalty-003` | codex:gpt-6-luna | 4,635.00 | 715.00 | -3,920.00 |  |
| `widow_penalty-004` | codex:gpt-6-luna | 5,631.00 | 10,689.00 | +5,058.00 |  |
| `widow_penalty-005` | codex:gpt-6-luna | 2,667.00 | 3,050.00 | +383.00 |  |
| `widow_penalty-006` | codex:gpt-6-luna | 4,321.00 | 6,534.00 | +2,213.00 |  |
| `widow_penalty-007` | codex:gpt-6-luna | 5,112.00 | 0.00 | -5,112.00 |  |
| `widow_penalty-008` | codex:gpt-6-luna | 5,204.00 | 0.00 | -5,204.00 |  |
| `widow_penalty-009` | codex:gpt-6-luna | 9,139.00 | 8,183.00 | -956.00 |  |
