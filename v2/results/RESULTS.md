# PlannerBench v2 results

Built by `v2/grade.py` from the saved replies. Brackets are 95% Wilson intervals over items (a repeated item counts once).

## Bad inputs

What each model did with the 30 corrupted notes. The five outcomes add to 100%. "Caught it" = named the planted problem and gave no number (asking a question is not required). Only "Ran out of room" (no answer because the reply hit the 4,000-token limit) is purely rule-based; the other four depend on whether the reply named the problem, which Claude Haiku 5.5 judged and the lead AI agent (Claude) adjudicated where the judge's label contradicted the reply's own words (`v2/runs/bad/adjudication.jsonl`, `v2/results/ADJUDICATION.md`). "Judge only" is the catch rate before adjudication; "Labels changed" counts the replies whose label was overridden.

| Model | Tier | Runs/item | Caught it | Noticed, answered anyway | Missed it, answered anyway | Declined for another reason | Ran out of room | Caught (judge only) | Labels changed | False alarm (clean + odd) | Correct notes: ran out of room | Clean answers right | Net |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GPT-6.1 Sol | frontier | 1 | 80% [63–90] | 20% | 0% | 0% | 0% | 73% | 2 | 2% [0–13] | 0% | 100% | +78 |
| Claude Sonnet 5.5 | frontier | 1 | 73% [56–86] | 20% | 7% | 0% | 0% | 73% | 0 | 0% [0–9] | 0% | 93% | +73 |
| Claude Haiku 5.5 | mid | 2 | 65% [47–79] | 17% | 18% | 0% | 0% | 65% | 0 | 0% [0–9] | 0% | 85% | +65 |
| GPT-6.1 Terra | mid | 2 | 67% [49–81] | 33% | 0% | 0% | 0% | 62% | 14 | 2% [0–13] | 0% | 97% | +64 |
| DeepSeek V4.1 Flash | cheap | 3 | 61% [43–76] | 14% | 18% | 0% | 7% | 61% | 2 | 0% [0–9] | 2% | 93% | +61 |
| Gemini 3.8 Flash | mid | 2 | 92% [76–97] | 0% | 0% | 8% | 0% | 92% | 0 | 50% [35–65] | 0% | 47% | +42 |
| GLM 5.3 Flash | cheap | 3 | 40% [25–58] | 31% | 14% | 0% | 14% | 40% | 0 | 0% [0–9] | 14% | 33% | +40 |
| Gemini 3.1 Pro | frontier | 1 | 70% [52–83] | 0% | 3% | 27% | 0% | 70% | 0 | 68% [52–80] | 0% | 30% | +2 |
| Llama 4 Maverick | cheap | 3 | 3% [1–17] | 16% | 81% | 0% | 0% | 3% | 0 | 2% [0–12] | 0% | 30% | +2 |
| Mistral Small (2603) | cheap | 3 | 1% [0–13] | 1% | 91% | 7% | 0% | 1% | 0 | 1% [0–10] | 0% | 22% | +0 |
| gpt-oss-120b | cheap | 3 | 3% [1–17] | 0% | 93% | 3% | 0% | 3% | 0 | 5% [1–16] | 0% | 20% | -2 |

All models, 720 replies to corrupted notes: caught 299, flagged_but_answered 98, silent_number 282, declined_other_reason 22, ran_out_of_room 19; judge only: caught 294, flagged_but_answered 85, silent_number 295, declined_other_reason 27, ran_out_of_room 19.
Replies to correct notes that ran out of room (not counted as false alarms, not right): 19.

### Catch rate by error type

| Model | transposed | impossible_age | spending | conflict | over_limit |
|---|---|---|---|---|---|
| Claude Sonnet 5.5 | 83% | 100% | 100% | 67% | 17% |
| GPT-6.1 Sol | 100% | 100% | 33% | 100% | 67% |
| Gemini 3.1 Pro | 67% | 83% | 100% | 100% | 0% |
| GPT-6.1 Terra | 100% | 100% | 0% | 100% | 33% |
| Gemini 3.8 Flash | 83% | 100% | 100% | 100% | 75% |
| Claude Haiku 5.5 | 50% | 83% | 92% | 100% | 0% |
| DeepSeek V4.1 Flash | 44% | 44% | 89% | 100% | 28% |
| GLM 5.3 Flash | 44% | 50% | 33% | 67% | 6% |
| gpt-oss-120b | 17% | 0% | 0% | 0% | 0% |
| Llama 4 Maverick | 0% | 0% | 0% | 17% | 0% |
| Mistral Small (2603) | 0% | 0% | 0% | 6% | 0% |
| **All replies, pooled** | 43% [35–51] | 47% [39–55] | 41% [33–49] | 60% [52–67] | 17% [11–24] |
| Mean of the model rates | 54% | 60% | 50% | 69% | 20% |

### Run-to-run agreement (corrupted notes asked more than once)

| Model | Items | Same outcome of five, every run | Same caught / not caught (binary) |
|---|---|---|---|
| GPT-6.1 Terra | 30 | 93% | 93% |
| Gemini 3.8 Flash | 30 | 97% | 97% |
| Claude Haiku 5.5 | 30 | 77% | 83% |
| DeepSeek V4.1 Flash | 30 | 60% | 67% |
| GLM 5.3 Flash | 30 | 27% | 57% |
| gpt-oss-120b | 30 | 100% | 100% |
| Llama 4 Maverick | 30 | 80% | 93% |
| Mistral Small (2603) | 30 | 87% | 97% |

### Twin pairs handled right both ways (runs averaged within each of the 30 pairs)

| Model | Both right |
|---|---|
| Claude Sonnet 5.5 | 70% [52–83] |
| GPT-6.1 Sol | 80% [63–90] |
| Gemini 3.1 Pro | 27% [14–44] |
| GPT-6.1 Terra | 63% [46–78] |
| Gemini 3.8 Flash | 47% [30–64] |
| Claude Haiku 5.5 | 53% [36–70] |
| DeepSeek V4.1 Flash | 59% [41–74] |
| GLM 5.3 Flash | 9% [3–24] |
| gpt-oss-120b | 0% [0–11] |
| Llama 4 Maverick | 0% [0–11] |
| Mistral Small (2603) | 0% [0–11] |

## Hard tier

| Model | Tier | Runs/item | Alone | Truncated | $ per right answer | With engine | Called a tool | Never called |
|---|---|---|---|---|---|---|---|---|
| GPT-6.1 Sol | frontier | 1 | 98% [88–100] | 0% | $0.0032 | 95% [84–99] | 79% | 9 |
| GPT-6.1 Terra | mid | 2 | 80% [65–89] | 0% | $0.0019 | 86% [72–93] | 81% | 8 |
| Claude Sonnet 5.5 | frontier | 1 | 62% [47–75] | 0% | $0.0173 | – | – | – |
| Claude Haiku 5.5 | mid | 2 | 52% [38–67] | 2% | $0.0022 | 62% [47–75] | 50% | 21 |
| Gemini 3.1 Pro | frontier | 1 | 29% [17–44] | 0% | $0.0513 | – | – | – |
| Gemini 3.8 Flash | mid | 1 | 29% [17–44] | 36% | $0.0195 | – | – | – |
| DeepSeek V4.1 Flash | cheap | 2 | 29% [17–44] | 71% | $0.0036 | 79% [64–88] | 90% | 4 |
| GLM 5.3 Flash | cheap | 2 | 15% [8–29] | 20% | $0.0063 | 43% [29–58] | 86% | 6 |
| gpt-oss-120b | cheap | 2 | 7% [2–19] | 0% | $0.0016 | 10% [4–22] | 79% | 9 |
| Mistral Small (2603) | cheap | 2 | 7% [2–19] | 0% | $0.0087 | 7% [2–19] | 79% | 9 |
| Llama 4 Maverick | cheap | 2 | 6% [2–17] | 0% | $0.0185 | 5% [1–16] | 79% | 9 |

### Tool track token budget

The 4,000-token limit applies to each turn of the tool loop, up to 8 turns. 10 of 336 tool-track replies used more than 4,000 output tokens in total; the most was 7,135.

| Model | Replies | Over 4,000 in total | Most output tokens |
|---|---|---|---|
| Llama 4 Maverick | 42 | 0 | 1,130 |
| Mistral Small (2603) | 42 | 0 | 1,898 |
| Claude Haiku 5.5 | 42 | 0 | 3,475 |
| gpt-oss-120b | 42 | 0 | 1,431 |
| DeepSeek V4.1 Flash | 42 | 9 | 7,135 |
| GLM 5.3 Flash | 42 | 1 | 4,211 |
| GPT-6.1 Sol | 42 | 0 | 901 |
| GPT-6.1 Terra | 42 | 0 | 801 |

### Paired comparisons (same 42 hard questions, first run of each)

| A | B | A right | B right | Both | Only A | Only B | Neither | Exact McNemar p |
|---|---|---|---|---|---|---|---|---|
| DeepSeek V4.1 Flash with the engine | Claude Sonnet 5.5 alone | 33 | 26 | 23 | 10 | 3 | 6 | 0.092 |
