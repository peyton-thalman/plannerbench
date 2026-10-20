# PlannerBench results: or-5models-15x1

## Accuracy by task

Each cell: accuracy (right/asked, 95% interval). With repeated runs, every run counts in the cell.

| Task | or:anthropic/claude-haiku-5.5@anthropic | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | or:openai/gpt-oss-120b@deepinfra/bf16 | or:qwen/qwen3.8-flash@alibaba | or:z-ai/glm-5.3-flash@z-ai/fp8 |
|---|---|---|---|---|---|
| bracket_room | 93% (14/15, 70–99) | 73% (11/15, 48–89) | 40% (6/15, 20–64) | 47% (7/15, 25–70) | 87% (13/15, 62–96) |
| breakpoint | 100% (15/15, 80–100) | 100% (15/15, 80–100) | 100% (15/15, 80–100) | 100% (15/15, 80–100) | 100% (15/15, 80–100) |
| comms_review | 100% (15/15, 80–100) | 100% (15/15, 80–100) | 100% (15/15, 80–100) | 100% (15/15, 80–100) | 100% (15/15, 80–100) |
| conversion_all_in | 40% (6/15, 20–64) | 53% (8/15, 30–75) | 7% (1/15, 1–30) | 0% (0/5, 0–43) | 33% (5/15, 15–58) |
| federal_tax | 100% (15/15, 80–100) | 67% (10/15, 42–85) | 0% (0/15, 0–20) | 0% (0/15, 0–20) | 60% (9/15, 36–80) |
| irmaa | 87% (13/15, 62–96) | 73% (11/15, 48–89) | 0% (0/15, 0–20) | 0% (0/15, 0–20) | 20% (3/15, 7–45) |
| rmd | 100% (15/15, 80–100) | 100% (15/15, 80–100) | 33% (5/15, 15–58) | 40% (6/15, 20–64) | 73% (11/15, 48–89) |
| rollover_flags | 80% (12/15, 55–93) | 87% (13/15, 62–96) | 73% (11/15, 48–89) | 73% (11/15, 48–89) | 80% (12/15, 55–93) |
| senior_phaseout | 0% (0/15, 0–20) | 20% (3/15, 7–45) | 7% (1/15, 1–30) | 0% (0/1, 0–79) | 27% (4/15, 11–52) |
| ss_claim | 80% (12/15, 55–93) | 100% (15/15, 80–100) | 93% (14/15, 70–99) | 93% (14/15, 70–99) | 93% (14/15, 70–99) |
| tax_torpedo | 80% (12/15, 55–93) | 93% (14/15, 70–99) | 20% (3/15, 7–45) | 7% (1/15, 1–30) | 73% (11/15, 48–89) |
| taxable_ss | 93% (14/15, 70–99) | 100% (15/15, 80–100) | 47% (7/15, 25–70) | 80% (12/15, 55–93) | 73% (11/15, 48–89) |
| widow_all_in | 20% (3/15, 7–45) | 33% (5/15, 15–58) | 0% (0/7, 0–35) | 0% (0/11, 0–26) | 20% (3/15, 7–45) |
| widow_penalty | 47% (7/15, 25–70) | 47% (7/15, 25–70) | 0% (0/15, 0–20) | 0% (0/15, 0–20) | 27% (4/15, 11–52) |
| **Overall** | **73% (153/210, 66–78)** | **75% (157/210, 68–80)** | **39% (78/202, 32–45)** | **45% (81/182, 37–52)** | **62% (130/210, 55–68)** |

## Where replies landed

| Model | correct | wrong | truncated | no_answer | refusal | error |
|---|---|---|---|---|---|---|
| or:anthropic/claude-haiku-5.5@anthropic | 153 | 57 | 0 | 0 | 0 | 0 |
| or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 157 | 47 | 4 | 2 | 0 | 0 |
| or:openai/gpt-oss-120b@deepinfra/bf16 | 78 | 98 | 26 | 0 | 0 | 0 |
| or:qwen/qwen3.8-flash@alibaba | 81 | 12 | 89 | 0 | 0 | 24 |
| or:z-ai/glm-5.3-flash@z-ai/fp8 | 130 | 73 | 7 | 0 | 0 | 0 |

## Review queue (different models agree with each other, not the key)

- `bracket_room-013`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8, or:z-ai/glm-5.3-flash@z-ai/fp8 all said 220,100.00; key says 211,400.00
- `conversion_all_in-000`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 17,422.00; key says 16,601.00
- `conversion_all_in-010`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8, or:z-ai/glm-5.3-flash@z-ai/fp8 all said 13,526.00; key says 14,291.00
- `conversion_all_in-011`: or:deepseek/deepseek-v4.1-flash@deepinfra/fp8, or:z-ai/glm-5.3-flash@z-ai/fp8 all said 22,127.00; key says 22,131.00
- `irmaa-010`: or:deepseek/deepseek-v4.1-flash@deepinfra/fp8, or:z-ai/glm-5.3-flash@z-ai/fp8 all said 649.30; key says 649.20
- `rmd-007`: or:openai/gpt-oss-120b@deepinfra/bf16, or:qwen/qwen3.8-flash@alibaba all said 120,695.00; key says 111,733.00
- `rmd-008`: or:openai/gpt-oss-120b@deepinfra/bf16, or:qwen/qwen3.8-flash@alibaba all said 126,310.00; key says 116,931.00
- `rollover_flags-011`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8, or:openai/gpt-oss-120b@deepinfra/bf16, or:qwen/qwen3.8-flash@alibaba, or:z-ai/glm-5.3-flash@z-ai/fp8 all said AGE55,NUA; key says AGE55
- `rollover_flags-012`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8, or:openai/gpt-oss-120b@deepinfra/bf16, or:qwen/qwen3.8-flash@alibaba, or:z-ai/glm-5.3-flash@z-ai/fp8 all said NUA; key says NONE
- `rollover_flags-013`: or:openai/gpt-oss-120b@deepinfra/bf16, or:qwen/qwen3.8-flash@alibaba, or:z-ai/glm-5.3-flash@z-ai/fp8 all said AGE55,NUA; key says AGE55
- `rollover_flags-014`: or:anthropic/claude-haiku-5.5@anthropic, or:openai/gpt-oss-120b@deepinfra/bf16, or:qwen/qwen3.8-flash@alibaba all said NUA; key says NONE
- `senior_phaseout-000`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8, or:z-ai/glm-5.3-flash@z-ai/fp8 all said 15,928.00; key says 16,152.00
- `senior_phaseout-002`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 16,379.00; key says 16,628.00
- `senior_phaseout-003`: or:anthropic/claude-haiku-5.5@anthropic, or:z-ai/glm-5.3-flash@z-ai/fp8 all said 22,794.00; key says 23,555.00
- `senior_phaseout-005`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 23,943.00; key says 24,620.00
- `senior_phaseout-008`: or:anthropic/claude-haiku-5.5@anthropic, or:z-ai/glm-5.3-flash@z-ai/fp8 all said 28,973.00; key says 29,935.00
- `senior_phaseout-009`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 24,060.00; key says 24,917.00
- `senior_phaseout-010`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 25,619.00; key says 26,391.00
- `senior_phaseout-011`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8, or:z-ai/glm-5.3-flash@z-ai/fp8 all said 18,683.00; key says 19,063.00
- `senior_phaseout-012`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 20,326.00; key says 20,995.00
- `senior_phaseout-013`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 28,038.00; key says 29,023.00
- `senior_phaseout-014`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 30,131.00; key says 31,159.00
- `tax_torpedo-011`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8, or:z-ai/glm-5.3-flash@z-ai/fp8 all said 4,865.00; key says 5,141.00
- `widow_all_in-012`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 12,707.00; key says 11,571.00
- `widow_penalty-002`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 9,906.00; key says 9,422.00
- `widow_penalty-004`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 6,013.00; key says 5,631.00
- `widow_penalty-009`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 10,010.00; key says 9,139.00
- `widow_penalty-011`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 7,531.00; key says 6,883.00

## Mistakes by type

| Model | combined senior phase-out | pre-2022 RMD table | right IRMAA tier, wrong cents | left out Medicare | one-step shortcut | counted adult child | counted other fund family | missed a violation | flagged a compliant sentence | missed an issue | flagged a non-issue | unexplained |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| or:anthropic/claude-haiku-5.5@anthropic | 32 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 21 |
| or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 21 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 20 |
| or:openai/gpt-oss-120b@deepinfra/bf16 | 0 | 8 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 4 | 85 |
| or:qwen/qwen3.8-flash@alibaba | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 5 |
| or:z-ai/glm-5.3-flash@z-ai/fp8 | 7 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 56 |

## Wrong answers

| Case | Model | Key | Got | Off by | Mistake |
|---|---|---|---|---|---|
| `bracket_room-001` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 15,600.00 | 15,300.00 | -300.00 |  |
| `bracket_room-001` | or:qwen/qwen3.8-flash@alibaba | 15,600.00 | 16,000.00 | +400.00 |  |
| `bracket_room-001` | or:openai/gpt-oss-120b@deepinfra/bf16 | 15,600.00 | 6,062.00 | -9,538.00 |  |
| `bracket_room-002` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 8,000.00 | 7,050.00 | -950.00 |  |
| `bracket_room-002` | or:openai/gpt-oss-120b@deepinfra/bf16 | 8,000.00 | 8,600.00 | +600.00 |  |
| `bracket_room-003` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 25,600.00 | 25,300.00 | -300.00 |  |
| `bracket_room-003` | or:openai/gpt-oss-120b@deepinfra/bf16 | 25,600.00 | 7,950.00 | -17,650.00 |  |
| `bracket_room-006` | or:openai/gpt-oss-120b@deepinfra/bf16 | 49,300.00 | 50,036.00 | +736.00 |  |
| `bracket_room-007` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 190,100.00 | 189,800.00 | -300.00 |  |
| `bracket_room-009` | or:openai/gpt-oss-120b@deepinfra/bf16 | 186,750.00 | 214,200.00 | +27,450.00 |  |
| `bracket_room-013` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 211,400.00 | 220,100.00 | +8,700.00 |  |
| `bracket_room-013` | or:anthropic/claude-haiku-5.5@anthropic | 211,400.00 | 220,100.00 | +8,700.00 |  |
| `bracket_room-013` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 211,400.00 | 220,100.00 | +8,700.00 |  |
| `bracket_room-013` | or:openai/gpt-oss-120b@deepinfra/bf16 | 211,400.00 | 197,250.00 | -14,150.00 |  |
| `conversion_all_in-000` | or:anthropic/claude-haiku-5.5@anthropic | 16,601.00 | 17,422.00 | +821.00 | combined senior phase-out |
| `conversion_all_in-000` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 16,601.00 | 17,422.00 | +821.00 | combined senior phase-out |
| `conversion_all_in-000` | or:openai/gpt-oss-120b@deepinfra/bf16 | 16,601.00 | 13,792.00 | -2,809.00 |  |
| `conversion_all_in-001` | or:anthropic/claude-haiku-5.5@anthropic | 17,437.00 | 17,478.00 | +41.00 |  |
| `conversion_all_in-001` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 17,437.00 | 16,542.00 | -895.00 |  |
| `conversion_all_in-001` | or:openai/gpt-oss-120b@deepinfra/bf16 | 17,437.00 | 14,124.00 | -3,313.00 |  |
| `conversion_all_in-002` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 11,043.00 | 10,940.00 | -103.00 |  |
| `conversion_all_in-002` | or:openai/gpt-oss-120b@deepinfra/bf16 | 11,043.00 | 9,573.00 | -1,470.00 |  |
| `conversion_all_in-004` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 4,515.00 | 5,542.00 | +1,027.00 |  |
| `conversion_all_in-004` | or:openai/gpt-oss-120b@deepinfra/bf16 | 4,515.00 | 4,080.00 | -435.00 |  |
| `conversion_all_in-005` | or:anthropic/claude-haiku-5.5@anthropic | 21,014.00 | 21,565.00 | +551.00 | combined senior phase-out |
| `conversion_all_in-005` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 21,014.00 | 21,633.00 | +619.00 |  |
| `conversion_all_in-005` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 21,014.00 | 21,020.00 | +6.00 |  |
| `conversion_all_in-005` | or:openai/gpt-oss-120b@deepinfra/bf16 | 21,014.00 | 20,047.00 | -967.00 |  |
| `conversion_all_in-006` | or:anthropic/claude-haiku-5.5@anthropic | 20,155.00 | 20,196.00 | +41.00 |  |
| `conversion_all_in-006` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 20,155.00 | 19,481.00 | -674.00 |  |
| `conversion_all_in-006` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 20,155.00 | 20,160.00 | +5.00 |  |
| `conversion_all_in-006` | or:openai/gpt-oss-120b@deepinfra/bf16 | 20,155.00 | 18,794.00 | -1,361.00 |  |
| `conversion_all_in-007` | or:anthropic/claude-haiku-5.5@anthropic | 13,363.00 | 13,590.00 | +227.00 |  |
| `conversion_all_in-007` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 13,363.00 | 13,243.00 | -120.00 |  |
| `conversion_all_in-007` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 13,363.00 | 13,369.00 | +6.00 |  |
| `conversion_all_in-007` | or:openai/gpt-oss-120b@deepinfra/bf16 | 13,363.00 | 10,862.00 | -2,501.00 |  |
| `conversion_all_in-009` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 14,019.00 | 13,918.00 | -101.00 |  |
| `conversion_all_in-009` | or:openai/gpt-oss-120b@deepinfra/bf16 | 14,019.00 | 11,556.00 | -2,463.00 |  |
| `conversion_all_in-010` | or:anthropic/claude-haiku-5.5@anthropic | 14,291.00 | 13,526.00 | -765.00 | combined senior phase-out |
| `conversion_all_in-010` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 14,291.00 | 13,526.00 | -765.00 | combined senior phase-out |
| `conversion_all_in-010` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 14,291.00 | 13,526.00 | -765.00 | combined senior phase-out |
| `conversion_all_in-010` | or:openai/gpt-oss-120b@deepinfra/bf16 | 14,291.00 | 12,760.00 | -1,531.00 |  |
| `conversion_all_in-011` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 22,131.00 | 22,127.00 | -4.00 |  |
| `conversion_all_in-011` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 22,131.00 | 22,127.00 | -4.00 |  |
| `conversion_all_in-011` | or:openai/gpt-oss-120b@deepinfra/bf16 | 22,131.00 | 22,359.00 | +228.00 |  |
| `conversion_all_in-012` | or:anthropic/claude-haiku-5.5@anthropic | 22,993.00 | 23,157.00 | +164.00 |  |
| `conversion_all_in-012` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 22,993.00 | 24,436.00 | +1,443.00 |  |
| `conversion_all_in-012` | or:openai/gpt-oss-120b@deepinfra/bf16 | 22,993.00 | 22,852.00 | -141.00 |  |
| `conversion_all_in-013` | or:anthropic/claude-haiku-5.5@anthropic | 17,811.00 | 18,171.00 | +360.00 |  |
| `conversion_all_in-013` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 17,811.00 | 18,111.00 | +300.00 |  |
| `conversion_all_in-013` | or:openai/gpt-oss-120b@deepinfra/bf16 | 17,811.00 | 14,752.00 | -3,059.00 |  |
| `conversion_all_in-014` | or:anthropic/claude-haiku-5.5@anthropic | 11,211.00 | 11,252.00 | +41.00 |  |
| `federal_tax-000` | or:openai/gpt-oss-120b@deepinfra/bf16 | 42,268.00 | 42,766.00 | +498.00 |  |
| `federal_tax-002` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 18,463.00 | 18,475.00 | +12.00 |  |
| `federal_tax-002` | or:openai/gpt-oss-120b@deepinfra/bf16 | 18,463.00 | 18,301.00 | -162.00 |  |
| `federal_tax-003` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 53,909.00 | 51,980.00 | -1,929.00 |  |
| `federal_tax-004` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 46,468.00 | 46,474.00 | +6.00 |  |
| `federal_tax-005` | or:openai/gpt-oss-120b@deepinfra/bf16 | 12,956.00 | 12,824.00 | -132.00 |  |
| `federal_tax-006` | or:openai/gpt-oss-120b@deepinfra/bf16 | 4,449.00 | 5,360.00 | +911.00 |  |
| `federal_tax-007` | or:openai/gpt-oss-120b@deepinfra/bf16 | 52,104.00 | 53,649.00 | +1,545.00 |  |
| `federal_tax-008` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 5,960.00 | 4,520.00 | -1,440.00 |  |
| `federal_tax-008` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 5,960.00 | 5,968.00 | +8.00 |  |
| `federal_tax-008` | or:openai/gpt-oss-120b@deepinfra/bf16 | 5,960.00 | 6,100.00 | +140.00 |  |
| `federal_tax-009` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 13,228.00 | 13,662.00 | +434.00 |  |
| `federal_tax-010` | or:openai/gpt-oss-120b@deepinfra/bf16 | 45,073.00 | 44,831.00 | -242.00 |  |
| `federal_tax-011` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 6,860.00 | 6,868.00 | +8.00 |  |
| `federal_tax-011` | or:openai/gpt-oss-120b@deepinfra/bf16 | 6,860.00 | 6,934.00 | +74.00 |  |
| `federal_tax-013` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 66,078.00 | 65,424.00 | -654.00 |  |
| `federal_tax-013` | or:openai/gpt-oss-120b@deepinfra/bf16 | 66,078.00 | 64,705.00 | -1,373.00 |  |
| `federal_tax-014` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 52,744.00 | 49,814.00 | -2,930.00 |  |
| `federal_tax-014` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 52,744.00 | 52,828.00 | +84.00 |  |
| `federal_tax-014` | or:openai/gpt-oss-120b@deepinfra/bf16 | 52,744.00 | 53,911.00 | +1,167.00 |  |
| `federal_tax-014` | or:qwen/qwen3.8-flash@alibaba | 52,744.00 | 52,926.00 | +182.00 |  |
| `irmaa-001` | or:openai/gpt-oss-120b@deepinfra/bf16 | 527.50 | 230.80 | -296.70 |  |
| `irmaa-002` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 649.20 | 649.50 | +0.30 | right IRMAA tier, wrong cents |
| `irmaa-002` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 649.20 | 649.30 | +0.10 | right IRMAA tier, wrong cents |
| `irmaa-002` | or:openai/gpt-oss-120b@deepinfra/bf16 | 649.20 | 477.80 | -171.40 |  |
| `irmaa-003` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 527.50 | 446.50 | -81.00 |  |
| `irmaa-003` | or:anthropic/claude-haiku-5.5@anthropic | 527.50 | 527.60 | +0.10 | right IRMAA tier, wrong cents |
| `irmaa-003` | or:openai/gpt-oss-120b@deepinfra/bf16 | 527.50 | 329.70 | -197.80 |  |
