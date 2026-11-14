# PlannerBench v2 results

Built by `v2/grade.py` from the saved replies. Brackets are 95% Wilson intervals over items (a repeated item counts once).

## Bad inputs

| Model | Tier | Runs/item | Caught | Flagged | Asked | No number | Silent number | False alarm (clean + odd) | Clean answers right | Net |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Sonnet 5.5 | frontier | 1 | 73% [56–86] | 93% | 80% | 73% | 7% | 0% [0–9] | 93% | +73 |
| GPT-6.1 Sol | frontier | 1 | 73% [56–86] | 93% | 93% | 80% | 0% | 2% [0–13] | 100% | +71 |
| Claude Haiku 5.5 | mid | 2 | 65% [47–79] | 82% | 75% | 65% | 18% | 0% [0–9] | 85% | +65 |
| DeepSeek V4.1 Flash | cheap | 3 | 61% [43–76] | 73% | 62% | 68% | 20% | 0% [0–9] | 93% | +61 |
| GPT-6.1 Terra | mid | 2 | 62% [44–77] | 77% | 70% | 67% | 18% | 2% [0–13] | 97% | +59 |
| Gemini 3.8 Flash | mid | 2 | 92% [76–97] | 92% | 90% | 100% | 0% | 50% [35–65] | 47% | +42 |
| GLM 5.3 Flash | cheap | 3 | 40% [25–58] | 71% | 54% | 54% | 14% | 0% [0–9] | 33% | +40 |
| Gemini 3.1 Pro | frontier | 1 | 70% [52–83] | 70% | 77% | 97% | 3% | 68% [52–80] | 30% | +2 |
| Llama 4 Maverick | cheap | 3 | 3% [1–17] | 19% | 4% | 3% | 81% | 2% [0–12] | 30% | +2 |
| Mistral Small (2603) | cheap | 3 | 1% [0–13] | 2% | 1% | 8% | 91% | 1% [0–10] | 22% | +0 |
| gpt-oss-120b | cheap | 3 | 3% [1–17] | 3% | 3% | 7% | 93% | 5% [1–16] | 20% | -2 |

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
