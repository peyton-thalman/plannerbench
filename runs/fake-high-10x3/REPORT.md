# PlannerBench results: fake-high-10x3

## Accuracy by task

Each cell: accuracy (right/asked, 95% interval). With repeated runs, every run counts in the cell.

| Task | fake |
|---|---|
| bracket_room | 80% (24/30, 63–90) |
| federal_tax | 80% (24/30, 63–90) |
| irmaa | 73% (22/30, 56–86) |
| rmd | 80% (24/30, 63–90) |
| ss_claim | 80% (24/30, 63–90) |
| taxable_ss | 77% (23/30, 59–88) |
| **Overall** | **78% (141/180, 72–84)** |

## Where replies landed

| Model | correct | wrong | truncated | no_answer | refusal | error |
|---|---|---|---|---|---|---|
| fake | 141 | 32 | 0 | 7 | 0 | 0 |

## Consistency (same question, repeated)

- fake: same answer every time on 29/60 questions

## Review queue (different models agree with each other, not the key)

Needs two or more models to run.

## Mistakes by type

| Model | combined senior phase-out | pre-2022 RMD table | right IRMAA tier, wrong cents | left out Medicare | one-step shortcut | counted adult child | counted other fund family | missed a violation | flagged a compliant sentence | missed an issue | flagged a non-issue | unexplained |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fake | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 32 |

## Wrong answers

| Case | Model | Key | Got | Off by | Mistake |
|---|---|---|---|---|---|
| `bracket_room-002` | fake | 8,000.00 | 11,000.00 | +3,000.00 |  |
| `bracket_room-003` | fake | 25,600.00 | 29,160.00 | +3,560.00 |  |
| `bracket_room-005` | fake | 0.00 | 1,000.00 | +1,000.00 |  |
| `bracket_room-006` | fake | 49,300.00 | 61,625.00 | +12,325.00 |  |
| `bracket_room-008` | fake | 0.00 | 1,000.00 | +1,000.00 |  |
| `bracket_room-009` | fake | 186,750.00 | 234,437.50 | +47,687.50 |  |
| `federal_tax-003` | fake | 53,909.00 | 48,518.10 | -5,390.90 |  |
| `federal_tax-005` | fake | 12,956.00 | 17,195.00 | +4,239.00 |  |
| `federal_tax-006` | fake | 4,449.00 | 4,004.10 | -444.90 |  |
| `federal_tax-007` | fake | 52,104.00 | 46,893.60 | -5,210.40 |  |
| `federal_tax-008` | fake | 5,960.00 | 6,556.00 | +596.00 |  |
| `irmaa-000` | fake | 284.10 | 255.69 | -28.41 |  |
| `irmaa-003` | fake | 527.50 | 474.75 | -52.75 |  |
| `irmaa-004` | fake | 689.90 | 620.91 | -68.99 |  |
| `irmaa-005` | fake | 405.80 | 1,446.38 | +1,040.58 |  |
| `irmaa-006` | fake | 527.50 | 1,580.25 | +1,052.75 |  |
| `irmaa-009` | fake | 405.80 | 1,446.38 | +1,040.58 |  |
| `rmd-002` | fake | 57,660.00 | 72,075.00 | +14,415.00 |  |
| `rmd-004` | fake | 90,545.00 | 81,490.50 | -9,054.50 |  |
| `rmd-004` | fake | 90,545.00 | 113,181.25 | +22,636.25 |  |
| `rmd-005` | fake | 65,972.00 | 59,374.80 | -6,597.20 |  |
| `rmd-008` | fake | 116,931.00 | 129,624.10 | +12,693.10 |  |
| `rmd-009` | fake | 44,454.00 | 48,899.40 | +4,445.40 |  |
| `ss_claim-000` | fake | 1,558.00 | 2,402.20 | +844.20 |  |
| `ss_claim-004` | fake | 3,360.00 | 5,200.00 | +1,840.00 |  |
| `ss_claim-005` | fake | 2,307.00 | 3,537.70 | +1,230.70 |  |
| `ss_claim-009` | fake | 4,158.00 | 3,742.20 | -415.80 |  |
| `taxable_ss-001` | fake | 36,550.00 | 32,895.00 | -3,655.00 |  |
| `taxable_ss-003` | fake | 20,825.00 | 19,742.50 | -1,082.50 |  |
| `taxable_ss-005` | fake | 5,625.00 | 8,031.25 | +2,406.25 |  |
| `taxable_ss-006` | fake | 18,143.00 | 16,328.70 | -1,814.30 |  |
| `taxable_ss-007` | fake | 38,760.00 | 43,636.00 | +4,876.00 |  |
