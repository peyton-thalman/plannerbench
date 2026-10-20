# PlannerBench results: live-high-10x1

## Accuracy by task

| Task | claude-haiku-5-5 | claude-sonnet-5-5 |
|---|---|---|
| bracket_room | 100% (10/10) | 100% (10/10) |
| breakpoint | 100% (10/10) | 100% (10/10) |
| comms_review | 100% (10/10) | 100% (10/10) |
| conversion_all_in | 30% (3/10) | 80% (8/10) |
| federal_tax | 100% (10/10) | 100% (10/10) |
| irmaa | 90% (9/10) | 100% (10/10) |
| rmd | 100% (10/10) | 100% (10/10) |
| rollover_flags | 100% (10/10) | 100% (10/10) |
| senior_phaseout | 0% (0/10) | 10% (1/10) |
| ss_claim | 90% (9/10) | 80% (8/10) |
| tax_torpedo | 90% (9/10) | 100% (10/10) |
| taxable_ss | 100% (10/10) | 100% (10/10) |
| widow_all_in | 20% (2/10) | 20% (2/10) |
| widow_penalty | 60% (6/10) | 80% (8/10) |
| **Overall** | **77% (108/140)** | **84% (117/140)** |

## Where replies landed

| Model | correct | wrong | no_answer | refusal | error |
|---|---|---|---|---|---|
| claude-haiku-5-5 | 108 | 32 | 0 | 0 | 0 |
| claude-sonnet-5-5 | 117 | 23 | 0 | 0 | 0 |

## Review queue (different models agree with each other, not the key)

- `conversion_all_in-007`: claude-haiku-5-5, claude-sonnet-5-5 all said 13,604.00; key says 13,363.00
- `senior_phaseout-000`: claude-haiku-5-5, claude-sonnet-5-5 all said 15,928.00; key says 16,152.00
- `senior_phaseout-002`: claude-haiku-5-5, claude-sonnet-5-5 all said 16,379.00; key says 16,628.00
- `senior_phaseout-003`: claude-haiku-5-5, claude-sonnet-5-5 all said 22,794.00; key says 23,555.00
- `senior_phaseout-005`: claude-haiku-5-5, claude-sonnet-5-5 all said 23,943.00; key says 24,620.00
- `senior_phaseout-006`: claude-haiku-5-5, claude-sonnet-5-5 all said 14,240.00; key says 14,368.00
- `senior_phaseout-007`: claude-haiku-5-5, claude-sonnet-5-5 all said 21,121.00; key says 21,639.00
- `senior_phaseout-008`: claude-haiku-5-5, claude-sonnet-5-5 all said 28,973.00; key says 29,935.00
- `senior_phaseout-009`: claude-haiku-5-5, claude-sonnet-5-5 all said 24,060.00; key says 24,917.00
- `widow_all_in-000`: claude-haiku-5-5, claude-sonnet-5-5 all said 8,458.00; key says 8,049.00
- `widow_all_in-003`: claude-haiku-5-5, claude-sonnet-5-5 all said 11,481.00; key says 10,768.00
- `widow_all_in-006`: claude-haiku-5-5, claude-sonnet-5-5 all said 9,934.00; key says 9,155.00
- `widow_all_in-007`: claude-haiku-5-5, claude-sonnet-5-5 all said 10,810.00; key says 9,997.00
- `widow_all_in-009`: claude-haiku-5-5, claude-sonnet-5-5 all said 10,754.00; key says 10,113.00
- `widow_penalty-002`: claude-haiku-5-5, claude-sonnet-5-5 all said 9,906.00; key says 9,422.00
- `widow_penalty-004`: claude-haiku-5-5, claude-sonnet-5-5 all said 6,012.00; key says 5,631.00

## Mistakes by type

| Model | combined senior phase-out | left out Medicare | one-step shortcut | counted adult child | counted other fund family | missed a violation | flagged a compliant sentence | missed an issue | flagged a non-issue | unexplained |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |
| claude-sonnet-5-5 | 19 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |

## Wrong answers

| Case | Model | Key | Got | Off by | Mistake |
|---|---|---|---|---|---|
| `conversion_all_in-000` | claude-haiku-5-5 | 16,601.00 | 17,422.00 | +821.00 | combined senior phase-out |
| `conversion_all_in-001` | claude-haiku-5-5 | 17,437.00 | 17,478.00 | +41.00 |  |
| `conversion_all_in-002` | claude-haiku-5-5 | 11,043.00 | 12,401.00 | +1,358.00 |  |
| `conversion_all_in-005` | claude-sonnet-5-5 | 21,014.00 | 24,486.00 | +3,472.00 |  |
| `conversion_all_in-005` | claude-haiku-5-5 | 21,014.00 | 21,631.00 | +617.00 |  |
| `conversion_all_in-006` | claude-haiku-5-5 | 20,155.00 | 20,196.00 | +41.00 |  |
| `conversion_all_in-007` | claude-sonnet-5-5 | 13,363.00 | 13,604.00 | +241.00 | combined senior phase-out |
| `conversion_all_in-007` | claude-haiku-5-5 | 13,363.00 | 13,604.00 | +241.00 | combined senior phase-out |
| `conversion_all_in-009` | claude-haiku-5-5 | 14,019.00 | 13,917.00 | -102.00 |  |
| `irmaa-006` | claude-haiku-5-5 | 527.50 | 649.20 | +121.70 |  |
| `senior_phaseout-000` | claude-sonnet-5-5 | 16,152.00 | 15,928.00 | -224.00 | combined senior phase-out |
| `senior_phaseout-000` | claude-haiku-5-5 | 16,152.00 | 15,928.00 | -224.00 | combined senior phase-out |
| `senior_phaseout-001` | claude-haiku-5-5 | 16,074.00 | 15,854.00 | -220.00 | combined senior phase-out |
| `senior_phaseout-002` | claude-sonnet-5-5 | 16,628.00 | 16,379.00 | -249.00 | combined senior phase-out |
| `senior_phaseout-002` | claude-haiku-5-5 | 16,628.00 | 16,379.00 | -249.00 | combined senior phase-out |
| `senior_phaseout-003` | claude-sonnet-5-5 | 23,555.00 | 22,794.00 | -761.00 | combined senior phase-out |
| `senior_phaseout-003` | claude-haiku-5-5 | 23,555.00 | 22,794.00 | -761.00 | combined senior phase-out |
| `senior_phaseout-004` | claude-sonnet-5-5 | 35,336.00 | 34,084.00 | -1,252.00 | combined senior phase-out |
| `senior_phaseout-004` | claude-haiku-5-5 | 35,336.00 | 34,085.00 | -1,251.00 | combined senior phase-out |
| `senior_phaseout-005` | claude-sonnet-5-5 | 24,620.00 | 23,943.00 | -677.00 | combined senior phase-out |
| `senior_phaseout-005` | claude-haiku-5-5 | 24,620.00 | 23,943.00 | -677.00 | combined senior phase-out |
| `senior_phaseout-006` | claude-sonnet-5-5 | 14,368.00 | 14,240.00 | -128.00 | combined senior phase-out |
| `senior_phaseout-006` | claude-haiku-5-5 | 14,368.00 | 14,240.00 | -128.00 | combined senior phase-out |
| `senior_phaseout-007` | claude-sonnet-5-5 | 21,639.00 | 21,121.00 | -518.00 | combined senior phase-out |
| `senior_phaseout-007` | claude-haiku-5-5 | 21,639.00 | 21,121.00 | -518.00 | combined senior phase-out |
| `senior_phaseout-008` | claude-sonnet-5-5 | 29,935.00 | 28,973.00 | -962.00 | combined senior phase-out |
| `senior_phaseout-008` | claude-haiku-5-5 | 29,935.00 | 28,973.00 | -962.00 | combined senior phase-out |
| `senior_phaseout-009` | claude-sonnet-5-5 | 24,917.00 | 24,060.00 | -857.00 | combined senior phase-out |
| `senior_phaseout-009` | claude-haiku-5-5 | 24,917.00 | 24,060.00 | -857.00 | combined senior phase-out |
| `ss_claim-001` | claude-sonnet-5-5 | 4,061.00 | 3,961.00 | -100.00 |  |
| `ss_claim-004` | claude-haiku-5-5 | 3,360.00 | 3,486.00 | +126.00 |  |
| `ss_claim-006` | claude-sonnet-5-5 | 3,267.00 | 3,227.00 | -40.00 |  |
| `tax_torpedo-008` | claude-haiku-5-5 | 0.00 | 373.00 | +373.00 |  |
| `widow_all_in-000` | claude-sonnet-5-5 | 8,049.00 | 8,458.00 | +409.00 | combined senior phase-out |
| `widow_all_in-000` | claude-haiku-5-5 | 8,049.00 | 8,458.00 | +409.00 | combined senior phase-out |
| `widow_all_in-002` | claude-sonnet-5-5 | 9,564.00 | 10,841.00 | +1,277.00 | combined senior phase-out |
| `widow_all_in-002` | claude-haiku-5-5 | 9,564.00 | 9,950.00 | +386.00 |  |
| `widow_all_in-003` | claude-sonnet-5-5 | 10,768.00 | 11,481.00 | +713.00 | combined senior phase-out |
| `widow_all_in-003` | claude-haiku-5-5 | 10,768.00 | 11,481.00 | +713.00 | combined senior phase-out |
| `widow_all_in-004` | claude-sonnet-5-5 | 11,272.00 | 12,191.00 | +919.00 |  |
| `widow_all_in-004` | claude-haiku-5-5 | 11,272.00 | 12,185.00 | +913.00 |  |
| `widow_all_in-005` | claude-sonnet-5-5 | 9,448.00 | 9,732.00 | +284.00 | combined senior phase-out |
| `widow_all_in-005` | claude-haiku-5-5 | 9,448.00 | 9,498.00 | +50.00 |  |
| `widow_all_in-006` | claude-sonnet-5-5 | 9,155.00 | 9,934.00 | +779.00 | combined senior phase-out |
| `widow_all_in-006` | claude-haiku-5-5 | 9,155.00 | 9,934.00 | +779.00 | combined senior phase-out |
| `widow_all_in-007` | claude-sonnet-5-5 | 9,997.00 | 10,810.00 | +813.00 | combined senior phase-out |
| `widow_all_in-007` | claude-haiku-5-5 | 9,997.00 | 10,810.00 | +813.00 | combined senior phase-out |
| `widow_all_in-009` | claude-sonnet-5-5 | 10,113.00 | 10,754.00 | +641.00 | combined senior phase-out |
| `widow_all_in-009` | claude-haiku-5-5 | 10,113.00 | 10,754.00 | +641.00 | combined senior phase-out |
| `widow_penalty-000` | claude-haiku-5-5 | 1,540.00 | 1,532.00 | -8.00 |  |
| `widow_penalty-002` | claude-sonnet-5-5 | 9,422.00 | 9,906.00 | +484.00 | combined senior phase-out |
| `widow_penalty-002` | claude-haiku-5-5 | 9,422.00 | 9,906.00 | +484.00 | combined senior phase-out |
| `widow_penalty-004` | claude-sonnet-5-5 | 5,631.00 | 6,012.00 | +381.00 | combined senior phase-out |
| `widow_penalty-004` | claude-haiku-5-5 | 5,631.00 | 6,012.00 | +381.00 | combined senior phase-out |
| `widow_penalty-009` | claude-haiku-5-5 | 9,139.00 | 10,010.00 | +871.00 | combined senior phase-out |
