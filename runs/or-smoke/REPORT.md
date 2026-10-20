# PlannerBench results: or-smoke

## Accuracy by task

Each cell: accuracy (right/asked, 95% interval). With repeated runs, every run counts in the cell.

| Task | or:anthropic/claude-haiku-5.5@anthropic | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | or:openai/gpt-oss-120b@deepinfra/bf16 | or:qwen/qwen3.8-flash@alibaba | or:z-ai/glm-5.3-flash@z-ai/fp8 |
|---|---|---|---|---|---|
| bracket_room | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) |
| breakpoint | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) |
| comms_review | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) |
| conversion_all_in | 0% (0/1, 0–79) | 0% (0/1, 0–79) | 0% (0/1, 0–79) | 0% (0/1, 0–79) | 100% (1/1, 21–100) |
| federal_tax | 100% (1/1, 21–100) | 0% (0/1, 0–79) | 0% (0/1, 0–79) | 0% (0/1, 0–79) | 100% (1/1, 21–100) |
| irmaa | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 0% (0/1, 0–79) | 0% (0/1, 0–79) | 100% (1/1, 21–100) |
| rmd | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 0% (0/1, 0–79) | n/a | 0% (0/1, 0–79) |
| rollover_flags | 0% (0/1, 0–79) | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) |
| senior_phaseout | 0% (0/1, 0–79) | 0% (0/1, 0–79) | 0% (0/1, 0–79) | 0% (0/1, 0–79) | 0% (0/1, 0–79) |
| ss_claim | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) |
| tax_torpedo | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 0% (0/1, 0–79) | 100% (1/1, 21–100) |
| taxable_ss | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 0% (0/1, 0–79) | n/a | 100% (1/1, 21–100) |
| widow_all_in | 0% (0/1, 0–79) | 0% (0/1, 0–79) | n/a | 0% (0/1, 0–79) | 0% (0/1, 0–79) |
| widow_penalty | 100% (1/1, 21–100) | 100% (1/1, 21–100) | 0% (0/1, 0–79) | 0% (0/1, 0–79) | 0% (0/1, 0–79) |
| **Overall** | **71% (10/14, 45–88)** | **71% (10/14, 45–88)** | **46% (6/13, 23–71)** | **42% (5/12, 19–68)** | **71% (10/14, 45–88)** |

## Where replies landed

| Model | correct | wrong | truncated | no_answer | refusal | error |
|---|---|---|---|---|---|---|
| or:anthropic/claude-haiku-5.5@anthropic | 10 | 4 | 0 | 0 | 0 | 0 |
| or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 10 | 2 | 2 | 0 | 0 | 0 |
| or:openai/gpt-oss-120b@deepinfra/bf16 | 6 | 2 | 5 | 0 | 0 | 0 |
| or:qwen/qwen3.8-flash@alibaba | 5 | 0 | 7 | 0 | 0 | 2 |
| or:z-ai/glm-5.3-flash@z-ai/fp8 | 10 | 4 | 0 | 0 | 0 | 0 |

## Review queue (different models agree with each other, not the key)

- `conversion_all_in-000`: or:anthropic/claude-haiku-5.5@anthropic, or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 all said 17,422.00; key says 16,601.00

## Mistakes by type

| Model | combined senior phase-out | pre-2022 RMD table | right IRMAA tier, wrong cents | left out Medicare | one-step shortcut | counted adult child | counted other fund family | missed a violation | flagged a compliant sentence | missed an issue | flagged a non-issue | unexplained |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| or:anthropic/claude-haiku-5.5@anthropic | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| or:openai/gpt-oss-120b@deepinfra/bf16 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| or:qwen/qwen3.8-flash@alibaba | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| or:z-ai/glm-5.3-flash@z-ai/fp8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |

## Wrong answers

| Case | Model | Key | Got | Off by | Mistake |
|---|---|---|---|---|---|
| `conversion_all_in-000` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 16,601.00 | 17,422.00 | +821.00 | combined senior phase-out |
| `conversion_all_in-000` | or:anthropic/claude-haiku-5.5@anthropic | 16,601.00 | 17,422.00 | +821.00 | combined senior phase-out |
| `federal_tax-000` | or:deepseek/deepseek-v4.1-flash@deepinfra/fp8 | 42,268.00 | 42,274.00 | +6.00 |  |
| `irmaa-000` | or:openai/gpt-oss-120b@deepinfra/bf16 | 284.10 | 188.40 | -95.70 |  |
| `rmd-000` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 59,455.00 | 49,358.00 | -10,097.00 |  |
| `rmd-000` | or:openai/gpt-oss-120b@deepinfra/bf16 | 59,455.00 | 64,433.00 | +4,978.00 | pre-2022 RMD table |
| `rollover_flags-000` | or:anthropic/claude-haiku-5.5@anthropic | COST,NUA | AGE55,COST,NUA |  | flagged a non-issue |
| `senior_phaseout-000` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 16,152.00 | 16,450.00 | +298.00 |  |
| `senior_phaseout-000` | or:anthropic/claude-haiku-5.5@anthropic | 16,152.00 | 15,928.00 | -224.00 | combined senior phase-out |
| `widow_all_in-000` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 8,049.00 | 8,406.00 | +357.00 |  |
| `widow_all_in-000` | or:anthropic/claude-haiku-5.5@anthropic | 8,049.00 | 8,458.00 | +409.00 | combined senior phase-out |
| `widow_penalty-000` | or:z-ai/glm-5.3-flash@z-ai/fp8 | 1,540.00 | 1,459.00 | -81.00 |  |
