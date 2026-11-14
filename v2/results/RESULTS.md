# PlannerBench v2 results

Built by `v2/grade.py` from the saved replies. Brackets are 95% Wilson intervals over items (a repeated item counts once).

## Bad inputs

| Model | Tier | Runs/item | Caught | Flagged | Asked | No number | Silent number | False alarm (clean + odd) | Clean answers right | Net |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Sonnet 5.5 | frontier | 1 | 0% [0–11] | 0% | 0% | 77% | 23% | 0% [0–9] | 93% | +0 |
| Claude Haiku 5.5 | mid | 1 | 0% [0–35] | 0% | 0% | 71% | 29% | 0% [0–32] | 71% | +0 |
| DeepSeek V4.1 Flash | cheap | 1 | 0% [0–43] | 0% | 0% | 60% | 40% | 0% [0–39] | 100% | +0 |
| GLM 5.3 Flash | cheap | 1 | 0% [0–43] | 0% | 0% | 60% | 40% | 0% [0–39] | 40% | +0 |
| gpt-oss-120b | cheap | 1 | 0% [0–43] | 0% | 0% | 0% | 100% | 0% [0–39] | 20% | +0 |
| Llama 4 Maverick | cheap | 1 | 0% [0–43] | 0% | 0% | 0% | 100% | 0% [0–39] | 40% | +0 |
| GPT-6.1 Terra | mid | 1 | 0% [0–30] | 0% | 0% | 78% | 22% | 10% [2–40] | 89% | -10 |
| GPT-6.1 Sol | frontier | 1 | 0% [0–11] | 0% | 0% | 80% | 20% | 20% [10–35] | 83% | -20 |
| Gemini 3.8 Flash | mid | 1 | 0% [0–35] | 0% | 0% | 100% | 0% | 38% [14–69] | 57% | -38 |
| Gemini 3.1 Pro | frontier | 1 | 0% [0–11] | 0% | 0% | 97% | 3% | 68% [52–80] | 30% | -68 |

## Hard tier

| Model | Tier | Runs/item | Alone | Truncated | $ per right answer | With engine | Called a tool | Never called |
|---|---|---|---|---|---|---|---|---|
| GPT-6.1 Sol | frontier | 1 | 100% [65–100] | 0% | $0.0031 | – | – | – |
| GPT-6.1 Terra | mid | 1 | 71% [36–92] | 0% | $0.0024 | – | – | – |
| Claude Sonnet 5.5 | frontier | 1 | 43% [16–75] | 0% | $0.0240 | – | – | – |
| Claude Haiku 5.5 | mid | 1 | 43% [16–75] | 0% | $0.0029 | 57% [25–84] (n=7) | 43% | 4 |
| Gemini 3.1 Pro | frontier | 1 | 29% [8–64] | 0% | $0.0518 | – | – | – |
| DeepSeek V4.1 Flash | cheap | 1 | 29% [8–64] | 71% | $0.0037 | 71% [36–92] (n=7) | 86% | 1 |
| Gemini 3.8 Flash | mid | 1 | 14% [3–51] | 43% | $0.0412 | – | – | – |
| GLM 5.3 Flash | cheap | 1 | 0% [0–35] | 14% | – | 43% [16–75] (n=7) | 86% | 1 |
| gpt-oss-120b | cheap | 1 | 0% [0–35] | 0% | – | 0% [0–35] (n=7) | 86% | 1 |
| Llama 4 Maverick | cheap | 1 | 0% [0–35] | 0% | – | 0% [0–35] (n=7) | 86% | 1 |
| Mistral Small (2603) | cheap | 1 | 0% [0–35] | 0% | – | 14% [3–51] (n=7) | 86% | 1 |
